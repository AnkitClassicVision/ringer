#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"WHY: {message}")


def require(text: str, phrase: str, failures: list[str]) -> None:
    if phrase.lower() not in text.lower():
        failures.append(f"missing required language: {phrase}")


def require_pattern(text: str, pattern: str, label: str, failures: list[str]) -> None:
    if not re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
        failures.append(f"missing required rule: {label}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, type=Path)
    args = parser.parse_args()

    if not args.path.is_file():
        fail(f"runbook missing: {args.path}")
        return 1

    text = args.path.read_text(encoding="utf-8")
    failures: list[str] = []
    line_count = len(text.splitlines())
    if line_count < 170:
        failures.append(f"runbook is too short for the required operating contract: {line_count} lines")
    if "—" in text:
        failures.append("em dash present")

    for heading in (
        "## Record of engagement",
        "## Steps",
        "## Source hierarchy and fallback ladder",
        "## Gap register and null handling",
        "## QA gates",
        "## Automation path",
    ):
        require(text, heading, failures)

    for artifact in (
        "source_inventory.json",
        "missing_evidence.json",
        "data/source_receipts/",
        "scores.json",
        "onepager.html",
        "onepager.pdf",
        "number-explainer.md",
        "number-explainer.html",
        "number-explainer.pdf",
        "runlog.md",
    ):
        require(text, artifact, failures)

    for tool in (
        "DataForSEO",
        "Google Search/Maps",
        "Exa",
        "Perplexity",
        "NPPES",
        "Census",
        "ACS",
        "TIGER",
        "CDC PLACES",
        "OSRM",
        "Valhalla",
    ):
        require(text, tool, failures)

    for exact_rule in (
        "Discovery output is not publication evidence.",
        "NPPES records are not office counts.",
        "A dated SERP sample is not a rank grid.",
        "Full VDU is not calculated unless every required term is sourced.",
        "Room to Win = 100 - Competitive Pressure Index",
        "Unknown is not zero and is not proof of average performance.",
        "External use requires human Project Room approval.",
    ):
        require(text, exact_rule, failures)

    for phrase in (
        "DataForSEO preflight",
        "direct source URL",
        "official API",
        "frozen receipt",
        "query parameters",
        "source vintage",
        "access time",
        "authentication",
        "fallback",
        "platform-specific",
        "cross-platform",
        "geocode",
        "deduplicate",
        "block-group",
        "partial diagnostic",
        "source dictionary",
        "receipt manifest",
        "disconfirmers",
        "repeated values",
        "100%",
        "fresh-context",
    ):
        require(text, phrase, failures)

    require_pattern(
        text,
        r"5\s*,\s*10\s*,\s*15\s*,\s*20\s*,\s*and\s*30[- ]minute",
        "all five fixed benchmark windows",
        failures,
    )
    require_pattern(
        text,
        r"DataForSEO.{0,600}(not configured|authentication|credential|unavailable).{0,900}(Google|Exa|Perplexity|direct)",
        "DataForSEO failure path with named fallback",
        failures,
    )
    require_pattern(
        text,
        r"(Exa|Perplexity).{0,500}(discover|discovery|cross-check).{0,900}(direct source URL|official API|frozen receipt)",
        "search and AI tools separated from final evidence",
        failures,
    )
    require_pattern(
        text,
        r"rank grid.{0,700}(coordinates|latitude|longitude|geography|location).{0,500}(query|keyword).{0,500}(time|timestamp|access)",
        "rank-grid observation context",
        failures,
    )
    require_pattern(
        text,
        r"review.{0,700}(platform-specific).{0,700}(count|volume).{0,700}(recency|response)",
        "review platform, count, recency, and response handling",
        failures,
    )
    require_pattern(
        text,
        r"isochrone.{0,700}(GeoJSON|polygon).{0,900}(ACS|block-group)",
        "saved isochrone geometry and ACS block-group intersection",
        failures,
    )
    require_pattern(
        text,
        r"city.{0,500}(not|never|cannot).{0,500}(catchment|drive-time)",
        "city context cannot substitute for catchment values",
        failures,
    )
    require_pattern(
        text,
        r"number[- ]by[- ]number.{0,900}(source).{0,600}(date|vintage).{0,600}(unit).{0,600}(formula|derivation).{0,600}(direction)",
        "number explainer minimum lineage fields",
        failures,
    )
    require_pattern(
        text,
        r"Ringer.{0,1200}(fetch).{0,600}(transform|dedupe).{0,800}(source audit|audit).{0,800}(score).{0,800}(explainer).{0,800}(render).{0,800}(review)",
        "checked Ringer lane sequence",
        failures,
    )
    require_pattern(
        text,
        r"Project Room.{0,600}(human|approval).{0,600}(deliver|external|outward)",
        "human Project Room delivery gate",
        failures,
    )
    if text.lower().count("room to win = 100 - competitive pressure index") < 2:
        failures.append(
            "explicit Room to Win equation must appear in the scoring contract and its recomputation check"
        )

    if failures:
        for item in failures:
            fail(item)
        return 1

    print(
        "PASS: competitive-analysis runbook defines the required source ladder, "
        "fallbacks, completeness rules, mandatory number explainer, checked Ringer "
        "lanes, and human Project Room gate"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
