"""Build one Lambda ZIP per function group into .build/.

A function group is a package under lambda/cloud_photos/ that has a module defining `handler`.
Each ZIP contains cloud_photos/__init__.py, the group package, and the shared packages it imports
(followed through `cloud_photos.<package>` imports). Tests and caches are left out.

The ZIPs are reproducible: entries are sorted, and timestamps and permissions are fixed, so the
same sources always give the same bytes and the same hash in Terraform.

Run from anywhere: `python scripts/build_lambda.py`.
"""

import argparse
import ast
import sys
import zipfile
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
SOURCE_ROOT: Final = REPO_ROOT / "lambda"
PACKAGE: Final = "cloud_photos"
OUTPUT_DIR: Final = REPO_ROOT / ".build"

EXCLUDED_DIRS: Final = frozenset({"tests", "__pycache__", ".pytest_cache", ".ruff_cache"})
EXCLUDED_SUFFIXES: Final = frozenset({".pyc", ".pyo"})
FIXED_DATE_TIME: Final = (1980, 1, 1, 0, 0, 0)
FILE_MODE: Final = 0o100644
UNIX_SYSTEM: Final = 3
COMPRESS_LEVEL: Final = 9


def package_dir(name: str) -> Path:
    return SOURCE_ROOT / PACKAGE / name


def package_files(name: str) -> list[Path]:
    """Return the files of a package, without tests and caches."""
    files = []
    for path in package_dir(name).rglob("*"):
        relative = path.relative_to(package_dir(name))
        if not path.is_file() or EXCLUDED_DIRS.intersection(relative.parts[:-1]) or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def defines_handler(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return any(isinstance(node, ast.FunctionDef) and node.name == "handler" for node in tree.body)


def function_groups() -> list[str]:
    groups = []
    for directory in sorted((SOURCE_ROOT / PACKAGE).iterdir()):
        if directory.is_dir() and any(defines_handler(path) for path in directory.glob("*.py")):
            groups.append(directory.name)
    return groups


def imported_packages(path: Path) -> set[str]:
    """Return the cloud_photos subpackages that a module imports."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules = [node.module]
        elif isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        for module in modules:
            parts = module.split(".")
            if parts[0] == PACKAGE and len(parts) > 1:
                names.add(parts[1])
    return names


def required_packages(group: str) -> list[str]:
    """Return the group and every shared package it imports, directly or indirectly."""
    required = {group}
    pending = [group]
    while pending:
        current = pending.pop()
        for path in package_files(current):
            if path.suffix != ".py":
                continue
            for name in imported_packages(path) - required:
                if not package_dir(name).is_dir():
                    raise SystemExit(f"{path.relative_to(REPO_ROOT)} imports {PACKAGE}.{name}, which does not exist")
                required.add(name)
                pending.append(name)
    return sorted(required)


def write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_DATE_TIME)
    info.create_system = UNIX_SYSTEM
    info.external_attr = FILE_MODE << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compresslevel=COMPRESS_LEVEL)


def build_group(group: str, output_dir: Path) -> Path:
    entries = {f"{PACKAGE}/__init__.py": (SOURCE_ROOT / PACKAGE / "__init__.py").read_bytes()}
    for name in required_packages(group):
        for path in package_files(name):
            entries[path.relative_to(SOURCE_ROOT).as_posix()] = path.read_bytes()

    output = output_dir / f"{group}.zip"
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name in sorted(entries):
            write_entry(archive, name, entries[name])
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="where to write the ZIPs (default: .build/)")
    args = parser.parse_args(argv)

    groups = function_groups()
    if not groups:
        print(f"No function groups found under {SOURCE_ROOT / PACKAGE}", file=sys.stderr)
        return 1
    for group in groups:
        output = build_group(group, args.output_dir.resolve())
        print(f"Built {output.relative_to(REPO_ROOT) if output.is_relative_to(REPO_ROOT) else output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
