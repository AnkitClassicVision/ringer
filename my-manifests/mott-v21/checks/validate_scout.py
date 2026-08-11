#!/usr/bin/env python3
"""Validate the Mott v21 scout report.

Substance-strict, format-tolerant. Fails loudly with the exact reason so the
retry prompt has something to fix against.

Gates:
  1. report.md exists and is substantive.
  2. Every defect id F1..F14 carries an explicit verdict.
  3. At least MIN_GROUNDED verdicts are backed by a verbatim quote that really
     appears in the staged sources (the anti-hallucination gate).
  4. The report either names additional defects or explicitly says none.
  5. The read-only source snapshot was not modified.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFECT_IDS = [f"F{n}" for n in range(1, 15)]
VERDICT_WORDS = ("confirmed", "refuted", "unclear", "unverifiable", "partly", "partial")
MIN_REPORT_CHARS = 1500
MIN_GROUNDED = 6
MIN_QUOTE_CHARS = 20


def fail(reasons: list[str]) -> None:
    print("SCOUT CHECK FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    sys.exit(1)


def _decoded_strings(value: object, out: list[str]) -> None:
    """Collect every string inside a parsed JSON structure.

    JSON files store node bodies and prompts escaped, so a quote copied from the
    decoded value would not match the raw file text. Both forms must ground.
    """
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for key, nested in value.items():
            out.append(str(key))
            _decoded_strings(nested, out)
    elif isinstance(value, list):
        for nested in value:
            _decoded_strings(nested, out)


def load_sources(sources_dir: Path) -> str:
    if not sources_dir.is_dir():
        fail([f"sources directory missing: {sources_dir}"])
    blobs: list[str] = []
    for path in sorted(sources_dir.rglob("*")):
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        blobs.append(raw)
        if path.suffix.lower() == ".json":
            try:
                decoded: list[str] = []
                _decoded_strings(json.loads(raw), decoded)
                blobs.extend(decoded)
            except (json.JSONDecodeError, RecursionError):
                pass
    if not blobs:
        fail([f"sources directory is empty: {sources_dir}"])
    return "\n".join(blobs)


def normalize(text: str) -> str:
    """Collapse whitespace so quoting across line wraps still matches."""
    return re.sub(r"\s+", " ", text)


def verdict_lines(report: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if not any(word in lowered for word in VERDICT_WORDS):
            continue
        for defect_id in DEFECT_IDS:
            if re.search(rf"\b{defect_id}\b", line):
                found.setdefault(defect_id, line)
    return found


def quoted_spans(report: str) -> list[str]:
    spans: list[str] = []
    for pattern in (r"`([^`\n]{%d,})`" % MIN_QUOTE_CHARS,
                    r"\"([^\"\n]{%d,})\"" % MIN_QUOTE_CHARS,
                    r"“([^”\n]{%d,})”" % MIN_QUOTE_CHARS):
        spans.extend(re.findall(pattern, report))
    return spans


def snapshot_is_clean(repo: Path) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"could not run git status on {repo}: {exc}"
    if proc.returncode != 0:
        return False, f"git status failed on {repo}: {proc.stderr.strip()}"
    if proc.stdout.strip():
        return False, f"read-only snapshot was modified:\n{proc.stdout.strip()}"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--snapshot-repo", required=True, type=Path)
    args = parser.parse_args()

    reasons: list[str] = []

    if not args.report.is_file():
        fail([f"report not found: {args.report}"])
    report = args.report.read_text(encoding="utf-8", errors="replace")

    if len(report) < MIN_REPORT_CHARS:
        reasons.append(
            f"report is {len(report)} chars, needs at least {MIN_REPORT_CHARS}; "
            "this reads as a stub, not a review"
        )

    verdicts = verdict_lines(report)
    missing = [d for d in DEFECT_IDS if d not in verdicts]
    if missing:
        reasons.append(
            "no verdict line found for: "
            + ", ".join(missing)
            + f". Each of F1..F14 needs a line naming the id and one of "
            f"{'/'.join(VERDICT_WORDS[:4])}."
        )

    sources = normalize(load_sources(args.sources))
    spans = quoted_spans(report)
    grounded = [s for s in spans if normalize(s) in sources]
    if len(grounded) < MIN_GROUNDED:
        reasons.append(
            f"only {len(grounded)} of {len(spans)} quoted spans (>= {MIN_QUOTE_CHARS} chars) "
            f"actually appear in the staged sources; need at least {MIN_GROUNDED}. "
            "Quote the real file text verbatim instead of paraphrasing."
        )
        for span in spans:
            if normalize(span) not in sources:
                print(f"    ungrounded quote: {span[:90]!r}")

    lowered_report = report.lower()
    has_extra_section = bool(
        re.search(r"(additional|missed|further|new)\s+(defect|finding|issue)", lowered_report)
        or "no additional defect" in lowered_report
        or "no further defect" in lowered_report
    )
    if not has_extra_section:
        reasons.append(
            "report never addresses defects beyond F1..F14; add a section naming any "
            "additional findings, or state explicitly that there are none"
        )

    clean, detail = snapshot_is_clean(args.snapshot_repo)
    if not clean:
        reasons.append(detail)

    if reasons:
        fail(reasons)

    print("SCOUT CHECK PASSED")
    print(f"  verdicts: {len(verdicts)}/14")
    print(f"  grounded quotes: {len(grounded)}/{len(spans)}")
    print(f"  report chars: {len(report)}")
    print(f"  snapshot clean: yes ({args.snapshot_repo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
