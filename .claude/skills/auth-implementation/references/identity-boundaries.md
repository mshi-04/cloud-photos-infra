# Identity 境界

認証情報の入り口から、リソースごとの所有者境界までの実装です。

## 信頼の前提

API Gateway のメソッドが `authorization = "AWS_IAM"` である限り、SigV4 署名は API Gateway 側で
検証済みです。Lambda は `event.requestContext.identity.cognitoIdentityId` を信頼します。
JWT を Lambda で自前検証しません。

したがって認証の実効的な境界は Terraform 側にあります。`modules/media_api/main.tf` の業務メソッドから
`authorization = "AWS_IAM"` が外れると、Lambda 側のコードを変えずに全ハンドラが無認証になります。
`authorization = "NONE"` を許すのは CORS の `OPTIONS` だけです。

## identity の取得

[lambda/common/auth.py](../../../../lambda/common/auth.py) が正本です。

```python
def get_identity_id(event: Dict[str, Any]) -> Optional[str]:
    return event.get("requestContext", {}).get("identity", {}).get("cognitoIdentityId")


def mask_identity(identity_id: Optional[str]) -> str:
    if not identity_id:
        return "***"
    return f"{identity_id[:4]}***{identity_id[-4:]}" if len(identity_id) > 8 else "***"
```

`device_tokens/auth.py` と `push_notification/auth.py` はこれを re-export します。
`media_uploads/auth.py` と `users/auth.py` は同等実装のコピーです。新規は re-export に揃えます。

## 境界チェックの実装

| リソース | 境界 | 実装箇所 |
|---|---|---|
| S3 オブジェクト | `private/<identity_id>/` プレフィックス一致 | `create_upload_record.py`（書き込み前）、`delete_user.py`（削除対象の列挙） |
| DynamoDB（upload records） | HASH key `userId` に identity_id | `get_upload_records.py`、`create_upload_record.py`、`delete_upload_record.py` |
| DynamoDB（device tokens） | HASH key `userId` に identity_id | `register_device_token.py`、`unregister_device_token.py` |
| ページネーション継続キー | `lastEvaluatedKey.userId == identity_id` | `models.GetUploadRecordsRequest.from_dict` |

クライアントから来た値を、そのまま key やパスに使わないでください。
`cloudStoragePath` と `lastEvaluatedKey` は攻撃者が自由に指定できます。

### クライアント由来のパス

```python
expected_prefix = f"{PRIVATE_PATH_PREFIX}{identity_id}/"
if not request_data.cloud_storage_path.startswith(expected_prefix):
    return error(HTTPStatus.FORBIDDEN, "cloudStoragePath does not match your identity")
```

### クライアント由来の継続キー

`models.py` は境界違反を `AuthorizationError` として投げ、handler が 403 に変換します。
検証エラー（`ValidationError` → 400）と混ぜません。

```python
if exclusive_start_key.get(FIELD_USER_ID) != identity_id:
    raise AuthorizationError("lastEvaluatedKey does not match your identity")
```

```python
except ValidationError as e:
    return error(HTTPStatus.BAD_REQUEST, str(e))
except AuthorizationError as e:
    return error(HTTPStatus.FORBIDDEN, str(e))
```

`ExclusiveStartKey` は検証済みの `identity_id` から組み直します。受け取った dict をそのまま渡しません。

## Identity Pool 側の境界

[modules/identity_pool/main.tf](../../../../modules/identity_pool/main.tf) が、クライアントへ発行する
一時認証情報の範囲を決めます。Lambda 側の境界と二重化されています。

- `allow_unauthenticated_identities = false`、`server_side_token_check = true`
- S3 は `${var.media_bucket_arn}/private/$${cognito-identity.amazonaws.com:sub}/*` に限定。
  `ListBucket` は `s3:prefix` の `Condition` 付き
- `execute-api:Invoke` は `module.media_api.api_execution_arns`（メソッドとパス単位の列挙）に限定

このポリシーで `sub` に展開されるのが、Lambda が受け取る `cognitoIdentityId` と同じ値です。
S3 プレフィックスの形を変える場合は、両方を同時に変更します。

## User Pool の設定

[modules/cognito/main.tf](../../../../modules/cognito/main.tf) で弱めてはいけない設定です。

- `generate_secret = false`（モバイルクライアントのため）
- `prevent_user_existence_errors = "ENABLED"`
- `explicit_auth_flows` は `ALLOW_USER_SRP_AUTH` と `ALLOW_REFRESH_TOKEN_AUTH` のみ。
  `ALLOW_USER_PASSWORD_AUTH` を足さない
- password policy の 4 種要求、`mfa_configuration`（prod は `ON`）、`deletion_protection`（prod は `ACTIVE`）

## 参考資料

- [docs/security.md](../../../../docs/security.md)
- [docs/lambda.md](../../../../docs/lambda.md)
