# インフラ構成管理

この文書は、AWSリソースとTerraformモジュールを変更する際の実装手順です。

## Layout

| パス | 役割 |
|---|---|
| `envs/dev` | dev環境のルートモジュール |
| `envs/prod` | prod環境のルートモジュール |
| `modules/` | 再利用可能なTerraformモジュール |
| `bootstrap/` | Terraform backend、OIDC、初期IAMなどの手動セットアップ領域 |
| `.github/workflows/` | plan、apply、CI/CDのワークフロー |

## Adding A Resource

1. 既存モジュールで表現できるか確認します。
2. 新規モジュールが必要な場合は `modules/<resource_name>/` を作成します。
3. `main.tf`、`variables.tf`、`outputs.tf` を用意します。
4. `envs/dev` と `envs/prod` から呼び出します。
5. 環境差分はモジュール引数で渡します。
6. IAMやCIロールに追加権限が必要か確認します。
7. `terraform fmt -recursive` を実行します。
8. 影響環境で `terraform validate` と `terraform plan` を実行します。

IAM権限を広げる場合や `bootstrap/` の変更が必要な場合は、実装前にユーザーへ方針を提示してください。

## Modifying A Module

- module input/output の互換性を確認します。
- リソース名、for_each key、count、module path の変更は replacement や state move の可能性があります。
- `terraform plan` で destroy/replace が出た場合は、意図した変更かを明記してください。
- prodに影響する場合は devだけで判断しないでください。

## State And Backend

- state lock を迂回しないでください。
- `terraform force-unlock` は自動実行しません。
- `terraform plan -lock=false` と `terraform apply -lock=false` は使用禁止です。
- lock error は `Blocked by state lock` として環境とLock IDを報告します。

## Bootstrap

`bootstrap/` は通常のGitHub Actionsデプロイでは自動適用されません。変更が必要な場合は次を必ず記録します。

- 変更理由
- 影響するIAMロール、backend、OIDC、KMS、S3
- 手動適用が必要な順序
- 適用しない場合の制約

## CI/CD

ワークフローは `.github/workflows/` にあります。

- PRでは plan、lint、test を実行します。
- `main` マージ後、devへ自動適用されます。
- prodは手動承認を前提にします。

ワークフローを変更する場合は、認証方式、対象環境、permissions、secrets参照を確認してください。
