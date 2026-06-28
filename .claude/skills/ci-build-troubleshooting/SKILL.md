---
name: ci-build-troubleshooting
description: GitHub Actions / AWS OIDC / 静的解析・ビルドの調査・修正に使う。Terraform CI のジョブ失敗、OIDCロール権限、ruff / terraform fmt / validate / plan / trivy / pytest の失敗切り分けを提供。
---

# CI / Build Troubleshooting

## 実装手順

1. 失敗ジョブを特定する。Terraform CI（`.github/workflows/ci-terraform.yml`）は `fmt` / `lint-lambda` / `test-lambda` / `trivy` / `plan` で構成され、`plan` は前段の成功を `needs` にする。
2. `fmt` 失敗は `terraform fmt -recursive` で整形しコミットする。
3. `lint-lambda` 失敗は `Set-Location lambda; ruff check .; ruff format --check .`（差分は `ruff format .` で整形）。設定はルート `pyproject.toml`（`line-length = 130`）。
4. `test-lambda` 失敗は `Set-Location lambda; pytest <group>/tests`。よくある原因は `db._reset_for_testing()` 漏れ、環境変数（`TABLE_NAME`）未設定、conftest の `sys.path` 不足（`test-implementation`）。
5. `trivy` 失敗は `trivy conf .`（CI は `exit-code: 1`）。
6. `plan`（OIDC）失敗は assume ロール `gh-terraform-plan-dev` / `-plan-prod` と `oidc_roles.tf` の権限、SARIF アップロード用 `security-events: write` を確認する。ロール・権限変更は要承認（`infra-implementation`）。
7. state lock は `force-unlock` せず `Blocked by state lock`（環境 / Lock ID / 推定原因）で報告する。再現不可は `Not executed`（理由）で報告し成功扱いしない。

## 検証手順

1. 失敗ジョブに対応するローカルコマンド（上記）で再現・修正する。
2. `fmt` / `lint` は整形コマンドで解消しコミットする。

## 参考資料

- [docs/workflow.md](../../../docs/workflow.md)
- [docs/verification_policy.md](../../../docs/verification_policy.md)
- [docs/guardrails.md](../../../docs/guardrails.md)
