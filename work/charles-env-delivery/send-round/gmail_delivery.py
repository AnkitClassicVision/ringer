#!/usr/bin/env python3
"""Sanitized, dedupe-first Gmail delivery coordinator for the Charles setup handoff.

The script keeps recipient addresses, message IDs, OAuth material, and API bodies
in memory only. It writes receipts containing booleans/counts and safe reason codes.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import email
import email.policy
import io
import json
import os
import re
import subprocess
import sys
import time
from email.mime.text import MIMEText
from email.utils import getaddresses
from pathlib import Path
from typing import Any, Iterable

GMAIL_SKILL_DIR = Path("/home/ankit114/.claude/skills/gmail")
if str(GMAIL_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(GMAIL_SKILL_DIR))

import read_inbox  # type: ignore  # local skill module

SENDER = f"ankit{'@'}mybcat.com"
TRACKING_BCC = f"23344341{'@'}bcc.hubspot.com"
SUBJECT = "Finish your Claude Code capture setup"
SECRET_NAME = "ob-company/ingest/charles-env"
TARGET_PATH = "~/.config/ob_company/charles.env"
AWS_REGION = "us-east-1"
AWS_SECRET_ID = SECRET_NAME
COMPANY_DOMAIN = "mybcat.com"

FORBIDDEN_CONTENT_PATTERNS = (
    re.compile(r"\bOB_COMPANY_(?:INGEST_TOKEN|ENDPOINT|EMPLOYEE_ID)\b", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]+", re.I),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
)


def quiet_call(fn):
    """Run a Gmail/API call while discarding library stdout/stderr."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn()


def decode_b64(data: str) -> str:
    try:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="replace")
    except Exception:
        return ""


def plain_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    if payload.get("mimeType") == "text/plain":
        data = (payload.get("body") or {}).get("data")
        if data:
            chunks.append(decode_b64(data))
    for part in payload.get("parts") or []:
        chunks.append(plain_text(part))
    return "".join(chunks)


def headers(message: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("name", "")).lower(): str(item.get("value", ""))
        for item in (message.get("payload") or {}).get("headers") or []
    }


def addresses(value: str) -> list[str]:
    return [address.lower() for _, address in getaddresses([value]) if "@" in address]


def has_attachment(payload: dict[str, Any]) -> bool:
    if payload.get("filename") or (payload.get("body") or {}).get("attachmentId"):
        return True
    return any(has_attachment(part) for part in payload.get("parts") or [])


def secret_free_text(text: str) -> bool:
    return not any(pattern.search(text) for pattern in FORBIDDEN_CONTENT_PATTERNS)


def normalize_body(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def load_body(path: Path) -> str:
    return normalize_body(path.read_text(encoding="utf-8"))


def build_service():
    return quiet_call(read_inbox.get_gmail_service)


def execute(request):
    return quiet_call(lambda: request.execute(num_retries=5))


def search_full(service, query: str, max_pages: int = 5) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    token: str | None = None
    for _ in range(max_pages):
        kwargs: dict[str, Any] = {"userId": "me", "q": query, "maxResults": 100}
        if token:
            kwargs["pageToken"] = token
        result = execute(service.users().messages().list(**kwargs))
        refs.extend(result.get("messages") or [])
        token = result.get("nextPageToken")
        if not token:
            break
    messages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in refs:
        message_id = str(ref.get("id", ""))
        if not message_id or message_id in seen:
            continue
        seen.add(message_id)
        messages.append(execute(service.users().messages().get(userId="me", id=message_id, format="full")))
    return messages


def profile_email(service) -> str:
    profile = execute(service.users().getProfile(userId="me"))
    return str(profile.get("emailAddress", "")).strip().lower()


def candidate_addresses(service) -> tuple[list[str], dict[str, int]]:
    queries = (
        ("name", 'in:anywhere "Charles" newer_than:365d'),
        ("package", 'in:anywhere "charles-claude-code-capture-v5" newer_than:365d'),
        ("subject", 'in:anywhere subject:"Claude Code" "Charles" newer_than:365d'),
        ("env", 'in:anywhere "charles.env" newer_than:365d'),
    )
    candidates: dict[str, dict[str, int]] = {}

    def record(address: str) -> dict[str, int]:
        return candidates.setdefault(
            address,
            {
                "score": 0,
                "inbound": 0,
                "display_name_hits": 0,
                "package_hits": 0,
                "subject_hits": 0,
                "env_hits": 0,
            },
        )

    for label, query in queries:
        seen_ids: set[str] = set()
        for message in search_full(service, query):
            message_id = str(message.get("id", ""))
            if message_id in seen_ids:
                continue
            seen_ids.add(message_id)
            hdr = headers(message)
            body = plain_text(message.get("payload") or {})
            subject = hdr.get("subject", "")
            labels = set(message.get("labelIds") or [])
            sent = "SENT" in labels
            from_pairs = getaddresses([hdr.get("from", "")])
            to_pairs = getaddresses([hdr.get("to", "")])
            searchable = f"{subject}\n{body}".lower()
            for display_name, address in from_pairs:
                address = address.strip().lower()
                if not address or "@" not in address or address == SENDER:
                    continue
                local, _, domain = address.partition("@")
                if domain != COMPANY_DOMAIN:
                    continue
                name_hit = "charles" in display_name.lower() or "charles" in local.lower()
                if name_hit:
                    candidate = record(address)
                    candidate["score"] += 3 if not sent else 2
                    candidate["inbound"] += int(not sent)
                    candidate["display_name_hits"] += int("charles" in display_name.lower())
                    candidate[f"{label}_hits"] = candidate.get(f"{label}_hits", 0) + 1
            for display_name, address in to_pairs:
                address = address.strip().lower()
                if not address or "@" not in address or address == SENDER:
                    continue
                local, _, domain = address.partition("@")
                if domain != COMPANY_DOMAIN:
                    continue
                name_hit = "charles" in display_name.lower() or "charles" in local.lower()
                if name_hit:
                    candidate = record(address)
                    candidate["score"] += 3 if name_hit else 1
                    candidate["display_name_hits"] += int("charles" in display_name.lower())
                    candidate[f"{label}_hits"] = candidate.get(f"{label}_hits", 0) + 1
    verified = [
        address
        for address, candidate in candidates.items()
        if candidate["inbound"]
        or candidate["display_name_hits"]
        or candidate.get("package_hits", 0)
        or candidate.get("subject_hits", 0)
        or candidate.get("env_hits", 0)
    ]
    scores = {address: candidate["score"] for address, candidate in candidates.items()}
    return sorted(verified), scores


def matching_sent(message: dict[str, Any], recipient: str, body: str) -> bool:
    hdr = headers(message)
    labels = set(message.get("labelIds") or [])
    if "SENT" not in labels:
        return False
    if hdr.get("subject", "") != SUBJECT:
        return False
    if recipient not in addresses(hdr.get("to", "")):
        return False
    text = normalize_body(plain_text(message.get("payload") or {}))
    return SECRET_NAME in text and TARGET_PATH in text


def exact_sent_messages(service, recipient: str, body: str) -> list[dict[str, Any]]:
    query = f'in:sent subject:"{SUBJECT}" "{SECRET_NAME}"'
    return [message for message in search_full(service, query) if matching_sent(message, recipient, body)]


def message_checks(message: dict[str, Any], recipient: str, body: str, mailbox: str) -> dict[str, Any]:
    hdr = headers(message)
    text = normalize_body(plain_text(message.get("payload") or {}))
    from_addresses = addresses(hdr.get("from", ""))
    to_addresses = addresses(hdr.get("to", ""))
    labels = set(message.get("labelIds") or [])
    return {
        "sender_correct": mailbox == SENDER and SENDER in from_addresses,
        "recipient_correct": to_addresses == [recipient] or (recipient in to_addresses and len(to_addresses) == 1),
        "subject_exact": hdr.get("subject", "") == SUBJECT,
        "body_exact": text == body,
        "sent_label_present": "SENT" in labels,
        "zero_attachments": not has_attachment(message.get("payload") or {}),
        "secret_values_absent": text == body and secret_free_text(text),
        "tracking_bcc_present": TRACKING_BCC in addresses(hdr.get("bcc", "")),
    }


def aws_secret_exists() -> bool:
    env = os.environ.copy()
    env["HOME"] = "/home/ankit114"
    command = [
        "aws",
        "secretsmanager",
        "describe-secret",
        "--secret-id",
        AWS_SECRET_ID,
        "--region",
        AWS_REGION,
        "--query",
        "Name",
        "--output",
        "text",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, env=env)
    except Exception:
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def base_receipt() -> dict[str, Any]:
    return {
        "aws_secret_exists": False,
        "aws_region_us_east_1": False,
        "duplicate_count_before": -1,
        "gmail_sent_or_preexisting_exact": False,
        "sent_exact_match_count": 0,
        "sender_correct": False,
        "recipient_correct": False,
        "subject_exact": False,
        "body_exact": False,
        "sent_label_present": False,
        "zero_attachments": False,
        "secret_values_absent": False,
        "iam_changes_count": 0,
        "machine_install_pending": True,
        "downstream_acceptance_pending": True,
        "privacy_safe_events_verified": False,
        "approved_ob_company_access_verified": False,
        "open_skills_access_verified": False,
        "full_onboarding_complete": False,
        "external_actions_count": 0,
        "status": "block",
        "reason_code": "not_started",
    }


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def emit(receipt: dict[str, Any]) -> None:
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))


def preflight(body_path: Path, receipt_path: Path) -> int:
    body = load_body(body_path)
    receipt = base_receipt()
    receipt["aws_secret_exists"] = aws_secret_exists()
    receipt["aws_region_us_east_1"] = receipt["aws_secret_exists"]
    if not receipt["aws_secret_exists"]:
        receipt["reason_code"] = "aws_secret_metadata_missing"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 1
    try:
        service = build_service()
        mailbox = profile_email(service)
        recipients, scores = candidate_addresses(service)
    except Exception as exc:
        receipt["reason_code"] = f"gmail_read_failed_{type(exc).__name__}"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 1

    receipt["sender_correct"] = mailbox == SENDER
    receipt["recipient_verified"] = len(recipients) == 1
    if len(recipients) != 1:
        receipt["reason_code"] = "recipient_resolution_ambiguous_or_missing"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 1

    recipient = recipients[0]
    matches = exact_sent_messages(service, recipient, body)
    count = len(matches)
    receipt["duplicate_count_before"] = count
    if count > 1:
        receipt["reason_code"] = "duplicate_count_ambiguous"
    elif count == 1:
        checks = message_checks(matches[0], recipient, body, mailbox)
        receipt.update(checks)
        receipt["sent_exact_match_count"] = 1
        if all(checks.values()):
            receipt["gmail_sent_or_preexisting_exact"] = True
            receipt["status"] = "preexisting_exact"
            receipt["reason_code"] = "exact_preexisting_receipt"
        else:
            receipt["reason_code"] = "preexisting_match_failed_source_checks"
    else:
        receipt.update(
            {
                "recipient_correct": True,
                "subject_exact": True,
                "body_exact": True,
                "zero_attachments": True,
                "secret_values_absent": secret_free_text(body),
                "status": "ready_to_send",
                "reason_code": "fresh_dedupe_count_zero",
            }
        )
    write_receipt(receipt_path, receipt)
    emit(receipt)
    return 0 if receipt["status"] in {"ready_to_send", "preexisting_exact"} else 1


def send_once(body_path: Path, receipt_path: Path) -> int:
    body = load_body(body_path)
    receipt = base_receipt()
    receipt["aws_secret_exists"] = aws_secret_exists()
    receipt["aws_region_us_east_1"] = receipt["aws_secret_exists"]
    if not receipt["aws_secret_exists"]:
        receipt["reason_code"] = "aws_secret_metadata_missing"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 1
    try:
        service = build_service()
        mailbox = profile_email(service)
        recipients, scores = candidate_addresses(service)
    except Exception as exc:
        receipt["reason_code"] = f"gmail_read_failed_{type(exc).__name__}"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 1

    receipt["sender_correct"] = mailbox == SENDER
    receipt["recipient_verified"] = len(recipients) == 1
    if mailbox != SENDER or len(recipients) != 1:
        receipt["reason_code"] = "sender_or_recipient_not_verified"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 1

    recipient = recipients[0]
    matches = exact_sent_messages(service, recipient, body)
    receipt["duplicate_count_before"] = len(matches)
    if matches:
        receipt["reason_code"] = "fresh_dedupe_not_zero_no_send"
        if len(matches) == 1:
            checks = message_checks(matches[0], recipient, body, mailbox)
            receipt.update(checks)
            receipt["sent_exact_match_count"] = 1
            receipt["gmail_sent_or_preexisting_exact"] = all(checks.values())
            receipt["status"] = "preexisting_exact" if receipt["gmail_sent_or_preexisting_exact"] else "block"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 0 if receipt["status"] == "preexisting_exact" else 1

    if not secret_free_text(body):
        receipt["reason_code"] = "locked_body_failed_secret_free_scan"
        write_receipt(receipt_path, receipt)
        emit(receipt)
        return 1

    message = MIMEText(body, "plain", "utf-8")
    message["to"] = recipient
    message["from"] = SENDER
    message["subject"] = SUBJECT
    message["bcc"] = TRACKING_BCC
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    receipt["external_actions_count"] = 1
    send_error: str | None = None
    try:
        sent_result = execute(service.users().messages().send(userId="me", body={"raw": raw}))
    except Exception as exc:
        send_error = type(exc).__name__
        sent_result = {}

    # Never retry the send. Reconstruct state with a read-only search even when
    # the send call raised after the provider may have accepted the request.
    for attempt in range(3):
        try:
            matches = exact_sent_messages(service, recipient, body)
        except Exception as exc:
            matches = []
            if send_error is None:
                send_error = type(exc).__name__
        if matches or attempt == 2:
            break
        time.sleep(2)

    receipt["sent_exact_match_count"] = len(matches)
    if len(matches) == 1:
        checks = message_checks(matches[0], recipient, body, mailbox)
        receipt.update(checks)
        receipt["gmail_sent_or_preexisting_exact"] = all(checks.values())
        receipt["status"] = "sent_verified" if receipt["gmail_sent_or_preexisting_exact"] else "block"
        receipt["reason_code"] = "sent_once_and_read_back" if send_error is None else "send_response_error_but_receipt_verified"
    elif send_error is not None:
        receipt["reason_code"] = "send_response_error_state_not_reconstructed"
    elif len(matches) == 0:
        receipt["reason_code"] = "send_returned_but_exact_receipt_missing"
    else:
        receipt["reason_code"] = "post_send_exact_count_ambiguous"
    write_receipt(receipt_path, receipt)
    emit(receipt)
    return 0 if receipt["status"] == "sent_verified" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "send"), required=True)
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--receipt-file", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "preflight":
        return preflight(args.body_file, args.receipt_file)
    return send_once(args.body_file, args.receipt_file)


if __name__ == "__main__":
    raise SystemExit(main())
