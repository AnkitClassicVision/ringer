#!/usr/bin/env python3
"""Read live HubSpot PracticeOS deals and build an approval-pilot queue.

Read-only by design:
- no email sends
- no HubSpot writes
- no CRM stage moves
- no sequence enrollment

The queue may contain raw CRM IDs/emails locally because later approved actions need
stable identifiers. Human-facing markdown masks contact emails and IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

HELPER_DIR = Path.home() / ".claude" / "skills" / "hubspot"
sys.path.insert(0, str(HELPER_DIR))
try:
    import hubspot_api  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"WHY: unable to import hubspot_api helper: {exc}")

BASE = "https://api.hubapi.com"
DEFAULT_POLICY = Path(__file__).with_name("policy.json")
LEDGER_DIR_DEFAULT = Path.home() / ".ringer" / "sales-ops-ledger"

DEAL_PROPERTIES = [
    "dealname",
    "pipeline",
    "dealstage",
    "amount",
    "createdate",
    "hs_lastmodifieddate",
    "hs_last_activity_date",
    "notes_last_contacted",
    "hubspot_owner_id",
]

CONTACT_PROPERTIES = [
    "email",
    "firstname",
    "lastname",
    "company",
    "hs_email_optout",
    "hs_email_hard_bounce_reason",
    "hs_email_hard_bounce_reason_enum",
    "hs_email_last_send_date",
    "notes_last_contacted",
    "lastmodifieddate",
]

STAGE_SLA_DAYS = {
    "Identified": 21,
    "Hand Raised": 2,
    "Discovery Call Booked": 2,
    "Discovery Done / Mutual Fit": 7,
    "Practice Assessment": 7,
    "Options Presented / Term Sheet": 7,
    "Counsel + Diligence": 7,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value)
    try:
        if text.isdigit():
            return datetime.fromtimestamp(int(text) / 1000, tz=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def age_days(value: Any, now: datetime) -> Optional[int]:
    dt = parse_dt(value)
    if not dt:
        return None
    return max(0, int((now - dt).total_seconds() // 86400))


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_hash(value: str) -> str:
    return sha(value)[:16]


def mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return ""
    user, domain = email.split("@", 1)
    if not user:
        return "***@" + domain
    return user[:1] + "***@" + domain


def mask_id(value: Any) -> str:
    value = str(value or "")
    if not value:
        return ""
    return short_hash(value)


def safe_deal_label(name: str) -> str:
    # Keep this local artifact useful while avoiding raw IDs. Practice names are
    # already in HubSpot and not printed by the final Telegram summary.
    return str(name or "Unknown deal").replace("|", "/")[:96]


class HubSpotReadOnly:
    def __init__(self) -> None:
        key = hubspot_api.load_api_key()
        if not key:
            raise SystemExit("WHY: HubSpot API key unavailable")
        self.key = key

    def request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            BASE + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bearer " + self.key,
                "Content-Type": "application/json",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                body = exc.read().decode("utf-8", errors="replace")[:500]
                raise RuntimeError(f"HubSpot {method} {path} failed {exc.code}: {body}") from exc
            except Exception:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
        raise RuntimeError(f"HubSpot {method} {path} failed after retries")

    def pipeline(self, pipeline_id: str) -> dict:
        return self.request("GET", f"/crm/v3/pipelines/deals/{urllib.parse.quote(pipeline_id)}")

    def search_deals(self, pipeline_id: str, limit: int) -> List[dict]:
        out: List[dict] = []
        after: Optional[str] = None
        while len(out) < limit:
            payload: Dict[str, Any] = {
                "filterGroups": [{"filters": [{"propertyName": "pipeline", "operator": "EQ", "value": pipeline_id}]}],
                "properties": DEAL_PROPERTIES,
                "limit": min(100, limit - len(out)),
                "sorts": ["-hs_lastmodifieddate"],
            }
            if after:
                payload["after"] = after
            data = self.request("POST", "/crm/v3/objects/deals/search", payload)
            out.extend(data.get("results", []))
            after = (data.get("paging") or {}).get("next", {}).get("after")
            if not after:
                break
        return out

    def deal_associations(self, deal_id: str, to_type: str) -> List[str]:
        data = self.request("GET", f"/crm/v3/objects/deals/{urllib.parse.quote(deal_id)}/associations/{urllib.parse.quote(to_type)}?limit=100")
        return [str(r.get("id")) for r in data.get("results", []) if r.get("id")]

    def deal_contacts(self, deal_id: str) -> List[str]:
        return self.deal_associations(deal_id, "contacts")

    def deal_companies(self, deal_id: str) -> List[str]:
        return self.deal_associations(deal_id, "companies")

    def company_contacts(self, company_id: str) -> List[str]:
        data = self.request("GET", f"/crm/v3/objects/companies/{urllib.parse.quote(company_id)}/associations/contacts?limit=100")
        return [str(r.get("id")) for r in data.get("results", []) if r.get("id")]

    def contact(self, contact_id: str) -> Optional[dict]:
        props = urllib.parse.quote(",".join(CONTACT_PROPERTIES))
        try:
            return self.request("GET", f"/crm/v3/objects/contacts/{urllib.parse.quote(contact_id)}?properties={props}")
        except RuntimeError:
            # If an optional property does not exist, fall back to the minimum.
            props = urllib.parse.quote("email,firstname,lastname,company,hs_email_optout,notes_last_contacted")
            return self.request("GET", f"/crm/v3/objects/contacts/{urllib.parse.quote(contact_id)}?properties={props}")


def load_json(path: Path) -> dict:
    return json.loads(path.expanduser().read_text(encoding="utf-8"))


def used_idempotency_keys(ledger_dir: Path) -> set[str]:
    keys: set[str] = set()
    if not ledger_dir.exists():
        return keys
    for path in ledger_dir.glob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                key = obj.get("idempotency_key") or obj.get("candidate_id")
                if key:
                    keys.add(str(key))
        except Exception:
            continue
    return keys


def stage_maps(pipeline: dict) -> Tuple[dict[str, str], set[str]]:
    labels: dict[str, str] = {}
    closed: set[str] = set()
    for stage in pipeline.get("stages", []):
        sid = str(stage.get("id"))
        labels[sid] = str(stage.get("label") or sid)
        metadata = stage.get("metadata") or {}
        if str(metadata.get("isClosed", "false")).lower() == "true":
            closed.add(sid)
    return labels, closed


def choose_touch_date(deal_props: dict, contact_props: dict) -> Tuple[Optional[str], str]:
    candidates = [
        (deal_props.get("notes_last_contacted"), "deal.notes_last_contacted"),
        (contact_props.get("notes_last_contacted"), "contact.notes_last_contacted"),
        (deal_props.get("hs_last_activity_date"), "deal.hs_last_activity_date"),
    ]
    parsed: List[Tuple[datetime, Any, str]] = []
    for value, source in candidates:
        parsed_dt = parse_dt(value)
        if parsed_dt is not None:
            parsed.append((parsed_dt, value, source))
    if not parsed:
        return None, "none"
    parsed.sort(reverse=True, key=lambda item: item[0])
    return str(parsed[0][1]), parsed[0][2]


def suppression_status(contact_props: dict) -> Tuple[str, list[str]]:
    reasons: list[str] = []
    optout = str(contact_props.get("hs_email_optout") or "").lower()
    if optout in {"true", "1", "yes"}:
        reasons.append("contact_email_opted_out")
    bounce = contact_props.get("hs_email_hard_bounce_reason") or contact_props.get("hs_email_hard_bounce_reason_enum")
    if bounce:
        reasons.append("hard_bounce_present")
    if reasons:
        return "blocked:" + ",".join(reasons), reasons
    return "pass", []


def make_draft(deal_name: str, stage_label: str, days_idle: int) -> dict:
    subject = "PracticeOS fit check"
    body = (
        "Hi, this is Ankit.\n\n"
        f"I had {deal_name} in the PracticeOS follow-up lane. It looks like the thread has been quiet for about {days_idle} days.\n\n"
        "Worth a 15 minute review this week to decide if improving follow-up, owner time, or patient-demand execution is still a priority?"
    )
    return {"draft_subject": subject, "draft_body": body}


def build(args: argparse.Namespace) -> dict:
    policy = load_json(args.policy)
    lane = policy.get("approved_lane", {})
    pipeline_id = str(lane.get("pipeline_id") or "")
    cap = int(args.cap or lane.get("daily_send_cap") or 3)
    if cap > int(lane.get("daily_send_cap") or cap):
        raise SystemExit("WHY: requested cap exceeds policy daily_send_cap")
    if cap > 3:
        raise SystemExit("WHY: approval pilot cap cannot exceed 3")

    now = datetime.now(timezone.utc)
    client = HubSpotReadOnly()
    pipeline = client.pipeline(pipeline_id)
    stage_labels, closed_stages = stage_maps(pipeline)
    deals = client.search_deals(pipeline_id, args.scan_limit)
    used_keys = used_idempotency_keys(args.ledger_dir.expanduser())

    candidates: List[dict] = []
    context_rows: List[dict] = []
    counters: Dict[str, int] = {}

    for deal in deals:
        deal_id = str(deal.get("id"))
        props = deal.get("properties") or {}
        stage_id = str(props.get("dealstage") or "")
        stage_label = stage_labels.get(stage_id, stage_id)
        if stage_id in closed_stages:
            counters["closed_skipped"] = counters.get("closed_skipped", 0) + 1
            continue
        touch_value, touch_source = choose_touch_date(props, {})
        contact_ids = client.deal_contacts(deal_id)
        company_ids = client.deal_companies(deal_id)
        contact_source = "deal_association"
        if not contact_ids and company_ids:
            # Many PracticeOS deals are associated to companies, not contacts.
            # For approval-pilot queueing, fall back to company-associated contacts
            # and still keep the row in review mode, never live-send mode.
            for company_id in company_ids[:3]:
                contact_ids.extend(client.company_contacts(company_id))
            contact_ids = list(dict.fromkeys(contact_ids))
            if contact_ids:
                contact_source = "company_association"
        contact_obj = client.contact(contact_ids[0]) if contact_ids else None
        contact_props = (contact_obj or {}).get("properties") or {}
        if contact_props:
            touch_value, touch_source = choose_touch_date(props, contact_props)
        touch_days = age_days(touch_value, now)
        # Staleness is based on human touch/activity, not generic HubSpot record
        # modification. If human-touch context is missing, keep the row as a
        # held candidate so the operator exposes the missing context instead of
        # silently skipping the deal.
        fallback_age = age_days(props.get("createdate") or props.get("hs_lastmodifieddate"), now)
        days_idle = touch_days if touch_days is not None else fallback_age
        sla = STAGE_SLA_DAYS.get(stage_label, 7)
        if touch_days is not None and touch_days <= sla:
            counters["not_stale_skipped"] = counters.get("not_stale_skipped", 0) + 1
            continue

        email = contact_props.get("email")
        supp, supp_reasons = suppression_status(contact_props)
        recent_cooldown = int(policy.get("qa", {}).get("recent_touch_cooldown_days") or 7)
        recent_status = "unknown"
        if touch_days is not None:
            recent_status = "pass" if touch_days >= recent_cooldown else "blocked:recent_touch"

        action = "send_email"
        run_id = "sales-ops-approval-pilot-" + now.strftime("%Y-%m-%d")
        candidate_id = short_hash(f"{deal_id}:{contact_ids[0] if contact_ids else ''}:{action}:{run_id}")
        idempotency_key = short_hash(f"{deal_id}:{contact_ids[0] if contact_ids else ''}:practiceos-email")
        draft = make_draft(str(props.get("dealname") or "Unknown PracticeOS deal"), stage_label, int(days_idle or 0))

        holds: list[str] = []
        if not contact_ids:
            holds.append("hold_no_contact")
        if not email:
            holds.append("hold_no_email")
        if supp != "pass":
            holds.append("hold_suppression:" + supp)
        if recent_status == "unknown":
            holds.append("hold_recent_touch_unknown")
        elif recent_status.startswith("blocked"):
            holds.append("hold_recent_touch")
        if idempotency_key in used_keys:
            holds.append("hold_duplicate_idempotency")

        ready = not holds and len([c for c in candidates if c.get("status") == "ready_for_approval"]) < cap
        if not holds and not ready:
            holds.append("hold_cap_exhausted_for_pilot")

        row = {
            "schema_version": "sales_ops.approval_pilot.v1",
            "run_id": run_id,
            "candidate_id": candidate_id,
            "idempotency_key": idempotency_key,
            "cohort_name": "practiceos_stale_active_deals",
            "deal_id": deal_id,
            "deal_name": props.get("dealname"),
            "pipeline": pipeline_id,
            "stage_id": stage_id,
            "stage": stage_label,
            "days_idle": days_idle,
            "stage_sla_days": sla,
            "stale_reason": f"past {sla}-day stage SLA by {max(0, int(days_idle or 0) - sla)} days",
            "contact_id": contact_ids[0] if contact_ids else None,
            "contact_email": email,
            "contact_email_sha256": sha(email.lower()) if email else None,
            "contact_email_masked": mask_email(email),
            "company_id": company_ids[0] if company_ids else None,
            "contact_source": contact_source,
            "suppression_status": supp,
            "suppression_reasons": supp_reasons,
            "recent_touch_status": recent_status,
            "last_touch_at": touch_value,
            "last_touch_source": touch_source,
            "recommended_action": action,
            **draft,
            "context_qa": "pass" if contact_ids and email else "hold",
            "writing_qa": "pass",
            "suppression_qa": "pass" if supp == "pass" else "hold",
            "recent_touch_qa": "pass" if recent_status == "pass" else "hold",
            "action_qa": "pass",
            "approval_state": "pending_review" if ready else "hold",
            "status": "ready_for_approval" if ready else "held",
            "hold_reason": ";".join(holds) if holds else None,
            "send_receipt": None,
            "hubspot_receipt": None,
            "external_actions_taken": [],
            "audit": {
                "created_at": utc_now(),
                "created_by": "ringer_hubspot_live_enrichment",
                "source": "hubspot_live_enrichment.py",
                "deal_ref_hash": mask_id(deal_id),
                "contact_ref_hash": mask_id(contact_ids[0] if contact_ids else ""),
            },
        }
        candidates.append(row)
        context_rows.append({
            "deal_ref_hash": mask_id(deal_id),
            "contact_ref_hash": mask_id(contact_ids[0] if contact_ids else ""),
            "stage": stage_label,
            "days_idle": days_idle,
            "has_email": bool(email),
            "suppression_status": supp,
            "recent_touch_status": recent_status,
            "status": row["status"],
            "hold_reason": row["hold_reason"],
        })

    candidates.sort(key=lambda r: (0 if r["status"] == "ready_for_approval" else 1, -int(r.get("days_idle") or 0), str(r.get("deal_name") or "")))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    queue_path = args.out_dir / "approval_pilot_queue.jsonl"
    with queue_path.open("w", encoding="utf-8") as f:
        for row in candidates:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    os.chmod(queue_path, 0o600)

    with (args.out_dir / "hubspot_enriched_context_sanitized.jsonl").open("w", encoding="utf-8") as f:
        for row in context_rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    lines = [
        "# Sales Ops Approval Pilot",
        "",
        "Mode: approval-pilot, no sends, no HubSpot writes.",
        f"Daily cap: {cap}",
        "",
        "| candidate | deal | stage | idle_days | email | status | hold_reason |",
        "|---|---|---|---:|---|---|---|",
    ]
    for row in candidates:
        lines.append(
            f"| {row['candidate_id']} | {safe_deal_label(row.get('deal_name') or '')} | {row['stage']} | {row['days_idle']} | {row.get('contact_email_masked') or ''} | {row['status']} | {row.get('hold_reason') or ''} |"
        )
    (args.out_dir / "approval_pilot_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ready = sum(1 for r in candidates if r["status"] == "ready_for_approval")
    held = sum(1 for r in candidates if r["status"] == "held")
    receipt = {
        "run_id": "sales-ops-approval-pilot-" + now.strftime("%Y-%m-%d"),
        "generated_at": utc_now(),
        "mode": "approval_pilot",
        "pipeline_label": pipeline.get("label"),
        "pipeline_id_hash": mask_id(pipeline_id),
        "scan_limit": args.scan_limit,
        "deals_read": len(deals),
        "candidates": len(candidates),
        "ready_for_approval": ready,
        "held": held,
        "cap": cap,
        "external_actions_taken": 0,
        "sends": 0,
        "hubspot_writes": 0,
        "counters": counters,
        "artifacts": {
            "queue": str(queue_path),
            "approval_table": str(args.out_dir / "approval_pilot_table.md"),
            "sanitized_context": str(args.out_dir / "hubspot_enriched_context_sanitized.jsonl"),
        },
    }
    (args.out_dir / "approval_pilot_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = [
        "# Approval Pilot QA Report",
        "",
        f"Deals read: {len(deals)}",
        f"Candidates: {len(candidates)}",
        f"Ready for approval: {ready}",
        f"Held: {held}",
        f"Cap: {cap}",
        "External sends: 0",
        "HubSpot writes: 0",
        "",
        "## Hold counts",
    ]
    hold_counts: Dict[str, int] = {}
    for row in candidates:
        for reason in str(row.get("hold_reason") or "").split(";"):
            if reason:
                hold_counts[reason] = hold_counts.get(reason, 0) + 1
    for reason, count in sorted(hold_counts.items()):
        report.append(f"- {reason}: {count}")
    (args.out_dir / "qa_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cap", type=int, default=3)
    parser.add_argument("--scan-limit", type=int, default=100)
    parser.add_argument("--ledger-dir", type=Path, default=LEDGER_DIR_DEFAULT)
    args = parser.parse_args()
    receipt = build(args)
    print(
        "APPROVAL_PILOT_BUILT "
        f"deals_read={receipt['deals_read']} candidates={receipt['candidates']} "
        f"ready={receipt['ready_for_approval']} held={receipt['held']} "
        f"cap={receipt['cap']} sends=0 hubspot_writes=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
