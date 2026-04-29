# AGENTS.md

本リポジトリで作業するAIコーディングエージェント向けの唯一の入口です。ディレクトリごとの `AGENTS.md` は置かず、このファイルを短い地図として維持し、詳細は `docs/` に集約します。

## First Read

| 目的 | 参照先 |
|---|---|
| 作業の進め方 | [docs/workflow.md](docs/workflow.md) |
| 実行禁止・承認が必要な操作 | [docs/guardrails.md](docs/guardrails.md) |
| 完了前の検証 | [docs/verification_policy.md](docs/verification_policy.md) |
| よく使うコマンド | [docs/commands.md](docs/commands.md) |
| Terraform / Python の規約 | [docs/coding_standards.md](docs/coding_standards.md) |
| AWS / Terraform の変更 | [docs/infrastructure.md](docs/infrastructure.md) |
| Lambda の変更 | [docs/lambda.md](docs/lambda.md) |
| テスト | [docs/testing.md](docs/testing.md) |
| セキュリティ / IAM | [docs/security.md](docs/security.md) |
| 技術スタック | [docs/tech_stack.md](docs/tech_stack.md) |

## Repository Profile

- AWS インフラは Terraform で管理します。
- ルートモジュールは `envs/dev` と `envs/prod`、再利用モジュールは `modules/` に置きます。
- Lambda は `lambda/` 配下の Python 3.12 実装です。
- CI/CD は GitHub Actions と AWS OIDC を使います。
- `bootstrap/` は初期セットアップ用で、通常のCI/CDでは自動適用されません。

## Directory Scope

| パス | 作業時に読む文書 |
|---|---|
| `bootstrap/` | `docs/guardrails.md`, `docs/infrastructure.md`, `docs/security.md` |
| `envs/` | `docs/infrastructure.md`, `docs/verification_policy.md` |
| `modules/` | `docs/infrastructure.md`, `docs/coding_standards.md`, `docs/security.md` |
| `lambda/` | `docs/lambda.md`, `docs/testing.md`, `docs/coding_standards.md` |
| `.github/workflows/` | `docs/workflow.md`, `docs/infrastructure.md` |
| `docs/` | `docs/workflow.md`, `docs/verification_policy.md` |

## Operating Rules

- ユーザーの依頼、既存差分、リポジトリ文書の順に確認してから編集してください。
- 変更は依頼達成に必要な最小範囲に限定してください。
- 既存の未コミット変更を、明示的な依頼なしに戻さないでください。
- コード、変数名、コメントは英語で書いてください。ドキュメントは日本語で構いません。
- シークレット、トークン、秘密鍵、AWSアカウントID、個人情報をコミットしないでください。
- ファイル検索や文字列検索に `rg` は使わないでください。PowerShell の `Get-ChildItem`、`Select-String`、またはプロジェクトで許可されたスクリプトを使ってください。
- ディレクトリ固有の補足を追加したい場合も、新しい `AGENTS.md` を増やさず、対応する `docs/*.md` に追記してください。

## Autonomy Boundary

即座に進めてよい作業:

- 調査、読み取り、差分確認
- ドキュメント修正
- `terraform fmt -recursive`
- `ruff format`、`ruff check`
- `pytest`
- `terraform validate`
- `terraform plan`

事前にユーザー確認が必要な作業:

- `terraform apply`
- `terraform force-unlock`
- `terraform plan -lock=false` / `terraform apply -lock=false`
- `git push --force`
- 複数環境にまたがる設計変更
- リソース削除、置換、データ保持に影響する変更
- IAM権限の拡張
- `bootstrap/` 配下の変更

## Terraform Rules

- コミット前に `terraform fmt -recursive` を実行してください。
- IAMポリシーは heredoc ではなく `jsonencode()` を優先してください。
- モジュール内に `var.env == "prod"` のような環境分岐を持ち込まないでください。
- `"Action": "*"` と `"Resource": "*"` は避け、実用可能な範囲で具体的なアクションとARNを指定してください。
- リネームや構造変更は、強制再作成や state move が必要かを確認してください。

## Lambda Rules

- Python 3.12 と型ヒントを前提に実装してください。
- API系 Lambda は既存の `auth.py` パターンで Cognito JWT を検証してください。
- HTTPレスポンスは既存の `response.py` パターンに合わせてください。
- PII、生トークン、認証情報をログに出さないでください。
- 動作を変えた場合は、該当テストを追加または更新してください。

## Verification Report

完了報告では、関連する検証を次のステータスで明記してください。

- `Executed and passed`
- `Executed and failed`
- `Not executed` と理由
- `Blocked by state lock` と環境、Lock ID、推定原因

実行していない検証を成功扱いにしないでください。
