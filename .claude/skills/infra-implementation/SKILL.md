---
name: infra-implementation
description: Terraform / AWS インフラ（modules・envs・IAM・Cognito・S3・DynamoDB）の設計・実装・修正に使う。jsonencode最小権限、env分岐禁止、リネーム時のstate move確認、検証フローを提供。
---

# Infra Implementation

## 実装手順

1. 変更対象（Lambda / API Gateway / DynamoDB / S3 / Cognito / IAM）と影響環境（`envs/dev`、`envs/prod`）を特定する。
2. 環境差はルートモジュール側の変数で吸収し、`modules/` 内に `var.env` 分岐を入れない。標準構成は `main.tf` / `variables.tf` / `outputs.tf`。
3. IAM は `jsonencode()` で書き、`"Action":"*"` / `"Resource":"*"` を避け、アクションと ARN を限定する。CloudWatch Logs の event write は、限定した log group ARN に必要な `:*` suffixを許容する（`modules/media_api/main.tf` 参照）。
4. Lambda は `runtime = "python3.12"`、`handler = "<file>.handler"`、`environment.variables`（`TABLE_NAME` 等）、log group への `depends_on` を踏襲する。
5. リネーム・モジュール移動は強制再作成になるか確認し、必要なら `terraform state mv` で state を移す。判断がつかなければユーザーに確認する。
6. 承認必須操作（`apply` / `force-unlock` / `-lock=false` / リソース削除・置換 / IAM 拡張 / `bootstrap/` 変更 / 複数環境にまたがる設計変更）は事前にユーザー確認する。

## 検証手順

1. `terraform fmt -recursive`
2. 影響環境で `terraform validate` と `terraform plan`
3. IaC スキャン `trivy conf .`
4. 完了報告は検証ステータス（`Executed and passed` / `Not executed` / `Blocked by state lock` 等）で明記する。

## 参考資料

- [references/media-api-wiring.md](references/media-api-wiring.md): `modules/media_api` の構成、エンドポイント追加手順、置換になる変更
- [references/env-matrix.md](references/env-matrix.md): dev / prod の変数差分とモジュール既定値
- [docs/infrastructure.md](../../../docs/infrastructure.md)
- [docs/guardrails.md](../../../docs/guardrails.md)
- [docs/verification_policy.md](../../../docs/verification_policy.md)
