"""Check that every handler imports from the built Lambda ZIPs alone.

Each ZIP in .build/ is extracted to a temporary directory. A separate process started with
`python -I -S`, in that temporary directory, imports every module that defines `handler`. Its
module search path holds only the extracted ZIP, the layer's python/ for groups that use a layer,
and a directory with the packages the Lambda runtime provides (boto3). The source tree,
PYTHONPATH and the development site-packages are not on the path, so a module missing from the
ZIP fails the check.

Prepare the runtime packages once, outside .build/ so they are not deployed:

    python -m pip install --target <dir> boto3

Then run, after `python scripts/build_lambda.py`:

    python scripts/verify_lambda_packages.py --runtime-deps <dir> \
        --layer push_notification=.build/firebase_admin_layer.zip
"""

import argparse
import ast
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Final

from build_lambda import OUTPUT_DIR, PACKAGE, REPO_ROOT, function_groups

CHILD_CODE: Final = """
import importlib, json, sys
config = json.loads(sys.argv[1])
sys.path[:0] = config["paths"]
failures = []
for name in config["modules"]:
    try:
        module = importlib.import_module(name)
    except Exception as error:
        failures.append(f"{name}: {type(error).__name__}: {error}")
        continue
    if not callable(getattr(module, "handler", None)):
        failures.append(f"{name}: no callable handler")
    elif not module.__file__.startswith(config["package_root"]):
        failures.append(f"{name}: loaded from {module.__file__}, not from the ZIP")
print(json.dumps(failures))
sys.exit(1 if failures else 0)
"""


def handler_modules(archive: zipfile.ZipFile, group: str) -> list[str]:
    prefix = f"{PACKAGE}/{group}/"
    modules = []
    for name in sorted(archive.namelist()):
        if not name.startswith(prefix) or not name.endswith(".py") or "/" in name[len(prefix) :]:
            continue
        tree = ast.parse(archive.read(name), filename=name)
        if any(isinstance(node, ast.FunctionDef) and node.name == "handler" for node in tree.body):
            modules.append(name.removesuffix(".py").replace("/", "."))
    return modules


def layer_python_dir(layer: Path, workdir: Path) -> Path | None:
    """Return the layer's python/ directory, which Lambda adds to the path, or None if it is missing."""
    if layer.is_file():
        target = workdir / "layer"
        with zipfile.ZipFile(layer) as archive:
            archive.extractall(target)
        layer = target
    python_dir = layer / "python"
    return python_dir if python_dir.is_dir() else None


def verify_group(group: str, zip_path: Path, runtime_deps: Path, layer: Path | None) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        package_root = workdir / "package"
        with zipfile.ZipFile(zip_path) as archive:
            modules = handler_modules(archive, group)
            archive.extractall(package_root)
        if not modules:
            return [f"{zip_path.name}: no module defines handler"]

        paths = [str(package_root)]
        if layer is not None:
            python_dir = layer_python_dir(layer, workdir)
            if python_dir is None:
                return [f"{zip_path.name}: layer {layer} has no python/ directory, so Lambda would not load it"]
            paths.append(str(python_dir))
        paths.append(str(runtime_deps))
        config = {"paths": paths, "modules": modules, "package_root": str(package_root)}

        result = subprocess.run(
            [sys.executable, "-I", "-S", "-c", CHILD_CODE, json.dumps(config)],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print(f"OK {zip_path.name}: {', '.join(modules)}")
            return []
        try:
            return [f"{zip_path.name}: {failure}" for failure in json.loads(result.stdout.splitlines()[-1])]
        except (IndexError, json.JSONDecodeError):
            return [f"{zip_path.name}: check process failed: {result.stderr.strip()}"]


def parse_layers(values: list[str]) -> dict[str, Path]:
    layers = {}
    for value in values:
        group, separator, path = value.partition("=")
        if not separator or not path:
            raise SystemExit(f"--layer must be GROUP=PATH, got {value!r}")
        layers[group] = Path(path).resolve()
    return layers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip-dir", type=Path, default=OUTPUT_DIR, help="directory with the built ZIPs (default: .build/)")
    parser.add_argument("--runtime-deps", type=Path, required=True, help="directory with boto3 installed by pip --target")
    parser.add_argument("--layer", action="append", default=[], metavar="GROUP=PATH", help="layer ZIP or directory for a group")
    args = parser.parse_args(argv)

    layers = parse_layers(args.layer)
    groups = function_groups()
    unknown = sorted(set(layers) - set(groups))
    if unknown:
        print(f"--layer names unknown groups: {', '.join(unknown)}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for group in groups:
        zip_path = args.zip_dir.resolve() / f"{group}.zip"
        if not zip_path.is_file():
            failures.append(f"{group}.zip does not exist; run scripts/build_lambda.py first")
            continue
        layer = layers.get(group)
        if layer is not None and not layer.exists():
            failures.append(f"layer for {group} does not exist: {layer}")
            continue
        failures.extend(verify_group(group, zip_path, args.runtime_deps.resolve(), layer))

    for failure in failures:
        print(f"FAILED {failure}", file=sys.stderr)
    if failures:
        return 1
    print(
        f"All handlers import from the ZIPs in {args.zip_dir.resolve().relative_to(REPO_ROOT) if args.zip_dir.resolve().is_relative_to(REPO_ROOT) else args.zip_dir}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
