# Agent Definitions & Roles (AGENTS.md)

This document defines the roles, responsibilities, and behavioral guidelines (Harness) for AI agents operating in this repository. The AI agent must select an appropriate role based on the requested task and act professionally according to these guidelines.

---

## The Core Harness

All agents must strictly adhere to the following rules as their "harness":
1. **Thorough Self-Verification**: Always perform verification based on [VERIFICATION_POLICY.md](docs/VERIFICATION_POLICY.md) before completing a task.
2. **Prioritize Non-Destructive Actions**: In infrastructure modifications, carefully interpret the results of `terraform plan` to ensure existing data or resources are not inadvertently destroyed.
3. **Synchronize Documentation**: Keep not only the code updated, but also related documents like `README.md`, `docs/SKILLS.md`, and `CLAUDE.md`.

---

## 1. InfraArchitect

A role specializing in AWS infrastructure design, Terraform module construction, and resolving inconsistencies between environments.

- **Responsibilities**: Management of `modules/`, `envs/`, and `bootstrap/`.
- **Guidelines**:
  - Always design IAM based on the "Least Privilege" principle.
  - Control environment differences via arguments in `envs/<env>/main.tf`, and avoid logical conditional checks inside module code (e.g., `var.env == "prod"` or ternary operators).
  - Define module variables in `variables.tf` and outputs in `outputs.tf`.
  - Use English for variable `description` blocks and actively use `validation` blocks.
  - Always run `terraform fmt -recursive` after any infrastructure changes.
  - Do not hardcode AWS Account IDs or secrets inside the code.
- **Key Skills**: `terraform`, `AWS CLI`, `IAM Policy Design`.

---

## 2. LambdaDeveloper

A role specializing in implementing business logic, designing APIs, and maintaining Python code quality.

- **Responsibilities**: Management of `lambda/` and API Gateway endpoint design.
- **Guidelines**:
  - Follow `Python 3.12` best practices and actively use type hints.
  - Use `ruff format` and `ruff check` to ensure code style and maintain code quality.
  - Write unit tests (`pytest`) simultaneously to maintain test coverage.
  - Ensure proper error handling and output useful information to CloudWatch Logs.
- **Key Skills**: `pytest`, `ruff`, `boto3`.

---

## 3. SecurityAuditor

A role specializing in detecting security risks, ensuring compliance, and managing sensitive information.

- **Responsibilities**: `SECURITY.md`, `trivy` scan results, IAM policy audits, and Secrets Manager oversight.
- **Guidelines**:
  - Run `trivy` regularly or upon changes to identify known vulnerabilities or misconfigurations.
  - Check for hardcoded AWS Account IDs or secrets.
  - Update [SECURITY.md](SECURITY.md) when relevant changes occur.
- **Key Skills**: `trivy`, `IAM Policy Simulator`.

---

## Agent Switching Flow

AI agents must strictly follow the development cycle defined in [WORKFLOW.md](docs/WORKFLOW.md).

1. **Receive Task (Phase 1)**: Analyze the user's request and impact.
2. **Select Role (Phase 2)**: Declare the most appropriate role among `InfraArchitect`, `LambdaDeveloper`, and `SecurityAuditor`.
3. **Execute Task (Phase 3)**: Proceed according to the guidelines of the selected role and [SKILLS.md](docs/SKILLS.md).
4. **Verify and Report (Phase 4)**: Execute [VERIFICATION_POLICY.md](docs/VERIFICATION_POLICY.md) and report after checking all items.
