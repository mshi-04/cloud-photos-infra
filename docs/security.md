# セキュリティガイド

この文書は、IAM、認証、機密情報、ログ、IaCスキャンに関する基準を定義します。

## Baseline

- 最小権限を原則にします。
- 認証、認可、暗号化、監査ログを分けて考えます。
- セキュリティ上の例外は、理由、範囲、残リスクを明記します。
- CIや開発の都合だけで権限を広げないでください。

## IAM

IAM変更では次を確認します。

- 必要な `Action` だけを列挙しているか
- `Resource` を可能な範囲でARNに限定しているか
- `Condition` でさらに制約できるか
- `Sid` が権限の目的を説明しているか
- dev/prod の境界を壊していないか
- GitHub Actions OIDCロールの信頼ポリシーが広すぎないか

`"Action": "*"` と `"Resource": "*"` は原則として避けます。やむを得ない場合は、理由と代替案を明記してください。

## Authentication And Authorization

- API系Lambdaは Cognito JWT を検証します。
- ユーザーごとのS3 prefix、DynamoDB key、Identity ID の境界を維持します。
- 認証と所有者チェックを混同しないでください。
- 認証済みでも、他ユーザーのメディアやデバイストークンへアクセスできないことを確認します。

## Secrets

- シークレット、APIキー、トークン、秘密鍵、AWSアカウントIDをコミットしないでください。
- Firebaseなどの外部認証情報は Secrets Manager などの管理された保管先を使います。
- Terraform変数や出力で機密値を扱う場合は `sensitive = true` を検討します。
- ドキュメント例には明らかなダミー値を使います。

## Logging

- PII、生トークン、認証情報をログに出さないでください。
- ユーザー識別子をログに出す場合はマスクします。
- エラー詳細は運用調査に必要な範囲に留め、外部レスポンスへ内部情報を返さないでください。

## Encryption And Data

- S3、DynamoDB、Terraform state は暗号化を前提にします。
- KMS key policy と IAM policy の両方を確認します。
- データ削除、保持期間、公開アクセス設定に関わる変更は高リスクとして扱います。

## Scanning

IaCやIAMに影響する変更では、可能な限り次を実行します。

```powershell
trivy conf .
```

HIGH / CRITICAL の検出は、修正または明確なリスク受容なしに放置しないでください。実行できない場合は `Not executed` と理由を報告します。

## Security Reporting

完了報告には、必要に応じて次を含めます。

- 追加・変更した権限
- 最小権限と判断した根拠
- 検証結果
- 残るリスク
- 手動で必要なシークレット投入や運用作業
