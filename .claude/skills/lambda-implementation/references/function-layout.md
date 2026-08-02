# 関数グループの構成と配線

`lambda/` の関数グループごとの実ファイルと、Terraform 側の ZIP・環境変数の対応です。

## ディレクトリ

```text
lambda/
  common/
    __init__.py
    auth.py                      get_identity_id / mask_identity の正本
  media_uploads/
    auth.py  constants.py  db.py  models.py  response.py
    get_upload_records.py  create_upload_record.py  delete_upload_record.py
    tests/
  device_tokens/
    auth.py  constants.py  db.py  request_utils.py  response.py
    register_device_token.py  unregister_device_token.py
    tests/
  push_notification/
    auth.py  constants.py  response.py
    notify_upload_complete.py
    tests/
  users/
    auth.py  constants.py  response.py
    delete_user.py
    tests/
  layers/firebase_admin/requirements.txt
  pytest.ini
  requirements-dev.txt
```

Lambda の ZIP はフラット展開されるため、handler からの import は
`from auth import get_identity_id` のようにトップレベル名で書きます。

## auth.py の扱い

| 関数グループ | `auth.py` の実体 |
|---|---|
| `device_tokens` | `from common.auth import ...` の re-export |
| `push_notification` | `from common.auth import ...` の re-export |
| `media_uploads` | 同等実装のコピー |
| `users` | 同等実装のコピー（`requestContext` / `identity` の None を明示的に処理） |

新規関数は `common/auth.py` を re-export する形を採ります。コピーを増やしません。

## response.py の差

`media_uploads` / `device_tokens` / `users` の `success` は本文必須です。
`push_notification` の `success` のみ `body: Any = None` を許し、本文が無い場合は空文字列を返します
（204 を返すため）。本文なしの応答が要るときはこの形を踏襲します。

## Terraform の ZIP 配線

[modules/media_api/main.tf](../../../../modules/media_api/main.tf) の `archive_file` は 2 系統あります。

| ZIP | 生成方法 |
|---|---|
| `media_uploads` | `source_dir` でディレクトリ一括 |
| `users` | `source_dir` + `excludes = ["tests/*", "tests/**"]` |
| `device_tokens` | `locals.device_tokens_sources` の明示リスト（`common/` を同梱） |
| `push_notification` | `locals.push_notification_sources` の明示リスト（`common/` を同梱） |

明示リスト側の関数グループでファイルを追加・削除・改名したら、対応する `locals` を必ず更新します。
更新を忘れると ZIP に入らず、実行時に `ModuleNotFoundError` になります。

## 環境変数

| Lambda | 環境変数 |
|---|---|
| `get_upload_records` / `create_upload_record` / `delete_upload_record` | `TABLE_NAME`（upload records） |
| `register_device_token` / `unregister_device_token` | `TABLE_NAME`（device tokens） |
| `notify_upload_complete` | `TABLE_NAME`（device tokens）、`FIREBASE_CREDENTIALS_SECRET_ARN` |
| `delete_user` | `S3_BUCKET_NAME`、`UPLOAD_RECORDS_TABLE_NAME`、`DEVICE_TOKENS_TABLE_NAME` |

`db.py` を持つグループは `get_table_name()` が `os.environ["TABLE_NAME"]` をキャッシュします。
複数テーブルを扱う `delete_user.py` は `db.py` を持たず、handler で環境変数を直接読みます。

## 新規関数を追加するとき

1. 既存グループに属するか、新規グループを作るかを決める。新規なら `auth.py` / `response.py` /
   `constants.py` / `tests/` を揃える。
2. handler は [handler-patterns.md](handler-patterns.md) の骨格に合わせる。
3. `modules/media_api/main.tf` に `archive_file`（必要なら `locals` のソースリスト）、
   `aws_iam_role` + 用途別 `aws_iam_role_policy`、`local.lambda_functions` への追加、
   `aws_lambda_function`、API Gateway の resource / method / integration / `aws_lambda_permission` を足す。
4. `aws_api_gateway_deployment.media` の `triggers.redeployment` に新しい method / integration の id を追加する。
   忘れるとステージへ反映されません。
5. `tests/` を追加し、`lambda/` 基準で `pytest` を通す。

## 参考資料

- [docs/lambda.md](../../../../docs/lambda.md)
- [docs/infrastructure.md](../../../../docs/infrastructure.md)
