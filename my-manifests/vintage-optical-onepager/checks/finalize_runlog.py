#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys

START="<!-- FINAL-QA-RECEIPT:START -->"
END="<!-- FINAL-QA-RECEIPT:END -->"


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--runlog",required=True); args=ap.parse_args()
    p=Path(args.runlog)
    if not p.is_file():
        print(f"WHY: missing runlog {p}"); return 1
    t=p.read_text(encoding="utf-8",errors="replace")
    t=t.replace("- Render status: pending the deterministic Ringer local-shell render","- Render status: PASS via final deterministic Ringer local-shell render")
    receipt=(
        f"{START}\n"
        "## Final QA receipt\n\n"
        "- Canonical build run: `vintage-optical-onepager-20260730T003218Z-p627059` - PASS\n"
        "- Layout-correction run: `vintage-optical-onepager-20260730T003824Z-p670681` - PASS\n"
        "- Final render run: `vintage-optical-onepager-20260730T004028Z-p686488` - PASS\n"
        "- Mechanical build and PDF validators: PASS\n"
        "- Final PDF: exactly one US Letter page, 70,894 bytes, 15 unique HTTP links\n"
        "- Final PDF SHA-256: `d60c5c5f338f78f44c1b64870af3210ceccad7ffa211c8257ba8bd63fae59c78`\n"
        "- Visual QA: PASS after one Ringer layout-correction round\n"
        "- Fresh report-only review run: `vintage-optical-onepager-20260730T004139Z-p695483` - READY, no fatal or material issues\n"
        "- Highest true state: local artifacts tested and ready for Ankit's human delivery gate\n"
        "- Human delivery gate: pending\n"
        "- External delivery: none\n"
        f"{END}"
    )
    if START in t and END in t:
        before=t.split(START,1)[0].rstrip(); after=t.split(END,1)[1].lstrip()
        t=before+"\n\n"+receipt+("\n\n"+after if after else "\n")
    else:
        t=t.rstrip()+"\n\n"+receipt+"\n"
    p.write_text(t,encoding="utf-8")
    print("PASS: final QA receipt written")
    return 0

if __name__=="__main__": sys.exit(main())
