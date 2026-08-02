# DynamoDB アクセスパターン

テーブル定義、`db.py` のヘルパー、操作別の実装、対応する IAM です。

## テーブル

| テーブル | HASH | RANGE | 定義 |
|---|---|---|---|
| `<project>-upload-records-<env>` | `userId` | `mediaId` | [modules/media_db/main.tf](../../../../modules/media_db/main.tf) |
| `<project>-device-tokens-<env>` | `userId` | `deviceToken` | [modules/device_token_db/main.tf](../../../../modules/device_token_db/main.tf) |

いずれも `PAY_PER_REQUEST`、GSI なし、PITR 有効。`deletion_protection_enabled` は prod のみ true です。
GSI が無いため、`userId` を条件に含まない検索はできません。`Scan` を足す前に設計を見直します。

## db.py

`media_uploads/db.py` と `device_tokens/db.py` は同一内容です。

| 関数 | 役割 |
|---|---|
| `get_dynamodb_client()` | クライアントをモジュールスコープにキャッシュ |
| `get_table_name()` | `os.environ["TABLE_NAME"]` をキャッシュ |
| `serialize_item(item)` | `TypeSerializer` で `{"S": ...}` 形式へ |
| `deserialize_item(item)` | `TypeDeserializer` + `Decimal` を int / float へ変換 |
| `_reset_for_testing()` | キャッシュを破棄。テストの fixture から呼ぶ |

low-level client（`boto3.client("dynamodb")`）を使うため、値は必ず AttributeValue 形式です。
`serialize_item` は `ExpressionAttributeValues` にも使えます。

```python
"ExpressionAttributeValues": serialize_item({":user_id": identity_id})
```

レスポンスの `Decimal` をそのまま `json.dumps` に渡さないため、読み出しは `deserialize_item` を通します。
`LastEvaluatedKey` も同様に変換してからクライアントへ返します。

## Query とページネーション

`get_upload_records.py`。

```python
query_params: Dict[str, Any] = {
    "TableName": get_table_name(),
    "KeyConditionExpression": f"{FIELD_USER_ID} = :user_id",
    "ExpressionAttributeValues": serialize_item({":user_id": identity_id}),
    "Limit": request_data.limit,
}

if request_data.last_evaluated_key_user_id and request_data.last_evaluated_key_media_id:
    query_params["ExclusiveStartKey"] = serialize_item({...})
```

`limit` は `max(1, min(limit, MAX_LIMIT))` で丸めます（`DEFAULT_LIMIT = 100`、`MAX_LIMIT = 500`）。
`ExclusiveStartKey` は検証済み identity から組み直します。

## 条件付き PutItem

`create_upload_record.py`。重複作成を例外にせず 200 で吸収します。

```python
condition = f"attribute_not_exists({FIELD_USER_ID}) AND attribute_not_exists({FIELD_MEDIA_ID})"
try:
    client.put_item(TableName=get_table_name(), Item=serialize_item(item), ConditionExpression=condition)
except client.exceptions.ConditionalCheckFailedException:
    return success(HTTPStatus.OK, {"message": "Record already exists, skipped"})
```

## UpdateItem と if_not_exists

`register_device_token.py`。初回登録時刻を保ったまま upsert します。

```python
UpdateExpression="SET #platform = :platform, #registeredAt = if_not_exists(#registeredAt, :now), #updatedAt = :now",
ExpressionAttributeNames={"#platform": FIELD_PLATFORM, ...},
ExpressionAttributeValues=serialize_item({":platform": platform, ":now": now}),
```

予約語や `constants.py` 由来の名前は `ExpressionAttributeNames` で受けます。

## 論理削除

`delete_upload_record.py`。物理削除ではなく `isDeleted` と `updatedAt` を立てます。

```python
UpdateExpression=f"SET {FIELD_IS_DELETED} = :val, {FIELD_UPDATED_AT} = :time",
ExpressionAttributeValues={":val": {"BOOL": True}, ":time": {"N": str(updated_at)}},
ConditionExpression=f"attribute_exists({FIELD_USER_ID})",
```

`ConditionExpression` が無いと存在しない key に対して upsert してしまい、404 を返せません。
条件失敗は `ClientError` のコードで判定して 404 に変換します。

タイムスタンプは全実装で `int(time.time() * 1000)`（ミリ秒）です。

## BatchWrite

`users/delete_user.py` のみ物理削除を行います。

- `ProjectionExpression` で key 属性だけを取得してから削除する
- 25 件ずつ `batch_write_item` する
- `UnprocessedItems` は `0.1 * (2 ** attempt)` の指数バックオフで最大 5 回リトライし、
  それでも残る場合は `RuntimeError` にする
- `LastEvaluatedKey` がある限り Query を繰り返す

S3 側は `list_object_versions` のページネータで `Versions` と `DeleteMarkers` を集め、
1000 件ごとに `delete_objects` します。`Delete.Objects` の上限が 1000 のためです。
`result["Errors"]` を必ず確認します。返り値が 200 でも個別オブジェクトは失敗しえます。

## IAM との対応

アクションを増やしたら [modules/media_api/main.tf](../../../../modules/media_api/main.tf) の
対応する `aws_iam_role_policy` を更新します。現状の割り当ては次のとおりです。

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
