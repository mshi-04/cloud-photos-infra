# pytest フィクスチャとテンプレート

`lambda/cloud_photos/<function_group>/tests/` に置く conftest とテストの実装です。

## 実行前提

[lambda/pytest.ini](../../../../lambda/pytest.ini) は次のとおりです。

```ini
[pytest]
addopts = --import-mode=importlib
pythonpath = .
testpaths = cloud_photos
```

`pythonpath = .` で `lambda/` を import の起点にします。テストは `lambda/` を作業ディレクトリにして実行します。
全体を一度に実行でき、関数グループを指定することもできます。

```powershell
Set-Location lambda
pytest
pytest cloud_photos/<function_group>/tests
```

## import

テストも本番コードと同じく修飾付きで import します。`conftest.py` で `sys.path` を操作しません。

```python
from cloud_photos.media_uploads import db
from cloud_photos.media_uploads.create_upload_record import handler
```

## conftest（単一テーブル）

### media_uploads

```python
@pytest.fixture
def dynamodb_table(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    with mock_aws():
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

        # Recreate the cached client and table name inside the moto mock.
        db.get_dynamodb_client.cache_clear()
        db.get_table_name.cache_clear()

        yield client

        db.get_dynamodb_client.cache_clear()
        db.get_table_name.cache_clear()
```

### device_tokens

`media_uploads` と同じ形で、RANGE key だけが `deviceToken` です。`KeySchema` と
`AttributeDefinitions` の `mediaId` を `deviceToken` に置き換えます。`mediaId` の定義を流用しません。

`db.py` はクライアントとテーブル名を `functools.cache` でキャッシュします。
`cache_clear()` を `yield` の前後で呼ばないと、前のテストのキャッシュや実 AWS を向きます。
環境変数は `monkeypatch.setenv` で設定し、テストの終了時に元へ戻します。
値オブジェクト（`models.py`）は、AWS のモックを使わずに `test_models.py` で直接テストします。

`db.py` を持たない `users/delete_user.py` は、そのモジュールの `get_s3_client.cache_clear()` と `get_dynamodb_client.cache_clear()` を呼びます。

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
    monkeypatch.setattr(notify_upload_complete, "get_firebase_app", MagicMock())
```

初期化の失敗を確かめるテストは、`real_firebase_init` fixture で本物の `fcm.get_firebase_app` に戻し、
`functools.cache` のキャッシュを前後で `cache_clear()` します。環境変数は `monkeypatch.setenv` で設定し、自動で元に戻します。

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

値オブジェクトは AWS のモックを使わずに直接テストします。handler のテストでは次を確かめます。


| ケース | 期待 |
|---|---|
| 正常系 | 200 / 201 と本文の内容 |
| identity 無し | [docs/lambda.md](../../../../docs/lambda.md) の API 応答の契約のとおり（新規は 403、既存の `users` / `push_notification` は 401） |
| IDOR（他人の path / `lastEvaluatedKey`） | 403 |
| 必須欠落 | 400 |
| 不正 JSON・型不正・列挙外 | 400 |
| 対象なし（条件式失敗） | 404 |
| AWS 呼び出し失敗 | 500 |
| 想定外の例外（環境変数の欠落など） | handler から送出される（`pytest.raises`）。`delete_user` は、保存先ごとの削除の中の例外を 500 にする |
| 冪等性（二重実行） | `create_upload_record` は 200 skipped |

AWS 失敗は、moto のテーブルを削除するか、`unittest.mock` の `side_effect` でクライアントメソッドを差し替えて再現します。
実リソースは作りません。

既存の失敗を隠す方向にテストを緩めないでください。

## 参考資料

- [docs/testing.md](../../../../docs/testing.md)
- [docs/lambda.md](../../../../docs/lambda.md)
