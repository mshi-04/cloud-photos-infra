# Cloud Photos Infra

## Project Overview
AWS infrastructure for a cloud photos application, managed with Terraform.
Manages user authentication (Cognito User Pool + Identity Pool) and media storage (S3) with per-user access isolation.

## Tech Stack
- **IaC**: Terraform 1.14.6
- **Cloud**: AWS (ap-northeast-1)
- **CI/CD**: GitHub Actions (OIDC authentication)
- **State Backend**: S3 + KMS (encryption), file-based locking (`use_lockfile = true`)

## Project Structure
```
bootstrap/          # One-time setup resources (S3 state bucket, OIDC roles)
envs/
  dev/              # Dev environment Terraform root
  prod/             # Prod environment Terraform root
environments/       # .tfvars files per environment
modules/
  cognito/          # Cognito User Pool (authentication)
  identity_pool/    # Cognito Identity Pool (temporary AWS credentials for app users)
  media_storage/    # S3 bucket for user media (photos/videos)
.github/workflows/  # CI (plan on PR) / CD (apply on merge)
```

## Key Conventions
- All changes go through Pull Requests — local `terraform apply` is prohibited
- Dev environment: auto-deploy on merge to develop/main
- Prod environment: deploy only from main, requires manual approval via GitHub Environment
- Bootstrap resources are applied manually once, not through CI/CD

## Terraform Rules
- Run `terraform fmt` before committing
- Module variables defined in `variables.tf`, outputs in `outputs.tf`
- Environment-specific values passed via `envs/<env>/main.tf` module arguments
- Do not hardcode AWS account IDs or secrets in .tf files

## CI/CD Pipeline
- **CI** (`ci-terraform.yml`): On PR — format check, validate, plan (dev + prod), comment results on PR
- **CD** (`cd-terraform.yml` + `reusable-terraform-deploy.yml`): On push — apply dev first, then prod (main only, with approval gate)
- Concurrency groups prevent parallel deploys to the same environment

## Working with This Repo
- When adding new AWS resources, create a new module under `modules/` and reference it from `envs/dev/main.tf` and `envs/prod/main.tf`
- Environment differences (deletion protection, MFA, password policy, force_destroy) are controlled via module variables
- Security-sensitive variables (e.g., force_destroy) must be set explicitly in all environments, not rely on module defaults
