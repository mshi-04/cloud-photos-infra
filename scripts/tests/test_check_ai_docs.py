import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import check_ai_docs
from check_ai_docs import Config, Finding, run_checks

ENTRY_BODY = "Read [the skill](.{tool}/skills/demo/SKILL.md).\n"
SKILL_BODY = "---\nname: demo\ndescription: Demo skill.\n---\n\n# Demo\n\nSee [layout](references/layout.md).\n"


def write(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_both_skills(root: Path, name: str, content: str) -> None:
    for tool in ("agents", "claude"):
        write(root, f".{tool}/skills/{name}", content)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    write(tmp_path, "AGENTS.md", "# Entry\n\n" + ENTRY_BODY.format(tool="agents"))
    write(tmp_path, "CLAUDE.md", "# Entry\n\n" + ENTRY_BODY.format(tool="claude"))
    write_both_skills(tmp_path, "demo/SKILL.md", SKILL_BODY)
    write_both_skills(tmp_path, "demo/references/layout.md", "# Layout\n")
    return tmp_path


EMPTY_CONFIG = Config(source="ai_docs_check.toml", allowed_differences=(), retired_skills=(), retired_skill_exempt_paths=())


def messages(findings: list[Finding]) -> list[str]:
    return [str(finding) for finding in findings]


def test_valid_repository_has_no_findings(repo: Path):
    assert run_checks(repo, EMPTY_CONFIG) == []


def test_broken_relative_link_is_reported(repo: Path):
    write(repo, "docs/guide.md", "# Guide\n\nSee [missing](missing.md) and [ok](../AGENTS.md#entry).\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == ["docs/guide.md:3: link target does not exist: missing.md"]


def test_links_in_code_external_and_anchors_are_ignored(repo: Path):
    content = (
        "# Guide\n\n"
        "`[code](missing.md)` [web](https://example.com/x.md) [anchor](#guide) [mail](mailto:a@example.com)\n\n"
        "```markdown\n[fenced](missing.md)\n```\n"
    )
    write(repo, "docs/guide.md", content)

    assert run_checks(repo, EMPTY_CONFIG) == []


def test_link_outside_repository_is_reported(repo: Path):
    write(repo, "guide.md", "[up](../outside.md)\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == ["guide.md:1: link points outside the repository: ../outside.md"]


def test_reference_link_and_percent_encoding_are_resolved(repo: Path):
    write(repo, "docs/my file.md", "# File\n")
    write(repo, "docs/guide.md", "[file][ref] [encoded](my%20file.md)\n\n[ref]: <my file.md>\n[bad]: nothing.md\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == ["docs/guide.md:4: link target does not exist: nothing.md"]


def test_unclosed_code_fence_is_reported(repo: Path):
    write(repo, "guide.md", "# Guide\n\n````text\n```\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == ["guide.md:3: code fence is not closed"]


def test_ignored_files_are_not_checked(repo: Path):
    write(repo, ".gitignore", "ignored/\n")
    write(repo, "ignored/guide.md", "[missing](missing.md)\n")

    assert run_checks(repo, EMPTY_CONFIG) == []


def test_skill_without_front_matter_is_reported(repo: Path):
    write_both_skills(repo, "demo/SKILL.md", "# Demo\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == [
        ".agents/skills/demo/SKILL.md:1: front matter is missing or not closed",
        ".claude/skills/demo/SKILL.md:1: front matter is missing or not closed",
    ]


def test_skill_front_matter_keys_and_name_are_checked(repo: Path):
    write_both_skills(repo, "demo/SKILL.md", "---\nname: other\n---\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == [
        ".agents/skills/demo/SKILL.md:1: front matter has no `description`",
        ".agents/skills/demo/SKILL.md:1: `name` is `other` but the directory is `demo`",
        ".claude/skills/demo/SKILL.md:1: front matter has no `description`",
        ".claude/skills/demo/SKILL.md:1: `name` is `other` but the directory is `demo`",
    ]


def test_skill_directory_without_skill_file_is_reported(repo: Path):
    write_both_skills(repo, "empty/notes.md", "# Notes\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == [
        ".agents/skills/empty/SKILL.md:0: SKILL.md does not exist",
        ".claude/skills/empty/SKILL.md:0: SKILL.md does not exist",
    ]


def test_retired_skill_reference_is_reported_except_in_exempt_paths(repo: Path):
    write(repo, "docs/guide.md", "Use old-skill here, but not old-skill-two.\n")
    write(repo, "history.md", "old-skill was removed.\n")
    config = replace(EMPTY_CONFIG, retired_skills=("old-skill",), retired_skill_exempt_paths=("history.md",))

    assert messages(run_checks(repo, config)) == ["docs/guide.md:1: references retired skill `old-skill`"]


def test_entry_file_difference_needs_allowlist_entry(repo: Path):
    write(repo, "CLAUDE.md", "# Claude\n\n" + ENTRY_BODY.format(tool="claude"))

    assert messages(run_checks(repo, EMPTY_CONFIG)) == [
        "CLAUDE.md:1: differs from AGENTS.md (lines 1-1) without an allowlist entry"
    ]


def test_allowlisted_difference_passes(repo: Path):
    write(repo, "CLAUDE.md", "# Claude\n\n" + ENTRY_BODY.format(tool="claude"))
    allowed = check_ai_docs.AllowedDifference(path="AGENTS.md", agents=("# Entry",), claude=("# Claude",))

    assert run_checks(repo, replace(EMPTY_CONFIG, allowed_differences=(allowed,))) == []


def test_unused_allowlist_entry_is_reported(repo: Path):
    allowed = check_ai_docs.AllowedDifference(path="skills/demo/SKILL.md", agents=("a",), claude=("b",))

    assert messages(run_checks(repo, replace(EMPTY_CONFIG, allowed_differences=(allowed,)))) == [
        "ai_docs_check.toml:0: allowlist entry for `skills/demo/SKILL.md` matches no difference"
    ]


def test_skill_file_difference_and_missing_counterpart_are_reported(repo: Path):
    write(repo, ".claude/skills/demo/references/layout.md", "# Changed\n")
    write(repo, ".agents/skills/demo/references/extra.md", "# Extra\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == [
        ".agents/skills/demo/references/extra.md:0: has no counterpart in .claude/skills",
        ".claude/skills/demo/references/layout.md:1: differs from .agents/skills/demo/references/layout.md "
        "(lines 1-1) without an allowlist entry",
    ]


def test_load_config_reads_allowlist_and_retired_skills(tmp_path: Path):
    config_path = write(
        tmp_path,
        "config.toml",
        '[[parity.allowed]]\npath = "AGENTS.md"\nagents = ["a"]\nclaude = ["b"]\n\n'
        '[retired_skills]\nnames = ["old"]\nexempt_paths = ["history.md"]\n',
    )

    config = check_ai_docs.load_config(config_path)

    assert config == Config(
        source="config.toml",
        allowed_differences=(check_ai_docs.AllowedDifference(path="AGENTS.md", agents=("a",), claude=("b",)),),
        retired_skills=("old",),
        retired_skill_exempt_paths=("history.md",),
    )


def test_main_returns_one_on_findings(repo: Path, capsys: pytest.CaptureFixture[str]):
    write(repo, "guide.md", "[missing](missing.md)\n")
    config_path = write(repo, "config.toml", "")

    assert check_ai_docs.main(["--root", str(repo), "--config", str(config_path)]) == 1
    assert "guide.md:1: link target does not exist: missing.md" in capsys.readouterr().out


def test_repository_passes_with_its_config():
    assert check_ai_docs.main([]) == 0


def test_added_lines_are_reported_with_their_position(repo: Path):
    write(repo, ".claude/skills/demo/references/layout.md", "# Layout\nextra\n")

    assert messages(run_checks(repo, EMPTY_CONFIG)) == [
        ".claude/skills/demo/references/layout.md:2: differs from .agents/skills/demo/references/layout.md "
        "(after line 1) without an allowlist entry",
    ]
