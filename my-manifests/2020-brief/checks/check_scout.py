#!/usr/bin/env python3
"""Ringer check for 20/20 Brief topic-scout output.

Validates structure (candidates + required fields) and executes URL liveness
probes so a worker cannot pass with invented sources. Prints WHY on failure
so Ringer's retry can self-heal.

Usage: python3 check_scout.py <candidates-file.md>
Exit 0 = PASS. Exit 1 = FAIL (with WHY line).
"""

import concurrent.futures
import re
import sys
import urllib.error
import urllib.request

REQUIRED_FIELDS = [
    "title:",
    "lane:",
    "hook:",
    "money_stat_candidate:",
    "why_owners_share_it:",
    "market_gap:",
    "owner_language:",
    "sources:",
]


def fail(why: str) -> None:
    print(f"WHY: {why}")
    sys.exit(1)


def probe(url: str):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; ringer-check/1.0)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return url, resp.status
    except urllib.error.HTTPError as exc:
        return url, exc.code
    except Exception:
        return url, None


def main() -> int:
    if len(sys.argv) != 2:
        fail("usage: check_scout.py <candidates-file.md>")
    try:
        text = open(sys.argv[1], encoding="utf-8").read()
    except OSError as exc:
        fail(f"cannot read {sys.argv[1]}: {exc}")

    candidates = re.split(r"^## Candidate ", text, flags=re.M)[1:]
    if len(candidates) < 2:
        fail(f"expected at least 2 '## Candidate N' sections, got {len(candidates)}")

    for i, block in enumerate(candidates, 1):
        missing = [f for f in REQUIRED_FIELDS if f not in block]
        if missing:
            fail(f"candidate {i} missing fields: {', '.join(missing)}")

    urls = [u.rstrip(".,;)>\"]") for u in re.findall(r"https?://[^\s)\]|\"]+", text)]
    urls = sorted(set(urls))
    if len(urls) < 4:
        fail(f"expected at least 4 distinct source URLs, got {len(urls)}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(probe, urls))

    live = [u for u, s in results if s is not None and s < 400]
    walled = [u for u, s in results if s in (401, 403)]
    dead = [u for u, s in results if s is None or (s is not None and s >= 400 and s not in (401, 403))]
    need = max(3, int(len(urls) * 0.75))
    if len(live) + len(walled) < need:
        fail(
            f"only {len(live) + len(walled)}/{len(urls)} URLs reachable or bot-walled "
            f"(need {need}); dead: {dead[:5]}"
        )

    print(
        f"PASS: {len(candidates)} candidates, all fields present, "
        f"{len(live)} URLs live, {len(walled)} bot-walled, {len(dead)} dead"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
