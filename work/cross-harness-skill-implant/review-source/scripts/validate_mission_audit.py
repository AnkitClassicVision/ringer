#!/usr/bin/env python3
"""Validate a Mission Fit evidence file without third-party dependencies."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any


EVIDENCE_STATUSES = {
    "VERIFIED",
    "USER_REPORTED",
    "INFERRED",
    "INACCESSIBLE",
    "NOT_APPLICABLE",
}
CHECK_VERDICTS = {"READY", "GAP", "BLOCKED", "INACCESSIBLE"}
MISSION_VERDICTS = {"READY", "NEEDS_CHANGE", "BLOCKED", "INACCESSIBLE"}
ACTIONS = {
    "KEEP",
    "CONNECT",
    "NARROW",
    "CORRECT_SOURCE",
    "ADD_REVIEW",
    "MAKE_A_CHECK",
    "ADD_SKILL",
    "PROBATION",
    "RETIRE",
}


class ValidationError(ValueError):
    pass


def require_keys(obj: dict[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - obj.keys())
    if missing:
        raise ValidationError(f"{label} is missing: {', '.join(missing)}")


def require_text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be non-empty text")
    lowered = value.lower()
    if "todo" in lowered or "[replace" in lowered or "placeholder" in lowered:
        raise ValidationError(f"{label} still contains a placeholder")


def validate_text_list(value: Any, label: str, *, allow_empty: bool = True) -> None:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array")
    if not allow_empty and not value:
        raise ValidationError(f"{label} must not be empty")
    for index, item in enumerate(value):
        require_text(item, f"{label}[{index}]")


def validate_check(check: Any, label: str) -> None:
    if not isinstance(check, dict):
        raise ValidationError(f"{label} must be an object")
    require_keys(check, {"summary", "verdict", "evidence_ids"}, label)
    require_text(check["summary"], f"{label}.summary")
    if check["verdict"] not in CHECK_VERDICTS:
        raise ValidationError(f"{label}.verdict is invalid")
    validate_text_list(
        check["evidence_ids"],
        f"{label}.evidence_ids",
        allow_empty=check["verdict"] == "INACCESSIBLE",
    )


def validate_payload(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValidationError("root must be an object")
    require_keys(
        data,
        {
            "schema_version",
            "generated_at",
            "surface",
            "coverage",
            "cleaner_install",
            "missions",
            "recommendations",
            "overall_status",
            "limits",
        },
        "root",
    )
    if data["schema_version"] != "1.0":
        raise ValidationError("schema_version must be 1.0")
    require_text(data["generated_at"], "generated_at")
    try:
        datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError("generated_at must be an ISO 8601 timestamp") from error

    surface = data["surface"]
    if not isinstance(surface, dict):
        raise ValidationError("surface must be an object")
    require_keys(surface, {"name", "model", "evidence_status"}, "surface")
    if surface["name"] not in {"codex", "claude-code", "claude-ai", "other"}:
        raise ValidationError("surface.name is invalid")
    require_text(surface["model"], "surface.model")
    if surface["evidence_status"] not in EVIDENCE_STATUSES:
        raise ValidationError("surface.evidence_status is invalid")

    coverage = data["coverage"]
    if not isinstance(coverage, dict):
        raise ValidationError("coverage must be an object")
    require_keys(coverage, {"target", "sources", "excluded", "inaccessible"}, "coverage")
    require_text(coverage["target"], "coverage.target")
    if not isinstance(coverage["sources"], list):
        raise ValidationError("coverage.sources must be an array")
    validate_text_list(coverage["excluded"], "coverage.excluded")
    validate_text_list(coverage["inaccessible"], "coverage.inaccessible")
    source_ids: set[str] = set()
    for index, source in enumerate(coverage["sources"]):
        label = f"coverage.sources[{index}]"
        if not isinstance(source, dict):
            raise ValidationError(f"{label} must be an object")
        require_keys(source, {"id", "label", "type", "evidence_status"}, label)
        for key in ("id", "label", "type"):
            require_text(source[key], f"{label}.{key}")
        if source["id"] in source_ids:
            raise ValidationError(f"duplicate source id: {source['id']}")
        source_ids.add(source["id"])
        if source["evidence_status"] not in EVIDENCE_STATUSES:
            raise ValidationError(f"{label}.evidence_status is invalid")

    cleaner = data["cleaner_install"]
    if not isinstance(cleaner, dict):
        raise ValidationError("cleaner_install must be an object")
    require_keys(cleaner, {"status", "edition", "evidence_status"}, "cleaner_install")
    if cleaner["status"] not in {"FOUND", "NOT_FOUND", "INACCESSIBLE", "USER_REPORTED"}:
        raise ValidationError("cleaner_install.status is invalid")
    require_text(cleaner["edition"], "cleaner_install.edition")
    if cleaner["evidence_status"] not in EVIDENCE_STATUSES:
        raise ValidationError("cleaner_install.evidence_status is invalid")

    if not isinstance(data["missions"], list):
        raise ValidationError("missions must be an array")
    mission_ids: set[str] = set()
    for index, mission in enumerate(data["missions"]):
        label = f"missions[{index}]"
        if not isinstance(mission, dict):
            raise ValidationError(f"{label} must be an object")
        require_keys(
            mission,
            {
                "mission_id",
                "name",
                "job",
                "run_count",
                "outcome",
                "access",
                "quality",
                "evidence",
                "supervision",
                "run_findings",
                "repeated_patterns",
                "replay_cases",
                "verdict",
            },
            label,
        )
        for key in ("mission_id", "name", "job"):
            require_text(mission[key], f"{label}.{key}")
        if mission["mission_id"] in mission_ids:
            raise ValidationError(f"duplicate mission id: {mission['mission_id']}")
        mission_ids.add(mission["mission_id"])
        if not isinstance(mission["run_count"], int) or mission["run_count"] < 0:
            raise ValidationError(f"{label}.run_count must be a non-negative integer")
        for key in ("outcome", "access", "quality", "evidence", "supervision"):
            validate_check(mission[key], f"{label}.{key}")
        if mission["verdict"] not in MISSION_VERDICTS:
            raise ValidationError(f"{label}.verdict is invalid")
        for key in ("run_findings", "repeated_patterns", "replay_cases"):
            if not isinstance(mission[key], list):
                raise ValidationError(f"{label}.{key} must be an array")
        if mission["run_count"] != len(mission["run_findings"]):
            raise ValidationError(
                f"{label}.run_count must match the number of run_findings"
            )
        if mission["run_count"] > 0 and mission["verdict"] != "INACCESSIBLE":
            replay_count = len(mission["replay_cases"])
            if replay_count < 5 or replay_count > 20:
                raise ValidationError(f"{label}.replay_cases must contain 5 to 20 cases")
        run_ids: set[str] = set()
        for finding_index, finding in enumerate(mission["run_findings"]):
            finding_label = f"{label}.run_findings[{finding_index}]"
            if not isinstance(finding, dict):
                raise ValidationError(f"{finding_label} must be an object")
            require_keys(
                finding,
                {"run_id", "result", "summary", "evidence_ids"},
                finding_label,
            )
            require_text(finding["run_id"], f"{finding_label}.run_id")
            require_text(finding["summary"], f"{finding_label}.summary")
            if finding["run_id"] in run_ids:
                raise ValidationError(f"duplicate run id: {finding['run_id']}")
            run_ids.add(finding["run_id"])
            if finding["result"] not in {"USED", "CHANGED", "DROPPED", "UNKNOWN"}:
                raise ValidationError(f"{finding_label}.result is invalid")
            validate_text_list(
                finding["evidence_ids"],
                f"{finding_label}.evidence_ids",
                allow_empty=False,
            )
        for pattern_index, pattern in enumerate(mission["repeated_patterns"]):
            pattern_label = f"{label}.repeated_patterns[{pattern_index}]"
            if not isinstance(pattern, dict):
                raise ValidationError(f"{pattern_label} must be an object")
            require_keys(pattern, {"pattern", "count", "failure_mode", "evidence_ids"}, pattern_label)
            require_text(pattern["pattern"], f"{pattern_label}.pattern")
            require_text(pattern["failure_mode"], f"{pattern_label}.failure_mode")
            if not isinstance(pattern["count"], int) or pattern["count"] < 3:
                raise ValidationError(
                    f"{pattern_label}.count must be at least 3; keep single cases in run_findings"
                )
            validate_text_list(
                pattern["evidence_ids"],
                f"{pattern_label}.evidence_ids",
                allow_empty=False,
            )
        replay_ids: set[str] = set()
        impossible_case_found = False
        for replay_index, replay in enumerate(mission["replay_cases"]):
            replay_label = f"{label}.replay_cases[{replay_index}]"
            if not isinstance(replay, dict):
                raise ValidationError(f"{replay_label} must be an object")
            require_keys(
                replay,
                {"case_id", "name", "expected_outcome", "pass_criteria"},
                replay_label,
            )
            for key in ("case_id", "name", "expected_outcome"):
                require_text(replay[key], f"{replay_label}.{key}")
            if replay["case_id"] in replay_ids:
                raise ValidationError(f"duplicate replay case id: {replay['case_id']}")
            replay_ids.add(replay["case_id"])
            validate_text_list(
                replay["pass_criteria"],
                f"{replay_label}.pass_criteria",
                allow_empty=False,
            )
            if "BLOCKED" in replay["expected_outcome"].upper():
                impossible_case_found = True
        if mission["replay_cases"] and not impossible_case_found:
            raise ValidationError(
                f"{label}.replay_cases must include an impossible case whose expected_outcome is BLOCKED"
            )

    if not isinstance(data["recommendations"], list):
        raise ValidationError("recommendations must be an array")
    numbers: set[int] = set()
    for index, recommendation in enumerate(data["recommendations"]):
        label = f"recommendations[{index}]"
        if not isinstance(recommendation, dict):
            raise ValidationError(f"{label} must be an object")
        require_keys(
            recommendation,
            {"number", "action", "title", "why", "evidence_ids", "risk", "approver", "rollback", "status"},
            label,
        )
        number = recommendation["number"]
        if not isinstance(number, int) or number < 1 or number in numbers:
            raise ValidationError(f"{label}.number must be a unique positive integer")
        numbers.add(number)
        if recommendation["action"] not in ACTIONS:
            raise ValidationError(f"{label}.action is invalid")
        for key in ("title", "why", "risk", "approver", "rollback"):
            require_text(recommendation[key], f"{label}.{key}")
        validate_text_list(
            recommendation["evidence_ids"],
            f"{label}.evidence_ids",
            allow_empty=False,
        )
        if recommendation["status"] not in {"PROPOSED", "APPROVED", "REJECTED", "APPLIED"}:
            raise ValidationError(f"{label}.status is invalid")

    if data["overall_status"] not in {"REVIEW_REQUIRED", "NEEDS_INPUT", "NO_SAFE_CHANGE"}:
        raise ValidationError("overall_status is invalid")
    if not isinstance(data["limits"], list):
        raise ValidationError("limits must be an array")
    validate_text_list(data["limits"], "limits")
    if not data["missions"] and data["overall_status"] != "NEEDS_INPUT":
        raise ValidationError("an audit without missions must use NEEDS_INPUT")
    if numbers and numbers != set(range(1, len(numbers) + 1)):
        raise ValidationError("recommendation numbers must be contiguous from 1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.audit.read_text(encoding="utf-8"))
        validate_payload(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {args.audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
