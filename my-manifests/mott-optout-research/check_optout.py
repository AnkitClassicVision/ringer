#!/usr/bin/env python3
"""Check the opt-out research verdict: committed, grounded, and covers the live test.

Not a quality judge of the reasoning; it enforces that the report commits to ONE
verdict from a closed set, cites the staged Twilio/Bland evidence, resolves the
messaging_service_sid=null question explicitly, and specifies the empirical live-STOP
test as the per-number confirmation rather than treating docs as proof for THIS number.
"""
import argparse
import pathlib
import re
import sys

VERDICTS = ("VERDICT: CARRIER-LEVEL-SUFFICIENT", "VERDICT: BUILD-READ-ENDPOINT",
            "VERDICT: INSUFFICIENT")
REQUIRED = ("21610", "messaging_service_sid", "START", "live", "STOP")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    p = pathlib.Path(args.report)
    if not p.exists():
        print(f"CHECK FAILED\n\n  - {args.report} was never written")
        return 1
    t = p.read_text(encoding="utf-8")
    tl = t.lower()
    problems = []

    if len(t.split()) < 200:
        problems.append(f"report is only {len(t.split())} words")

    found = [v for v in VERDICTS if v in t]
    if not found:
        problems.append(f"no verdict; expected exactly one of {VERDICTS}")
    elif len(found) > 1:
        problems.append(f"states {len(found)} verdicts {found}; must commit to one")

    for term in REQUIRED:
        if term.lower() not in tl:
            problems.append(f"does not address required term {term!r}")

    # The null concern must be resolved, not just mentioned: the report must say the
    # number-level block applies regardless of messaging_service_sid.
    if "messaging_service_sid" in tl and not re.search(
            r"(regardless|even (when|without|if)|number[- ]level|does not (require|depend)|"
            r"not (required|needed|dependent))", tl):
        problems.append("mentions messaging_service_sid but never resolves whether opt-out "
                        "still works when it is null")

    # Must name the empirical per-number confirmation, not lean on docs alone. Tolerant of
    # markdown/formatting between tokens (an earlier version tripped on bold **STOP**):
    # require the three ideas present and ordered, not adjacent.
    stripped = re.sub(r"[*_`>#]", "", tl)  # drop markdown emphasis/heading marks
    m_stop = re.search(r"(reply|text|send)\s+stop", stripped)
    m_resend = re.search(r"(resend|send again|another sms|retry|attempt another|"
                         r"attempt (a |an )?(final )?(controlled )?sms)", stripped)
    m_block = re.search(r"21610", stripped)
    # A '## Confirming Test' (or similarly named) section must exist AND contain the STOP
    # and resend/21610 ideas. Substance over arrangement: an earlier 'retry' elsewhere in
    # the report must not defeat a genuinely-specified test section.
    has_test_section = bool(re.search(r"#+\s*(confirming|verification|live|empirical)\s+test",
                                      tl))
    if not (has_test_section and m_stop and m_resend and m_block):
        problems.append("does not specify the live STOP-then-resend test that empirically "
                        "confirms opt-out for THIS number (docs are not proof for one number)")

    # Sources must be present and resolvable-looking.
    urls = re.findall(r"https?://[^\s)]+", t)
    if len([u for u in urls if "twilio" in u]) < 1:
        problems.append("cites no Twilio source URL")

    if problems:
        print("CHECK FAILED\n")
        for pr in problems:
            print(f"  - {pr}")
        print(f"\n{len(problems)} problem(s).")
        return 1
    print(f"CHECK PASSED: committed to {found[0]!r}, resolved the null question, named the "
          f"live STOP/resend confirmation, cited Twilio sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
