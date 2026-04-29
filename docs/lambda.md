# Lambda 実装ガイド

この文書は、`lambda/` 配下の Python Lambda を変更する際の実装規約です。

## Layout

標準的な関数ディレクトリは次の形に揃えます。

```text
lambda/
  <function_name>/
    <function_name>.py
    auth.py
    response.py
    constants.py
    tests/
      conftest.py
      test_<behavior>.py
```

既存関数の構成が異なる場合は、周辺の実装パターンを優先します。

## Handler Design

- `lambda_handler` は入力の受け渡しと最終レスポンスに留めます。
- 認証、バリデーション、永続化、外部呼び出しを関数単位に分離します。
- API Gateway event の欠落値や不正JSONを明示的に扱います。
- 既存のレスポンス契約を黙って変更しないでください。

## Authentication

- API系Lambdaは `auth.py` の既存パターンで Cognito JWT を検証します。
- 認証済みユーザーのリソース境界を確認します。
- Identity ID や user sub を使う場合は、S3 prefix や DynamoDB key の境界を崩さないでください。

## AWS Calls

- `boto3` クライアントは再利用しやすい形にします。
- AWS例外はユーザー向けレスポンスと内部ログを分けて扱います。
- リトライ、重複実行、部分失敗が問題になる処理では冪等性を確認します。

## Logging

- PII、生トークン、認証情報をログに出さないでください。
- 必要な識別子はマスクします。
- エラー時は request id、操作名、失敗理由を最小限記録します。

## Tests

動作を変更したらテストを追加または更新します。

```powershell
ruff format lambda/
ruff check lambda/
Set-Location lambda
pytest <function_name>/tests/
```

AWS呼び出しはモックし、実リソースを作成しないでください。
