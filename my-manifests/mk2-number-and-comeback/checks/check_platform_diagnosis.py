#!/usr/bin/env python3
"""Executable check for the platform-diff DIAGNOSIS.md.

Fails loudly with WHY. Substance checks:
- required sections present (case-insensitive, format-tolerant);
- a one-line CONVENTION: verdict exists;
- the doc discusses n_goal_search;
- at least 3 distinct backtick-quoted spans (len >= 6) from the doc appear
  VERBATIM in the captured corpus, so evidence cannot be invented.
"""

import glob
import re
import sys


def main():
    if len(sys.argv) < 3:
        print("usage: check_platform_diagnosis.py <DIAGNOSIS.md> <corpus_dir>...")
        return 1
    doc_path, corpus_dirs = sys.argv[1], sys.argv[2:]
    try:
        doc = open(doc_path, encoding="utf-8").read()
    except OSError as exc:
        print(f"FAIL: cannot read diagnosis: {exc}")
        return 1
    low = doc.lower()

    failures = []
    for section in ("root cause", "evidence", "proposed assertion", "fix plan"):
        if section not in low:
            failures.append(f"missing section: {section}")
    if not re.search(r"^\s*CONVENTION:", doc, re.MULTILINE):
        failures.append("missing one-line 'CONVENTION:' verdict")
    if "n_goal_search" not in doc:
        failures.append("never names n_goal_search, the node under study")

    corpus = ""
    corpus_files = []
    for d in corpus_dirs:
        for path in glob.glob(f"{d.rstrip('/')}/*"):
            if path.endswith((".json", ".txt", ".log")):
                corpus_files.append(path)
                try:
                    corpus += open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    pass
    if not corpus_files:
        failures.append(f"no corpus files found under {corpus_dirs}")

    spans = {s.strip() for s in re.findall(r"`([^`\n]{6,120})`", doc)}
    grounded = sorted(s for s in spans if s in corpus)
    if len(grounded) < 3:
        failures.append(
            f"only {len(grounded)} backtick-quoted spans found verbatim in the corpus "
            f"(need >= 3); grounded={grounded[:5]} sampled_ungrounded="
            f"{sorted(spans - set(grounded))[:5]}"
        )

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print(f"PASS: diagnosis grounded ({len(grounded)} verbatim evidence spans)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
