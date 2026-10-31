"""Static checks for AI-facing documents and skills.

The checks need no AWS access and no third-party packages:

- Markdown: every code fence is closed.
- Links: relative links in Markdown point to files or directories that exist.
- Skills: each SKILL.md has front matter with `name` and `description`, and `name` matches its directory.
- Retired skills: names listed in the config are no longer referenced.
- Parity: AGENTS.md and CLAUDE.md, and .agents/skills and .claude/skills, match after `.agents` is
  rewritten to `.claude`. Intended differences are listed in the config.

Run from anywhere: `python scripts/check_ai_docs.py`. The exit code is 1 when any check fails.
"""

import argparse
import difflib
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import unquote

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
CONFIG_PATH: Final = Path(__file__).resolve().parent / "ai_docs_check.toml"

AGENTS_DIR: Final = ".agents"
CLAUDE_DIR: Final = ".claude"
SKILLS_SUBDIR: Final = "skills"
SKILL_FILE: Final = "SKILL.md"
REQUIRED_SKILL_KEYS: Final = ("name", "description")
FRONT_MATTER_DELIMITER: Final = "---"

FENCE_PATTERN: Final = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_CODE_PATTERN: Final = re.compile(r"(`+).*?\1")
INLINE_LINK_PATTERN: Final = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]*)(?:\s+[\"'(][^)]*)?\)")
REFERENCE_LINK_PATTERN: Final = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)")
EXTERNAL_LINK_PATTERN: Final = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


@dataclass(frozen=True, slots=True)
class AllowedDifference:
    path: str
    agents: tuple[str, ...]
    claude: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Config:
    source: str
    allowed_differences: tuple[AllowedDifference, ...]
    retired_skills: tuple[str, ...]
    retired_skill_exempt_paths: tuple[str, ...]


def load_config(path: Path) -> Config:
    with path.open("rb") as file:
        data = tomllib.load(file)
    parity = data.get("parity", {})
    retired = data.get("retired_skills", {})
    allowed = tuple(
        AllowedDifference(
            path=entry["path"],
            agents=tuple(entry.get("agents", [])),
            claude=tuple(entry.get("claude", [])),
        )
        for entry in parity.get("allowed", [])
    )
    return Config(
        source=path.name,
        allowed_differences=allowed,
        retired_skills=tuple(retired.get("names", [])),
        retired_skill_exempt_paths=tuple(retired.get("exempt_paths", [])),
    )


def list_markdown_files(root: Path) -> list[Path]:
    """List tracked and untracked (but not ignored) Markdown files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.md"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    names = {name for name in result.stdout.decode("utf-8").split("\0") if name}
    return sorted(root / name for name in names if (root / name).is_file())


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def is_closing_fence(line: str, marker: str, fence: str) -> bool:
    return marker[0] == fence[0] and len(marker) >= len(fence) and not line.strip(" `~")


def scan_fences(lines: list[str]) -> tuple[list[tuple[int, str]], int | None]:
    """Split lines by code fences.

    Returns (line number, text) for lines outside code fences, with inline code removed, and the line
    number of a fence that is never closed, if any.
    """
    prose: list[tuple[int, str]] = []
    fence: str | None = None
    opened_at = 0
    for number, line in enumerate(lines, start=1):
        match = FENCE_PATTERN.match(line)
        if fence is None and match:
            fence = match.group(1)
            opened_at = number
            continue
        if fence is None:
            prose.append((number, INLINE_CODE_PATTERN.sub("", line)))
            continue
        if match and is_closing_fence(line, match.group(1), fence):
            fence = None
    return prose, (opened_at if fence is not None else None)


def check_fences(root: Path, path: Path, lines: list[str]) -> list[Finding]:
    _, unclosed_at = scan_fences(lines)
    if unclosed_at is None:
        return []
    return [Finding(relative(root, path), unclosed_at, "code fence is not closed")]


def extract_link_targets(line: str) -> list[str]:
    targets = [match.group(1) for match in INLINE_LINK_PATTERN.finditer(line)]
    reference = REFERENCE_LINK_PATTERN.match(line)
    if reference:
        targets.append(reference.group(1))
    return [target.removeprefix("<").removesuffix(">") for target in targets]


def check_links(root: Path, path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    prose, _ = scan_fences(lines)
    for number, text in prose:
        for target in extract_link_targets(text):
            if not target or target.startswith("#") or EXTERNAL_LINK_PATTERN.match(target):
                continue
            target_path = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target_path:
                continue
            base = root if target_path.startswith("/") else path.parent
            resolved = (base / target_path.lstrip("/")).resolve()
            if not resolved.is_relative_to(root):
                findings.append(Finding(relative(root, path), number, f"link points outside the repository: {target}"))
                continue
            if not resolved.exists():
                findings.append(Finding(relative(root, path), number, f"link target does not exist: {target}"))
    return findings


def parse_front_matter(lines: list[str]) -> dict[str, str] | None:
    if not lines or lines[0].strip() != FRONT_MATTER_DELIMITER:
        return None
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == FRONT_MATTER_DELIMITER:
            return values
        key, separator, value = line.partition(":")
        if separator and not line.startswith((" ", "\t")):
            values[key.strip()] = value.strip()
    return None


def check_skills(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for tool_dir in (AGENTS_DIR, CLAUDE_DIR):
        skills_dir = root / tool_dir / SKILLS_SUBDIR
        if not skills_dir.is_dir():
            findings.append(Finding(f"{tool_dir}/{SKILLS_SUBDIR}", 0, "skills directory does not exist"))
            continue
        for skill_dir in sorted(entry for entry in skills_dir.iterdir() if entry.is_dir()):
            skill_file = skill_dir / SKILL_FILE
            display = relative(root, skill_file)
            if not skill_file.is_file():
                findings.append(Finding(display, 0, f"{SKILL_FILE} does not exist"))
                continue
            front_matter = parse_front_matter(skill_file.read_text(encoding="utf-8").splitlines())
            if front_matter is None:
                findings.append(Finding(display, 1, "front matter is missing or not closed"))
                continue
            findings.extend(
                Finding(display, 1, f"front matter has no `{key}`") for key in REQUIRED_SKILL_KEYS if not front_matter.get(key)
            )
            name = front_matter.get("name")
            if name and name != skill_dir.name:
                findings.append(Finding(display, 1, f"`name` is `{name}` but the directory is `{skill_dir.name}`"))
    return findings


def check_retired_skills(root: Path, config: Config, files: list[Path]) -> list[Finding]:
    if not config.retired_skills:
        return []
    pattern = re.compile(r"(?<![\w-])(" + "|".join(re.escape(name) for name in config.retired_skills) + r")(?![\w-])")
    findings: list[Finding] = []
    for path in files:
        display = relative(root, path)
        if display in config.retired_skill_exempt_paths:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            findings.extend(
                Finding(display, number, f"references retired skill `{match.group(1)}`") for match in pattern.finditer(line)
            )
    return findings


def list_relative_files(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {relative(directory, path) for path in directory.rglob("*") if path.is_file()}


def compare_pair(
    root: Path,
    agents_path: Path,
    claude_path: Path,
    display: str,
    allowed: dict[str, list[AllowedDifference]],
    used: set[AllowedDifference],
) -> list[Finding]:
    agents_lines = [
        line.replace(f"{AGENTS_DIR}/", f"{CLAUDE_DIR}/") for line in agents_path.read_text(encoding="utf-8").splitlines()
    ]
    claude_lines = claude_path.read_text(encoding="utf-8").splitlines()
    findings: list[Finding] = []
    matcher = difflib.SequenceMatcher(a=agents_lines, b=claude_lines, autojunk=False)
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        block_agents = tuple(agents_lines[a_start:a_end])
        block_claude = tuple(claude_lines[b_start:b_end])
        match = next(
            (entry for entry in allowed.get(display, []) if entry.agents == block_agents and entry.claude == block_claude),
            None,
        )
        if match is not None:
            used.add(match)
            continue
        findings.append(
            Finding(
                relative(root, claude_path),
                b_start + 1,
                f"differs from {relative(root, agents_path)} ({describe_lines(a_start, a_end)}) without an allowlist entry",
            )
        )
    return findings


def describe_lines(start: int, end: int) -> str:
    """Describe a 0-based half-open line range as 1-based text."""
    if end > start:
        return f"lines {start + 1}-{end}"
    return f"after line {start}"


def check_parity(root: Path, config: Config) -> list[Finding]:
    allowed: dict[str, list[AllowedDifference]] = {}
    for entry in config.allowed_differences:
        allowed.setdefault(entry.path, []).append(entry)
    used: set[AllowedDifference] = set()
    findings = compare_pair(root, root / "AGENTS.md", root / "CLAUDE.md", "AGENTS.md", allowed, used)

    agents_skills = root / AGENTS_DIR / SKILLS_SUBDIR
    claude_skills = root / CLAUDE_DIR / SKILLS_SUBDIR
    agents_files = list_relative_files(agents_skills)
    claude_files = list_relative_files(claude_skills)
    for name in sorted(agents_files - claude_files):
        findings.append(Finding(f"{AGENTS_DIR}/{SKILLS_SUBDIR}/{name}", 0, f"has no counterpart in {CLAUDE_DIR}/{SKILLS_SUBDIR}"))
    for name in sorted(claude_files - agents_files):
        findings.append(Finding(f"{CLAUDE_DIR}/{SKILLS_SUBDIR}/{name}", 0, f"has no counterpart in {AGENTS_DIR}/{SKILLS_SUBDIR}"))
    for name in sorted(agents_files & claude_files):
        display = f"{SKILLS_SUBDIR}/{name}"
        findings.extend(compare_pair(root, agents_skills / name, claude_skills / name, display, allowed, used))

    findings.extend(
        Finding(config.source, 0, f"allowlist entry for `{entry.path}` matches no difference")
        for entry in config.allowed_differences
        if entry not in used
    )
    return findings


def run_checks(root: Path, config: Config) -> list[Finding]:
    files = list_markdown_files(root)
    findings: list[Finding] = []
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        findings.extend(check_fences(root, path, lines))
        findings.extend(check_links(root, path, lines))
    findings.extend(check_skills(root))
    findings.extend(check_retired_skills(root, config, files))
    findings.extend(check_parity(root, config))
    return findings


def report(findings: list[Finding]) -> None:
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for finding in findings:
        print(finding)
        if in_actions:
            line = f",line={finding.line}" if finding.line > 0 else ""
            print(f"::error file={finding.path}{line}::{finding.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root (default: this repository)")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="config with the allowlist and retired skills")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    findings = run_checks(root, load_config(args.config))
    if findings:
        report(findings)
        print(f"AI docs check failed: {len(findings)} finding(s).")
        return 1
    print("AI docs check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
