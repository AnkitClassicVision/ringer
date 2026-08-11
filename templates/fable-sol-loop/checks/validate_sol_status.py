#!/usr/bin/env python3
"""Validate Sol READY/HOLD status, execute proof, and compute the review gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from lib_packets import (
    PacketError,
    WhyArgumentParser,
    decision_units_by_id,
    load_json_object,
    normalize_path_list,
    path_is_owned,
    path_matches_surface,
    print_why,
    reject_extra_keys,
    require,
    require_keys,
    require_string,
    run_verification,
    sanitized_subprocess_env,
    validate_declared_result,
    validate_hold,
    validate_verification_command,
    write_json,
)


STATUS_STATES = {"COMPLETE", "PARTIAL", "NOT_STARTED", "BLOCKED"}


def validate_status_packet(data: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    decision_units = decision_units_by_id(decision)
    required = ("status", "build_units", "deviations", "holds", "probes", "diff_summary")
    allowed = required + ("review_required", "review_reasons")
    require_keys(data, required, where="Sol status packet")
    reject_extra_keys(data, allowed, where="Sol status packet")
    require(data["status"] in {"READY", "HOLD"}, "status must be READY or HOLD")

    units = data["build_units"]
    require(isinstance(units, list) and bool(units), "build_units must be a non-empty list")
    seen_ids: list[str] = []
    for index, unit in enumerate(units):
        where = f"build_units[{index}]"
        require(isinstance(unit, dict), f"{where} must be an object")
        fields = ("id", "state", "verification_command", "verification_result")
        require_keys(unit, fields, where=where)
        reject_extra_keys(unit, fields, where=where)
        unit_id = require_string(unit["id"], where=f"{where}.id")
        seen_ids.append(unit_id)
        require(unit_id in decision_units, f"{where}.id is not in the decision contract: {unit_id}")
        require(unit["state"] in STATUS_STATES, f"{where}.state is not recognized")
        command = validate_verification_command(unit["verification_command"], where=f"{where}.verification_command")
        require(command == decision_units[unit_id]["verification_command"], f"{where}.verification_command differs from Fable's contract")
        validate_declared_result(unit["verification_result"], where=f"{where}.verification_result")
    require(len(seen_ids) == len(set(seen_ids)), "build unit ids must be unique")
    require(set(seen_ids) == set(decision_units), "build_units must report every decision-contract unit exactly once")

    deviations = data["deviations"]
    require(isinstance(deviations, list), "deviations must be a list")
    for index, deviation in enumerate(deviations):
        where = f"deviations[{index}]"
        require(isinstance(deviation, dict), f"{where} must be an object")
        fields = ("what", "why", "material")
        require_keys(deviation, fields, where=where)
        reject_extra_keys(deviation, fields, where=where)
        require_string(deviation["what"], where=f"{where}.what", min_length=5)
        require_string(deviation["why"], where=f"{where}.why", min_length=5)
        require(isinstance(deviation["material"], bool), f"{where}.material must be a boolean")

    holds = data["holds"]
    require(isinstance(holds, list), "holds must be a list")
    for index, hold in enumerate(holds):
        validate_hold(hold, where=f"holds[{index}]")
    if data["status"] == "HOLD":
        require(bool(holds), "status HOLD requires at least one complete HOLD entry")
    else:
        require(not holds, "status READY cannot contain HOLD entries")

    probes = data["probes"]
    require(isinstance(probes, list), "probes must be a list")
    unknown_ids = {item["id"] for item in decision["unknowns"]}
    for index, probe in enumerate(probes):
        where = f"probes[{index}]"
        require(isinstance(probe, dict), f"{where} must be an object")
        fields = ("unknown_id", "finding", "evidence")
        require_keys(probe, fields, where=where)
        reject_extra_keys(probe, fields, where=where)
        unknown_id = require_string(probe["unknown_id"], where=f"{where}.unknown_id")
        require(unknown_id in unknown_ids, f"{where}.unknown_id is not declared in the decision packet")
        require_string(probe["finding"], where=f"{where}.finding", min_length=8)
        require_string(probe["evidence"], where=f"{where}.evidence", min_length=5)

    summary = data["diff_summary"]
    require(isinstance(summary, dict), "diff_summary must be an object")
    fields = ("paths_touched", "files_changed", "insertions", "deletions")
    require_keys(summary, fields, where="diff_summary")
    reject_extra_keys(summary, fields, where="diff_summary")
    normalize_path_list(summary["paths_touched"], where="diff_summary.paths_touched")
    for field in ("files_changed", "insertions", "deletions"):
        require(isinstance(summary[field], int) and not isinstance(summary[field], bool) and summary[field] >= 0, f"diff_summary.{field} must be a non-negative integer")
    require(summary["files_changed"] == len(summary["paths_touched"]), "diff_summary.files_changed must equal the number of unique paths_touched")

    return data


def compute_review_gate(data: dict[str, Any], decision: dict[str, Any]) -> tuple[bool, list[str], list[dict[str, Any]]]:
    """Compute the locked objective gate without relying on Sol's conclusion."""

    validate_status_packet(data, decision)
    paths = normalize_path_list(data["diff_summary"]["paths_touched"], where="diff_summary.paths_touched")
    owned = decision["owned_paths"]
    surfaces = decision["fable_owned_surfaces"]
    declared_results = [
        validate_declared_result(unit["verification_result"], where=f"build_units[{index}].verification_result")
        for index, unit in enumerate(data["build_units"])
    ]
    checks = [
        (
            "hold_present",
            data["status"] == "HOLD" or bool(data["holds"]),
            "status is HOLD or a HOLD entry exists",
        ),
        (
            "owned_path_or_material_deviation",
            any(not path_is_owned(path, owned) for path in paths)
            or any(item["material"] for item in data["deviations"]),
            "a changed path is outside owned_paths or a material deviation is recorded",
        ),
        (
            "fable_owned_surface_touched",
            any(path_matches_surface(path, surface) for path in paths for surface in surfaces),
            "a changed path matches a Fable-owned surface selector",
        ),
        (
            "verification_unclean",
            any(
                unit["state"] != "COMPLETE" or not passed or exit_code != 0
                for unit, (passed, exit_code) in zip(data["build_units"], declared_results)
            ),
            "a build unit is incomplete or its declared verification is not clean",
        ),
    ]
    rules = [
        {"rule": rule, "triggered": triggered, "evidence": evidence}
        for rule, triggered, evidence in checks
    ]
    reasons = [evidence for _rule, triggered, evidence in checks if triggered]
    required = bool(reasons)
    if not reasons:
        reasons = ["No deterministic review rule triggered; a generated skip notice is required."]
    return required, reasons, rules


def git_changed_paths(repo: Path) -> list[str]:
    require(repo.is_dir(), f"repo does not exist: {repo}")
    require((repo / ".git").exists(), f"repo is not a git checkout or approved git snapshot: {repo}")
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
            env=sanitized_subprocess_env(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PacketError(f"git porcelain could not execute: {exc}") from exc
    require(proc.returncode == 0, f"git porcelain failed: {proc.stderr.strip() or proc.stdout.strip()}")
    chunks = proc.stdout.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(chunks):
        entry = chunks[index]
        index += 1
        if not entry:
            continue
        require(len(entry) >= 4, f"unexpected git porcelain entry: {entry!r}")
        status = entry[:2]
        paths.append(entry[3:])
        if "R" in status or "C" in status:
            require(index < len(chunks) and bool(chunks[index]), "git rename/copy entry is incomplete")
            paths.append(chunks[index])
            index += 1
    return sorted({path.replace("\\", "/") for path in paths})


def validate_repo_diff(data: dict[str, Any], decision: dict[str, Any], repo: Path) -> None:
    actual = git_changed_paths(repo)
    declared = sorted(normalize_path_list(data["diff_summary"]["paths_touched"], where="diff_summary.paths_touched"))
    require(actual == declared, f"diff_summary.paths_touched does not match git porcelain; declared={declared}, actual={actual}")
    outside = [path for path in actual if not path_is_owned(path, decision["owned_paths"])]
    require(not outside, f"git porcelain contains changes outside owned_paths: {', '.join(outside)}")


def execute_ready_verification(data: dict[str, Any], *, repo: Path, timeout_s: int) -> None:
    if data["status"] != "READY":
        return
    for index, unit in enumerate(data["build_units"]):
        passed, exit_code = validate_declared_result(
            unit["verification_result"],
            where=f"build_units[{index}].verification_result",
        )
        require(
            unit["state"] == "COMPLETE" and passed and exit_code == 0,
            "READY requires every build unit to be COMPLETE with clean declared verification",
        )
        proc = run_verification(unit["verification_command"], cwd=repo, timeout_s=timeout_s)
        if proc.returncode != 0:
            detail = (proc.stderr.strip() or proc.stdout.strip() or "no process output")[-1200:]
            raise PacketError(f"verification re-execution failed for {unit['id']} with exit {proc.returncode}: {detail}")


def build_skip_notice(status_path: Path, rules: list[dict[str, Any]], reasons: list[str]) -> dict[str, Any]:
    return {
        "generated_by": "validate_sol_status.py",
        "review_required": False,
        "status": "READY",
        "status_packet": status_path.name,
        "gate_rules": rules,
        "skip_reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = WhyArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--skip-notice", type=Path, default=Path("skip-notice.json"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        require(1 <= args.timeout <= 1800, "--timeout must be between 1 and 1800 seconds")
        data = load_json_object(args.packet)
        decision = load_json_object(args.decision)
        validate_status_packet(data, decision)
        review_required, reasons, rules = compute_review_gate(data, decision)
        validate_repo_diff(data, decision, args.repo.resolve())
        execute_ready_verification(data, repo=args.repo.resolve(), timeout_s=args.timeout)
        data["review_required"] = review_required
        data["review_reasons"] = reasons
        write_json(args.packet, data)

        skip_path = args.skip_notice
        if not skip_path.is_absolute():
            skip_path = args.packet.parent / skip_path
        skip_path = skip_path.resolve()
        require(args.packet.parent.resolve() == skip_path.parent, "skip notice must stay beside the status packet")
        if review_required:
            if skip_path.exists():
                skip_path.unlink()
        else:
            write_json(skip_path, build_skip_notice(args.packet, rules, reasons))
    except (PacketError, OSError) as exc:
        print_why(exc)
        return 1
    shape = "HOLD" if data["status"] == "HOLD" else "READY"
    print(f"PASS: valid Sol {shape}; review_required={str(review_required).lower()}; objective gate recorded")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover - fail closed on unexpected runtime errors
        print_why(exc)
        sys.exit(1)
