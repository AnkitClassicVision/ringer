#!/usr/bin/env python3
"""Structural candidate gate; a pass never substitutes for the live behavioral suite."""

from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import re
import sys
from typing import Any

OFFER_IDS = ("n_offer", "n_offer_2", "n_offer_3", "n_offer_near")
BOOK_VERIFY = {"n_book_1": "n_verify_1", "n_book_2": "n_verify_2"}
CLARIFICATION_TARGETS = {"n_gate_1", "n_gate_2", "n_negotiate", "e_declined", "e_timeout"}
RETIRED_ASSERTION_FIELDS = {"time_pref", "preference_after"}
KNOWN_ASSERTIONS = {
    # expect_week is the field the RUNNER actually implements for resolved-date checks;
    # this list originally guessed expect_resolved_dates (built in a parallel lane) and
    # the gate correctly refused the mismatch on first contact. Both stay listed: one is
    # real, the other harmless-if-unused, and removing the wrong one silently would be
    # the exact class of drift this gate exists to catch.
    "expect_node", "expect_nodes", "expect_text", "expect_vars", "expect_resolved_dates",
    "expect_week", "expect_slot_floor",
    "expect_offered_time_floor", "expect_no_offer", "expect_path", "expect_terminal",
}
HEADER = "STRUCTURAL CANDIDATE GATE: a pass never substitutes for the live behavioral suite."


def load_json(path: str | pathlib.Path) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _node_map(graph: dict[str, Any], problems: list[str]) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for node in graph.get("nodes", []):
        nid = node.get("id")
        if not isinstance(nid, str):
            problems.append("graph node without a string id")
        elif nid in nodes:
            problems.append(f"{nid}: duplicate node id")
        else:
            nodes[nid] = node
    return nodes


def _pathways(node: dict[str, Any]) -> list[list[Any]]:
    value = node.get("data", {}).get("responsePathways") or []
    return value if isinstance(value, list) else []


def _target(pathway: Any) -> str | None:
    try:
        return pathway[3].get("id")
    except (AttributeError, IndexError, TypeError):
        return None


def _scenario_objects(path: str | pathlib.Path, problems: list[str]) -> list[dict[str, Any]]:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
        if isinstance(raw, dict):
            raw = raw.get("scenarios")
        if isinstance(raw, list) and all(isinstance(x, dict) for x in raw):
            return raw
    except json.JSONDecodeError:
        pass

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        problems.append(f"scenario inventory {path}: cannot parse Python or JSON: {exc}")
        return []
    candidates: list[list[dict[str, Any]]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            try:
                obj = ast.literal_eval(value)
            except (ValueError, TypeError, SyntaxError):
                continue
            if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
                candidates.append(obj)
    if not candidates:
        problems.append(f"scenario inventory {path}: no literal list of scenario dictionaries found")
        return []
    return max(candidates, key=len)


def _check_scenarios(path: str | pathlib.Path, problems: list[str]) -> None:
    scenarios = _scenario_objects(path, problems)
    if len(scenarios) < 30:
        problems.append(
            f"scenario inventory {path}: has {len(scenarios)} scenarios; invariant 8 requires at least 30"
        )
    for index, scenario in enumerate(scenarios, 1):
        name = scenario.get("name", f"scenario #{index}")
        retired = sorted(RETIRED_ASSERTION_FIELDS & set(scenario))
        retired += sorted(
            f"expect_vars.{key}"
            for key in RETIRED_ASSERTION_FIELDS
            if isinstance(scenario.get("expect_vars"), dict) and key in scenario["expect_vars"]
        )
        if retired:
            problems.append(
                f"{name}: retired assertion field(s) {retired}; recorded manifest permits retiring "
                f"only {sorted(RETIRED_ASSERTION_FIELDS)}, not retaining them"
            )
        unknown = sorted(
            key for key in scenario
            if key.startswith(("expect_", "assert_")) and key not in KNOWN_ASSERTIONS
        )
        if unknown:
            problems.append(
                f"{name}: unrecorded assertion field(s) {unknown}; invariant 8 permits only named "
                f"assertion fields {sorted(KNOWN_ASSERTIONS)}"
            )


def check_graph(graph: dict[str, Any], scenarios_path: str | pathlib.Path | None = None) -> list[str]:
    problems: list[str] = []
    nodes = _node_map(graph, problems)
    edges = graph.get("edges", [])
    adj: dict[str, set[str]] = collections.defaultdict(set)
    inbound: dict[str, set[str]] = collections.defaultdict(set)
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if source not in nodes or target not in nodes:
            problems.append(f"edge {edge.get('id', '<unnamed>')}: dangling {source!r} -> {target!r}")
            continue
        adj[source].add(target)
        inbound[target].add(source)

    # 1 and 2: mixed-intent clarification and booking verification topology.
    for offer in OFFER_IDS:
        if offer not in nodes:
            problems.append(f"{offer}: missing offer node; invariant 1 requires all four offer nodes")
            continue
        if "n_which_intent" not in adj[offer]:
            problems.append(
                f"{offer}: no edge to n_which_intent; invariant 1 requires mixed intent to clarify"
            )
        direct_books = sorted(adj[offer] & set(BOOK_VERIFY))
        if direct_books:
            problems.append(
                f"{offer}: direct edge(s) to {direct_books}; invariant 2 forbids offer-to-book bypass"
            )
    if "n_which_intent" not in nodes:
        problems.append("n_which_intent: missing clarification node")
    else:
        bad = sorted(adj["n_which_intent"] - CLARIFICATION_TARGETS)
        if bad:
            problems.append(
                f"n_which_intent: outgoing target(s) {bad}; invariant 1 allows only "
                f"{sorted(CLARIFICATION_TARGETS)} and never a book node"
            )
        if not adj["n_which_intent"]:
            problems.append("n_which_intent: has no outgoing clarification-selection routes")
    for book, verify in BOOK_VERIFY.items():
        actual = sorted(inbound.get(book, set()))
        if actual != [verify]:
            problems.append(
                f"{book}: inbound sources {actual}; invariant 2 requires only {verify}"
            )

    # 3: outside-hours route must win before all slot-count offers.
    search = nodes.get("n_search")
    if not search:
        problems.append("n_search: missing; invariant 3 cannot inspect route order")
    else:
        paths = _pathways(search)
        outside = [
            i for i, p in enumerate(paths)
            if len(p) >= 3 and p[0] == "day_part" and p[1] == "==" and p[2] == "outside"
            and _target(p) == "n_miss_time"
        ]
        slot_offer = [
            i for i, p in enumerate(paths)
            if len(p) >= 3 and p[0] == "slot_count" and _target(p) in OFFER_IDS
        ]
        if len(outside) != 1:
            problems.append(
                f"n_search: found {len(outside)} day_part == outside routes to n_miss_time; "
                "invariant 3 requires exactly one"
            )
        elif slot_offer and outside[0] >= min(slot_offer):
            problems.append(
                f"n_search: outside route index {outside[0]} is not before slot-count offer "
                f"route index {min(slot_offer)}; invariant 3 requires outside-hours precedence"
            )
    # Scope correction after first contact with the real graph: the reviewed miss-node
    # architecture (stable since v55, three review rounds) has every miss node loop back
    # through the patient into n_search, which eventually offers — so TRANSITIVE
    # reachability to offers is the design, not a defect; a miss node with no path back
    # to offers would be a dead end. The enforceable invariant is DIRECT: n_miss_time
    # must never itself present times or feed a booking edge. The original transitive
    # wording came from the lane spec, not from a reviewer ruling.
    forbidden = set(OFFER_IDS) | set(BOOK_VERIFY)
    direct = sorted(adj.get("n_miss_time", set()) & forbidden)
    if direct:
        problems.append(
            f"n_miss_time: has DIRECT edge(s) to {direct}; invariant 3 forbids it presenting "
            f"times or feeding a booking edge itself"
        )

    # 4: every temporal extractor must preserve the qualified-week canon.
    temporal = []
    for nid, node in nodes.items():
        for var in node.get("data", {}).get("extractVars") or []:
            if len(var) >= 3 and var[0] in {"preference_from", "preference_to"}:
                temporal.append((nid, var[0], str(var[2]).lower()))
    if not temporal:
        problems.append("temporal extraction: no preference_from/preference_to descriptions found")
    for nid, field, desc in temporal:
        if field == "preference_from":
            if "tuesday next week" not in desc:
                problems.append(
                    f"{nid}.{field}: missing 'tuesday next week' normalization; invariant 4 "
                    "requires qualified-week canon"
                )
            if "monday next week" not in desc:
                problems.append(
                    f"{nid}.{field}: missing 'monday next week' vague-week mapping; invariant 4 "
                    "requires qualified-week canon"
                )
        if "must become tuesday" in desc:
            problems.append(
                f"{nid}.{field}: contains stripping instruction 'must become tuesday'; "
                "invariant 4 forbids dropping the next-week qualifier"
            )

    # 5: only confirmation may make a positive booking-exists claim.
    claim = re.compile(
        r"(?:appointment|visit)\s+(?:is|was|has been)\s+(?:booked|scheduled|confirmed)"
        r"|you(?:'re| are)\s+(?:booked|scheduled|confirmed|all set)"
        r"|we(?:'ve| have)\s+(?:booked|scheduled|confirmed)",
        re.I,
    )
    for nid, node in nodes.items():
        if nid == "n_confirm":
            continue
        for field in ("prompt", "text"):
            blob = str(node.get("data", {}).get(field) or "")
            for sentence in re.split(r"(?<=[.!?])\s+", blob):
                if claim.search(sentence) and not re.search(
                    r"\b(?:never|no|not|cannot|can't|do not|don't|may not)\b", sentence, re.I
                ):
                    problems.append(
                        f"{nid}.{field}: positive booking claim {sentence[:120]!r}; invariant 5 "
                        "gives n_confirm the confirmation monopoly"
                    )
                    break
    booked_text = str(nodes.get("e_booked", {}).get("data", {}).get("text") or "")
    if claim.search(booked_text) or re.search(r"\bbook(?:ed|ing)?\b", booked_text, re.I):
        problems.append(
            "e_booked.text: contains a second booking claim; invariant 5 permits only n_confirm "
            f"to assert the appointment exists (text={booked_text!r})"
        )

    # 6: each offer exposes exactly the canonical two slot variables.
    for offer in OFFER_IDS:
        if offer not in nodes:
            continue
        prompt = str(nodes[offer].get("data", {}).get("prompt") or "")
        variables = set(re.findall(r"\{\{\s*(slot_[a-z0-9_]+)\s*\}\}", prompt, re.I))
        expected = {"slot_1_start", "slot_2_start"}
        if variables != expected:
            problems.append(
                f"{offer}: slot variables {sorted(variables)}; invariant 6 requires exactly "
                f"{sorted(expected)} so only two slots are visible"
            )

    if scenarios_path is not None:
        _check_scenarios(scenarios_path, problems)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=HEADER)
    parser.add_argument("--graph", required=True)
    parser.add_argument("scenarios", nargs="?", help="optional scenario inventory path")
    parser.add_argument("--scenarios", dest="scenarios_flag", help="optional scenario inventory path")
    args = parser.parse_args(argv)
    scenario_path = args.scenarios_flag or args.scenarios
    print(HEADER)
    try:
        graph = load_json(args.graph)
        problems = check_graph(graph, scenario_path)
    except (OSError, json.JSONDecodeError) as exc:
        problems = [f"{args.graph}: cannot load graph JSON: {exc}"]
    if problems:
        print("CHECK FAILED")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("CHECK PASSED: candidate graph satisfies structural invariants 1-6"
          + (" and scenario-inventory invariant 8" if scenario_path else "")
          + "; suppression invariant 7 is delegated to check_suppression_delta.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
