#!/usr/bin/env python3
"""Validate the Fable review verdict on the generated Mott v21 build.

A review that cannot point at real text is not a review. Every quoted piece of
evidence is checked against the staged artifacts, so an approving narrative
built on invented detail fails.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "mott-v22-review.v1"
VERDICTS = {"APPROVE", "REVISE"}
SEVERITIES = {"block", "high", "medium", "low"}

REQUIRED_DIMENSIONS = {
    "R1 failure exits": ("failure exit", "fallback", "__never__", "strand", "r1"),
    "R2 one state one node": ("one state", "one node", "duplicate", "offered", "r2"),
    "R3 no model-produced booking values": ("tool", "webhook", "transcrib", "response mapping", "r3"),
    "R4 waiting exits and timeout": ("timeout", "waiting", "global", "r4"),
    "R5 confirmation gating": ("book_success", "confirm", "r5"),
    "R6 message copy": ("start time", "end time", "render", "timezone", "r6"),
    "R7 faq auto-return": ("faq", "auto-return", "autoreturn", "invent", "r7"),
    "R8 no false suppression": ("suppress", "r8"),
}

MIN_QUOTE_CHARS = 20
MIN_GROUNDED = 5
MIN_RATIONALE = 40


def fail(reasons: list[str]) -> None:
    print("REVIEW CHECK FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    sys.exit(1)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _decoded_strings(value: object, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for key, nested in value.items():
            out.append(str(key))
            _decoded_strings(nested, out)
    elif isinstance(value, list):
        for nested in value:
            _decoded_strings(nested, out)


def load_corpus(sources: Path) -> str:
    if not sources.is_dir():
        fail([f"sources directory missing: {sources}"])
    blobs: list[str] = []
    for path in sorted(sources.rglob("*")):
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        blobs.append(raw)
        if path.suffix.lower() == ".json":
            try:
                decoded: list[str] = []
                _decoded_strings(json.loads(raw), decoded)
                blobs.extend(decoded)
            except (json.JSONDecodeError, RecursionError):
                pass
    return normalize("\n".join(blobs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    args = parser.parse_args()

    if not args.review.is_file():
        fail([f"review not found: {args.review}"])
    try:
        review = json.loads(args.review.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"review is not valid JSON: {exc}"])
    if not isinstance(review, dict):
        fail(["review must be a JSON object"])

    reasons: list[str] = []
    corpus = load_corpus(args.sources)

    if review.get("schema_version") != SCHEMA_VERSION:
        reasons.append(
            f"schema_version must be exactly {SCHEMA_VERSION!r}, got {review.get('schema_version')!r}"
        )

    verdict = as_text(review.get("verdict")).strip().upper()
    if verdict not in VERDICTS:
        reasons.append(f"verdict must be APPROVE or REVISE, got {review.get('verdict')!r}")

    # --- dimensions actually examined -------------------------------------
    dimensions = review.get("checked_dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        reasons.append(
            "checked_dimensions must be a non-empty list of objects "
            "{name, what_you_checked, result}"
        )
        dimensions = []
    dim_blob = " ".join(
        f"{as_text(d.get('name'))} {as_text(d.get('what_you_checked'))}"
        for d in dimensions
        if isinstance(d, dict)
    ).lower()
    for label, hints in REQUIRED_DIMENSIONS.items():
        if not any(hint in dim_blob for hint in hints):
            reasons.append(
                f"checked_dimensions never covers {label!r} (expected one of {hints})"
            )
    for entry in dimensions:
        if not isinstance(entry, dict):
            reasons.append(f"checked_dimensions entry is not an object: {entry!r}")
            continue
        if len(as_text(entry.get("what_you_checked")).strip()) < MIN_RATIONALE:
            reasons.append(
                f"dimension {as_text(entry.get('name'))!r} needs at least {MIN_RATIONALE} "
                "characters saying what you actually checked"
            )

    # --- findings -----------------------------------------------------------
    findings = review.get("findings")
    if not isinstance(findings, list):
        reasons.append("findings must be a list (empty is allowed only with an APPROVE verdict)")
        findings = []
    blocking = 0
    for finding in findings:
        if not isinstance(finding, dict):
            reasons.append(f"finding is not an object: {finding!r}")
            continue
        severity = as_text(finding.get("severity")).strip().lower()
        if severity not in SEVERITIES:
            reasons.append(
                f"finding {as_text(finding.get('id'))!r} has severity {finding.get('severity')!r}; "
                f"must be one of {sorted(SEVERITIES)}"
            )
        if severity in {"block", "high"}:
            blocking += 1
        if not as_text(finding.get("locus")).strip():
            reasons.append(
                f"finding {as_text(finding.get('id'))!r} must name a locus: the file, node id, or edge"
            )
        if len(as_text(finding.get("why")).strip()) < MIN_RATIONALE:
            reasons.append(
                f"finding {as_text(finding.get('id'))!r} needs at least {MIN_RATIONALE} "
                "characters explaining why it matters"
            )

    if verdict == "REVISE" and blocking == 0:
        reasons.append(
            "verdict is REVISE but no finding has severity block or high; a revision demand "
            "needs at least one blocking reason"
        )
    if verdict == "APPROVE" and blocking > 0:
        reasons.append(
            f"verdict is APPROVE but {blocking} finding(s) are block or high severity; "
            "approve and blocking findings are contradictory"
        )

    # --- grounding ------------------------------------------------------------
    review_text = json.dumps(review)
    spans: list[str] = []
    for pattern in (r"`([^`\n]{%d,})`" % MIN_QUOTE_CHARS,
                    r"\\\"([^\"\n]{%d,})\\\"" % MIN_QUOTE_CHARS):
        spans.extend(re.findall(pattern, review_text))
    evidence_fields: list[str] = []
    for finding in findings:
        if isinstance(finding, dict):
            evidence_fields.append(as_text(finding.get("evidence")))
    for entry in dimensions:
        if isinstance(entry, dict):
            evidence_fields.append(as_text(entry.get("evidence")))
    for text in evidence_fields:
        spans.extend(re.findall(r"`([^`\n]{%d,})`" % MIN_QUOTE_CHARS, text))
        if len(text.strip()) >= MIN_QUOTE_CHARS:
            spans.append(text.strip())

    grounded = [s for s in spans if normalize(s) in corpus]
    if len(grounded) < MIN_GROUNDED:
        reasons.append(
            f"only {len(grounded)} of {len(spans)} quoted spans appear verbatim in the staged "
            f"artifacts; need at least {MIN_GROUNDED}. Quote the real text of the graph, the "
            "generator, or the decision packet."
        )

    # --- residual risk disclosure ----------------------------------------------
    residual = review.get("residual_risks")
    if not isinstance(residual, list) or not residual:
        reasons.append(
            "residual_risks must be a non-empty list; an approval that discloses no residual "
            "risk is not a review"
        )

    if reasons:
        fail(reasons)

    print("REVIEW CHECK PASSED")
    print(f"  verdict: {verdict}")
    print(f"  dimensions checked: {len(dimensions)}")
    print(f"  findings: {len(findings)} ({blocking} blocking)")
    print(f"  grounded quotes: {len(grounded)}/{len(spans)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
