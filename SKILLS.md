# Skills — AI Task Guide

This file describes common tasks and how to execute them in this repository.

## Skill: Add a New AWS Resource

When asked to add a new AWS resource (e.g., S3 bucket, Lambda, API Gateway):

1. **Create a module** under `modules/<resource_name>/`
   - `main.tf` — resource definitions
   - `variables.tf` — input variables with `description`, `type`, `default`, and `validation` blocks
   - `outputs.tf` — output values
2. **Wire it into both environments**
   - `envs/dev/main.tf` — add `module "<name>" { source = "../../modules/<name>" ... }` with dev defaults
   - `envs/prod/main.tf` — add the same module with prod overrides (stricter settings)
3. **Update IAM roles** in `bootstrap/oidc_roles.tf`
   - Add read permissions to `plan_dev` and `plan_prod` role policies
   - Add full CRUD permissions to `apply_dev` and `apply_prod` role policies
   - Use resource-level ARN scoping wherever possible; use `"*"` only for create actions that require it
4. Run `terraform fmt -recursive` before committing

### Naming conventions
- Resource names: `${var.project_name}-<resource>-${var.env}` (e.g., `cloud-photos-user-pool-dev`)
- IAM policy Sids: `Allow<Service><Action>` (e.g., `AllowCognitoManagementUserPool`)
- Module variable descriptions: written in Japanese

### Environment differences pattern
| Setting | Dev | Prod |
|---------|-----|------|
| deletion_protection | INACTIVE | ACTIVE |
| MFA | OPTIONAL | ON |
| Password length | 8 | 12+ |

Apply the same pattern for new resources: dev is permissive, prod is strict.

## Skill: Modify an Existing Module

1. Edit files under `modules/<name>/`
2. If adding a new variable, provide a sensible `default` so existing environments don't break
3. Security-sensitive variables (e.g., `force_destroy`, `deletion_protection`) must NOT have a default — require explicit setting in all `envs/*/main.tf`
4. If a variable needs different values per environment, explicitly set it in both `envs/dev/main.tf` and `envs/prod/main.tf` — do not use `var.env == "prod" ? ...` logic inside modules
5. Add `validation` blocks for variables that accept constrained values

### Variable validation style
```hcl
variable "example" {
  description = "説明文（日本語）"
  type        = string
  default     = "value"
  validation {
    condition     = contains(["value_a", "value_b"], var.example)
    error_message = "example は value_a または value_b を指定してください。"
  }
}
```

## Skill: Update CI/CD Workflows

Workflow files are in `.github/workflows/`.

- `ci-terraform.yml` — runs on PR (plan only, comments results)
- `cd-terraform.yml` — runs on push to main/develop (apply)
- `reusable-terraform-deploy.yml` — shared deploy logic

### Key rules
- Terraform version must match `.terraform-version` (currently `1.14.6`)
- IAM role ARN format: `arn:aws:iam::<account_id>:role/gh-terraform-<plan|apply>-<env>`
- Account ID is stored in `vars.AWS_ACCOUNT_ID` (GitHub Actions variable, not a secret)
- CI triggers only on changes to `envs/**`, `modules/**`, or `.github/workflows/**`
- Prod apply runs only on `main` branch and requires manual approval

## Skill: Add a New Environment

If a new environment (e.g., staging) is needed:

1. Create `envs/staging/` with `backend.tf`, `main.tf`, `outputs.tf`
2. Set the S3 backend key to `staging/terraform.tfstate`
3. Add `default_tags` with `Environment = "staging"`
4. Add IAM roles (`plan-staging`, `apply-staging`) in `bootstrap/oidc_roles.tf`
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
- Provider version pinned in `envs/<env>/main.tf` (currently `hashicorp/aws 6.32.1`)
- Backend config uses `use_lockfile = true` (file-based locking via S3, DynamoDB is not used)
- `default_tags` on the provider — do not duplicate Project/Environment/ManagedBy tags on individual resources
