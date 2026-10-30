# AI文書・開発基盤リファクタリング設計

- 作成日: 2026-10-30
- 更新日: 2026-10-31。レビュー指摘の反映、コーディング規約の章の追加、型検査とlintの厳しさの決定、段階ごとの作業とブランチの追加、PRのレビュー指摘の反映
- 状態: 設計案。実装前。
- 設計の起点: `develop` の `e4dfb2d`
- 本設計書のブランチ: `feature/ai-documentation-refactoring`。各段階のブランチは第10.1節に記す

## 1. 目的と前提

AIが、変更する場所、守る契約、必要な検証、完了の判断方法を一貫して理解できるプロジェクトにする。文書の整理と、文書が説明する開発手順を支えるコード・ビルド・テストの改善を一体で設計する。

`AGENTS.md`と`CLAUDE.md`は、それぞれのツール向けの入口として独立して管理する。二重管理は許容し、共通の意味が揃っていることを第9章の差分検出で確認する。入口の統合、import化、自動同期を本設計の前提にしない。`.agents/skills/`と`.claude/skills/`についても、片方を生成物にする方式は必須としない。

必要なコード変更は対象に含める。ただし、文書に合わせるために正しい実装を変えるのではなく、現行動作、意図した要件、実装上の不具合を区別して判断する。認証方式、API互換性、データ保持、IAM権限に影響する変更は、その影響を個別に扱う。

本番運用はまだ開始していない。そのため、CI/CDの既存の失敗を解消することを本設計の前提作業にしない。ただし、検証を実行できたかと成功したかは区別して記録し、環境に接続できなくても判断できる確認手段を各段階に用意する。

本ファイルの追加段階では設計を記録するだけとし、以下のコード・文書・Skill・CI変更はまだ実施しない。

## 2. 目標

1. セキュリティやAPIの契約を、文書とSkillで別々に定義しない。
2. 通常の変更が、少数の作業単位に対応するSkillから進められる。
3. ローカルとCIが同じ方法と同じツールのバージョンで、lint、全体テスト、個別テストを実行できる。
4. テストが参照するパッケージ構成と、Lambdaへ配布するZIPの構成が一致する。
5. 配布漏れやAPI設定の反映漏れを、説明の読み落としだけに依存せず検出できる。
6. AI文書や検証設定の変更を、AWS認証が不要な検証で確認できる。
7. 移行の途中でも、AIが読む文書とSkillが、その時点のリポジトリの構成と一致している。
8. 値オブジェクトや早期リターンなど、PythonとTerraformとして望ましい書き方を規約で定め、判定できるものは機械的に確かめられる。

## 3. 現状と課題

調査時の文書・ソース・ワークフローと、レビュー時に実行したテスト・lint・CI履歴の確認を根拠とする。Terraform planと実環境への適用で確認した結果ではない。実行した内容は第12章に記録する。

| 項目 | 現状 | 設計上の判断 |
|---|---|---|
| 入口 | [AGENTS.md](AGENTS.md)と[CLAUDE.md](CLAUDE.md)は各27行で、共通文書と6種類のSkillを案内する。両者の違いはパス表記だけで、`.agents/skills/`と`.claude/skills/`は現在一致している | 独立した入口を維持し、必読事項と作業別の参照順を明確にする |
| 共通ルール | 検証、state lock、IAM、ログの要件が複数の文書・Skillへ繰り返し記載される | 各要件の正本と、参照する側を決める |
| 認証 | [Lambdaガイド](docs/lambda.md)などはLambdaでのJWT検証を指示するが、[認証Skill](.agents/skills/auth-implementation/SKILL.md)と[実装](lambda/common/auth.py)はCognito Identity IDを扱う。業務用の7メソッドはAPI GatewayのIAM認証である`AWS_IAM`を使い、`NONE`はCORSの`OPTIONS`だけである | API GatewayのIAM認証とLambdaの所有者確認を正しく説明する。JWT検証の追加は行わない |
| テスト | 文書は全体を一度に実行する手順だが、[CI](.github/workflows/ci-terraform.yml)は4つの関数群を別プロセスで実行する。関数群別の実行は成功し、一括実行は`constants`の名前衝突により収集時に失敗する | 名前空間とimportを整理し、一度の全体実行を成立させる。それまでは関数群別の実行を現行手順として記載する |
| import | [関数群のfixture](lambda/device_tokens/tests/conftest.py)が`sys.path`を変更し、`auth`、`constants`、`db`などを同名でimportする | 関数群ごとに区別できるモジュール名へ移行する |
| 配布 | [Lambda ZIP生成](modules/media_api/main.tf)はディレクトリ収録とファイル列挙が混在する。`media_uploads`のZIPは`tests/`を含み、`users`のZIPは`__pycache__/`を除外していない | 共通の配布方針と、生成物を使う読み込み検証を設ける |
| レイヤー | [Firebaseレイヤー](modules/push_notification/main.tf)のZIPは毎回ビルドされ、ZIPのハッシュで更新を判定する。同じ手順で2回ビルドするとハッシュが異なる | 成果物の生成を再現可能にする |
| 依存関係 | `firebase-admin`のバージョンが[テスト用](lambda/requirements-dev.txt)と[レイヤー用](lambda/layers/firebase_admin/requirements.txt)の2か所にある。[Dependabot](.github/dependabot.yml)のpip設定は、依存定義のない`/lambda/media_uploads`を対象にしている | バージョンを一元化するか、一致を検証する |
| Terraform | `media_api/main.tf`の1,108行にZIP生成、IAM、Lambda、API Gatewayが集まる | モジュールを維持したまま、責務別のファイルへ分ける |
| API反映 | APIの再デプロイ判定は、主にmethod/integrationのIDとCORS originを参照する | IDが変わらない設定変更も再デプロイへ反映する |
| CI対象 | AI文書と`pyproject.toml`は既存CIのパス条件に含まれない | 文書・検証設定を対象にした軽量な検証を設ける |
| CI/CDの状態 | PRのCIでは、バージョン未指定の`ruff-action`が新しいruffを使い、既定ルールの追加により`Lambda Lint`が失敗する。その結果、planジョブはスキップされる。CDは直近2回ともOIDCのロール引受けで失敗している | 本番運用前のため、解消を前提作業にしない。ruffのバージョン固定は目標3の一部として段階1で扱い、OIDCは本設計の対象外とする。planに依存する確認には、AWS不要の代替手段を用意する |
| 文書の誤り | [インフラ文書](docs/infrastructure.md)と[技術スタック](docs/tech_stack.md)はCDを「mainへのマージ後にdevへ適用」と説明するが、実際はdevelopへのpushでdev、mainへのpushでdevとprodへ適用する。ほかに、[テストガイド](docs/testing.md)の`Cognito claims`、[Lambdaガイド](docs/lambda.md)の関数ディレクトリの例、各文書の一括`pytest`の案内が現状と異なる | 段階1で修正する |
| コーディング規約 | [コーディング規約](docs/coding_standards.md)は型ヒントやruffなど一般的な項目が中心で、値オブジェクト、早期リターン、例外の扱い、型の書き方、Terraformのモジュール構成といった設計の原則がない。ruffは既定ルールのままで、型検査とtflintは使っていない | 規約に設計の原則を加え、判定できるものはruff、Pyright、tflintで確かめる。詳細は第8章 |
| コードの書き方 | 早期リターンは概ね守られており、ruffの`RET`と`SIM`の指摘は0件である。一方で、関数群ごとにimportの形式やHTTPステータスの書き方が2系統に分かれ、入力は文字列や数値のまま扱われる。検証を1つに集めた`CreateUploadRecordRequest.from_dict`は複雑度が15あり、クライアントのキャッシュは`global`文で実装されている。Terraformのモジュールは`required_providers`を宣言しておらず、`media_api`には使われていないdata sourceが2つある | 段階6と段階7で規約へ移行し、手本となる書き方を1つにする |

### 調査で確認した実装上の不足

- [通知処理](lambda/push_notification/notify_upload_complete.py)は、JSON配列・文字列・数値などをオブジェクトとして扱おうとして例外になる。`successCount`の整数判定は真偽値も受け入れ、`true`を送ると201を返して「True件のメディアをアップロードしました」と通知する。
- 同処理の端末取得はDynamoDB Queryの最初のページだけを取得し、継続キーを処理していない。1ページは最大1MBのため、影響が出るのは1ユーザーあたり数千台規模からであり、優先度は低い。
- 同処理では、DynamoDB QueryとSecrets Managerの失敗が例外のまま返る。登録解除済みトークンの削除に失敗した場合も例外のまま返り、残りの端末へは送信されない。
- [共通認証ヘルパー](lambda/common/auth.py)と[Media Uploadsの認証ヘルパー](lambda/media_uploads/auth.py)は、`requestContext`や`identity`がnullの場合に例外となる。[Usersのヘルパー](lambda/users/auth.py)とは扱いが異なる。
- UsersとPushの未認証応答は401、Media UploadsとDevice Tokensは403であり、既存テストもそれぞれを期待する。多くのSkill資料は「新規は403、既存の401は維持」と書き分けている。ただし、[認証Skill](.agents/skills/auth-implementation/SKILL.md)は401の例外を`delete_user.py`だけとしてPushを含めておらず、[テストSkill](.agents/skills/test-implementation/SKILL.md)は例外に触れずに未認証を403としている。

これらは文書整理や構造変更とは区別し、個別の動作変更としてテストとともに修正する。401と403の統一は、本リファクタリングの完了条件にしない。

## 4. 文書の責務

| 文書 | 正本として持つ内容 | 他へ委ねる内容 |
|---|---|---|
| [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) | 必読文書、作業別のSkill、参照の順序 | API仕様、詳細手順、コード例 |
| [guardrails.md](docs/guardrails.md) | 実行・承認の境界、既存変更の保護、state lock時の操作方針 | セキュリティ実装の詳細、検証コマンド |
| [verification_policy.md](docs/verification_policy.md) | 変更種別ごとの検証範囲、必須・条件付きの区別、結果ステータス | コマンドの詳細、fixtureの実装 |
| [commands.md](docs/commands.md) | コマンドの入口、作業ディレクトリ、前提条件 | 検証範囲の再定義、他文書と重複する禁止操作一覧 |
| [security.md](docs/security.md) | 認証の信頼境界、IDOR防止、IAM、シークレット、ログの要件 | 個別ハンドラの実装手順 |
| [lambda.md](docs/lambda.md) | パッケージ構成、ハンドラの責務、API応答・冪等性・エラー処理の契約 | セキュリティ要件や検証方針の再定義 |
| [infrastructure.md](docs/infrastructure.md) | 環境とモジュールの責務、配布とデプロイの構成、stateへの影響の見方 | 安全境界やコマンドの再掲 |
| [testing.md](docs/testing.md) | テストの配置、分離、AWS/外部サービスのモック、fixtureとキャッシュの扱い | HTTP仕様や共通検証範囲の再定義 |
| [coding_standards.md](docs/coding_standards.md) | PythonとTerraformの設計の原則と書き方、機械的な確認との対応、短い良い例と悪い例 | 認証方式・検証手順・安全境界の重複定義 |
| [tech_stack.md](docs/tech_stack.md) | 技術の概要と設定の参照先 | バージョン、CI、コマンドなど更新されやすい情報の並行した一覧 |
| [README.md](README.md) / [README.en.md](README.en.md) | 利用者・開発者向けの概要と開始方法 | AI固有の詳細手順 |
| [SECURITY.md](SECURITY.md) | 公開リポジトリの脆弱性報告方針 | AI向けの実装規約 |
| 本設計書 | 設計の判断、移行の順序、未決事項 | 現行の手順と契約。実装した内容は各正本へ移す |

既存の文書名を基本的に維持する。セキュリティ要件と操作の許可は区別し、共通ルールを参照する際には「いつ読むか」を示す。参考リンクの列挙だけで必読要件を表現しない。

本設計書は、入口文書から必読として参照しない。段階8の完了後、残す判断を各正本へ移し、本設計書を削除するかアーカイブする。

API契約では、正常応答、入力エラー、認証情報欠落、所有者境界違反、条件付き書き込み、冪等操作、外部サービス障害を区別する。DBの条件式失敗を一律404にするなど、操作ごとの差を消す一般化は避ける。新規APIの未認証応答は現行の規則どおり403とし、API GatewayのIAM認証が失敗したときの応答と揃える。既存のUsersとPushの401は、互換性のため維持する。

## 5. Skillの再編

両ツール向けのSkillを、次の3つの作業単位に整理する。既存の名前を利用し、目的だけのための改名は増やさない。

| Skill | 主な作業 | 必要時に読む資料 |
|---|---|---|
| `lambda-implementation` | API追加、ハンドラ修正、認証・認可ロジック、DBアクセス、テストのみの変更 | ハンドラ、認証境界、DynamoDB、fixture、配布構成 |
| `infra-implementation` | Terraform、IAM、Cognito、API Gateway、Lambda配布、環境差分 | 共通セキュリティ要件、環境差、API配線、配布手順 |
| `implementation-review` | 差分と影響範囲の確認、問題の分類、根拠付きの報告 | 変更された領域に関係する契約と実装 |

### 移行する内容

- `auth-implementation`の有用な手順と参考資料は、Lambda Skillの認証・認可資料へ移す。信頼境界や所有者確認の要件は`docs/security.md`を参照する。
- `db-implementation`のアクセスパターンと例は、Lambda SkillのDB資料へ移す。IAMの変更が必要ならInfra Skillを使う。
- `test-implementation`のfixtureとモックの資料は、Lambda Skillのテスト資料へ移す。Lambda Skillにはテストだけの変更も対象であることを明記する。
- 既存の`handler-patterns.md`、`function-layout.md`、`identity-boundaries.md`、`dynamodb-access-patterns.md`、`pytest-fixtures.md`を基に、重複や長い実装コピーを減らす。
- 認証SkillとテストSkillにある未認証応答の記述は、第4章の規則に合わせる。
- Infra Skillのリソースアドレス変更の手順は、手作業の`terraform state mv`より`moved`ブロックを優先する内容へ更新する。理由は第7.2節に記す。
- 各Skillの実装手順に、コーディング規約の要点を手順として書く。Lambda Skillには入力を値オブジェクトで受け取ることと、前提条件をガード節で返すことを、Infra Skillにはモジュールの構成と変数の書き方を書き、詳細は[coding_standards.md](docs/coding_standards.md)を参照させる。レビューSkillは規約の観点でも指摘し、根拠となる規則を示す。
- 削除予定のSkill名を参照する入口・文書・他Skillを確認し、移動先へ更新してから旧Skillを削除する。両ツールで同じ移行を行う。

`SKILL.md`は目的、作業の選び方、必要な判断、参照条件に絞る。資料をまとめて必読にせず、作業に必要な資料だけを読む。3種類に減らす狙いは、行数の削減ではなく作業の分かれ方を明確にすることにある。

レビューSkillは、このリポジトリが提供しない`review-branch`や`security-review`を必須の依存にしない。比較対象のブランチは依頼やPR情報から確認し、固定の`develop`を常に正しいと仮定しない。

### 期待する作業の対応

| 依頼例 | 主なSkillと資料 |
|---|---|
| アップロードAPIを追加する | Lambda。認証・DB・テスト資料を必要に応じて読み、Terraform配線の変更時はInfraも使う |
| 他人のページングキーを拒否する | Lambda。所有者境界とページング資料 |
| 通知処理の不足テストを追加する | Lambdaのテストのみの作業。通知契約とfixture資料 |
| Cognito設定やDynamoDB削除保護を変更する | Infra。セキュリティ契約と環境差 |
| ブランチをレビューする | Review。実際の差分に関係する契約 |
| 設計書の文言だけを修正する | 実装Skillの一律適用は不要。文書変更の検証方針に従う |

## 6. Lambda・配布・テストの設計

### 6.1 名前空間を持つパッケージ

プロジェクト固有のパッケージ名の配下に、関数群と必要な共有処理を置く。例えば`cloud_photos.media_uploads`、`cloud_photos.device_tokens`のように、どの関数群のモジュールか分かるimportを使う。`lambda`はPythonの予約語でパッケージ名に使えないため、`lambda/`はソースのルートとして扱い、その下に固有のパッケージを置く。

テストのために関数群のディレクトリを`sys.path`の先頭へ追加する構成を解消する。パッケージ名、ディレクトリの最終配置、Terraformのhandler値、ZIP内の階層は同じ変更段階で確定する。関数群の責務と既存のLambdaリソースは維持する。

API Gatewayはバージョンを指定せずにLambdaを呼び出すため、常に`$LATEST`が実行される。Lambdaのコード更新と設定更新は別々のAPI呼び出しになるので、ZIPの階層とhandlerを同時に変えると、適用の途中で短時間`Runtime.ImportModuleError`が起き得る。本番運用の開始前はこれを許容し、同時に変更してよい。本番運用の開始後に同種の変更を行う場合は、次の順に進め、各適用で変わるのをコードか設定の片方だけにする。

1. 新しいパッケージに、旧トップレベル名の薄い互換モジュールを加えたZIPを、旧handlerのまま配布する。
2. handlerを新しい値へ切り替える。
3. 互換モジュールを削除する。

### 6.2 共有処理

認証情報の抽出やJSONオブジェクトの解析など、契約が共通で状態を持たない処理は共有候補とする。値オブジェクトのうち、Identity IDやデバイストークンのように複数の関数群で使うものも共有候補とする。共通化は名前空間と配布方法を整えてから行う。

API応答は204の空bodyなどの差を保つ。DynamoDBのクライアント・テーブル名キャッシュは、関数群ごとの設定とテスト分離を考慮する。同じコードであることだけを理由にキャッシュやDBアクセスを一つの汎用層へ統合しない。

### 6.3 配布物の契約

- 本番に必要なパッケージと共有処理を、関数群ごとのZIPへ収録する。
- `tests/`、`__pycache__/`、テスト・ツールのキャッシュを配布対象から外す。
- テストと本番で同じ修飾付きimportを使う。
- ZIPの生成は、Terraformの`archive_file`からリポジトリのビルドスクリプトへ移す。スクリプトは`.build/`へZIPを出力し、Terraformは`filename`と`filebase64sha256()`で参照する。これにより、AWS認証やplanなしでZIPを生成できる。
- ビルドスクリプトは、ローカルのPowerShellとCIのbashのどちらからも同じ手順で呼べるよう、Pythonで実装する。
- ZIPは再現可能にする。エントリの順序、更新時刻、権限を固定し、同じ入力から同じハッシュを得る。Firebaseレイヤーも同じ方針とし、ビルドに使うコンテナイメージのタグを固定する。再現できない場合、planのたびにLambdaやレイヤーの差分が現れる。
- 生成したZIPを独立した場所へ展開し、リポジトリのソース検索パスに依存せず各handlerをimportできることを検証する。検証の対象は、Terraformが参照するものと同じZIPとする。
- 読み込み検証は、ZIPに入っていないモジュールをソースツリーや開発環境から解決しないよう、実行環境を隔離する。
  - 検証は、ビルドスクリプトとは別のプロセスで行う。
  - そのプロセスは`python -I -S`で起動し、作業ディレクトリを一時ディレクトリにする。これにより、`PYTHONPATH`、作業ディレクトリ、スクリプトの場所、開発用仮想環境の`site-packages`が検索パスに入らない。
  - 検索パスに加えるのは、ZIPの展開先とレイヤーの`python/`だけとする。Lambdaランタイムが同梱するboto3は、`pip install --target`で用意した専用のディレクトリから読み込む。
  - 検証が隔離できていることは、共有処理を1つ外したZIPで検証が失敗することで確かめる。
- 読み込み検証には実AWS認証情報や実サービス呼び出しを必要としない。外部ライブラリを持つ関数では、その配布レイヤーも含めて依存関係を確認する。`firebase-admin`のバージョンは、テスト用とレイヤー用で一元化するか、一致を検証する。
- ローカル、CI、CDで同じ成果物生成手順を呼ぶ。Firebaseレイヤーのビルド手順も重複させない。
- `terraform validate`とplanは、現在のレイヤーと同様に、成果物の生成後に実行する。
- 保存したplanとビルド済み成果物をapplyへ渡す既存の構成を保ち、plan後に別の成果物へ作り直さない。

### 6.4 テスト実行

移行前に、現行CIと同じ関数群別実行で基準となる結果を記録する。レビュー時点では、関数群別の実行は成功し、一括実行は収集時に失敗する。

移行後は、同じ全体実行コマンドをローカルとCIで利用でき、個別の関数群も選択できるようにする。モジュールキャッシュの掃除や実行順への依存で名前衝突を回避する方式は採用しない。[pytestの設定](lambda/pytest.ini)は現在`pythonpath`を空に上書きしているため、名前空間の導入時にソースのルートを設定で明示する。

fixtureは`monkeypatch`などで環境変数を元の状態へ戻す。MotoとFirebaseのモック、クライアントキャッシュのリセット、関数群固有のテーブル構造は維持する。テスト用のキャッシュリセットを本番コードの設計として不要に一般化しない。

### 6.5 個別の不具合修正

| 対象 | 修正する動作 | 必要な確認 |
|---|---|---|
| 通知の入力 | JSONオブジェクトではないリクエストボディと、真偽値・負数・非整数の`successCount`を400として扱う | 不正入力でDBやFCMへ進まない。既存の正常応答、401、201、204を保つ |
| 通知先の取得 | Queryの継続キーを処理し、全ページの端末を対象にする | 複数ページ、継続キー付きの空ページ、所有者条件の維持 |
| 通知処理の外部サービス障害 | DynamoDB QueryとSecrets Managerの失敗を500として扱う。登録解除済みトークンの削除に失敗しても、記録したうえで残りの端末への送信を続ける | 応答に内部情報を含めない。ログの識別子とトークンをマスクする。削除の失敗後も残りの端末へ送信される |
| identity取得 | 認証情報の欠落・nullを未認証として扱う | 関数群ごとの既存401/403契約を保ち、例外にしない |

構造変更と不具合修正は、差分と検証結果を分けて追跡できる単位にする。不具合修正は、段階1で契約を確定した後、段階6より前に、第10.12節のブランチで行う。先にテストで正しい動作を固定し、その動作を保ったまま値オブジェクトへ移す。通知基盤の非同期化など、別のアーキテクチャ変更はここへ混ぜない。

## 7. Terraformの設計

### 7.1 同一モジュール内のファイル分割

`modules/media_api/`を次の責務へ分ける。

| ファイル | 責務 |
|---|---|
| `main.tf` | 必要なデータ参照と共通定義 |
| `archives.tf` | Lambdaの配布物 |
| `iam.tf` | Lambdaごとのロールと最小権限ポリシー |
| `lambda.tf` | ロググループとLambda関数 |
| `api_gateway.tf` | API、method、integration、permission、CORS、deployment、stage |
| `variables.tf` / `outputs.tf` | 入出力の契約 |

この分割だけの段階では、モジュールパス、resource/dataの種別・名前、キーを変えない。子モジュール化や`for_each`化は同時に行わない。配布構成の変更と、ファイルを移すだけの変更は別の差分として確認する。

分割の確認は、AWSに接続せずに行えるようにする。分割前後で、トップレベルのブロックであるresource、data、locals、variable、outputの内容が一致し、配置ファイルだけが変わったことをブロック単位で比較する。あわせて`terraform init -backend=false`で初期化し、`terraform validate`を実行する。planを実行できる場合は、分割前後のplan結果が同じであることも確認する。レイヤーのビルドが再現可能になるまでは、レイヤー由来の差分を既知の差分として扱う。

### 7.2 APIの接続と再デプロイ

現行の`aws_api_gateway_deployment.media`の`triggers`は、`cors_allow_origin`のほかに、method、integration、method response、integration responseの`.id`だけを参照している。`.id`は`authorization`やintegrationの`uri`などを変えても変わらないため、これらの変更は再デプロイされない。Gateway Responseは`triggers`に含まれていない。

設定変更を確実に反映するため、deploymentの更新判定に次の設定内容を含める。値は`locals`に集めて`triggers`へ渡す。

| リソース | 含める属性 |
|---|---|
| method | `authorization` |
| integration | `type`、`integration_http_method`、`uri`、`request_templates` |
| method response、integration response | `status_code`、`response_parameters` |
| Gateway Response | `response_type`、`response_parameters` |
| モジュールの入力 | `cors_allow_origin`（現行どおり） |

これらはレビュー時点で設定している属性である。`passthrough_behavior`や`request_parameters`など、公開されたAPIの動作へ影響する属性を新しく設定する場合は、同じ差分で更新判定にも加える。

更新判定の確認は次のとおりとする。

- AWSに接続しない確認として、モジュール内のmethod、integration、method response、integration response、Gateway Responseがすべて更新判定の入力に含まれることを、ブロック単位で機械的に比較する。
- planを実行できる場合は、devで上の表の属性を種類ごとに1つずつ変えたplanを作り、deploymentが置き換えられて`triggers`の値が変わることを確かめる。属性を変えないplanでは、deploymentに差分が出ないことを確かめる。確認のための変更はコミットせずに戻す。

必要なmethod・path・実行可能ARNの関係を小さな定義にまとめ、実行可能ARNやpermissionの重複を導出できる箇所を整理する。導出するのは、実行可能ARNの文字列や更新判定の入力値などの`locals`に限り、リソースは個別の定義のまま残す。全リソースを汎用化するための抽象層や`for_each`化は導入せず、Lambdaごとの権限境界と既存のリソースアドレスを維持する。

deploymentの更新は意図した変更として扱う。それ以外の削除・置換、権限の拡張、state移行が発生する場合は、別途その必要性と影響を確認する。

将来リソースアドレスを変える場合は、手作業の`terraform state mv`ではなく`moved`ブロックを使う。CDがapplyを自動で行う構成のため、移動をplanで確認でき、CDの流れの中で適用できる方法を優先する。state移行が承認の対象であることは変わらない。

### 7.3 環境の境界

`envs/dev`と`envs/prod`、既存の用途別モジュール、独立したstateを保つ。削除保護、MFA、ログ・ストレージ保持期間などの差はルートモジュールで明示する。環境全体を一つの巨大なモジュールにまとめることは目標にしない。

## 8. コーディング規約

### 8.1 方針

規約の正本は[coding_standards.md](docs/coding_standards.md)とし、PythonとTerraformとして望ましい設計と書き方を、短い良い例と悪い例とともに定める。Skillは規約の要点を作業手順として示し、詳細は正本を参照する。

AIは周辺の既存コードを手本にするため、規約は文書だけでなくコードでも示す。現状は関数群ごとに書き方が2系統あり、どちらを真似るかが定まらない。段階6で全関数群を規約に揃え、手本となる書き方を1つにする。

機械で判定できる規則は、ruff、Pyright、tflintで確かめる。値オブジェクトの切り出し方など判定できない原則は、例とレビューの観点で伝える。規約への移行は段階6と段階7でまとめて行い、それ以外の作業では、変更する関数とリソースの範囲だけを規約に合わせる。無関係な整形やリファクタリングを混ぜないという既存の原則は維持する。

### 8.2 Python

| 原則 | 内容 | 機械的な確認 |
|---|---|---|
| 値オブジェクト | 不変条件や機密性を持つ概念を、`@dataclass(frozen=True, slots=True)`の値オブジェクトや`enum.StrEnum`で表す。対象はIdentity ID、メディアID、保存パス、デバイストークン、件数、ページング位置、列挙値などとする。検証は`__post_init__`に置き、どの経路で生成しても同じ規則を適用して、生成できた値は常に正しい状態にする。`parse`などの生成メソッドは、入力の型を絞り込んでから生成に委ねる。すべてのプリミティブを包むことはしない | Pyright、レビュー |
| 規則の置き場所 | 所有者確認などの規則は、値オブジェクトのメソッドに置く。例えば、保存パスが本人のものかは保存パスの値オブジェクトが判定する | レビュー |
| 機密値 | デバイストークンなどの機密値は`__repr__`で伏せ字にし、ログへ生の値が出ることを構造的に防ぐ。既存の`mask_identity`と同じく、8文字以下の値は全体を伏せ字にする。生の値は、AWSやFCMを呼び出す直前にだけ取り出す | レビュー、テスト |
| 早期リターン | 前提条件はガード節で先に返すか送出する。`return`や`raise`の後に`else`を書かず、ネストを浅く保つ | ruffの`RET`、`SIM`、`C901` |
| handlerの責務 | handlerは、イベントの解釈、処理の呼び出し、HTTP応答への変換だけを行う。検証と業務規則は値オブジェクトと純粋な関数に置き、AWSの呼び出しは薄い関数に分ける | レビュー |
| 例外 | 入力不正や所有者違反は専用の例外で表し、HTTP応答への変換はhandlerの1か所で行う。`except Exception`は最も外側で、記録と理由のコメントがある場合に限る | ruffの`BLE`、`TRY400` |
| 型 | Python 3.12の書き方である`dict[str, Any]`や`X \| None`を使う。引数と戻り値に型を付け、`Any`はLambdaのイベントと応答の境界に限る | ruffの`UP`、`ANN`、Pyright |
| 状態の保持 | クライアントなどの遅延生成は、`global`文ではなく`functools.cache`で行い、テストでは`cache_clear()`で元に戻す | ruffの`PLW0603` |
| 定数と列挙 | 意味のある数値や文字列は、`Final`を付けた名前付き定数か列挙にする | ruffの`PLR2004` |
| ログとimport | ロガーは`logging.getLogger(__name__)`で取得し、引数は遅延評価の形で渡す。例外時は`logger.exception`を使う。importはファイルの先頭に、パッケージ名から始まる絶対importで書く | ruffの`G`、`TRY400`、`I`、`PLC0415` |
| 命名とテスト | 名前はPEP 8に従う。テストはpytestの書き方に揃え、値オブジェクトはAWSのモックを使わずに直接テストする | ruffの`N`、`PT` |

値オブジェクトとガード節を組み合わせた例を示す。値オブジェクトは現行の検証内容と応答メッセージを保ったまま移す。

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


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    try:
        request = RegisterDeviceTokenRequest.parse(event)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    try:
        save_device_token(identity_id, request.device_token, request.platform)
    except (BotoCoreError, ClientError):
        # IdentityId masks itself in __repr__, so it is safe to log.
        logger.exception("Failed to register device token: userId=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    return success(HTTPStatus.CREATED, {"message": "registered"})
```

### 8.3 Terraform

| 原則 | 内容 | 機械的な確認 |
|---|---|---|
| モジュールの構成 | 各モジュールに`versions.tf`を置き、`required_providers`でプロバイダの取得元とバージョンの下限を宣言する。大きなモジュールは第7.1節のように責務別のファイルに分ける | tflintの`terraform_required_providers`、`terraform_standard_module_structure` |
| 変数と出力 | `type`と`description`を必ず付ける。値の範囲が決まる入力には`validation`、nullを受け付けない入力には`nullable = false`、機密値には`sensitive = true`を付ける | tflintの`terraform_typed_variables`、`terraform_documented_variables`、`terraform_documented_outputs` |
| 繰り返し | 複数のリソースは安定したキーを持つ`for_each`で作り、`count`は有効と無効の切り替えだけに使う | レビュー |
| 値の導出 | 同じ文字列や計算を繰り返さず、`locals`から導出する | レビュー |
| 環境差 | モジュールの中で環境名による分岐をせず、ルートモジュールから変数で渡す。コメントアウトしたコードを残さない | レビュー |
| 未使用の宣言 | 使われていない変数、data source、localsを残さない | tflintの`terraform_unused_declarations` |
| 命名 | snake_caseを使い、resource名にリソースの種別を繰り返さない。既存の名前を変える場合は`moved`ブロックを使う | tflintの`terraform_naming_convention` |
| IAM | `jsonencode()`で書き、アクションとARNを限定する既存の規約を維持する | trivy、レビュー |

### 8.4 機械的な確認

ruffとPyrightは、どちらも中間の厳しさで運用する。すべてのルールを有効にする強い設定は、指摘の多さに比べて得られる効果が小さいため採用しない。

- ruffは、段階1でバージョンを固定し、従来の既定ルールである`E4`、`E7`、`E9`、`F`を明示する。段階6で中間のルールに広げる。中間のルールは、既定ルールに`I`、`N`、`UP`、`B`、`SIM`、`RET`、`C4`、`C90`、`ANN`、`BLE`、`G`、`LOG`、`TRY400`、`PLC0415`、`PLW0603`、`PLR2004`、`PT`、`RUF`を加え、`ANN401`を除いたものとする。テストでは`ANN`と`PLR2004`を除く。
- レビュー時点で中間のルールを当てると、本番コードで124件、テストで11件の指摘がある。そのうち本番コードの65件とテストの9件は自動修正できる。`N`、`PT`、`RET`、`SIM`の指摘は0件である。
- returnの数を制限する`PLR0911`は採用しない。ガード節の多いhandlerと衝突するためで、現状でも`create_upload_record.handler`はreturnが7つあり、上限の6を超える。関数の複雑さは`C901`で確かめる。
- 型検査にはPyrightを使う。厳しさは、`off`、`basic`、`standard`、`strict`の4段階のうち中間の`standard`とする。`standard`はPyrightの既定値でもある。
- Pyrightは現在の構成でも動作し、同名モジュールの取り違えによる指摘は出なかった。レビュー時点の指摘は1件で、`GetUploadRecordsRequest.from_dict`は`None`を受け付けるのに、型ヒントが`None`を許していない。段階1でバージョンを固定して導入し、段階5でimportを書き換える際の安全網にする。
- boto3のクライアントは、型スタブがないと型が付かず検査されない。段階6で`boto3-stubs`のDynamoDB・S3・Secrets Manager用を開発用の依存に加える。加えた場合の新たな指摘は、`delete_user.py`で省略可能なキーを直接参照している4件である。参考として、型スタブを加えた状態で`strict`にすると883件になる。
- Terraformは、`terraform fmt`と`validate`に加えてtflintを段階7で導入する。tflintの静的検査はAWS認証を必要としないため、AWS不要の検証に含める。

段階6が終わった時点の`pyproject.toml`は次の形になる。ruffとPyrightのバージョンは、ローカル用の依存定義とCIで同じ値に固定する。

```toml
[tool.ruff]
line-length = 130

[tool.ruff.lint]
select = [
    "E4", "E7", "E9", "F",
    "I", "N", "UP", "B", "SIM", "RET", "C4", "C90", "ANN", "BLE", "G", "LOG",
    "TRY400", "PLC0415", "PLW0603", "PLR2004", "PT", "RUF",
]
ignore = ["ANN401"]

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["ANN", "PLR2004"]

[tool.pyright]
include = ["lambda"]
pythonVersion = "3.12"
typeCheckingMode = "standard"
```

## 9. CIと検証の設計

検証を、AWS接続が不要なものと、環境に接続するものに分ける。

| 対象 | 主な検証 |
|---|---|
| AI文書 | Markdown、相対リンク、Skill frontmatter、移動したSkill参照の残存、両系統の差分 |
| Pythonと検証設定 | バージョンを固定したruffとPyright、全体テスト、個別テスト、配布物の生成と読み込み |
| Terraform | format、validate、tflint、影響環境のplan、権限と差分のレビュー |
| セキュリティに関係するIaC | 共通ポリシーに沿ったスキャンと、実行可否・未実施理由の報告 |

文書や`pyproject.toml`の変更が対応する検証を起動するようにする。文書だけの変更にAWS接続やTerraform planを要求しない。既存のTerraform CIは起動するとplanジョブまで実行する構成のため、そのパス条件に文書を加えるのではなく、文書の検証は別のワークフローにする。`pyproject.toml`の変更ではruffを起動し、planは要求しない。ブランチ保護で必須にするチェックは、パス条件で起動しなかったPRで待機のまま残らない構成にする。例えば、ワークフローは常に起動し、対象パスはジョブの中で判定する。

ruffは、ローカル用の依存定義とCIの`ruff-action`で同じバージョンに固定し、有効にするルールを`pyproject.toml`の`[tool.ruff.lint] select`で明示する。バージョン未指定のままでは、ruffの更新で既定ルールが変わり、ローカルとCIの結果がずれる。Pyrightも同じくバージョンを固定する。ルールを広げる順序は第8.4節に従う。

両系統の入口とSkillは、それぞれ構文と参照先を確認する。そのうえで、生成や同期は行わず、差分を検出するチェックで意味の一致を確認する。`AGENTS.md`と`CLAUDE.md`、`.agents/skills/`と`.claude/skills/`を、パス表記の`.agents`と`.claude`を揃えて比較し、意図した差分だけを許可リストで認める。byte単位の一致は必須にしない。

Skillの構文やリンクの検証と、AIが適切なSkillを選び必要な資料を読むかの確認は別に扱う。前者の成功を、後者の成功として報告しない。後者は第5章の依頼例などを使い、独立したセッションで選択・参照・検証範囲を観察する。未実施なら未実施と明示する。

planの結果を判断に使う場合は、CIのPRコメントの切り詰めに注意する。コメントは60,000文字で切り詰められ、末尾の`Plan:`サマリが失われることがある。[PR 52](https://github.com/mshi-04/cloud-photos-infra/pull/52)のplanコメントで実際に起きている。サマリはコメントの先頭か、ジョブのstep summaryに出す。

## 10. 実施順序とブランチ

### 10.1 全体の流れ

| 段階 | ブランチ | 目的 | 前提 |
|---|---|---|---|
| 0. 基準の記録 | `feature/ai-refactor-0-baseline` | 構造変更前の結果と既知の失敗を記録する | 本設計書の`develop`への取り込み |
| 1. 契約と規約の確定 | `feature/ai-refactor-1-contracts-and-standards` | 文書間の矛盾を解消し、規約とツールのバージョンを固定する | 段階0 |
| 2. 文書の静的検証 | `feature/ai-refactor-2-docs-checks` | 文書とSkillを、AWSに接続せずに検証できるようにする | 段階1 |
| 3. Skillの再編 | `feature/ai-refactor-3-skills` | Skillを3つの作業単位に揃える | 段階2 |
| 4. Terraformのファイル分割 | `feature/ai-refactor-4-media-api-split` | `media_api`を責務別のファイルへ移す | 段階1。段階2・3と並行してよい |
| 5. Lambda基盤 | `feature/ai-refactor-5-lambda-packages` | 名前空間、import、ZIPのビルドを整える | 段階3と段階4 |
| 6. Lambdaの規約への移行 | `feature/ai-refactor-6-lambda-standards` | Lambdaの書き方を規約に揃える | 段階5と、第10.12節の不具合修正 |
| 7. Terraformの改善 | `feature/ai-refactor-7-terraform-improvements` | API反映、成果物の再現性、Terraformの規約を整える | 段階5。段階6と並行してよい |
| 8. Skill選択の評価 | `feature/ai-refactor-8-skill-evaluation` | AIが適切なSkillを選び、必要な資料を読むかを評価する | 段階6と段階7 |

各段階を独立してレビューできる変更単位にする。文書の静的検証とSkillの再編をLambda基盤より先に行うのは、構造変更を実装するAIが、移行後の作業単位と最新の参照先を使えるようにするためである。ファイル分割をLambda基盤より先に行うのは、Lambda基盤で変更する配布物とLambdaの定義を先に責務別のファイルへ移し、移動だけの差分を単独で確認するためである。構造の変更である段階5と、書き方の変更である段階6を分けるのは、性質の異なる差分を別々にレビューするためである。段階6では、handlerのテストが期待値を変えずに成功することで、動作が変わっていないことを確かめる。Pyrightを段階1で導入するのは、段階5でimportを書き換える際に、解決できないimportや存在しない属性の参照を機械的に見つけるためである。

新しい配置やコマンドは、利用可能になった段階で文書とSkillへ反映し、設計上の予定を現行手順として記載しない。現状で失敗する手順も、現行手順として残さない。

実装時の承認・state lock・シークレットの扱いは、引き続き[guardrails.md](docs/guardrails.md)に従う。検証結果は[verification_policy.md](docs/verification_policy.md)の4つのステータスで報告する。planなど環境に接続する検証を実行できない場合は、`Not executed`として理由を記録し、AWS不要の確認の結果と区別する。

### 10.2 ブランチの運用

- 各段階のブランチは`develop`から作り、`develop`へのPRで取り込む。`main`へは、これまでどおり`develop`から取り込む。
- 名前は既存の慣例に合わせて`feature/`で始め、英小文字とハイフンで書く。段階のブランチは`feature/ai-refactor-<段階の番号>-<内容>`とし、`ai-refactor`で本設計の取り組みであることを示す。不具合修正は、既存の`feature/fix-`で始まる名前に合わせる。
- 1つのブランチでは1つの段階だけを扱う。前提の段階が`develop`へ取り込まれてからブランチを作り、取り込まれていないブランチの上に積み重ねない。
- 1つの段階の差分が大きい場合は、PRを分けてよい。その場合は`feature/ai-refactor-6-lambda-standards-media-uploads`のように、末尾に対象を足す。
- 本設計書を扱う`feature/ai-documentation-refactoring`は、段階0より前に`develop`へ取り込む。

### 10.3 段階0: 基準の記録

1. 関数群別のテストと、`lambda/`での一括実行の結果を記録する。
2. 既存テストの期待値から、各handlerが返すステータスと応答本文の一覧を作る。
3. 各ZIPに入るファイルを、`archive_file`の定義とディレクトリの内容から一覧にする。planを実行できる場合は、生成されたZIPでも確かめる。
4. Firebaseレイヤーを、CIと同じSAMイメージで2回ビルドし、それぞれのハッシュを記録する。
5. ruffの中間のルールとPyrightの`standard`での指摘件数、CI/CDの直近の結果、devとprodの変数の違いを記録する。

記録は本設計書の第12章に追記する。確認はAWSに接続せずに行い、planを実行できない場合は`Not executed`として理由を書く。

完了条件: 実行結果と未実施理由が揃い、構造変更前の契約と既知の失敗が分かる。

### 10.4 段階1: 契約と規約の確定

1. [security.md](docs/security.md)、[lambda.md](docs/lambda.md)、[coding_standards.md](docs/coding_standards.md)、[tech_stack.md](docs/tech_stack.md)にあるJWT検証の記述を、API GatewayのIAM認証とLambdaの所有者確認の説明に置き換える。
2. API応答の規則を[lambda.md](docs/lambda.md)に正本として書き、両系統の認証SkillとテストSkillにある未認証応答の記述を合わせる。
3. 第3章の「文書の誤り」を直す。テストの手順は、関数群別のコマンドにする。
4. [coding_standards.md](docs/coding_standards.md)を、第8章の内容で書き直す。
5. ruffとPyrightのバージョンを、[開発用の依存定義](lambda/requirements-dev.txt)とCIで同じ値に固定する。`pyproject.toml`には、ruffの従来の既定ルールと、Pyrightの`standard`を書く。
6. CIのlintジョブにPyrightを加え、`GetUploadRecordsRequest.from_dict`の型ヒントを直す。
7. [commands.md](docs/commands.md)、[verification_policy.md](docs/verification_policy.md)、[README.md](README.md)、[README.en.md](README.en.md)に、ruffとPyrightのコマンドを書く。

確認: 固定したバージョンでの`ruff check`、`ruff format --check`、`pyright`、関数群別のテスト、文書のリンクの確認。

完了条件: 文書間の認証方式・必須検証・HTTP応答・CI/CDの説明の矛盾が解消され、文書に記載したAWS不要の検証手順が、現状のリポジトリで成功する。

### 10.5 段階2: 文書の静的検証

1. 第9章のAI文書の検証を行うスクリプトをPythonで書き、リポジトリに置く。対象は、Markdown、相対リンク、Skillのfrontmatter、旧Skill名の参照、両系統の差分とする。
2. 両系統で意図して変える差分を書いた許可リストを置く。
3. AWSに接続しない別のワークフローを追加し、文書、Skill、`pyproject.toml`の変更で起動させる。`pyproject.toml`の変更では、ruffとPyrightも実行する。
4. ブランチ保護で必須にするチェックを決める。

確認: 文書だけを変えたPRで新しいワークフローが起動し、AWS接続とplanが行われないこと。リンクを意図的に壊したときに失敗すること。

完了条件: 文書だけの変更で検証が起動し、AWS接続とplanを要求しない。

### 10.6 段階3: Skillの再編

1. 第5章のとおり、`auth-implementation`、`db-implementation`、`test-implementation`の手順と資料を、Lambda Skillへ移す。
2. 各`SKILL.md`を、目的、作業の選び方、判断、参照条件に絞り、コーディング規約の要点を手順に入れる。
3. Infra Skillのアドレス変更の手順を`moved`ブロック優先にし、レビューSkillが比較対象のブランチをPR情報から確かめるようにする。
4. `AGENTS.md`と`CLAUDE.md`のSkill一覧を3つに更新し、旧Skillを削除する。両系統で同じ変更を行う。

確認: 段階2の検証。旧Skill名の参照が残らず、両系統の差分が許可リストの範囲に収まること。

完了条件: 段階2の検証が成功し、移行前のSkillへの参照が残らず、共通契約の重複定義がなく、必要な資料へ辿れる。

### 10.7 段階4: Terraformのファイル分割

1. `modules/media_api/main.tf`のブロックを、第7.1節の責務別のファイルへ移す。ブロックの内容は変えない。
2. `modules/media_api/main.tf`を参照している文書とSkillを、新しいファイル名に合わせる。

確認: ブロック単位の比較、`terraform fmt -check`、`terraform init -backend=false`と`terraform validate`。planを実行できる場合は、分割前後の結果を比べる。比較の方法と結果はPRに記録する。

完了条件: ブロック単位の比較で移動以外の変更がなく、`terraform validate`が成功する。planを実行できる場合は、分割前後の結果が同じ。

### 10.8 段階5: Lambda基盤

1. パッケージ名と、ディレクトリの最終配置を決める。
2. 関数群と共有処理を名前空間付きのパッケージへ移し、importを修飾付きにする。書き方の変更は含めない。
3. `conftest.py`の`sys.path`の操作を削除し、[pytestの設定](lambda/pytest.ini)でソースのルートを指定する。
4. ZIPを作るビルドスクリプトをPythonで追加する。Terraformの`archive_file`を`filename`と`filebase64sha256()`の参照に置き換え、handlerの値を更新する。
5. ビルドしたZIPを展開して各handlerを読み込む検証を加え、CIとCDのビルド手順を同じスクリプトに揃える。
6. 影響する文書とSkillを、同じ差分で更新する。

確認: 一括と関数群別のテスト、ruff、Pyright、第6.3節の隔離した環境でのZIPの読み込み検証、`terraform validate`。planを実行できる場合は、Lambdaの更新が意図した範囲にとどまることを確かめる。

ZIPの階層とhandlerを同時に変えるため、適用の途中で短時間エラーが起き得る。第6.1節のとおり、本番運用の開始前はこれを許容する。

完了条件: ローカルとCIで同じ全体テストが成功し、ビルドしたZIPから各handlerを読み込め、文書とSkillの記述が新しい構成と一致する。

### 10.9 段階6: Lambdaの規約への移行

1. 値オブジェクト、例外、型、クライアントのキャッシュ、定数、ログを第8.2節に揃え、2系統ある書き方を1つにする。
2. ruffを中間のルールへ広げ、`boto3-stubs`を開発用の依存に加え、Pyrightの指摘を直す。
3. 値オブジェクトの単体テストを加える。handlerのテストの期待値は変えない。

確認: ruffの中間のルール、Pyrightの`standard`、全体テスト。

差分が大きい場合は、関数群ごとにPRを分ける。その場合、ruffの中間のルールは最後のPRで有効にする。

完了条件: 全関数群が同じ書き方になり、ruffとPyrightがローカルとCIで成功し、handlerのテストが期待値を変えずに成功する。

### 10.10 段階7: Terraformの改善

1. deploymentの更新判定に、第7.2節の表の属性を含める。
2. 実行可能ARNなどの重複を、`locals`から導出する。
3. Firebaseレイヤーのビルドを段階5のスクリプトへ統合し、ZIPを再現可能にして、ビルドイメージのタグを固定する。`firebase-admin`のバージョンを一元化し、Dependabotの対象ディレクトリを直す。
4. 各モジュールに`versions.tf`を置き、使われていないdata sourceと、コメントアウトしたコードを削除する。
5. tflintの設定を置き、CIに加える。

確認: 同じ入力から2回ビルドしてハッシュが一致すること、tflint、`terraform fmt -check`、`terraform validate`、第7.2節の更新判定の確認。planを実行できる場合は、deploymentの更新のほかに意図しない変更がないこと。

完了条件: 同じ入力から同じハッシュの成果物が得られ、tflintが成功する。planを実行できる場合は、動作変更が意図した範囲でplanに現れる。

### 10.11 段階8: Skill選択の評価

1. 第5章の依頼例を、独立したセッションのAIに依頼する。
2. 選ばれたSkill、読まれた資料、実行された検証を記録する。期待と違う場合は、Skillを直す。
3. 結果を本設計書の第12章に記録する。

確認: 評価の結果を、静的検証の結果と区別して記録する。行わなかった依頼例は、未実施と書く。

完了条件: 静的検証の結果と実行評価の結果が区別して記録される。

### 10.12 不具合修正のブランチ

第6.5節の不具合修正は、段階とは別のブランチで行う。

| ブランチ | 対象 |
|---|---|
| `feature/fix-notify-upload-complete` | 通知の入力、通知先の取得、通知処理の外部サービス障害。修正ごとにコミットを分け、`successCount`が0のときの扱いもここで決める |
| `feature/fix-identity-null-handling` | identity取得で、認証情報の欠落やnullを未認証として扱う |

どちらも構造変更とは別の差分にし、段階1の後、段階6より前に`develop`へ取り込む。段階5の前後のどちらで行ってもよい。

## 11. 未決事項

| 事項 | 決める時期 |
|---|---|
| ブランチ保護で必須にするチェックと、文書の検証をそこへ含めるか | 段階2 |
| パッケージ名と、ディレクトリの最終配置 | 段階5 |
| `successCount`が0のときに通知するか。現状は「0件のメディアをアップロードしました」と通知する | 第6.5節の修正時 |
| 本番運用を開始する時期。開始後は、第6.1節の段階的なhandlerの切り替え手順を使う | 本番運用の開始前 |

型検査のツールをPyrightとし、ruffとPyrightをどちらも中間の厳しさで運用することは、2026-10-31に決めた。内容は第8.4節に記す。

## 12. 検証の記録

設計書の作成とレビューで行った検証を記録する。段階0と段階8の記録も、この章に追記する。

- 作成時に、リポジトリの文書、6種類のSkillと参考資料、関係するLambda・Terraform・CI定義を調査した。作成時の環境では、Pythonの既存仮想環境の起動確認に失敗した。
- レビュー時の2026-10-30に、Python 3.12.3の新しい仮想環境で次を実行した。
  - 関数群別のテストは成功した。件数は`media_uploads`が82件、`device_tokens`が19件、`push_notification`が17件、`users`が29件である。
  - `lambda/`での一括実行は、`media_uploads/models.py`が`device_tokens/constants.py`を読み込む名前衝突により、収集時に4件のエラーで失敗した。
  - `ruff check lambda/`は、ruff 0.12.0・0.15.0・0.15.12で成功し、0.16.0・0.16.9・0.17.3では102件の指摘で失敗した。`ruff format --check lambda/`は、試したすべてのバージョンで成功した。
  - 第3章の実装上の不足のうち、通知処理の入力・ページング・外部サービス障害と、認証ヘルパーのnullの扱いを、モックを使ったスクリプトで再現した。
  - Firebaseレイヤーと同じ`pip install -t`と`zip -r9`の手順を2回実行し、ZIPのハッシュが異なることを確認した。CIと同じSAMイメージではなく、レビュー環境で確認した。
- 2026-10-31に、第8.4節のruffの中間のルールをruff 0.17.3で当て、本番コードで124件、テストで11件の指摘を確認した。`N`、`PT`と、早期リターンに関する`RET`、`SIM`の指摘は0件だった。第8.4節の`pyproject.toml`をリポジトリの写しに置いた場合も、同じく合計135件、うち自動修正できるものが74件だった。
- 2026-10-31に、Pyright 1.1.414を`standard`で実行し、指摘が1件であることを確認した。`boto3-stubs`を加えると5件、加えたうえで`strict`にすると883件だった。あわせてTerraformのモジュールを確認し、すべての変数に`type`と`description`があること、モジュールが`required_providers`を宣言していないこと、`media_api`の`aws_region`と`aws_caller_identity`のdata sourceが使われていないことを確認した。
- GitHub Actionsの記録で、PRのCIの`Lambda Lint`がruff 0.16.1で失敗してplanジョブがスキップされたことと、CDの直近2回がOIDCのロール引受けで失敗したことを確認した。
- Terraformのvalidate・plan、trivy、tflintは未実施であり、現行の全検証が成功するとは主張しない。
- 本設計のコード・Skill・CIの変更は未実装。設計書を作成したことと、提案した変更を検証したことを区別する。

## 13. 外部仕様の確認先

- [pytestのimport方式](https://docs.pytest.org/en/stable/explanation/pythonpath.html): `importlib`によるテストモジュールの読み込みと、アプリ側のimport構成を区別する。
- [DynamoDB Queryのページング](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.Pagination.html): 継続キーを使い、最後のページまで取得する。
- [Terraform AWS ProviderのAPI Gateway Deployment](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/api_gateway_deployment.html.markdown): deploymentはAPI設定のスナップショットであり、IDだけを使ったtriggerは将来の全設定変更を捉えるものではない。
- [ruff-action](https://github.com/astral-sh/ruff-action): `version`を指定せず、`pyproject.toml`にもruffのバージョンがない場合は最新版を使う。`version`または`version-file`でバージョンを固定できる。
- [Pyrightの設定](https://github.com/microsoft/pyright/blob/main/docs/configuration.md): `typeCheckingMode`は`off`、`basic`、`standard`、`strict`から選び、既定値は`standard`である。設定は`pyproject.toml`の`[tool.pyright]`にも書ける。
- [boto3-stubs](https://pypi.org/project/boto3-stubs/): boto3の型注釈で、Pyrightでも使える。`boto3-stubs[dynamodb]`のように、使うサービスを指定して入れる。
- [Pylance](https://github.com/microsoft/pylance-release): VS CodeのPylanceは、Pyrightを型検査の中核に使う。Pylance自体の厳しさの既定値は`off`だが、`pyproject.toml`の設定で上書きできる。
