# AI文書・開発基盤リファクタリング設計

- 作成日: 2026-10-30
- 状態: 設計案。実装前。
- 設計の起点: `develop` の `e4dfb2d`
- 作業ブランチ: `feature/ai-documentation-refactoring`

## 1. 目的と前提

AIが、変更する場所、守る契約、必要な検証、完了の判断方法を一貫して理解できるプロジェクトにする。文書の整理と、文書が説明する開発手順を支えるコード・ビルド・テストの改善を一体で設計する。

`AGENTS.md`と`CLAUDE.md`は、それぞれのツール向けの入口として独立して管理する。二重管理は許容し、共通の意味が揃っていることを確認する。入口の統合、import化、自動同期を本設計の前提にしない。`.agents/skills/`と`.claude/skills/`についても、片方を生成物にする方式は必須としない。

必要なコード変更は対象に含める。ただし、文書に合わせるために正しい実装を変えるのではなく、現行動作、意図した要件、実装上の不具合を区別して判断する。認証方式、API互換性、データ保持、IAM権限に影響する変更は、その影響を個別に扱う。

本ファイルの追加段階では設計を記録するだけとし、以下のコード・文書・Skill・CI変更はまだ実施しない。

## 2. 目標

1. セキュリティやAPIの契約を、文書とSkillで別々に定義しない。
2. 通常の変更が、少数の作業単位に対応するSkillから進められる。
3. ローカルとCIが同じ方法で全体テストと個別テストを実行できる。
4. テストが参照するパッケージ構成と、Lambdaへ配布するZIPの構成が一致する。
5. 配布漏れやAPI設定の反映漏れを、説明の読み落としだけに依存せず検出できる。
6. AI文書や検証設定の変更を、AWS認証が不要な検証で確認できる。

## 3. 現状と課題

調査時の文書・ソース・ワークフローを根拠とする。全体テスト、Terraform plan、実環境への適用で動作を確認した結果ではない。

| 項目 | 現状 | 設計上の判断 |
|---|---|---|
| 入口 | [AGENTS.md](AGENTS.md)と[CLAUDE.md](CLAUDE.md)は各27行で、共通文書と6種類のSkillを案内する | 独立した入口を維持し、必読事項と作業別の参照順を明確にする |
| 共通ルール | 検証、state lock、IAM、ログの要件が複数の文書・Skillへ繰り返し記載される | 各要件の正本と、参照する側を決める |
| 認証 | [Lambdaガイド](docs/lambda.md)などはLambdaでのJWT検証を指示するが、[認証Skill](.agents/skills/auth-implementation/SKILL.md)と[実装](lambda/common/auth.py)はCognito Identity IDを扱う | API GatewayのIAM認証とLambdaの所有者確認を正しく説明する。JWT検証の追加は行わない |
| テスト | 文書は全体を一度に実行する手順だが、[CI](.github/workflows/ci-terraform.yml)は4つの関数群を別プロセスで実行する | 名前空間とimportを整理し、一度の全体実行を成立させる |
| import | [関数群のfixture](lambda/device_tokens/tests/conftest.py)が`sys.path`を変更し、`auth`、`constants`、`db`などを同名でimportする | 関数群ごとに区別できるモジュール名へ移行する |
| 配布 | [Lambda ZIP生成](modules/media_api/main.tf)はディレクトリ収録とファイル列挙が混在する | 共通の配布方針と、生成物を使う読み込み検証を設ける |
| Terraform | `media_api/main.tf`の1,108行にZIP生成、IAM、Lambda、API Gatewayが集まる | モジュールを維持したまま、責務別のファイルへ分ける |
| API反映 | APIの再デプロイ判定は、主にmethod/integrationのIDとCORS originを参照する | IDが変わらない設定変更も再デプロイへ反映する |
| CI対象 | AI文書と`pyproject.toml`は既存CIのパス条件に含まれない | 文書・検証設定を対象にした軽量な検証を設ける |

### 調査で確認した実装上の不足

- [通知処理](lambda/push_notification/notify_upload_complete.py)は、JSON配列・文字列・数値などをオブジェクトとして扱おうとする。`successCount`の整数判定は真偽値も受け入れる。
- 同処理の端末取得はDynamoDB Queryの最初のページだけを取得し、継続キーを処理していない。
- [共通認証ヘルパー](lambda/common/auth.py)と[Media Uploadsの認証ヘルパー](lambda/media_uploads/auth.py)は、`requestContext`や`identity`がnullの場合に例外となる。[Usersのヘルパー](lambda/users/auth.py)とは扱いが異なる。
- UsersとPushの未認証応答は401、Media UploadsとDevice Tokensは403であり、既存テストもそれぞれを期待する。一律403を要求するSkillの記述は現行契約と一致しない。

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
| [coding_standards.md](docs/coding_standards.md) | 命名、型、コード構成、Terraform記述などの実装規約 | 認証方式・検証手順・安全境界の重複定義 |
| [tech_stack.md](docs/tech_stack.md) | 技術の概要と設定の参照先 | バージョン、CI、コマンドなど更新されやすい情報の並行した一覧 |
| [README.md](README.md) / [README.en.md](README.en.md) | 利用者・開発者向けの概要と開始方法 | AI固有の詳細手順 |
| [SECURITY.md](SECURITY.md) | 公開リポジトリの脆弱性報告方針 | AI向けの実装規約 |

既存の文書名を基本的に維持する。セキュリティ要件と操作の許可は区別し、共通ルールを参照する際には「いつ読むか」を示す。参考リンクの列挙だけで必読要件を表現しない。

API契約では、正常応答、入力エラー、認証情報欠落、所有者境界違反、条件付き書き込み、冪等操作、外部サービス障害を区別する。DBの条件式失敗を一律404にするなど、操作ごとの差を消す一般化は避ける。

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

プロジェクト固有のパッケージ名の配下に、関数群と必要な共有処理を置く。例えば`cloud_photos.media_uploads`、`cloud_photos.device_tokens`のように、どの関数群のモジュールか分かるimportを使う。

テストのために関数群のディレクトリを`sys.path`の先頭へ追加する構成を解消する。パッケージ名、ディレクトリの最終配置、Terraformのhandler値、ZIP内の階層は同じ変更段階で確定する。関数群の責務と既存のLambdaリソースは維持する。

### 6.2 共有処理

認証情報の抽出やJSONオブジェクトの解析など、契約が共通で状態を持たない処理は共有候補とする。共通化は名前空間と配布方法を整えてから行う。

API応答は204の空bodyなどの差を保つ。DynamoDBのクライアント・テーブル名キャッシュは、関数群ごとの設定とテスト分離を考慮する。同じコードであることだけを理由にキャッシュやDBアクセスを一つの汎用層へ統合しない。

### 6.3 配布物の契約

- 本番に必要なパッケージと共有処理を、関数群ごとのZIPへ収録する。
- `tests/`、`__pycache__/`、テスト・ツールのキャッシュを配布対象から外す。
- テストと本番で同じ修飾付きimportを使う。
- 生成したZIPを独立した場所へ展開し、リポジトリのソース検索パスに依存せず各handlerをimportできることを検証する。
- 読み込み検証には実AWS認証情報や実サービス呼び出しを必要としない。外部ライブラリを持つ関数では、その配布レイヤーも含めて依存関係を確認する。
- ローカルとCIで同じ成果物生成手順を呼ぶ。Firebaseレイヤーのビルド手順も重複させない。
- 保存したplanとビルド済み成果物をapplyへ渡す既存の構成を保ち、plan後に別の成果物へ作り直さない。

### 6.4 テスト実行

移行前に、現行CIと同じ関数群別実行で基準となる結果を記録する。現行の全体一括実行が成功するとは仮定しない。

移行後は、同じ全体実行コマンドをローカルとCIで利用でき、個別の関数群も選択できるようにする。モジュールキャッシュの掃除や実行順への依存で名前衝突を回避する方式は採用しない。

fixtureは`monkeypatch`などで環境変数を元の状態へ戻す。MotoとFirebaseのモック、クライアントキャッシュのリセット、関数群固有のテーブル構造は維持する。テスト用のキャッシュリセットを本番コードの設計として不要に一般化しない。

### 6.5 個別の不具合修正

| 対象 | 修正する動作 | 必要な確認 |
|---|---|---|
| 通知の入力 | JSONオブジェクト以外と、真偽値・負数・非整数の`successCount`を400として扱う | 不正入力でDBやFCMへ進まない。既存の正常応答、401、201、204を保つ |
| 通知先の取得 | Queryの継続キーを処理し、全ページの端末を対象にする | 複数ページ、継続キー付きの空ページ、所有者条件の維持 |
| identity取得 | 認証情報の欠落・nullを未認証として扱う | 関数群ごとの既存401/403契約を保ち、例外にしない |

構造変更と不具合修正は、差分と検証結果を分けて追跡できる単位にする。通知基盤の非同期化など、別のアーキテクチャ変更はここへ混ぜない。

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

### 7.2 APIの接続と再デプロイ

設定変更を確実に反映するため、deploymentの更新判定に対象APIの設定内容を含める。対象は認証設定、integration、CORS、Gateway Responseなど、公開されたAPIの動作へ影響する設定とする。

必要なmethod・path・実行可能ARNの関係を小さな定義にまとめ、実行可能ARNやpermissionの重複を導出できる箇所を整理する。ただし、全リソースを汎用化するための抽象層は導入しない。Lambdaごとの権限境界と既存のリソースアドレスを維持する。

deploymentの更新は意図した変更として扱う。それ以外の削除・置換、権限の拡張、state移行が発生する場合は、別途その必要性と影響を確認する。

### 7.3 環境の境界

`envs/dev`と`envs/prod`、既存の用途別モジュール、独立したstateを保つ。削除保護、MFA、ログ・ストレージ保持期間などの差はルートモジュールで明示する。環境全体を一つの巨大なモジュールにまとめることは目標にしない。

## 8. CIと検証の設計

検証を、AWS接続が不要なものと、環境に接続するものに分ける。

| 対象 | 主な検証 |
|---|---|
| AI文書 | Markdown、相対リンク、Skill frontmatter、移動したSkill参照の残存 |
| Pythonと検証設定 | Ruff、全体テスト、個別テスト、配布物の読み込み |
| Terraform | format、validate、影響環境のplan、権限と差分のレビュー |
| セキュリティに関係するIaC | 共通ポリシーに沿ったスキャンと、実行可否・未実施理由の報告 |

文書や`pyproject.toml`の変更が対応する検証を起動するようにする。文書だけの変更にAWS接続やTerraform planを要求しない。Skillの両系統はそれぞれ構文と参照先を確認し、byte単位の一致を必須にしない。

Skillの構文やリンクの検証と、AIが適切なSkillを選び必要な資料を読むかの確認は別に扱う。前者の成功を、後者の成功として報告しない。後者は第5章の依頼例などを使い、独立したセッションで選択・参照・検証範囲を観察する。未実施なら未実施と明示する。

## 9. 実施順序と完了条件

| 段階 | 主な変更 | 完了条件 |
|---|---|---|
| 0. 基準の記録 | 現行の関数群別テスト、API応答、ZIP構成、環境差を確認する | 実行結果と未実施理由が揃い、構造変更前の契約が分かる |
| 1. 契約の確定 | 認証方式、API応答、セキュリティ、検証方針の正本を決め、誤記を修正する | 文書間の認証方式・必須検証・HTTP応答の矛盾が解消される |
| 2. Lambda基盤 | パッケージ・import・ZIP・fixtureを一緒に整える。個別の不具合は分けて修正する | ローカルとCIで同じ全体テストが成功し、ZIPから各handlerを読み込める |
| 3. Terraform整理 | 同一モジュール内のファイル分割後、API反映の判定と配布手順を改善する | ファイル分割だけで実リソース差分がない。動作変更は意図した範囲でplanに現れる |
| 4. 文書とSkill | 両入口・両Skill系統を3つの作業単位に揃え、資料と参照先を整理する | 移行前のSkillへの参照が残らず、共通契約の重複定義がなく、必要な資料へ辿れる |
| 5. 継続的な検証 | 文書・ツール設定の検証と、Skill選択の確認を行う | 関連パスで検証が起動し、静的検証と実行評価が区別して記録される |

各段階を独立してレビューできる変更単位にする。新しい配置やコマンドは利用可能になった段階で文書へ反映し、設計上の予定を現行手順として記載しない。

実装時の承認・state lock・シークレットの扱いは、引き続き[guardrails.md](docs/guardrails.md)に従う。検証結果は[verification_policy.md](docs/verification_policy.md)の4つのステータスで報告する。

## 10. 設計書作成時点の検証範囲

- リポジトリの文書、6種類のSkillと参考資料、関係するLambda・Terraform・CI定義を調査した。
- 全体テストとTerraform planは未実施であり、現行の全検証が成功するとは主張しない。
- Pythonの既存仮想環境は起動確認に失敗しているため、実装段階の基準測定前に実行環境の状態を確認する。
- 本設計のコード・Skill・CIの変更は未実装。設計書を作成したことと、提案した変更を検証したことを区別する。

## 11. 外部仕様の確認先

- [pytestのimport方式](https://docs.pytest.org/en/stable/explanation/pythonpath.html): `importlib`によるテストモジュールの読み込みと、アプリ側のimport構成を区別する。
- [DynamoDB Queryのページング](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.Pagination.html): 継続キーを使い、最後のページまで取得する。
- [Terraform AWS ProviderのAPI Gateway Deployment](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/api_gateway_deployment.html.markdown): deploymentはAPI設定のスナップショットであり、IDだけを使ったtriggerは将来の全設定変更を捉えるものではない。
