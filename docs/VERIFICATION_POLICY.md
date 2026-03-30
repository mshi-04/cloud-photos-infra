# Verification Policy

This document defines the standard verification process that AI agents and developers must perform before committing changes or reporting task completion. This process serves as a guide for AI to maintain its "harness" and make consistent modifications.

## 1. Infrastructure (Terraform) Verification

When changing infrastructure (under `envs/` or `modules/`), the following steps **must** be executed.

### Step 1: Formatting and Validation
1. Run `terraform fmt -recursive` at the root directory to format code.
2. Run `terraform validate` in both `envs/dev/` and `envs/prod/` where changes were made to verify there are no syntax errors.

### Step 2: Change Preview (Optional but Recommended)
1. Run `terraform plan` before starting and after finishing work to check for unintended resource deletions or modifications.
2. Explicitly warn the user if destructive changes (e.g., S3 bucket deletion, DynamoDB table recreation) are involved.

## 2. Application Logic (Lambda) Verification

When modifying code (Python 3.12) or adding new functions under `lambda/`, perform the following verifications:

### Step 1: Unit Test Execution
1. Use `pytest` to run tests for the applicable function.
   ```bash
   cd lambda/<function_name>
   pytest tests/
   ```
2. When adding new features, always add corresponding test cases under the `tests/` directory.

### Step 2: Static Analysis
1. Use `ruff` (or `flake8`) to check for Linter errors (if configured).

## 3. Security and Permissions Verification

### Least Privilege Principle
1. When altering IAM policies, verify that Actions are not overly permissive (avoid using `*`).
2. Verify that Resources are appropriately narrowed down (specified via ARN).

### Security Scanning
1. If possible, use `trivy` to check for security vulnerabilities and misconfigurations.
   ```bash
   trivy conf .
   ```

## 4. Completion Reporting Requirements

When reporting task completion, the AI must explicitly state that the following checks were made, or provide the execution results of each command:
- [ ] `terraform fmt` executed
- [ ] `terraform validate` passed
- [ ] `pytest` passed for all cases (if Lambda was modified)
- [ ] Confirmed that no unintended destructive changes were included
- [ ] `trivy conf .` run and no new HIGH/CRITICAL findings introduced (if infrastructure was modified)
