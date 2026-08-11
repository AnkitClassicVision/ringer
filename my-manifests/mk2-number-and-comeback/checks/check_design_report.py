#!/usr/bin/env python3
"""Validate a Round A design report for the mk2-number-and-comeback job.

Fails with a printed WHY for every missing requirement. Substance checks only:
node coverage, mandated copy, come-back mechanics grounded in measurable Bland
behavior, scenario/gate/risk sections, brand-naming flag. Tolerant on format.
"""
import argparse
import pathlib
import re
import sys

sys.dont_write_bytecode = True

REQUIRED_NODES = [
    "n_confirm", "n_office", "n_faq", "e_safe_identity", "e_safe_failure",
    "e_booking_failed", "e_office", "e_declined", "e_stop", "e_not_me",
    "e_existing", "e_booked", "n_identity",
]

LINE_BOOKED = "you're all set. if you have further questions, please call mk2 optical at (212) 219-2219"
LINE_DEFER = "for that you'll have to contact the mk2 optical office at (212) 219-2219"

SECTIONS = {
    "change list (per-node v62 changes)": r"change\s*list|node[- ]?level|per[- ]?node",
    "come-back / re-engagement design": r"come[- ]?back|re[- ]?engage|text[- ]?back|re[- ]?entry",
    "scenario additions": r"scenario",
    "gate / redproof additions": r"gate|validator|redproof",
    "regression risks": r"risk|regression",
}

MECHANICS = ["isstart", "new_conversation", "start_node", "inbound", "end call"]
PROBE_WORDS = ["probe", "verify", "verified", "measure", "measured", "live test", "empirical"]


def norm(text: str) -> str:
    text = text.lower()
    for a, b in [("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("‑", "-"), (" ", " ")]:
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="report.md")
    args = ap.parse_args()

    path = pathlib.Path(args.file)
    if not path.is_file():
        print(f"FAIL: {args.file} does not exist — the task produced no report")
        return 1
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = norm(raw)
    words = len(raw.split())

    failures = []

    if words < 350:
        failures.append(f"report is only {words} words; a real design review of a 41-node live pathway needs at least 350")
    if words > 3000:
        failures.append(f"report is {words} words; ceiling is 3000 — cut restatement, keep decisions")

    if LINE_BOOKED not in text:
        failures.append("mandated post-booking closing line missing verbatim: \"You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219\"")
    if LINE_DEFER not in text:
        failures.append("mandated deferral line missing verbatim: \"For that you'll have to contact the MK2 Optical office at (212) 219-2219\"")
    if "855) 750-6688" not in text and "(855)" not in text:
        failures.append("report never mentions the outgoing number (855) 750-6688 — the change list must show what each node says today, not only the new copy")

    missing_nodes = [n for n in REQUIRED_NODES if n not in text]
    if missing_nodes:
        failures.append(f"change list does not cover these v61 nodes that must change or be examined: {', '.join(missing_nodes)}")

    for label, pat in SECTIONS.items():
        if not re.search(pat, text):
            failures.append(f"no section addressing: {label}")

    if not any(m in text for m in MECHANICS):
        failures.append("come-back design never engages Bland conversation mechanics (isStart / new_conversation / start_node / inbound / End Call) — it is not grounded in how threads actually restart")
    if not any(p in text for p in PROBE_WORDS):
        failures.append("no empirical probe named — the come-back mechanism cannot be trusted unmeasured; name the live test that settles Bland's post-End-Call behavior")

    if "mott optical" not in text or "mk2 optical" not in text:
        failures.append("brand-naming inconsistency (Mott Optical vs MK2 Optical) not addressed — 26 nodes say Mott Optical and the mandated lines say MK2 Optical")

    if failures:
        print(f"FAIL: {len(failures)} requirement(s) unmet in {args.file}:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"PASS: {args.file} covers all {len(REQUIRED_NODES)} required nodes, both mandated lines, come-back mechanics with a named probe, scenarios/gate/risks, and the brand flag ({words} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
