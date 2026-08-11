#!/usr/bin/env python3
"""Validate a Sales Ops send queue before any live action.

This checker is intentionally strict: unknown context never passes silently, and
live receipts are forbidden while policy keeps live sends disabled.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_FIELDS = [
    "schema_version",
    "run_id",
    "candidate_id",
    "idempotency_key",
    "cohort_name",
    "deal_id",
    "deal_name",
    "pipeline",
    "stage",
    "days_idle",
    "stale_reason",
    "recommended_action",
    "draft_subject",
    "draft_body",
    "context_qa",
    "writing_qa",
    "suppression_qa",
    "recent_touch_qa",
    "action_qa",
    "status",
    "external_actions_taken",
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.expanduser().read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"WHY: invalid JSONL at line {lineno}: {exc}")
    return rows


def fail(msg: str) -> None:
    raise SystemExit(f"WHY: {msg}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--min-rows", type=int, default=1)
    args = parser.parse_args()

    policy = load_json(args.policy)
    rows = load_jsonl(args.queue)
    if len(rows) < args.min_rows:
        fail(f"queue has {len(rows)} rows, expected at least {args.min_rows}")

    send_enabled = bool(policy.get("live_actions", {}).get("send_enabled"))
    hubspot_write_enabled = bool(policy.get("live_actions", {}).get("hubspot_write_enabled"))
    banned_phrases = [p.lower() for p in policy.get("qa", {}).get("banned_copy_phrases", [])]
    banned_chars = policy.get("qa", {}).get("banned_characters", [])

    seen = set()
    seen_idempotency = set()
    held = 0
    ready = 0
    for idx, row in enumerate(rows, 1):
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        if missing:
            fail(f"row {idx} missing fields {missing}")
        if row.get("schema_version") != "sales_ops.send_queue.v1":
            fail(f"row {idx} has unsupported schema_version {row.get('schema_version')!r}")
        cid = row["candidate_id"]
        idem = row["idempotency_key"]
        if cid in seen:
            fail(f"duplicate candidate_id {cid}")
        if idem in seen_idempotency:
            fail(f"duplicate idempotency_key {idem}")
        seen.add(cid)
        seen_idempotency.add(idem)

        if row.get("send_receipt") or row.get("hubspot_receipt"):
            fail(f"row {idx} has live receipts in a pre-send queue")
        if row.get("external_actions_taken"):
            fail(f"row {idx} claims external actions were taken")
        if not send_enabled and row.get("status") in {"sent", "sent_and_logged"}:
            fail(f"row {idx} is sent while send_enabled=false")
        if not hubspot_write_enabled and row.get("hubspot_receipt"):
            fail(f"row {idx} has HubSpot receipt while hubspot_write_enabled=false")

        draft_surface = f"{row.get('draft_subject', '')} {row.get('draft_body', '')}".lower()
        for phrase in banned_phrases:
            if phrase and phrase in draft_surface:
                fail(f"row {idx} draft contains banned phrase {phrase!r}")
        for char in banned_chars:
            if char and char in f"{row.get('draft_subject', '')}{row.get('draft_body', '')}":
                fail(f"row {idx} draft contains banned character {char!r}")

        status = row.get("status")
        if status == "ready_for_approval":
            ready += 1
            for qa_field in ["context_qa", "writing_qa", "suppression_qa", "recent_touch_qa", "action_qa"]:
                if row.get(qa_field) != "pass":
                    fail(f"row {idx} ready_for_approval but {qa_field}={row.get(qa_field)!r}")
            if not row.get("contact_email"):
                fail(f"row {idx} ready_for_approval without contact_email")
        elif status == "held":
            held += 1
            if not row.get("hold_reason"):
                fail(f"row {idx} is held without hold_reason")
        else:
            fail(f"row {idx} has unsupported status {status!r}")

    print(f"PASS: send_queue validated rows={len(rows)} ready={ready} held={held} sends=0 hubspot_writes=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
