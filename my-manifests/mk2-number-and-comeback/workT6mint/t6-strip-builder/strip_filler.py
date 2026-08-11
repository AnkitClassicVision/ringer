#!/usr/bin/env python3
"""Remove the schedule-check filler sentence from a pathway graph."""

import json
import sys
from pathlib import Path
from typing import Any


FILLER = "One moment while I check the schedule for you."


def strip_from_string(value: str) -> tuple[str, int]:
    """Remove FILLER and clean only whitespace bordering its old positions."""
    parts = value.split(FILLER)
    removed = len(parts) - 1
    if removed == 0:
        return value, 0

    result = parts[0]
    for following in parts[1:]:
        left_spaces = len(result) - len(result.rstrip(" \t"))
        right_spaces = len(following) - len(following.lstrip(" \t"))

        left_core = result[:-left_spaces] if left_spaces else result
        right_core = following[right_spaces:]
        left_at_line_start = not left_core or left_core.endswith(("\n", "\r"))
        right_at_line_end = not right_core or right_core.startswith(("\n", "\r"))

        if right_at_line_end and left_spaces:
            result = result[:-left_spaces]
            left_spaces = 0
        if left_at_line_start and right_spaces:
            following = following[right_spaces:]
            right_spaces = 0
        if left_spaces and right_spaces:
            result = result[:-left_spaces] + " "
            following = following[right_spaces:]

        result += following

    return result, removed


def transform(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        return strip_from_string(value)
    if isinstance(value, list):
        output = []
        total = 0
        for item in value:
            changed, count = transform(item)
            output.append(changed)
            total += count
        return output, total
    if isinstance(value, dict):
        output = {}
        total = 0
        for key, item in value.items():
            changed, count = transform(item)
            output[key] = changed
            total += count
        return output, total
    return value, 0


def graph_counts(graph: Any) -> tuple[int, int]:
    assert isinstance(graph, dict), "top-level JSON must be an object"
    assert "nodes" in graph, "top-level 'nodes' field is missing"
    assert "edges" in graph, "top-level 'edges' field is missing"
    assert isinstance(graph["nodes"], list), "top-level 'nodes' field must be a list"
    assert isinstance(graph["edges"], list), "top-level 'edges' field must be a list"
    return len(graph["nodes"]), len(graph["edges"])


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {Path(sys.argv[0]).name} <in.json> <out.json>", file=sys.stderr)
        return 1

    try:
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
        with input_path.open("r", encoding="utf-8") as handle:
            graph = json.load(handle)

        before_nodes, before_edges = graph_counts(graph)
        transformed, removed = transform(graph)
        print(f"REMOVED={removed}")
        if removed == 0:
            return 1

        after_nodes, after_edges = graph_counts(transformed)
        assert before_nodes == after_nodes, (
            f"node count changed: {before_nodes} -> {after_nodes}"
        )
        assert before_edges == after_edges, (
            f"edge count changed: {before_edges} -> {after_edges}"
        )

        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(transformed, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        print(f"NODES={after_nodes} EDGES={after_edges}")
        return 0
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
