# ==========================================
# Secrets Manager: Firebase service account key
# ==========================================
resource "aws_secretsmanager_secret" "firebase_credentials" {
  name        = "${var.project_name}-firebase-credentials-${var.env}"
  description = "Firebase Admin SDK service account key for push notifications"
}
