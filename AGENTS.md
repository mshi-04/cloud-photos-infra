# AGENTS.md

このリポジトリのAI作業ルールです。詳細は [docs/](docs/) の該当文書を参照してください。
ここは作業時の地図として役割をします。

## 主要文書

- [docs/guardrails.md](docs/guardrails.md): 実行禁止・承認が必要な操作、state lock、シークレット
- [docs/verification_policy.md](docs/verification_policy.md): 変更種別ごとの検証スコープと報告形式
- [docs/commands.md](docs/commands.md): よく使うコマンド（検索・Terraform・Lambda・security）
- [docs/coding_standards.md](docs/coding_standards.md): Terraform / Python / ドキュメントの規約
- [docs/infrastructure.md](docs/infrastructure.md): envs / modules 構成、AWS / Terraform の変更
- [docs/lambda.md](docs/lambda.md): Lambda の構成、handler 設計、認証、ログ
- [docs/testing.md](docs/testing.md): pytest + moto のテスト構成と方針
- [docs/security.md](docs/security.md): セキュリティ / IAM 最小権限 / IDOR / ログ衛生
- [docs/tech_stack.md](docs/tech_stack.md): 技術スタック

## AI skills

作業内容に応じて [.agents/skills/](.agents/skills/) の該当 `SKILL.md` を読む。

- [lambda-implementation](.agents/skills/lambda-implementation/SKILL.md): Lambda 関数（handler / models / response / constants）の設計・実装・修正
- [db-implementation](.agents/skills/db-implementation/SKILL.md): DynamoDB データアクセスの設計・実装・修正
- [auth-implementation](.agents/skills/auth-implementation/SKILL.md): 認証・認可（Cognito Identity / IDOR）の設計・実装・修正
- [infra-implementation](.agents/skills/infra-implementation/SKILL.md): Terraform / AWS インフラの設計・実装・修正
- [test-implementation](.agents/skills/test-implementation/SKILL.md): テストの追加・修正・レビュー
- [implementation-review](.agents/skills/implementation-review/SKILL.md): 実装差分のレビュー
