#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--render", choices=("pending", "complete"), required=True)
    parser.add_argument("--visual", choices=("pending", "PASS"), required=True)
    args = parser.parse_args()
    path = args.dir / "runlog.md"
    if not path.is_file():
        print("FAIL: runlog missing")
        return 1
    lines = path.read_text(encoding="utf-8").splitlines()
    render_found = visual_found = False
    for index, line in enumerate(lines):
        if line.startswith("- render: render ") and not render_found:
            lines[index] = f"- render: render {args.render}"
            render_found = True
        elif line.startswith("- visual_qa: visual QA ") and not visual_found:
            lines[index] = f"- visual_qa: visual QA {args.visual}"
            visual_found = True
    if not render_found or not visual_found:
        print(f"FAIL: runlog state rows missing render={render_found} visual={visual_found}")
        return 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS: report state render={args.render} visual={args.visual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
