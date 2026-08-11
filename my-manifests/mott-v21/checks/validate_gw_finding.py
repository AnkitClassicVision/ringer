#!/usr/bin/env python3
"""Validate one gateway-diagnosis lane report.

A diagnosis that cannot quote the real code, cannot say what would disprove it,
and cannot say whether its fix touches the other client is not a diagnosis.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "gw-patient-search-diagnosis.v1"
CONFIDENCE = {"high", "medium", "low"}
MIN_QUOTE_CHARS = 25
MIN_GROUNDED = 3


def fail(reasons: list[str]) -> None:
    print("GATEWAY DIAGNOSIS CHECK FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    sys.exit(1)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def load_corpus(sources: Path) -> str:
    if not sources.is_dir():
        fail([f"sources directory missing: {sources}"])
    blobs = [p.read_text(encoding="utf-8", errors="replace")
             for p in sorted(sources.rglob("*")) if p.is_file()]
    if not blobs:
        fail([f"sources directory is empty: {sources}"])
    return normalize("\n".join(blobs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--require-executed", action="store_true",
                        help="lane must have actually run code, not just read it")
    args = parser.parse_args()

    if not args.report.is_file():
        fail([f"report not found: {args.report}"])
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"report is not valid JSON: {exc}"])
    if not isinstance(report, dict):
        fail(["report must be a JSON object"])

    reasons: list[str] = []
    corpus = load_corpus(args.sources)

    if report.get("schema_version") != SCHEMA_VERSION:
        reasons.append(f"schema_version must be exactly {SCHEMA_VERSION!r}")
    if not as_text(report.get("lane")).strip():
        reasons.append("lane must name which diagnosis lane produced this report")

    root = report.get("root_cause")
    if not isinstance(root, dict):
        reasons.append("root_cause must be an object {statement, mechanism, confidence}")
        root = {}
    if len(as_text(root.get("statement")).strip()) < 60:
        reasons.append("root_cause.statement must be at least 60 characters and say what is actually wrong")
    if len(as_text(root.get("mechanism")).strip()) < 60:
        reasons.append(
            "root_cause.mechanism must be at least 60 characters tracing HOW the request "
            "becomes an empty result"
        )
    if as_text(root.get("confidence")).strip().lower() not in CONFIDENCE:
        reasons.append(f"root_cause.confidence must be one of {sorted(CONFIDENCE)}")

    evidence = report.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        reasons.append("evidence must be a non-empty list of {quote, file, why}")
        evidence = []
    spans: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            reasons.append(f"evidence entry is not an object: {item!r}")
            continue
        quote = as_text(item.get("quote"))
        if len(quote.strip()) < MIN_QUOTE_CHARS:
            reasons.append(f"evidence quote is shorter than {MIN_QUOTE_CHARS} chars: {quote[:40]!r}")
            continue
        spans.append(quote)
        if not as_text(item.get("file")).strip():
            reasons.append(f"evidence quote {quote[:35]!r} does not name its file")
        if len(as_text(item.get("why")).strip()) < 30:
            reasons.append(f"evidence quote {quote[:35]!r} needs at least 30 characters of why")

    grounded = [s for s in spans if normalize(s) in corpus]
    if len(grounded) < MIN_GROUNDED:
        reasons.append(
            f"only {len(grounded)} of {len(spans)} quotes appear verbatim in the staged sources; "
            f"need at least {MIN_GROUNDED}. Copy the real code, do not paraphrase it."
        )
        for span in spans:
            if normalize(span) not in corpus:
                print(f"    ungrounded quote: {span[:80]!r}")

    if len(as_text(report.get("disproof")).strip()) < 40:
        reasons.append(
            "disproof must be at least 40 characters naming a concrete observation that would "
            "refute this root cause. An unfalsifiable diagnosis is not usable."
        )
    if len(as_text(report.get("shared_impact")).strip()) < 40:
        reasons.append(
            "shared_impact must be at least 40 characters stating whether the implied fix changes "
            "behavior for callers other than the id-pinned recall path. This container serves a "
            "second live client."
        )

    if args.require_executed:
        executed = report.get("executed")
        if not isinstance(executed, list) or not executed:
            reasons.append(
                "this lane must actually RUN code: executed must be a non-empty list of "
                "{command, output} showing real output, not a description of what would happen"
            )
        else:
            for run in executed:
                if not isinstance(run, dict):
                    reasons.append(f"executed entry is not an object: {run!r}")
                    continue
                if not as_text(run.get("command")).strip():
                    reasons.append("an executed entry has no command")
                if len(as_text(run.get("output")).strip()) < 10:
                    reasons.append(
                        f"executed command {as_text(run.get('command'))[:50]!r} shows no real output"
                    )

    if reasons:
        fail(reasons)

    print("GATEWAY DIAGNOSIS CHECK PASSED")
    print(f"  lane: {as_text(report.get('lane'))}")
    print(f"  confidence: {as_text(root.get('confidence'))}")
    print(f"  grounded quotes: {len(grounded)}/{len(spans)}")
    if args.require_executed:
        print(f"  executed commands: {len(report.get('executed') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
