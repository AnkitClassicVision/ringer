#!/usr/bin/env python3
"""Validate the Fable scenario pack for live testing of the recall pathway.

A scenario is only useful if a human can execute it verbatim and tell pass from
fail without interpretation. Anything vaguer than that is rejected.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "mott-v30-scenarios.v1"
PRIORITIES = {"critical", "high", "medium", "low"}
MIN_SCENARIOS = 6


def fail(reasons: list[str]) -> None:
    print("SCENARIO PACK CHECK FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    sys.exit(1)


def as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, type=Path)
    args = parser.parse_args()

    if not args.pack.is_file():
        fail([f"pack not found: {args.pack}"])
    try:
        pack = json.loads(args.pack.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"pack is not valid JSON: {exc}"])
    if not isinstance(pack, dict):
        fail(["pack must be a JSON object"])

    reasons: list[str] = []
    if pack.get("schema_version") != SCHEMA_VERSION:
        reasons.append(f"schema_version must be exactly {SCHEMA_VERSION!r}")

    scenarios = pack.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) < MIN_SCENARIOS:
        reasons.append(f"scenarios must be a list of at least {MIN_SCENARIOS} entries")
        scenarios = []

    seen_ids, books_flagged = set(), 0
    for s in scenarios:
        if not isinstance(s, dict):
            reasons.append(f"scenario is not an object: {s!r}")
            continue
        sid = as_text(s.get("id")) or "<unnamed>"
        if sid in seen_ids:
            reasons.append(f"duplicate scenario id {sid!r}")
        seen_ids.add(sid)

        if as_text(s.get("priority")).strip().lower() not in PRIORITIES:
            reasons.append(f"{sid}: priority must be one of {sorted(PRIORITIES)}")

        # The tester must be able to send it verbatim.
        msgs = s.get("messages_to_send")
        if not isinstance(msgs, list) or not msgs or not all(
            isinstance(m, str) and m.strip() for m in msgs
        ):
            reasons.append(
                f"{sid}: messages_to_send must be a non-empty list of the EXACT texts to send, "
                "in order, with no placeholders to fill in"
            )
        else:
            for m in msgs:
                if re.search(r"[<\[{]{1,2}[A-Za-z_ ]+[>\]}]{1,2}", m):
                    reasons.append(
                        f"{sid}: message {m[:40]!r} contains a placeholder; the tester must be "
                        "able to send it verbatim"
                    )

        for field, minlen in (("expected", 40), ("failure_signature", 40), ("why_it_matters", 40)):
            if len(as_text(s.get(field)).strip()) < minlen:
                reasons.append(f"{sid}: {field} must be at least {minlen} characters and be specific")

        if not isinstance(s.get("books_a_real_appointment"), bool):
            reasons.append(
                f"{sid}: books_a_real_appointment must be a boolean. Booking is irreversible from "
                "the pathway side, so the tester has to know before sending."
            )
        elif s["books_a_real_appointment"]:
            books_flagged += 1

        if not as_text(s.get("verify_where")).strip():
            reasons.append(
                f"{sid}: verify_where must say where to confirm the outcome, for example the "
                "practice system, the gateway logs, or the message text alone"
            )

    ordering = pack.get("recommended_order")
    if not isinstance(ordering, list) or set(ordering) != seen_ids:
        reasons.append(
            "recommended_order must list every scenario id exactly once, so the tester knows "
            "which to run first given that some scenarios end the conversation"
        )

    if len(as_text(pack.get("sequencing_rationale")).strip()) < 60:
        reasons.append(
            "sequencing_rationale must explain the ordering, especially which scenarios must run "
            "before ones that book or end a conversation"
        )

    if reasons:
        fail(reasons)

    print("SCENARIO PACK CHECK PASSED")
    print(f"  scenarios: {len(scenarios)}")
    print(f"  that book a real appointment: {books_flagged}")
    print(f"  priorities: {sorted({as_text(s.get('priority')).lower() for s in scenarios})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
