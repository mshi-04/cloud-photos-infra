# レビュー チェックリスト

観点ごとの具体的な確認項目と、根拠となる実装位置です。

## IAM

- `jsonencode()` で書かれているか。ヒアドキュメントや文字列連結になっていないか
- `"Action": "*"` / `"Resource": "*"` が無いか。アクションは配列で列挙されているか
- logs ポリシーが `"${aws_cloudwatch_log_group.lambda["<key>"].arn}:*"` に限定されているか。
  `arn:aws:logs:*:*:*` になっていないか
- Lambda ごとに `aws_iam_role` が分かれているか。既存ロールへ権限を相乗りさせていないか
- S3 の `ListBucketVersions` に `s3:prefix` の `Condition` が付いているか
  （`delete_user_s3` が既存例）
- `Sid` が権限の目的を説明しているか

## IDOR

すべてのデータアクセスの前に identity 境界があるか確認します。認証の有無だけで通していないか。

| 入力 | 必要なチェック |
|---|---|
| `cloudStoragePath` | `private/<identity_id>/` で始まるか |
| `lastEvaluatedKey` | `userId == identity_id` か。受け取った dict をそのまま `ExclusiveStartKey` にしていないか |
| `pathParameters.mediaId` | key の HASH に `identity_id` が入っているか |
| `deviceToken` | key の HASH に `identity_id` が入っているか |

境界違反は 403 です。400 に落とすと存在有無が漏れます。

## ログ衛生

- identity は `mask_identity` を通しているか
- 生の `cognitoIdentityId`、`deviceToken`、リクエストボディ、認証情報が出ていないか
  （FCM トークンは `token[-4:]` のみが既存の扱い）
- 例外の詳細をレスポンス本文へ載せていないか。500 の本文は `"Internal server error"` 固定か

## シークレット混入

- トークン、秘密鍵、12 桁の AWS アカウント ID、PII が差分に無いか
- Firebase 認証情報が Secrets Manager 経由のままか。Terraform 変数や tfvars へ移していないか
- ドキュメントの例が明らかなダミー値か

## 認証・認可設定

- 業務メソッドの `authorization = "AWS_IAM"` が維持されているか。`NONE` は CORS の `OPTIONS` だけか
- `outputs.api_execution_arns` がメソッドとパス単位のままか。`/*` へ広がっていないか
- Identity Pool の S3 ポリシーが `private/$${cognito-identity.amazonaws.com:sub}/*` のままか
- `allow_unauthenticated_identities = false`、`server_side_token_check = true` が維持されているか
- User Pool の `prevent_user_existence_errors`、password policy、`generate_secret = false`、
  `explicit_auth_flows`、prod の `mfa_configuration = "ON"` と `deletion_protection = "ACTIVE"` が
  弱められていないか

## Terraform の破壊的変更

`terraform plan` に destroy / replace が出た場合、意図した変更かを明記します。

- `local.lambda_functions` の key 変更 → log group の置換
- `aws_api_gateway_resource.path_part` 変更 → 下流 method / integration の置換
- リソース名・モジュールパスの変更 → `terraform state mv` の要否
- `deletion_protection_enabled` / `force_destroy` / `noncurrent_version_expiration_days` の変更 → データ保護の後退
- `aws_api_gateway_deployment.media` の `triggers.redeployment` に新しい id が入っているか

## コード品質

- `auth.py` / `response.py` / `db.py` のパターンに従っているか。ヘルパーを迂回していないか
- フィールド名・列挙値が `constants.py` に集約されているか。文字列直書きが無いか
- 型ヒントが付いているか（Python 3.12）
- 条件式失敗を操作別に扱っているか。`create_upload_record.py` の重複は 200、`delete_upload_record.py` の対象不存在は 404、その他の例外は 500
- 動作変更に対応するテストが追加・更新されているか
- 新規ファイルが明示リスト方式の ZIP に属する場合、`modules/media_api/main.tf` の `locals` へ
  追加されているか

## トリアージ

- **Critical**: クラッシュ・未処理例外、データ損失、認証/権限不備、secret 漏洩、state 破壊、CI 確実失敗
- **Suggestion**: 保守性・責務分離・テスト網羅・エラー処理・性能の明確な改善
- **Nitpick**: 表記・命名・整形。対応任意

指摘には「ファイル:行」と根拠（規約または既存実装の該当箇所）を添えます。

## 参考資料

- [docs/security.md](../../../../docs/security.md)
- [docs/guardrails.md](../../../../docs/guardrails.md)
- [docs/verification_policy.md](../../../../docs/verification_policy.md)
