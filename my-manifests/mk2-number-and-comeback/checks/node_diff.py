#!/usr/bin/env python3
"""Deterministic diff inputs for the goal-loop platform diagnosis.

Extracts the search webhook node from two stored pathway graphs (any envelope
shape - found by node id anywhere in the JSON), writes each sorted, and emits
a unified diff. Also emits a key-structure walk of both turn-2 chat envelopes
so structural differences (missing variables, absent webhook traces) are
visible without reading raw files side by side.
"""

import difflib
import json
import sys


def find_node(obj, node_id):
    """Depth-first search for a dict whose 'id' equals node_id."""
    if isinstance(obj, dict):
        if obj.get("id") == node_id:
            return obj
        for value in obj.values():
            found = find_node(value, node_id)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_node(item, node_id)
            if found is not None:
                return found
    return None


def walk(obj, prefix="", depth=0, lines=None):
    if lines is None:
        lines = []
    if depth > 3:
        lines.append(f"{prefix} = <depth-limit type={type(obj).__name__}>")
        return lines
    if isinstance(obj, dict):
        for key in sorted(obj):
            walk(obj[key], f"{prefix}.{key}" if prefix else key, depth + 1, lines)
    elif isinstance(obj, list):
        lines.append(f"{prefix} = list(len={len(obj)})")
        for index, item in enumerate(obj[:3]):
            walk(item, f"{prefix}[{index}]", depth + 1, lines)
    else:
        preview = str(obj).replace("\n", " ")[:80]
        lines.append(f"{prefix} = {type(obj).__name__}: {preview}")
    return lines


def main():
    if len(sys.argv) != 6:
        print(
            "usage: node_diff.py <graph96.json> <graph101.json> "
            "<turn2_96.json> <turn2_101.json> <outdir>",
            file=sys.stderr,
        )
        return 1
    graph96_path, graph101_path, turn96_path, turn101_path, outdir = sys.argv[1:]

    graph96 = json.load(open(graph96_path))
    graph101 = json.load(open(graph101_path))
    node96 = find_node(graph96, "n_search")
    node101 = find_node(graph101, "n_goal_search")
    if node96 is None:
        print("FAIL: node n_search not found in v96 stored graph")
        return 1
    if node101 is None:
        print("FAIL: node n_goal_search not found in v101 stored graph")
        return 1

    text96 = json.dumps(node96, indent=2, sort_keys=True).splitlines(keepends=True)
    text101 = json.dumps(node101, indent=2, sort_keys=True).splitlines(keepends=True)
    diff = difflib.unified_diff(
        text96, text101, fromfile="v96:n_search", tofile="v101:n_goal_search"
    )
    with open(f"{outdir}/NODE-DIFF.txt", "w") as f:
        f.writelines(diff)

    with open(f"{outdir}/ENVELOPE-DIFF.txt", "w") as f:
        for label, path in (("v96", turn96_path), ("v101", turn101_path)):
            f.write(f"===== {label} turn2 structure =====\n")
            f.write("\n".join(walk(json.load(open(path)))) + "\n\n")

    print("DIFF_COMPLETE nodes=n_search,n_goal_search")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
