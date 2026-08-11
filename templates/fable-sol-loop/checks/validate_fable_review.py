#!/usr/bin/env python3
"""Validate round-3 Fable APPROVE, REVISE, or controlled ESCALATE output."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from lib_packets import (
    PacketError,
    WhyArgumentParser,
    load_json_object,
    normalize_relative_path,
    print_why,
    reject_extra_keys,
    require,
    require_keys,
    require_string,
    validate_decision_packet,
    validate_question,
    validate_safe_required_change,
)
from validate_sol_status import compute_review_gate


def validate_evidence(value: Any, *, where: str, evidence_root: Path) -> None:
    require(isinstance(value, dict), f"{where} must be an object")
    require_keys(value, ("source", "detail"), where=where)
    reject_extra_keys(value, ("source", "detail"), where=where)
    source = normalize_relative_path(value["source"], where=f"{where}.source")
    require(
        source in {"status.json", "notes.md"} or source.startswith("changed/"),
        f"{where}.source must cite status.json, notes.md, or a staged changed/ artifact",
    )
    require_string(value["detail"], where=f"{where}.detail", min_length=8)
    evidence_path = (evidence_root / source).resolve()
    try:
        evidence_path.relative_to(evidence_root.resolve())
    except ValueError as exc:
        raise PacketError(f"{where}.source escapes the staged evidence root") from exc
    require(evidence_path.is_file() and evidence_path.stat().st_size > 0, f"{where}.source is not a non-empty staged artifact: {source}")


def status_hold_unknowns(status: dict[str, Any]) -> set[str]:
    holds = status.get("holds")
    require(isinstance(holds, list), "staged status packet holds must be a list")
    result: set[str] = set()
    for index, hold in enumerate(holds):
        require(isinstance(hold, dict), f"staged status holds[{index}] must be an object")
        result.add(require_string(hold.get("unknown"), where=f"staged status holds[{index}].unknown"))
    return result


def validate_review_packet(
    data: dict[str, Any],
    status: dict[str, Any],
    decision: dict[str, Any],
    *,
    evidence_root: Path,
) -> dict[str, Any]:
    required = ("verdict", "findings", "holds_resolved")
    allowed = required + ("question",)
    require(evidence_root.is_dir(), f"staged evidence root does not exist: {evidence_root}")
    validate_decision_packet(decision)
    require_keys(data, required, where="Fable review packet")
    reject_extra_keys(data, allowed, where="Fable review packet")
    require(status.get("review_required") is True, "Fable review requires staged status.review_required=true from the deterministic gate")
    require(isinstance(status.get("review_reasons"), list) and bool(status["review_reasons"]), "staged status must carry the deterministic review reasons")
    computed_required, computed_reasons, _rules = compute_review_gate(status, decision)
    require(computed_required is True, "staged status does not trigger any deterministic review rule")
    require(status["review_reasons"] == computed_reasons, "staged status.review_reasons differ from deterministic recomputation")
    verdict = data["verdict"]
    require(verdict in {"APPROVE", "REVISE", "ESCALATE"}, "verdict must be APPROVE, REVISE, or ESCALATE")

    findings = data["findings"]
    require(isinstance(findings, list), "findings must be a list")
    finding_ids: list[str] = []
    for index, finding in enumerate(findings):
        where = f"findings[{index}]"
        require(isinstance(finding, dict), f"{where} must be an object")
        fields = ("id", "severity", "evidence", "required_change", "owner")
        require_keys(finding, fields, where=where)
        reject_extra_keys(finding, fields, where=where)
        finding_ids.append(require_string(finding["id"], where=f"{where}.id"))
        require(finding["severity"] in {"BLOCKER", "MAJOR", "MINOR"}, f"{where}.severity is not recognized")
        validate_evidence(finding["evidence"], where=f"{where}.evidence", evidence_root=evidence_root)
        validate_safe_required_change(finding["required_change"], where=f"{where}.required_change")
        require(finding["owner"] in {"sol", "fable"}, f"{where}.owner must be sol or fable")
    require(len(finding_ids) == len(set(finding_ids)), "finding ids must be unique")

    resolved = data["holds_resolved"]
    require(isinstance(resolved, list), "holds_resolved must be a list")
    resolved_unknowns: list[str] = []
    for index, item in enumerate(resolved):
        where = f"holds_resolved[{index}]"
        require(isinstance(item, dict), f"{where} must be an object")
        fields = ("unknown", "resolution", "evidence")
        require_keys(item, fields, where=where)
        reject_extra_keys(item, fields, where=where)
        resolved_unknowns.append(require_string(item["unknown"], where=f"{where}.unknown"))
        require_string(item["resolution"], where=f"{where}.resolution", min_length=8)
        require_string(item["evidence"], where=f"{where}.evidence", min_length=5)
    require(len(resolved_unknowns) == len(set(resolved_unknowns)), "holds_resolved unknowns must be unique")
    staged_holds = status_hold_unknowns(status)
    require(set(resolved_unknowns).issubset(staged_holds), "holds_resolved references an unknown not present in staged status")

    if verdict == "APPROVE":
        require(not findings, "APPROVE cannot carry pending findings")
        require("question" not in data, "APPROVE cannot carry a QUESTION")
        require(set(resolved_unknowns) == staged_holds, "APPROVE must address every staged HOLD")
    elif verdict == "REVISE":
        require(bool(findings), "REVISE requires at least one evidence-cited finding")
        require("question" not in data, "REVISE cannot carry a QUESTION")
    else:
        require(not findings, "ESCALATE must contain only the single QUESTION, not pending findings")
        require("question" in data, "ESCALATE requires exactly one QUESTION packet")
        require(not staged_holds or set(resolved_unknowns) == staged_holds, "ESCALATE cannot leave unrelated HOLDs pending")
        validate_question(data["question"], where="question")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = WhyArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = load_json_object(args.packet)
        status = load_json_object(args.status)
        decision = load_json_object(args.decision)
        validate_review_packet(data, status, decision, evidence_root=args.evidence_root.resolve())
    except (PacketError, OSError) as exc:
        print_why(exc)
        return 1
    shape = "QUESTION" if data["verdict"] == "ESCALATE" else data["verdict"]
    print(f"PASS: valid Fable review packet ({shape}) with staged evidence checks")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover
        print_why(exc)
        sys.exit(1)
