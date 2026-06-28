---
name: auth-implementation
description: 認証・認可（Cognito Identity 抽出、IDOR防止、統一HTTPレスポンス）の設計・実装・修正に使う。未認証時の403、所有者境界チェック、response.py パターンを提供。
---

# Auth Implementation

## 実装手順

1. 前提を確認する: API Gateway の `authorization = "AWS_IAM"` が署名検証済みで、Lambda は `requestContext.identity.cognitoIdentityId` を信頼する（JWT を自前検証しない）。
2. handler 冒頭で `get_identity_id(event)` を取り、無ければ `error(HTTPStatus.FORBIDDEN, "Unauthorized")` を返す。
3. 認証 ≠ 認可。リソース操作前に所有者境界を必ず確認する: S3 は `private/<identity_id>/` プレフィックス一致、DynamoDB は Key の HASH に `identity_id`、ページネーションは `lastEvaluatedKey.userId == identity_id`。
4. 境界違反は `AuthorizationError` → 403 に変換する（`models.py` / `get_upload_records.py` パターン）。
5. レスポンスは `response.py` の `success` / `error` のみ。ステータスは 未認証/IDOR=403、検証/不正JSON=400、不在=404、内部=500。新規実装は未認証=403 に揃える（`delete_user.py` は 401 だが踏襲しない）。
6. ログのユーザー識別子は `mask_identity` を通す。PII・生トークン・認証情報を出さない。

## 検証手順

1. `Set-Location lambda; pytest <function_group>/tests/test_auth.py`
2. `Set-Location lambda; pytest <function_group>/tests`（identity 有無・IDOR ケースを含める）

## 参考資料

- [docs/security.md](../../../docs/security.md)
- [docs/lambda.md](../../../docs/lambda.md)
