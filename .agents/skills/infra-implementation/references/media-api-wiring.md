# media_api モジュールの配線

[modules/media_api/main.tf](../../../../modules/media_api/main.tf) は Lambda、IAM、API Gateway を
1 ファイルで持ちます。1 つのエンドポイントを足すのに触る箇所が多いため、順序を固定します。

## 構成の並び

```text
data archive_file           Lambda ZIP（source_dir 一括 / locals の明示リスト）
locals assume_role_policy   Lambda 共通の信頼ポリシー
aws_iam_role                Lambda ごとに 1 つ
aws_iam_role_policy         用途ごとに分割（dynamodb / s3 / secretsmanager / logs）
aws_cloudwatch_log_group    local.lambda_functions を for_each
aws_lambda_function         Lambda ごと
aws_api_gateway_rest_api    1 つ
aws_api_gateway_resource    パスセグメントごと
method / integration / lambda_permission   エンドポイントごとに 3 点セット
options 系                  CORS プリフライト（method_response と integration_response も必要）
aws_api_gateway_deployment  triggers.redeployment に全 method / integration の id
aws_api_gateway_stage       stage_name = var.env
```

## エンドポイント追加の手順

1. `local.lambda_functions` に `<key> = "<ハイフン区切り関数名>"` を足す。
   log group の `for_each` がこのマップを参照します。
2. `aws_iam_role` を 1 つ作り、`assume_role_policy = local.assume_role_policy` を使う。
3. 用途ごとに `aws_iam_role_policy` を分ける。`name` は `dynamodb-query` / `s3-delete` /
   `cloudwatch-logs` のように権限内容を表す。logs は必ず自分の log group ARN に限定する。

   ```hcl
   Resource = "${aws_cloudwatch_log_group.lambda["<key>"].arn}:*"
   ```

4. `aws_lambda_function` を追加する。`runtime = "python3.12"`、`handler = "<file>.handler"`、
   `filename` と `source_code_hash` は `data.archive_file` から取り、
   `depends_on = [aws_cloudwatch_log_group.lambda["<key>"]]` を付ける。
5. パスが新しければ `aws_api_gateway_resource` を足す。既存パスなら再利用する。
6. `aws_api_gateway_method`（`authorization = "AWS_IAM"`）、
   `aws_api_gateway_integration`（`integration_http_method = "POST"`、`type = "AWS_PROXY"`）、
   `aws_lambda_permission` の 3 点セットを作る。
   `source_arn` はメソッドとパスまで絞る。

   ```hcl
   source_arn = "${aws_api_gateway_rest_api.media.execution_arn}/*/GET/media/uploads"
   ```

7. `outputs.tf` の `api_execution_arns` に同じ ARN を足す。これが Identity Pool の
   `execute-api:Invoke` の範囲になるため、漏らすとクライアントから 403 になります。
8. `aws_api_gateway_deployment.media` の `triggers.redeployment` に新しい method と integration の
   id を足す。漏らすとリソースは作られてもステージへ反映されません。
9. ブラウザからの利用を想定するパスなら `OPTIONS`（`authorization = "NONE"`）と
   `method_response` / `integration_response` を追加し、これらの id も `triggers` に足す。

## 変数と環境差

`modules/` 内に `var.env` の分岐を書きません。差分は `envs/*/main.tf` から変数で渡します。
`media_api` の既定値は `lambda_memory_size = 256`、`lambda_timeout = 10` です。
`notify_upload_complete` と `delete_user` はモジュール内で `timeout = 30` を直接指定しています。

`env` には `contains(["dev", "prod"], var.env)` の `validation` があります。
新しい環境を足すときはここも更新が必要です。

## 変更時の注意

- `local.lambda_functions` の key を変えると log group が置換されます。関数名の変更は
  Lambda 本体・log group・IAM ロール名を同時に動かすため、`terraform plan` の destroy / replace を必ず読みます。
- `aws_api_gateway_resource` の `path_part` 変更は下流の method / integration をすべて置換します。
- リソース名やモジュールパスを変えるだけの整理でも state move が必要になります。判断がつかなければ
  ユーザーへ確認します。
- IAM 権限を広げる変更と `bootstrap/` の変更は、実装前に方針を提示します。

## 検証

```powershell
terraform fmt -recursive
```

```powershell
Set-Location envs/dev
terraform validate
terraform plan
```

`validate` / `plan` には `.build/firebase_admin_layer.zip` と backend 初期化が必要です。手順は
[README.md](../../../../README.md) のローカル開発を参照します。実行できない場合は
`Not executed` と理由を報告します。

## 参考資料

- [docs/infrastructure.md](../../../../docs/infrastructure.md)
- [docs/guardrails.md](../../../../docs/guardrails.md)
- [docs/verification_policy.md](../../../../docs/verification_policy.md)
