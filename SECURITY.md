# Security Policy

## Supported Versions

| Branch | Support Status |
|--------|----------------|
| main   | :white_check_mark: |
| develop| :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please help us by disclosing it responsibly.

**Do not create a public issue for security vulnerabilities.**

Instead, please report them via [GitHub Private Vulnerability Reporting](https://github.com/mshi-04/cloud-photos-infra/security/advisories/new).

### Information to Include in Your Report

- Overview of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested mitigation (if any)

### Response Timeline

- **Acknowledgement**: Within 3 business days
- **Initial Assessment**: Within 7 business days
- **Fix/Mitigation**: Depending on severity

## Contributor Security Guidelines

- Do not commit secrets, credentials, or AWS Account IDs to the repository.
- Infrastructure changes must always go through a Pull Request.
- Do not commit Terraform state files to the repository.
- Manage sensitive information securely using environment variables or AWS Secrets Manager.
