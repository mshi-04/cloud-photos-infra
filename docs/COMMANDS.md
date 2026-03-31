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

## Terraform State Lock Inspection

When `terraform plan` or `terraform validate` reports a state lock error, read the error output carefully. Terraform prints the Lock ID, timestamp, operation, and the process that holds the lock.

To read the current state (does not acquire a lock and is safe to run at any time):

```bash
cd envs/dev && terraform show
cd envs/prod && terraform show
```

**Do not run any of the following automatically:**

```bash
# FORBIDDEN — never run automatically
terraform force-unlock <LOCK_ID>       # requires explicit user instruction
terraform plan -lock=false             # bypasses locking — never use this
terraform apply -lock=false            # bypasses locking — never use this
```

If a lock is suspected to be stale, report the Lock ID to the user and ask them to run the unlock command manually from the affected environment directory.

## Reporting Reminder

When a command was not executed, say so clearly and explain why. When verification was blocked by a state lock, report it as blocked, not as failed.
