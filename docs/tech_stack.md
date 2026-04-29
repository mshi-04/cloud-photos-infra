# 技術スタック

この文書は、リポジトリで前提にする技術と運用ツールをまとめます。

## Infrastructure

| 項目 | 内容 |
|---|---|
| Cloud | AWS |
| Region | `ap-northeast-1` |
| IaC | Terraform |
| Root modules | `envs/dev`, `envs/prod` |
| Reusable modules | `modules/` |
| Bootstrap | `bootstrap/` |

## AWS Services

| カテゴリ | サービス | 用途 |
|---|---|---|
| Auth | Amazon Cognito User Pool / Identity Pool | ユーザー認証とAWS認可 |
| Storage | Amazon S3 | メディアファイル、Terraform state |
| Database | Amazon DynamoDB | メディアメタデータ、デバイストークン |
| Compute | AWS Lambda | APIロジック |
| API | Amazon API Gateway | REST API |
| Notification | Amazon SNS | プッシュ通知 |
| Security | IAM, KMS, Secrets Manager | 権限、暗号化、機密情報 |

## Terraform

| 項目 | 内容 |
|---|---|
| Version | `.terraform-version` を参照 |
| Provider | `hashicorp/aws` |
| State | S3 backend |
| Locking | backend lock mechanism を使用 |
| Formatting | `terraform fmt -recursive` |
| Validation | `terraform validate`, `terraform plan` |

## Lambda

| 項目 | 内容 |
|---|---|
| Runtime | Python 3.12 |
| SDK | `boto3` |
| Lint / format | `ruff` |
| Test | `pytest` |
| Auth pattern | Cognito JWT validation via existing `auth.py` helpers |

## CI/CD

| 項目 | 内容 |
|---|---|
| Platform | GitHub Actions |
| Auth to AWS | OIDC roles |
| PR | Terraform plan、lint、test |
| Main merge | dev auto deploy |
| Prod | manual approval |

## Agent Instruction Files

| ファイル | 役割 |
|---|---|
| `AGENTS.md` | 全エージェント向けの唯一の入口と地図 |
| `CLAUDE.md` | Claude Code向けの薄い入口 |
| `docs/*.md` | 実際の詳細ルール |

入口ファイルは短く維持し、長い手順や領域別規約は `docs/` に置いてください。ディレクトリごとの `AGENTS.md` は作成しません。
