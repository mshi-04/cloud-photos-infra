---
name: db-implementation
description: DynamoDB データアクセス（Query / PutItem / UpdateItem / soft delete / BatchWrite）の設計・実装・修正に使う。db.py の共通ヘルパー、serialize/deserialize、ページネーション、最小権限IAMのパターンを提供。
---

# DB Implementation

## 実装手順

1. 変更が Query / PutItem / UpdateItem / 論理削除 / BatchWrite のどれに当たるか分ける。
2. 既存の `db.py`（`get_dynamodb_client` / `get_table_name` / `serialize_item` / `deserialize_item` / `_reset_for_testing`）とアクセス元 handler を確認する。
3. 読み書きは必ず `serialize_item` / `deserialize_item` を通す。フィールド名・キーは `constants.py`（`userId`=HASH、`mediaId`/`deviceToken`=RANGE、GSIなし）から取る。
4. アクセスパターンは既存実装を踏襲する: Query+ページネーション=`get_upload_records.py`、条件付きPut=`create_upload_record.py`、UpdateItem+`if_not_exists`=`register_device_token.py`、論理削除(`isDeleted`)=`delete_upload_record.py`、BatchWrite+指数バックオフ=`users/delete_user.py`。
5. エラーは `ClientError` で条件式失敗(404)と一般例外(500)を分け、ログは `mask_identity` を通す。
6. ページネーションキーやパスは identity 境界で所有者確認する（`auth-implementation`）。
7. アクションを増やしたら `modules/media_api/main.tf` に対応する最小権限 `aws_iam_role_policy`（`jsonencode`・アクション単位・ARN限定）を追加する。

## 検証手順

1. `Set-Location lambda; pytest <function_group>/tests`
2. `Set-Location lambda; ruff check .`
3. IAM を変えたら `infra-implementation` の検証（`terraform fmt`/`validate`/`plan`、`trivy conf .`）。

## 参考資料

- [references/dynamodb-access-patterns.md](references/dynamodb-access-patterns.md): テーブル定義、`db.py` ヘルパー、操作別の実装、Lambda ごとの IAM 対応
- [docs/infrastructure.md](../../../docs/infrastructure.md)
- [docs/security.md](../../../docs/security.md)
- [docs/coding_standards.md](../../../docs/coding_standards.md)
