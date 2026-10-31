# コーディング規約

この文書は、Terraform、Python、ドキュメントの規約の正本です。PythonとTerraformとして望ましい設計と書き方を、確かめ方とともに定めます。

## Common

- コード、変数名、関数名、コメントは英語で書いてください。
- ドキュメントは日本語で構いません。
- 変更は既存の構成、命名、ヘルパー、テスト配置に合わせてください。
- シークレット、AWSアカウントID、個人情報をコードや例に含めないでください。
- 無関係な整形やリファクタリングを混ぜないでください。

### 既存コードとの関係

既存のコードには、この規約と異なる書き方が残っています。例えば、関数群ごとに import の形式や HTTP ステータスの書き方が2通りあり、クライアントのキャッシュは `global` 文で実装されています。

- 新しく書くコードは、この規約に従います。
- 既存のコードを変更する場合は、変更する関数とリソースの範囲だけを規約に合わせます。触れない部分を書き換えないでください。
- 同じモジュールの既存の仕組みと組み合わせる必要がある場合は、既存の仕組みを優先します。例えば、`db.py` のクライアントのキャッシュとテスト用の `_reset_for_testing()` は、まとめて移行するまで既存の形を使います。

### 機械的な確認

判定できる規則は、ツールで確かめます。ツールのバージョンは [lambda/requirements-dev.txt](../lambda/requirements-dev.txt) で固定し、設定は [pyproject.toml](../pyproject.toml) に置きます。コマンドは [commands.md](commands.md) を参照してください。

| ツール | 現在の設定 | CI |
|---|---|---|
| ruff | `E4`、`E7`、`E9`、`F`（ruffの従来の既定ルール）と、`ruff format` | 実行する |
| Pyright | `standard`（`off`、`basic`、`standard`、`strict` のうち中間） | 実行する |
| terraform fmt | `terraform fmt -check -recursive` | 実行する |

以下の表の「確かめ方」に挙げたruffのルールのうち、上の表にないものと、tflintは、まだ導入していません。導入するまではレビューで確かめます。

## Python Lambda

### 原則

| 原則 | 内容 | 確かめ方 |
|---|---|---|
| 値オブジェクト | 不変条件や機密性を持つ概念を、`@dataclass(frozen=True, slots=True)` の値オブジェクトや `enum.StrEnum` で表す。対象は Identity ID、メディアID、保存パス、デバイストークン、件数、ページング位置、列挙値などとする。検証は `__post_init__` に置き、どの経路で生成しても同じ規則を適用して、生成できた値は常に正しい状態にする。`parse` などの生成メソッドは、入力の型を絞り込んでから生成に委ねる。すべてのプリミティブを包むことはしない | Pyright、レビュー |
| 規則の置き場所 | 所有者確認などの規則は、値オブジェクトのメソッドに置く。例えば、保存パスが本人のものかは保存パスの値オブジェクトが判定する | レビュー |
| 機密値 | デバイストークンなどの機密値は `__repr__` で伏せ字にし、ログへ生の値が出ることを構造的に防ぐ。既存の `mask_identity` と同じく、8文字以下の値は全体を伏せ字にする。生の値は、AWSやFCMを呼び出す直前にだけ取り出す | レビュー、テスト |
| 早期リターン | 前提条件はガード節で先に返すか送出する。`return` や `raise` の後に `else` を書かず、ネストを浅く保つ | ruffの `RET`、`SIM`、`C901` |
| handlerの責務 | `handler` は、イベントの解釈、処理の呼び出し、HTTP応答への変換だけを行う。検証と業務規則は値オブジェクトと純粋な関数に置き、AWSの呼び出しは薄い関数に分ける | レビュー |
| 例外 | 入力不正や所有者違反は専用の例外で表し、HTTP応答への変換は `handler` の1か所で行う。`except Exception` は最も外側で、記録と理由のコメントがある場合に限る | ruffの `BLE`、`TRY400` |
| 型 | Python 3.12 の書き方である `dict[str, Any]` や `X \| None` を使う。引数と戻り値に型を付け、`Any` は Lambda のイベントと応答の境界に限る | ruffの `UP`、`ANN`、Pyright |
| 状態の保持 | クライアントなどの遅延生成は、`global` 文ではなく `functools.cache` で行い、テストでは `cache_clear()` で元に戻す | ruffの `PLW0603` |
| 定数と列挙 | 意味のある数値や文字列は、`Final` を付けた名前付き定数か列挙にする | ruffの `PLR2004` |
| ログ | ロガーは `logging.getLogger(__name__)` で取得し、引数は遅延評価の形（`logger.info("... %s", value)`）で渡す。例外時は `logger.exception` を使う | ruffの `G`、`TRY400` |
| import | import はファイルの先頭に書き、関数の中で import しない | ruffの `I`、`PLC0415` |
| 命名とテスト | 名前は PEP 8 に従う。テストは pytest の書き方に揃え、値オブジェクトは AWS のモックを使わずに直接テストする | ruffの `N`、`PT` |

### 例: 値オブジェクト

```python
FULLY_MASKED_MAX_LENGTH: Final = 8


@dataclass(frozen=True, slots=True)
class DeviceToken:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValidationError("deviceToken is required")

    @classmethod
    def parse(cls, raw: object) -> Self:
        if not isinstance(raw, str):
            raise ValidationError("deviceToken is required")
        return cls(raw)

    def __repr__(self) -> str:
        if len(self.value) <= FULLY_MASKED_MAX_LENGTH:
            return "DeviceToken(***)"
        return f"DeviceToken(***{self.value[-4:]})"
```

`DeviceToken("")` のように直接生成しても `__post_init__` で拒否されます。ログに渡しても、末尾4文字より多くは出ません。

### 例: 早期リターン

悪い例です。正常系が深いネストの中にあり、`else` の後を追わないと結果が分かりません。

```python
def handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    identity_id = get_identity_id(event)
    if identity_id:
        body = parse_body(event)
        if body is not None:
            return success(HTTPStatus.CREATED, save(identity_id, body))
        else:
            return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
    else:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")
```

良い例です。前提条件をガード節で先に返し、正常系を最後に置きます。

```python
def handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    identity_id = get_identity_id(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    body = parse_body(event)
    if body is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")

    return success(HTTPStatus.CREATED, save(identity_id, body))
```

### 例: 状態の保持

```python
@functools.cache
def get_dynamodb_client() -> BaseClient:
    return boto3.client("dynamodb")
```

テストでは `get_dynamodb_client.cache_clear()` で、moto のモックに向いたクライアントを作り直します。`global` 文と、リセット用の関数を別に用意する必要がありません。

### API Behavior

- 認証は API Gateway の IAM 認証で行い、Lambda は `auth.py` の `get_identity_id` で Identity ID を取り出して所有者を確認します。Lambda で JWT は検証しません。
- レスポンスは各関数群の `response.py` の `success` と `error` で作ります。
- ステータスと本文の形式は、[lambda.md](lambda.md) の API 応答の契約に従います。
- 既存のAPI契約を変える場合は、テストとドキュメントを更新します。

### AWS Clients

- テストしやすいよう、AWS呼び出しは薄い関数に分離します。
- 外部サービス呼び出しはタイムアウト、エラー処理、ログの粒度を意識します。

### Logging

- PII、生トークン、認証情報をログに出さないでください。
- Identity ID などの識別子は既存ヘルパーでマスクします。
- ログは原因調査に必要な最小限の文脈に留めます。

## Terraform

### 原則

| 原則 | 内容 | 確かめ方 |
|---|---|---|
| モジュールの構成 | 各モジュールに `versions.tf` を置き、`required_providers` でプロバイダの取得元とバージョンの下限を宣言する。大きなモジュールは、モジュールを分けずに責務別のファイルに分ける | tflintの `terraform_required_providers`、`terraform_standard_module_structure` |
| 変数と出力 | `type` と `description` を必ず付ける。値の範囲が決まる入力には `validation`、nullを受け付けない入力には `nullable = false`、機密値には `sensitive = true` を付ける | tflintの `terraform_typed_variables`、`terraform_documented_variables`、`terraform_documented_outputs` |
| 繰り返し | 複数のリソースは安定したキーを持つ `for_each` で作り、`count` は有効と無効の切り替えだけに使う | レビュー |
| 値の導出 | 同じ文字列や計算を繰り返さず、`locals` から導出する | レビュー |
| 環境差 | モジュールの中で環境名による分岐をせず、ルートモジュールから変数で渡す。コメントアウトしたコードを残さない | レビュー |
| 未使用の宣言 | 使われていない変数、data source、localsを残さない | tflintの `terraform_unused_declarations` |
| 命名 | snake_case を使い、resource名にリソースの種別を繰り返さない。既存の名前を変える場合は `moved` ブロックを使う | tflintの `terraform_naming_convention` |
| IAM | `jsonencode()` で書き、アクションとARNを限定する | trivy、レビュー |

既存のモジュールは `required_providers` を宣言していません。新しく作るモジュールには `versions.tf` を置いてください。

### Structure

- ルートモジュールは `envs/<env>/` に置きます。
- 再利用可能なリソースは `modules/<name>/` に置きます。
- 標準構成は `main.tf`、`variables.tf`、`outputs.tf` です。新しいモジュールには `versions.tf` も置きます。
- モジュール内で `provider` ブロックを定義しないでください。
- モジュール内に環境分岐を持ち込まないでください。差異は `envs/*` から変数として渡します。

### Variables And Outputs

- 変数には `description` と `type` を付けます。
- 不正値を防げる場合は `validation` を使います。
- 他モジュールや運用で必要な値は `outputs.tf` に出します。
- 機密値を output する場合は `sensitive = true` を設定します。

### IAM

- IAMポリシーは `jsonencode()` を使って記述してください。
- `"Action": "*"` は避け、必要なアクションを列挙してください。
- `"Resource": "*"` は避け、可能な範囲でARNを限定してください。
- `Sid` は目的が分かる名前にします。

### Style

- `terraform fmt -recursive` を実行してください。
- provider-level `default_tags` を優先し、リソースごとの重複タグを避けます。
- 名前変更やモジュール移動では、resource replacement と state の移行の必要性を確認します。state の移行は、手作業の `terraform state mv` ではなく `moved` ブロックで行い、plan で移動を確認します。state の移行が必要になり得る変更は、[guardrails.md](guardrails.md) のとおり実装前に方針を提示します。

## Documentation

- 手順は実行可能なコマンドと前提条件を分けて書きます。
- 禁止事項、承認が必要な操作、検証ステータスは他文書と矛盾させないでください。
- エージェント向け入口は短くし、詳細は領域別文書へ分けます。
- 予定している構成やコマンドを、現行の手順として書かないでください。現状で失敗する手順も残さないでください。
