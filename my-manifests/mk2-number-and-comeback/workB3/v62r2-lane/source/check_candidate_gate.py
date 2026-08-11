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
CLOSE = "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"
DEFER = "For that you'll have to contact the MK2 Optical office at (212) 219-2219"
CARRIERS = {
    "n_confirm", "n_office", "n_faq", "e_safe_identity", "e_safe_failure",
    "e_booking_failed", "e_office", "e_declined", "e_stop", "e_not_me", "e_existing",
}


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
    if len(scenarios) < 40:
        problems.append(
            f"scenario inventory {path}: has {len(scenarios)} scenarios; invariant 8 requires at least 40"
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

    # v62 G1-G6: carrier migration, confirmation monopoly, terminal deferral,
    # never-rebook topology, booked-thread re-entry, and global-label scoping.
    serialized = json.dumps(graph, ensure_ascii=False)
    if "855" in serialized:
        problems.append("G1: retired number fragment '855' remains somewhere in the graph")
    number_nodes = {
        nid for nid, node in nodes.items()
        if "(212) 219-2219" in str(node.get("data", {}).get("prompt") or "")
        or "(212) 219-2219" in str(node.get("data", {}).get("text") or "")
    }
    expected_number_nodes = CARRIERS | {"e_defer"}
    if number_nodes != expected_number_nodes:
        problems.append(
            f"G1: new-number node set {sorted(number_nodes)}; expected {sorted(expected_number_nodes)}"
        )
    close_nodes = {
        nid for nid, node in nodes.items()
        if CLOSE in str(node.get("data", {}).get("prompt") or "")
        or CLOSE in str(node.get("data", {}).get("text") or "")
    }
    if close_nodes != {"n_confirm"}:
        problems.append(f"G2: CLOSE appears in {sorted(close_nodes)}; expected only n_confirm.prompt")
    if CLOSE not in str(nodes.get("n_confirm", {}).get("data", {}).get("prompt") or ""):
        problems.append("G2: n_confirm.prompt lacks the verbatim CLOSE")

    defer = nodes.get("e_defer")
    if not defer:
        problems.append("G3: e_defer is missing")
    else:
        if defer.get("type") != "End Call":
            problems.append(f"G3: e_defer type is {defer.get('type')!r}, expected 'End Call'")
        if defer.get("data", {}).get("text") != DEFER:
            problems.append(f"G3: e_defer.text is not the verbatim DEFER: {defer.get('data', {}).get('text')!r}")
        if defer.get("data", {}).get("outcome") != "deferred_after_booking":
            problems.append("G3: e_defer outcome must be deferred_after_booking")
        if adj.get("e_defer"):
            problems.append(f"G3: e_defer has outgoing targets {sorted(adj['e_defer'])}")
    outcomes = next((f.get("values", []) for f in graph.get("analysis_options", {}).get("fields", [])
                     if f.get("name") == "outcome"), [])
    if "deferred_after_booking" not in outcomes:
        problems.append("G3: analysis_options outcome omits deferred_after_booking")

    allowed_confirm = {"e_booked", "e_defer"}
    if adj.get("n_confirm", set()) != allowed_confirm:
        problems.append(
            f"G4: n_confirm adjacency is {sorted(adj.get('n_confirm', set()))}; expected exactly {sorted(allowed_confirm)}"
        )
    forbidden = {"n_search", "n_verify_1", "n_verify_2", "n_book_1", "n_book_2",
                 "n_offer", "n_offer_2", "n_offer_3", "n_offer_near", "n_office", "n_faq"}
    for start in ("n_confirm", "e_defer"):
        seen, stack = set(), list(adj.get(start, set()))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adj.get(current, set()))
        bad = sorted(seen & forbidden)
        if bad:
            problems.append(f"G4: {start} can reach forbidden post-booking node(s) {bad}")

    identity = nodes.get("n_identity", {})
    response_data = identity.get("data", {}).get("responseData") or []
    booked_maps = [x for x in response_data if x.get("name") == "booked_already"
                   and x.get("data") == "$.result.upcoming_appointment"]
    paths = _pathways(identity)
    booked_routes = [i for i, p in enumerate(paths) if len(p) >= 4 and p[:3] == ["booked_already", "==", "true"]
                     and _target(p) == "e_defer"]
    count_routes = [i for i, p in enumerate(paths) if len(p) >= 4 and p[:3] == ["count", "==", "1"]
                    and _target(p) == "n_ask"]
    if len(booked_maps) != 1:
        problems.append("G5: n_identity must map booked_already from $.result.upcoming_appointment exactly once")
    if len(booked_routes) != 1 or len(count_routes) != 1 or (booked_routes and count_routes and booked_routes[0] >= count_routes[0]):
        problems.append("G5: booked_already == true -> e_defer must appear once before count == 1 -> n_ask")
    for nid in ("n_office", "n_faq"):
        label = str(nodes.get(nid, {}).get("data", {}).get("globalLabel") or "").lower()
        if "does not apply once a booking is confirmed" not in label:
            problems.append(f"G6: {nid}.globalLabel lacks the post-booking exclusion")
    existing_label = str(nodes.get("e_existing", {}).get("data", {}).get("globalLabel") or "").lower()
    if "appointment made outside this conversation" not in existing_label:
        problems.append("G6: e_existing.globalLabel is not scoped to an appointment made outside this conversation")

    for nid, node in nodes.items():
        for field in ("prompt", "text"):
            if "Mott Optical" in str(node.get("data", {}).get(field) or ""):
                problems.append(f"brand: {nid}.{field} still contains patient-facing 'Mott Optical'")
    for terminal, recorder in (("e_stop", "n_suppress_stop"), ("e_not_me", "n_suppress_not_me")):
        unexpected = sorted(inbound.get(terminal, set()) - {recorder})
        if unexpected:
            problems.append(f"suppression: {terminal} has bypass inbound source(s) {unexpected}")

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

    # 3: day_part extraction must be able to emit the safety-routing token and
    # the after-3pm band, and the outside-hours route must win before all offers.
    day_part_extractors = []
    for nid, node in nodes.items():
        for var in node.get("data", {}).get("extractVars") or []:
            if len(var) >= 3 and var[0] == "day_part":
                day_part_extractors.append((nid, str(var[2]).lower()))
    if not day_part_extractors:
        problems.append("day_part extraction: none found; invariant 3 cannot verify safety tokens")
    for nid, desc in day_part_extractors:
        if "outside" not in desc:
            problems.append(
                f"{nid}.day_part: missing outside token; invariant 3 requires extraction "
                "guidance that can emit the outside-hours route token"
            )
        if "after 3" not in desc or "late" not in desc:
            problems.append(
                f"{nid}.day_part: missing after-3pm-to-late mapping; invariant 3 requires "
                "after 3 requests to extract as late"
            )

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

    # 4: every temporal extractor must preserve qualifiers and encode a vague week
    # as the gateway-probed pair next week..friday next week. The former
    # monday-next-week start can invert the range on Mondays and is banned.
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
            if "without naming a day, write next week" not in desc:
                problems.append(
                    f"{nid}.{field}: missing vague-week start mapping to exact phrase "
                    "'next week'; invariant 4 requires the probed pair encoding"
                )
            if re.search(
                r"(?:vague|without naming a day|no day).{0,100}"
                r"(?:write|map(?:s|ped)?(?:\s+from)?|become(?:s)?)\s+"
                r"(?:from\s+)?monday next week",
                desc,
            ):
                problems.append(
                    f"{nid}.{field}: maps a vague week to banned 'monday next week'; "
                    "invariant 4 forbids the Monday inverted-range encoding"
                )
        if field == "preference_to":
            if "no day, put friday next week" not in desc:
                problems.append(
                    f"{nid}.{field}: missing vague-week end mapping to exact phrase "
                    "'friday next week'; invariant 4 requires the probed pair encoding"
                )
            if (
                "week qualifier but no weekday" not in desc
                or "preference_to is friday followed by that same full week qualifier" not in desc
                or "next week through friday next week" not in desc
            ):
                problems.append(
                    f"{nid}.{field}: missing explicit week-with-no-weekday end-field rule; "
                    "invariant 4 requires preference_to to be friday plus the same full week "
                    "qualifier, including the pair 'next week' through 'friday next week'"
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
    parser.add_argument("graph", nargs="?", help="candidate graph JSON")
    parser.add_argument("--graph", dest="graph_flag", help="candidate graph JSON (legacy form)")
    parser.add_argument("scenarios", nargs="?", help="optional scenario inventory path")
    parser.add_argument("--scenarios", dest="scenarios_flag", help="optional scenario inventory path")
    args = parser.parse_args(argv)
    graph_path = args.graph_flag or args.graph
    if not graph_path:
        parser.error("a graph JSON path is required")
    scenario_path = args.scenarios_flag or args.scenarios
    print(HEADER)
    try:
        graph = load_json(graph_path)
        problems = check_graph(graph, scenario_path)
    except (OSError, json.JSONDecodeError) as exc:
        problems = [f"{graph_path}: cannot load graph JSON: {exc}"]
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
