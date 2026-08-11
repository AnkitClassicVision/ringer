#!/usr/bin/env python3
"""Rewrite compound responsePathway condition values into simple triples.

Bland evaluates [field, operator, value] literally; a value like
"true AND slot_count >= 1" can never match. This splits any such value at the
first AND/OR and keeps the leading literal, leaving ordering (which already
handles slot_count == 0 earlier) to do the rest.

usage: patch_anchor_conditions.py <draft.json> <out.json>
"""

import json
import re
import sys


def clean(value):
    if not isinstance(value, str):
        return value, False
    match = re.split(r"\s+(?:AND|OR)\s+", value, maxsplit=1, flags=re.I)
    if len(match) == 1:
        return value, False
    return match[0].strip(), True


def main():
    if len(sys.argv) != 3:
        print("usage: patch_anchor_conditions.py <draft.json> <out.json>")
        return 1
    src, dst = sys.argv[1:]
    graph = json.load(open(src, encoding="utf-8"))
    patched = 0

    for node in graph.get("nodes", []):
        pathways = node.get("data", {}).get("responsePathways")
        if not isinstance(pathways, list):
            continue
        for row in pathways:
            if isinstance(row, list) and len(row) >= 3:
                new_value, changed = clean(row[2])
                if changed:
                    print(f"PATCHED node={node.get('id')} {row[0]} {row[1]} {row[2]!r} -> {new_value!r}")
                    row[2] = new_value
                    patched += 1

    for edge in graph.get("edges", []):
        data = edge.get("data") or {}
        for key in ("label", "description"):
            value = data.get(key)
            if isinstance(value, str) and re.search(r"\s+AND\s+slot_count", value, re.I):
                new_value = re.split(r"\s+AND\s+", value, maxsplit=1, flags=re.I)[0].strip()
                print(f"PATCHED edge={edge.get('id')} {key} -> {new_value!r}")
                data[key] = new_value
                patched += 1

    json.dump(graph, open(dst, "w", encoding="utf-8"), indent=2)
    print(f"PATCH_DONE count={patched}")
    return 0 if patched else 1


if __name__ == "__main__":
    raise SystemExit(main())
