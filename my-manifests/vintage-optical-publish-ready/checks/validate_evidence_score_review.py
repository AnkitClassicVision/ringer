#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

CURRENT_SCORES = {
    "Market Demand-Supply": 57,
    "Competitive Pressure Index": 57,
    "Room to Win": 43,
    "Practice Competitiveness": 58,
    "Client Opportunity": 54,
    "Digital Presence": 57,
    "Dry eye / ocular surface": 52,
    "Myopia management": 52,
    "Specialty contact lenses": 51,
}
REQUIRED_FACTS = {
    "FACT_CATCHMENT_05",
    "FACT_CATCHMENT_10",
    "FACT_CATCHMENT_15",
    "FACT_CATCHMENT_20",
    "FACT_CATCHMENT_30",
    "FACT_MORTON_POP_GROWTH",
    "FACT_SCHOOL_ENROLLMENT_GROWTH",
    "FACT_FOCUS_ROUTE_CORRECTED",
    "FACT_GOOGLE_REVIEW_SAMPLE",
    "FACT_BIRDEYE_COUNT_DISCREPANCY",
}
REQUIRED_BLOCKERS = {
    "canonical_full_vdu",
    "canonical_office_count",
    "rank_grid",
    "complete_provider_entity_dedupe",
}


def why(message: str) -> None:
    print(f"WHY: {message}")


def close(a: float, b: float, tol: float = 0.02) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=tol)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()
    failures: list[str] = []
    required = ("evidence-score-review.json", "evidence-score-review.md", "report-update-contract.json")
    for name in required:
        p = args.dir / name
        if not p.is_file() or p.stat().st_size == 0:
            failures.append(f"missing or empty file: {name}")
    if failures:
        for item in failures:
            why(item)
        return 1

    try:
        review = json.loads((args.dir / "evidence-score-review.json").read_text())
        contract = json.loads((args.dir / "report-update-contract.json").read_text())
    except Exception as exc:
        why(f"JSON parse failed: {exc}")
        return 1

    if review.get("verdict") != "PASS":
        failures.append("evidence review verdict must be PASS")
    if review.get("highest_truthful_state") != "EVIDENCE_REVIEWED_REPORT_REBUILD_REQUIRED":
        failures.append("highest truthful state is overstated or missing")
    if review.get("external_actions_taken") != "none":
        failures.append("review must record no external actions")

    packet_checks = review.get("packet_checks") or {}
    for key in ("catchment_growth", "supply_visibility_candidates", "reconciled_supply_routing"):
        if packet_checks.get(key) != "PASS":
            failures.append(f"packet check not PASS: {key}")

    facts = {row.get("fact_id"): row for row in review.get("promotable_facts") or []}
    missing_facts = REQUIRED_FACTS - set(facts)
    if missing_facts:
        failures.append(f"missing promotable facts: {sorted(missing_facts)}")
    expected_windows = {
        "FACT_CATCHMENT_05": (5, 6624, 2722),
        "FACT_CATCHMENT_10": (10, 19322, 7873),
        "FACT_CATCHMENT_15": (15, 54768, 23793),
        "FACT_CATCHMENT_20": (20, 173058, 75244),
        "FACT_CATCHMENT_30": (30, 283661, 120940),
    }
    for fact_id, (minutes, population, households) in expected_windows.items():
        row = facts.get(fact_id) or {}
        value = row.get("value") or {}
        if value.get("minutes") != minutes or value.get("population") != population or value.get("households") != households:
            failures.append(f"{fact_id} has incorrect accepted values")
        if not row.get("source_ids") or not row.get("limitations"):
            failures.append(f"{fact_id} lacks sources or limitations")
    route = (facts.get("FACT_FOCUS_ROUTE_CORRECTED") or {}).get("value") or {}
    if route.get("minutes") != 3.89 or route.get("miles") != 1.53:
        failures.append("corrected Focus route must be 3.89 minutes and 1.53 miles")

    prohibited = {row.get("field"): row for row in review.get("not_promotable") or []}
    for field in REQUIRED_BLOCKERS:
        row = prohibited.get(field)
        if not row or row.get("canonical_value") is not None:
            failures.append(f"{field} must remain non-promotable and null")

    scoring = review.get("scoring_decisions") or []
    decisions = {row.get("score_name"): row for row in scoring}
    if set(decisions) != set(CURRENT_SCORES):
        failures.append("scoring decisions must cover exactly all nine report scores")
    for name, current in CURRENT_SCORES.items():
        row = decisions.get(name) or {}
        if row.get("current_score") != current:
            failures.append(f"{name} current score must remain {current}")
        recommended = row.get("recommended_score")
        if not isinstance(recommended, int) or not 0 <= recommended <= 100:
            failures.append(f"{name} recommended score is invalid")
            continue
        if row.get("changed") is not (recommended != current):
            failures.append(f"{name} changed flag is inconsistent")
        if not row.get("decision_rationale") or not row.get("source_ids"):
            failures.append(f"{name} lacks rationale or source IDs")
        components = row.get("components") or []
        if components:
            total = 0.0
            weight_total = 0.0
            for component in components:
                try:
                    band = float(component["value"])
                    weight = float(component["weight"])
                    contribution = float(component["contribution"])
                except Exception as exc:
                    failures.append(f"{name} component schema invalid: {exc}")
                    continue
                if not close(contribution, band * weight, 0.011):
                    failures.append(f"{name} contribution does not recompute: {component.get('component')}")
                total += contribution
                weight_total += weight
            if not close(weight_total, 1.0, 0.001):
                failures.append(f"{name} component weights do not total 1")
            if not close(total, float(row.get("full_precision_total", math.nan)), 0.011):
                failures.append(f"{name} full precision total does not recompute")
    cpi = decisions.get("Competitive Pressure Index", {}).get("recommended_score")
    room = decisions.get("Room to Win", {}).get("recommended_score")
    if isinstance(cpi, int) and room != 100 - cpi:
        failures.append("Room to Win must equal 100 minus Competitive Pressure Index")
    if review.get("directionality_guard") != "Room to Win = 100 - Competitive Pressure Index":
        failures.append("exact Room to Win directionality guard is missing")

    superseded = {row.get("claim_id") for row in review.get("superseded_claims") or []}
    for required_id in ("OLD_ROUTE_FOCUS_4_07", "OLD_NO_CATCHMENT_DEMOGRAPHICS", "OLD_NO_GROWTH_EVIDENCE"):
        if required_id not in superseded:
            failures.append(f"missing superseded claim: {required_id}")

    if contract.get("status") != "APPROVED_FOR_INTERNAL_REBUILD_ONLY":
        failures.append("report update contract has the wrong status")
    if contract.get("external_delivery_authorized") is not False:
        failures.append("report update contract must not authorize delivery")
    required_outputs = set(contract.get("required_outputs") or [])
    for name in ("onepager.html", "onepager.pdf", "number-explainer.md", "number-explainer.html", "number-explainer.pdf"):
        if name not in required_outputs:
            failures.append(f"report update contract lacks required output: {name}")
    update_ids = {row.get("update_id") for row in contract.get("required_updates") or []}
    for required_id in (
        "UPDATE_CATCHMENT_TABLE",
        "UPDATE_GROWTH_EVIDENCE",
        "UPDATE_ROUTE_LINEAGE",
        "UPDATE_REVIEW_EVIDENCE",
        "UPDATE_SCORE_RECOMPUTATION",
        "UPDATE_WHAT_WE_DO_NOT_KNOW",
        "UPDATE_SOURCE_DICTIONARY",
        "UPDATE_RECEIPT_MANIFEST",
    ):
        if required_id not in update_ids:
            failures.append(f"report update contract lacks {required_id}")
    for phrase in (
        "100% substantive-number lineage",
        "zero unexplained substantive numbers",
        "Room to Win = 100 - Competitive Pressure Index",
        "human Project Room approval",
    ):
        if phrase not in json.dumps(contract):
            failures.append(f"report update contract lacks release requirement: {phrase}")

    for name in ("evidence-score-review.md",):
        text = (args.dir / name).read_text()
        if "—" in text:
            failures.append(f"{name} contains an em dash")
        if "CANARY" in text:
            failures.append(f"{name} contains a canary")

    if failures:
        for item in failures:
            why(item)
        return 1
    print(
        "PASS: source packets, promotable facts, null gates, nine score decisions, "
        "Room-to-Win directionality, superseded claims, and the internal-only report "
        "rebuild contract all verify"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
