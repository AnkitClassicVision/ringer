#!/usr/bin/env python3
"""Validate one MyBCAT weekly founder-exception review report."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_WORDS = 1500
REQUIRED_HEADINGS = (
    "Summary",
    "Decision",
    "Findings",
    "Owner-Outcome-Date-Risk-Visibility",
    "Clean",
    "Safety",
    "Assumptions",
)
FINDING_FIELDS = (
    "Evidence:",
    "Business Impact:",
    "Recommended Owner:",
    "Outcome:",
    "Date:",
    "Risk:",
    "Visibility:",
    "Founder Decision Required:",
    "Priority:",
    "Confidence:",
)
DECISIONS = (
    "NO_FOUNDER_ACTION",
    "FOUNDER_DECISION_REQUIRED",
    "OPERATOR_FOLLOWUP",
)
OODRV_FIELDS = ("Owner:", "Outcome:", "Date:", "Risk:", "Visibility:")
STRONG_SETUP_FIELDS = (
    "Opportunity Spine:",
    "Revenue Proof Rubric:",
    "Permission Matrix:",
    "Model Routing Policy:",
    "RACI:",
    "Run Card:",
    "Blocked promotion:",
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\d)")
SECRET_RE = re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._~+/=-]{12,}|(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*\S+)"
)


def fail(name: str, detail: str) -> str:
    return f"FAIL [{name}]: {detail}"


def words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def has_heading(text: str, heading: str) -> bool:
    return bool(re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.IGNORECASE | re.MULTILINE))


def section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def validate(path: Path, surface: str, require_strong_setup: bool = False) -> list[str]:
    failures: list[str] = []
    if not path.is_file():
        return [fail("missing_report", f"{path} does not exist")]
    if path.stat().st_size == 0:
        return [fail("empty_report", f"{path} is empty")]

    text = path.read_text(encoding="utf-8", errors="replace")
    if words(text) > MAX_WORDS:
        failures.append(fail("too_long", f"report exceeds {MAX_WORDS} words"))
    if not re.search(r"^#\s+Weekly Founder Exception Review\s*$", text, re.IGNORECASE | re.MULTILINE):
        failures.append(fail("missing_title", "report must start with '# Weekly Founder Exception Review'"))
    for heading in REQUIRED_HEADINGS:
        if not has_heading(text, heading):
            failures.append(fail("missing_section", f"missing '## {heading}'"))

    summary = section(text, "Summary")
    summary_lines = [line for line in summary.splitlines() if line.strip()]
    if len(summary_lines) > 3:
        failures.append(fail("summary_too_long", "Summary must be no more than 3 non-empty lines"))

    decision = section(text, "Decision")
    decision_matches = re.findall(r"^DECISION:\s*([A-Z_]+)\s*$", decision, re.MULTILINE)
    if len(decision_matches) != 1 or decision_matches[0] not in DECISIONS:
        failures.append(fail("bad_decision", f"Decision must contain exactly one DECISION line using {', '.join(DECISIONS)}"))

    findings = section(text, "Findings")
    if not findings:
        failures.append(fail("missing_findings_body", "Findings section has no content"))
    elif re.search(r"^###\s+Finding:", findings, re.IGNORECASE | re.MULTILINE):
        blocks = re.split(r"(?=^###\s+Finding:)", findings, flags=re.IGNORECASE | re.MULTILINE)
        for index, block in enumerate([item for item in blocks if item.strip()], start=1):
            for field in FINDING_FIELDS:
                if field.lower() not in block.lower():
                    failures.append(fail("finding_missing_field", f"finding {index} is missing {field}"))
            if "Evidence:" in block and not re.search(r"\b[\w./-]+:\d+\b", block):
                failures.append(fail("finding_missing_line", f"finding {index} evidence must cite file:line"))
            if not re.search(r"Founder Decision Required:\s*(yes|no)\b", block, re.IGNORECASE):
                failures.append(fail("finding_bad_founder_gate", f"finding {index} must set Founder Decision Required to yes or no"))
            if not re.search(r"Priority:\s*P[0-3]\b", block, re.IGNORECASE):
                failures.append(fail("finding_bad_priority", f"finding {index} priority must be P0, P1, P2, or P3"))
            if not re.search(r"Confidence:\s*(high|medium|low)\b", block, re.IGNORECASE):
                failures.append(fail("finding_bad_confidence", f"finding {index} confidence must be high, medium, or low"))
    elif "no findings" not in findings.lower():
        failures.append(fail("findings_not_explicit", "Findings must contain a Finding block or explicitly say No findings"))

    oodrv = section(text, "Owner-Outcome-Date-Risk-Visibility")
    for field in OODRV_FIELDS:
        if field.lower() not in oodrv.lower():
            failures.append(fail("oodrv_missing_field", f"Owner-Outcome-Date-Risk-Visibility is missing {field}"))

    safety = section(text, "Safety")
    if not re.search(r"^External actions taken:\s*0\s*$", safety, re.IGNORECASE | re.MULTILINE):
        failures.append(fail("external_action_receipt", "Safety must say 'External actions taken: 0'"))
    if not re.search(r"^Sensitive data included:\s*no\s*$", safety, re.IGNORECASE | re.MULTILINE):
        failures.append(fail("sensitive_data_receipt", "Safety must say 'Sensitive data included: no'"))

    if require_strong_setup:
        if not has_heading(text, "Strong Setup Gate"):
            failures.append(fail("missing_strong_setup", "Demand Protection review must include '## Strong Setup Gate'"))
        strong_setup = section(text, "Strong Setup Gate")
        if not re.search(r"^Current level:\s*L1\b", strong_setup, re.IGNORECASE | re.MULTILINE):
            failures.append(fail("bad_current_level", "Strong Setup Gate must state 'Current level: L1 read-only'"))
        for field in STRONG_SETUP_FIELDS:
            if field.lower() not in strong_setup.lower():
                failures.append(fail("strong_setup_missing_field", f"Strong Setup Gate is missing {field}"))
        if not re.search(r"^HubSpot role:\s*aggregate/control-plane\b", strong_setup, re.IGNORECASE | re.MULTILINE):
            failures.append(fail("bad_hubspot_role", "Strong Setup Gate must keep HubSpot as aggregate/control-plane"))

    if EMAIL_RE.search(text):
        failures.append(fail("email_leak", "report contains an email address"))
    if PHONE_RE.search(text):
        failures.append(fail("phone_leak", "report contains a phone-number-shaped value"))
    if SECRET_RE.search(text):
        failures.append(fail("secret_like_leak", "report contains a secret-like assignment or bearer value"))
    if "{{" in surface or "}}" in surface:
        failures.append(fail("placeholder_unfilled", "surface placeholder was not filled"))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a weekly founder-exception review report.")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--surface", required=True)
    parser.add_argument("--require-strong-setup", action="store_true")
    args = parser.parse_args()
    failures = validate(args.report, args.surface, args.require_strong_setup)
    if failures:
        for item in failures:
            print(item)
        return 1
    print(f"PASS [weekly_founder_exception]: {args.report} is decision-ready and privacy-safe for {args.surface}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
