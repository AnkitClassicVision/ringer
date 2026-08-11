#!/usr/bin/env python3
"""Shared validation and execution helpers for the Fable-to-Sol loop packets."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable


UNKNOWN_ROUTES = {
    "tool_or_repo_answerable",
    "cheap_prototype_or_probe",
    "reversible_local_implementation_detail",
    "product_framing_architecture_data_contract_public_api_security_privacy_user_visible",
    "founder_taste_strategy_courage_relationship_risk_appetite",
    "external_or_irreversible_boundary",
}

FORBIDDEN_VERIFICATION_PATTERNS = (
    re.compile(r"\bgit\s+(?:add|commit|push|merge|rebase|reset|checkout|switch|clean|tag|stash)\b", re.I),
    re.compile(r"\b(?:curl|wget|ssh|scp|sftp|rsync|telnet|ncat|nc)\b", re.I),
    re.compile(r"\b(?:rm|rmdir|mv|truncate|dd|mkfs|mount|umount|chown|chmod)\b", re.I),
    re.compile(r"\b(?:touch|mkdir|cp|install|tee|bash|sh|zsh|fish)\b", re.I),
    re.compile(r"\b(?:sudo|systemctl|crontab)\b", re.I),
    re.compile(r"\b(?:pip|pip3|npm|pnpm|yarn)\s+(?:install|add|publish)\b", re.I),
    re.compile(r"\b(?:kubectl|helm|terraform|ansible-playbook|vercel)\b", re.I),
    re.compile(r"\bmake\s+(?:deploy|release|publish)\b", re.I),
)

UNSAFE_AUTHORITY_PATTERN = re.compile(
    r"(?:^|[.;:]\s*)(?:please\s+|must\s+|should\s+|then\s+)?"
    r"(?:(?:run|execute|perform)\s+)?(?:git\s+)?"
    r"(?:commit|push|merge|deploy|publish|release|send|schedule)\b"
    r"|\b(?:may|can|is allowed to)\s+(?:git\s+)?"
    r"(?:commit|push|merge|deploy|publish|release|send|schedule)\b",
    re.I,
)

DIRECT_VERIFIERS = {
    "bats",
    "eslint",
    "flake8",
    "mypy",
    "phpunit",
    "py.test",
    "pylint",
    "pyright",
    "pytest",
    "rspec",
    "ruff",
    "shellcheck",
    "tsc",
}
VERIFIER_TARGET = re.compile(r"(?:^|[-_.:])(build|check|clippy|lint|test|typecheck|validate|verify)(?:[-_.:]|$)", re.I)


class PacketError(ValueError):
    """A packet or its declared verification is invalid."""


class WhyArgumentParser(__import__("argparse").ArgumentParser):
    """ArgumentParser whose CLI failures respect the Ringer WHY contract."""

    def error(self, message: str) -> None:  # pragma: no cover - argparse owns dispatch
        self.exit(2, f"WHY: {message}\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PacketError(message)


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PacketError(f"cannot read JSON packet {path}: {exc}") from exc
    require(bool(raw.strip()), f"JSON packet is empty: {path}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PacketError(f"invalid JSON in {path}: {exc}") from exc
    require(isinstance(value, dict), f"JSON packet root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_keys(value: dict[str, Any], required: Iterable[str], *, where: str) -> None:
    missing = [key for key in required if key not in value]
    require(not missing, f"{where} missing required field(s): {', '.join(missing)}")


def reject_extra_keys(value: dict[str, Any], allowed: Iterable[str], *, where: str) -> None:
    extras = sorted(set(value) - set(allowed))
    require(not extras, f"{where} has unsupported field(s): {', '.join(extras)}")


def require_string(value: Any, *, where: str, min_length: int = 1) -> str:
    require(isinstance(value, str), f"{where} must be a string")
    clean = value.strip()
    require(len(clean) >= min_length, f"{where} must contain at least {min_length} characters")
    return clean


def require_string_list(
    value: Any,
    *,
    where: str,
    nonempty: bool = False,
    unique: bool = True,
) -> list[str]:
    require(isinstance(value, list), f"{where} must be a list")
    if nonempty:
        require(bool(value), f"{where} must not be empty")
    cleaned = [require_string(item, where=f"{where}[{index}]") for index, item in enumerate(value)]
    if unique:
        require(len(cleaned) == len(set(cleaned)), f"{where} must not contain duplicates")
    return cleaned


def normalize_relative_path(value: str, *, where: str) -> str:
    clean = require_string(value, where=where).replace("\\", "/")
    path = Path(clean)
    require(not path.is_absolute(), f"{where} must be repo-relative, not absolute")
    require(".." not in path.parts, f"{where} must not traverse outside the repo")
    require(".git" not in path.parts, f"{where} must not target .git")
    normalized = path.as_posix().lstrip("./")
    require(normalized not in {"", "."}, f"{where} must name a repo path")
    return normalized.rstrip("/")


def normalize_path_list(value: Any, *, where: str, nonempty: bool = False) -> list[str]:
    paths = require_string_list(value, where=where, nonempty=nonempty)
    normalized = [normalize_relative_path(item, where=f"{where}[{index}]") for index, item in enumerate(paths)]
    require(len(normalized) == len(set(normalized)), f"{where} must not contain duplicate paths")
    return normalized


def path_is_owned(path: str, owned_paths: Iterable[str]) -> bool:
    normalized = normalize_relative_path(path, where="changed path")
    for owned in owned_paths:
        candidate = normalize_relative_path(owned, where="owned path")
        if normalized == candidate or normalized.startswith(candidate + "/"):
            return True
    return False


def path_matches_surface(path: str, surface: str) -> bool:
    """Match a changed path to a deterministic path/prefix/glob surface selector."""

    from fnmatch import fnmatch

    normalized = normalize_relative_path(path, where="changed path")
    selector = normalize_relative_path(surface, where="Fable-owned surface")
    if any(marker in selector for marker in "*?["):
        return fnmatch(normalized, selector)
    return normalized == selector or normalized.startswith(selector + "/")


def contains_unquoted_character(value: str, characters: set[str]) -> bool:
    in_single = False
    in_double = False
    escaped = False
    for character in value:
        if escaped:
            escaped = False
            continue
        if character == "\\" and not in_single:
            escaped = True
            continue
        if character == "'" and not in_double:
            in_single = not in_single
            continue
        if character == '"' and not in_single:
            in_double = not in_double
            continue
        if not in_single and not in_double and character in characters:
            return True
    return False


def validate_verification_command(value: Any, *, where: str) -> str:
    command = require_string(value, where=where, min_length=4)
    require("\n" not in command and "\r" not in command, f"{where} must be one command line")
    require(len(command) <= 2000, f"{where} is too long")
    require("$(" not in command and "`" not in command, f"{where} uses command substitution")
    require(
        not contains_unquoted_character(command, {";", "&", "|", "<", ">"}),
        f"{where} must be one argv command without shell operators or redirection",
    )
    for pattern in FORBIDDEN_VERIFICATION_PATTERNS:
        require(not pattern.search(command), f"{where} requests an unsafe or external action")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise PacketError(f"{where} is not shell-parseable: {exc}") from exc
    require(bool(tokens), f"{where} is empty")
    require(tokens[0] not in {"true", ":", "echo", "printf"}, f"{where} is a trivial check")
    validate_named_verifier(tokens, where=where)
    return command


def validate_named_verifier(tokens: list[str], *, where: str) -> None:
    executable = Path(tokens[0]).name.lower()
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?", executable):
        validate_python_verification(tokens, where=where)
        return
    if executable in DIRECT_VERIFIERS:
        if executable == "ruff" and "format" in tokens:
            require("--check" in tokens, f"{where} may run ruff format only with --check")
        return
    if executable == "go":
        require(len(tokens) > 1 and tokens[1] in {"test", "vet"}, f"{where} uses go outside test or vet")
        return
    if executable == "cargo":
        require(len(tokens) > 1 and tokens[1] in {"check", "clippy", "test"}, f"{where} uses cargo outside check, clippy, or test")
        return
    if executable in {"deno", "dotnet", "swift"}:
        require(len(tokens) > 1 and tokens[1] in {"build", "check", "lint", "test"}, f"{where} uses an unsupported {executable} verifier")
        return
    if executable in {"npm", "pnpm", "yarn", "bun"}:
        require(len(tokens) > 1, f"{where} omits the package-script verifier")
        if tokens[1] == "test":
            return
        require(tokens[1] == "run" and len(tokens) > 2 and VERIFIER_TARGET.search(tokens[2]), f"{where} must name a test, build, lint, check, typecheck, validate, or verify package script")
        return
    if executable in {"make", "gmake", "just"}:
        targets = [token for token in tokens[1:] if not token.startswith("-") and "=" not in token]
        require(bool(targets) and all(VERIFIER_TARGET.search(target) for target in targets), f"{where} must name only verification-oriented targets")
        return
    if executable in {"gradle", "gradlew", "mvn", "mvnw"}:
        targets = [token for token in tokens[1:] if not token.startswith("-")]
        require(bool(targets) and all(VERIFIER_TARGET.search(target) for target in targets), f"{where} must name only verification-oriented build targets")
        return
    raise PacketError(f"{where} invokes unsupported executable {executable}; use a named test, build, lint, check, or validation runner")


def validate_python_verification(tokens: list[str], *, where: str) -> None:
    if "-c" in tokens:
        index = tokens.index("-c")
        require(index + 1 < len(tokens), f"{where} has python -c without code")
        validate_read_only_python_code(tokens[index + 1], where=where)
        return
    if "-m" in tokens:
        index = tokens.index("-m")
        require(index + 1 < len(tokens), f"{where} has python -m without a module")
        require(tokens[index + 1] in {"unittest", "pytest"}, f"{where} uses a Python module that is not an approved verifier")
        return
    verification_marker = re.compile(r"(?:^|[-_.])(test|check|lint|verify|validate)(?:[-_.]|$)", re.I)
    require(
        any(verification_marker.search(Path(token).name) for token in tokens[1:]),
        f"{where} invokes an arbitrary Python program instead of a named verifier",
    )


def validate_read_only_python_code(code: str, *, where: str) -> None:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise PacketError(f"{where} contains invalid python -c code: {exc}") from exc
    forbidden_nodes = (
        ast.Assign,
        ast.AnnAssign,
        ast.AugAssign,
        ast.NamedExpr,
        ast.Delete,
        ast.With,
        ast.AsyncWith,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Lambda,
        ast.Global,
        ast.Nonlocal,
        ast.Import,
    )
    allowed_imports = {"json", "math", "pathlib", "re", "statistics"}
    allowed_calls = {"Path", "all", "any", "isinstance", "len", "max", "min", "print", "sorted", "sum"}
    allowed_methods = {
        "endswith",
        "exists",
        "fullmatch",
        "is_dir",
        "is_file",
        "load",
        "loads",
        "lower",
        "match",
        "read_bytes",
        "read_text",
        "search",
        "split",
        "startswith",
        "stat",
        "strip",
        "upper",
    }
    for node in ast.walk(tree):
        require(not isinstance(node, forbidden_nodes), f"{where} contains write-capable or dynamic python -c syntax")
        if isinstance(node, ast.ImportFrom):
            require(node.module in allowed_imports, f"{where} imports a module outside the read-only verifier allowlist")
        if isinstance(node, ast.Attribute):
            require(not node.attr.startswith("_"), f"{where} accesses a private Python attribute")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                require(node.func.id in allowed_calls, f"{where} calls non-read-only Python function {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                require(node.func.attr in allowed_methods, f"{where} calls non-read-only Python method {node.func.attr}")
            else:
                raise PacketError(f"{where} uses a dynamic Python call")


def sanitized_subprocess_env() -> dict[str, str]:
    allowed = ("PATH", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "WINDIR")
    env = {name: os.environ[name] for name in allowed if name in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def git_visible_fingerprint(cwd: Path) -> str | None:
    if not (cwd / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=cwd,
            capture_output=True,
            timeout=60,
            env=sanitized_subprocess_env(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PacketError(f"cannot fingerprint git-visible verification inputs: {exc}") from exc
    require(proc.returncode == 0, f"git-visible fingerprint failed: {proc.stderr.decode(errors='replace').strip()}")
    digest = hashlib.sha256()
    for raw_relative in sorted(item for item in proc.stdout.split(b"\0") if item):
        relative = raw_relative.decode("utf-8", errors="surrogateescape")
        path = cwd / relative
        digest.update(raw_relative)
        digest.update(b"\0")
        try:
            stat = path.lstat()
        except OSError as exc:
            raise PacketError(f"cannot fingerprint git-visible path {relative}: {exc}") from exc
        digest.update(str(stat.st_mode).encode("ascii"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            try:
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
            except OSError as exc:
                raise PacketError(f"cannot fingerprint git-visible path {relative}: {exc}") from exc
        digest.update(b"\0")
    return digest.hexdigest()


def sandboxed_verification_argv(tokens: list[str], *, cwd: Path) -> list[str]:
    """Run proof offline in a write-discarding checkout overlay with user data hidden."""

    bwrap = next(
        (
            str(candidate)
            for candidate in (Path("/usr/bin/bwrap"), Path("/bin/bwrap"))
            if candidate.is_file() and os.access(candidate, os.X_OK)
        ),
        None,
    )
    if bwrap is None:
        discovered = shutil.which("bwrap", path="/usr/bin:/bin")
        bwrap = discovered if discovered and Path(discovered).is_file() else None
    require(
        bwrap is not None,
        "read-only verification sandbox unavailable: install Bubblewrap (bwrap); refusing to execute repository proof unsandboxed",
    )
    network_unshare = next(
        (
            str(candidate)
            for candidate in (Path("/usr/bin/unshare"), Path("/bin/unshare"))
            if candidate.is_file() and os.access(candidate, os.X_OK)
        ),
        None,
    )
    if network_unshare is None:
        discovered = shutil.which("unshare", path="/usr/bin:/bin")
        network_unshare = discovered if discovered and Path(discovered).is_file() else None
    require(
        network_unshare is not None,
        "offline verification sandbox unavailable: install util-linux unshare; refusing to execute repository proof with host networking",
    )

    resolved = cwd.resolve()
    require(resolved != Path("/"), "verification cwd cannot be the filesystem root")
    bwrap_argv = [
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--ro-bind",
        "/",
        "/",
    ]
    masked_roots = [Path(path) for path in ("/home", "/root", "/mnt", "/media", "/run/user") if Path(path).exists()]
    for masked in masked_roots:
        bwrap_argv.extend(("--tmpfs", str(masked)))
    bwrap_argv.extend(
        (
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/var/tmp",
            "--dir",
            "/tmp/fable-sol-home",
        )
    )
    hidden_roots = masked_roots + [Path("/tmp"), Path("/var/tmp")]
    for masked in hidden_roots:
        if not resolved.is_relative_to(masked):
            continue
        current = masked
        for part in resolved.relative_to(masked).parts[:-1]:
            current /= part
            bwrap_argv.extend(("--dir", str(current)))
    bwrap_argv.extend(
        (
            "--overlay-src",
            str(resolved),
            "--tmp-overlay",
            str(resolved),
            "--chdir",
            str(resolved),
            "--setenv",
            "HOME",
            "/tmp/fable-sol-home",
            "--setenv",
            "TMPDIR",
            "/tmp",
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
            "--",
            *tokens,
        )
    )
    return [
        network_unshare,
        "--user",
        "--map-root-user",
        "--net",
        "--",
        *bwrap_argv,
    ]


def run_verification(command: str, *, cwd: Path, timeout_s: int) -> subprocess.CompletedProcess[str]:
    validate_verification_command(command, where="verification command")
    require(cwd.is_dir(), f"verification cwd does not exist: {cwd}")
    tokens = shlex.split(command)
    sandboxed = sandboxed_verification_argv(tokens, cwd=cwd)
    before = git_visible_fingerprint(cwd)
    try:
        proc = subprocess.run(
            sandboxed,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=sanitized_subprocess_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise PacketError(f"verification timed out after {timeout_s}s: {command}") from exc
    except OSError as exc:
        raise PacketError(f"verification could not start: {exc}") from exc
    after = git_visible_fingerprint(cwd)
    require(before == after, "verification sandbox failed to preserve git-visible repository content")
    return proc


def validate_declared_result(value: Any, *, where: str) -> tuple[bool, int | None]:
    require(isinstance(value, dict), f"{where} must be an object")
    require_keys(value, ("passed", "exit_code", "summary"), where=where)
    reject_extra_keys(value, ("passed", "exit_code", "summary"), where=where)
    require(isinstance(value["passed"], bool), f"{where}.passed must be a boolean")
    exit_code = value["exit_code"]
    require(exit_code is None or (isinstance(exit_code, int) and not isinstance(exit_code, bool)), f"{where}.exit_code must be an integer or null")
    require_string(value["summary"], where=f"{where}.summary", min_length=4)
    if value["passed"]:
        require(exit_code == 0, f"{where} says passed but exit_code is not 0")
    else:
        require(exit_code != 0, f"{where} says failed but exit_code is 0")
    return value["passed"], exit_code


def validate_question(value: Any, *, where: str = "question") -> None:
    require(isinstance(value, dict), f"{where} must be an object")
    required = ("question", "why_now", "consequence_if_wrong", "options_with_default", "answer_deadline_effect")
    require_keys(value, required, where=where)
    reject_extra_keys(value, required, where=where)
    require_string(value["question"], where=f"{where}.question", min_length=10)
    require_string(value["why_now"], where=f"{where}.why_now", min_length=10)
    require_string(value["consequence_if_wrong"], where=f"{where}.consequence_if_wrong", min_length=10)
    require_string(value["answer_deadline_effect"], where=f"{where}.answer_deadline_effect", min_length=10)
    options = value["options_with_default"]
    require(isinstance(options, list) and len(options) >= 2, f"{where}.options_with_default must contain at least two options")
    defaults = 0
    for index, option in enumerate(options):
        option_where = f"{where}.options_with_default[{index}]"
        require(isinstance(option, dict), f"{option_where} must be an object")
        require_keys(option, ("option", "tradeoff", "default"), where=option_where)
        reject_extra_keys(option, ("option", "tradeoff", "default"), where=option_where)
        require_string(option["option"], where=f"{option_where}.option", min_length=2)
        require_string(option["tradeoff"], where=f"{option_where}.tradeoff", min_length=5)
        require(isinstance(option["default"], bool), f"{option_where}.default must be a boolean")
        defaults += int(option["default"])
    require(defaults == 1, f"{where}.options_with_default must mark exactly one default")


def validate_hold(value: Any, *, where: str) -> None:
    require(isinstance(value, dict), f"{where} must be an object")
    required = ("unknown", "consequence", "evidence", "options", "owner", "safe_remaining_work")
    allowed = required + ("id", "route")
    require_keys(value, required, where=where)
    reject_extra_keys(value, allowed, where=where)
    if "id" in value:
        require_string(value["id"], where=f"{where}.id")
    if "route" in value:
        require(value["route"] in UNKNOWN_ROUTES, f"{where}.route is not a recognized route")
        require(value["owner"] == "fable", f"{where}.route may be declared only on a Fable-owned HOLD")
    require_string(value["unknown"], where=f"{where}.unknown", min_length=3)
    require_string(value["consequence"], where=f"{where}.consequence", min_length=10)
    require_string(value["evidence"], where=f"{where}.evidence", min_length=5)
    require(value["owner"] in {"fable", "ankit"}, f"{where}.owner must be fable or ankit")
    require_string(value["safe_remaining_work"], where=f"{where}.safe_remaining_work", min_length=10)
    options = value["options"]
    require(isinstance(options, list) and len(options) >= 2, f"{where}.options must contain at least two options")
    for index, option in enumerate(options):
        option_where = f"{where}.options[{index}]"
        require(isinstance(option, dict), f"{option_where} must be an object")
        require_keys(option, ("option", "tradeoff"), where=option_where)
        reject_extra_keys(option, ("option", "tradeoff"), where=option_where)
        require_string(option["option"], where=f"{option_where}.option", min_length=2)
        require_string(option["tradeoff"], where=f"{option_where}.tradeoff", min_length=5)


def validate_safe_required_change(value: Any, *, where: str) -> str:
    text = require_string(value, where=where, min_length=5)
    require(not UNSAFE_AUTHORITY_PATTERN.search(text), f"{where} grants unsafe action authority")
    return text


def prohibition_covers(text: str, marker: str) -> bool:
    marker_pattern = r"secrets?" if marker == "secret" else re.escape(marker)
    pattern = (
        r"\b(?:do\s+not|must\s+not|never|forbid(?:den)?|prohibit(?:ed)?)\b"
        r"[^.\n]{0,100}\b"
        + marker_pattern
        + r"\b"
    )
    return re.search(pattern, text, re.I) is not None


def validate_decision_packet(data: dict[str, Any]) -> dict[str, Any]:
    required = (
        "intent",
        "architecture",
        "owned_paths",
        "fable_owned_surfaces",
        "unknowns",
        "implementation_contract",
        "forbidden_actions",
    )
    allowed = required + ("question",)
    require_keys(data, required, where="decision packet")
    reject_extra_keys(data, allowed, where="decision packet")
    require_string(data["intent"], where="intent", min_length=20)

    architecture = data["architecture"]
    require(isinstance(architecture, dict), "architecture must be an object")
    require_keys(architecture, ("components", "boundaries"), where="architecture")
    require_string_list(architecture["components"], where="architecture.components", nonempty=True)
    require_string_list(architecture["boundaries"], where="architecture.boundaries", nonempty=True)

    owned_paths = normalize_path_list(data["owned_paths"], where="owned_paths", nonempty=True)
    surfaces = normalize_path_list(data["fable_owned_surfaces"], where="fable_owned_surfaces")
    for surface in surfaces:
        require(path_is_owned(surface.replace("**", "surface").replace("*", "surface").replace("?", "x"), owned_paths), f"Fable-owned surface is outside owned_paths: {surface}")

    unknowns = data["unknowns"]
    require(isinstance(unknowns, list), "unknowns must be a list")
    unknown_ids: list[str] = []
    founder_unknown = False
    for index, unknown in enumerate(unknowns):
        where = f"unknowns[{index}]"
        require(isinstance(unknown, dict), f"{where} must be an object")
        require_keys(unknown, ("id", "description", "route"), where=where)
        reject_extra_keys(unknown, ("id", "description", "route"), where=where)
        unknown_ids.append(require_string(unknown["id"], where=f"{where}.id"))
        require_string(unknown["description"], where=f"{where}.description", min_length=8)
        require(unknown["route"] in UNKNOWN_ROUTES, f"{where}.route is not a recognized route")
        founder_unknown = founder_unknown or unknown["route"] == "founder_taste_strategy_courage_relationship_risk_appetite"
    require(len(unknown_ids) == len(set(unknown_ids)), "unknown ids must be unique")

    implementation = data["implementation_contract"]
    require(isinstance(implementation, dict), "implementation_contract must be an object")
    require_keys(implementation, ("build_units",), where="implementation_contract")
    units = implementation["build_units"]
    require(isinstance(units, list) and bool(units), "implementation_contract.build_units must be a non-empty list")
    unit_ids: list[str] = []
    for index, unit in enumerate(units):
        where = f"implementation_contract.build_units[{index}]"
        require(isinstance(unit, dict), f"{where} must be an object")
        required_unit = ("id", "owned_paths", "done_criteria", "verification_command")
        require_keys(unit, required_unit, where=where)
        reject_extra_keys(unit, required_unit, where=where)
        unit_ids.append(require_string(unit["id"], where=f"{where}.id"))
        unit_paths = normalize_path_list(unit["owned_paths"], where=f"{where}.owned_paths", nonempty=True)
        for unit_path in unit_paths:
            require(path_is_owned(unit_path, owned_paths), f"{where}.owned_paths includes path outside packet ownership: {unit_path}")
        require_string(unit["done_criteria"], where=f"{where}.done_criteria", min_length=12)
        validate_verification_command(unit["verification_command"], where=f"{where}.verification_command")
    require(len(unit_ids) == len(set(unit_ids)), "implementation build unit ids must be unique")

    forbidden = require_string_list(data["forbidden_actions"], where="forbidden_actions", nonempty=True)
    joined = " ".join(forbidden)
    for index, statement in enumerate(forbidden):
        require(
            not UNSAFE_AUTHORITY_PATTERN.search(statement),
            f"forbidden_actions[{index}] grants authority instead of prohibiting it",
        )
    for marker in ("commit", "push", "external", "secret", "fallback", "accept"):
        require(prohibition_covers(joined, marker), f"forbidden_actions must explicitly prohibit {marker}")

    if "question" in data:
        validate_question(data["question"])
        require(founder_unknown, "a decision QUESTION requires a founder-class unknown")
    else:
        require(not founder_unknown, "a founder-class unknown requires the single Fable QUESTION packet")
    return data


def decision_units_by_id(decision: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_decision_packet(decision)
    return {unit["id"]: unit for unit in decision["implementation_contract"]["build_units"]}


def print_why(exc: BaseException) -> None:
    print(f"WHY: {exc}")
