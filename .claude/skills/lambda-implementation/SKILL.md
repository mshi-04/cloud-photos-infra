---
name: lambda-implementation
description: Lambda（Python）の API の追加、handler の修正、認証・認可（Identity ID と所有者確認）、DynamoDB のアクセス、テストだけの変更に使う。handler の骨格、所有者境界、DynamoDB のアクセスパターン、pytest と moto の fixture を提供する。Terraform の配線や IAM を変える場合は infra-implementation も使う。
---

# Lambda Implementation

`lambda/` の Python コードを変える作業に使う。テストだけを追加・修正する作業も対象にする。

## 作業の選び方

作業に必要な資料だけを読む。

| 作業 | 読む資料 |
|---|---|
| handler を追加・修正する | [handler-patterns.md](references/handler-patterns.md) |
| 関数やファイルを追加する、関数群の構成を変える | [function-layout.md](references/function-layout.md) |
| Identity ID、S3 のパス、ページングキーなど、認証と所有者確認に触れる | [identity-boundaries.md](references/identity-boundaries.md) |
| DynamoDB の読み書きを追加・変更する | [dynamodb-access-patterns.md](references/dynamodb-access-patterns.md) |
| テストを追加・修正する | [pytest-fixtures.md](references/pytest-fixtures.md) |
| Terraform の配線、IAM、API Gateway を変える | infra-implementation Skill |

API 応答のステータスと本文の形式は、[docs/lambda.md](../../../docs/lambda.md) の API 応答の契約が正本。信頼の境界、IDOR、ログの要件は [docs/security.md](../../../docs/security.md) に従う。

## 実装手順

1. 変更する関数群と handler を特定し、近い既存の実装を読む。
2. 新しく受け取る入力や概念は、値オブジェクト（`@dataclass(frozen=True, slots=True)`）で表し、検証を `__post_init__` に置く。既存の `models.py` の `from_dict` を直す場合は、変更する範囲だけを規約に合わせる。
3. handler は、認証、本文の解析、入力の検証、所有者確認、永続化、応答の順に組む。前提条件はガード節で先に返し、`return` の後に `else` を書かない。
4. Identity ID は `auth.py` の `get_identity_id` で取り出す。所有者確認は永続化より前に行い、クライアントから来たパスやページングキーをそのまま key に使わない。
5. DynamoDB の値は `serialize_item` と `deserialize_item` を通し、フィールド名は `constants.py` から取る。条件式の失敗は、操作ごとに応答の意味を決める。
6. ログの識別子は `mask_identity` を通す。生のトークン、リクエストの本文、認証情報を出さない。
7. 動作を変えたら、テストを追加・更新する。未認証、IDOR、入力の不正、AWS 呼び出しの失敗を含める。既存の失敗を隠すためにテストを弱めない。

書き方の詳細は [docs/coding_standards.md](../../../docs/coding_standards.md) の Python の原則と例に従う。

## 判断が必要な場面

- **未認証の応答:** 新しい API は 403 にする。既存の `users` と `push_notification` の 401 を変える場合は、API 互換性の変更としてユーザーに確認する。
- **既存の書き方と規約の衝突:** `global` 文によるクライアントのキャッシュなど、同じモジュールの既存の仕組みと組み合わせる場合は、[docs/coding_standards.md](../../../docs/coding_standards.md) の「既存コードとの関係」に従う。
- **新しい AWS アクション:** IAM ポリシーの追加が必要になる。infra-implementation Skill で、アクションと ARN を限定して追加する。
- **新しいファイル:** import は `cloud_photos.<function_group>.<module>` の修飾付きで書く。ZIP は `scripts/build_lambda.py` が import をたどって作るため、定義の更新は要らない。ZIP から handler を読み込めることを検証で確かめる。

## 検証手順

リポジトリルートで lint、整形、型検査を実行し、`lambda/` で関数群ごとにテストする。

```powershell
ruff check lambda/
ruff format --check lambda/
pyright
Set-Location lambda
pytest
```

ファイルや共有処理を追加・移動した場合は、ZIP をビルドして、各 handler を ZIP から読み込めることも確かめる（[docs/commands.md](../../../docs/commands.md) の Lambda の ZIP）。実行する範囲と報告の形式は [docs/verification_policy.md](../../../docs/verification_policy.md) に従う。

## 参考資料

- [docs/lambda.md](../../../docs/lambda.md): 関数群の構成、handler の責務、API 応答の契約
- [docs/security.md](../../../docs/security.md): 信頼の境界、IDOR、ログ
- [docs/coding_standards.md](../../../docs/coding_standards.md): Python の原則と例
- [docs/testing.md](../../../docs/testing.md): テストの配置とモックの方針
