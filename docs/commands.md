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

規約は tflint で確かめます。設定は [.tflint.hcl](../.tflint.hcl) で、tflint に同梱された terraform ルールセットだけを使うため、プラグインの取得や AWS の認証情報は要りません。CI と同じ v0.58.0 を使ってください。

```powershell
tflint --recursive --config "$PWD/.tflint.hcl"
```

`media_api` の method、integration、レスポンス、Gateway Response が、API の再デプロイの判定にすべて含まれているかと、`local.api_routes` と `local.cors_preflights` の key が重ならないかを確かめます。CI も同じスクリプトを実行します。

```powershell
python scripts/check_api_deployment_inputs.py
```

`bootstrap` の PassRole の対象の関数名が、`media_api` の関数と一致しているかを確かめます。CI も同じスクリプトを実行します。

```powershell
python scripts/check_lambda_role_names.py
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

ruff と Pyright、Pyright が使う boto3 の型スタブ（`boto3-stubs`）は、[lambda/requirements-dev.txt](../lambda/requirements-dev.txt) で CI と同じバージョンに固定しています。pytest と moto は互換リリース指定（`~=`）のため、入るバージョンが CI と異なる場合があります。仮想環境を有効にしてから、依存を入れてください。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r lambda/requirements-dev.txt
```

リポジトリルートで、lint、整形、型検査を実行します。ルールと型検査の厳しさは [pyproject.toml](../pyproject.toml) で設定しています。

```powershell
ruff check lambda/ scripts/
ruff format --check lambda/ scripts/
pyright
```

整形を適用する場合は `ruff format lambda/ scripts/` を実行します。`pyright` は、有効にした仮想環境の Python と依存を使って import を解決します。

テストは `lambda/` で実行します。全体を一度に実行でき、関数群を指定して実行することもできます。

```powershell
Push-Location lambda
pytest
pytest cloud_photos/<function_group>/tests/
pytest -v cloud_photos/<function_group>/tests/
Pop-Location
```

### Lambda の ZIP

リポジトリルートで、関数群ごとの ZIP を `.build/` に作ります。同じソースからは、同じハッシュの ZIP ができます。

```powershell
python scripts/build_lambda.py
```

Firebase のレイヤーの ZIP（`.build/firebase_admin_layer.zip`）も作る場合は `--with-layers` を付けます。CI と CD と同じく、タグとダイジェストを固定した AWS SAM のビルドイメージで依存を入れるため、Docker が必要です。依存はバイトコードにせず、ZIP の時刻と権限も固定するため、同じ依存の定義からは同じハッシュの ZIP ができます。

```powershell
python scripts/build_lambda.py --with-layers
```

Docker を使えない場合は、`pip install --target` で入れたディレクトリを `--layer-from` に渡してレイヤーの ZIP を作れます。ビルドイメージと pip のバージョンが違うため、CD が作る ZIP とハッシュは一致しません。

```powershell
python -m pip install --no-compile --target "$env:TEMP\firebase-layer" -r lambda/layers/firebase_admin/requirements.txt
python scripts/build_lambda.py --layer-from "firebase_admin=$env:TEMP\firebase-layer"
```

ZIP から各 handler を読み込めるかを確かめます。検証は、ソースツリーや開発環境の依存を使わない別のプロセスで行います。boto3 は Lambda ランタイムと同じく ZIP の外から読み込むため、`.build/` の外に入れます。`push_notification` には Firebase のレイヤーが必要です。

```powershell
python -m pip install --target "$env:TEMP\lambda-runtime-deps" boto3
python scripts/verify_lambda_packages.py --runtime-deps "$env:TEMP\lambda-runtime-deps" --layer push_notification=.build/firebase_admin_layer.zip
```

レイヤーは、Lambda と同じく `python/` と `python/lib/python3.12/site-packages/` から読み込みます。`python/` がないレイヤーは検証に失敗します。CI は、CD と同じく `--with-layers` で作ったレイヤーの ZIP で確かめます。あわせて、ZIP を2回作ってハッシュが一致することも確かめます。

### Firebase のレイヤーの依存

[lambda/layers/firebase_admin/requirements.txt](../lambda/layers/firebase_admin/requirements.txt) は、`firebase-admin` と、その依存をすべてバージョン固定で並べます。依存まで固定するのは、同じ定義から同じレイヤーを作り、plan に不要な差分を出さないためです。[lambda/requirements-dev.txt](../lambda/requirements-dev.txt) はこのファイルを読み込むため、テストもレイヤーと同じバージョンを使います。

`firebase-admin` を更新する場合は、Lambda と同じ Linux の Python 3.12 環境（WSL など）で、空の仮想環境に新しいバージョンを入れ、`pip freeze` の出力で依存の行を置き換えます。Windows で解決すると、プラットフォームによって依存が変わる場合があります。ファイル先頭のコメントと `firebase-admin` の行は残してください。

```bash
python3.12 -m venv /tmp/layer-lock
/tmp/layer-lock/bin/pip install firebase-admin==<version>
/tmp/layer-lock/bin/pip freeze
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
