# Verification Policy

This document defines the standard verification process that AI agents and developers must perform before committing changes or reporting task completion. This process serves as a guide for AI to maintain its harness and make consistent modifications.

## Verification Status Categories

Every verification item must be reported using one of these states:
- **Executed and passed**
- **Executed and failed**
- **Not executed because prerequisites were missing**

Do not report a verification item as passed if it was not actually executed.

## 1. Infrastructure (Terraform) Verification

When changing infrastructure under `envs/` or `modules/`, use the following verification flow.

### Step 1: Formatting
1. Run `terraform fmt -recursive` at the repository root to format code, or `terraform fmt -check -recursive` to verify it passes CI.

### Step 2: Validation
1. Run `terraform validate` in affected environment directories when Terraform has been initialized and the local environment is ready.
2. If validation cannot be executed because initialization, credentials, or backend access are unavailable, report that explicitly.

### Step 3: Change Preview
1. Run `terraform plan` before finishing work when credentials and initialization are available.
2. Check for unintended resource deletions or modifications.
3. Explicitly warn the user if destructive changes such as resource deletion or replacement are involved.

## 2. Application Logic (Lambda) Verification

When modifying Python 3.12 code or adding new functions under `lambda/`, perform the following checks.

### Step 1: Unit Test Execution
1. Use `pytest` to run tests for the applicable function.
   ```bash
   cd lambda
   pytest <function_name>/tests/
   ```
2. When adding new features, add corresponding test cases under the `tests/` directory.

### Step 2: Formatting and Static Analysis
1. Use `ruff format` to auto-format the code, or `ruff format --check` to verify it passes CI format checks.
2. Use `ruff check` to check for linter errors.

## 3. Security and Permissions Verification

### Least Privilege Principle
1. When altering IAM policies, verify that actions are not overly permissive.
2. Verify that resources are narrowed appropriately whenever the service supports it.

### Security Scanning
1. If possible, use `trivy` to check for security vulnerabilities and misconfigurations.
   ```bash
   trivy conf .
   ```
2. If the scan could not be run, report that explicitly.

## 4. Completion Reporting Requirements

When reporting task completion, include the execution state or result of each relevant item:
- [ ] `terraform fmt -recursive` executed or `terraform fmt -check -recursive` passed
- [ ] `terraform validate` executed and passed, or reported as not executed with reason
- [ ] `terraform plan` executed and reviewed, or reported as not executed with reason
- [ ] `ruff format` and `ruff check` passed if Lambda code was modified
- [ ] `pytest` passed for applicable Lambda tests if Lambda code was modified
- [ ] Confirmed that no unintended destructive changes were included, or clearly described any remaining risk
- [ ] `trivy conf .` run and reviewed if infrastructure was modified, or reported as not executed with reason

Use [COMPLETION_TEMPLATE.md](./COMPLETION_TEMPLATE.md) when preparing the final completion report.
