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
      auth.py                    IdentityId の正本
      response.py                success / error
      masking.py                 MASK / FULLY_MASKED_MAX_LENGTH
      errors.py                  ValidationError / AuthorizationError
      device_token.py            DeviceToken（device_tokens と push_notification で共有）
      dynamodb.py                serialize_item / deserialize_item（Decimal の変換を含む）
      tables.py                  FIELD_USER_ID / FIELD_MEDIA_ID / FIELD_DEVICE_TOKEN
      storage.py                 PRIVATE_PATH_PREFIX
      request.py                 parse_body（本文の JSON オブジェクトを取り出す）
      tests/                     共通処理の単体テスト
    media_uploads/
      __init__.py  constants.py  db.py  models.py
      get_upload_records.py  create_upload_record.py  delete_upload_record.py
      tests/
    device_tokens/
      __init__.py  constants.py  db.py  models.py
      register_device_token.py  unregister_device_token.py
      tests/
    push_notification/
      __init__.py  constants.py  db.py  fcm.py  models.py
      notify_upload_complete.py
      tests/
    users/
      __init__.py  constants.py  db.py  storage.py
      delete_user.py
      tests/
  layers/firebase_admin/requirements.txt
  pytest.ini
  requirements-dev.txt
```

import は、本番とテストのどちらでも修飾付きで書きます。トップレベル名（`from auth import ...`）は使いません。

```python
from cloud_photos.common.auth import IdentityId
from cloud_photos.common.response import error, success
```

## 共通の認証・応答・契約

すべての関数群で `IdentityId` を `cloud_photos.common.auth` から直接 import します。関数群ごとの `auth.py` や再エクスポートは作りません。

応答は `cloud_photos.common.response` の `success(status, body=None)` と `error(status, message)` を使います。
`success` は `body` が `None` なら空文字列を返し、204 の本文なし応答に使えます。本文があれば JSON 化し、JSON にできない値は `str` で文字列にします。

テーブルのキー属性名は `common.tables`、保存パスのプレフィックスは `common.storage`、DynamoDB の値の変換は `common.dynamodb` に置きます。
関数群の `constants.py` には、その関数群だけが使う項目名や上限を残します。`common` から関数群のモジュールは import しません。

## ZIP のビルドと Terraform の配線

ZIP は [scripts/build_lambda.py](../../../../scripts/build_lambda.py) が作ります。`handler` を定義するモジュールを持つパッケージを関数群とみなし、
関数群ごとに `.build/<function_group>.zip` を出力します。

- ZIP には `cloud_photos/__init__.py`、関数群のパッケージ、そこから `cloud_photos.<package>` として import している共有パッケージが入ります。
  `media_uploads`、`device_tokens`、`push_notification`、`users` のすべての ZIP に `common/` が入ります。
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

`users` 以外の `db.py` は `get_table_name()` が `os.environ["TABLE_NAME"]` をキャッシュします。
複数の保存先を扱う `delete_user.py` は handler で環境変数を直接読み、バケット名とテーブル名を `users/storage.py` と `users/db.py` の関数へ引数で渡します。

## 新規関数を追加するとき

1. 既存グループに属するか、新規グループを作るかを決める。新規なら `__init__.py` / handler / `constants.py` / `tests/` を揃え、
   認証と応答は `common` から直接 import する。
2. handler は [handler-patterns.md](handler-patterns.md) の骨格に合わせる。
3. `modules/media_api/` の次のファイルに追加する。新規グループなら `archives.tf` の `local.lambda_packages` に ZIP のパスを足し、
   `main.tf` の `local.lambda_functions` に関数名、`iam.tf` に `aws_iam_role` と用途別の `aws_iam_role_policy`、
   `lambda.tf` に `aws_lambda_function`、`api_gateway.tf` に resource / method / integration / `aws_lambda_permission`。
4. 新しい method / integration を `api_gateway.tf` の `local.api_methods` と `local.api_integrations` に足す。
   忘れるとステージへ反映されません。手順は infra-implementation Skill の media-api-wiring にあります。
5. `tests/` を追加し、`lambda/` で `pytest` を通す。CI も同じ `pytest` を実行するため、ジョブへの追加は要りません。
6. `python scripts/build_lambda.py` で ZIP を作り、`scripts/verify_lambda_packages.py` で新しい handler を読み込めることを確かめる。

## 参考資料

- [docs/lambda.md](../../../../docs/lambda.md)
- [docs/infrastructure.md](../../../../docs/infrastructure.md)
