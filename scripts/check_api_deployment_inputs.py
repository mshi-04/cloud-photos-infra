"""Check that every API Gateway setting resource feeds the deployment's redeployment trigger.

modules/media_api lists its methods, integrations, method responses, integration responses and
gateway responses in locals, and the deployment is replaced when any of their settings changes.
A resource that is declared but missing from those locals would change the API without
redeploying the stage. This check finds such resources without AWS credentials.

Run from anywhere: `python scripts/check_api_deployment_inputs.py`.
"""

import re
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
MODULE_DIR: Final = REPO_ROOT / "modules" / "media_api"

# Resource type suffix -> name of the locals map that must list every resource of the type.
TRACKED_TYPES: Final = {
    "method": "api_methods",
    "integration": "api_integrations",
    "method_response": "api_method_responses",
    "integration_response": "api_integration_responses",
    "gateway_response": "api_gateway_responses",
}


def module_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(MODULE_DIR.glob("*.tf")))


def declared_names(source: str, resource_type: str) -> set[str]:
    pattern = rf'^resource\s+"aws_api_gateway_{resource_type}"\s+"(\w+)"'
    return set(re.findall(pattern, source, flags=re.MULTILINE))


def listed_names(source: str, local_name: str, resource_type: str) -> set[str] | None:
    """Return the resources listed in a locals map, or None when the map is missing."""
    match = re.search(rf"^\s*{local_name}\s*=\s*\{{(.*?)^\s*\}}", source, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        return None
    entries = re.findall(rf"^\s*(\w+)\s*=\s*aws_api_gateway_{resource_type}\.(\w+)\s*$", match.group(1), flags=re.MULTILINE)
    mismatched = [key for key, name in entries if key != name]
    if mismatched:
        print(f"{local_name}: keys must match the resource names: {', '.join(mismatched)}", file=sys.stderr)
    return {name for _, name in entries}


def main() -> int:
    source = module_source()
    failed = False
    for resource_type, local_name in TRACKED_TYPES.items():
        declared = declared_names(source, resource_type)
        listed = listed_names(source, local_name, resource_type)
        if listed is None:
            print(f"local.{local_name} is missing from {MODULE_DIR.relative_to(REPO_ROOT)}", file=sys.stderr)
            failed = True
            continue
        missing = sorted(declared - listed)
        unknown = sorted(listed - declared)
        if missing:
            print(f"local.{local_name} does not list aws_api_gateway_{resource_type}: {', '.join(missing)}", file=sys.stderr)
        if unknown:
            print(f"local.{local_name} lists undeclared aws_api_gateway_{resource_type}: {', '.join(unknown)}", file=sys.stderr)
        if missing or unknown:
            failed = True
            continue
        print(f"OK aws_api_gateway_{resource_type}: {len(declared)} resource(s) in local.{local_name}")
    if failed:
        return 1
    print("Every API Gateway setting resource feeds the redeployment trigger.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
