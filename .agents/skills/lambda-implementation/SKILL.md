---
name: lambda-implementation
description: Lambda 関数（handler / models / response / constants）の設計・実装・修正に使う。新規 API 関数のスキャフォールドから既存ハンドラの修正まで。認証は auth-implementation、DBアクセスは db-implementation、テストは test-implementation を参照。
---

# Lambda Implementation

## 実装手順

1. 変更が handler ロジック、models バリデーション、response、constants、Terraform 配線のどれに当たるか分ける。
2. 近い既存関数（`lambda/media_uploads/`、`lambda/device_tokens/`）の構成（`<fn>.py` / `auth.py` / `response.py` / `constants.py` / `models.py` / `db.py` / `tests/`）を確認する。
3. handler は 認証 → バリデーション → 永続化 → レスポンス の順に薄く組む。認証は `auth-implementation`、DB アクセスは `db-implementation` を参照する。
4. 入力検証は `models.py` の `@dataclass` + `from_dict` に集約し、`ValidationError` / `AuthorizationError` を投げる。フィールド名・列挙は `constants.py` に集約し直書きしない。
5. ログに PII・生トークンを出さない（`mask_identity` を使う）。引数・戻り値に型ヒントを付ける（Python 3.12）。
6. 新規関数なら `modules/media_api/main.tf` に Lambda リソース・最小権限 IAM・API Gateway method（`authorization = "AWS_IAM"`）・log group を追加する（`infra-implementation`）。
7. 動作を変えたら該当テストを追加・更新する（`test-implementation`）。

## 検証手順

1. `Set-Location lambda; ruff format .; ruff check .`
2. `Set-Location lambda; pytest <function_group>/tests`
3. 新規関数で Terraform を変えた場合は `terraform fmt -recursive` と影響環境で `terraform validate` / `terraform plan`。

## 参考資料

- [references/handler-patterns.md](references/handler-patterns.md): handler の骨格、実在ハンドラ一覧、ステータスコード、冪等性、例外処理
- [references/function-layout.md](references/function-layout.md): 関数グループの構成、`auth.py` / `response.py` の差、ZIP 配線、環境変数
- [docs/lambda.md](../../../docs/lambda.md)
- [docs/coding_standards.md](../../../docs/coding_standards.md)
- [docs/testing.md](../../../docs/testing.md)
