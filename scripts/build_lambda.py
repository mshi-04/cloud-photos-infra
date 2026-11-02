"""Build one Lambda ZIP per function group, and the Lambda layer ZIPs, into .build/.

A function group is a package under lambda/cloud_photos/ that has a module defining `handler`.
Each ZIP contains cloud_photos/__init__.py, the group package, and the shared packages it imports
(followed through `cloud_photos.<package>` imports). Tests and caches are left out.

A layer is a directory under lambda/layers/ with a requirements.txt. With --with-layers, its pinned
requirements are installed with the AWS SAM build image (Docker is required) and packed into
.build/<layer>_layer.zip under python/. --layer-from packs a directory that was installed some
other way, for example by `pip install --target` without Docker.

The ZIPs are reproducible: entries are sorted, and timestamps and permissions are fixed, so the
same inputs always give the same bytes and the same hash in Terraform. Bytecode is not compiled,
because .pyc files record the time they were written.

Run from anywhere: `python scripts/build_lambda.py [--with-layers]`.
"""

import argparse
import ast
import os
import shutil
import subprocess
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

LAYERS_DIR: Final = SOURCE_ROOT / "layers"
# Lambda adds python/ of each layer to the module search path.
LAYER_PYTHON_DIR: Final = "python"
# The build image is pinned by tag and digest, so that the same requirements install the same files.
# Pulling the image and installing the requirements normally take a few minutes.
LAYER_INSTALL_TIMEOUT_SECONDS: Final = 20 * 60
BUILD_IMAGE: Final = (
    "public.ecr.aws/sam/build-python3.12:1.170.0-x86_64@sha256:4eda3c4611584d96724726d0569ad9334084291cc4ea5e9416026dcb28054f25"
)


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
    # The same mode for every entry, so that the hash does not depend on the host's file permissions.
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


def layer_names() -> list[str]:
    return sorted(path.parent.name for path in LAYERS_DIR.glob("*/requirements.txt"))


def install_layer(name: str, target: Path) -> None:
    """Install the layer's requirements into target with the pinned build image."""
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    command = ["docker", "run", "--rm", "--env", "HOME=/tmp"]
    if hasattr(os, "getuid"):
        # Write the files as the current user, so that the next build can remove them.
        command += ["--user", f"{os.getuid()}:{os.getgid()}"]
    command += [
        "--mount",
        f"type=bind,source={target},target=/out",
        "--mount",
        f"type=bind,source={LAYERS_DIR / name},target=/requirements,readonly",
        BUILD_IMAGE,
        "pip",
        "install",
        "--no-compile",
        "--no-cache-dir",
        "--disable-pip-version-check",
        "--quiet",
        "--requirement",
        "/requirements/requirements.txt",
        "--target",
        "/out",
    ]
    try:
        subprocess.run(command, check=True, timeout=LAYER_INSTALL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise SystemExit(f"Installing layer {name} did not finish in {LAYER_INSTALL_TIMEOUT_SECONDS // 60} minutes") from None


def build_layer(name: str, installed_dir: Path, output_dir: Path) -> Path:
    """Pack a directory filled by `pip install --target` into a layer ZIP, under python/."""
    if not installed_dir.is_dir():
        raise SystemExit(f"Layer directory {installed_dir} does not exist")
    files = sorted(
        path
        for path in installed_dir.rglob("*")
        if path.is_file() and "__pycache__" not in path.relative_to(installed_dir).parts and path.suffix not in EXCLUDED_SUFFIXES
    )

    output = output_dir / f"{name}_layer.zip"
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for path in files:
            name_in_zip = f"{LAYER_PYTHON_DIR}/{path.relative_to(installed_dir).as_posix()}"
            write_entry(archive, name_in_zip, path.read_bytes())
    return output


def parse_layer_dirs(values: list[str]) -> dict[str, Path]:
    layers = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not name or not path:
            raise SystemExit(f"--layer-from must be LAYER=DIR, got {value!r}")
        if name not in layer_names():
            raise SystemExit(f"Unknown layer {name!r}; layers are {', '.join(layer_names())}")
        layers[name] = Path(path).resolve()
    return layers


def display_path(path: Path) -> Path:
    return path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="where to write the ZIPs (default: .build/)")
    parser.add_argument(
        "--with-layers",
        action="store_true",
        help="install every layer's requirements with the pinned build image (needs Docker) and build the layer ZIPs",
    )
    parser.add_argument(
        "--layer-from",
        action="append",
        default=[],
        metavar="LAYER=DIR",
        help="build a layer ZIP from a directory already filled by `pip install --target`",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir.resolve()

    groups = function_groups()
    if not groups:
        print(f"No function groups found under {SOURCE_ROOT / PACKAGE}", file=sys.stderr)
        return 1
    for group in groups:
        print(f"Built {display_path(build_group(group, output_dir))}")

    layer_dirs = parse_layer_dirs(args.layer_from)
    if args.with_layers:
        for name in layer_names():
            if name not in layer_dirs:
                layer_dirs[name] = output_dir / "layers" / name
                install_layer(name, layer_dirs[name])
    for name, installed_dir in sorted(layer_dirs.items()):
        print(f"Built {display_path(build_layer(name, installed_dir, output_dir))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
