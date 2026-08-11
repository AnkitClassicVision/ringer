#!/usr/bin/env python3
"""Deny-by-default live send boundary for Sales Ops.

This file is intentionally not a network client. It is the hard edge that later
live adapters must satisfy before any provider send or HubSpot write can run.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict


REQUIRED_ENV = "RINGER_SALES_OPS_ALLOW_LIVE_SEND"
KILL_SWITCH = Path.home() / ".ringer/sales-ops-ledger/KILL_SWITCH"


def load_first_queue_row(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                return json.loads(line)
    raise SystemExit("queue is empty")


def decision(queue_row: Dict[str, Any], approval_file: Path | None) -> Dict[str, Any]:
    reasons = []
    if os.environ.get(REQUIRED_ENV) != "1":
        reasons.append("missing_live_env_flag")
    if KILL_SWITCH.exists():
        reasons.append("kill_switch_present")
    if not approval_file:
        reasons.append("missing_approval_file")
    elif not approval_file.exists():
        reasons.append("approval_file_not_found")
    if queue_row.get("approval_state") != "approved_to_send":
        reasons.append("row_not_approved_to_send")
    for qa_field in ["context_qa", "writing_qa", "suppression_qa", "recent_touch_qa", "action_qa"]:
        if queue_row.get(qa_field) != "pass":
            reasons.append(f"{qa_field}_not_pass")
    if queue_row.get("recommended_action") != "send_email":
        reasons.append("channel_not_email")
    if queue_row.get("send_receipt") or queue_row.get("hubspot_receipt"):
        reasons.append("row_already_has_receipt")

    allowed = not reasons
    return {
        "allowed": allowed,
        "decision": "allow" if allowed else "block",
        "reasons": reasons,
        "candidate_id": queue_row.get("candidate_id"),
        "external_actions_taken": [],
        "send_receipt": None,
        "hubspot_receipt": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--approval-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    row = load_first_queue_row(args.queue)
    result = decision(row, args.approval_file)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"LIVE_BOUNDARY_{result['decision'].upper()} reasons={len(result['reasons'])}")
    return 0 if not result["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
