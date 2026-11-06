"""Check that bootstrap lists the Lambda functions that modules/media_api declares.

bootstrap grants iam:PassRole on the role of each function named in local.lambda_function_names. It is a
separate root module and cannot read media_api, so the two lists are compared here. A function missing
from bootstrap would make the apply of CD fail on PassRole. This check needs no AWS credentials.

Run from anywhere: `python scripts/check_lambda_role_names.py`.
"""

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Final

from check_api_deployment_inputs import local_expression, without_comments

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
BOOTSTRAP_FILE: Final = REPO_ROOT / "bootstrap" / "oidc_roles.tf"
MEDIA_API_FILE: Final = REPO_ROOT / "modules" / "media_api" / "main.tf"


def source_of(path: Path) -> str:
    return without_comments(path.read_text(encoding="utf-8"))


def bootstrap_names() -> list[str]:
    expression = local_expression(source_of(BOOTSTRAP_FILE), "lambda_function_names") or ""
    return re.findall(r'"([^"]+)"', expression)


def media_api_names() -> list[str]:
    expression = local_expression(source_of(MEDIA_API_FILE), "lambda_functions") or ""
    return re.findall(r'^\s*name\s*=\s*"([^"]+)"', expression, flags=re.MULTILINE)


def duplicates(names: list[str]) -> list[str]:
    return sorted(name for name, count in Counter(names).items() if count > 1)


def main() -> int:
    bootstrap, media_api = bootstrap_names(), media_api_names()
    problems: list[str] = []
    if not bootstrap:
        problems.append(f"local.lambda_function_names has no names in {BOOTSTRAP_FILE.relative_to(REPO_ROOT)}")
    if not media_api:
        problems.append(f"local.lambda_functions has no names in {MEDIA_API_FILE.relative_to(REPO_ROOT)}")
    if repeated := duplicates(bootstrap):
        problems.append(f"local.lambda_function_names in bootstrap repeats: {', '.join(repeated)}")
    if repeated := duplicates(media_api):
        problems.append(f"local.lambda_functions in media_api repeats: {', '.join(repeated)}")
    if bootstrap and media_api:
        if missing := sorted(set(media_api) - set(bootstrap)):
            problems.append(f"local.lambda_function_names in bootstrap lacks: {', '.join(missing)}")
        if unknown := sorted(set(bootstrap) - set(media_api)):
            problems.append(f"local.lambda_function_names in bootstrap has functions unknown to media_api: {', '.join(unknown)}")
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"bootstrap and media_api list the same {len(media_api)} Lambda functions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
