# AWS Terraform + GitHub Actions CI/CD プロジェクト

このプロジェクトは、`cloud-photos-infra` の AWS 基盤を Terraform と GitHub Actions を用いて実運用レベルで管理・デプロイする構成になっています。
写真共有アプリケーションのバックエンド（認証、API、データベース、ストレージ）インフラを構築します。

## アーキテクチャ構成

本リポジトリでデプロイされる主要なAWSリソースは以下の通りです。

- **Amazon Cognito (User Pool / Identity Pool)**: ユーザー認証およびクレデンシャルの発行。
- **Amazon API Gateway**: クライアントからのリクエストを受け付けるREST API。CORSにも完全対応。
- **AWS Lambda (Python 3.12)**: 写真のメタデータ（アップロード記録）を管理するビジネスロジック。
- **Amazon DynamoDB**: メタデータを保持するNoSQLデータベース。
- **Amazon S3**: 実際のメディア（写真・動画）ファイルを保存するストレージ（Cognito Identity ID単位のプレフィックスでアクセス制御）。

## API エンドポイント

API Gateway によって以下のエンドポイントが提供されます。すべてのエンドポイントは Cognito による認証（AWS_IAM）が必要です。

- `GET /media/uploads`: 自身のアップロード済みメディア一覧を取得
- `POST /media/uploads`: 新しいメディアのアップロード記録を作成
- `DELETE /media/uploads/{mediaId}`: 指定したメディアのアップロード記録を削除

## セキュリティと権限管理 (Least Privilege)

- 各 Lambda 関数には単一の共有ロールではなく、**関数ごとに最小権限を持つ個別の IAM ロール**（`get_upload_records-role`, `create_upload_record-role`, `delete_upload_record-role`）が割り当てられています。
- 各ロールは、DynamoDB テーブルに対する必要なアクション（`dynamodb:Query`, `dynamodb:PutItem`, `dynamodb:DeleteItem`）のみが特別に許可されています。
- フロントエンドクライアント（認証済みユーザー）のロールは、S3 の `/private/${cognito-identity.amazonaws.com:sub}/` プレフィックスに対する読み書き権限と、API Gateway の特定のエンドポイントに対する `execute-api:Invoke` 権限のみを持っています。

## ディレクトリ構成

- `envs/`
  - `dev/`: 開発環境の Terraform コード（State は S3 の dev/ キーを使用）
  - `prod/`: 本番環境の Terraform コード（State は S3 の prod/ キーを使用）
- `bootstrap/`: 最初に1回だけ手動適用する S3 バケット、DynamoDB テーブル、OIDC 用 IAM ロールの定義
- `modules/`: 各リソースの定義モジュール（`cognito`, `identity_pool`, `media_api`, `media_db`, `media_storage`）
- `lambda/media_uploads/`: API のバックエンドを処理する Python スクリプトおよび依存関係
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
