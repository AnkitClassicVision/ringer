#!/usr/bin/env python3
"""Inspect, apply, verify, and roll back an immutable skill implant plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


SCHEMA_VERSION = "1.0.0"
LEVELS = ("present", "indexed", "loaded", "invoked")
COLLISION_ACTIONS = {"BLOCK", "KEEP", "MERGE", "REPLACE", "RENAME"}
INSTALL_METHODS = {"link", "copy"}
MANIFEST_KEYS = {"schema_version", "plan", "plan_hash", "status", "receipts", "events"}
PLAN_KEYS = {"implant_id", "source", "scope", "compatibility", "targets", "rollback"}
REQUEST_KEYS = {
    "schema_version",
    "implant_id",
    "source",
    "scope",
    "compatibility",
    "targets",
    "rollback",
}
SOURCE_REQUEST_KEYS = {"path", "uri", "expected_skill_name"}
SCOPE_KEYS = {"goal", "allowed_actions", "excluded_expansions"}
COMPATIBILITY_KEYS = {"status", "blocking_reasons"}
TARGET_REQUEST_REQUIRED_KEYS = {
    "surface",
    "root",
    "destination_name",
    "ownership",
    "collision_action",
    "minimum_discovery_level",
    "discovery_adapters",
}
TARGET_REQUEST_KEYS = TARGET_REQUEST_REQUIRED_KEYS | {"method", "rename_to"}
ADAPTER_KEYS = {
    "level",
    "version_command",
    "version_regex",
    "command",
    "success_regex",
    "timeout_seconds",
}
ROLLBACK_REQUEST_KEYS = {
    "required",
    "backup_root_required_for_replace",
    "backup_root",
}
SOURCE_PLAN_KEYS = {
    "path",
    "uri",
    "expected_skill_name",
    "frontmatter_name",
    "tree_sha256",
}
ROLLBACK_PLAN_KEYS = ROLLBACK_REQUEST_KEYS | {
    "removes_only_manifest_created_targets",
    "keeps_existing_keep_targets",
}
TARGET_PLAN_KEYS = {
    "surface",
    "root",
    "destination_name",
    "destination",
    "effective_destination",
    "ownership",
    "method",
    "collision_action",
    "collision_classification",
    "rename_to",
    "minimum_discovery_level",
    "discovery_adapters",
    "prior_state",
    "alternate_prior_state",
}
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HASH_RECEIPT = re.compile(r"^sha256:[0-9a-f]{64}$")
PLAIN_HASH = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_STATUSES = {"INSPECTED", "APPLIED", "VERIFIED", "VERIFY_FAILED", "ROLLED_BACK"}
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "assets" / "implant-manifest.schema.json"
DEFAULT_TEMPLATE_PATH = REPO_ROOT / "assets" / "implant-request.template.json"
FORBIDDEN_RECEIPT_KEYS = {
    "stdout",
    "stderr",
    "output",
    "excerpt",
    "raw_output",
    "raw_stdout",
    "raw_stderr",
}
FRONTMATTER_NAME = re.compile(
    r"(?m)^name:\s*['\"]?([a-z0-9][a-z0-9-]*)['\"]?\s*$"
)


class WorkflowError(Exception):
    """A fail-closed workflow error with a stable machine-readable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def fail(code: str, detail: str = "") -> None:
    raise WorkflowError(code, detail)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def plan_hash(plan: dict[str, Any]) -> str:
    return "sha256:" + sha256_bytes(canonical_json(plan))


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _remove_path(path: Path) -> None:
    if not _lexists(path):
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _tree_entries(root: Path) -> list[tuple[str, str, bytes]]:
    if not _lexists(root):
        fail("SOURCE_NOT_FOUND", str(root))
    if root.is_symlink() or not root.is_dir():
        fail("SOURCE_NOT_DIRECTORY", str(root))

    entries: list[tuple[str, str, bytes]] = []

    def visit(directory: Path) -> None:
        for child in sorted(directory.iterdir(), key=lambda item: item.name):
            relative = child.relative_to(root).as_posix()
            if child.is_symlink():
                entries.append(("link", relative, os.readlink(child).encode("utf-8")))
            elif child.is_dir():
                entries.append(("dir", relative, b""))
                visit(child)
            elif child.is_file():
                entries.append(("file", relative, child.read_bytes()))
            else:
                fail("UNSUPPORTED_SOURCE_ENTRY", relative)

    visit(root)
    return entries


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for kind, relative, content in _tree_entries(root):
        kind_bytes = kind.encode("ascii")
        path_bytes = relative.encode("utf-8")
        digest.update(len(kind_bytes).to_bytes(4, "big"))
        digest.update(kind_bytes)
        digest.update(len(path_bytes).to_bytes(8, "big"))
        digest.update(path_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def parse_frontmatter_name(source: Path) -> str:
    skill_path = source / "SKILL.md"
    if not skill_path.is_file() or skill_path.is_symlink():
        fail("SKILL_FILE_NOT_FOUND", str(skill_path))
    try:
        text = skill_path.read_text(encoding="utf-8")[:16384]
    except (OSError, UnicodeError) as exc:
        fail("SKILL_FILE_UNREADABLE", str(exc))
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        fail("FRONTMATTER_NAME_MISSING", str(skill_path))
    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        fail("FRONTMATTER_NAME_MISSING", str(skill_path))
    match = FRONTMATTER_NAME.search("\n".join(lines[1:closing_index]))
    if not match:
        fail("FRONTMATTER_NAME_MISSING", str(skill_path))
    return match.group(1)


def _require_dict(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail("INVALID_REQUEST", f"{field} must be an object")
    return value


def _require_list(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        fail("INVALID_REQUEST", f"{field} must be an array")
    return value


def _require_string(value: object, field: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        fail("INVALID_REQUEST", f"{field} must be a non-empty string")
    return value


def _absolute_path(value: object, field: str) -> Path:
    raw = _require_string(value, field)
    path = Path(raw)
    if not path.is_absolute():
        fail("INVALID_REQUEST", f"{field} must be absolute")
    return path.resolve(strict=False)


def _reject_source_target_overlap(source: Path, target: Path) -> None:
    try:
        resolved_source = source.resolve(strict=False)
        resolved_target = target.parent.resolve(strict=False) / target.name
    except (OSError, RuntimeError) as exc:
        fail("SOURCE_TARGET_OVERLAP", f"could not resolve source and target safely: {exc}")
    try:
        resolved_source.relative_to(resolved_target)
        fail("SOURCE_TARGET_OVERLAP", "target is the source or one of its ancestors")
    except ValueError:
        pass
    try:
        resolved_target.relative_to(resolved_source)
        fail("SOURCE_TARGET_OVERLAP", "target is the source or one of its descendants")
    except ValueError:
        pass


def _component(value: object, field: str) -> str:
    component = _require_string(value, field)
    if component in {".", ".."} or not SAFE_COMPONENT.fullmatch(component):
        fail("INVALID_REQUEST", f"{field} must be one safe path component")
    return component


def _string_array(value: object, field: str, *, nonempty: bool = False) -> list[str]:
    values = _require_list(value, field)
    if nonempty and not values:
        fail("INVALID_REQUEST", f"{field} must not be empty")
    if not all(isinstance(item, str) and item for item in values):
        fail("INVALID_REQUEST", f"{field} must contain non-empty strings")
    return list(values)


def _validate_adapter(value: object, field: str) -> dict[str, Any]:
    adapter = _require_dict(value, field)
    if set(adapter) != ADAPTER_KEYS:
        fail("INVALID_REQUEST", f"{field} keys must be {sorted(ADAPTER_KEYS)}")
    level = _require_string(adapter["level"], f"{field}.level")
    if level not in LEVELS[1:]:
        fail("INVALID_REQUEST", f"{field}.level must be indexed, loaded, or invoked")
    version_command = _string_array(
        adapter["version_command"], f"{field}.version_command", nonempty=True
    )
    command = _string_array(adapter["command"], f"{field}.command", nonempty=True)
    if not Path(version_command[0]).is_absolute() or not Path(command[0]).is_absolute():
        fail("INVALID_REQUEST", f"{field} executables must be absolute")
    version_regex = _require_string(adapter["version_regex"], f"{field}.version_regex")
    success_regex = _require_string(adapter["success_regex"], f"{field}.success_regex")
    try:
        re.compile(version_regex)
        re.compile(success_regex)
    except re.error as exc:
        fail("INVALID_REQUEST", f"{field} contains an invalid regular expression: {exc}")
    timeout = adapter["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 300:
        fail("INVALID_REQUEST", f"{field}.timeout_seconds must be greater than 0 and at most 300")
    return {
        "level": level,
        "version_command": version_command,
        "version_regex": version_regex,
        "command": command,
        "success_regex": success_regex,
        "timeout_seconds": timeout,
    }


def _path_state(path: Path) -> dict[str, Any]:
    state: dict[str, Any] = {"path": str(path), "exists": _lexists(path)}
    if not state["exists"]:
        state["kind"] = "absent"
        return state
    if path.is_symlink():
        state.update({"kind": "link", "link_target": os.readlink(path)})
    elif path.is_dir():
        state.update({"kind": "directory", "tree_sha256": tree_sha256(path)})
    elif path.is_file():
        state.update({"kind": "file", "sha256": sha256_bytes(path.read_bytes())})
    else:
        state["kind"] = "other"
    return state


def build_plan(request: dict[str, Any]) -> dict[str, Any]:
    if set(request) != REQUEST_KEYS:
        fail("INVALID_REQUEST", f"top-level keys must be {sorted(REQUEST_KEYS)}")
    if request.get("schema_version") != SCHEMA_VERSION:
        fail("INVALID_REQUEST", f"schema_version must be {SCHEMA_VERSION}")
    implant_id = _component(request.get("implant_id"), "implant_id")

    source_request = _require_dict(request.get("source"), "source")
    if set(source_request) != SOURCE_REQUEST_KEYS:
        fail("INVALID_REQUEST", "source keys are invalid")
    source_path = _absolute_path(source_request.get("path"), "source.path")
    source_uri = _require_string(source_request.get("uri"), "source.uri")
    expected_name = _component(
        source_request.get("expected_skill_name"), "source.expected_skill_name"
    )
    source_hash = tree_sha256(source_path)
    parsed_name = parse_frontmatter_name(source_path)

    scope_request = _require_dict(request.get("scope"), "scope")
    if set(scope_request) != SCOPE_KEYS:
        fail("INVALID_REQUEST", "scope keys are invalid")
    scope = {
        "goal": _require_string(scope_request.get("goal"), "scope.goal"),
        "allowed_actions": _string_array(
            scope_request.get("allowed_actions"), "scope.allowed_actions", nonempty=True
        ),
        "excluded_expansions": _string_array(
            scope_request.get("excluded_expansions"), "scope.excluded_expansions", nonempty=True
        ),
    }

    compatibility_request = _require_dict(request.get("compatibility"), "compatibility")
    if set(compatibility_request) != COMPATIBILITY_KEYS:
        fail("INVALID_REQUEST", "compatibility keys are invalid")
    compatibility_status = _require_string(
        compatibility_request.get("status"), "compatibility.status"
    )
    if compatibility_status not in {"compatible", "incompatible"}:
        fail("INVALID_REQUEST", "compatibility.status must be compatible or incompatible")
    blocking_reasons = _string_array(
        compatibility_request.get("blocking_reasons"), "compatibility.blocking_reasons"
    )
    if parsed_name != expected_name:
        compatibility_status = "incompatible"
        blocking_reasons.append(
            f"frontmatter name {parsed_name!r} does not match expected name {expected_name!r}"
        )
    if compatibility_status == "incompatible" and not blocking_reasons:
        fail("INVALID_REQUEST", "an incompatible request must state a blocking reason")

    targets_request = _require_list(request.get("targets"), "targets")
    if not targets_request:
        fail("INVALID_REQUEST", "targets must not be empty")
    targets: list[dict[str, Any]] = []
    surfaces: set[str] = set()
    destinations: set[str] = set()
    for index, raw_target in enumerate(targets_request):
        field = f"targets[{index}]"
        target = _require_dict(raw_target, field)
        if not TARGET_REQUEST_REQUIRED_KEYS.issubset(target) or not set(target).issubset(
            TARGET_REQUEST_KEYS
        ):
            fail("INVALID_REQUEST", f"{field} keys are invalid")
        surface = _component(target.get("surface"), f"{field}.surface")
        if surface in surfaces:
            fail("INVALID_REQUEST", f"duplicate target surface {surface!r}")
        surfaces.add(surface)
        root = _absolute_path(target.get("root"), f"{field}.root")
        destination_name = _component(
            target.get("destination_name"), f"{field}.destination_name"
        )
        destination = root / destination_name
        destination_key = str(destination)
        if destination_key in destinations:
            fail("INVALID_REQUEST", f"duplicate target destination {destination_key!r}")
        destinations.add(destination_key)
        ownership = _require_string(target.get("ownership"), f"{field}.ownership")
        method = _require_string(target.get("method", "link"), f"{field}.method")
        if method not in INSTALL_METHODS:
            fail("INVALID_REQUEST", f"{field}.method must be link or copy")
        if method not in scope["allowed_actions"]:
            fail("INVALID_REQUEST", f"{field}.method is outside scope.allowed_actions")
        action = _require_string(
            target.get("collision_action"), f"{field}.collision_action"
        )
        if action not in COLLISION_ACTIONS:
            fail("INVALID_REQUEST", f"{field}.collision_action must be uppercase and known")
        rename_to_value = target.get("rename_to")
        rename_to = None
        if action == "RENAME":
            rename_to = _component(rename_to_value, f"{field}.rename_to")
            if rename_to == destination_name:
                fail("INVALID_REQUEST", f"{field}.rename_to must differ from destination_name")
        elif rename_to_value is not None:
            fail("INVALID_REQUEST", f"{field}.rename_to is only valid for RENAME")
        minimum_level = _require_string(
            target.get("minimum_discovery_level"), f"{field}.minimum_discovery_level"
        )
        if minimum_level not in LEVELS:
            fail("INVALID_REQUEST", f"{field}.minimum_discovery_level is invalid")
        adapter_values = _require_list(
            target.get("discovery_adapters", []), f"{field}.discovery_adapters"
        )
        adapters = [
            _validate_adapter(value, f"{field}.discovery_adapters[{adapter_index}]")
            for adapter_index, value in enumerate(adapter_values)
        ]
        levels = [adapter["level"] for adapter in adapters]
        if len(levels) != len(set(levels)):
            fail("INVALID_REQUEST", f"{field} has duplicate discovery adapter levels")
        effective_destination = root / (rename_to if action == "RENAME" else destination_name)
        for candidate in (destination, effective_destination):
            _reject_source_target_overlap(source_path, candidate)
        targets.append(
            {
                "surface": surface,
                "root": str(root),
                "destination_name": destination_name,
                "destination": str(destination),
                "effective_destination": str(effective_destination),
                "ownership": ownership,
                "method": method,
                "collision_action": action,
                "collision_classification": action,
                "rename_to": rename_to,
                "minimum_discovery_level": minimum_level,
                "discovery_adapters": adapters,
                "prior_state": _path_state(destination),
                "alternate_prior_state": (
                    _path_state(effective_destination) if action == "RENAME" else None
                ),
            }
        )

    rollback_request = _require_dict(request.get("rollback"), "rollback")
    if set(rollback_request) != ROLLBACK_REQUEST_KEYS:
        fail("INVALID_REQUEST", "rollback keys are invalid")
    required = rollback_request.get("required")
    backup_required = rollback_request.get("backup_root_required_for_replace")
    backup_root = _absolute_path(rollback_request.get("backup_root"), "rollback.backup_root")
    if required is not True or not isinstance(backup_required, bool):
        fail(
            "INVALID_REQUEST",
            "rollback.required must be true and backup_root_required_for_replace must be boolean",
        )
    if "rollback" not in scope["allowed_actions"]:
        fail("INVALID_REQUEST", "rollback must be present in scope.allowed_actions")
    if any(target["minimum_discovery_level"] != "present" for target in targets):
        if "verify" not in scope["allowed_actions"]:
            fail("INVALID_REQUEST", "verify must be allowed for native discovery")

    return {
        "implant_id": implant_id,
        "source": {
            "path": str(source_path),
            "uri": source_uri,
            "expected_skill_name": expected_name,
            "frontmatter_name": parsed_name,
            "tree_sha256": source_hash,
        },
        "scope": scope,
        "compatibility": {
            "status": compatibility_status,
            "blocking_reasons": blocking_reasons,
        },
        "targets": targets,
        "rollback": {
            "required": True,
            "backup_root_required_for_replace": backup_required,
            "backup_root": str(backup_root),
            "removes_only_manifest_created_targets": True,
            "keeps_existing_keep_targets": True,
        },
    }


def _read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(code, str(exc))
    if not isinstance(value, dict):
        fail(code, "top-level JSON value must be an object")
    return value


def _contract_set(value: object, expected: set[str]) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(expected)
        and all(isinstance(item, str) for item in value)
        and set(value) == expected
    )


def _contract_expect(condition: bool, code: str, detail: str) -> None:
    if not condition:
        fail(code, detail)


def _validate_schema_parity(schema: dict[str, Any]) -> None:
    code = "SCHEMA_PARITY_MISMATCH"
    try:
        properties = schema["properties"]
        definitions = schema["$defs"]
        plan = definitions["plan"]
        target = definitions["target"]
        adapter = definitions["adapter"]
        path_state = definitions["pathState"]
        source = plan["properties"]["source"]
        rollback = plan["properties"]["rollback"]
    except (KeyError, TypeError) as exc:
        fail(code, f"missing schema structure: {exc}")

    _contract_expect(_contract_set(schema.get("required"), MANIFEST_KEYS), code, "top-level required keys diverge")
    _contract_expect(set(properties) == MANIFEST_KEYS, code, "top-level properties diverge")
    _contract_expect(schema.get("additionalProperties") is False, code, "top-level additionalProperties must be false")
    _contract_expect(properties.get("schema_version", {}).get("const") == SCHEMA_VERSION, code, "schema version diverges")
    _contract_expect(_contract_set(properties.get("status", {}).get("enum"), MANIFEST_STATUSES), code, "manifest status enum diverges")
    _contract_expect(properties.get("plan_hash", {}).get("pattern") == HASH_RECEIPT.pattern, code, "plan hash pattern diverges")

    _contract_expect(_contract_set(plan.get("required"), PLAN_KEYS), code, "plan required keys diverge")
    _contract_expect(set(plan.get("properties", {})) == PLAN_KEYS, code, "plan properties diverge")
    _contract_expect(plan.get("additionalProperties") is False, code, "plan additionalProperties must be false")
    _contract_expect(_contract_set(source.get("required"), SOURCE_PLAN_KEYS), code, "source required keys diverge")
    _contract_expect(set(source.get("properties", {})) == SOURCE_PLAN_KEYS, code, "source properties diverge")
    _contract_expect(source.get("properties", {}).get("tree_sha256", {}).get("pattern") == PLAIN_HASH.pattern, code, "source hash pattern diverges")

    _contract_expect(_contract_set(target.get("required"), TARGET_PLAN_KEYS), code, "target required keys diverge")
    _contract_expect(set(target.get("properties", {})) == TARGET_PLAN_KEYS, code, "target properties diverge")
    _contract_expect(target.get("additionalProperties") is False, code, "target additionalProperties must be false")
    target_properties = target.get("properties", {})
    _contract_expect(_contract_set(target_properties.get("method", {}).get("enum"), INSTALL_METHODS), code, "target methods diverge")
    for field in ("collision_action", "collision_classification"):
        _contract_expect(_contract_set(target_properties.get(field, {}).get("enum"), COLLISION_ACTIONS), code, f"{field} enum diverges")
    _contract_expect(_contract_set(target_properties.get("minimum_discovery_level", {}).get("enum"), set(LEVELS)), code, "discovery levels diverge")

    _contract_expect(_contract_set(adapter.get("required"), ADAPTER_KEYS), code, "adapter required keys diverge")
    _contract_expect(set(adapter.get("properties", {})) == ADAPTER_KEYS, code, "adapter properties diverge")
    _contract_expect(adapter.get("additionalProperties") is False, code, "adapter additionalProperties must be false")
    _contract_expect(_contract_set(adapter.get("properties", {}).get("level", {}).get("enum"), set(LEVELS[1:])), code, "adapter levels diverge")

    _contract_expect(_contract_set(rollback.get("required"), ROLLBACK_PLAN_KEYS), code, "rollback fields diverge")
    _contract_expect(set(rollback.get("properties", {})) == ROLLBACK_PLAN_KEYS, code, "rollback properties diverge")
    _contract_expect(rollback.get("additionalProperties") is False, code, "rollback additionalProperties must be false")
    rollback_properties = rollback.get("properties", {})
    _contract_expect(rollback_properties.get("required", {}).get("const") is True, code, "rollback.required diverges")
    _contract_expect(rollback_properties.get("backup_root_required_for_replace", {}).get("type") == "boolean", code, "rollback backup requirement diverges")
    _contract_expect(rollback_properties.get("backup_root", {}).get("pattern") == "^/", code, "rollback backup_root pattern diverges")
    for field in ("removes_only_manifest_created_targets", "keeps_existing_keep_targets"):
        _contract_expect(rollback_properties.get(field, {}).get("const") is True, code, f"rollback.{field} diverges")

    _contract_expect(_contract_set(path_state.get("required"), {"path", "exists", "kind"}), code, "pathState base keys diverge")
    _contract_expect(path_state.get("additionalProperties") is False, code, "pathState additionalProperties must be false")
    path_properties = path_state.get("properties", {})
    _contract_expect(set(path_properties) == {"path", "exists", "kind", "link_target", "tree_sha256", "sha256"}, code, "pathState properties diverge")
    _contract_expect(_contract_set(path_properties.get("kind", {}).get("enum"), {"absent", "link", "directory", "file", "other"}), code, "pathState kinds diverge")
    for field in ("tree_sha256", "sha256"):
        _contract_expect(path_properties.get(field, {}).get("pattern") == PLAIN_HASH.pattern, code, f"pathState {field} pattern diverges")
    expected_conditionals = [
        {
            "if": {"properties": {"kind": {"const": kind}}, "required": ["kind"]},
            "then": {"required": [required_field]},
        }
        for kind, required_field in (
            ("link", "link_target"),
            ("directory", "tree_sha256"),
            ("file", "sha256"),
        )
    ]
    _contract_expect(path_state.get("allOf") == expected_conditionals, code, "pathState conditional requirements diverge")


def _validate_template_parity(template: dict[str, Any]) -> None:
    code = "TEMPLATE_PARITY_MISMATCH"
    _contract_expect(set(template) == REQUEST_KEYS, code, "top-level request keys diverge")
    _contract_expect(template.get("schema_version") == SCHEMA_VERSION, code, "template schema version diverges")
    for field, expected in (
        ("source", SOURCE_REQUEST_KEYS),
        ("scope", SCOPE_KEYS),
        ("compatibility", COMPATIBILITY_KEYS),
        ("rollback", ROLLBACK_REQUEST_KEYS),
    ):
        value = template.get(field)
        _contract_expect(isinstance(value, dict) and set(value) == expected, code, f"template {field} keys diverge")
    targets = template.get("targets")
    _contract_expect(isinstance(targets, list) and bool(targets), code, "template targets must be a non-empty array")
    for index, target in enumerate(targets):
        _contract_expect(isinstance(target, dict) and set(target) == TARGET_REQUEST_KEYS, code, f"template target {index} keys diverge")
        adapters = target.get("discovery_adapters") if isinstance(target, dict) else None
        _contract_expect(isinstance(adapters, list), code, f"template target {index} adapters must be an array")
        for adapter_index, adapter in enumerate(adapters):
            _contract_expect(isinstance(adapter, dict) and set(adapter) == ADAPTER_KEYS, code, f"template adapter {index}:{adapter_index} keys diverge")


def validate_contract_artifacts(schema_path: Path, template_path: Path) -> None:
    """Check the shipped schema and request template against the Python contract."""

    schema = _read_json(schema_path, "SCHEMA_PARITY_MISMATCH")
    try:
        _validate_schema_parity(schema)
    except WorkflowError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        fail("SCHEMA_PARITY_MISMATCH", f"malformed schema structure: {exc}")
    template = _read_json(template_path, "TEMPLATE_PARITY_MISMATCH")
    try:
        _validate_template_parity(template)
    except WorkflowError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        fail("TEMPLATE_PARITY_MISMATCH", f"malformed template structure: {exc}")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    if not path.parent.is_dir():
        fail("OUTPUT_PARENT_NOT_FOUND", str(path.parent))
    encoded = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temp_name = handle.name
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except OSError as exc:
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
        fail("MANIFEST_WRITE_FAILED", str(exc))


def _validate_plan_shape(plan: dict[str, Any]) -> None:
    if set(plan) != PLAN_KEYS:
        fail("INVALID_MANIFEST", f"plan keys must be {sorted(PLAN_KEYS)}")
    source = _require_dict(plan.get("source"), "plan.source")
    if set(source) != SOURCE_PLAN_KEYS:
        fail("INVALID_MANIFEST", "plan.source keys are invalid")
    source_path = Path(str(source.get("path")))
    if not source_path.is_absolute() or source_path.resolve(strict=False) != source_path:
        fail("INVALID_MANIFEST", "plan.source.path must be an exact absolute path")
    _require_string(source.get("uri"), "plan.source.uri")
    _component(source.get("expected_skill_name"), "plan.source.expected_skill_name")
    _component(source.get("frontmatter_name"), "plan.source.frontmatter_name")
    if not PLAIN_HASH.fullmatch(str(source.get("tree_sha256"))):
        fail("INVALID_MANIFEST", "plan.source.tree_sha256 is invalid")
    _component(plan.get("implant_id"), "plan.implant_id")
    targets = _require_list(plan.get("targets"), "plan.targets")
    if not targets:
        fail("INVALID_MANIFEST", "plan.targets must not be empty")
    seen_surfaces: set[str] = set()
    seen_destinations: set[str] = set()
    for index, raw_target in enumerate(targets):
        target = _require_dict(raw_target, f"plan.targets[{index}]")
        if set(target) != TARGET_PLAN_KEYS:
            fail("INVALID_MANIFEST", f"plan.targets[{index}] keys are invalid")
        surface = _component(target.get("surface"), f"plan.targets[{index}].surface")
        if surface in seen_surfaces:
            fail("INVALID_MANIFEST", f"duplicate surface {surface!r}")
        seen_surfaces.add(surface)
        root = Path(_require_string(target.get("root"), "target.root"))
        destination = Path(_require_string(target.get("destination"), "target.destination"))
        effective = Path(
            _require_string(target.get("effective_destination"), "target.effective_destination")
        )
        if not root.is_absolute() or destination.parent != root or effective.parent != root:
            fail("INVALID_MANIFEST", "target paths escape the declared root")
        for candidate in (destination, effective):
            _reject_source_target_overlap(source_path, candidate)
        destination_name = _component(target.get("destination_name"), "target.destination_name")
        if destination.name != destination_name:
            fail("INVALID_MANIFEST", "target destination does not match destination_name")
        destination_key = str(effective)
        if destination_key in seen_destinations:
            fail("INVALID_MANIFEST", f"duplicate effective destination {destination_key!r}")
        seen_destinations.add(destination_key)
        method = target.get("method")
        action = target.get("collision_action")
        _require_string(target.get("ownership"), "target.ownership")
        if method not in INSTALL_METHODS or action not in COLLISION_ACTIONS:
            fail("INVALID_MANIFEST", "target method or collision action is invalid")
        if target.get("collision_classification") != action:
            fail("INVALID_MANIFEST", "collision classification differs from collision action")
        rename_to = target.get("rename_to")
        if action == "RENAME":
            rename = _component(rename_to, "target.rename_to")
            if effective.name != rename or rename == destination_name:
                fail("INVALID_MANIFEST", "RENAME destination is invalid")
        elif rename_to is not None or effective != destination:
            fail("INVALID_MANIFEST", "non-RENAME target has an alternate destination")
        minimum = target.get("minimum_discovery_level")
        if minimum not in LEVELS:
            fail("INVALID_MANIFEST", "minimum discovery level is invalid")
        adapters = _require_list(target.get("discovery_adapters"), "target.discovery_adapters")
        checked = [
            _validate_adapter(adapter, f"target.discovery_adapters[{adapter_index}]")
            for adapter_index, adapter in enumerate(adapters)
        ]
        if len({adapter["level"] for adapter in checked}) != len(checked):
            fail("INVALID_MANIFEST", "duplicate discovery adapter levels")
        _validate_path_state(target.get("prior_state"), destination, "target.prior_state")
        alternate = target.get("alternate_prior_state")
        if action == "RENAME" and not isinstance(alternate, dict):
            fail("INVALID_MANIFEST", "RENAME requires alternate prior state")
        if action == "RENAME":
            _validate_path_state(alternate, effective, "target.alternate_prior_state")
        if action != "RENAME" and alternate is not None:
            fail("INVALID_MANIFEST", "alternate prior state is only valid for RENAME")
    scope = _require_dict(plan.get("scope"), "plan.scope")
    if set(scope) != SCOPE_KEYS:
        fail("INVALID_MANIFEST", "plan.scope keys are invalid")
    _require_string(scope.get("goal"), "plan.scope.goal")
    allowed_actions = _string_array(
        scope.get("allowed_actions"), "plan.scope.allowed_actions", nonempty=True
    )
    _string_array(
        scope.get("excluded_expansions"), "plan.scope.excluded_expansions", nonempty=True
    )
    compatibility = _require_dict(plan.get("compatibility"), "plan.compatibility")
    if set(compatibility) != COMPATIBILITY_KEYS:
        fail("INVALID_MANIFEST", "plan.compatibility keys are invalid")
    if compatibility.get("status") not in {"compatible", "incompatible"}:
        fail("INVALID_MANIFEST", "compatibility status is invalid")
    reasons = _string_array(
        compatibility.get("blocking_reasons"), "compatibility.blocking_reasons"
    )
    if compatibility.get("status") == "incompatible" and not reasons:
        fail("INVALID_MANIFEST", "incompatible plans require blocking reasons")
    rollback = _require_dict(plan.get("rollback"), "plan.rollback")
    if set(rollback) != ROLLBACK_PLAN_KEYS:
        fail("INVALID_MANIFEST", "plan.rollback keys are invalid")
    if rollback.get("required") is not True:
        fail("INVALID_MANIFEST", "rollback must be required")
    if not isinstance(rollback.get("backup_root_required_for_replace"), bool):
        fail("INVALID_MANIFEST", "backup root requirement must be boolean")
    backup_root = Path(_require_string(rollback.get("backup_root"), "plan.rollback.backup_root"))
    if not backup_root.is_absolute() or backup_root.resolve(strict=False) != backup_root:
        fail("INVALID_MANIFEST", "plan.rollback.backup_root must be an exact absolute path")
    if rollback.get("removes_only_manifest_created_targets") is not True:
        fail("INVALID_MANIFEST", "rollback removal boundary must be true")
    if rollback.get("keeps_existing_keep_targets") is not True:
        fail("INVALID_MANIFEST", "rollback KEEP boundary must be true")
    if "rollback" not in allowed_actions:
        fail("INVALID_MANIFEST", "rollback is outside the allowed scope")
    for target in targets:
        if target["method"] not in allowed_actions:
            fail("INVALID_MANIFEST", "target method is outside the allowed scope")
        if target["minimum_discovery_level"] != "present" and "verify" not in allowed_actions:
            fail("INVALID_MANIFEST", "native discovery is outside the allowed scope")


def _validate_path_state(value: object, path: Path, field: str) -> None:
    state = _require_dict(value, field)
    base_keys = {"path", "exists", "kind"}
    kind = state.get("kind")
    expected_keys = set(base_keys)
    if kind == "link":
        expected_keys.add("link_target")
    elif kind == "directory":
        expected_keys.add("tree_sha256")
    elif kind == "file":
        expected_keys.add("sha256")
    elif kind not in {"absent", "other"}:
        fail("INVALID_MANIFEST", f"{field}.kind is invalid")
    if set(state) != expected_keys:
        fail("INVALID_MANIFEST", f"{field} keys do not match its kind")
    if state.get("path") != str(path):
        fail("INVALID_MANIFEST", f"{field}.path differs from its destination")
    exists = state.get("exists")
    if not isinstance(exists, bool) or exists != (kind != "absent"):
        fail("INVALID_MANIFEST", f"{field}.exists is inconsistent")
    if kind == "link":
        _require_string(state.get("link_target"), f"{field}.link_target", nonempty=False)
    if kind == "directory" and not PLAIN_HASH.fullmatch(str(state.get("tree_sha256"))):
        fail("INVALID_MANIFEST", f"{field}.tree_sha256 is invalid")
    if kind == "file" and not PLAIN_HASH.fullmatch(str(state.get("sha256"))):
        fail("INVALID_MANIFEST", f"{field}.sha256 is invalid")


def _validate_sanitized_runtime(value: object, field: str) -> None:
    stack: list[tuple[object, str]] = [(value, field)]
    while stack:
        item, location = stack.pop()
        if isinstance(item, dict):
            leaked = FORBIDDEN_RECEIPT_KEYS.intersection(item)
            if leaked:
                fail("UNSANITIZED_RECEIPT", f"{location} contains {sorted(leaked)}")
            for key, child in item.items():
                if key in {"command_sha256", "stdout_sha256", "stderr_sha256"}:
                    if not PLAIN_HASH.fullmatch(str(child)):
                        fail("INVALID_MANIFEST", f"{location}.{key} is invalid")
                stack.append((child, f"{location}.{key}"))
        elif isinstance(item, list):
            for index, child in enumerate(item):
                stack.append((child, f"{location}[{index}]"))


def load_and_validate_manifest(path: Path) -> dict[str, Any]:
    validate_contract_artifacts(DEFAULT_SCHEMA_PATH, DEFAULT_TEMPLATE_PATH)
    manifest = _read_json(path, "INVALID_MANIFEST")
    if set(manifest) != MANIFEST_KEYS:
        fail("INVALID_MANIFEST", f"top-level keys must be {sorted(MANIFEST_KEYS)}")
    plan = manifest.get("plan")
    stored_hash = manifest.get("plan_hash")
    if not isinstance(plan, dict) or not isinstance(stored_hash, str):
        fail("INVALID_MANIFEST", "plan and plan_hash are required")
    if plan_hash(plan) != stored_hash:
        fail("PLAN_HASH_MISMATCH")
    if not HASH_RECEIPT.fullmatch(stored_hash):
        fail("INVALID_MANIFEST", "plan_hash has an invalid format")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        fail("INVALID_MANIFEST", f"schema_version must be {SCHEMA_VERSION}")
    if manifest.get("status") not in MANIFEST_STATUSES:
        fail("INVALID_MANIFEST", "status is invalid")
    receipts = _require_dict(manifest.get("receipts"), "receipts")
    events = _require_list(manifest.get("events"), "events")
    _validate_sanitized_runtime(receipts, "receipts")
    _validate_sanitized_runtime(events, "events")
    _validate_plan_shape(plan)
    return manifest


def _event(manifest: dict[str, Any], phase: str, result: str, code: str | None = None) -> None:
    item = {"phase": phase, "result": result}
    if code:
        item["code"] = code
    manifest["events"].append(item)


def inspect_request(request_path: Path, manifest_path: Path) -> None:
    validate_contract_artifacts(DEFAULT_SCHEMA_PATH, DEFAULT_TEMPLATE_PATH)
    request = _read_json(request_path, "INVALID_REQUEST")
    plan = build_plan(request)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "plan": plan,
        "plan_hash": plan_hash(plan),
        "status": "INSPECTED",
        "receipts": {"targets": {}},
        "events": [{"phase": "inspect", "result": "passed"}],
    }
    _write_json(manifest_path, manifest)


def _source_path(plan: dict[str, Any]) -> Path:
    return Path(plan["source"]["path"])


def _check_source(plan: dict[str, Any]) -> str:
    observed = tree_sha256(_source_path(plan))
    if observed != plan["source"]["tree_sha256"]:
        fail("SOURCE_DRIFT", "canonical source tree hash changed")
    return observed


def _same_prior_state(expected: dict[str, Any], path: Path) -> bool:
    return _path_state(path) == expected


def _same_content_state(expected: dict[str, Any], path: Path) -> bool:
    try:
        observed = _path_state(path)
    except (OSError, WorkflowError):
        return False
    observed["path"] = expected["path"]
    return observed == expected


def _matches_source(destination: Path, source: Path, source_hash: str) -> bool:
    if not _lexists(destination):
        return False
    if destination.is_symlink():
        try:
            return os.path.samefile(destination, source)
        except OSError:
            return False
    if destination.is_dir():
        try:
            return tree_sha256(destination) == source_hash
        except (OSError, WorkflowError):
            return False
    return False


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _is_exact_directory(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink() and path.resolve(strict=True) == path
    except OSError:
        return False


def _validate_backup_ancestors(backup: Path, backup_root: Path) -> None:
    try:
        relative_parent = backup.parent.relative_to(backup_root)
    except ValueError:
        fail("BACKUP_PATH_INVALID", str(backup))
    current = backup_root
    for component in relative_parent.parts:
        current = current / component
        if _lexists(current) and (current.is_symlink() or not current.is_dir()):
            fail("BACKUP_PATH_INVALID", str(current))


def _backup_path(backup_root: Path, plan: dict[str, Any], target: dict[str, Any]) -> Path:
    return backup_root / plan["implant_id"] / target["surface"] / target["destination_name"]


def apply_manifest(manifest_path: Path, approval_token: str, backup_root_raw: str) -> None:
    manifest = load_and_validate_manifest(manifest_path)
    if approval_token != manifest["plan_hash"]:
        fail("APPROVAL_TOKEN_MISMATCH")
    if manifest["status"] != "INSPECTED":
        fail("MANIFEST_STATE_INVALID", f"apply requires INSPECTED, found {manifest['status']}")
    plan = manifest["plan"]
    sealed_backup_root = Path(plan["rollback"]["backup_root"])
    supplied_backup_root = Path(backup_root_raw)
    if not supplied_backup_root.is_absolute():
        supplied_backup_root = (Path.cwd() / supplied_backup_root).resolve(strict=False)
    else:
        supplied_backup_root = supplied_backup_root.resolve(strict=False)
    if supplied_backup_root != sealed_backup_root:
        fail("BACKUP_ROOT_MISMATCH")
    source = _source_path(plan)
    source_hash = _check_source(plan)
    if plan["compatibility"]["status"] != "compatible":
        fail("INCOMPATIBLE_FRAMEWORK", "; ".join(plan["compatibility"]["blocking_reasons"]))
    backup_root = sealed_backup_root
    if _inside(backup_root, source):
        fail("BACKUP_ROOT_INVALID", "backup root cannot be inside the canonical source")
    for target in plan["targets"]:
        for destination_value in (target["destination"], target["effective_destination"]):
            destination = Path(destination_value)
            if _inside(backup_root, destination) or _inside(destination, backup_root):
                fail("BACKUP_ROOT_INVALID", "backup root cannot overlap a target destination")

    prepared: list[dict[str, Any]] = []
    for target in plan["targets"]:
        root = Path(target["root"])
        destination = Path(target["destination"])
        effective = Path(target["effective_destination"])
        action = target["collision_action"]
        if not _is_exact_directory(root):
            fail("TARGET_ROOT_NOT_FOUND", str(root))
        if not _same_prior_state(target["prior_state"], destination):
            fail("PRIOR_STATE_CHANGED", str(destination))
        if action == "RENAME" and not _same_prior_state(
            target["alternate_prior_state"], effective
        ):
            fail("PRIOR_STATE_CHANGED", str(effective))
        if action == "MERGE":
            fail("MERGE_REQUIRES_HUMAN", str(destination))
        exists = _lexists(destination)
        if action == "BLOCK" and exists:
            fail("COLLISION_BLOCKED", str(destination))
        if action == "KEEP":
            if not _matches_source(destination, source, source_hash):
                fail("KEEP_SOURCE_MISMATCH", str(destination))
            prepared.append(
                {
                    "target": target,
                    "effective": destination,
                    "keep": True,
                    "backup": None,
                }
            )
            continue
        if action == "RENAME" and _lexists(effective):
            fail("RENAME_DESTINATION_OCCUPIED", str(effective))
        backup = None
        if action == "REPLACE" and exists:
            backup = _backup_path(backup_root, plan, target)
            _validate_backup_ancestors(backup, backup_root)
            if _lexists(backup):
                fail("BACKUP_DESTINATION_OCCUPIED", str(backup))
        prepared.append(
            {
                "target": target,
                "effective": effective,
                "keep": False,
                "backup": backup,
            }
        )

    mutations: list[dict[str, Any]] = []
    target_receipts: dict[str, Any] = {}
    try:
        for item in prepared:
            target = item["target"]
            effective = item["effective"]
            backup = item["backup"]
            surface = target["surface"]
            if item["keep"]:
                target_receipts[surface] = {
                    "install": {
                        "passed": True,
                        "status": "KEPT",
                        "method": target["method"],
                        "collision_action": "KEEP",
                        "effective_destination": str(effective),
                        "created_by_manifest": False,
                        "backup_path": None,
                        "installed_tree_sha256": source_hash,
                    }
                }
                continue
            mutation = {
                "destination": effective,
                "backup": backup,
                "backup_original": Path(target["destination"]),
                "created_destination": False,
                "backed_up": False,
            }
            mutations.append(mutation)
            if backup is not None:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target["destination"]), str(backup))
                mutation["backed_up"] = True
            if target["method"] == "link":
                os.symlink(str(source), str(effective), target_is_directory=True)
                mutation["created_destination"] = True
            else:
                effective.mkdir()
                mutation["created_destination"] = True
                shutil.copytree(source, effective, symlinks=True, dirs_exist_ok=True)
            installed_hash = tree_sha256(effective) if target["method"] == "copy" else source_hash
            target_receipts[surface] = {
                "install": {
                    "passed": True,
                    "status": "INSTALLED",
                    "method": target["method"],
                    "collision_action": target["collision_action"],
                    "effective_destination": str(effective),
                    "created_by_manifest": True,
                    "backup_path": str(backup) if backup else None,
                    "installed_tree_sha256": installed_hash,
                }
            }
        source_after = _check_source(plan)
        manifest["receipts"]["targets"] = target_receipts
        manifest["receipts"]["apply"] = {
            "passed": True,
            "status": "APPLIED",
            "source_sha256_before": source_hash,
            "source_sha256_after": source_after,
            "backup_root": str(backup_root),
        }
        manifest["status"] = "APPLIED"
        _event(manifest, "apply", "passed")
        _write_json(manifest_path, manifest)
    except Exception as exc:
        restore_errors: list[str] = []
        for mutation in reversed(mutations):
            try:
                if mutation["created_destination"]:
                    _remove_path(mutation["destination"])
                if mutation["backed_up"] and _lexists(mutation["backup"]):
                    mutation["backup_original"].parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(mutation["backup"]), str(mutation["backup_original"]))
            except OSError as restore_exc:
                restore_errors.append(str(restore_exc))
        if restore_errors:
            fail("TRANSACTION_RESTORE_FAILED", "; ".join(restore_errors))
        if isinstance(exc, WorkflowError):
            raise
        fail("APPLY_FAILED", str(exc))


def _command_sha256(argv: list[str]) -> str:
    return sha256_bytes(canonical_json(argv))


def _timeout_bytes(value: object) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8", errors="replace")


def _run_sanitized(
    argv: list[str], timeout_seconds: int | float, pattern: str, *, version: bool
) -> tuple[dict[str, Any], bool]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        return_code: int | None = proc.returncode
        match = bool(
            re.search(pattern, (stdout + b"\n" + stderr).decode("utf-8", errors="replace"))
        )
        passed = proc.returncode == 0 and match
        status = "PASSED" if passed else ("VERSION_MISMATCH" if version else "DISCOVERY_FAILED")
    except subprocess.TimeoutExpired as exc:
        stdout = _timeout_bytes(exc.stdout)
        stderr = _timeout_bytes(exc.stderr)
        return_code = None
        match = False
        passed = False
        status = "TIMEOUT"
    except OSError:
        stdout = b""
        stderr = b""
        return_code = None
        match = False
        passed = False
        status = "EXECUTABLE_NOT_FOUND"
    duration = round(time.monotonic() - started, 6)
    receipt = {
        "status": status,
        "return_code": return_code,
        "duration_seconds": duration,
        "command_sha256": _command_sha256(argv),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "version_match": match if version else None,
        "passed": passed,
    }
    return receipt, passed


def _adapter_receipt(
    adapter: dict[str, Any], allowed: set[str]
) -> tuple[dict[str, Any], str | None]:
    version_argv = adapter["version_command"]
    command_argv = adapter["command"]
    for argv in (version_argv, command_argv):
        if argv[0] not in allowed:
            empty_hash = sha256_bytes(b"")
            blocked = {
                "passed": False,
                "status": "EXECUTABLE_NOT_ALLOWED",
                "return_code": None,
                "duration_seconds": 0.0,
                "command_sha256": _command_sha256(argv),
                "stdout_sha256": empty_hash,
                "stderr_sha256": empty_hash,
                "version_match": False,
            }
            return (
                {
                    "passed": False,
                    "status": "EXECUTABLE_NOT_ALLOWED",
                    "version": blocked,
                    "discovery": None,
                },
                "EXECUTABLE_NOT_ALLOWED",
            )
    version_receipt, version_passed = _run_sanitized(
        version_argv,
        adapter["timeout_seconds"],
        adapter["version_regex"],
        version=True,
    )
    if not version_passed:
        return (
            {
                "passed": False,
                "status": version_receipt["status"],
                "version": version_receipt,
                "discovery": None,
            },
            version_receipt["status"],
        )
    discovery_receipt, discovery_passed = _run_sanitized(
        command_argv,
        adapter["timeout_seconds"],
        adapter["success_regex"],
        version=False,
    )
    return (
        {
            "passed": discovery_passed,
            "status": discovery_receipt["status"],
            "version": version_receipt,
            "discovery": discovery_receipt,
        },
        None if discovery_passed else discovery_receipt["status"],
    )


def verify_manifest(
    manifest_path: Path, level: str, allow_executables: list[str]
) -> None:
    manifest = load_and_validate_manifest(manifest_path)
    if level not in LEVELS:
        fail("INVALID_DISCOVERY_LEVEL", level)
    if manifest["status"] not in {"APPLIED", "VERIFIED", "VERIFY_FAILED"}:
        fail("MANIFEST_STATE_INVALID", f"verify cannot run from {manifest['status']}")
    plan = manifest["plan"]
    source_hash = _check_source(plan)
    allowed = set(allow_executables)
    required_index = LEVELS.index(level)
    overall = True
    failure_codes: list[str] = []
    existing_receipts = manifest["receipts"].setdefault("targets", {})

    for target in plan["targets"]:
        surface = target["surface"]
        destination = Path(target["effective_destination"])
        target_receipt = existing_receipts.setdefault(surface, {})
        present = _lexists(destination)
        target_receipt["present"] = {
            "passed": present,
            "status": "PRESENT" if present else "MISSING",
        }
        if not present:
            overall = False
            failure_codes.append("PRESENCE_FAILED")

        integrity = False
        integrity_mode = target["method"]
        observed_hash: str | None = None
        if present:
            if target["collision_action"] == "KEEP":
                integrity_mode = "link" if destination.is_symlink() else "copy"
                integrity = _matches_source(destination, _source_path(plan), source_hash)
                if integrity and not destination.is_symlink():
                    observed_hash = source_hash
            elif target["method"] == "link" and destination.is_symlink():
                try:
                    integrity = os.path.samefile(destination, _source_path(plan))
                except OSError:
                    integrity = False
            elif (
                target["method"] == "copy"
                and not destination.is_symlink()
                and destination.is_dir()
            ):
                try:
                    observed_hash = tree_sha256(destination)
                    integrity = observed_hash == source_hash
                except (OSError, WorkflowError):
                    integrity = False
        target_receipt["integrity"] = {
            "passed": integrity,
            "status": "MATCHED" if integrity else "INTEGRITY_FAILED",
            "method": integrity_mode,
            "tree_sha256": observed_hash,
        }
        if not integrity:
            overall = False
            failure_codes.append("INTEGRITY_FAILED")

        adapters = {adapter["level"]: adapter for adapter in target["discovery_adapters"]}
        prerequisites_passed = present and integrity
        for level_index, current_level in enumerate(LEVELS[1:], start=1):
            if level_index > required_index:
                target_receipt[current_level] = {
                    "passed": False,
                    "status": "NOT_RUN",
                    "version": None,
                    "discovery": None,
                }
                continue
            if not prerequisites_passed:
                target_receipt[current_level] = {
                    "passed": False,
                    "status": "PREREQUISITE_FAILED",
                    "version": None,
                    "discovery": None,
                }
                overall = False
                continue
            adapter = adapters.get(current_level)
            if adapter is None:
                target_receipt[current_level] = {
                    "passed": False,
                    "status": "ADAPTER_MISSING",
                    "version": None,
                    "discovery": None,
                }
                overall = False
                failure_codes.append("ADAPTER_MISSING")
                prerequisites_passed = False
                continue
            receipt, error_code = _adapter_receipt(adapter, allowed)
            target_receipt[current_level] = receipt
            if not receipt["passed"]:
                overall = False
                failure_codes.append(error_code or "DISCOVERY_FAILED")
                prerequisites_passed = False

        if required_index < LEVELS.index(target["minimum_discovery_level"]):
            overall = False
            failure_codes.append("DISCOVERY_LEVEL_BELOW_MINIMUM")

    manifest["receipts"]["verify"] = {
        "passed": overall,
        "status": "VERIFIED" if overall else "VERIFY_FAILED",
        "requested_level": level,
        "source_tree_sha256": source_hash,
    }
    manifest["status"] = "VERIFIED" if overall else "VERIFY_FAILED"
    _event(manifest, "verify", "passed" if overall else "failed", None if overall else failure_codes[0])
    _write_json(manifest_path, manifest)
    if not overall:
        fail(failure_codes[0] if failure_codes else "VERIFY_FAILED")


def _restore_rollback_mutations(
    mutations: list[dict[str, Any]], staging_root: Path
) -> list[str]:
    restore_errors: list[str] = []
    for mutation in reversed(mutations):
        if mutation["backup_restored"]:
            try:
                mutation["backup"].parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(mutation["original"]), str(mutation["backup"]))
            except (OSError, WorkflowError) as restore_exc:
                restore_errors.append(str(restore_exc))
        if mutation["target_staged"]:
            try:
                shutil.move(str(mutation["staged"]), str(mutation["destination"]))
            except (OSError, WorkflowError) as restore_exc:
                restore_errors.append(str(restore_exc))
    if not restore_errors:
        try:
            if _lexists(staging_root):
                shutil.rmtree(staging_root)
        except OSError as cleanup_exc:
            restore_errors.append(str(cleanup_exc))
    return restore_errors


def _rollback_staging_path(manifest: dict[str, Any]) -> Path:
    backup_root = Path(manifest["plan"]["rollback"]["backup_root"])
    return backup_root / f".rollback-staging-{manifest['plan_hash'][7:]}"


def _validate_rollback_staging(
    manifest: dict[str, Any], staging_root: Path, *, allow_partial: bool
) -> None:
    expected_staging = _rollback_staging_path(manifest)
    if staging_root != expected_staging:
        fail("ROLLBACK_RECEIPT_INVALID", "rollback staging path differs from sealed plan")
    if not _lexists(staging_root):
        return
    if staging_root.is_symlink() or not staging_root.is_dir():
        fail("ROLLBACK_STAGING_DRIFT", "rollback staging path changed kind")

    targets = [
        target
        for target in manifest["plan"]["targets"]
        if target["collision_action"] != "KEEP"
    ]
    expected_surfaces = {target["surface"] for target in targets}
    try:
        observed_surfaces = {child.name for child in staging_root.iterdir()}
    except OSError:
        fail("ROLLBACK_STAGING_DRIFT", "rollback staging contents are unreadable")
    if (
        observed_surfaces != expected_surfaces
        if not allow_partial
        else not observed_surfaces.issubset(expected_surfaces)
    ):
        fail("ROLLBACK_STAGING_DRIFT", "rollback staging contents changed")
    source = _source_path(manifest["plan"])
    source_hash = manifest["plan"]["source"]["tree_sha256"]
    for target in targets:
        surface_root = staging_root / target["surface"]
        if target["surface"] not in observed_surfaces:
            continue
        staged = surface_root / "installed-target"
        if surface_root.is_symlink() or not surface_root.is_dir():
            fail("ROLLBACK_STAGING_DRIFT", target["surface"])
        try:
            observed_entries = {child.name for child in surface_root.iterdir()}
        except OSError:
            fail("ROLLBACK_STAGING_DRIFT", target["surface"])
        if (
            observed_entries != {"installed-target"}
            if not allow_partial
            else not observed_entries.issubset({"installed-target"})
        ):
            fail("ROLLBACK_STAGING_DRIFT", target["surface"])
        if not observed_entries:
            continue
        if target["method"] == "link":
            try:
                matched = staged.is_symlink() and os.path.samefile(staged, source)
            except OSError:
                matched = False
        else:
            matched = staged.is_dir() and not staged.is_symlink()
            if matched:
                try:
                    matched = tree_sha256(staged) == source_hash
                except (OSError, WorkflowError):
                    matched = False
        if not matched:
            fail("ROLLBACK_STAGING_DRIFT", target["surface"])


def _finish_rollback_cleanup(
    manifest_path: Path, manifest: dict[str, Any]
) -> None:
    rollback_receipt = manifest["receipts"].get("rollback")
    if not isinstance(rollback_receipt, dict):
        fail("ROLLBACK_RECEIPT_INVALID", "rollback receipt is missing")
    cleanup = rollback_receipt.get("cleanup")
    if not isinstance(cleanup, dict):
        fail("ROLLBACK_RECEIPT_INVALID", "rollback cleanup receipt is missing")
    staging_value = cleanup.get("staging_path")
    if not isinstance(staging_value, str):
        fail("ROLLBACK_RECEIPT_INVALID", "rollback staging path is missing")
    staging_root = Path(staging_value)
    _validate_rollback_staging(
        manifest,
        staging_root,
        allow_partial=cleanup.get("status") == "CLEANUP_FAILED",
    )
    if _lexists(staging_root):
        try:
            shutil.rmtree(staging_root)
        except OSError:
            cleanup.update({"passed": False, "status": "CLEANUP_FAILED"})
            rollback_receipt.update(
                {"passed": False, "status": "ROLLED_BACK_CLEANUP_FAILED"}
            )
            _event(manifest, "rollback_cleanup", "failed", "ROLLBACK_CLEANUP_FAILED")
            _write_json(manifest_path, manifest)
            fail("ROLLBACK_CLEANUP_FAILED")
    cleanup.update({"passed": True, "status": "CLEANED"})
    rollback_receipt.update({"passed": True, "status": "ROLLED_BACK"})
    _event(manifest, "rollback", "passed")
    _write_json(manifest_path, manifest)


def rollback_manifest(manifest_path: Path, approval_token: str) -> None:
    manifest = load_and_validate_manifest(manifest_path)
    if approval_token != manifest["plan_hash"]:
        fail("APPROVAL_TOKEN_MISMATCH")
    plan = manifest["plan"]
    if manifest["status"] == "ROLLED_BACK":
        rollback_receipt = manifest["receipts"].get("rollback")
        cleanup = rollback_receipt.get("cleanup") if isinstance(rollback_receipt, dict) else None
        if isinstance(cleanup, dict) and cleanup.get("status") != "CLEANED":
            _finish_rollback_cleanup(manifest_path, manifest)
        print("ALREADY_ROLLED_BACK")
        return
    apply_receipt = manifest["receipts"].get("apply")
    if not isinstance(apply_receipt, dict) or apply_receipt.get("passed") is not True:
        fail("NOT_APPLIED")
    target_receipts = manifest["receipts"].get("targets", {})
    if not isinstance(target_receipts, dict):
        fail("ROLLBACK_RECEIPT_INVALID", "target receipts must be an object")
    backup_root = Path(plan["rollback"]["backup_root"])
    if apply_receipt.get("backup_root") != str(backup_root):
        fail("ROLLBACK_RECEIPT_INVALID", "apply backup root differs from sealed plan")
    source = _source_path(plan)

    prepared: list[dict[str, Any]] = []
    for target in plan["targets"]:
        root = Path(target["root"])
        if not _is_exact_directory(root):
            fail("TARGET_ROOT_DRIFT", target["surface"])
        surface_receipts = target_receipts.get(target["surface"])
        if not isinstance(surface_receipts, dict):
            fail("ROLLBACK_RECEIPT_MISSING", target["surface"])
        receipt = surface_receipts.get("install")
        if not isinstance(receipt, dict) or receipt.get("passed") is not True:
            fail("ROLLBACK_RECEIPT_MISSING", target["surface"])
        expected_destination = Path(target["effective_destination"])
        if receipt.get("effective_destination") != str(expected_destination):
            fail("ROLLBACK_RECEIPT_INVALID", target["surface"])
        if receipt.get("method") != target["method"]:
            fail("ROLLBACK_RECEIPT_INVALID", target["surface"])
        if receipt.get("collision_action") != target["collision_action"]:
            fail("ROLLBACK_RECEIPT_INVALID", target["surface"])
        installed_hash = receipt.get("installed_tree_sha256")
        if installed_hash != plan["source"]["tree_sha256"]:
            fail("ROLLBACK_RECEIPT_INVALID", target["surface"])
        created = receipt.get("created_by_manifest") is True
        if target["collision_action"] == "KEEP" and created:
            fail("ROLLBACK_RECEIPT_INVALID", "KEEP cannot be manifest-created")
        if target["collision_action"] != "KEEP" and not created:
            fail("ROLLBACK_RECEIPT_INVALID", "installed target must be manifest-created")
        backup_value = receipt.get("backup_path")
        if backup_value is not None and not isinstance(backup_value, str):
            fail("ROLLBACK_RECEIPT_INVALID", target["surface"])
        backup = Path(backup_value) if isinstance(backup_value, str) else None
        expected_backup = (
            _backup_path(backup_root, plan, target)
            if target["collision_action"] == "REPLACE"
            and target["prior_state"]["exists"]
            else None
        )
        if backup != expected_backup:
            fail("ROLLBACK_RECEIPT_INVALID", target["surface"])
        if backup is not None:
            _validate_backup_ancestors(backup, backup_root)
            if not _inside(backup, backup_root):
                fail("ROLLBACK_RECEIPT_INVALID", target["surface"])
            if not _lexists(backup):
                fail("BACKUP_NOT_FOUND", str(backup))
            if not _same_content_state(target["prior_state"], backup):
                fail("ROLLBACK_BACKUP_DRIFT", target["surface"])
        if created:
            if target["method"] == "link":
                try:
                    matches_install = expected_destination.is_symlink() and os.path.samefile(
                        expected_destination, source
                    )
                except OSError:
                    matches_install = False
            else:
                matches_install = (
                    not expected_destination.is_symlink()
                    and expected_destination.is_dir()
                )
                if matches_install:
                    try:
                        matches_install = tree_sha256(expected_destination) == installed_hash
                    except (OSError, WorkflowError):
                        matches_install = False
            if not matches_install:
                fail("ROLLBACK_TARGET_DRIFT", target["surface"])
        prepared.append(
            {
                "target": target,
                "destination": expected_destination,
                "created": created,
                "backup": backup,
            }
        )

    backup_root.mkdir(parents=True, exist_ok=True)
    staging_root = _rollback_staging_path(manifest)
    if _lexists(staging_root):
        if staging_root.is_symlink() or not staging_root.is_dir():
            fail("ROLLBACK_STAGING_OCCUPIED", str(staging_root))
        try:
            next(staging_root.iterdir())
        except StopIteration:
            staging_root.rmdir()
        else:
            fail("ROLLBACK_STAGING_OCCUPIED", str(staging_root))
    staging_root.mkdir(mode=0o700)
    rollback_targets: dict[str, Any] = {}
    mutations: list[dict[str, Any]] = []
    try:
        for item in reversed(prepared):
            target = item["target"]
            destination = item["destination"]
            mutation = {
                "destination": destination,
                "staged": staging_root / target["surface"] / "installed-target",
                "backup": item["backup"],
                "original": Path(target["destination"]),
                "target_staged": False,
                "backup_restored": False,
            }
            mutations.append(mutation)
            if item["created"]:
                mutation["staged"].parent.mkdir(parents=True, exist_ok=False)
                shutil.move(str(destination), str(mutation["staged"]))
                mutation["target_staged"] = True
            backup = item["backup"]
            if backup is not None:
                original = mutation["original"]
                if _lexists(original):
                    fail("ROLLBACK_DESTINATION_OCCUPIED", str(original))
                shutil.move(str(backup), str(original))
                mutation["backup_restored"] = True
            rollback_targets[target["surface"]] = {
                "passed": True,
                "status": "KEPT" if target["collision_action"] == "KEEP" else "ROLLED_BACK",
                "removed_manifest_target": item["created"],
                "restored_backup": backup is not None,
            }
    except Exception as exc:
        restore_errors = _restore_rollback_mutations(mutations, staging_root)
        if restore_errors:
            fail("TRANSACTION_RESTORE_FAILED", "; ".join(restore_errors))
        if isinstance(exc, WorkflowError):
            raise
        fail("ROLLBACK_FAILED", str(exc))

    manifest["receipts"]["rollback"] = {
        "passed": False,
        "status": "ROLLED_BACK_CLEANUP_PENDING",
        "targets": rollback_targets,
        "cleanup": {
            "passed": False,
            "status": "CLEANUP_PENDING",
            "staging_path": str(staging_root),
        },
    }
    manifest["status"] = "ROLLED_BACK"
    try:
        _write_json(manifest_path, manifest)
    except WorkflowError:
        restore_errors = _restore_rollback_mutations(mutations, staging_root)
        if restore_errors:
            fail("TRANSACTION_RESTORE_FAILED", "; ".join(restore_errors))
        raise
    _finish_rollback_cleanup(manifest_path, manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--request", type=Path, required=True)
    inspect_parser.add_argument("--manifest", type=Path, required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--manifest", type=Path, required=True)
    apply_parser.add_argument("--approval-token", required=True)
    apply_parser.add_argument("--backup-root", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.add_argument("--level", choices=LEVELS, required=True)
    verify_parser.add_argument("--allow-executable", action="append", default=[])

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--manifest", type=Path, required=True)
    rollback_parser.add_argument("--approval-token", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            inspect_request(args.request, args.manifest)
        elif args.command == "apply":
            apply_manifest(args.manifest, args.approval_token, args.backup_root)
        elif args.command == "verify":
            verify_manifest(args.manifest, args.level, args.allow_executable)
        elif args.command == "rollback":
            rollback_manifest(args.manifest, args.approval_token)
    except WorkflowError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
