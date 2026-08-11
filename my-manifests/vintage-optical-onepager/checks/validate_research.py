#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    "# Vintage Optical One-Pager Research",
    "## The Read",
    "## Verified Inputs",
    "## Score Rationale",
    "## Competitor Tiers",
    "## Opportunity Lanes",
    "## Three Actions",
    "## Disconfirmers",
    "## Missing Data",
    "## Decision Residue",
]
REQUIRED_TOP = [
    "schema_version", "analysis_product", "data_mode", "report_visibility",
    "practice", "market", "scores", "subscores", "competitor_tiers",
    "specialty_options", "drivers", "white_space", "recommended_actions",
    "data_quality", "disconfirmers", "hidden_appendices",
]
REQUIRED_SCORES = [
    "market_demand_supply_score", "competitive_pressure_index",
    "room_to_win_score", "practice_competitiveness_score",
    "client_opportunity_score", "confidence_grade",
]
EID_RE = re.compile(r"\bE\d{3}\b")
URL_RE = re.compile(r"https?://[^\s)>\"\]]+")


def why(msg: str) -> None:
    print(f"WHY: {msg}")


def walk_strings(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from walk_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk_strings(v)
    elif isinstance(value, str):
        yield value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--scores", required=True)
    ap.add_argument("--ledger", required=True)
    args = ap.parse_args()

    failures: list[str] = []
    rp, sp, lp = map(Path, [args.report, args.scores, args.ledger])
    for p in [rp, sp, lp]:
        if not p.is_file():
            failures.append(f"missing required file: {p}")
    if failures:
        for f in failures: why(f)
        return 1

    report = rp.read_text(encoding="utf-8", errors="replace")
    for section in REQUIRED_SECTIONS:
        if section.lower() not in report.lower():
            failures.append(f"research report missing section: {section}")
    words = len(re.findall(r"\b[\w'-]+\b", report))
    if not 600 <= words <= 2600:
        failures.append(f"research report word count {words} is outside 600..2600")
    if "$" in report or re.search(r"\b\d+[kKmM]\s*/?\s*(?:yr|year)", report):
        failures.append("research report contains a public-data dollar forecast")

    try:
        data = json.loads(sp.read_text(encoding="utf-8"))
    except Exception as e:
        failures.append(f"scores JSON does not parse: {e}")
        data = {}

    for key in REQUIRED_TOP:
        if key not in data:
            failures.append(f"missing top-level scores key: {key}")
    if data.get("schema_version") != "2.0":
        failures.append("schema_version must be 2.0")
    if data.get("analysis_product") != "single_practice":
        failures.append("analysis_product must be single_practice")
    if data.get("data_mode") != "public_only":
        failures.append("data_mode must be public_only")

    scores = data.get("scores", {}) if isinstance(data.get("scores"), dict) else {}
    for key in REQUIRED_SCORES:
        if key not in scores:
            failures.append(f"missing score: {key}")
    for key in REQUIRED_SCORES[:-1]:
        val = scores.get(key)
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not 0 <= val <= 100:
            failures.append(f"score {key} must be numeric in 0..100, got {val!r}")
    cpi, rtw = scores.get("competitive_pressure_index"), scores.get("room_to_win_score")
    if isinstance(cpi, (int, float)) and isinstance(rtw, (int, float)) and abs(rtw - (100 - cpi)) > 0.001:
        failures.append(f"Room to Win {rtw} must equal 100 - CPI {cpi}")
    if scores.get("confidence_grade") not in {"C", "D"}:
        failures.append("public-only confidence_grade must be C or D")

    actions = data.get("recommended_actions")
    if not isinstance(actions, list) or not 1 <= len(actions) <= 3:
        failures.append("recommended_actions must contain 1..3 items")
    missing = data.get("data_quality", {}).get("missing_to_upgrade") if isinstance(data.get("data_quality"), dict) else None
    if not isinstance(missing, list) or len(missing) < 3:
        failures.append("data_quality.missing_to_upgrade must list at least 3 gaps")
    tier3 = data.get("hidden_appendices", {}).get("tier_3_reference_comps", {}) if isinstance(data.get("hidden_appendices"), dict) else {}
    if isinstance(tier3, dict) and tier3.get("included") is not False:
        failures.append("Tier 3 must be hidden in the client output")

    with lp.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ledger_ids = {r.get("claim_id", "") for r in rows}
    ledger_urls = {r.get("url", "").rstrip(".,;:") for r in rows if r.get("url")}
    strings = list(walk_strings(data)) + [report]
    cited_ids = set(EID_RE.findall("\n".join(strings)))
    unknown_ids = sorted(cited_ids - ledger_ids)
    if unknown_ids:
        failures.append("unknown evidence IDs: " + ", ".join(unknown_ids))
    urls = {u.rstrip(".,;:") for u in URL_RE.findall("\n".join(strings))}
    disallowed = sorted(urls - ledger_urls)
    if disallowed:
        failures.append("URLs outside the evidence ledger: " + ", ".join(disallowed[:10]))
    if len(cited_ids) < 10:
        failures.append(f"only {len(cited_ids)} unique evidence IDs cited; need at least 10")

    text = "\n".join(strings).lower()
    banned = ["patient-level", "actual payer mix is", "confirmed leakage", "guaranteed", "owner dependence exists"]
    for phrase in banned:
        if phrase in text:
            failures.append(f"banned unsupported phrase present: {phrase}")

    if failures:
        for f in failures: why(f)
        return 1
    print(f"PASS: research package valid; {words} words, {len(cited_ids)} evidence IDs, Room to Win reconciles, confidence {scores.get('confidence_grade')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
