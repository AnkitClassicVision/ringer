#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
import re
import sys
from pathlib import Path

REQUIRED_INTAKE = {
    "practice_name": "Vintage Optical",
    "website_url": "https://www.vintageopt.com/",
    "locations": "605 S Main St, Morton, IL 61550",
    "owner_intent": "grow",
    "data_mode": "public_only",
    "existing_client_check": "not an existing MyBCAT client",
}
PUBLIC_EIDS = {f"E{i:03d}" for i in range(1, 33)} | {"E037"}
DECISION_EIDS = {"E033", "E034", "E035", "E036"}
EID_RE = re.compile(r"\bE\d{3}\b")


class HTMLAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href", "")
            self._anchor_text = []

    def handle_data(self, data):
        self.text.append(data)
        if self._href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.links.append(("".join(self._anchor_text).strip(), self._href))
            self._href = None
            self._anchor_text = []


def why(msg: str) -> None:
    print(f"WHY: {msg}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--research-scores", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--notes", required=True)
    args = ap.parse_args()
    dest = Path(args.dest)
    failures: list[str] = []
    required = [
        dest / "intake.md", dest / "data/evidence.md", dest / "data/sources.json",
        dest / "scores.json", dest / "onepager.html", dest / "runlog.md", Path(args.notes),
    ]
    for p in required:
        if not p.is_file(): failures.append(f"missing required output: {p}")
    if failures:
        for f in failures: why(f)
        return 1

    full_pdf = dest / "competitive-growth-analysis-full.pdf"
    readme = dest / "README.md"
    if digest(full_pdf) != "b7f8afac2316ce41dc4d8244edbfdf0eec519539020a641cda576822a6715222":
        failures.append("pre-existing full PDF was modified")
    if digest(readme) != "ef6f7cd86d964b89ad1e219b0975be223cc14db0138257f26a6502d4efa8334e":
        failures.append("final README was modified after closure")

    intake = (dest / "intake.md").read_text(encoding="utf-8", errors="replace")
    for key, value in REQUIRED_INTAKE.items():
        if not re.search(rf"(?im)^\s*{re.escape(key)}\s*:\s*{re.escape(value)}\s*$", intake):
            failures.append(f"intake missing exact field {key}: {value}")

    try:
        final_scores = json.loads((dest / "scores.json").read_text(encoding="utf-8"))
        research_scores = json.loads(Path(args.research_scores).read_text(encoding="utf-8"))
        if final_scores != research_scores:
            failures.append("scores.json is not byte-semantically identical to the accepted Ringer research scores")
    except Exception as e:
        failures.append(f"score JSON parse/compare failed: {e}")
        final_scores = {}
    scores = final_scores.get("scores", {}) if isinstance(final_scores, dict) else {}
    if scores.get("room_to_win_score") != 100 - scores.get("competitive_pressure_index", -999):
        failures.append("Room to Win does not equal 100 - CPI")

    with Path(args.ledger).open(encoding="utf-8", newline="") as f:
        ledger = {r["claim_id"]: r["url"] for r in csv.DictReader(f)}
    evidence = (dest / "data/evidence.md").read_text(encoding="utf-8", errors="replace")
    evidence_ids = set(EID_RE.findall(evidence))
    if len(evidence_ids & PUBLIC_EIDS) < 20:
        failures.append(f"evidence.md has only {len(evidence_ids & PUBLIC_EIDS)} public evidence IDs; need at least 20")
    if DECISION_EIDS & evidence_ids:
        failures.append("evidence.md presents decision rows E033-E036 as source evidence")
    for heading in ["# Public Evidence", "## Verified facts", "## Directional evidence", "## Working hypotheses", "## Unknowns"]:
        if heading.lower() not in evidence.lower():
            failures.append(f"evidence.md missing section: {heading}")

    try:
        sources = json.loads((dest / "data/sources.json").read_text(encoding="utf-8"))
    except Exception as e:
        failures.append(f"sources.json does not parse: {e}")
        sources = []
    if not isinstance(sources, list) or len(sources) < 20:
        failures.append("sources.json must contain at least 20 source objects")
        sources = []
    seen_ids = set()
    for i, row in enumerate(sources):
        if not isinstance(row, dict):
            failures.append(f"sources.json row {i} is not an object")
            continue
        eid, url = row.get("claim_id"), row.get("url")
        if eid not in PUBLIC_EIDS:
            failures.append(f"sources.json row {i} uses non-public or unknown ID {eid}")
        elif ledger.get(eid) != url:
            failures.append(f"sources.json URL mismatch for {eid}")
        seen_ids.add(eid)
        for field in ["accessed", "confidence", "source_type"]:
            if not row.get(field): failures.append(f"sources.json row {i} missing {field}")

    html = (dest / "onepager.html").read_text(encoding="utf-8", errors="replace")
    parser = HTMLAudit(); parser.feed(html)
    visible = " ".join(" ".join(parser.text).split())
    for phrase in ["The Read", "Your Market", "Your Competition", "Your Opportunity", "First 30 Days", "Vintage Optical", "Room to Win", "Higher = better", "Confidence C", "Public data only"]:
        if phrase.lower() not in visible.lower():
            failures.append(f"onepager missing visible phrase: {phrase}")
    for score in ["44", "72", "66"]:
        if not re.search(rf"\b{score}\b", visible): failures.append(f"onepager missing client score {score}")
    if "Competitive Pressure Index".lower() in visible.lower():
        failures.append("onepager exposes the high-worse Competitive Pressure Index instead of Room to Win")
    if "SAMPLE" in visible.upper() or "ILLUSTRATIVE" in visible.upper():
        failures.append("real-data onepager still carries SAMPLE/ILLUSTRATIVE labeling")
    if "—" in html:
        failures.append("onepager contains em dashes")
    if any(x in html.lower() for x in ["lorem ipsum", "undefined", "api_key", "password:", "bearer "]):
        failures.append("onepager contains a placeholder or secret-like literal")
    if re.search(r"\$\s*\d[\d,.]*\s*[kKmM]?\s*/?\s*(?:yr|year)", visible):
        failures.append("onepager contains a public-data revenue forecast")
    if not re.search(r"@page\s*\{[^}]*size\s*:\s*(?:letter|8\.5in\s+11in)", html, re.I | re.S):
        failures.append("onepager CSS does not declare Letter page size")

    anchor_map: dict[str, set[str]] = {}
    for text, href in parser.links:
        for eid in EID_RE.findall(text):
            anchor_map.setdefault(eid, set()).add(href)
    visible_eids = set(EID_RE.findall(visible))
    if len(visible_eids) < 12:
        failures.append(f"onepager shows only {len(visible_eids)} evidence IDs; need at least 12")
    if DECISION_EIDS & visible_eids:
        failures.append("onepager uses E033-E036 as source evidence; use H labels for hypotheses")
    for eid in visible_eids:
        if eid not in anchor_map:
            failures.append(f"visible evidence ID {eid} is not clickable")
        elif anchor_map[eid] != {ledger.get(eid)}:
            failures.append(f"visible evidence ID {eid} does not link only to its exact ledger URL")
    if not {"H1", "H2", "H3"}.issubset(set(re.findall(r"\bH[1-3]\b", visible))):
        failures.append("onepager must label all three actions as H1-H3 working hypotheses")

    runlog = (dest / "runlog.md").read_text(encoding="utf-8", errors="replace")
    for phrase in ["Ringer research", "Chromium probe", "Builder verification", "Render status", "Human delivery gate", "No external delivery occurred", "Decision residue"]:
        if phrase.lower() not in runlog.lower(): failures.append(f"runlog missing: {phrase}")
    notes = Path(args.notes).read_text(encoding="utf-8", errors="replace")
    if "verification" not in notes.lower() or "files changed" not in notes.lower():
        failures.append("notes.md lacks files changed and verification sections")

    if failures:
        for f in failures: why(f)
        return 1
    print(f"PASS: canonical build valid; {len(visible_eids)} clickable E-IDs, {len(sources)} source rows, scores reconciled, pre-existing files preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
