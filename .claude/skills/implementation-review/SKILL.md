---
name: implementation-review
description: 実装差分のレビューに使う。比較対象を依頼や PR から確かめ、最小権限 IAM、IDOR 防止、PII とトークンのログ漏洩、シークレットの混入、API 応答の契約、コーディング規約を観点に変更を点検し、根拠とともに分類して報告する。セキュリティの観点を中核に据える。
---

# Implementation Review

ブランチや PR の差分をレビューする作業に使う。このリポジトリにない他の Skill を前提にしない。

## 比較対象の確かめ方

1. 依頼に比較対象のブランチやコミットがあれば、それを使う。
2. PR のレビューなら、PR の base branch を使う。`develop` が常に比較対象だと仮定しない。
3. どちらも分からない場合は、ユーザーに確認する。

比較対象を取得してから、共通の祖先からの差分を見る。

```powershell
git fetch origin <base>
git diff origin/<base>...HEAD
```

## レビュー手順

1. 変更されたファイルから、関係する契約と規約を選んで読む。Lambda なら [docs/lambda.md](../../../docs/lambda.md)、Terraform なら [docs/infrastructure.md](../../../docs/infrastructure.md)、どちらにも [docs/security.md](../../../docs/security.md) と [docs/coding_standards.md](../../../docs/coding_standards.md) を使う。
2. セキュリティを確かめる。IAM の最小権限、データアクセス前の所有者確認（IDOR）、ログの衛生、シークレットや AWS アカウント ID の混入、Cognito と API の認証設定。
3. 契約を確かめる。API の応答（ステータス、本文、未認証の 401 と 403）、条件付き書き込み、冪等性が、[docs/lambda.md](../../../docs/lambda.md) と一致するか。
4. コーディング規約を確かめる。新しく書いたコードと変更した範囲が、[docs/coding_standards.md](../../../docs/coding_standards.md) の原則に従っているか。指摘には、根拠の原則の名前（例:「早期リターン」「値オブジェクト」）を示す。
5. Terraform では、plan で destroy や replace が出る変更、`moved` ブロックのない改名、データ保護の後退を確かめる。
6. 動作の変更に対応するテストがあるかを確かめる。

観点ごとの確認項目は [review-checklist.md](references/review-checklist.md) を参照する。

## トリアージ

各指摘は次のいずれかに分類する。

- **Critical**: マージを止める。例: Lambda のクラッシュや未処理例外、データ損失（物理削除、リソースの置換や destroy）、認証・権限の不備（IDOR、IAM の過剰な権限やワイルドカード）、シークレットの漏洩（トークン、鍵、AWS アカウント ID、PII の混入やログ出力）、state の破壊、CI で確実に失敗する問題。
- **Suggestion**: マージは止めないが、保守性、責務の分離、テストの網羅、エラー処理、性能、規約への準拠を明確に改善する。
- **Nitpick**: 動作や設計への影響が小さい表記、命名、整形。対応は任意。

## 報告

指摘ごとに「ファイル:行」、分類、根拠（契約、規約の原則、既存の実装の該当箇所）を示す。IaC を含む差分では、可能なら `trivy conf .` を実行し、実行できなければ `Not executed` として理由を書く。検証の報告は [docs/verification_policy.md](../../../docs/verification_policy.md) の形式に従う。

## 参考資料

- [references/review-checklist.md](references/review-checklist.md): 観点ごとの確認項目と根拠となる実装の位置
- [docs/security.md](../../../docs/security.md)
- [docs/coding_standards.md](../../../docs/coding_standards.md)
- [docs/guardrails.md](../../../docs/guardrails.md)
