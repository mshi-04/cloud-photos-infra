# media_api モジュールの配線

[modules/media_api/](../../../../modules/media_api/) は、Lambda の配布物、IAM、Lambda、API Gateway を
責務ごとのファイルに分けて持ちます。1 つのエンドポイントを足すのに複数のファイルを触るため、順序を固定します。

## ファイルの構成

| ファイル | 内容 |
|---|---|
| [main.tf](../../../../modules/media_api/main.tf) | `locals` の `function_prefix`、`lambda_runtime`、関数の定義表 `lambda_functions` |
| [archives.tf](../../../../modules/media_api/archives.tf) | `local.lambda_packages`（`scripts/build_lambda.py` が `.build/` に作る ZIP のパス） |
| [iam.tf](../../../../modules/media_api/iam.tf) | `locals` の `assume_role_policy`、`aws_iam_role.lambda` と `aws_iam_role_policy.logs`（`local.lambda_functions` を `for_each`）、関数ごとのデータアクセスの `aws_iam_role_policy`（dynamodb / s3 / secretsmanager） |
| [lambda.tf](../../../../modules/media_api/lambda.tf) | `aws_cloudwatch_log_group.lambda` と `aws_lambda_function.api`（`local.lambda_functions` を `for_each`）、`aws_lambda_code_signing_config` |
| [api_gateway.tf](../../../../modules/media_api/api_gateway.tf) | REST API、パスごとの resource、定義表 `api_routes` と `cors_preflights`、method / integration / `aws_lambda_permission`（`route[<key>]`）、CORS の 4 種類（`cors_preflight[<key>]`）、Gateway Response、deployment、stage |
| [variables.tf](../../../../modules/media_api/variables.tf) / [outputs.tf](../../../../modules/media_api/outputs.tf) | 入出力 |
| [moved.tf](../../../../modules/media_api/moved.tf) | `for_each` へ移したリソースの `moved` ブロック |

## エンドポイント追加の手順

1. `main.tf` の `local.lambda_functions` に要素を足す。Lambda 本体、ロール、ログ用のポリシー、log group は、この表から `for_each` で作られます。

   ```hcl
   <key> = {
     name                    = "<ハイフン区切り関数名>"
     handler                 = "cloud_photos.<function_group>.<module>.handler"
     package                 = "<function_group>"
     timeout                 = var.lambda_timeout
     layers                  = null
     code_signing_config_arn = null
     environment             = tomap({ TABLE_NAME = var.dynamodb_table_name })
   }
   ```

   要素はすべて同じ属性を持たせます。レイヤーやコード署名を持たない関数は `null` にします。`layers = []` にすると、設定値が空配列に変わります。新しい関数群なら、`archives.tf` の `local.lambda_packages` にも ZIP のパスを足します。
2. `iam.tf` にデータアクセスのポリシーを足す。権限の境界をレビューしやすいように、関数ごとの個別のリソースにします。`name` は `dynamodb-query` / `s3-delete` のように権限内容を表し、`role` は `aws_iam_role.lambda["<key>"].id` にします。
3. 以降は `api_gateway.tf` を変える。パスが新しければ `aws_api_gateway_resource` を足し、`local.api_resource_ids` にも足す。既存パスなら再利用する。
4. `local.api_routes` に 1 行足す。method、integration（`AWS_PROXY`）、`aws_lambda_permission` は、この表から `for_each` で作られます。`function` は `local.lambda_functions` の key、`resource` は `local.api_resource_ids` の key です。`source_arn` は `method` と `path` から導出され、メソッドとパスまで絞られます。

   ```hcl
   get_uploads = { method = "GET", path = "media/uploads", resource = "uploads", function = "get_upload_records" }
   ```

5. `outputs.tf` の `api_execution_arns` の末尾に `local.api_execution_arns.<key>` を足す。これが Identity Pool の `execute-api:Invoke` の範囲になるため、漏らすとクライアントから 403 になります。順序はロールのポリシーの JSON に入るため、既存の順序を変えません。
6. ブラウザからの利用を想定する新しいパスなら、`local.cors_preflights` に 1 行足す。`OPTIONS` の method、integration、`method_response`、`integration_response` が作られます。`local.api_routes` と同じ key は使えません。既存のパスにメソッドを足す場合は、行を足さず、そのパスの `allow_methods` を更新します。同じパスに `OPTIONS` を 2 つ定義すると、適用時に競合します。
7. API の動作に影響する属性を新しく設定する場合は、`local.api_deployment_inputs` にもその属性を加える。Gateway Response を足す場合は、`local.api_gateway_responses` にも足す。`aws_api_gateway_deployment.media` は、これらの id と設定（`authorization`、integration の `type`、`integration_http_method`、`uri`、`request_templates`）が変わると置き換えられ、ステージへ反映されます。`local.api_routes` と `local.cors_preflights` に足したものは自動で含まれます。`python scripts/check_api_deployment_inputs.py` で確かめます。

## 変数と環境差

`modules/` 内に `var.env` の分岐を書きません。差分は `envs/*/main.tf` から変数で渡します。
`media_api` の既定値は `lambda_memory_size = 256`、`lambda_timeout = 10` です。
`notify_upload_complete` と `delete_user` は `local.lambda_functions` で `timeout = 30` を直接指定しています。

`env` には `contains(["dev", "prod"], var.env)` の `validation` があります。
新しい環境を足すときはここも更新が必要です。

## 変更時の注意

- `local.lambda_functions`、`local.api_routes`、`local.cors_preflights` の key は state のアドレスになります。key を変えるときは `moved` ブロックで移します。関数の `name` の変更は
  Lambda 本体・log group・IAM ロール名を同時に動かすため、`terraform plan` の destroy / replace を必ず読みます。
- `aws_api_gateway_resource` の `path_part` 変更は下流の method / integration をすべて置換します。
- リソース名やモジュールパスを変えるだけの整理でも state の移行が必要になります。`moved` ブロックで移し、
  実装前にユーザーへ方針を示します。ファイルを分けるだけなら、リソースアドレスは変わりません。
- `moved.tf` のブロックは、dev と prod の両方へ適用したことを確かめた後の、別の変更で削除します。
- IAM 権限を広げる変更と `bootstrap/` の変更は、実装前に方針を提示します。

## 検証

```powershell
terraform fmt -recursive
tflint --recursive --config "$PWD/.tflint.hcl"
python scripts/check_api_deployment_inputs.py
```

```powershell
Set-Location envs/dev
terraform validate
terraform plan
```

`validate` / `plan` には、`python scripts/build_lambda.py --with-layers` で作る Lambda とレイヤーの ZIP と、backend の初期化が必要です。手順は
[README.md](../../../../README.md) のローカル開発を参照します。実行できない場合は
`Not executed` と理由を報告します。

## 参考資料

- [docs/infrastructure.md](../../../../docs/infrastructure.md)
- [docs/guardrails.md](../../../../docs/guardrails.md)
- [docs/verification_policy.md](../../../../docs/verification_policy.md)
