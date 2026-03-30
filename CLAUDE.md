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
```text
bootstrap/          # One-time setup resources (S3 state bucket, OIDC roles)
envs/
  dev/              # Dev environment Terraform root
  prod/             # Prod environment Terraform root
environments/       # .tfvars files per environment
lambda/             # Python 3.12 Lambda function code
modules/
  cognito/          # Cognito User Pool (authentication)
  identity_pool/    # Cognito Identity Pool (temporary AWS credentials for app users)
  media_storage/    # S3 bucket for user media (photos/videos)
  media_db/         # DynamoDB table for media upload records
  device_token_db/  # DynamoDB table for push notification device tokens
  media_api/        # API Gateway + Lambda integration for media operations
  push_notification/ # SNS-based push notification dispatch
docs/               # AI workflow documents
.github/workflows/  # CI (plan on PR) / CD (apply on merge)
```

## Read This First
Before making any change, read the following files in this order:
1. `AGENTS.md`
2. `docs/GUARDRAILS.md`
3. `docs/WORKFLOW.md`
4. `docs/VERIFICATION_POLICY.md`
5. `docs/SKILLS.md`

Additional supporting guides:
- `docs/COMMANDS.md`
- `docs/COMPLETION_TEMPLATE.md`
- `bootstrap/AGENTS.md`
- `modules/AGENTS.md`
- `lambda/AGENTS.md`

## Agentic Workflow (Harness Engineering)

This repository employs **Harness Engineering** (a project-specific framework establishing boundaries and standardized processes for AI agents) to help AI perform tasks consistently and safely.

### 1. Agent Roles ([AGENTS.md](AGENTS.md))
Before starting work, select and declare an appropriate role based on the task context. Refer to [AGENTS.md](AGENTS.md) for details.
- **InfraArchitect**: Responsible for infrastructure design and Terraform management.
- **LambdaDeveloper**: Responsible for Python 3.12 implementation and quality control.
- **SecurityAuditor**: Responsible for security audits and sensitive information management.
*Note: For tasks outside these specific domains (e.g., CI/CD workflow updates, general repository maintenance), fallback to a general engineering approach while strictly adhering to global guardrails.*

### 2. Development Workflow ([WORKFLOW.md](docs/WORKFLOW.md))
Follow the standard development cycle (Planning, Role Selection, Implementation, Verification, Release) defined in [WORKFLOW.md](docs/WORKFLOW.md).

### 3. Verification Loop ([VERIFICATION_POLICY.md](docs/VERIFICATION_POLICY.md))
All changes must undergo self-verification based on [VERIFICATION_POLICY.md](docs/VERIFICATION_POLICY.md) before reporting completion. If verification cannot be executed due to missing prerequisites, explicitly report the blocked steps and escalate for manual review instead of assuming success.

---

## Key Conventions & Rules

### Role-Specific Rules
- Coding standards, formatting requirements (`terraform fmt`, `ruff format`), and best practices are defined per agent role. **You must refer to [AGENTS.md](AGENTS.md) for these specific guidelines.**

### CI/CD Pipeline
- **CI**: When a PR is created, `plan` is executed for both `dev`/`prod` environments, and the results are commented on the PR.
- **CD**: Upon merge, changes are applied to `dev` first. `prod` runs require manual approval via the GitHub Environment before deploying.

### Working with This Repo
- Create new resources inside `modules/` and reference them from `main.tf` for each environment.
- Security-sensitive variables (such as `force_destroy`) must not have a default value and must be explicitly set in each environment configuration.
- If verification steps cannot be executed because prerequisites are missing, report that clearly instead of assuming success.
