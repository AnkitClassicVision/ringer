#!/usr/bin/env python3
"""Canonical Ringer entrypoint for the deterministic goal-loop derivation."""
from __future__ import annotations

import json
import sys

from derive_goalloop import FROZEN_EXTRACTORS, OUTPUT, assert_kept_verbatim, build, write_fixtures


def main() -> int:
    graph = build()
    kept = assert_kept_verbatim(graph)
    OUTPUT.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if "--fixtures" in sys.argv:
        write_fixtures(graph)
    print(f"WROTE={OUTPUT.name}")
    print(f"WROTE={FROZEN_EXTRACTORS.name}")
    print(f"KEPT_VERBATIM={kept} nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
