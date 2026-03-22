# セキュリティポリシー

## サポート対象バージョン

| ブランチ | サポート状況 |
|----------|-------------|
| main     | :white_check_mark: |
| develop  | :white_check_mark: |

## 脆弱性の報告方法

セキュリティ上の脆弱性を発見した場合は、責任ある開示にご協力ください。

**セキュリティ脆弱性に関する公開 Issue は作成しないでください。**

代わりに [GitHub Private Vulnerability Reporting](https://github.com/mshi-04/cloud-photos-infra/security/advisories/new) からご報告ください。

### 報告に含めてほしい情報

- 脆弱性の概要
- 再現手順
- 想定される影響範囲
- 修正案（あれば）

### 対応スケジュール

- **受領確認**: 3営業日以内
- **初期評価**: 7営業日以内
- **修正・緩和策**: 深刻度に応じて対応

## コントリビューター向けセキュリティガイドライン

- シークレット、認証情報、AWS アカウント ID をリポジトリにコミットしないこと
- インフラ変更は必ず Pull Request を経由すること
- Terraform state ファイルをリポジトリにコミットしないこと
- 機密情報は環境変数または AWS Secrets Manager で管理すること
