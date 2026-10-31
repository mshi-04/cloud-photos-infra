# テストガイド

この文書は、LambdaとTerraform変更のテスト方針を定義します。

## Principles

- 変更した動作を直接確認するテストを優先します。
- 既存の失敗を隠すためにテストを弱めないでください。
- 外部AWSリソースはユニットテストから作成しません。
- 未実行の検証は理由付きで報告します。

## Lambda Tests

テストは `lambda/` を作業ディレクトリにして実行します。CI も同じく `pytest` を一度だけ実行します。

```powershell
Set-Location lambda
pytest
```

[lambda/pytest.ini](../lambda/pytest.ini) が `lambda/` を import の起点にします。テストは `from cloud_photos.<function_group>.<module> import ...` のように修飾付きで import するため、関数群どうしで同じ名前のモジュールがあっても衝突しません。`conftest.py` で `sys.path` を操作しないでください。

関数群を指定する場合や、詳細を表示する場合:

```powershell
Set-Location lambda
pytest cloud_photos/<function_group>/tests/
pytest -v cloud_photos/<function_group>/tests/
```

## Test Structure

```text
lambda/
  pytest.ini
  cloud_photos/
    <function_group>/
      tests/
        conftest.py
        test_<behavior>.py
```

`conftest.py` には、API Gateway event、`requestContext.identity.cognitoIdentityId` を持つ認証済みの event、環境変数、AWS mock などの共有フィクスチャを置きます。API Gateway は IAM 認証のため、event に Cognito のクレームや JWT は含まれません。

## What To Cover

- 正常系
- 認証エラー（ステータスは [lambda.md](lambda.md) の API 応答の契約に従う）
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

PRでは GitHub Actions が Terraform と Lambda の検証を実行します。Lambda では ruff、Pyright、pytest と、ビルドした ZIP から各 handler を読み込む検証を実行します。ローカルで全てを再現できない場合でも、実行できた範囲と未実行理由を明確にしてください。
