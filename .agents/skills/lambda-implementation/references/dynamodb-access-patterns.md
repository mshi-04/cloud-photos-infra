# DynamoDB アクセスパターン

テーブル定義、共有の値の変換、関数群ごとの操作、対応する IAM です。

## テーブル

| テーブル | HASH | RANGE | 定義 |
|---|---|---|---|
| `<project>-upload-records-<env>` | `userId` | `mediaId` | [modules/media_db/main.tf](../../../../modules/media_db/main.tf) |
| `<project>-device-tokens-<env>` | `userId` | `deviceToken` | [modules/device_token_db/main.tf](../../../../modules/device_token_db/main.tf) |

いずれも `PAY_PER_REQUEST`、GSI なし、PITR 有効。`deletion_protection_enabled` は prod のみ true です。
`Query` は partition key の等価条件が必須なので、現行テーブルでは `userId` を条件に含めます。
`Scan` は `userId` 条件なしでも実行できますが、テーブル全体を読むため現行設計では使いません。追加する前にアクセスパターンとテーブル設計を見直します。

## 共通の変換と db.py

`serialize_item` と `deserialize_item` は `cloud_photos.common.dynamodb` から import します。テーブルのキー属性名（`FIELD_USER_ID`、`FIELD_MEDIA_ID`、`FIELD_DEVICE_TOKEN`）は `cloud_photos.common.tables` に置きます。リクエストの項目名など、その関数群だけが使う定数は各 `constants.py` に残し、入力を解析する `models.py` はテーブル定義に依存させません。

| 関数 | 役割 |
|---|---|
| `common.dynamodb.serialize_item(item)` | `TypeSerializer` で AttributeValue 形式へ |
| `common.dynamodb.deserialize_item(item)` | `TypeDeserializer` + `Decimal` を int / float へ変換 |
| 各 `db.py` の `get_dynamodb_client()` | クライアントを `functools.cache` でキャッシュ |
| 各 `db.py` の `get_table_name()` | `os.environ["TABLE_NAME"]` を `functools.cache` でキャッシュ |
| `media_uploads/db.py` の `put_upload_record` / `mark_upload_record_deleted` / `query_upload_records` | 操作ごとの DynamoDB の呼び出し |

テストでは `get_dynamodb_client.cache_clear()` と `get_table_name.cache_clear()` を呼びます。DynamoDB の呼び出しは操作ごとの関数に分け、値オブジェクトを受け取って、呼び出しの直前に生の値を取り出します。条件式の失敗は関数の中で `bool` に変え、それ以外の `ClientError` はそのまま送出します。応答への変換は handler が行います。

low-level client（`boto3.client("dynamodb")`）を使うため、値は必ず AttributeValue 形式です。
`serialize_item` は `ExpressionAttributeValues` にも使えます。
キーの組み立て（`_key`）とクエリの `ExpressionAttributeValues` は、キャッシュや IAM の境界と同じく関数群に残します。`push_notification/db.py` の読み出しも `deserialize_item` を通します。

```python
"ExpressionAttributeValues": serialize_item({":user_id": identity_id.value})
```

レスポンスの `Decimal` をそのまま `json.dumps` に渡さないため、読み出しは `deserialize_item` を通します。
`LastEvaluatedKey` も同様に変換してからクライアントへ返します。

## Query とページネーション

`media_uploads/db.py` の `query_upload_records`。

```python
params: dict[str, Any] = {
    "TableName": get_table_name(),
    "KeyConditionExpression": f"{FIELD_USER_ID} = :user_id",
    "ExpressionAttributeValues": serialize_item({":user_id": identity_id.value}),
    "Limit": limit.value,
}
if cursor is not None:
    params["ExclusiveStartKey"] = _key(cursor.identity_id, cursor.media_id)
```

`limit` は値オブジェクト `PageLimit` が `MIN_LIMIT` から `MAX_LIMIT` の範囲に丸めます（`DEFAULT_LIMIT = 100`、`MAX_LIMIT = 500`）。
`ExclusiveStartKey` は、所有者を確認済みの `PageCursor` から組み直します。

## 条件付き PutItem

`media_uploads/db.py` の `put_upload_record`。重複作成を例外にせず `False` を返し、handler が 200 に変換します。

```python
try:
    get_dynamodb_client().put_item(
        TableName=get_table_name(),
        Item=serialize_item(item),
        ConditionExpression=f"attribute_not_exists({FIELD_USER_ID}) AND attribute_not_exists({FIELD_MEDIA_ID})",
    )
except ClientError as e:
    if _is_conditional_check_failure(e):
        return False
    raise
return True
```

## UpdateItem と if_not_exists

`register_device_token.py`。初回登録時刻を保ったまま upsert します。

```python
UpdateExpression="SET #platform = :platform, #registeredAt = if_not_exists(#registeredAt, :now), #updatedAt = :now",
ExpressionAttributeNames={"#platform": FIELD_PLATFORM, ...},
ExpressionAttributeValues=serialize_item({":platform": platform, ":now": now}),
```

予約語や定数由来の名前は `ExpressionAttributeNames` で受けます。

## 論理削除

`media_uploads/db.py` の `mark_upload_record_deleted`。物理削除ではなく `isDeleted` と `updatedAt` を立てます。

```python
get_dynamodb_client().update_item(
    TableName=get_table_name(),
    Key=_key(identity_id, media_id),
    UpdateExpression=f"SET {FIELD_IS_DELETED} = :val, {FIELD_UPDATED_AT} = :time",
    ExpressionAttributeValues=serialize_item({":val": True, ":time": updated_at}),
    ConditionExpression=f"attribute_exists({FIELD_USER_ID})",
)
```

`ConditionExpression` が無いと存在しない key に対して upsert してしまい、404 を返せません。
条件失敗は `ClientError` のコードで判定して `False` を返し、handler が 404 に変換します。

タイムスタンプは全実装で `int(time.time() * 1000)`（ミリ秒）です。

## BatchWrite

`users/delete_user.py` のみ物理削除を行います。

- `ProjectionExpression` で key 属性だけを取得してから削除する
- 25 件ずつ `batch_write_item` する
- `UnprocessedItems` は `0.1 * (2 ** attempt)` の指数バックオフで最大 5 回リトライし、
  それでも残る場合は `RuntimeError` にする
- `LastEvaluatedKey` がある限り Query を繰り返す

`users/delete_user.py` の `_batch_delete_items` は、query が返す AttributeValue 形式のキーを `DeleteRequest` にそのまま渡します。ここで再度 `serialize_item` は使いません。

S3 側は `list_object_versions` のページネータで `Versions` と `DeleteMarkers` を集め、
1000 件ごとに `delete_objects` します。`Delete.Objects` の上限が 1000 のためです。
`result["Errors"]` を必ず確認します。返り値が 200 でも個別オブジェクトは失敗しえます。

## IAM との対応

アクションを増やしたら [modules/media_api/iam.tf](../../../../modules/media_api/iam.tf) の
対応する `aws_iam_role_policy` を、infra-implementation Skill の手順で更新します。現状の割り当ては次のとおりです。

| Lambda | DynamoDB アクション | Resource |
|---|---|---|
| `get_upload_records` | `dynamodb:Query` | upload records |
| `create_upload_record` | `dynamodb:PutItem` | upload records |
| `delete_upload_record` | `dynamodb:UpdateItem` | upload records |
| `register_device_token` | `dynamodb:UpdateItem` | device tokens |
| `unregister_device_token` | `dynamodb:DeleteItem` | device tokens |
| `notify_upload_complete` | `dynamodb:Query`、`dynamodb:DeleteItem` | device tokens |
| `delete_user` | `dynamodb:Query`、`dynamodb:BatchWriteItem` | 両テーブル |

ロールは Lambda ごとに分けます。共有ロールへまとめないでください。

## 参考資料

- [docs/security.md](../../../../docs/security.md)
- [docs/coding_standards.md](../../../../docs/coding_standards.md)
- [docs/infrastructure.md](../../../../docs/infrastructure.md)
