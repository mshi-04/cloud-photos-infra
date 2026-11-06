# TFLint checks the Terraform conventions in docs/coding_standards.md.
# Only the bundled terraform ruleset is used, so tflint runs without downloading plugins or AWS credentials.
config {
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_standard_module_structure" {
  enabled = true
}
