# 検証ポリシー

この文書は、変更完了前に実行する検証と、その報告形式を定義します。

## Status Vocabulary

検証結果は必ず次のいずれかで報告してください。

| ステータス | 意味 |
|---|---|
| `Executed and passed` | 実行し、成功した |
| `Executed and failed` | 実行し、失敗した |
| `Not executed` | 未実行。理由を添える |
| `Blocked by state lock` | Terraform state lock により実行できなかった |

実行していないコマンドを成功扱いにしないでください。

## Change Matrix

| 変更対象 | 必須検証 |
|---|---|
| ドキュメントのみ | Markdownの整合性、リンク対象の存在確認 |
| Terraform | `terraform fmt -recursive`、影響環境の `terraform validate`、可能なら `terraform plan` |
| IAM / security | Terraform検証に加え、権限差分レビュー、可能なら `trivy conf .` |
| Lambda | `ruff format`、`ruff check`、関連 `pytest` |
| CI/CD | ワークフロー構文と影響するコマンドの確認 |
| bootstrap | 検証に加え、手動適用手順とリスクの明記 |

## Terraform

リポジトリルートで整形します。

```powershell
terraform fmt -recursive
```

影響を受ける環境で検証します。

```powershell
Set-Location envs/dev
terraform validate
terraform plan
```

prodに影響する場合は `envs/prod` でも同様に確認します。認証情報、backend access、init が不足している場合は `Not executed` として理由を報告してください。

### State Lock

ロックエラーが出た場合:

- `-lock=false` を使わない
- `force-unlock` を実行しない
- 環境、Lock ID、Operation、Who、Created を報告する
- ステータスは `Blocked by state lock` にする

## Lambda

Lambda変更時は `lambda/` を基準にテストします。

```powershell
ruff format lambda/
ruff check lambda/
Set-Location lambda
pytest
```

対象が限定されている場合は、関連するテストディレクトリだけを実行して構いません。ただし、その理由を報告してください。

## Security

IaCやIAMに影響する変更では、可能な限り次を実行します。

```powershell
trivy conf .
```

`trivy` が未インストール、認証不足、ネットワーク制約などで実行できない場合は `Not executed` として理由を明記してください。

## Completion Format

完了報告では、次の形式を推奨します。

```text
Verification:
- Executed and passed: <command or check>
- Executed and failed: <command> (<reason>)
- Not executed: <command> (<reason>)
- Blocked by state lock: <env>, Lock ID <id>
```

残る手動作業や未解決リスクがある場合は、検証結果とは別に明記してください。
