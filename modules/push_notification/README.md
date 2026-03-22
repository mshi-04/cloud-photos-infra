# push_notification module

Manages the Firebase push notification infrastructure for the cloud-photos application.

## Resources

- **AWS Secrets Manager** (`aws_secretsmanager_secret.firebase_credentials`): Creates the secret container for the Firebase Admin SDK service account key. The secret name follows the pattern: `{project_name}-firebase-credentials-{env}` (e.g., `cloud-photos-firebase-credentials-dev`).

## Post-deployment: Populating the Firebase secret

This module only creates the Secrets Manager **container**. You must manually populate the secret value with the Firebase service account JSON before the push notification feature will work.

**Steps:**

1. Download the Firebase Admin SDK service account key from the Firebase console (JSON format).
2. Store it in Secrets Manager using the AWS CLI:

```bash
aws secretsmanager put-secret-value \
  --secret-id "cloud-photos-firebase-credentials-dev" \
  --secret-string file:///path/to/firebase-service-account.json \
  --region ap-northeast-1
```

Replace `dev` with `prod` for the production environment.

**Secret format:** The value must be the raw Firebase service account JSON object, e.g.:
```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  ...
}
```

> **Security:** Never commit the service account JSON to the repository. Handle the file securely and delete it from local disk after storing it in Secrets Manager.
