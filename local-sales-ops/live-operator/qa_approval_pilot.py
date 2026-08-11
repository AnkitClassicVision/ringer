#!/usr/bin/env python3
"""Validate live-read approval-pilot artifacts.

This is read-only verification. It does not send email or write HubSpot.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def fail(message: str) -> None:
    raise SystemExit(f"WHY: {message}")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                fail(f"invalid JSONL line {lineno}: {exc}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cap", type=int, default=3)
    parser.add_argument("--min-candidates", type=int, default=1)
    args = parser.parse_args()

    queue = args.out_dir / "approval_pilot_queue.jsonl"
    table = args.out_dir / "approval_pilot_table.md"
    receipt_path = args.out_dir / "approval_pilot_receipt.json"
    qa_report = args.out_dir / "qa_report.md"
    context = args.out_dir / "hubspot_enriched_context_sanitized.jsonl"
    for path in [queue, table, receipt_path, qa_report, context]:
        if not path.exists() or path.stat().st_size == 0:
            fail(f"missing artifact {path.name}")

    rows = read_jsonl(queue)
    if len(rows) < args.min_candidates:
        fail(f"expected at least {args.min_candidates} candidate row(s), got {len(rows)}")
    receipt = read_json(receipt_path)
    if receipt.get("mode") != "approval_pilot":
        fail("receipt mode is not approval_pilot")
    if receipt.get("external_actions_taken") != 0 or receipt.get("sends") != 0 or receipt.get("hubspot_writes") != 0:
        fail("receipt claims external sends or HubSpot writes")
    if int(receipt.get("cap") or 0) > args.cap:
        fail("receipt cap exceeds requested cap")

    ready = [r for r in rows if r.get("status") == "ready_for_approval"]
    held = [r for r in rows if r.get("status") == "held"]
    if len(ready) > args.cap:
        fail(f"ready rows {len(ready)} exceed cap {args.cap}")
    if len(ready) != int(receipt.get("ready_for_approval", -1)):
        fail("ready count mismatch between queue and receipt")
    if len(held) != int(receipt.get("held", -1)):
        fail("held count mismatch between queue and receipt")

    seen = set()
    for idx, row in enumerate(rows, 1):
        if row.get("schema_version") != "sales_ops.approval_pilot.v1":
            fail(f"row {idx} wrong schema_version")
        if row.get("candidate_id") in seen:
            fail(f"duplicate candidate_id {row.get('candidate_id')}")
        seen.add(row.get("candidate_id"))
        if row.get("send_receipt") or row.get("hubspot_receipt") or row.get("external_actions_taken"):
            fail(f"row {idx} has external-action receipt in approval pilot")
        if row.get("status") == "ready_for_approval":
            required_pass = ["context_qa", "writing_qa", "suppression_qa", "recent_touch_qa", "action_qa"]
            for field in required_pass:
                if row.get(field) != "pass":
                    fail(f"ready row {idx} has {field}={row.get(field)!r}")
            for field in ["deal_id", "contact_id", "contact_email", "idempotency_key"]:
                if not row.get(field):
                    fail(f"ready row {idx} missing {field}")
            if row.get("suppression_status") != "pass":
                fail(f"ready row {idx} suppression not pass")
            if row.get("recent_touch_status") != "pass":
                fail(f"ready row {idx} recent touch not pass")
            if row.get("approval_state") != "pending_review":
                fail(f"ready row {idx} not pending_review")
        elif row.get("status") == "held":
            if not row.get("hold_reason"):
                fail(f"held row {idx} missing hold_reason")
        else:
            fail(f"row {idx} unsupported status {row.get('status')!r}")

    table_text = table.read_text(encoding="utf-8")
    if EMAIL_RE.search(table_text):
        fail("approval table contains an unmasked raw email")
    if "No sends" not in qa_report.read_text(encoding="utf-8") and "External sends: 0" not in qa_report.read_text(encoding="utf-8"):
        fail("qa report does not state zero sends")

    print(f"PASS: approval pilot verified candidates={len(rows)} ready={len(ready)} held={len(held)} cap={args.cap} sends=0 hubspot_writes=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
