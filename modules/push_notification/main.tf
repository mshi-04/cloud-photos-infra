# ==========================================
# Secrets Manager: Firebase service account key
# ==========================================
resource "aws_secretsmanager_secret" "firebase_credentials" {
  name        = "${var.project_name}-firebase-credentials-${var.env}"
  description = "Firebase Admin SDK service account key for push notifications"
}

# ==========================================
# Lambda Layer: firebase-admin SDK
# ==========================================
resource "aws_lambda_layer_version" "firebase_admin" {
  layer_name               = "${var.project_name}-firebase-admin-${var.env}"
  filename                 = "${path.module}/../../.build/firebase_admin_layer.zip"
  source_code_hash         = filebase64sha256("${path.module}/../../.build/firebase_admin_layer.zip")
  compatible_runtimes      = ["python3.12"]
  compatible_architectures = ["x86_64"]
}
