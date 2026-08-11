#!/usr/bin/env python3
"""Build a Sales Ops send queue from a PracticeOS snapshot.

This is the deterministic bridge from Ringer detection artifacts to live-capable
work. It does not send email and does not write HubSpot. Optional live HubSpot
read enrichment can be added with --live-hubspot, but live actions remain blocked
by policy unless a later send adapter is explicitly enabled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_SNAPSHOT = Path("/tmp/ringer-sales-ops-input/live_practiceos_snapshot.json")


def load_json(path: Path) -> Dict[str, Any]:
    with path.expanduser().open("r", encoding="utf-8") as f:
        return json.load(f)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stage_sla_days(snapshot: Dict[str, Any], deal: Dict[str, Any]) -> int:
    rules = snapshot.get("pipeline", {}).get("stage_sla_days", {})
    stage = str(deal.get("stage_label") or "").lower()
    if "closed won" in stage:
        return int(rules.get("closed won", 999))
    if "closed lost" in stage or "park" in stage:
        return int(rules.get("closed lost", rules.get("default", 7)))
    if "hand raised" in stage or "inbound" in stage:
        return int(rules.get("new/inbound", rules.get("default", 7)))
    if "discovery" in stage:
        return int(rules.get("discovery", rules.get("default", 7)))
    if "assessment" in stage or "meeting" in stage:
        return int(rules.get("meeting", rules.get("default", 7)))
    if "options" in stage or "term sheet" in stage or "quote" in stage:
        return int(rules.get("quote", rules.get("default", 7)))
    return int(rules.get("default", 7))


def stable_candidate_id(deal_id: str, action: str, run_date: str) -> str:
    raw = f"{deal_id}:{action}:{run_date}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def split_deal_name(deal: Dict[str, Any]) -> str:
    return str(deal.get("dealname") or deal.get("deal_name") or "Unknown PracticeOS deal").strip()


def draft_for(deal_name: str) -> Dict[str, str]:
    subject = "PracticeOS fit check"
    body = (
        "Hi, this is Ankit.\n\n"
        f"I had {deal_name} on my PracticeOS follow-up list and wanted to ask one direct question: "
        "is improving follow-up, owner time, or patient-demand execution still worth a short fit review, "
        "or should I park this for later?\n\n"
        "If it is worth a look, I can send over the cleanest next step."
    )
    return {"draft_subject": subject, "draft_body": body}


def base_context_from_snapshot(deal: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "deal_id": str(deal.get("deal_id") or ""),
        "deal_name": split_deal_name(deal),
        "pipeline": str(deal.get("pipeline") or ""),
        "stage": str(deal.get("stage_label") or ""),
        "stage_id": str(deal.get("stage_id") or ""),
        "days_idle": int(deal.get("days_idle") or 0),
        "lastmodifieddate": deal.get("lastmodifieddate"),
        "contact_id": None,
        "contact_email": None,
        "company_id": None,
        "suppression_status": "unknown_snapshot_missing_contact_level_suppression",
        "recent_touch_status": "unknown_snapshot_missing_activity_history",
        "context_sources": [
            {
                "source": "practiceos_snapshot",
                "id": str(deal.get("deal_id") or ""),
                "checked_at": utc_now(),
                "snapshot_captured_at": snapshot.get("captured_at"),
            }
        ],
    }


def classify_row(row: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    qa = {
        "context_qa": "pass",
        "writing_qa": "pass",
        "suppression_qa": "pass",
        "recent_touch_qa": "pass",
        "action_qa": "pass",
    }
    holds: List[str] = []

    if not row.get("contact_id") or not row.get("contact_email"):
        qa["context_qa"] = "hold"
        holds.append("hold_no_email_or_contact")
    if str(row.get("suppression_status", "")).startswith("unknown"):
        qa["suppression_qa"] = "hold"
        holds.append("hold_suppression_unknown")
    if str(row.get("recent_touch_status", "")).startswith("unknown"):
        qa["recent_touch_qa"] = "hold"
        holds.append("hold_recent_touch_unknown")

    draft_surface = f"{row.get('draft_subject', '')} {row.get('draft_body', '')}".lower()
    for phrase in policy.get("qa", {}).get("banned_copy_phrases", []):
        if phrase.lower() in draft_surface:
            qa["writing_qa"] = "hold"
            holds.append(f"hold_copy_phrase:{phrase}")
    for char in policy.get("qa", {}).get("banned_characters", []):
        if char and char in f"{row.get('draft_subject', '')}{row.get('draft_body', '')}":
            qa["writing_qa"] = "hold"
            holds.append("hold_copy_banned_character")

    if not policy.get("live_actions", {}).get("send_enabled", False):
        qa["action_qa"] = "hold"
        holds.append("hold_send_disabled_by_policy")

    return {**qa, "hold_reason": ";".join(sorted(set(holds))) if holds else None}


def eligible_deals(snapshot: Dict[str, Any], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    pipeline_id = str(policy.get("approved_lane", {}).get("pipeline_id") or snapshot.get("pipeline", {}).get("id") or "")
    rows = []
    for deal in snapshot.get("deals", []):
        stage = str(deal.get("stage_label") or "").lower()
        if str(deal.get("pipeline") or "") != pipeline_id:
            continue
        if "closed won" in stage or "closed lost" in stage or "park" in stage:
            continue
        if deal.get("bcat_suppressed") or deal.get("lead_unqualified"):
            continue
        if int(deal.get("days_idle") or 0) <= stage_sla_days(snapshot, deal):
            continue
        rows.append(deal)
    return sorted(rows, key=lambda d: (-int(d.get("days_idle") or 0), split_deal_name(d).lower()))


def build_rows(snapshot: Dict[str, Any], policy: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows: List[Dict[str, Any]] = []
    for deal in eligible_deals(snapshot, policy)[:limit]:
        context = base_context_from_snapshot(deal, snapshot)
        action = "send_email"
        draft = draft_for(context["deal_name"])
        sla = stage_sla_days(snapshot, deal)
        candidate_id = stable_candidate_id(context["deal_id"], action, run_date)
        idempotency_key = stable_candidate_id(context["deal_id"], action, "practiceos-email")
        row: Dict[str, Any] = {
            "schema_version": "sales_ops.send_queue.v1",
            "run_id": f"sales-ops-daily-sweep-{run_date}",
            "candidate_id": candidate_id,
            "idempotency_key": idempotency_key,
            **context,
            "cohort_name": "practiceos_stale_active_deals",
            "stage_sla_days": sla,
            "stale_reason": f"past {sla}-day stage SLA by {max(0, context['days_idle'] - sla)} days",
            "recommended_action": action,
            **draft,
            "approval_state": "not_requested",
            "status": "pending_qa",
            "send_receipt": None,
            "hubspot_receipt": None,
            "external_actions_taken": [],
            "audit": {
                "created_at": utc_now(),
                "created_by": "ringer",
                "source": "local-sales-ops/live-operator/build_send_queue.py",
            },
        }
        qa = classify_row(row, policy)
        row.update({k: v for k, v in qa.items() if k != "hold_reason"})
        row["hold_reason"] = qa["hold_reason"]
        if qa["hold_reason"]:
            row["status"] = "held"
        else:
            row["status"] = "ready_for_approval"
            row["approval_state"] = "pending_review"
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def write_approval_table(path: Path, rows: List[Dict[str, Any]]) -> None:
    lines = [
        "# Sales Ops Approval Table",
        "",
        "Status: generated by Ringer live-operator bridge. No sends or HubSpot writes performed.",
        "",
        "| candidate_id | deal | stage | days_idle | status | hold_reason | action |",
        "|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {candidate_id} | {deal_name} | {stage} | {days_idle} | {status} | {hold_reason} | {recommended_action} |".format(
                **{k: str(row.get(k) or "") for k in ["candidate_id", "deal_name", "stage", "days_idle", "status", "hold_reason", "recommended_action"]}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_qa_report(path: Path, rows: List[Dict[str, Any]], policy: Dict[str, Any]) -> None:
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        if row.get("hold_reason"):
            for reason in str(row["hold_reason"]).split(";"):
                counts[reason] = counts.get(reason, 0) + 1
    lines = [
        "# Sales Ops Queue QA Report",
        "",
        "No sends performed. No HubSpot writes performed.",
        "",
        f"Rows: {len(rows)}",
        f"Live send enabled: {policy.get('live_actions', {}).get('send_enabled')}",
        f"HubSpot write enabled: {policy.get('live_actions', {}).get('hubspot_write_enabled')}",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(["", "## Next unlock", "", "Provide live HubSpot contact/activity enrichment and select a sender account before pilot sends."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    snapshot = load_json(args.snapshot)
    policy = load_json(args.policy)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = build_rows(snapshot, policy, args.limit)
    write_jsonl(args.out_dir / "send_queue.jsonl", rows)
    write_approval_table(args.out_dir / "approval_table.md", rows)
    write_qa_report(args.out_dir / "qa_report.md", rows, policy)
    print(f"SEND_QUEUE_BUILT rows={len(rows)} sends=0 hubspot_writes=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
