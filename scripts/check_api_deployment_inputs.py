"""Check that every API Gateway setting resource feeds the deployment's redeployment trigger.

modules/media_api gathers its methods, integrations, method responses, integration responses and
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

# Resource type suffix -> name of the local that must contain every resource of the type.
TRACKED_TYPES: Final = {
    "method": "api_methods",
    "integration": "api_integrations",
    "method_response": "api_method_responses",
    "integration_response": "api_integration_responses",
    "gateway_response": "api_gateway_responses",
}
# merge() in api_methods and api_integrations silently drops one of two entries with the same key.
DISJOINT_TABLES: Final = ("api_routes", "cors_preflights")
OPENING: Final = "{[("
CLOSING: Final = "}])"
# Strings are matched first, because they can contain comment markers such as the `/*` in "private/*".
STRING_OR_COMMENT: Final = re.compile(r'"(?:\\.|[^"\\\n])*"|(?:#|//)[^\n]*|/\*.*?\*/', flags=re.DOTALL)


def without_comments(source: str) -> str:
    return STRING_OR_COMMENT.sub(lambda match: match.group() if match.group().startswith('"') else "", source)


def module_source() -> str:
    return without_comments("\n".join(path.read_text(encoding="utf-8") for path in sorted(MODULE_DIR.glob("*.tf"))))


def declared_resources(source: str, resource_type: str) -> dict[str, bool]:
    """Return resource name -> whether the resource uses for_each."""
    pattern = rf'^resource\s+"aws_api_gateway_{resource_type}"\s+"(\w+)"\s*\{{\n(\s*for_each\s*=)?'
    return {name: bool(for_each) for name, for_each in re.findall(pattern, source, flags=re.MULTILINE)}


def local_expression(source: str, local_name: str) -> str | None:
    """Return the text of a local's value, or None when the local is missing."""
    match = re.search(rf"^\s*{local_name}\s*=[ \t]*", source, flags=re.MULTILINE)
    if match is None:
        return None
    depth = 0
    for position in range(match.end(), len(source)):
        character = source[position]
        if character in OPENING:
            depth += 1
        elif character in CLOSING:
            depth -= 1
        elif character == "\n" and depth == 0:
            return source[match.end() : position]
    return source[match.end() :]


def whole_map_references(expression: str, resource_type: str) -> set[str]:
    """Return the resources referenced as a whole map, which excludes `name[...]` and `name.attribute`."""
    return set(re.findall(rf"\baws_api_gateway_{resource_type}\.(\w+)\b(?![\[.\w])", expression))


def listed_entries(expression: str, resource_type: str) -> list[tuple[str, str]]:
    """Return the (key, resource name) pairs written as `key = aws_api_gateway_<type>.<name>`."""
    pattern = rf"^\s*(\w+)\s*=\s*aws_api_gateway_{resource_type}\.(\w+)\s*$"
    return re.findall(pattern, expression, flags=re.MULTILINE)


def top_level_keys(expression: str) -> set[str]:
    """Return the keys of a map literal, ignoring those nested in its values."""
    keys: set[str] = set()
    depth = 0
    for line in expression.splitlines():
        if depth == 1 and (match := re.match(r"\s*(\w+)\s*=", line)):
            keys.add(match.group(1))
        depth += sum(line.count(character) for character in OPENING) - sum(line.count(character) for character in CLOSING)
    return keys


def check_resource_type(source: str, resource_type: str, local_name: str) -> list[str]:
    declared = declared_resources(source, resource_type)
    expression = local_expression(source, local_name)
    if expression is None:
        return [f"local.{local_name} is missing from {MODULE_DIR.relative_to(REPO_ROOT)}"]

    entries = listed_entries(expression, resource_type)
    whole_maps = whole_map_references(expression, resource_type)
    listed_names = {name for _, name in entries}
    resource = f"aws_api_gateway_{resource_type}"
    problems: list[str] = []

    missing = sorted(name for name in declared if name not in (whole_maps if declared[name] else listed_names))
    if missing:
        problems.append(f"local.{local_name} does not contain {resource}: {', '.join(missing)}")
    unknown = sorted((whole_maps | listed_names) - declared.keys())
    if unknown:
        problems.append(f"local.{local_name} contains undeclared {resource}: {', '.join(unknown)}")
    mismatched = sorted(key for key, name in entries if key != name)
    if mismatched:
        problems.append(f"local.{local_name}: keys must match the resource names: {', '.join(mismatched)}")
    return problems


def check_disjoint_tables(source: str) -> list[str]:
    tables = {name: local_expression(source, name) for name in DISJOINT_TABLES}
    problems = [f"local.{name} is missing" for name, expression in tables.items() if expression is None]
    if problems:
        return problems
    first, second = (top_level_keys(expression or "") for expression in tables.values())
    shared = sorted(first & second)
    return [f"{' and '.join(f'local.{name}' for name in tables)} share keys: {', '.join(shared)}"] if shared else []


def main() -> int:
    source = module_source()
    problems: list[str] = []
    for resource_type, local_name in TRACKED_TYPES.items():
        type_problems = check_resource_type(source, resource_type, local_name)
        problems += type_problems
        if not type_problems:
            count = len(declared_resources(source, resource_type))
            print(f"OK aws_api_gateway_{resource_type}: {count} resource(s) in local.{local_name}")
    problems += check_disjoint_tables(source)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print("Every API Gateway setting resource feeds the redeployment trigger.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
