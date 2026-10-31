# 関数グループの構成と配線

`lambda/` の関数グループごとの実ファイルと、Terraform 側の ZIP・環境変数の対応です。

## ディレクトリ

`lambda/` はソースのルートで、コードは `cloud_photos` パッケージの下にあります。

```text
lambda/
  cloud_photos/
    __init__.py
    common/
      __init__.py
      auth.py                    get_identity_id / mask_identity の正本
    media_uploads/
      __init__.py  auth.py  constants.py  db.py  models.py  response.py
      get_upload_records.py  create_upload_record.py  delete_upload_record.py
      tests/
    device_tokens/
      __init__.py  auth.py  constants.py  db.py  request_utils.py  response.py
      register_device_token.py  unregister_device_token.py
      tests/
    push_notification/
      __init__.py  auth.py  constants.py  response.py
      notify_upload_complete.py
      tests/
    users/
      __init__.py  auth.py  constants.py  response.py
      delete_user.py
      tests/
  layers/firebase_admin/requirements.txt
  pytest.ini
  requirements-dev.txt
```

import は、本番とテストのどちらでも修飾付きで書きます。トップレベル名（`from auth import ...`）は使いません。

```python
from cloud_photos.media_uploads.auth import get_identity_id
from cloud_photos.users import auth
```

## auth.py の扱い

| 関数グループ | `auth.py` の実体 |
|---|---|
| `device_tokens` | `from cloud_photos.common.auth import ...` の re-export |
| `push_notification` | `from cloud_photos.common.auth import ...` の re-export |
| `media_uploads` | 同等実装のコピー |
| `users` | 同等実装のコピー（`requestContext` / `identity` の None を明示的に処理） |

新規関数は `cloud_photos/common/auth.py` を re-export する形を採ります。コピーを増やしません。

## response.py の差

`media_uploads` / `device_tokens` / `users` の `success` は本文必須です。
`push_notification` の `success` のみ `body: Any = None` を許し、本文が無い場合は空文字列を返します
（204 を返すため）。本文なしの応答が要るときはこの形を踏襲します。

## ZIP のビルドと Terraform の配線

ZIP は [scripts/build_lambda.py](../../../../scripts/build_lambda.py) が作ります。`handler` を定義するモジュールを持つパッケージを関数群とみなし、
関数群ごとに `.build/<function_group>.zip` を出力します。

- ZIP には `cloud_photos/__init__.py`、関数群のパッケージ、そこから `cloud_photos.<package>` として import している共有パッケージが入ります。
  `device_tokens` と `push_notification` の ZIP には `common/` が入ります。
- `tests/` とキャッシュは入りません。
- エントリの順序、更新時刻、権限を固定しているため、同じソースからは同じハッシュの ZIP ができます。

ファイルの追加や削除で、ZIP の定義を直す必要はありません。新しい共有パッケージも、import すれば自動で入ります。
追加や移動の後は [scripts/verify_lambda_packages.py](../../../../scripts/verify_lambda_packages.py) で、
ZIP だけから各 handler を読み込めることを確かめます。手順は [docs/commands.md](../../../../docs/commands.md) にあります。

Terraform は [modules/media_api/archives.tf](../../../../modules/media_api/archives.tf) の `local.lambda_packages` で ZIP のパスを持ち、
`lambda.tf` で `filename` と `filebase64sha256()` に使います。`handler` は `cloud_photos.<function_group>.<module>.handler` です。

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
3. `modules/media_api/` の次のファイルに追加する。新規グループなら `archives.tf` の `local.lambda_packages` に ZIP のパスを足し、
   `main.tf` の `local.lambda_functions` に関数名、`iam.tf` に `aws_iam_role` と用途別の `aws_iam_role_policy`、
   `lambda.tf` に `aws_lambda_function`、`api_gateway.tf` に resource / method / integration / `aws_lambda_permission`。
4. `aws_api_gateway_deployment.media` の `triggers.redeployment` に新しい method / integration の id を追加する。
   忘れるとステージへ反映されません。
5. `tests/` を追加し、`lambda/` で `pytest` を通す。CI も同じ `pytest` を実行するため、ジョブへの追加は要りません。
6. `python scripts/build_lambda.py` で ZIP を作り、`scripts/verify_lambda_packages.py` で新しい handler を読み込めることを確かめる。

## 参考資料

- [docs/lambda.md](../../../../docs/lambda.md)
- [docs/infrastructure.md](../../../../docs/infrastructure.md)
