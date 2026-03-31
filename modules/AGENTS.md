# Modules Local Agent Guide

This guide applies only to the modules directory.

## Purpose

The modules directory contains reusable Terraform building blocks used by environment root modules.

## Working Style

- Keep modules reusable and environment-agnostic.
- Put environment differences in `envs/<env>/main.tf`, not inside module logic.
- Keep file roles clear: `main.tf` for resources, `variables.tf` for inputs, and `outputs.tf` for outputs.
- Prefer small changes that preserve compatibility for existing callers.

## Variable Rules

- Use English descriptions.
- Add validation blocks when a variable accepts a constrained set of values.
- Avoid defaults for security-sensitive variables.
- If a new variable is added, check whether each environment should set it explicitly.

## Review Focus

- resource naming consistency
- input and output design
- compatibility with existing environment roots
- least-privilege implications for IAM-related changes
- replacement risk caused by renames or structural changes

## State Lock During Verification

Terraform verification for modules is exercised by running `terraform plan` or `terraform validate` from the environment directories that reference the module (`envs/dev`, `envs/prod`). If either command is blocked by a state lock:
- Do not retry with `-lock=false`.
- Do not run `terraform force-unlock` automatically.
- Report the locked environment, Lock ID, and suspected cause (e.g., concurrent CI run, interrupted local run).
- Ask the user to manually unlock before re-running verification.
- Mark the verification step as **Blocked by Terraform state lock** in the completion report.

## Notes for Completion Reports

When reporting module work, include:
- which modules changed
- whether caller changes were required in `envs/`
- any replacement risk or compatibility concern
- what verification was executed (or whether it was blocked by a state lock)
