#!/usr/bin/env python3
"""Executable post-delivery review for the sanitized Charles handoff receipt."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PLAN_MARKERS = (
    "PLAN VERDICT: PASS",
    "Exact Dedupe Method",
    "Gmail Source-of-Truth Verification",
    "Downstream Acceptance Boundary",
    "machine_install_pending: true",
)
TRUE_FIELDS = (
    "aws_secret_exists",
    "aws_region_us_east_1",
    "gmail_sent_or_preexisting_exact",
    "sender_correct",
    "recipient_correct",
    "recipient_verified",
    "subject_exact",
    "body_exact",
    "sent_label_present",
    "tracking_bcc_present",
    "zero_attachments",
    "secret_values_absent",
    "machine_install_pending",
    "downstream_acceptance_pending",
)
FALSE_FIELDS = (
    "privacy_safe_events_verified",
    "approved_ob_company_access_verified",
    "open_skills_access_verified",
    "full_onboarding_complete",
)
FORBIDDEN = (
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    re.compile(r"(?i)\barn:aws:"),
    re.compile(r"\b[0-9]{12}\b"),
)


def evaluate(plan_path: Path, receipt_path: Path) -> tuple[bool, list[str], dict[str, Any]]:
    failures: list[str] = []
    plan = plan_path.read_text(encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for marker in PLAN_MARKERS:
        if marker.lower() not in plan.lower():
            failures.append(f"missing_plan_marker:{marker}")
    for field in TRUE_FIELDS:
        if receipt.get(field) is not True:
            failures.append(f"receipt_not_true:{field}")
    for field in FALSE_FIELDS:
        if receipt.get(field) is not False:
            failures.append(f"receipt_not_false:{field}")
    for field, expected in (
        ("duplicate_count_before", 1),
        ("sent_exact_match_count", 1),
        ("iam_changes_count", 0),
        ("external_actions_count", 0),
    ):
        if receipt.get(field) != expected:
            failures.append(f"receipt_count_mismatch:{field}")
    if receipt.get("status") != "preexisting_exact":
        failures.append("receipt_status_not_preexisting_exact")
    for pattern in FORBIDDEN:
        if pattern.search(plan) or pattern.search(receipt_path.read_text(encoding="utf-8")):
            failures.append("forbidden_durable_identifier_detected")
            break
    return not failures, failures, receipt


def write_review(output_path: Path, plan_path: Path, receipt_path: Path) -> int:
    passed, failures, receipt = evaluate(plan_path, receipt_path)
    if passed:
        lines = [
            "POST-SEND RINGER REVIEW: PASS",
            "delivery_stage: verified_existing_sent_receipt",
            "external_send_this_round: false",
            "duplicate_count_before: 1",
            "sent_exact_match_count: 1",
            "sender_recipient_subject_body: verified",
            "sent_label_bcc_attachments_secret_free: verified",
            "iam_changes_count: 0",
            "machine_install_pending: true",
            "downstream_acceptance_pending: true",
            "privacy_safe_events_verified: false",
            "approved_ob_company_access_verified: false",
            "open_skills_access_verified: false",
            "full_onboarding_complete: false",
            "acceptance_scope: delivery handoff only; parent-gated follow-up owns end-to-end access proof",
        ]
        code = 0
    else:
        lines = ["POST-SEND RINGER REVIEW: BLOCK"]
        lines.extend(f"WHY: {failure}" for failure in failures)
        code = 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    passed, failures, _ = evaluate(args.plan, args.receipt)
    if args.check:
        if passed:
            print("PASS: post-send review proves the verified existing Sent receipt and downstream boundary")
            return 0
        for failure in failures:
            print(f"WHY: {failure}")
        return 1
    if args.output is None:
        parser.error("--output is required unless --check is used")
    return write_review(args.output, args.plan, args.receipt)


if __name__ == "__main__":
    raise SystemExit(main())
