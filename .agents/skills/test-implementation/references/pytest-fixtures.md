# pytest フィクスチャとテンプレート

`lambda/<function_group>/tests/` に置く conftest とテストの実装です。

## 実行前提

[lambda/pytest.ini](../../../../lambda/pytest.ini) は次の 1 行だけです。

```ini
addopts = --import-mode=importlib --override-ini="pythonpath="
```

`pythonpath` を空にしているため、import path は各 `conftest.py` の `sys.path.insert` が作ります。
テストは必ず `lambda/` を作業ディレクトリにして実行します。

```powershell
Set-Location lambda
pytest
```

## sys.path

| 関数グループ | 追加するパス |
|---|---|
| `media_uploads` / `users` | 関数グループのルートのみ |
| `device_tokens` / `push_notification` | 関数グループのルート + `lambda/`（`common/` を import するため） |

```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
```

`auth.py` が `from common.auth import ...` を使うグループでは 2 行目が必須です。

## conftest（単一テーブル）

### media_uploads

```python
@pytest.fixture
def dynamodb_table():
    with mock_aws():
        os.environ["AWS_DEFAULT_REGION"] = REGION
        os.environ["TABLE_NAME"] = TABLE_NAME

        client = boto3.client("dynamodb", region_name=REGION)
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "mediaId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "mediaId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        db._reset_for_testing()

        yield client

        db._reset_for_testing()
        del os.environ["TABLE_NAME"]
        del os.environ["AWS_DEFAULT_REGION"]
```

### device_tokens

`device_tokens` は RANGE key が `deviceToken` です。`mediaId` の定義を流用しません。

```python
@pytest.fixture
def dynamodb_table():
    with mock_aws():
        os.environ["AWS_DEFAULT_REGION"] = REGION
        os.environ["TABLE_NAME"] = TABLE_NAME

        client = boto3.client("dynamodb", region_name=REGION)
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "deviceToken", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "deviceToken", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        db._reset_for_testing()

        yield client

        db._reset_for_testing()
        del os.environ["TABLE_NAME"]
        del os.environ["AWS_DEFAULT_REGION"]
```

`db.py` はクライアントとテーブル名をモジュールスコープにキャッシュします。
`_reset_for_testing()` を `yield` の前後で呼ばないと、前のテストのキャッシュや実 AWS を向きます。

`db.py` を持たない関数（`users/delete_user.py`）は、そのモジュールの `_reset_for_testing()` を呼びます。

## conftest（S3 + 複数テーブル）

`users` の形です。バージョニングまで再現します。`delete_user.py` が
`list_object_versions` と `DeleteMarkers` を扱うため、これが無いとテストになりません。

```python
s3.create_bucket(Bucket=S3_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": REGION})
s3.put_bucket_versioning(Bucket=S3_BUCKET_NAME, VersioningConfiguration={"Status": "Enabled"})
```

環境変数は `S3_BUCKET_NAME` / `UPLOAD_RECORDS_TABLE_NAME` / `DEVICE_TOKENS_TABLE_NAME` の 3 つです。

## conftest（外部 SDK）

`push_notification` は Firebase 初期化を `autouse` で潰します。Secrets Manager 呼び出しごと回避されます。

```python
@pytest.fixture(autouse=True)
def mock_firebase(monkeypatch):
    import notify_upload_complete

    monkeypatch.setattr(notify_upload_complete, "_firebase_app", MagicMock())
```

環境変数の退避と復元も行います（`os.environ.get` で元の値を保持し、`yield` 後に戻す）。
他のテストと同じプロセスで環境変数が衝突する場合はこの形にします。

## event のひな形

テストファイル側にローカルヘルパーを置きます。

```python
IDENTITY_ID = "ap-northeast-1:test-user-id"


def _make_event(body=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "body": json.dumps(body) if body is not None else None,
    }
```

未認証は `{"requestContext": {"identity": {}}}` を渡します。
パスパラメータが要る handler は `"pathParameters": {"mediaId": ...}` を足します。
クエリは `"queryStringParameters"` です。

## 命名

```python
@mock_aws
class TestCreateUploadRecord:
    def test_create_success(self, dynamodb_table): ...
    def test_unauthorized_no_identity(self, dynamodb_table): ...
    def test_idor_prevention(self, dynamodb_table): ...
```

クラスは `Test<動作>`、メソッドは `test_<シナリオ>` です。

## カバーするケース

| ケース | 期待 |
|---|---|
| 正常系 | 200 / 201 と本文の内容 |
| identity 無し | 403（`users` / `push_notification` の既存は 401） |
| IDOR（他人の path / `lastEvaluatedKey`） | 403 |
| 必須欠落 | 400 |
| 不正 JSON・型不正・列挙外 | 400 |
| 対象なし（条件式失敗） | 404 |
| AWS 呼び出し失敗 | 500 |
| 冪等性（二重実行） | `create_upload_record` は 200 skipped |

AWS 失敗は `unittest.mock` の `side_effect` でクライアントメソッドを差し替えて再現します。
実リソースは作りません。

既存の失敗を隠す方向にテストを緩めないでください。

## 参考資料

- [docs/testing.md](../../../../docs/testing.md)
- [docs/lambda.md](../../../../docs/lambda.md)
