# Guardrails for AI Changes

This document defines repository-wide safety rules for AI agents.

## Destructive Changes

- Never introduce a destructive Terraform change without explicitly warning the user.
- Never treat resource replacement as a harmless refactor.
- Treat changes that may delete, recreate, or significantly alter core infrastructure resources as high risk.
- If a change may affect data retention, downtime risk, or permission scope, call it out clearly before completion.

## Execution Safety

- Never run `terraform apply` unless the user explicitly requests it.
- Never assume cloud credentials, backend access, or environment initialization are available.
- If validation or planning cannot be executed because prerequisites are missing, report that explicitly instead of guessing.

## Terraform State Lock Safety

- **Never run `terraform force-unlock` automatically.** State unlocking is a manual, user-initiated action only.
- **Never use `-lock=false`** as a workaround for lock conflicts. Bypassing the lock mechanism risks corrupting shared state.
- If a state lock is detected during `terraform plan` or `terraform validate`, read the lock error output and report the following to the user:
  - Which environment is locked (e.g., `envs/dev`, `envs/prod`)
  - The Lock ID, timestamp, and operation shown in the error (if available)
  - Whether the lock likely originated from a concurrent CI run or a local run that did not release cleanly
- Treat a lock conflict as an execution/coordination issue, not as evidence that the code change is wrong.
- Tell the user explicitly: the lock must be removed manually if it appears stale, and provide the Lock ID so they can run `terraform force-unlock <ID>` themselves.
- Never claim verification passed when it was blocked by a state lock. Report it as a distinct blocked state (see [VERIFICATION_POLICY.md](./VERIFICATION_POLICY.md)).

## Bootstrap Safety

- Treat everything under `bootstrap/` as high-impact setup infrastructure.
- Do not assume bootstrap changes are handled by the normal CI/CD pipeline.
- Mention any manual follow-up work that may be required after a bootstrap change.

## Secrets and Environment Data

- Avoid hardcoding secrets, tokens, private keys, or passwords.
- Do not commit environment-specific values — supply them through managed configuration.
- Never expose sensitive values in logs, examples, comments, or completion reports.

## Module Design Rules

- Never place environment branching logic inside reusable Terraform modules.
- Keep environment differences in environment root modules.
- Do not add security-sensitive defaults that weaken protections in production.

## IAM and Security Rules

- Follow least privilege for every IAM change.
- Avoid wildcard actions whenever the service allows explicit action lists.
- Scope resources as narrowly as practical.
- Do not loosen permissions only to make CI or local testing easier.

## Lambda and Logging Rules

- Do not log personal data, secrets, raw tokens, or credentials.
- Prefer minimal error context.
- Add or update tests when Lambda behavior changes.
- Do not change response contracts silently.

## Reporting Rules

- Do not claim verification steps were completed if they were not actually completed.
- Distinguish clearly between passed, failed, and not executed.
- Always mention remaining manual steps, assumptions, and unresolved risks.

## When in Doubt

- Choose the safer interpretation.
- Prefer explicit user approval before a risky change.
- Prefer a smaller safe change over a larger speculative one.
