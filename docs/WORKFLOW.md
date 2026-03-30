# Development Workflow

This document outlines the standard development cycle in this repository. Both AI agents and human developers must follow these phases to ensure architectural integrity and infrastructure safety.

---

## Phase 1: Planning & Research

Before modifying any files, perform an initial assessment of the task.
1. **Understand Requirements**: Clarify the goal and constraints of the user request.
2. **Impact Analysis**: Identify which Terraform modules (`modules/`), environments (`envs/`), or Lambda functions (`lambda/`) are affected.
3. **Environment Check**: Run `terraform plan` on the target environments (usually start with `dev`) to establish a baseline.

## Phase 2: Role Selection

Refer to [AGENTS.md](../AGENTS.md) to choose the appropriate role for the task.
- **Select Role(s)**: Declare whether you are acting as an `InfraArchitect`, `LambdaDeveloper`, `SecurityAuditor`, or a combination.
- **Declare Intent**: State the selected role and the high-level plan before starting implementation.

## Phase 3: Implementation

Follow the guidelines in [CLAUDE.md](../CLAUDE.md) and [SKILLS.md](./SKILLS.md).
1. **Branching Strategy**:
   - Create a feature branch (e.g., `feature/<task-name>`) for significant changes.
   - **Exception: Direct changes to `develop`**:
     - **Authorized by**: Requires explicit permission from the Repository Administrator (the User).
     - **Applicable Changes**: Limited to minor documentation typos, non-functional markup changes, or trivial configuration tweaks. No code logic changes allowed.
     - **Review Process**: AI must explicitly ask the user for approval before committing directly. Alternatively, if authorized, report the changes immediately after merging.
     - **Procedure**: When asking for approval, explicitly state that the change meets the criteria for a direct `develop` commit.
2. **Development**: Implement changes following the project's coding standards.
   - Use English for code and comments.
   - Adhere to the "Least Privilege" principle for IAM changes.
3. **Synchronization**: Ensure related documents (README, SKILLS, etc.) are kept up-to-date with your changes.

## Phase 4: Verification

Mandatory self-verification as defined in [VERIFICATION_POLICY.md](./VERIFICATION_POLICY.md).
1. **Static Analysis**: Run `terraform fmt`/`terraform validate` for infrastructure. Run `ruff format` and `ruff check` for Python code.
2. **Testing**: Run `pytest` for any modified Lambda functions.
3. **Review Plan**: Execute `terraform plan` and ensure the output matches expectations. **Never proceed with unintended resource destructions.**
4. **Final Check**: Complete the "Completion Reporting Requirements" in `VERIFICATION_POLICY.md`.

## Phase 5: Release & Deployment

Follow the CI/CD pipeline as described in [CLAUDE.md](../CLAUDE.md).
1. **Pull Request**: Create a PR to merge your changes into the `main` or `develop` branch.
2. **CI Check**: Ensure the GitHub Actions CI (Plan dev/prod) passes successfully.
3. **Deployment**:
   - **Dev**: Automatically applied upon merge.
   - **Prod**: Requires manual approval in the GitHub Environment after a successful dev deployment.
