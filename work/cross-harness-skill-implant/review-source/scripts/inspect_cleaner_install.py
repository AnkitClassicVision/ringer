#!/usr/bin/env python3
"""Read-only detector for the official Clean My AI Harness editions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED_NAMES = {
    "codex": "clean-my-ai-harness-codex",
    "claude-code": "clean-my-ai-harness-claude",
}


def portable(path: Path) -> str:
    home = Path.home()
    try:
        return f"<home>/{path.resolve().relative_to(home.resolve())}"
    except ValueError:
        return str(path.resolve())


def frontmatter_name(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")[:8192]
    except (OSError, UnicodeError):
        return None
    match = re.search(r"(?m)^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", text)
    return match.group(1) if match else None


def candidates(surface: str, project_root: Path) -> list[Path]:
    home = Path.home()
    if surface == "codex":
        return [
            home / ".codex/skills/clean-my-ai-harness-codex/SKILL.md",
            home / ".agents/skills/clean-my-ai-harness-codex/SKILL.md",
            project_root / ".agents/skills/clean-my-ai-harness-codex/SKILL.md",
        ]
    if surface == "claude-code":
        return [
            home / ".claude/skills/clean-my-ai-harness-claude/SKILL.md",
            project_root / ".claude/skills/clean-my-ai-harness-claude/SKILL.md",
            project_root / ".agents/skills/clean-my-ai-harness-claude/SKILL.md",
        ]
    return []


def inspect(surface: str, project_root: Path) -> dict:
    if surface == "claude-ai":
        return {
            "surface": surface,
            "status": "INACCESSIBLE",
            "edition": "claude",
            "evidence_status": "INACCESSIBLE",
            "matches": [],
            "checked": [],
            "note": "Claude.ai uploaded skills are not inspectable from the local filesystem.",
        }

    expected = EXPECTED_NAMES[surface]
    checked = candidates(surface, project_root)
    matches = []
    for skill_path in checked:
        if not skill_path.is_file():
            continue
        observed_name = frontmatter_name(skill_path)
        if observed_name == expected:
            matches.append(
                {
                    "path": portable(skill_path),
                    "frontmatter_name": observed_name,
                    "evidence_status": "VERIFIED",
                }
            )

    return {
        "surface": surface,
        "status": "FOUND" if matches else "NOT_FOUND",
        "edition": "codex" if surface == "codex" else "claude",
        "evidence_status": "VERIFIED",
        "matches": matches,
        "checked": [portable(path) for path in checked],
        "note": "Read-only exact-path check. No files were changed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--surface",
        required=True,
        choices=("codex", "claude-code", "claude-ai"),
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = inspect(args.surface, args.project_root)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
