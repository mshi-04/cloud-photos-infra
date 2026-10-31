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

ruff と Pyright は、[lambda/requirements-dev.txt](../lambda/requirements-dev.txt) で CI と同じバージョンに固定しています。pytest と moto は互換リリース指定（`~=`）のため、入るバージョンが CI と異なる場合があります。仮想環境を有効にしてから、依存を入れてください。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r lambda/requirements-dev.txt
```

リポジトリルートで、lint、整形、型検査を実行します。ルールと型検査の厳しさは [pyproject.toml](../pyproject.toml) で設定しています。

```powershell
ruff check lambda/
ruff format --check lambda/
pyright
```

整形を適用する場合は `ruff format lambda/` を実行します。`pyright` は、有効にした仮想環境の Python と依存を使って import を解決します。

テストは `lambda/` で、関数群ごとに実行します。`lambda/` で `pytest` を一度に実行すると、関数群どうしの同名モジュールが衝突して失敗します。

```powershell
Set-Location lambda
pytest media_uploads/tests/
pytest device_tokens/tests/
pytest push_notification/tests/
pytest users/tests/
pytest -v <function_group>/tests/
```

## AI文書

リポジトリルートで、文書とSkillを検証します。AWSへの接続も、追加のパッケージも要りません。

```powershell
python scripts/check_ai_docs.py
```

次を確かめます。

- Markdownのコードブロックが閉じていること
- 相対リンクの参照先が存在すること。見出しへのアンカー（`#` 以降）は確かめません
- 各 `SKILL.md` のfrontmatterに `name` と `description` があり、`name` がディレクトリ名と一致すること
- 廃止したSkillの名前が参照されていないこと
- `AGENTS.md` と `CLAUDE.md`、`.agents/skills/` と `.claude/skills/` が、`.agents/` を `.claude/` に読み替えたうえで一致すること

両系統を意図して変える場合は、[scripts/ai_docs_check.toml](../scripts/ai_docs_check.toml) の許可リストに差分を書きます。Skillを廃止した場合は、同じファイルの `retired_skills` に名前を加えます。

スクリプトを変更した場合は、次も実行します。

```powershell
ruff check scripts/
ruff format --check scripts/
pyright
pytest scripts/tests/
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
