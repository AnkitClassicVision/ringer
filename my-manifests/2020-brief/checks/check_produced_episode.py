#!/usr/bin/env python3
"""Ringer check for a freshly produced 20/20 Brief episode (pre-image gate).

Runs inside the produce-episode ringer task, BEFORE render_cards.py draws the
images and BEFORE the full voice checker (check_episode.py) runs as gate L1.
This gate proves the producer wrote the four contract files and honored the
research/teaser contracts:

- research.md: 5+ distinct URLs, a language swipe file with >= 3 quoted owner
  phrases, and an incumbent coverage log section.
- article.md: 1100-1900 words and a '## Sources' section.
- teaser-pack.md: all 6 channel sections and >= 4 join lines.
- images/cards.txt: non-empty, and every stat string appears verbatim in
  research.md (card-number-to-packet match; the deterministic card renderer
  typesets from this file).

Usage: python3 check_produced_episode.py <episode-dir>
Exit 0 = PASS. Exit 1 = FAIL (all WHYs printed).
"""

import re
import sys
from pathlib import Path

failures: list[str] = []


def fail(why: str) -> None:
    failures.append(why)


def check_research(ep: Path) -> str:
    p = ep / "research.md"
    if not p.exists():
        fail("research.md missing")
        return ""
    text = p.read_text(encoding="utf-8")
    urls = set(re.findall(r"https?://[^\s)\]|\"]+", text))
    if len(urls) < 5:
        fail(f"research.md has {len(urls)} distinct URLs, need >= 5")
    low = text.lower()
    if not ("language swipe" in low or "demand notes" in low or "owner language" in low):
        fail("research.md has no owner-language section (language swipe / demand notes)")
    m = re.search(
        r"^## .*(?:language swipe|demand notes|owner language).*?\n(.*?)(?=^## |\Z)",
        text, re.M | re.S | re.I,
    )
    quoted = re.findall(r'"([^"]{12,})"', m.group(1)) if m else []
    quoted += re.findall(r"“([^”]{12,})”", m.group(1)) if m else []
    if len(quoted) < 3:
        fail(f"language swipe file has {len(quoted)} quoted owner phrases, need >= 3")
    if not ("coverage" in low or "folklore" in low or "market gap" in low):
        fail("research.md has no incumbent coverage log section")
    return text


def check_article(ep: Path) -> None:
    p = ep / "article.md"
    if not p.exists():
        fail("article.md missing")
        return
    text = p.read_text(encoding="utf-8")
    words = len(text.split())
    if not 1100 <= words <= 1900:
        fail(f"article.md is {words} words, target 1200-1800 (allowed 1100-1900)")
    if not re.search(r"^## Sources", text, re.M):
        fail("article.md has no '## Sources' section")


def check_teasers(ep: Path) -> None:
    p = ep / "teaser-pack.md"
    if not p.exists():
        fail("teaser-pack.md missing")
        return
    text = p.read_text(encoding="utf-8")
    channels = {
        "LinkedIn personal": r"LinkedIn.*personal",
        "LinkedIn OBE page": r"LinkedIn.*OBE",
        "Facebook": r"Facebook",
        "X/Twitter thread": r"(X/Twitter|Twitter thread|X thread)",
        "Instagram carousel": r"Instagram",
        "Email teaser": r"[Ee]mail teaser",
    }
    for name, pat in channels.items():
        if not re.search(pat, text):
            fail(f"teaser-pack.md missing channel section: {name}")
    joins = len(re.findall(r"Apply to join", text))
    if joins < 4:
        fail(f"teaser-pack.md has {joins} join lines, need >= 4 (one per channel)")


def check_cards(ep: Path, research: str) -> None:
    p = ep / "images" / "cards.txt"
    if not p.exists():
        fail("images/cards.txt missing; card-number-to-packet match is not machine-checked")
        return
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.strip().startswith("#")]
    if not lines:
        fail("images/cards.txt has no card lines")
        return
    for line in lines:
        stat = line.split("|")[0].strip()
        if stat and research and stat not in research:
            fail(f"cards.txt stat '{stat}' not found verbatim in research.md")


def main() -> int:
    if len(sys.argv) != 2:
        print("WHY: usage: check_produced_episode.py <episode-dir>")
        return 1
    ep = Path(sys.argv[1])
    if not ep.is_dir():
        print(f"WHY: {ep} is not a directory")
        return 1
    research = check_research(ep)
    check_article(ep)
    check_teasers(ep)
    check_cards(ep, research)
    if failures:
        for f in failures:
            print(f"WHY: {f}")
        print(f"FAIL: {len(failures)} produce-gate check(s) failed")
        return 1
    print("PASS: produce-gate contract green (research, article, teasers, cards.txt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
