# Handler パターン

既存 handler から抽出した骨格と、実装時に踏襲する判断基準です。

## 骨格

`create_upload_record.py` が最も標準的な形です。

```python
def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    identity_id = get_identity_id(event)
    if not identity_id:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    body_dict = _parse_body(event)
    if body_dict is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")

    try:
        request_data = CreateUploadRecordRequest.from_dict(body_dict)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    expected_prefix = f"{PRIVATE_PATH_PREFIX}{identity_id}/"
    if not request_data.cloud_storage_path.startswith(expected_prefix):
        return error(HTTPStatus.FORBIDDEN, "cloudStoragePath does not match your identity")

    ...  # 永続化

    return success(HTTPStatus.CREATED, {"message": "created", ...})
```

順序は 認証 → ボディ解析 → 入力検証 → 所有者境界 → 永続化 → レスポンス で固定です。
境界チェックを永続化の後ろに置かないでください。

## 実在 handler 一覧

| メソッド / パス | 実装 | 未認証 | 入力検証 | 成功時 |
|---|---|---|---|---|
| `GET /media/uploads` | [get_upload_records.py](../../../../lambda/media_uploads/get_upload_records.py) | 403 | `GetUploadRecordsRequest.from_dict` | 200 |
| `POST /media/uploads` | [create_upload_record.py](../../../../lambda/media_uploads/create_upload_record.py) | 403 | `CreateUploadRecordRequest.from_dict` | 201 / 既存時 200 |
| `DELETE /media/uploads/{mediaId}` | [delete_upload_record.py](../../../../lambda/media_uploads/delete_upload_record.py) | 403 | `pathParameters.mediaId` | 200 |
| `POST /media/uploads/complete` | [notify_upload_complete.py](../../../../lambda/push_notification/notify_upload_complete.py) | 401 | `successCount` が非負 int | 201 / トークン無し 204 |
| `PUT /devices/token` | [register_device_token.py](../../../../lambda/device_tokens/register_device_token.py) | 403 | `deviceToken` 文字列、`platform` 列挙 | 201 |
| `DELETE /devices/token` | [unregister_device_token.py](../../../../lambda/device_tokens/unregister_device_token.py) | 403 | `deviceToken` 文字列 | 200 |
| `DELETE /users` | [delete_user.py](../../../../lambda/users/delete_user.py) | 401 | なし | 200 / 部分失敗 500 |

未認証時の 401 は `users` と `push_notification` に残る既存実装です。新規実装は 403 に揃えます。

## ステータスコード

| 状況 | コード |
|---|---|
| identity 無し | 403 |
| identity 境界違反（IDOR） | 403 |
| ボディが不正 JSON / 非オブジェクト | 400 |
| 必須欠落・型不正・列挙外 | 400 |
| 対象が存在しない | 404 |
| AWS 呼び出し失敗・想定外例外 | 500 |
| 作成成功 | 201 |
| 取得・更新・削除成功 | 200 |
| 返す本文が無い | 204 |

`HTTPStatus` を使う実装（`media_uploads` / `device_tokens`）と、数値リテラルを使う実装
（`users` / `push_notification`）が混在します。新規実装は `HTTPStatus` を使います。

## 冪等性

- `create_upload_record.py` は `attribute_not_exists(userId) AND attribute_not_exists(mediaId)` を条件に
  `put_item` し、`ConditionalCheckFailedException` を 200 `"Record already exists, skipped"` として扱います。
  クライアントの再送でエラーにしません。
- `register_device_token.py` は `if_not_exists(registeredAt, :now)` で初回登録時刻を保持したまま
  `platform` と `updatedAt` を更新します。

## 例外処理

条件式失敗を 404 に落とす場合は `ClientError` のエラーコードで分岐します（`delete_upload_record.py`）。

```python
except ClientError as e:
    error_code = e.response.get("Error", {}).get("Code")
    if error_code == "ConditionalCheckFailedException":
        return error(HTTPStatus.NOT_FOUND, "Media not found")
    logger.exception("Failed to logically delete item: userId=%s, mediaId=%s", mask_identity(identity_id), media_id)
    return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
```

`put_item` の条件失敗だけを拾う場合は `client.exceptions.ConditionalCheckFailedException` を使えます
（`create_upload_record.py`）。いずれも内部例外の詳細をレスポンス本文へ載せません。

`delete_user.py` は S3、upload records、device tokens をそれぞれ独立の `try` で処理し、
失敗したサブシステム名だけを集約して 500 を返します。片方の失敗で残りをスキップしません。

## ログ

- `logger = logging.getLogger(__name__)` をモジュールスコープに置きます。
- identity は必ず `mask_identity` を通します。生の `cognitoIdentityId`、`deviceToken`、
  リクエストボディをログに出しません。FCM トークンは `token[-4:]` のみです。
- AWS 呼び出し失敗は `logger.exception` で操作名と対象キーを記録します。

## 参考資料

- [docs/lambda.md](../../../../docs/lambda.md)
- [docs/coding_standards.md](../../../../docs/coding_standards.md)
