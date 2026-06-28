---
name: implementation-review
description: 実装差分のレビューに使う。最小権限IAM / IDOR防止 / PII・トークンのログ漏洩 / シークレット混入 / 既存パターン準拠を観点に変更を点検する。セキュリティ観点を中核に据える。
---

# Implementation Review

## 実装手順

1. ベースブランチ（`develop` / `main`）との差分を対象にする。一般的な品質網羅は `review-branch` skill、脆弱性スキャンは `security-review` / `trivy` と併用する。
2. IAM: アクション・ARN 限定でワイルドカード無し・`jsonencode` か確認する（`modules/media_api/main.tf`）。
3. IDOR: 全データアクセス前に identity 境界（S3 `private/<identity>/`、DynamoDB key、`lastEvaluatedKey.userId`）を確認しているか。認証だけで満足していないか。
4. ログ衛生: `mask_identity` を通し、生 `cognitoIdentityId` / `deviceToken` / 認証情報・リクエストボディをログに出していないか。
5. シークレット混入: トークン・秘密鍵・AWSアカウントID（12桁）・PII が差分に無いか。
6. Cognito / 認可設定: `prevent_user_existence_errors`、password policy、`generate_secret = false`、API method の `authorization = "AWS_IAM"` が弱められていないか。
7. コード品質: `auth.py` / `response.py` / `db.py` パターン準拠、`constants.py` 集約、型ヒント、`ClientError` の 404/500 分離、未認証=403、テスト更新を確認する。

## トリアージ

各指摘は次のいずれかに分類して報告する。

- **Critical**: マージブロック。リリース前に必ず直す。例: Lambda のクラッシュ・未処理例外、データ損失（破壊的な物理削除・`terraform` のリソース置換/destroy）、認証・権限不備（IDOR、IAM の過剰権限・ワイルドカード）、secret 漏洩（トークン・鍵・AWSアカウントID・PII の混入やログ出力）、state/migration 破壊（不適切な `state mv`・互換性のない変更）、CI で確実に失敗する問題。
- **Suggestion**: マージブロックではないが、保守性、責務分離、テスト網羅、エラー処理、性能、将来の変更容易性を明確に改善する指摘。
- **Nitpick**: 動作や設計への影響が小さい表記、命名、整形、軽微な読みやすさの指摘。対応任意として扱う。

## 検証手順

1. 差分取得 `git diff develop...HEAD`（リモート PR は `review-branch` skill）。
2. IaC を含むなら `trivy conf .`。
3. 指摘は「ファイル:行」と根拠（規約・出典）を添えて報告する。

## 参考資料

- [docs/security.md](../../../docs/security.md)
- [docs/guardrails.md](../../../docs/guardrails.md)
