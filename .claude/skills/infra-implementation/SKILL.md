---
name: infra-implementation
description: Terraform / AWS インフラ（modules・envs・IAM・Cognito・API Gateway・S3・DynamoDB・Lambda の配布）の設計・実装・修正に使う。モジュールの構成と変数の書き方、jsonencode による最小権限、環境分岐の禁止、moved ブロックによる state の移行、検証の流れを提供する。
---

# Infra Implementation

`envs/`、`modules/`、`bootstrap/` の Terraform を変える作業に使う。Lambda の Python コードも変える場合は lambda-implementation Skill も使う。

## 作業の選び方

作業に必要な資料だけを読む。

| 作業 | 読む資料 |
|---|---|
| API のエンドポイントや Lambda を追加する、`modules/media_api` を変える | [media-api-wiring.md](references/media-api-wiring.md) |
| dev と prod で値を変える、モジュールの既定値に触れる | [env-matrix.md](references/env-matrix.md) |
| IAM、Cognito、Identity Pool を変える | [docs/security.md](../../../docs/security.md) |
| `bootstrap/` を変える | [docs/infrastructure.md](../../../docs/infrastructure.md) の Bootstrap |

## 実装手順

1. 変更するリソースと、影響する環境（`envs/dev`、`envs/prod`）を特定する。
2. モジュールは `main.tf`、`variables.tf`、`outputs.tf` で構成する。新しいモジュールには `versions.tf` を置き、`required_providers` でプロバイダの取得元とバージョンの下限を宣言する。大きなモジュールは、モジュールを分けずに責務別のファイルに分ける。
3. 変数と出力には `type` と `description` を付ける。値の範囲が決まる入力には `validation`、null を受け付けない入力には `nullable = false`、機密値には `sensitive = true` を付ける。
4. 環境差はルートモジュールから変数で渡し、モジュールの中で環境名による分岐をしない。同じ文字列や計算は `locals` から導出する。
5. 複数のリソースは安定したキーを持つ `for_each` で作り、`count` は有効と無効の切り替えだけに使う。使われていない変数、data source、`locals` を残さない。
6. IAM は `jsonencode()` で書き、アクションと ARN を限定する。`"Action": "*"` と `"Resource": "*"` を避ける。CloudWatch Logs の event write は、限定した log group ARN に必要な `:*` の suffix を許容する。
7. 名前は snake_case にし、resource 名にリソースの種別を繰り返さない。名前やモジュールのパスを変える場合は、`moved` ブロックで state を移し、plan で移動を確かめる。手作業の `terraform state mv` は使わない。

書き方の詳細は [docs/coding_standards.md](../../../docs/coding_standards.md) の Terraform の原則に従う。既存のモジュールは `required_providers` を宣言していないため、変更する範囲だけを規約に合わせる。

## 判断が必要な場面

次の操作は、実装または実行の前にユーザーに方針を示して確認する。詳細は [docs/guardrails.md](../../../docs/guardrails.md) に従う。

- `terraform apply`、`force-unlock`、`-lock=false`
- plan に destroy または replace が出る変更、state の移行が必要になり得る変更
- IAM の権限を広げる変更、`bootstrap/` の変更
- dev と prod の両方にまたがる設計の変更

## 検証手順

```powershell
terraform fmt -recursive
Set-Location envs/dev
terraform validate
terraform plan
```

prod に影響する場合は `envs/prod` でも確かめる。IaC や IAM を変えた場合は、可能なら `trivy conf .` も実行する。認証情報や backend に接続できず実行できない場合は、`Not executed` として理由を報告する。state lock が出た場合は回避せず、`Blocked by state lock` として報告する。報告の形式は [docs/verification_policy.md](../../../docs/verification_policy.md) に従う。

## 参考資料

- [docs/infrastructure.md](../../../docs/infrastructure.md): 環境とモジュールの責務、CI/CD
- [docs/coding_standards.md](../../../docs/coding_standards.md): Terraform の原則
- [docs/guardrails.md](../../../docs/guardrails.md): 承認が必要な操作、state lock
- [docs/verification_policy.md](../../../docs/verification_policy.md): 検証の範囲と報告の形式
