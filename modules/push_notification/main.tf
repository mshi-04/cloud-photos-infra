# ==========================================
# Secrets Manager: Firebase service account key
# ==========================================
resource "aws_secretsmanager_secret" "firebase_credentials" {
  name        = "${var.project_name}-firebase-credentials-${var.env}"
  description = "Firebase Admin SDK service account key for push notifications"
}

# ==========================================
# Lambda Layer: firebase-admin
# ==========================================
resource "aws_lambda_layer_version" "firebase_admin" {
  layer_name          = "${var.project_name}-firebase-admin-${var.env}"
  filename            = var.firebase_layer_zip_path
  source_code_hash    = filebase64sha256(var.firebase_layer_zip_path)
  compatible_runtimes = ["python3.12"]
  description         = "firebase-admin SDK layer"
}
