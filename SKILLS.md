# Skills — AI Task Guide

This file describes common tasks and how to execute them in this repository.

## Skill: Add a New AWS Resource

When asked to add a new AWS resource (e.g., S3 bucket, Lambda, API Gateway):

1. **Create a module** under `modules/<resource_name>/`
   - `main.tf` — resource definitions
   - `variables.tf` — input variables with `description`, `type`, and `validation` blocks; add `default` only for non-security-sensitive variables
   - `outputs.tf` — output values
2. **Wire it into both environments**
   - `envs/dev/main.tf` — add `module "<name>" { source = "../../modules/<name>" ... }` with dev defaults
   - `envs/prod/main.tf` — add the same module with prod overrides (stricter settings)
3. **Update IAM roles** in `bootstrap/oidc_roles.tf`
   - Add read permissions to `gh-terraform-plan-dev` and `gh-terraform-plan-prod` role policies
   - Add full CRUD permissions to `gh-terraform-apply-dev` and `gh-terraform-apply-prod` role policies
   - Use resource-level ARN scoping wherever possible; use `"*"` only for create actions that require it
   - **Bootstrap changes are NOT applied via CI/CD** — manually run `terraform init && terraform apply` in the `bootstrap/` directory after editing
4. Run `terraform fmt -recursive` before committing

### Naming conventions
- Resource names: `${var.project_name}-<resource>-${var.env}` (e.g., `cloud-photos-user-pool-dev`). S3 buckets use `${account_id}-${var.project_name}-<resource>-${var.env}` for global uniqueness
- IAM policy Sids: `Allow<Service><Action>` (e.g., `AllowCognitoManagementUserPool`)
- Module variable descriptions: written in Japanese

### Environment differences pattern

| Setting | Dev | Prod |
|---------|-----|------|
| deletion_protection | INACTIVE | ACTIVE |
| MFA | OPTIONAL | ON |
| Password length | 8 | 8 |

Apply the same pattern for new resources: dev is permissive, prod is strict.

## Skill: Modify an Existing Module

1. Edit files under `modules/<name>/`
2. If adding a new variable, provide a sensible `default` so existing environments don't break — but if the value differs between environments, always set it explicitly in both `envs/dev/main.tf` and `envs/prod/main.tf` regardless of whether a default exists
3. Security-sensitive variables (e.g., `force_destroy`) must NOT have a default — require explicit setting in all `envs/*/main.tf`. Variables with a safe fallback (e.g., `deletion_protection` defaulting to `"INACTIVE"`) may have a default, but prod must always override them explicitly
4. Never use `var.env == "prod" ? ...` logic inside modules — environment differences belong in `envs/*/main.tf`, not in module code
5. Add `validation` blocks for variables that accept constrained values

### Variable validation style
```hcl
variable "env" {
  description = "環境名"
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env は dev または prod を指定してください。"
  }
}
```

## Skill: Update CI/CD Workflows

Workflow files are in `.github/workflows/`.

- `ci-terraform.yml` — runs on PR (plan only, comments results)
- `cd-terraform.yml` — runs on push to main/develop (apply)
- `reusable-terraform-deploy.yml` — shared deploy logic

### Key rules
- Terraform version must match `.terraform-version` (see `.terraform-version` for the current version)
- IAM role ARN format: `arn:aws:iam::<account_id>:role/gh-terraform-<plan|apply>-<env>`
- Account ID is stored in `vars.AWS_ACCOUNT_ID` (GitHub Actions variable, not a secret)
- CI triggers on changes to `envs/**`, `modules/**`, or `.github/workflows/**`; CD triggers on `envs/**` and `modules/**` only (workflow changes do not trigger auto-apply)
- Prod apply runs only on `main` branch and requires manual approval

## Skill: Add a New Environment

If a new environment (e.g., staging) is needed:

1. Create `envs/staging/` with `backend.tf`, `main.tf`, `outputs.tf`
2. Set the S3 backend key to `staging/terraform.tfstate`
3. Add `default_tags` with `Environment = "staging"`
4. Add IAM roles (`gh-terraform-plan-staging`, `gh-terraform-apply-staging`) in `bootstrap/oidc_roles.tf`
   - **Bootstrap changes are NOT applied via CI/CD** — after editing `bootstrap/oidc_roles.tf`, manually run `terraform init && terraform apply` in the `bootstrap/` directory with appropriate AWS credentials before proceeding
5. Add matrix entries in CI/CD workflows
6. Create the GitHub Environment with appropriate protection rules

## Skill: Bootstrap / Initial Setup

The `bootstrap/` directory is applied manually (not via CI/CD). It contains:
- **S3 bucket** for Terraform state (`backend_resources.tf`)
- **KMS key** for state encryption
- State locking uses file-based locking (`use_lockfile = true`), not DynamoDB
- **GitHub OIDC provider and IAM roles** (`oidc_roles.tf`)

To modify bootstrap resources, edit files in `bootstrap/` and apply locally with appropriate AWS credentials. These changes do NOT go through the CI/CD pipeline.

## Terraform Style Rules

- Always run `terraform fmt -recursive` before committing
- Use `jsonencode()` for inline IAM policies (not heredoc)
- Provider version pinned in `envs/<env>/main.tf` — check that file for the current `hashicorp/aws` version
- Backend config uses `use_lockfile = true` (file-based locking via S3, DynamoDB is not used)
- `default_tags` on the provider — do not duplicate Project/Environment/ManagedBy tags on individual resources
