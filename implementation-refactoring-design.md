# 実装リファクタリング設計

- 作成日: 2026-11-04
- 更新日: 2026-11-04。`for_each`化の決定
- 状態: 設計のみ。コード・Terraform・文書・Skillの変更はまだ行わない
- 設計の起点: `develop` の `1242b7f`
- 前の設計: [AI文書・開発基盤リファクタリング設計](ai-documentation-refactoring-design.md)（以下「前設計」）

## 1. 目的と前提

前設計の段階1〜8で、文書・Skill・規約・ツールが揃い、Lambdaの関数群も規約へ移行した。ただし前設計の段階6は関数群の中の書き方を揃えることが中心で、関数群をまたぐ重複は残っている。Terraformの繰り返しは、前設計の第7.2節で`for_each`化を見送ったため残っている。

本設計はその残りを対象にする。AIが手本として真似る書き方を1つにし、APIを足すときに触る箇所を減らし、コードが自身の規約（[coding_standards.md](docs/coding_standards.md)）に従う状態にする。

- 外部から見える挙動（API応答、IAM権限、リソースの設定値）を変えない。変わるものは個別に明記する。
- handlerのテストの期待値を変えない。
- 本番運用はまだ開始していない（前設計の第1章）。
- 承認・state lock・シークレットの扱いは[guardrails.md](docs/guardrails.md)に従う。

## 2. 目標

1. 関数群をまたぐ同じ契約（応答の形式、Identity ID、伏せ字、テーブルのキーの属性名、保存パス、DynamoDBの値の変換）を1か所で定義する。
2. APIを1つ追加するときに触るファイルと箇所を減らす。
3. Terraformが規約の「複数のリソースは`for_each`で作る」「同じ値は`locals`から導出する」に従い、AIが真似てよい形になる。
4. 変更の前後で外部の挙動が同じことを、AWSに接続せずに確かめられる。

## 3. 現状と課題

### 3.1 Lambda

| 項目 | 現状 |
|---|---|
| 応答 | `response.py`が4つの関数群に同じ内容である。違いは`push_notification`だけが本文なし（204）を空文字にすること。`success`の`default`引数を渡す呼び出しはない |
| 認証 | 各関数群の`auth.py`は`common.auth.IdentityId`を再エクスポートするだけである。handlerは再エクスポートから、`db.py`と`models.py`は`common.auth`から直接importしており、同じ値オブジェクトのimportが2通りある。`tests/test_auth.py`も、import行を除いて4つとも同じである |
| 伏せ字 | `MASK`と`FULLY_MASKED_MAX_LENGTH`が`common/auth.py`にあり、`common/device_token.py`と`media_uploads/models.py`が認証のモジュールから伏せ字の定数をimportしている。伏せ字の形式は2つある。Identity IDは先頭4文字と末尾4文字を残し（`mask_identity`）、デバイストークンは末尾4文字だけを残す（`DeviceToken.__str__`）。`get_identity_id`と`mask_identity`は`IdentityId`の中でしか使われない |
| テーブルと保存パスの契約 | デバイストークンのテーブルのキー名が`device_tokens`、`push_notification`、`users`の`constants.py`に、アップロード記録のテーブルのキー名が`media_uploads`と`users`にある。保存パスのプレフィックス`private/`は`media_uploads`と`users`にある |
| DynamoDBの値 | `device_tokens`と`media_uploads`は`TypeSerializer`を使い、`push_notification`と`users`は`{"S": ...}`を直接書き、`push_notification`は読み出しも`.get("S")`で行う。`serialize_item`が2つの`db.py`で別々に定義され、引数の型も`dict`と`Mapping`で異なる。`deserialize_item`は`media_uploads`にだけある |
| `users` | `delete_user.py`の185行に、handler、S3の削除、DynamoDBの削除が同居する。他の関数群はAWSの呼び出しを`db.py`に分けている。型スタブの参照にここだけ`from __future__ import annotations`を使う |
| 入力の解釈 | `delete_upload_record`はパスパラメータの解釈をhandlerのモジュールで行い、他のhandlerのように`models.py`の`parse`を使わない。`get_upload_records`は、handlerと`GetUploadRecordsRequest.parse`の両方で`queryStringParameters`のnullを扱う |
| テストの配置 | `common/device_token.py`の単体テスト（`TestDeviceToken`）が`device_tokens/tests/test_models.py`に置かれている。`common/request.py`（`parse_body`）の単体テストは独立したファイルがない |
| scripts | `build_lambda.py`と`verify_lambda_packages.py`が、`handler`を定義するモジュールの判定を別々に実装している |

### 3.2 Terraform

| 項目 | 現状 |
|---|---|
| Lambda | `media_api/lambda.tf`の7つの`aws_lambda_function`は、名前、handler、ZIP、環境変数、timeout、layer、コード署名のほかは同じである。`runtime`が7回書かれている |
| IAM | 7つのロールと7つのログ用ポリシーは、関数名のほかは同じである。出力の`lambda_role_arns`と`lambda_role_names`は7つを手で並べているが、どこからも参照されていない |
| 出力の順序 | 出力の`api_execution_arns`は7つを手で並べ、`identity_pool`の認証済みロールのポリシーの`Resource`にそのまま入る。並び順は`api_routes`の順と異なる（`post_uploads_complete`が6番目）ため、順序を変えるとポリシーのJSONが変わる |
| API Gateway | 業務の7ルートごとにmethod、integration、permissionを、CORSの5つのパスごとにmethod、integration、method response、integration responseを個別に書いている（`api_gateway.tf`の642行）。更新判定の入力の一覧も手で並べ、漏れを`scripts/check_api_deployment_inputs.py`で検出している |
| 規約との矛盾 | 規約は「複数のリソースは安定したキーを持つ`for_each`で作る」とするが、`media_api`はそうなっていない。AIが周辺のコードを手本にすると、規約と逆の書き方を真似る |
| APIの追加 | 1つ足すと、`api_routes`、method、integration、permission、Lambda、ロール、データ用とログ用のポリシー、ロググループのキー、更新判定の一覧2つ、出力の一覧3つ（`api_execution_arns`、`lambda_role_arns`、`lambda_role_names`）、`bootstrap`のPassRoleの一覧2つを触る。`bootstrap`の一覧を忘れると、CDのapplyがPassRoleで失敗する |
| ルートモジュール | `envs/*/main.tf`で、`env`と`project_name`が各モジュールの呼び出しに繰り返される |
| `bootstrap` | `oidc_roles.tf`の889行のうち、devとprodのplan・applyロールの定義（約390行ずつ）は、環境名、OIDCの`sub`条件、stateのキーのパス（`dev/`と`prod/`）のほかは同じである。Sid、アクション、リソースの構成は一致する。ARNの`locals`も`_dev`と`_prod`の組で並ぶ。日本語のコメントが3か所あり、うち2か所はCognitoのPassRoleに`Condition`を付けない理由の説明である |

## 4. 方針

- 共通化は「同じ契約」を対象にし、「同じ形のコード」というだけでは共通化しない。前設計の第6.2節の方針を維持する。
  - 共有する: 応答の形式、Identity ID、伏せ字の定数、テーブルのキーの属性名、保存パスのプレフィックス、DynamoDBの値の変換
  - 関数群に残す: クライアントとテーブル名のキャッシュ、DBの操作（`delete_device_token`のように同じ操作が2つの関数群にあっても、キャッシュとIAMの境界が関数ごとのため残す）、各モジュールのテスト用fixture（`tests/conftest.py`）
- handlerの骨格（認証、本文、`parse`、処理の呼び出し、応答）は、デコレータやフレームワークで隠さない。handlerを上から読めば挙動が分かる形を保つ。
- Terraformの繰り返しは、`locals`の定義表と`for_each`へ寄せる。Lambdaごとのデータアクセスのポリシーは、権限の境界をレビューしやすいように、関数ごとの個別のリソースに残す。
- 前設計の第7.2節の「`for_each`化は導入しない」を、本設計で改める。理由は、規約との矛盾、APIの追加で触る箇所の多さ、更新判定の漏れを外部のスクリプトで補っている構造の3つである。アドレスの変更は`moved`ブロックで行う。
- 1つの段階では構造だけを変え、挙動の変更を混ぜない。

## 5. Lambdaの設計

### 5.1 `common`の構成

| モジュール | 持つもの | 移す元 |
|---|---|---|
| `common/response.py` | `success(status, body=None)`と`error(status, message)`。`body`がNoneなら本文は空文字。JSONにできない値は`str`で文字列にする（現行の`default=str`） | 4つの`response.py` |
| `common/auth.py` | `IdentityId`（`from_event`） | 現行。`get_identity_id`と`mask_identity`は`IdentityId`の非公開の処理にする |
| `common/masking.py` | `MASK`、`FULLY_MASKED_MAX_LENGTH` | `common/auth.py`の定数 |
| `common/device_token.py` | `DeviceToken` | 現行。伏せ字の定数は`masking`を使う |
| `common/tables.py` | 2つのテーブルのキーの属性名（`FIELD_USER_ID`、`FIELD_MEDIA_ID`、`FIELD_DEVICE_TOKEN`） | 各`constants.py` |
| `common/storage.py` | 保存パスのプレフィックス`PRIVATE_PATH_PREFIX`（`"private/"`） | `media_uploads/constants.py`、`users/constants.py` |
| `common/dynamodb.py` | `serialize_item`、`deserialize_item`（Decimalの変換を含む） | `device_tokens/db.py`、`media_uploads/db.py` |
| `common/request.py`、`common/errors.py` | 現行どおり | |

- 伏せ字の形式は現行の2つを保つ。Identity IDは先頭4文字と末尾4文字を、デバイストークンは末尾4文字を残し、8文字以下はどちらも全体を伏せる。文字数を引数に取る汎用関数にはせず、スライス`value[-0:]`のような誤用を防ぐ。ログに出る文字列は変わらない。
- キーの組み立て（各`db.py`の`_key`）とクエリの`ExpressionAttributeValues`は関数群に残し、`device_tokens`・`media_uploads`に加えて`push_notification/db.py`と`users/db.py`でも`common.dynamodb.serialize_item`と`common.tables`の属性名を使う形に揃える。`push_notification/db.py`の読み出しも`common.dynamodb.deserialize_item`を使う。ただし`users/db.py`の`_batch_delete_items`は、`query`が返したAttributeValue形式の要素をそのまま`DeleteRequest`の`Key`に渡しているため、`serialize_item`は使わない。`common`が`media_uploads.models.MediaId`などの関数群のモジュールをimportすると、ビルドスクリプトがimportをたどって`media_uploads`をすべてのZIPに入れ、`common`と関数群の依存の向きも逆になるため、`common`のモジュールは`common`の中だけをimportする。
- 保存パスのプレフィックス`PRIVATE_PATH_PREFIX`（`"private/"`）は`common/storage.py`に置く。認証の値オブジェクトである`IdentityId`にはS3のパス規則や生の値を含む文字列を返すメソッドを持たせず、S3操作やパスの検証を行う直前（`CloudStoragePath.belongs_to`と`users/storage.py`）で`f"{PRIVATE_PATH_PREFIX}{identity_id.value}/"`を組み立てる。
- 各関数群の`auth.py`と`response.py`は削除する。`IdentityId`のimportは、handler、`db.py`、`models.py`、テストのすべてで`cloud_photos.common.auth`からに揃える。
- `common/response.py`の`success`は、`body`がNoneのときに空文字を返す。現行の`push_notification`以外の関数群の`success`は、Noneを受けると`"null"`を返すが、Noneを渡す呼び出しはないため応答は変わらない。
- 関数群の`constants.py`には、その関数群だけが使う名前（リクエストJSONやパスパラメータの項目名、ページングの上限など）を残し、リクエスト解析の`models.py`がテーブル定義の`common.tables`に依存しないようにする。
- 時刻の取得（`int(time.time() * 1000)`）はPythonの標準的な書き方であり、時刻を使わない関数のZIPに不要なモジュールを増やさないため、現行どおり各モジュールに置く。
- ZIPに入る共有パッケージは、ビルドスクリプトがimportをたどって決めるため、Terraformの`handler`は変わらない。`common`はすでに4つのZIPすべてに入っており、新しい`common`のモジュールもすべてのZIPに入る。ZIPの中身は変わるので、適用時には7つのLambdaのコードが更新される。

### 5.2 `users`の分割

- `users/storage.py`: S3のバージョンと削除マーカーの削除、`get_s3_client`
- `users/db.py`: DynamoDBの削除（ページング、25件ごとの書き込み、`UnprocessedItems`の再試行）、`get_dynamodb_client`
- `users/delete_user.py`: handler、保存先の一覧、保存先ごとに記録して続ける`_try_delete`
- 削除しきれない場合の例外は現行どおり`RuntimeError`を維持する。`_try_delete`が`except Exception`で捕捉して`logger.exception`を呼ぶため、専用例外に変えるとログ末尾の例外クラス名が変わることを避ける。
- `_write_with_retries`が`users/db.py`へ移るため、再試行時の警告ログ（`UnprocessedItems in ...`）のロガー名は`cloud_photos.users.delete_user`から`cloud_photos.users.db`に変わる。ログのメッセージ本文は変わらない。
- 型スタブの型は、他のモジュールと同じく`TYPE_CHECKING`の中でimportし、文字列の注釈で参照する（`-> "S3Client"`、`Sequence["WriteRequestTypeDef"]`など）。`from __future__ import annotations`は使わない。
- `storage.py`と`db.py`の削除の関数は、handlerから呼ぶため公開の名前にする。
- テストは、パッチの対象とimport元だけを変え、期待値は変えない。変わる対象は次のとおりである。
  - `delete_user`の`_delete_s3_objects`と`_delete_dynamodb_records`へのパッチ（18か所）は、handlerがimportした公開の名前へのパッチになる。
  - `users/tests/test_delete_user.py`で内部関数を直接呼んでいる10か所（`TestBatchDeleteItems`の3か所、`TestFlushS3Batch`の2か所、`TestDeleteS3Objects`の1か所、`TestDeleteDynamodbRecords`の1か所、`TestObjectIdentifier`の3か所）は、`storage`と`db`の関数への呼び出しに変える。
  - `get_s3_client`は`storage`へ、`get_dynamodb_client`は`db`へ移り、`users/tests/conftest.py`のキャッシュのクリアもそれに合わせる。
  - 再試行の待ち時間を消す`delete_user.time`へのパッチは、`users.db.time`へのパッチにする。`db.py`は`import time`と`time.sleep`の形を保つ。
  - 失敗を記録するログの文言は`_try_delete`が出すため、`_try_delete`を`delete_user.py`に残すことで、ログを確かめるテストは変わらない。

### 5.3 入力の解釈

- `delete_upload_record`: パスパラメータの解釈を`models.py`の`DeleteUploadRecordRequest.parse`へ移す。移す前に、既存のテストが覆っていない現行の挙動を固定するテストを足す。
  - 現行は、`pathParameters`がオブジェクトでない場合と、`mediaId`が文字列でないか空文字の場合に400の`Missing mediaId`を返し、それ以外は前後の空白を除かずに`MediaId`を作る。空白だけの値や`" abc "`は、そのままキーになり、該当がなければ404になる。
  - `MediaId.parse`は前後の空白を除き、空白だけの値を別のメッセージの400にする。`" abc "`が`abc`のレコードを削除し得るため、使わない。`DeleteUploadRecordRequest.parse`は、`pathParameters`が`Mapping`でない場合や`mediaId`が空でない`str`でない場合に`ValidationError("Missing mediaId")`を送出し、`str`に絞り込んだ値を空白除去せずに`MediaId(raw)`へ渡す。
  - 先に足すテスト: 空白だけの`mediaId`と、前後に空白がある`mediaId`。
- `get_upload_records`: `queryStringParameters`の扱いを`GetUploadRecordsRequest.parse`の1か所にする。
  - `get_upload_records.py`の`or {}`を外し、`event.get("queryStringParameters")`を直接`GetUploadRecordsRequest.parse`に渡す。`parse`は現行どおり`None`と`Mapping`だけを受け付け、それ以外の型は`ValidationError("params must be a dict")`として400にする（`test_models.py`の既存の型検証テストを維持する）。
  - API Gatewayが渡す`queryStringParameters`は`None`かオブジェクト（`dict`）のみであり、既存のhandlerテストも`None`と`{}`のみのため、実際のAPI応答は変わらない。

### 5.4 テスト

- `common/tests/`を作り、次を置く。
  - `test_auth.py`: 4つの関数群の`test_auth.py`（16件ずつ）を1つにする。
  - `test_response.py`: `media_uploads`から移し、204の空文字を加える。
  - `test_dynamodb.py`: `media_uploads/tests/test_db.py`のうち、`serialize_item`、`deserialize_item`、Decimalの変換のテストを移す。
  - `test_device_token.py`: `device_tokens/tests/test_models.py`にある`TestDeviceToken`（8件）を移す。
  - `test_request.py`: `common/request.py`（`parse_body`）の単体テストを置く。
- テーブルやバケットを作るmotoのfixture（`dynamodb_table`、`aws_resources`）は、前設計の第6.4節の方針どおり各関数群の`tests/conftest.py`に残す。単一テーブルの3関数群と、S3バケットと2つのテーブルをまとめて作り異なるクライアントキャッシュをクリアする`users`ではライフサイクルが異なるため、無理に1つのfixtureにまとめない。
- 段階1の前の件数は331件（`device_tokens`が58、`media_uploads`が170、`push_notification`が59、`users`が44）。`test_auth.py`を1つにすると48件減り、`test_request.py`の追加分だけ増える。各段階で、件数の増減が統合・追加したテストの分だけであることを記録する。

### 5.5 scripts

`handler`を定義するかの判定を`build_lambda.py`の1つの関数にまとめる。この関数は、ファイルとZIPのどちらから読んだ内容も扱えるように、ソース（`str`または`bytes`）とファイル名を受け取る。`verify_lambda_packages.py`はすでに`build_lambda`からimportしており、ZIPから読んだ内容でこの関数を使う。

## 6. Terraformの設計

### 6.1 Lambda関数とIAM（`media_api`）

`local.lambda_functions`を、ロググループのキーだけの表から、関数の定義表に広げる。

```hcl
locals {
  lambda_runtime = "python3.12"

  lambda_functions = {
    get_upload_records = {
      name                    = "get-upload-records"
      handler                 = "cloud_photos.media_uploads.get_upload_records.handler"
      package                 = "media_uploads"
      timeout                 = var.lambda_timeout
      layers                  = null
      code_signing_config_arn = null
      environment             = tomap({ TABLE_NAME = var.dynamodb_table_name })
    }
    notify_upload_complete = {
      name    = "notify-upload-complete"
      handler = "cloud_photos.push_notification.notify_upload_complete.handler"
      package = "push_notification"
      timeout = 30
      layers  = [var.firebase_layer_arn]
      # ...
    }
  }
}
```

| リソース | 変更後 | 変更前 |
|---|---|---|
| Lambda関数 | `aws_lambda_function.api[<key>]` | 7つの個別のリソース |
| ロール | `aws_iam_role.lambda[<key>]` | 7つの個別のリソース |
| ログ用のポリシー | `aws_iam_role_policy.logs[<key>]` | 7つの`<key>_logs` |
| ロググループ | 現行の`aws_cloudwatch_log_group.lambda[<key>]`。`name`の`each.value`を`each.value.name`にする | アドレスは変わらない |
| データアクセスのポリシー | 現行の9つの個別のリソース。`role`の参照だけを`aws_iam_role.lambda["<key>"].id`にする | アドレスは変わらない |
| コード署名の設定 | 現行の`aws_lambda_code_signing_config.delete_user` | 変更なし |

- 表の要素は、すべて同じ属性を持たせる（レイヤーを持たない関数は`layers = null`、コード署名を持たない関数は`code_signing_config_arn = null`）。現行の6関数は`layers`を省略して値が`null`になっており、`layers = []`にすると設定値が空配列に変わるため`null`にする。`environment`は`tomap({...})`で渡す。
- `depends_on`には`each.key`を使えない。関数ごとのロググループを指す現行の`depends_on`は、`depends_on = [aws_cloudwatch_log_group.lambda]`（ロググループ全体）にする。関数はロググループの作成後に作られるという現行の順序は保たれる。
- 出力の`lambda_role_arns`と`lambda_role_names`は、7つのロールを手で並べており、かつ参照する箇所がないため削除する。子モジュールの出力でありルートモジュールのstate出力ではないため、stateには影響しない。
- `moved`ブロックは21個（関数、ロール、ログ用のポリシーが7つずつ）になる。キーは現行のリソース名にする。
- IAMポリシーの文を1つにまとめるなど、ポリシーの内容は変えない。

### 6.2 API Gateway（`media_api`）

ルートとCORSの定義表を置き、method、integration、permission、CORSのリソースを`for_each`で作る。

```hcl
locals {
  cors_allow_headers = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"

  api_routes = {
    get_uploads = { method = "GET", path = "media/uploads", resource = "uploads", function = "get_upload_records" }
    # ...
  }

  cors_preflights = {
    options_uploads = { resource = "uploads", allow_methods = "GET,POST,OPTIONS" }
    # ...
  }

  api_resource_ids = {
    uploads = aws_api_gateway_resource.uploads.id
    # ...
  }
}
```

| リソース | 変更後 |
|---|---|
| 業務のmethod、integration | `aws_api_gateway_method.route[<key>]`、`aws_api_gateway_integration.route[<key>]` |
| Lambdaのpermission | `aws_lambda_permission.route[<key>]` |
| CORSの4種類 | `aws_api_gateway_method.cors_preflight[<key>]`など、4種類とも`cors_preflight[<key>]` |
| パス（`aws_api_gateway_resource`） | 木構造のため個別のまま |
| Gateway Response、deployment、stage | 個別のまま（`default_4xx`と`default_5xx`のCORS Allow-Headersは`local.cors_allow_headers`を共有する） |

- キーは現行のリソース名（`get_uploads`、`options_uploads`など）にする。`moved`ブロックは41個（ルートが7つずつ3種類、CORSが5つずつ4種類）になる。
- 更新判定の入力に使う5つの`local`（`api_methods`、`api_integrations`、`api_method_responses`、`api_integration_responses`、`api_gateway_responses`）は残し、methodとintegrationは`merge(aws_api_gateway_method.route, aws_api_gateway_method.cors_preflight)`のように`for_each`のリソース全体から作る。method responseとintegration responseはCORSだけにあるため、`cors_preflight`をそのまま使う。ルートやCORSを表に足せば、更新判定にも自動で入る。
- `merge`はキーが重なると片方を黙って上書きする。`api_routes`と`cors_preflights`のキーが重ならないことを、`aws_api_gateway_deployment.media`の`lifecycle.precondition`（または`check`ブロック）と`scripts/check_api_deployment_inputs.py`で確かめる。
- `local.api_routes`に足す`resource`と`function`は、リソースの参照を選ぶためだけに使い、更新判定の入力には入れない。
- `jsonencode`はキーを並べ替えて出力し、`moved`の後もAPI Gatewayのidは変わらない。キーと属性の値が現行と同じため、`triggers.redeployment`の値は変わらない。変わらなければ、deploymentは置き換えられない。確かめ方は第7.2節に記す。
- 出力の`api_execution_arns`は、現行の順序を明示した一覧で作る。`for`式や`values`で導出するとキーの辞書順になり、`identity_pool`の認証済みロールのポリシーのJSONが変わるためである。
- `scripts/check_api_deployment_inputs.py`は、現行の正規表現が個別のリソース名と`<key> = aws_api_gateway_<type>.<name>`の形を前提にしているため、書き直す。確かめる内容は「種類ごとに宣言されたresourceが、更新判定の入力に含まれる」のまま変えない。`for_each`のリソースはインデックス指定`[...]`を伴わないマップ全体の参照であること、個別のリソース（`gateway_response`、`rest_api`、`resource`）は`<key> = aws_api_gateway_<type>.<name>`でキーとリソース名が一致すること、および`api_routes`と`cors_preflights`のキーが重ならないことを検査する。

変更後にAPIを1つ追加するときに触るのは、`api_routes`の1行、出力の`api_execution_arns`の1行、`lambda_functions`の1要素、データアクセスのポリシー1つ、新しいパスの場合の`aws_api_gateway_resource`と`cors_preflights`の1要素、`bootstrap`のロール名の一覧（第6.4節）になる。

### 6.3 ルートモジュール

`envs/<env>/main.tf`に`env`と`project_name`の`locals`を置き、`default_tags`と各モジュールの呼び出しから参照する。値とアドレスは変わらない。環境ごとに異なる値（削除保護、保持期間など）は、現行どおり呼び出しに直接書き、差が見える形を保つ。

### 6.4 `bootstrap`（承認が必要）

- plan・applyのロールとポリシーを、環境をキーにした`for_each`にする。ロール名（`gh-terraform-plan-dev`など）は変えない。

  ```hcl
  locals {
    account_id = data.aws_caller_identity.current.account_id
    region     = data.aws_region.current.id

    environments = {
      dev = {
        plan_subjects = ["pull_request", "ref:refs/heads/develop", "ref:refs/heads/main"]
        apply_subject = "environment:development"
      }
      prod = {
        plan_subjects = ["pull_request", "ref:refs/heads/main"]
        apply_subject = "environment:production"
      }
    }
  }
  ```

| リソース | 変更後 | 変更前 |
|---|---|---|
| planロール | `aws_iam_role.plan[<env>]` | `aws_iam_role.plan_dev`、`aws_iam_role.plan_prod` |
| applyロール | `aws_iam_role.apply[<env>]` | `aws_iam_role.apply_dev`、`aws_iam_role.apply_prod` |
| planポリシー | `aws_iam_role_policy.plan[<env>]` | `aws_iam_role_policy.plan_dev`、`aws_iam_role_policy.plan_prod` |
| applyポリシー | `aws_iam_role_policy.apply[<env>]` | `aws_iam_role_policy.apply_dev`、`aws_iam_role_policy.apply_prod` |

- `assume_role_policy`の`Condition`は、planロールが`StringEquals`（`aud`のみ）と`StringLike`（`sub`のリスト）を使うのに対し、applyロールは`StringEquals`の中に`aud`と単一文字列の`sub`を置く構造になっている。信頼ポリシーのJSONを変えないため、planロールとapplyロールでそれぞれの`Condition`構造をそのまま維持する。
- `data.aws_caller_identity.current.account_id`と`data.aws_region.current.id`を`locals`に置き、`_dev`と`_prod`の組で並ぶARNの`locals`とstateのキーのパス（`dev/`、`prod/`）を環境から導出する。
- PassRoleの対象のロール名を、ハイフン区切りの関数名の一覧1つから導出する。一覧の順序は現行のとおりにする。ロールのARNはポリシーの`Resource`に並んで入るため、並び替えるとポリシーのJSONが変わる。
- `bootstrap`と`media_api`は別のルートモジュールで、互いの値を参照できない。そのため、`bootstrap`の関数名の一覧（ハイフン区切り）と`media_api`の`lambda_functions`の各要素の`name`属性が一致することを、両方の`.tf`を読む小さなスクリプトで確かめ、CIで実行する。`check_api_deployment_inputs.py`と同じくAWSを使わない。
- `moved`ブロックは8個（plan・applyのロールが2環境ずつで4つ、そのポリシーが4つ）になる。ポリシーのJSONは変えない。
- `oidc_roles.tf`の日本語のコメントのうち、意味のない1か所（`locals`の説明）を削除する。CognitoのPassRoleに`Condition`を付けない理由の2か所は、外部の都合による理由のため残し、規約に合わせて英語にする。`for_each`化で1か所にまとまる。

guardrailsの「Bootstrap」の記載事項は次のとおりとする。

| 項目 | 内容 |
|---|---|
| 必要な理由 | devとprodの権限の重複を解消し、片方だけを直してずれることを防ぐ。PassRoleの一覧と`media_api`の関数のずれを検出する |
| 影響するロール | `gh-terraform-plan-dev`、`gh-terraform-apply-dev`、`gh-terraform-plan-prod`、`gh-terraform-apply-prod`と、それぞれのポリシー。アドレスが移るだけで、内容は変わらない |
| 手動の適用 | 管理者が`bootstrap/`でplanし、`moved`のほかに差分がないことを確かめてからapplyする |
| 適用しない場合 | コードとstateのアドレスがずれたままになる。ロールの権限とCI/CDの動作は変わらない |

## 7. 検証の設計

### 7.1 Lambda

- handlerのテストを期待値を変えずに実行し、`lambda/`での一括実行が成功すること。
- 第8.4節（前設計）のruffの中間のルール、`ruff format --check`、Pyright（`standard`）が指摘なしであること。
- ZIPを2回ビルドしてハッシュが一致し、`verify_lambda_packages.py`で7つのhandlerを読み込めること。
- ZIPに入るファイルの一覧の差分が、段階1では関数群の`auth.py`・`response.py`の削除と`common`のモジュールの追加だけであること、段階2では`users`の`storage.py`・`db.py`の追加だけであること。ファイルの中身はimportなどで変わるため、中身が同じことは、handlerのテストが期待値を変えずに成功することで確かめる。

### 7.2 Terraform

- `terraform fmt -check -recursive`、tflint、`envs/dev`・`envs/prod`・`bootstrap`の`terraform validate`。`scripts/`のPythonスクリプトを変更・追加する段階（段階3、段階5）では、`ruff check scripts`、`ruff format --check scripts`、Pyright（`standard`）も実行する。
- 変更前後の同値の確認を、AWSに接続せずに次の方法で行う。確認の一時的なルートモジュール、テスト、スクリプトはリポジトリの外に置き、結果だけをPRに記録する。

| 確認 | 方法 | 確かめること |
|---|---|---|
| 設定値と更新判定の比較（`media_api`） | 空のstateのplanでは`invoke_arn`、リソースの`id`、ロググループの`arn`、`execution_arn`などが`(known after apply)`になり、integrationの`uri`や`resource_id`、ログ用ポリシーのJSON、出力の`api_execution_arns`の順序、deploymentの`triggers`を比較できない。そのため、`terraform test`の`mock_provider "aws"`を`command = apply`で実行し、`override_resource`（または`mock_resource`）でAPI Gatewayの各リソースの`id`、REST APIの`execution_arn`、各Lambda関数の`invoke_arn`、各IAMロールの`id`・`arn`、各ロググループの`arn`にリソースごとに識別できる固定値を与える。`filebase64sha256`のため、`.build/`に4つのZIPを置く。適用後の値と一時的な出力に取り出した`sha1(jsonencode(local.api_deployment_inputs))`を、変更前後で比べる（アドレスは`moved`の対応で読み替える） | 7つのLambda関数の属性（handler、環境変数、timeout、layers、コード署名、role）、7つのロールと16個のポリシーのJSON・role、業務7ルートとCORS5パスの属性（`resource_id`、`authorization`、`uri`の参照先、CORS応答ヘッダー）、permissionの`function_name`と`source_arn`、出力の`api_execution_arns`の順序、deploymentの`triggers.redeployment`のハッシュ値が変わらないこと |
| `moved`の対応 | 変更前のコミットのresourceのアドレスの一覧と、`moved`の`from`、`for_each`のキーを突き合わせる | 変更前のアドレスがすべて`moved`で新しいアドレスに対応し、数が21、41、8であること。空のstateでは`moved`を確かめられないため |

- `envs/*`は、`identity_pool`と`media_storage`のdata sourceがAWSを呼ぶためそのままではplanできず、また`terraform test`の`assert`式からは子モジュールの`output`しか参照できないため、出力を持たない子モジュール（`cognito`、`identity_pool`、`push_notification`、`media_api`）へ渡した値や`default_tags`を`assert`では確かめられない。そのため第6.3節の確認は、`terraform validate`に加えて、一時ディレクトリに`envs/*`をコピーしてダミーのprovider設定と`aws_lambda_layer_version`等のダミー置換を置いたうえで`terraform plan -out=tfplan`と`terraform show -json tfplan`を実行し、`planned_values.root_module.child_modules`内の全リソースの属性と`tags_all`（`default_tags`）が変更前後で完全一致することを確かめる。
- `bootstrap`は、`terraform test`の`mock_provider`で、`aws_s3_bucket.terraform_state`、`aws_kms_key.terraform_state`、`aws_iam_openid_connect_provider.github`のARNを`mock_resource`（または`override_resource`）で、`aws_caller_identity`と`aws_region`を`override_data`で固定し、`command = apply`で実行する。`command = plan`ではARNが未確定でポリシーのJSONを読めない。変更前のコミットで同じテストを実行して4つのロールの`name`・`assume_role_policy`と4つのロールポリシーの`name`・`policy`のJSONを書き出し、変更後の値と一致することを確かめる。このテストを、ポリシーの変更を検出する回帰テストとして残すかは段階5で決める。
- planを実行できる場合は、`moved`のほかにcreate・update・destroyがないこと、deploymentが置き換えられないことを確かめる。これが同値の最終的な確認になる。実行できない場合は`Not executed`とし、上のAWS不要の確認の結果と区別して報告する。

## 8. 文書とSkillの更新

各段階で、変えた構成を記述する文書とSkillを同じ差分で更新する。`.claude/skills/`と`.agents/skills/`は同じ変更を行う。

| 段階 | 主な対象 |
|---|---|
| 1、2 | 下の表のとおり（段階1と段階2で該当箇所を分けて更新する） |
| 3 | [infrastructure.md](docs/infrastructure.md)、[lambda.md](docs/lambda.md)の配布の説明、Lambda Skillの`function-layout.md`（新規関数を追加するときのTerraform手順）、Infra Skillの`media-api-wiring.md`（APIの追加の手順、および`main.tf`から削除済みの`data`の記述の修正）、レビューSkillの`review-checklist.md`。`check_api_deployment_inputs.py`を書き直すため、その説明がある[commands.md](docs/commands.md)、[verification_policy.md](docs/verification_policy.md)、[README.md](README.md)、[README.en.md](README.en.md)も確かめる |
| 4 | Infra Skillの`env-matrix.md`（`envs/*`から各モジュールへ渡す`env`と`project_name`の記述） |
| 5 | Infra Skillの`media-api-wiring.md`（PassRoleの一覧と検証コマンド）、[README.md](README.md)と[README.en.md](README.en.md)の`bootstrap`・基本検証・CIの説明、関数名の一覧を確かめるスクリプトのCIのstepと[commands.md](docs/commands.md)、[verification_policy.md](docs/verification_policy.md)、レビューSkillの`review-checklist.md` |

段階1、2で更新する箇所は次のとおりである。Skillの資料は特に記載がない限りLambda Skillのものである。

| 対象 | 段階1で更新する内容 | 段階2で更新する内容 |
|---|---|---|
| [lambda.md](docs/lambda.md) | 関数群の中で`auth.py`と`response.py`を共有するという記述、Layoutの図（`common`のモジュールと`common/tests/`）、Authenticationの`auth.py`の再エクスポート、API Response Contractの`response.py` | Layoutの図（`users`の`storage.py`と`db.py`） |
| [coding_standards.md](docs/coding_standards.md) | 原則の表の`mask_identity`、API Behaviorの`auth.py`と`response.py` | なし |
| [testing.md](docs/testing.md) | `common/tests/`の追加 | `users`のテスト対象モジュールの記述 |
| `SKILL.md` | `constants.py`と`mask_identity`の記述 | なし |
| `function-layout.md` | `auth.py`の扱いと`response.py`の差の節、「新規なら`auth.py` / `response.py` / `constants.py` / `tests/`を揃える」の記述、ZIPに`common`が入る関数群から`users`が漏れている既存の誤り | `users`のファイル一覧、「`db.py`を持たない」という記述 |
| `identity-boundaries.md` | `get_identity_id`と`mask_identity`の記述、再エクスポート | 実装箇所の表と`delete_user.py`での保存パスの組み立て（`users/storage.py`への変更） |
| `handler-patterns.md` | `mask_identity`の記述 | なし |
| `dynamodb-access-patterns.md` | キーの組み立て、`serialize_item`の置き場所、テーブルのキー属性名の置き場所 | `users/delete_user.py`の記述（`users/db.py`への変更） |
| `pytest-fixtures.md` | なし | `delete_user`のクライアントキャッシュのクリア先（`storage.get_s3_client`、`db.get_dynamodb_client`） |
| レビューSkillの`review-checklist.md` | `mask_identity`、`auth.py / response.py / db.py`、テーブルのキー属性名の置き場所を`constants.py`とする記述 | なし |

前設計の第7.2節の判断を改めたことは本設計に記録し、前設計は書き換えない。

## 9. 段階とブランチ

ブランチは前設計の第10.2節の運用に従い、名前は`feature/impl-refactor-<段階の番号>-<内容>`とする。

| 段階 | ブランチ | 内容 | 前提 |
|---|---|---|---|
| 0 | `feature/implementation-refactoring` | 本設計書 | なし |
| 1 | `feature/impl-refactor-1-lambda-common` | 第5.1節、第5.4節、第5.5節 | 段階0 |
| 2 | `feature/impl-refactor-2-lambda-groups` | 第5.2節、第5.3節 | 段階1 |
| 3 | `feature/impl-refactor-3-media-api` | 第6.1節、第6.2節 | 段階0。段階1・2と並行してよい |
| 4 | `feature/impl-refactor-4-root-modules` | 第6.3節 | 段階0。他と並行してよい |
| 5 | `feature/impl-refactor-5-bootstrap` | 第6.4節。実装前に承認を得て、マージ後に管理者が手動で適用する | 段階3 |

段階3は、Lambda関数・IAMとAPI Gatewayの差分が大きい場合に、末尾に対象を足してPRを分けてよい（例: `feature/impl-refactor-3-media-api-lambda`と`feature/impl-refactor-3-media-api-apigw`）。ただし`api_gateway.tf`が`aws_lambda_function`を参照しているため、分ける場合は第6.1節（`moved` 21個）を先にマージし、続けて第6.2節（`moved` 41個を追加し計62個）を直列で進める。

### 完了条件

| 段階 | 完了条件 |
|---|---|
| 1 | 第7.1節（段階1のZIP差分を含む）がすべて成功し、関数群の間で同じ契約の定義が`common`の1か所になり、段階1の文書とSkillの記述が新しい構成と一致する |
| 2 | 第7.1節（段階2のZIP差分を含む）がすべて成功し、`users`の分割と`media_uploads`の入力解釈の統一が完了し、段階2の文書とSkillの記述が新しい構成と一致する |
| 3 | 第7.2節の確認で、設定値と更新判定の入力が変わらず、変更前のアドレスがすべて`moved`（計62個）で対応し、`scripts/check_api_deployment_inputs.py`のruff・Pyrightと実行が成功する。実環境のplanは、実行できた場合に結果を、できなかった場合に`Not executed`を、別に報告する |
| 4 | 第7.2節の`envs/*`の確認（`terraform validate`と一時コピーでのplanのJSON比較）で、全子モジュールのリソース属性と`default_tags`が変わらない |
| 5 | 第7.2節の`bootstrap`の確認で4つのロールの`name`・`assume_role_policy`と4つのロールポリシーの`name`・`policy`のJSONが変更前と一致し、変更前のアドレスがすべて`moved`（8個）で対応し、関数名の一覧の一致を確かめるスクリプトのruff・PyrightとCIでの実行が成功し、guardrailsの記載事項がPRに書かれている |

## 10. 行わないこと

- handlerの骨格を隠すデコレータやフレームワークの導入
- クライアントとテーブル名のキャッシュの共通化
- 未認証の401と403の統一（前設計の第4章のとおり互換性のため維持する）
- IAMポリシーの文の統合など、ポリシーの内容の変更
- `aws_api_gateway_resource`（パス）の`for_each`化、Lambdaの子モジュール化
- 新しい機能、OpenAPIによるAPIの定義への移行

## 11. 判断が必要な事項

| 事項 | 本設計の案 | 決める時期 |
|---|---|---|
| `bootstrap`を対象に含めるか | 含める。ただし承認と手動の適用が必要なため、最後の段階にする | 段階5の着手前 |
| `moved`ブロックをいつ削除するか | devとprodの両方へ適用したことを確かめた後の、別の変更で削除する | 段階3、5の適用後 |

前設計の第7.2節の判断（`for_each`化しない）を改め、`media_api`を`for_each`化することは、2026-11-04に決めた。理由は第4章に記す。
