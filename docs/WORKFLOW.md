# Development Workflow

This document outlines the standard development cycle in this repository. Both AI agents and human developers must follow these phases to ensure architectural integrity and infrastructure safety.

---

## Phase 1: Planning & Research

Before modifying any files, perform an initial assessment of the task.
1. **Understand Requirements**: Clarify the goal and constraints of the user request.
2. **Impact Analysis**: Identify which Terraform modules (`modules/`), environments (`envs/`), or Lambda functions (`lambda/`) are affected.
3. **Environment Check**: Run `terraform plan` on the target environments when available, usually starting with `dev`, to establish a baseline.

## Phase 2: Role Selection

Refer to [AGENTS.md](../AGENTS.md) to choose the appropriate role for the task.
- **Select Role(s)**: Declare whether you are acting as an `InfraArchitect`, `LambdaDeveloper`, `SecurityAuditor`, or a combination.
- **Declare Intent**: State the selected role and the high-level plan before starting implementation.

## Phase 3: Implementation

Follow the guidelines in [CLAUDE.md](../CLAUDE.md) and [SKILLS.md](./SKILLS.md).
1. **Branching Strategy**:
   - Create a feature branch (for example `feature/<task-name>`) for significant changes.
   - Open a pull request against the repository's active target branch.
   - If direct changes to `develop` are exceptionally allowed by the repository administrator, limit them to minor documentation typos, non-functional markup changes, or trivial configuration tweaks.
   - Do not assume that `develop` exists or is the default integration branch unless the user or repository configuration makes that explicit.
2. **Development**: Implement changes following the project's coding standards.
   - Use English for code and comments.
   - Adhere to the Least Privilege principle for IAM changes.
3. **Synchronization**: Ensure related documents (README, SKILLS, workflow docs, and local guides) are kept up to date with your changes.

## Phase 4: Verification

Mandatory self-verification as defined in [VERIFICATION_POLICY.md](./VERIFICATION_POLICY.md).
1. **Static Analysis**: Run `terraform fmt` and `terraform validate` for infrastructure when available. Run `ruff format` and `ruff check` for Python code when Lambda code was modified.
2. **Testing**: Run `pytest` for any modified Lambda functions.
3. **Review Plan**: Execute `terraform plan` when credentials and initialization are available, and ensure the output matches expectations. Never proceed with unintended resource destructions.
4. **State Lock Handling**: If `terraform validate` or `terraform plan` is blocked by a state lock, stop immediately. Do not use `-lock=false` or `terraform force-unlock`. Report the locked environment, Lock ID, and suspected cause to the user. Ask the user to manually unlock if the lock appears stale. Classify the verification step as **Blocked by Terraform state lock**, not as a code failure.
5. **Final Check**: Complete the completion reporting requirements in [VERIFICATION_POLICY.md](./VERIFICATION_POLICY.md).

## Phase 5: Release & Deployment

Follow the CI/CD pipeline as described in [CLAUDE.md](../CLAUDE.md).
1. **Pull Request**: Create a PR to merge your changes into the active target branch for the repository.
2. **CI Check**: Ensure the GitHub Actions CI checks pass successfully.
3. **Deployment**:
   - **Dev**: Automatically applied upon merge if the workflow is configured for dev deployment.
   - **Prod**: Requires manual approval in the GitHub Environment after a successful dev deployment when the production workflow is enabled.
