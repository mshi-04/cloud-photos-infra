# Handler パターン

既存 handler から抽出した骨格と、実装時に踏襲する判断基準です。

## 骨格

規約に移行済みの `device_tokens/register_device_token.py` が手本です。

```python
def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    body = parse_body(event)
    if body is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")

    try:
        request = RegisterDeviceTokenRequest.parse(body)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    try:
        save_device_token(identity_id, request.device_token, request.platform)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to register device token: userId=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    return success(HTTPStatus.CREATED, {"message": "registered"})
```

所有者確認を含む例は `media_uploads/create_upload_record.py` です。判定は保存パスの値オブジェクトが持ち、handler は結果を応答に変換します。

```python
    try:
        request = CreateUploadRecordRequest.parse(body)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    if not request.cloud_storage_path.belongs_to(identity_id):
        return error(HTTPStatus.FORBIDDEN, "cloudStoragePath does not match your identity")

    uploaded_at = int(time.time() * 1000)
    try:
        created = put_upload_record(identity_id, request, uploaded_at)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to create upload record: userId=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
```

順序は 認証 → ボディ解析 → 入力検証 → 所有者境界 → 永続化 → レスポンス で固定です。
境界チェックを永続化の後ろに置かないでください。前提条件はガード節で先に返し、正常系を最後に置きます。
新しく書く入力の検証は、値オブジェクトの `__post_init__` に置きます（[docs/coding_standards.md](../../../../docs/coding_standards.md)）。

## ステータスと現在の API

ステータスの規則と、現在の API ごとの未認証応答・成功時の応答は、[docs/lambda.md](../../../../docs/lambda.md) の API 応答の契約が正本です。ここには書き写しません。

`HTTPStatus` を使う実装（`media_uploads` / `device_tokens` / `push_notification`）と、数値リテラルを使う実装
（`users`）が混在します。新規実装は `HTTPStatus` を使います。

## 冪等性

- `create_upload_record.py` は `attribute_not_exists(userId) AND attribute_not_exists(mediaId)` を条件に
  `put_item` し（`db.put_upload_record`）、条件式の失敗を 200 `"Record already exists, skipped"` として扱います。
  クライアントの再送でエラーにしません。
- `register_device_token.py` は `if_not_exists(registeredAt, :now)` で初回登録時刻を保持したまま
  `platform` と `updatedAt` を更新します。

## 例外処理

捕捉するのは AWS 呼び出しの失敗（`BotoCoreError`、`ClientError`）だけです。環境変数の欠落など想定外の例外は捕捉せず、
Lambda のエラーとして送出します（API Gateway が 502 を返す）。

条件式の失敗は、`db.py` の関数が `ClientError` のエラーコードで判定して `bool` を返し、handler が応答の意味を決めます
（`delete_upload_record.py` は 404、`create_upload_record.py` は 200）。

```python
try:
    deleted = mark_upload_record_deleted(identity_id, media_id)
except (BotoCoreError, ClientError):
    logger.exception("Failed to logically delete item: userId=%s, mediaId=%s", identity_id, media_id.value)
    return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

if not deleted:
    return error(HTTPStatus.NOT_FOUND, "Media not found")
```

内部例外の詳細をレスポンス本文へ載せません。

`delete_user.py` は S3、upload records、device tokens をそれぞれ独立の `try` で処理し、
失敗したサブシステム名だけを集約して 500 を返します。片方の失敗で残りをスキップしません。

## ログ

- `logger = logging.getLogger(__name__)` をモジュールスコープに置きます。
- identity は、伏せ字にする `IdentityId` を渡すか、`mask_identity` を通します。生の `cognitoIdentityId`、`deviceToken`、
  リクエストボディをログに出しません。FCM トークンは `DeviceToken` で渡し、末尾 4 文字より多くは出しません。
- AWS 呼び出し失敗は `logger.exception` で操作名と対象キーを記録します。

## 参考資料

- [docs/lambda.md](../../../../docs/lambda.md)
- [docs/coding_standards.md](../../../../docs/coding_standards.md)
