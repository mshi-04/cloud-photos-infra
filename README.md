# AWS Terraform + GitHub Actions CI/CD プロジェクト

このプロジェクトは、`cloud-photos-infra` の AWS 基盤（Cognito 等）を Terraform と GitHub Actions を用いて実運用レベルで管理する構成になっています。

## ディレクトリ構成

- `envs/`
  - `dev/`: 開発環境の Terraform コード（State は S3 の dev/ キーを使用）
  - `prod/`: 本番環境の Terraform コード（State は S3 の prod/ キーを使用）
- `bootstrap/`: 最初に1回だけ手動適用する S3 バケット、DynamoDB テーブル、OIDC 用 IAM ロールの定義
- `.github/workflows/`: CI (PR検証) および CD (マージ時デプロイ) の定義

## 重要な運用ルール

1. **ローカル Apply は原則禁止（仕組みでブロック）**
   - 開発者の IAM 権限では直接 Apply できないよう、S3 バケットポリシーおよび IAM ロール権限で制御しています。
   - 構成変更は必ず Pull Request を作成し、GitHub Actions 経由で Apply させてください。

2. **本番環境へのデプロイ（CD）フロー**
   - `.github/workflows/cd-terraform.yml` により、`main` ブランチにマージされたタイミングで発火します。
   - `apply-dev`（開発環境への自動適用）が完了した後、本番環境の `plan-prod` が実行されます。
   - `plan-prod` で生成された Plan 差分（アーティファクト）を確認の上、**GitHubの Environment ("production") 画面から手動承認** を行うことで、初めて `apply-prod` が実行されます。

## GitHub リポジトリの初期設定手順

本リポジトリを安全に運用するために、GitHub 側で以下の設定を行ってください。

1. **Environments (承認ゲート) の作成**
   - リポジトリの Settings > Environments から `production` を作成します。
   - 「Required reviewers」を有効にし、承認権限を持つユーザーまたはチームを指定します。
   - 「Deployment branches and tags」で `Selected branches and tags` を選び、`main` のみに制限します。

2. **Branch Protection rule (ブランチ保護) の設定**
   - `main` ブランチに対してルールを作成します。
   - **Require a pull request before merging**: 有効化（ローカルからの直接 Push 禁止）
   - **Require status checks to pass before merging**: 有効化し、CI のジョブ名（`plan-dev` と `plan-prod`）を必須チェックに追加します。
