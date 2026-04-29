# テストガイド

この文書は、LambdaとTerraform変更のテスト方針を定義します。

## Principles

- 変更した動作を直接確認するテストを優先します。
- 既存の失敗を隠すためにテストを弱めないでください。
- 外部AWSリソースはユニットテストから作成しません。
- 未実行の検証は理由付きで報告します。

## Lambda Tests

テストは `lambda/` を基準に実行します。

```powershell
Set-Location lambda
pytest
```

対象を絞る場合:

```powershell
Set-Location lambda
pytest <function_name>/tests/
pytest -v <function_name>/tests/
```

## Test Structure

```text
lambda/
  <function_name>/
    tests/
      conftest.py
      test_<behavior>.py
```

`conftest.py` には API Gateway event、Cognito claims、環境変数、AWS mock などの共有フィクスチャを置きます。

## What To Cover

- 正常系
- 認証エラー
- 必須パラメータ不足
- 不正JSONや不正型
- AWS呼び出し失敗
- ユーザー境界や所有者チェック
- レスポンス形式とステータスコード

## Mocking

- `unittest.mock` または既存のpytest fixtureを使います。
- `boto3` 呼び出しはモックします。
- 現実のAWS認証情報に依存するユニットテストを書かないでください。

## Terraform Validation

Terraform変更では、テストの代わりに次の検証を実行します。

```powershell
terraform fmt -recursive
Set-Location envs/dev
terraform validate
terraform plan
```

prodに影響する場合は `envs/prod` でも確認します。state lock や認証不足で実行できない場合は、`docs/verification_policy.md` のステータスで報告してください。

## CI Expectations

PRでは GitHub Actions が Terraform と Lambda の検証を実行します。ローカルで全てを再現できない場合でも、実行できた範囲と未実行理由を明確にしてください。
