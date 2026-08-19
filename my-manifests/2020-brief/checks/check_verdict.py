#!/usr/bin/env python3
"""Ringer check for red-team judge output (20/20 Brief).

Two-layer QA: the judge reasons against holdout criteria the producer never
saw; this wrapper then TESTS the judge's own spot checks by fetching the URLs
and verifying the claimed figures appear verbatim on the page. Neither the
producer nor the judge can pass on say-so.

Usage: python3 check_verdict.py <verdict.json>
Exit 0 = pass or revise (structure valid, spot checks confirmed).
Exit 1 = fail (bad structure, failed spot checks, or verdict=fail).
Prints WHY on every failure.
"""

import concurrent.futures
import html
import json
import re
import sys
import urllib.error
import urllib.request

MIN_SPOT_CHECKS = 2
SPOT_CHECK_PASS_RATIO = 0.5


def fail(why: str) -> None:
    print(f"WHY: {why}")
    sys.exit(1)


def fetch_text(url: str) -> str | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; ringer-redteam/1.0)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read(400000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return "BOTWALLED"
        return None
    except Exception:
        return None
    text = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


def main() -> int:
    if len(sys.argv) != 2:
        fail("usage: check_verdict.py <verdict.json>")
    try:
        data = json.load(open(sys.argv[1], encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"verdict.json unreadable or invalid JSON: {exc}")

    verdict = data.get("verdict")
    if verdict not in ("pass", "revise", "fail"):
        fail(f"verdict must be pass|revise|fail, got {verdict!r}")

    findings = data.get("findings")
    if not isinstance(findings, list) or not findings:
        fail("findings must be a non-empty list")

    scores = data.get("scores", {})
    for key in ("surprise", "shareability", "honesty", "voice"):
        if not isinstance(scores.get(key), (int, float)):
            fail(f"scores.{key} missing or not numeric")
    if "math_holds" not in scores:
        fail("scores.math_holds missing")

    spot_checks = data.get("spot_checks")
    if not isinstance(spot_checks, list) or len(spot_checks) < MIN_SPOT_CHECKS:
        fail(f"spot_checks must have >= {MIN_SPOT_CHECKS} entries")
    for i, sc in enumerate(spot_checks):
        if not isinstance(sc, dict) or not sc.get("url") or not sc.get("claimed_figure"):
            fail(f"spot_checks[{i}] needs url and claimed_figure")

    def test_one(sc):
        page = fetch_text(sc["url"])
        if page is None:
            return sc, "unreachable"
        if page == "BOTWALLED":
            return sc, "botwalled"
        needle = re.sub(r"\s+", " ", str(sc["claimed_figure"])).strip().casefold()
        return sc, ("confirmed" if needle in page.casefold() else "figure-not-on-page")

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(test_one, spot_checks))

    confirmed = [r for r, s in results if s == "confirmed"]
    botwalled = [r for r, s in results if s == "botwalled"]
    for sc, status in results:
        print(f"spot-check {status}: {sc['claimed_figure']!r} @ {sc['url']}")

    need = max(1, int(len(spot_checks) * SPOT_CHECK_PASS_RATIO))
    if len(confirmed) < need:
        fail(
            f"only {len(confirmed)}/{len(spot_checks)} spot-check figures confirmed on-page "
            f"(need {need}); botwalled (unverifiable): {len(botwalled)}"
        )

    if verdict == "fail":
        print(f"WHY: judge verdict is fail; findings: {findings[:3]}")
        return 1

    print(
        f"{verdict.upper()}: structure valid, {len(confirmed)}/{len(spot_checks)} "
        f"spot checks confirmed, {len(botwalled)} bot-walled, math_holds={scores['math_holds']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
