#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_CHECKS = (
    "contract_traceability",
    "source_hierarchy",
    "dataforseo_preflight",
    "fallbacks",
    "discovery_evidence_separation",
    "local_seo_context",
    "review_handling",
    "catchment_completeness",
    "supply_census",
    "vdu_gate",
    "gap_register",
    "number_explainer",
    "release_qa",
    "ringer_lanes",
    "human_boundary",
    "formula_preservation",
    "one_file_scope",
    "style",
)


def why(message: str) -> None:
    print(f"WHY: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()

    review_json = args.dir / "review.json"
    review_md = args.dir / "review.md"
    failures: list[str] = []
    if not review_json.is_file() or not review_md.is_file():
        why("review.json or review.md missing")
        return 1
    try:
        data = json.loads(review_json.read_text(encoding="utf-8"))
    except Exception as exc:
        why(f"invalid review.json: {exc}")
        return 1

    if data.get("verdict") != "PASS":
        failures.append(f"verdict={data.get('verdict')}")
    if data.get("readiness") != "REVIEWED_PATCH_READY_TO_APPLY":
        failures.append(f"readiness={data.get('readiness')}")
    if data.get("changed_files") != ["RUNBOOK_COMPETITIVE_ANALYSIS.md"]:
        failures.append(f"changed_files={data.get('changed_files')}")
    if data.get("scoring_formulas_changed") is not False:
        failures.append("scoring_formulas_changed must be false")
    if data.get("external_action_authority_changed") is not False:
        failures.append("external_action_authority_changed must be false")
    for field in ("fatal_issues", "material_issues", "minor_issues"):
        if data.get(field) != []:
            failures.append(f"{field} not empty: {data.get(field)}")
    checks = data.get("checks") or {}
    for check in REQUIRED_CHECKS:
        if checks.get(check) not in ("PASS", True):
            failures.append(f"check {check}={checks.get(check)}")

    text = review_md.read_text(encoding="utf-8")
    for phrase in (
        "Verdict: PASS",
        "Readiness: REVIEWED_PATCH_READY_TO_APPLY",
        "Changed file: RUNBOOK_COMPETITIVE_ANALYSIS.md",
        "Scoring formulas changed: no",
        "External-action authority changed: no",
        "No fatal, material, or minor issues",
        "Patch may be applied for human review",
    ):
        if phrase.lower() not in text.lower():
            failures.append(f"review.md missing: {phrase}")
    if len(text) < 3000:
        failures.append("review.md is too short for a fresh contract review")
    if "—" in text:
        failures.append("review.md contains an em dash")
    if "CANARY" in text:
        failures.append("review artifact contains a canary")

    if failures:
        for item in failures:
            why(item)
        return 1

    print(
        "PASS: fresh runbook patch review found one scoped file, all operating "
        "contract checks passed, formulas and external authority unchanged, and "
        "no issues"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
