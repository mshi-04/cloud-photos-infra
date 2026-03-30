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

## Notes for Completion Reports

When reporting module work, include:
- which modules changed
- whether caller changes were required in `envs/`
- any replacement risk or compatibility concern
- what verification was executed
