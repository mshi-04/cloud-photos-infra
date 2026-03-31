# Bootstrap Local Agent Guide

This guide applies only to the bootstrap directory.

## Purpose

Bootstrap contains setup resources that support the rest of the repository.

## Working Style

- Prefer small and isolated edits.
- Explain the expected impact of the change in plain language.
- Mention when follow-up manual work may be needed.
- Keep the structure and naming consistent with existing bootstrap files.

## Review Focus

- state backend resources
- encryption-related resources
- OIDC providers and IAM roles
- shared permissions used by environments or workflows

## State Lock During Verification

Bootstrap has its own Terraform state separate from environment states. If `terraform plan` or `terraform validate` in `bootstrap/` is blocked by a state lock:
- Do not retry with `-lock=false`.
- Do not run `terraform force-unlock` automatically.
- Report the Lock ID, timestamp, and suspected source of the lock to the user.
- Ask the user to manually unlock before re-running verification.
- Mark the verification step as **Blocked by Terraform state lock** in the completion report.

## Notes for Completion Reports

When reporting bootstrap work, include:
- what changed
- why the change was needed
- what may need to be done next
- what parts of the repository are related to the change
- whether Terraform verification was executed, blocked by a state lock, or skipped with reason
