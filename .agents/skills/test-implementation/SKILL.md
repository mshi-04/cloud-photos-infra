---
name: test-implementation
description: Lambda のテスト（pytest + moto）の追加・修正・レビューに使う。conftest フィクスチャ、Cognito identity / Firebase / DynamoDB / S3 のモック、カバーすべきケースを提供。
---

# Test Implementation

## 実装手順

1. テストは `lambda/<function_group>/tests/` に置き、クラス `Test<動作>`、メソッド `test_<シナリオ>` で命名する。
2. `conftest.py` で moto（`mock_aws`）により DynamoDB / S3 をモックし、`sys.path` に function group ルートを追加する。テンプレは `media_uploads`（単一テーブル）/ `users`（S3 + DynamoDB×2）/ `push_notification`（Firebase autouse モック）を参照する。
3. テーブル作成後に `db._reset_for_testing()` を呼び、キャッシュ済みクライアントをモックへ差し替える（呼ばないと実 AWS を向く）。
4. API Gateway event は `requestContext.identity.cognitoIdentityId` を組み立てる。
5. handler テストは最低限を網羅する: 正常系 / 未認証(403) / IDOR(403) / 必須欠落(400) / 不正JSON・型・列挙(400) / AWS 呼び出し失敗(500、`side_effect`) / レスポンス形式。
6. 既存の失敗を隠すためにテストを弱めない。

## 検証手順

1. `Set-Location lambda; pytest`（全体）または `pytest <function_group>/tests`
2. `Set-Location lambda; ruff format .; ruff check .`

## 参考資料

- [docs/testing.md](../../../docs/testing.md)
- [docs/lambda.md](../../../docs/lambda.md)
