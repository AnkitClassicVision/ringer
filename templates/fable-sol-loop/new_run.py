#!/usr/bin/env python3
"""Generate a no-secrets, OAuth-only four-round Fable-to-Sol run package."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


MANIFEST_NAMES = (
    "manifest-round1-fable-map.json",
    "manifest-round2-sol-build.json",
    "manifest-round3-fable-review.json",
    "manifest-round4-sol-close.json",
)
PROMPT_NAMES = (
    "fable-map.md",
    "sol-build.md",
    "fable-review.md",
    "sol-close.md",
    "source-packet-layout.md",
)
CHECK_NAMES = (
    "lib_packets.py",
    "validate_decision_packet.py",
    "validate_sol_status.py",
    "validate_fable_review.py",
    "validate_receipt.py",
)
ROUND_LAYOUT = (
    ("ROUND1_WORKDIR", "01-fable-map", "fable-map"),
    ("ROUND2_WORKDIR", "02-sol-build", "sol-build"),
    ("ROUND3_WORKDIR", "03-fable-review", "fable-review"),
    ("ROUND4_WORKDIR", "04-sol-close", "sol-close"),
)
ROUTE_MARKERS = (
    "anthropic",
    "openai",
    "openrouter",
    "z.ai",
    "zai/",
    "xai/",
    "ollama",
    "api key",
    "api-key",
    "api_key",
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:client_secret|api[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{8,}", re.I),
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_\-]{12,}\b", re.I),
)
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


class GenerationError(ValueError):
    pass


class WhyArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover
        self.exit(2, f"WHY: {message}\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GenerationError(message)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def normalize_owned_path(raw: str) -> str:
    clean = raw.strip().replace("\\", "/")
    require(bool(clean), "--owned-path cannot be empty")
    path = Path(clean)
    require(not path.is_absolute(), "--owned-path must be repo-relative")
    require(".." not in path.parts, "--owned-path cannot traverse outside the source repo")
    require(".git" not in path.parts, "--owned-path cannot target .git")
    normalized = path.as_posix().lstrip("./").rstrip("/")
    require(normalized not in {"", "."}, "--owned-path must name a repo path")
    return normalized


def read_curated_brief(path: Path) -> str:
    require(path.is_file(), f"curated brief does not exist: {path}")
    require(not path.is_symlink(), "curated brief must be a regular file, not a symlink")
    require(path.stat().st_size <= 1_000_000, "curated brief exceeds the 1 MB no-secrets input limit")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise GenerationError("curated brief must be UTF-8 text") from exc
    require(len(text.strip()) >= 20, "curated brief is too small to define a real task")
    require("{{" not in text, "curated brief contains unresolved template syntax")
    for pattern in SECRET_PATTERNS:
        require(not pattern.search(text), "curated brief appears to contain a credential or private key")
    return text


def git_status(source_repo: Path) -> list[str]:
    require((source_repo / ".git").exists(), "source repo must be a git checkout or disposable git snapshot with .git metadata")
    env = {"PATH": os.environ.get("PATH", "")}
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=source_repo,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GenerationError(f"cannot inspect source repo status: {exc}") from exc
    require(proc.returncode == 0, f"git status failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return [line for line in proc.stdout.splitlines() if line]


def render_text(text: str, values: dict[str, str], *, source: str) -> str:
    unknown = sorted(set(PLACEHOLDER_RE.findall(text)) - set(values))
    require(not unknown, f"{source} has unfilled placeholder(s): {', '.join(unknown)}")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    require("{{" not in text, f"{source} still contains unresolved template syntax")
    return text


def render_json_value(value: Any, replacements: dict[str, str], *, source: str) -> Any:
    if isinstance(value, str):
        return render_text(value, replacements, source=source)
    if isinstance(value, list):
        return [render_json_value(item, replacements, source=source) for item in value]
    if isinstance(value, dict):
        return {key: render_json_value(item, replacements, source=source) for key, item in value.items()}
    return value


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def source_readme(round_name: str) -> str:
    requirements = {
        "01-fable-map": "brief.md and answers.md are already staged. Add only explicitly curated, no-secrets context copies.",
        "02-sol-build": "Stage the validated round-1 packet here as decision-packet.json before launch.",
        "03-fable-review": "Stage decision-packet.json, status.json, notes.md, answers.md when resuming a QUESTION, and curated changed-file evidence under changed/.",
        "04-sol-close": "Stage decision-packet.json, status.json, and exactly one of review.json or validator-generated skip-notice.json.",
    }
    return (
        f"# {round_name} source packet\n\n"
        f"{requirements[round_name]}\n\n"
        "These are task-local read-only copies. Do not stage secrets, credential files, arbitrary repository copies, or live cross-round paths.\n"
    )


def package_readme(project_slug: str, source_repo: Path, owned_paths: list[str]) -> str:
    owned = ", ".join(f"`{path}`" for path in owned_paths)
    return f"""# {project_slug} Fable-to-Sol run package

This generated package contains four sequential OAuth-only Ringer manifests for one shared human job.

- Clean source checkout or clean disposable snapshot: `{source_repo}`
- Sol-owned paths: {owned}
- OAuth unavailable: `STOP_NO_API_FALLBACK`

Run the manifests in numeric order. After each validator passes, copy only the named artifacts into the next round's task-local `sources/` directory. Round 3 runs only when round 2 records `review_required=true`. When it is false, copy the validator-generated `skip-notice.json` to round 4.

The generator copied only the explicitly supplied brief. It did not copy the source repository, discover files, read credentials, or authorize external actions. Generation accepted this source path only after Git reported a clean state. Dirty source input is never accepted directly. A dirty live checkout must first be copied into an operator-approved disposable Git snapshot, and that snapshot must be made clean before generation.
"""


def validate_generated_manifests(package: Path) -> None:
    manifests = [json.loads((package / name).read_text(encoding="utf-8")) for name in MANIFEST_NAMES]
    run_names = {manifest.get("run_name") for manifest in manifests}
    require(len(run_names) == 1, "generated manifests do not share one run_name")
    require(all(len(manifest.get("tasks", [])) == 1 for manifest in manifests), "every generated manifest must contain one task")

    for index, manifest in enumerate(manifests):
        task = manifest["tasks"][0]
        require(task.get("full_access") is False, f"round {index + 1} must set full_access=false")
        require(bool(task.get("expect_files")), f"round {index + 1} must declare expect_files")
        require(len(task.get("verified", "").strip()) >= 40, f"round {index + 1} verified sentence is not substantive")
        require(task.get("check", "").strip() not in {"true", ":", "exit 0"}, f"round {index + 1} has a trivial check")
        raw = json.dumps(manifest).lower()
        marker = next((item for item in ROUTE_MARKERS if item in raw), None)
        require(marker is None, f"generated manifest contains forbidden route or credential marker: {marker}")

    for index in (0, 2):
        task = manifests[index]["tasks"][0]
        require(task.get("engine") == "claude-lean" and task.get("model") == "fable", f"round {index + 1} does not use the locked Fable OAuth route")
        require("engine_args" not in task, f"round {index + 1} must not declare writable roots or engine_args")
    expected_prefix = ["-c", "model_reasoning_effort=ultra"]
    for index in (1, 3):
        task = manifests[index]["tasks"][0]
        require(task.get("engine") == "codex", f"round {index + 1} does not use the locked Sol OAuth route")
        require(task.get("model") == "gpt-5.6-sol", f"round {index + 1} must use the locked Sol model field")
        require(task.get("engine_args", [])[:2] == expected_prefix, f"round {index + 1} engine_args do not begin with the locked Sol reasoning selector")
        require(any("writable_roots=" in arg for arg in task["engine_args"][2:]), f"round {index + 1} is missing bounded writable_roots")


def generate(args: argparse.Namespace) -> Path:
    kit_dir = Path(__file__).resolve().parent
    source_repo = args.source_repo.expanduser().resolve()
    brief_input = args.brief.expanduser()
    require(not brief_input.is_symlink(), "curated brief must be a regular file, not a symlink")
    brief_path = brief_input.resolve()
    output = args.output.expanduser().resolve()

    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", args.project_slug) is not None, "--project-slug must be 2-63 lowercase letters, digits, or hyphens")
    require(source_repo.is_dir(), f"source repo does not exist: {source_repo}")
    require(not output.exists(), f"output already exists; refusing to overwrite: {output}")
    require(not is_within(output, source_repo), "output must be outside the source repo")
    require(not is_within(source_repo, output), "output and source repo must not overlap")
    brief_text = read_curated_brief(brief_path)

    owned_paths = [normalize_owned_path(item) for item in args.owned_path]
    require(bool(owned_paths), "at least one --owned-path is required")
    require(len(owned_paths) == len(set(owned_paths)), "--owned-path values must be unique")
    writable_roots: list[str] = []
    for owned in owned_paths:
        resolved = (source_repo / owned).resolve(strict=False)
        require(is_within(resolved, source_repo), f"owned path escapes source repo: {owned}")
        writable_roots.append(str(resolved))

    dirty_lines = git_status(source_repo)
    require(
        not dirty_lines,
        "source repo is dirty and cannot be used directly; first copy the intended state into an operator-approved disposable git snapshot and make that snapshot clean before generation",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=f".{args.project_slug}-fable-sol-", dir=output.parent))
    package = temp_root / "package"
    try:
        package.mkdir()
        replacements: dict[str, str] = {
            "RUN_SLUG": args.project_slug,
            "PROJECT_SLUG": args.project_slug,
            "SOURCE_REPO": str(source_repo),
            "SOURCE_REPO_SHELL": shlex.quote(str(source_repo)),
            "OWNED_PATHS": ", ".join(owned_paths),
            "WRITABLE_ROOTS_JSON": json.dumps(writable_roots, separators=(",", ":")),
            "KIT_DIR": str(output),
            "KIT_DIR_SHELL": shlex.quote(str(output)),
        }
        for key, round_dir, _task_key in ROUND_LAYOUT:
            replacements[key] = str(output / "rounds" / round_dir)

        prompt_values: dict[str, str] = {}
        for prompt_name in PROMPT_NAMES:
            source = kit_dir / "prompts" / prompt_name
            rendered = render_text(source.read_text(encoding="utf-8"), replacements, source=str(source))
            write_text(package / "prompts" / prompt_name, rendered)
            prompt_key = prompt_name.removesuffix(".md").replace("-", "_").upper() + "_PROMPT"
            prompt_values[prompt_key] = rendered.rstrip()
        replacements.update(prompt_values)

        for manifest_name in MANIFEST_NAMES:
            source = kit_dir / manifest_name
            raw = json.loads(source.read_text(encoding="utf-8"))
            rendered = render_json_value(raw, replacements, source=str(source))
            write_text(package / manifest_name, json.dumps(rendered, indent=2))

        for check_name in CHECK_NAMES:
            source = kit_dir / "checks" / check_name
            require(source.is_file(), f"kit check is missing: {source}")
            (package / "checks").mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, package / "checks" / check_name)

        for _key, round_dir, task_key in ROUND_LAYOUT:
            sources = package / "rounds" / round_dir / task_key / "sources"
            sources.mkdir(parents=True, exist_ok=True)
            write_text(sources / "README.md", source_readme(round_dir))
        write_text(package / "rounds" / "01-fable-map" / "fable-map" / "sources" / "brief.md", brief_text)
        write_text(
            package / "rounds" / "01-fable-map" / "fable-map" / "sources" / "answers.md",
            "# Operator answers\n\nNo prior Fable question has been answered for this run.",
        )
        write_text(
            package / "rounds" / "03-fable-review" / "fable-review" / "sources" / "answers.md",
            "# Operator answers\n\nNo prior Fable review question has been answered for this run.",
        )

        input_contract = {
            "project_slug": args.project_slug,
            "source_repo": str(source_repo),
            "owned_paths": owned_paths,
            "brief_source": str(brief_path),
            "source_repo_git_state": "clean",
            "oauth_failure_policy": "STOP_NO_API_FALLBACK",
            "source_copy_policy": "explicit-curated-brief-only",
        }
        write_text(package / "input-contract.json", json.dumps(input_contract, indent=2))
        write_text(package / "README.md", package_readme(args.project_slug, source_repo, owned_paths))

        validate_generated_manifests(package)
        for path in package.rglob("*"):
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise GenerationError(f"generated package contains unexpected binary file: {path}") from exc
                require("{{" not in content, f"generated file contains unresolved placeholder: {path.relative_to(package)}")
        package.rename(output)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    shutil.rmtree(temp_root, ignore_errors=True)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = WhyArgumentParser(description=__doc__)
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--owned-path", action="append", default=[], help="repeat for each repo-relative Sol-owned path")
    parser.add_argument("--brief", type=Path, required=True, help="explicitly curated UTF-8 brief")
    parser.add_argument("--output", type=Path, required=True, help="new run-package directory outside the source repo")
    args = parser.parse_args(argv)
    try:
        output = generate(args)
    except (GenerationError, OSError, json.JSONDecodeError) as exc:
        print(f"WHY: {exc}")
        return 1
    print(f"PASS: generated OAuth-only Fable-to-Sol run package at {output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover
        print(f"WHY: {exc}")
        sys.exit(1)
