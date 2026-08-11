#!/usr/bin/env python3
"""Fail-closed validator for the Charles env delivery plan."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def normalized(value: str) -> str:
    return re.sub(r"\\s+", " ", value).strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--body", required=True)
    args = parser.parse_args()

    failures: list[str] = []
    plan_path = Path(args.plan)
    evidence_path = Path(args.evidence)
    body_path = Path(args.body)

    if not plan_path.is_file():
        fail(failures, f"WHY: missing delivery plan: {plan_path}")
    if not evidence_path.is_file():
        fail(failures, f"WHY: missing sanitized evidence: {evidence_path}")
    if not body_path.is_file():
        fail(failures, f"WHY: missing locked email body: {body_path}")
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        return 1

    plan = plan_path.read_text(encoding="utf-8", errors="replace")
    body = body_path.read_text(encoding="utf-8", errors="replace")
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: WHY: sanitized evidence is not valid JSON: {exc.msg}")
        return 1

    if not plan.strip():
        fail(failures, "WHY: delivery plan is empty")

    required_evidence = {
        "aws_secret_exists": True,
        "aws_region_us_east_1": True,
        "package_v5_present": True,
        "passbolt_route_failed": True,
        "passbolt_sent_receipt": False,
        "google_chat_route_failed": True,
        "google_chat_sent_receipt": False,
        "gmail_selected_route": True,
        "iam_changes_allowed": False,
        "machine_install_pending": True,
        "downstream_acceptance_pending": True,
        "privacy_safe_events_verified": False,
        "approved_ob_company_access_verified": False,
        "open_skills_access_verified": False,
        "full_onboarding_complete": False,
    }
    for key, expected in required_evidence.items():
        if evidence.get(key) is not expected:
            fail(failures, f"WHY: evidence invariant {key} must be {str(expected).lower()}")

    lowered = plan.lower()
    plan_norm = normalized(plan)
    required_markers = [
        "delivery plan",
        "aws_secret_exists: true",
        "us-east-1",
        "ob-company/ingest/charles-env",
        "charles-claude-code-capture-v5",
        "passbolt",
        "google chat",
        "gmail",
        "one-time",
        "duplicate_count_before",
        "sent_exact_match_count",
        "sender_correct",
        "recipient_correct",
        "subject_exact",
        "body_exact",
        "sent_label_present",
        "zero_attachments",
        "ambiguous",
        "stop",
        "block",
        "downstream",
        "privacy-safe",
        "ob_company",
        "open skills",
        "full onboarding",
    ]
    for marker in required_markers:
        if marker not in lowered:
            fail(failures, f"WHY: plan is missing required invariant marker: {marker}")

    body_norm = normalized(body)
    if body_norm not in plan_norm:
        fail(failures, "WHY: plan does not contain the locked plain-text email body exactly")
    if not re.search(r"subject:\s*[`\"']?\s*finish your claude code capture setup", lowered):
        fail(failures, "WHY: plan does not state the exact subject")

    if "no iam" not in lowered or "aws mutation" not in lowered:
        fail(failures, "WHY: plan must explicitly prohibit IAM and AWS mutation")
    if not re.search(r"iam_changes_count\s*[:=]\s*0\b", lowered):
        fail(failures, "WHY: plan must set iam_changes_count to zero")
    if not re.search(r"machine_install_pending\s*[:=]\s*true\b", lowered):
        fail(failures, "WHY: plan must set machine_install_pending to true")
    if "do not retry" not in lowered and "never retry" not in lowered:
        fail(failures, "WHY: plan must prohibit retrying an external send without a fresh dedupe read")

    # Reject sensitive or durable identifiers. The plan may contain labels and paths,
    # but never a recipient address, message id, ARN, account id, token, or secret value.
    forbidden_patterns = [
        (r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b", "email address"),
        (r"\\barn:aws:[^\\s`]+", "AWS ARN"),
        (r"\\b\\d{12}\\b", "12-digit account identifier"),
        (r"\\bAKIA[0-9A-Z]{16}\\b", "access-key material"),
        (r"\\bBearer\\s+[A-Za-z0-9._-]+", "bearer credential"),
        (r"\\b(?:secretstring|refresh_token|client_secret|private_key)\\b", "credential field"),
    ]
    for pattern, label in forbidden_patterns:
        if re.search(pattern, plan, flags=re.IGNORECASE):
            fail(failures, f"WHY: forbidden {label} detected in plan")

    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        return 1

    print("PASS: delivery plan contains current sanitized evidence, locked body, dedupe, verification, stop, and rollback invariants")
    print("WHY: no forbidden durable identifiers or credential patterns detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
