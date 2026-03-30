# Skills — AI Task Guide

This file describes common tasks and how to execute them in this repository.

## Role-Based Skills

Each skill is based on the specialty areas of the roles defined in [AGENTS.md](../AGENTS.md).

## Skill: Add a New AWS Resource [InfraArchitect]

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
- Module variable descriptions: written in English

### Environment differences pattern

| Setting | Dev | Prod |
|---------|-----|------|
| deletion_protection | INACTIVE | ACTIVE |
| MFA | OPTIONAL | ON |
| Password length | 8 | 8 |

Apply the same pattern for new resources: dev is permissive, prod is strict.

## Skill: Modify an Existing Module [InfraArchitect]

1. Edit files under `modules/<name>/`
2. If adding a new variable, provide a sensible `default` so existing environments don't break — but if the value differs between environments, always set it explicitly in both `envs/dev/main.tf` and `envs/prod/main.tf` regardless of whether a default exists
3. Security-sensitive variables (e.g., `force_destroy`) must NOT have a default — require explicit setting in all `envs/*/main.tf`. Variables with a safe fallback (e.g., `deletion_protection` defaulting to `"INACTIVE"`) may have a default, but prod must always override them explicitly
4. Never use `var.env == "prod" ? ...` logic inside modules — environment differences belong in `envs/*/main.tf`, not in module code
5. Add `validation` blocks for variables that accept constrained values

### Variable validation style
```hcl
variable "env" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env must be dev or prod."
  }
}
```

## Skill: Update CI/CD Workflows [InfraArchitect]

Workflow files are in `.github/workflows/`.

- `ci-terraform.yml` — runs on PR (plan only, comments results)
- `cd-terraform.yml` — runs on push to main/develop (apply)
- `reusable-terraform-deploy.yml` — shared deploy logic

### Key rules
- Terraform version must match `.terraform-version` (see `.terraform-version` for the current version)
- IAM role ARN format: `arn:aws:iam::<account_id>:role/gh-terraform-<plan|apply>-<env>`
- Account ID is stored in `vars.AWS_ACCOUNT_ID` (GitHub Actions variable, not a secret)
- CI triggers on changes to `envs/**`, `modules/**`, `lambda/**`, `bootstrap/**`, `.github/workflows/**`, or `.terraform-version`; CD triggers on `envs/**`, `modules/**`, and `lambda/**` only (workflow changes do not trigger auto-apply)
- Prod apply runs only on `main` branch and requires manual approval

## Skill: Add a New Environment [InfraArchitect]

If a new environment (e.g., staging) is needed:

1. Create `envs/staging/` with `backend.tf`, `main.tf`, `outputs.tf`
2. Set the S3 backend key to `staging/terraform.tfstate`
3. Add `default_tags` with `Environment = "staging"`
4. Add IAM roles (`gh-terraform-plan-staging`, `gh-terraform-apply-staging`) in `bootstrap/oidc_roles.tf`
   - **Bootstrap changes are NOT applied via CI/CD** — after editing `bootstrap/oidc_roles.tf`, manually run `terraform init && terraform apply` in the `bootstrap/` directory with appropriate AWS credentials before proceeding
5. Add matrix entries in CI/CD workflows
6. Create the GitHub Environment with appropriate protection rules

## Skill: Bootstrap / Initial Setup [InfraArchitect]

The `bootstrap/` directory is applied manually (not via CI/CD). It contains:
- **S3 bucket** for Terraform state (`backend_resources.tf`)
- **KMS key** for state encryption
- State locking uses file-based locking (`use_lockfile = true`), not DynamoDB
- **GitHub OIDC provider and IAM roles** (`oidc_roles.tf`)

To modify bootstrap resources, edit files in `bootstrap/` and apply locally with appropriate AWS credentials. These changes do NOT go through the CI/CD pipeline.

## Skill: Add a New Lambda Function [LambdaDeveloper]

When asked to implement a new Lambda function:

1. **Create a directory** under `lambda/<function_name>/`
   - Follow the existing structure in `lambda/device_tokens/` or `lambda/media_uploads/` as a reference
   - Required files: handler entry point (e.g., `<function_name>.py`), `auth.py`, `constants.py`, `response.py`
   - Create `tests/` with `conftest.py` and at minimum one `test_<function_name>.py`
2. **Create a Terraform module** under `modules/<name>/` for the supporting infrastructure (Lambda resource, IAM role, CloudWatch log group)
3. **Wire it into environments** — add the module in both `envs/dev/main.tf` and `envs/prod/main.tf`
4. **Update bootstrap IAM** in `bootstrap/oidc_roles.tf` if the new Lambda requires new AWS service permissions
5. **Update `pyproject.toml`** at repo root if new dependencies are required

### Lambda conventions
- Python 3.12; use type hints throughout
- All handler functions must validate the Cognito JWT from the request (`auth.py` pattern)
- Return values use the `response.py` helper for consistent HTTP response format
- Log errors to CloudWatch using `print()` or `logging` — include enough context to debug without exposing PII

## Skill: Run Lambda Tests [LambdaDeveloper]

Whenever you modify code under the `lambda/` directory, you must run unit tests. See [VERIFICATION_POLICY.md](VERIFICATION_POLICY.md) for details.

1. Navigate to the modified Lambda function's directory
   ```bash
   cd lambda/<function_name>
   ```
2. Run `pytest`
   ```bash
   pytest tests/
   ```

## Skill: Security Audit [SecurityAuditor]

### Run Trivy Scan

```bash
trivy conf .
```

Review the output and address any HIGH or CRITICAL findings before committing. Informational/LOW findings should be documented in [SECURITY.md](../SECURITY.md) if accepted as known risks.

### IAM Policy Review Checklist

When reviewing or writing IAM policies:
1. **No wildcard Actions** — avoid `"Action": "*"`; list only required actions explicitly
2. **Scoped Resources** — use ARNs instead of `"Resource": "*"` wherever the service allows it
3. **No hardcoded Account IDs or secrets** — use variables or data sources (`data "aws_caller_identity"`)
4. **Least Privilege per environment** — plan-role gets read-only, apply-role gets CRUD; prod roles are separate from dev

### Update SECURITY.md

When a security-relevant change is made (new IAM policy, new resource, encryption setting, etc.), update [SECURITY.md](../SECURITY.md) to reflect:
- What was changed
- Why it is considered safe or what risk it introduces
- Any accepted known issues and their rationale

---

## Terraform Style Rules [InfraArchitect]

- Always run `terraform fmt -recursive` before committing
- Use `jsonencode()` for inline IAM policies (not heredoc)
- Provider version pinned in `envs/<env>/main.tf` — check that file for the current `hashicorp/aws` version
- Backend config uses `use_lockfile = true` (file-based locking via S3, DynamoDB is not used)
- `default_tags` on the provider — do not duplicate Project/Environment/ManagedBy tags on individual resources
