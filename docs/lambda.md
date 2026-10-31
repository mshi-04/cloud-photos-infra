# Lambda 実装ガイド

この文書は、`lambda/` 配下の Python Lambda を変更する際の実装規約と、API 応答の契約の正本です。

## Layout

Lambda のコードは、`lambda/` をソースのルートとして、`cloud_photos` パッケージの下に関数群ごとにまとめます。1 つの関数群に複数の handler を置き、関数群の中で `auth.py`、`response.py`、`constants.py` などを共有します。

```text
lambda/
  pytest.ini
  cloud_photos/
    common/                  # 複数の関数群で使う共有処理
    media_uploads/           # get_upload_records / create_upload_record / delete_upload_record
    device_tokens/           # register_device_token / unregister_device_token
    push_notification/       # notify_upload_complete
    users/                   # delete_user
    <function_group>/
      __init__.py
      <handler_module>.py    # def handler(event, context)
      auth.py
      response.py
      constants.py
      tests/
        conftest.py
        test_<behavior>.py
```

import は、本番とテストのどちらでも `from cloud_photos.<function_group>.<module> import ...` のように修飾付きで書きます。Lambda の `handler` 設定は `cloud_photos.<function_group>.<handler_module>.handler` です。

ZIP は [scripts/build_lambda.py](../scripts/build_lambda.py) が関数群ごとに `.build/<function_group>.zip` へ作ります。ZIP には、関数群のパッケージと、そこから import している `cloud_photos` の共有パッケージが入り、`tests/` とキャッシュは入りません。Terraform は [modules/media_api/archives.tf](../modules/media_api/archives.tf) でこの ZIP を参照します。新しいファイルや共有処理を追加した場合は、[scripts/verify_lambda_packages.py](../scripts/verify_lambda_packages.py) で、ZIP から各 handler を読み込めることを確かめてください。手順は [commands.md](commands.md) にあります。

## Handler Design

- `handler` は入力の受け渡しと最終レスポンスに留めます。
- 認証、バリデーション、永続化、外部呼び出しを関数単位に分離します。
- API Gateway event の欠落値や不正JSONを明示的に扱います。
- 既存のレスポンス契約を黙って変更しないでください。

## Authentication

認証は API Gateway の IAM 認証で行い、Lambda は所有者確認を行います。Lambda で JWT を検証する処理はありません。

- 業務用のメソッドは `authorization = "AWS_IAM"` です。クライアントは Cognito Identity Pool が発行した一時認証情報で SigV4 署名し、API Gateway が署名を検証します。`authorization = "NONE"` は CORS の `OPTIONS` だけです。
- Lambda は `event.requestContext.identity.cognitoIdentityId` を、呼び出したユーザーの Identity ID として使います。取得には各関数群の `auth.py` の `get_identity_id` を使います。
- 認証済みでも、操作するリソースが本人のものかを Lambda で確認します。S3 は `private/<identity_id>/` のプレフィックス、DynamoDB はパーティションキーの `userId`、ページングは `lastEvaluatedKey.userId` で確かめます。
- 業務メソッドの `authorization` を変えると、Lambda のコードを変えずに認証が外れます。Terraform の変更では、この設定を必ず確認してください。

信頼の境界、IDOR 防止、ログの要件は [security.md](security.md) を参照してください。

## API Response Contract

### 形式

応答は各関数群の `response.py` の `success` と `error` で作ります。

- ヘッダーは `Content-Type: application/json` です。
- 本文は JSON の文字列です。エラーの本文は `{"message": "<理由>"}` です。
- 本文のない応答（204）は、本文を空文字列にします。
- 外部サービスの例外内容やスタックトレースなど、内部の情報を本文に含めないでください。

### ステータス

| 状況 | ステータス |
|---|---|
| 作成・登録に成功した。`PUT /devices/token` は既存のトークンの更新でも 201 | 201 |
| 取得・更新・削除に成功した（`PUT /devices/token` を除く） | 200 |
| 返す本文がない | 204 |
| 本文が不正な JSON、または JSON オブジェクトではない | 400 |
| 必須項目の欠落、型の不正、列挙外の値 | 400 |
| 認証情報（Identity ID）がない | 403。既存の `users` と `push_notification` は 401 |
| 本人のものではないリソースを指定した（IDOR） | 403 |
| 対象が存在しない | 404 |
| AWS 呼び出しの失敗、想定外の例外 | 500 |

新しい API の未認証応答は 403 にします。API Gateway の IAM 認証に失敗したときの応答も 403 のためです。`users`（`DELETE /users`）と `push_notification`（`POST /media/uploads/complete`）の 401 は、クライアントとの互換性のために維持します。401 を 403 に変える場合は、API 互換性の変更として扱い、テストとクライアントへの影響を確認してください。

条件付き書き込みの失敗は、操作ごとに意味を決めます。例えば `create_upload_record` は、同じレコードがある場合に 200 の `Record already exists, skipped` を返し、`delete_upload_record` は対象がない場合に 404 を返します。条件式の失敗を一律に同じステータスにしないでください。

### 現在の API

| メソッド / パス | handler | 未認証 | 成功時 |
|---|---|---|---|
| `GET /media/uploads` | `media_uploads/get_upload_records` | 403 | 200 |
| `POST /media/uploads` | `media_uploads/create_upload_record` | 403 | 201。既存時は 200 |
| `DELETE /media/uploads/{mediaId}` | `media_uploads/delete_upload_record` | 403 | 200 |
| `POST /media/uploads/complete` | `push_notification/notify_upload_complete` | 401 | 201。通知先がない場合は 204 |
| `PUT /devices/token` | `device_tokens/register_device_token` | 403 | 201 |
| `DELETE /devices/token` | `device_tokens/unregister_device_token` | 403 | 200 |
| `DELETE /users` | `users/delete_user` | 401 | 200。一部の削除に失敗した場合は 500 |

## AWS Calls

- `boto3` クライアントは再利用しやすい形にします。
- AWS例外はユーザー向けレスポンスと内部ログを分けて扱います。
- リトライ、重複実行、部分失敗が問題になる処理では冪等性を確認します。

## Logging

- PII、生トークン、認証情報をログに出さないでください。
- 必要な識別子はマスクします。
- エラー時は request id、操作名、失敗理由を最小限記録します。

## Tests

動作を変更したらテストを追加または更新します。テストは `lambda/` で全体を一度に実行できます。

```powershell
ruff format lambda/
ruff check lambda/
pyright
Set-Location lambda
pytest
```

AWS呼び出しはモックし、実リソースを作成しないでください。テストの詳細は [testing.md](testing.md)、コマンドの前提は [commands.md](commands.md) を参照してください。
