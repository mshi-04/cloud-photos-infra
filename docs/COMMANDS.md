# Common Commands for AI Tasks

This file lists common commands used in this repository.

## Terraform

Run from the repository root unless noted otherwise.

```bash
terraform fmt -recursive
terraform fmt -check -recursive
```

Execute validation from each environment directory when necessary.

```bash
cd envs/dev && terraform validate
cd envs/prod && terraform validate
```

Perform planning from each environment directory prior to applying changes.

```bash
cd envs/dev && terraform plan
cd envs/prod && terraform plan
```

## Lambda Formatting and Lint

Run from the repository root or the lambda directory, depending on the existing project setup.

```bash
ruff format lambda/
ruff check lambda/
```

## Lambda Tests

Run from the lambda directory when using the existing test layout.

```bash
cd lambda
pytest
pytest push_notification/tests/
```

## Security Scan

Run from the repository root.

```bash
trivy conf .
```

## Reporting Reminder

When a command was not executed, say so clearly and explain why.
