#!/usr/bin/env python3
"""Assert every live gateway gate line produced by gw_gates.py."""

import datetime
import re
import sys


def parse(path):
    gates = {}
    expected = None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("GATE="):
            fields = dict(
                part.split("=", 1) for part in re.findall(r"\b\w+=[^ ]*(?: [ap]m)?", line)
            )
            gates[fields.get("GATE", "")] = (line, fields)
        elif line.startswith("EXPECT_RELATIVE_DATE="):
            expected = line.split("=", 1)[1]
    return gates, expected


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "gates.txt"
    gates, expected = parse(path)
    if expected is None:
        expected = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%m/%d/%Y")
    failures = []

    def line(label):
        return gates.get(label, ("<missing>", {}))[0]

    checks = [
        ("anchor-exact", lambda t: "first=08/07/2026 11:15 am" in t and "exact=True" in t,
         "exact anchor must return 11:15 first and report exact=True"),
        ("anchor-offgrid", lambda t: "exact=False" in t,
         "an off-grid anchor must report exact=False"),
        ("specificity", lambda t: "first=08/27/2026" in t,
         "explicit date must win over a vaguer sentence reading"),
        ("ordinal", lambda t: "first=08/27/2026" in t, "ordinal correction must resolve"),
        ("anaphora", lambda t: "first=08/17/2026" in t, "anaphoric week must defer to the pathway"),
        ("away-override", lambda t: f"first={expected}" in t, "away sentence must resolve to today+14"),
        ("week-of-reg", lambda t: "first=08/17/2026" in t, "week-of vocabulary"),
        ("relative-reg", lambda t: f"first={expected}" in t, "relative offset"),
        ("latest-reg", lambda t: re.search(r"first=[\d/]+ 0[45]:\d{2} pm", t) is not None, "latest ordering"),
        ("default-window", lambda t: re.search(r"first=[\d/]+ 0[3-5]:\d{2} pm", t) is not None, "default window"),
        ("oob-3am", lambda t: "oob=True" in t, "out-of-hours flag"),
    ]
    for label, predicate, why in checks:
        text = line(label)
        if not predicate(text):
            failures.append(f"{label}: {why} | got: {text}")

    for label, _, _ in checks:
        print(line(label))
    if failures:
        for item in failures:
            print("FAIL: " + item)
        return 1
    print(f"PASS: all {len(checks)} live gateway gates green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
