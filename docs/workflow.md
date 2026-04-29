# 開発ワークフロー

この文書は、AIエージェントと開発者がこのリポジトリで変更を行う際の標準手順です。目的は、探索のしすぎと確認不足の両方を避け、変更・検証・報告を一貫させることです。

## 1. Intake

作業開始時に次を確認します。

- ユーザーの依頼内容、明示的な禁止事項、承認が必要な操作
- `git status --short` による既存差分
- 変更対象に近いファイルと、対応する `docs/*.md`
- Terraform、Lambda、CI/CD、bootstrap、IAM のどれに影響するか

既存差分はユーザーの作業として扱い、依頼がない限り戻さないでください。

## 2. Context

ルートの `AGENTS.md` が唯一の入口です。詳細は変更対象ごとに読む文書を絞ります。

| 変更対象 | 読む文書 |
|---|---|
| Terraform / AWS | `docs/infrastructure.md`, `docs/coding_standards.md`, `docs/security.md` |
| Lambda | `docs/lambda.md`, `docs/testing.md`, `docs/coding_standards.md` |
| IAM / secrets / auth | `docs/security.md`, `docs/guardrails.md` |
| 検証・完了報告 | `docs/verification_policy.md`, `docs/commands.md` |
| bootstrap | `docs/guardrails.md`, `docs/infrastructure.md` |

検索には `rg` を使わず、PowerShell の `Get-ChildItem` と `Select-String` を使ってください。
ディレクトリ別の `AGENTS.md` は作成せず、恒久的なルールは `docs/` の該当文書へ追加してください。

## 3. Plan

次のいずれかに該当する場合は、編集前に方針をユーザーへ提示します。

- リソース削除、置換、データ保持への影響があり得る
- IAM権限を広げる
- `bootstrap/` を変更する
- dev/prod の両方にまたがる設計変更を行う
- Terraform state move/import が必要になり得る

小さなドキュメント修正、局所的なテスト修正、既存パターンに沿った実装は自律的に進めて構いません。

## 4. Implement

- 変更は依頼達成に必要な最小範囲に限定します。
- コード、変数名、コメントは英語で書きます。
- ドキュメントは日本語で構いません。
- 既存の構成、命名、ヘルパー、テスト配置を優先します。
- 無関係なリファクタリング、整形、依存更新を混ぜないでください。

Terraform と Lambda の具体ルールは `docs/infrastructure.md` と `docs/lambda.md` に従います。

## 5. Verify

変更対象に応じて `docs/verification_policy.md` の検証を実行します。代表的な検証は次の通りです。

| 対象 | コマンド |
|---|---|
| Terraform整形 | `terraform fmt -recursive` |
| Terraform検証 | 影響環境で `terraform validate` |
| Terraform計画 | 影響環境で `terraform plan` |
| Lambda整形 | `ruff format lambda/` |
| Lambda静的解析 | `ruff check lambda/` |
| Lambdaテスト | `cd lambda; pytest` または対象テスト |
| IaCスキャン | `trivy conf .` |

ステートロックが出た場合は `-lock=false` や `force-unlock` で回避せず、`Blocked by state lock` として報告します。

## 6. Report

完了報告には次を含めます。

- 変更した内容の要約
- 実行した検証と結果
- 実行しなかった検証と理由
- 残るリスク、手動作業、ユーザー承認が必要な事項

検証ステータスは `Executed and passed`、`Executed and failed`、`Not executed`、`Blocked by state lock` のいずれかで表記してください。

## 7. Release

PR作成やpushを行う場合は、ユーザーの依頼または合意に従います。

- PRは影響範囲、検証結果、残リスクを明記します。
- Devは `main` マージ後に自動適用されます。
- Prodは GitHub Actions 上の手動承認が必要です。
- `bootstrap/` の変更は通常のデプロイ経路では反映されないため、手動フォローアップを明記します。
