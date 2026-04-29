# 共通コマンド

このリポジトリでよく使うコマンドです。PowerShell を前提にしています。

## 検索

`rg` は使用禁止です。ファイル探索と文字列検索は次を使います。

```powershell
Get-ChildItem -Recurse -File
Get-ChildItem -Recurse -File -Include *.tf,*.py,*.md
Get-ChildItem -Recurse -File | Select-String -Pattern 'keyword'
```

## Git

```powershell
git status --short
git diff --name-status
git diff --cached --name-status
```

既存差分はユーザー作業として扱い、依頼がない限り戻さないでください。

## Terraform

リポジトリルートから整形します。

```powershell
terraform fmt -recursive
terraform fmt -check -recursive
```

環境ごとの検証とプランです。

```powershell
Set-Location envs/dev
terraform validate
terraform plan
```

```powershell
Set-Location envs/prod
terraform validate
terraform plan
```

禁止:

```powershell
terraform apply
terraform force-unlock <LOCK_ID>
terraform plan -lock=false
terraform apply -lock=false
```

これらはユーザーの明示的な承認なしに実行しません。

## Lambda

```powershell
ruff format lambda/
ruff check lambda/
```

```powershell
Set-Location lambda
pytest
pytest <function_name>/tests/
pytest -v <function_name>/tests/
```

## Security

```powershell
trivy conf .
```

未インストールや認証不足で実行できない場合は、完了報告で `Not executed` として理由を示します。

## Terraform State Inspection

stateの確認だけが必要な場合:

```powershell
Set-Location envs/dev
terraform show
```

```powershell
Set-Location envs/prod
terraform show
```

state lock が出た場合は、Lock ID と環境を報告し、`docs/guardrails.md` に従ってください。
