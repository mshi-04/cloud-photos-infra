# dev / prod の差分

[envs/dev/main.tf](../../../../envs/dev/main.tf) と [envs/prod/main.tf](../../../../envs/prod/main.tf) は
同じモジュールを同じ順序で呼び、変数だけが異なります。新しい変数を足すときは両方を更新します。

## モジュール引数

| モジュール | 変数 | dev | prod |
|---|---|---|---|
| `cognito` | `deletion_protection` | 既定（`INACTIVE`） | `ACTIVE` |
| `cognito` | `mfa_configuration` | 既定（`OPTIONAL`） | `ON` |
| `media_storage` | `force_destroy` | `true` | `false` |
| `media_storage` | `noncurrent_version_expiration_days` | `30` | `90` |
| `media_db` | `deletion_protection_enabled` | `false` | `true` |
| `device_token_db` | `deletion_protection_enabled` | `false` | `true` |
| `media_api` | `log_retention_in_days` | `14` | `90` |
| `media_api` | `enable_code_signing` | `false` | `false` |
| `media_api` | `cors_allow_origin` | `"*"` | `"*"` |
| provider | `default_tags.Environment` | `dev` | `prod` |

`cors_allow_origin` は prod でも `"*"` です。クライアントが Android アプリのみでブラウザ
フロントエンドが無いためで、`envs/prod/main.tf` にその旨のコメントがあります。

## モジュール側の既定値

`envs/*` が渡していない値はモジュールの `default` が効きます。

| 変数 | 既定 |
|---|---|
| `project_name` | `"cloud-photos"` |
| `lambda_memory_size` | `256` |
| `lambda_timeout` | `10` |
| `password_minimum_length` | `8` |
| `temporary_password_validity_days` | `7` |
| `code_signing_profile_version_arns` | `[]` |

`log_retention_in_days`、`cors_allow_origin`、`enable_code_signing` は既定値を持たないため、
新しい環境を足すときは必ず指定が要ります。

## 変更時のルール

- prod だけで有効にしたい設定は、モジュール内の条件分岐ではなく `envs/prod/main.tf` の変数で表現します。
- 削除保護、バージョン保持期間、ログ保持期間に関わる変更は高リスクとして扱い、
  dev の `plan` だけで判断しません。
- `envs/*/backend.tf` の bucket は `-backend-config` で渡します。ファイルに直接書きません。

## 参考資料

- [docs/infrastructure.md](../../../../docs/infrastructure.md)
- [docs/coding_standards.md](../../../../docs/coding_standards.md)
