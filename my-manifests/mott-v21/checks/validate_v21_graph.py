#!/usr/bin/env python3
"""Independent gate on the generated Mott v21 pathway graph (revision 2).

The build worker authors its own validate_v21.py, so a check that only runs the
worker's validator proves nothing. This validator is owned by the orchestrator
and encodes the contract AFTER the Fable review round, which found nine defects
in revision 1 including a double-booking path.

Substance-strict, format-tolerant. Every failure prints the exact reason.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECRET_REFERENCE = "{{ SECRET.MottGatewayToken }}"

REQUIRED_NODES = {
    "n_identity": "start webhook, patient identity revalidation",
    "n_availability": "silent first-availability webhook",
    "n_opener_two": "first message when two openings exist",
    "n_opener_one": "first message when exactly one opening exists",
    "n_mixed_clarify": "mixed slot-and-preference clarification",
    "n_negotiate": "global negotiation wait node, collects the preference",
    "n_search": "deterministic availability webhook for the negotiation lane",
    "n_negotiate_offer": "offers the slots the search returned",
    "n_office": "global office direction",
    "n_conflict_1": "conflict check for slot 1",
    "n_conflict_2": "conflict check for slot 2",
    "n_sign_1": "governed booking for slot 1",
    "n_sign_2": "governed booking for slot 2",
    "n_confirmation": "confirmed appointment message",
    "e_safe_identity": "identity safe exit",
    "e_safe_failure": "gateway safe exit",
    "e_booking_failed": "ordinary booking failure exit",
    "e_booked": "booked end",
    "e_office": "office handoff end",
    "e_declined": "patient declined this offer",
    "e_stop": "global STOP exit",
    "e_not_me": "global wrong-person exit",
    "e_existing": "global existing-appointment exit",
    "e_timeout": "72-hour timeout exit, EXPLICIT edges only",
}

# e_timeout is deliberately absent: a global fires by matching a patient
# message, and silence produces no message, so a global timeout can never fire.
REQUIRED_GLOBALS = ["n_negotiate", "n_office", "e_stop", "e_not_me", "e_existing"]

WAITING_NODES = ["n_opener_two", "n_opener_one", "n_mixed_clarify", "n_negotiate",
                 "n_negotiate_offer", "n_confirmation"]

DATE_NORMALIZATION = re.compile(r"(?i)normaliz\w*\s+(exact\s+and\s+)?relative\s+dates|to\s+MM/DD/YYYY")

MAX_NODES = 26
MAX_EDGES = 54


def fail(reasons: list[str]) -> None:
    print("V21 GRAPH CHECK FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    sys.exit(1)


def node_data(node: dict) -> dict:
    data = node.get("data")
    return data if isinstance(data, dict) else {}


def text_of(value: object) -> str:
    return value if isinstance(value, str) else ""


def var_names(node: dict) -> list[str]:
    names: list[str] = []
    extract = node_data(node).get("extractVars")
    if isinstance(extract, list):
        for entry in extract:
            if isinstance(entry, list) and entry:
                names.append(text_of(entry[0]))
            elif isinstance(entry, dict):
                names.append(text_of(entry.get("name")))
    return names


def response_names(node: dict) -> list[str]:
    names: list[str] = []
    mapping = node_data(node).get("responseData")
    if isinstance(mapping, list):
        for entry in mapping:
            if isinstance(entry, dict):
                names.append(text_of(entry.get("name")))
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--packet", required=True, type=Path)
    args = parser.parse_args()

    for path in (args.graph, args.packet):
        if not path.is_file():
            fail([f"required file not found: {path}"])
    try:
        graph = json.loads(args.graph.read_text(encoding="utf-8"))
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"invalid JSON: {exc}"])

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        fail(["graph must have a nodes list and an edges list"])

    reasons: list[str] = []
    by_id = {n.get("id"): n for n in nodes if isinstance(n, dict)}

    # --- inventory ---------------------------------------------------------
    for node_id, purpose in REQUIRED_NODES.items():
        if node_id not in by_id:
            reasons.append(f"missing required node {node_id!r} ({purpose})")
    for gone, why in (
        ("n_contact_lookup", "defect F7 requires deleting the lookup the sender already made"),
        ("n_opener", "revision 2 splits the opener into n_opener_one and n_opener_two (finding V21-R5)"),
    ):
        if gone in by_id:
            reasons.append(f"{gone} still exists; {why}")
    if len(nodes) > MAX_NODES:
        reasons.append(f"{len(nodes)} nodes exceeds the {MAX_NODES} ceiling")
    if len(edges) > MAX_EDGES:
        reasons.append(f"{len(edges)} edges exceeds the {MAX_EDGES} ceiling (v20 was 56)")

    starts = [n.get("id") for n in nodes if isinstance(n, dict) and node_data(n).get("isStart")]
    if starts != ["n_identity"]:
        reasons.append(f"exactly one start node is required and it must be n_identity, got {starts!r}")

    # --- no tool-transcribed slot values anywhere (finding V21-R6) ---------
    for node in nodes:
        if isinstance(node, dict) and node_data(node).get("tools"):
            reasons.append(
                f"{node.get('id')} still attaches a tool. The negotiation lane must use the "
                "deterministic n_search webhook so slot values come from the gateway response, "
                "never transcribed by the model (finding V21-R6)"
            )

    search = by_id.get("n_search")
    if search is not None:
        data = node_data(search)
        if "/availability" not in text_of(data.get("url")):
            reasons.append("n_search must POST the gateway /availability route")
        mapped = response_names(search)
        for required in ("slot_count", "slot_1_start", "slot_1_end", "slot_1_doctor",
                         "slot_2_start", "slot_2_end", "slot_2_doctor", "time_pref_relaxed"):
            if required not in mapped:
                reasons.append(
                    f"n_search.responseData does not map {required!r}; the whole point of "
                    "revision 2 is that these values come from the gateway, not the model"
                )
        body = text_of(data.get("body"))
        if "{{preference_from}}" not in body or "{{preference_to}}" not in body:
            reasons.append("n_search body must template the collected preference_from and preference_to")

    negotiate = by_id.get("n_negotiate")
    if negotiate is not None:
        produced = var_names(negotiate)
        for banned in ("slot_1_start", "slot_1_end", "slot_1_doctor",
                       "slot_2_start", "slot_2_end", "slot_2_doctor"):
            if banned in produced:
                reasons.append(
                    f"n_negotiate still extracts {banned!r}. Slot values must be produced by "
                    "n_search responseData, never by model extraction (finding V21-R6)"
                )
        for required in ("preference_from", "preference_to"):
            if required not in produced:
                reasons.append(f"n_negotiate must collect {required!r} to feed n_search")

    # --- globals -----------------------------------------------------------
    declared = {text_of(g.get("node")): g for g in packet.get("globals", []) if isinstance(g, dict)}
    for node_id in REQUIRED_GLOBALS:
        node = by_id.get(node_id)
        if node is None:
            continue
        data = node_data(node)
        if data.get("isGlobal") is not True:
            reasons.append(f"{node_id} must set isGlobal true")
        label = text_of(data.get("globalLabel"))
        if not label.strip():
            reasons.append(f"{node_id} is global but has no globalLabel to trigger on")
        expected = declared.get(node_id, {}).get("autoReturn")
        if isinstance(expected, bool) and bool(data.get("enableGlobalAutoReturn")) != expected:
            reasons.append(
                f"{node_id} enableGlobalAutoReturn is {bool(data.get('enableGlobalAutoReturn'))!r} "
                f"but the decision packet declared {expected!r}"
            )

    # e_timeout must NOT be global: silence produces no message to match (V21-R2)
    timeout = by_id.get("e_timeout")
    if timeout is not None and node_data(timeout).get("isGlobal"):
        reasons.append(
            "e_timeout is marked global, but a global fires by matching a patient message and "
            "a 72-hour silence produces none, so it could never fire (finding V21-R2)"
        )

    # --- trigger disambiguation (findings V21-R1, V21-R9) -------------------
    neg_label = text_of(node_data(by_id.get("n_negotiate", {})).get("globalLabel")).lower()
    if neg_label:
        if not re.search(r"(?i)(after|once).{0,40}(confirm|book)", neg_label) or "not" not in neg_label:
            reasons.append(
                "n_negotiate globalLabel must explicitly EXCLUDE the post-confirmation case. "
                "Re-entering booking after a confirmed appointment double-books the patient "
                "(blocking finding V21-R1)"
            )
        if not re.search(r"(?i)(select|choos|pick).{0,60}(not|exclud)|(not|exclud).{0,60}(select|choos|pick)", neg_label):
            reasons.append(
                "n_negotiate globalLabel must exclude replies that ALSO select an offered slot; "
                "those belong to n_mixed_clarify (finding V21-R9)"
            )

    confirm_prompt = text_of(node_data(by_id.get("n_confirmation", {})).get("prompt"))
    if confirm_prompt and not re.search(r"(?i)(cancel|reschedul|chang)", confirm_prompt):
        reasons.append(
            "n_confirmation prompt no longer directs post-booking cancel or reschedule requests "
            "to the office; v20 had that defense and deleting it is the double-booking path "
            "(blocking finding V21-R1)"
        )

    # --- openers carry real slot data (F1, F2, V21-R5) ----------------------
    checks = [
        ("n_opener_two", ["slot_1_start", "slot_1_end", "slot_2_start", "slot_2_end"], True),
        ("n_opener_one", ["slot_1_start", "slot_1_end"], True),
        ("n_negotiate_offer", ["slot_1_start", "slot_1_end"], False),
        ("n_mixed_clarify", ["slot_1_start", "slot_1_end"], False),
    ]
    for node_id, required_vars, needs_name in checks:
        node = by_id.get(node_id)
        if node is None:
            continue
        prompt = text_of(node_data(node).get("prompt"))
        for var in required_vars:
            if var not in prompt:
                reasons.append(f"{node_id} prompt never references {{{{{var}}}}} (defect F1 class)")
        if needs_name and "patient_first" not in prompt:
            reasons.append(f"{node_id} prompt does not personalize with patient_first")
        if not re.search(r"(?i)new_york|new york|eastern", prompt):
            reasons.append(f"{node_id} prompt never names the display timezone (defect F2)")
    two = by_id.get("n_opener_two")
    if two is not None and "slot_count" in text_of(node_data(two).get("prompt")):
        reasons.append(
            "n_opener_two prompt still branches on slot_count; the split into two opener nodes "
            "exists so the edge decides the shape, not the model (finding V21-R5)"
        )

    # --- no model-side date computation (F3) --------------------------------
    for node in nodes:
        if not isinstance(node, dict):
            continue
        match = DATE_NORMALIZATION.search(text_of(node_data(node).get("prompt")))
        if match:
            reasons.append(
                f"{node.get('id')} prompt still instructs date normalization ({match.group(0)!r}); "
                "the gateway owns the deterministic resolver (defect F3)"
            )

    # --- webhook safety ------------------------------------------------------
    for node in nodes:
        if not isinstance(node, dict):
            continue
        data = node_data(node)
        if not data.get("url"):
            continue
        node_id = node.get("id")
        headers = data.get("headers") if isinstance(data.get("headers"), dict) else {}
        if headers.get("Authorization") != SECRET_REFERENCE:
            reasons.append(f"{node_id} Authorization is not the stored secret reference")
        options = data.get("modelOptions") if isinstance(data.get("modelOptions"), dict) else {}
        if options.get("retryAttempts") != 0:
            reasons.append(f"{node_id} must set retryAttempts 0, found {options.get('retryAttempts')!r}")
        for legacy in ("/book", "/reschedule", "/cancel"):
            if text_of(data.get("url")).rstrip("/").endswith(legacy):
                reasons.append(f"{node_id} calls edge-denied legacy route {legacy}")

    for slot in ("1", "2"):
        sign = by_id.get(f"n_sign_{slot}")
        if sign is None:
            continue
        body = text_of(node_data(sign).get("body"))
        for token in ('"appt.book"', '"new-booking"'):
            if token not in body:
                reasons.append(f"n_sign_{slot} body is missing {token}")
        if "allow_conflict" in body:
            reasons.append(f"n_sign_{slot} body contains allow_conflict, which the safety contract forbids")

    # --- edges ----------------------------------------------------------------
    adjacency: dict[str, list[tuple[str, str]]] = {}
    inbound: dict[str, list[str]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = text_of(edge.get("source"))
        target = text_of(edge.get("target"))
        label = text_of(edge.get("label")) or text_of((edge.get("data") or {}).get("label"))
        if not label.strip():
            reasons.append(f"unlabeled edge {source} -> {target}")
        adjacency.setdefault(source, []).append((target, label))
        inbound.setdefault(target, []).append(source)

    for slot in ("1", "2"):
        targets = [t for t, _ in adjacency.get(f"n_conflict_{slot}", [])]
        if f"n_sign_{slot}" not in targets:
            reasons.append(f"n_conflict_{slot} does not route to n_sign_{slot}")
        confirm = [lbl for tgt, lbl in adjacency.get(f"n_sign_{slot}", []) if tgt == "n_confirmation"]
        if not confirm:
            reasons.append(f"n_sign_{slot} has no edge to n_confirmation")
        elif not any("book_success" in lbl and "true" in lbl.lower() for lbl in confirm):
            reasons.append(f"n_sign_{slot} reaches confirmation on {confirm!r}, not book_success == true")

    # timeout must be wired explicitly from every waiting node (V21-R2)
    timeout_sources = set(inbound.get("e_timeout", []))
    for waiting in WAITING_NODES:
        if waiting in by_id and waiting not in timeout_sources:
            reasons.append(
                f"{waiting} has no explicit edge to e_timeout; the timeout cannot be a global "
                "so every waiting node must wire it (finding V21-R2)"
            )

    # office must terminate somewhere (V21-R3)
    if "n_office" in by_id and "e_office" not in {t for t, _ in adjacency.get("n_office", [])}:
        reasons.append("n_office has no outgoing edge to e_office; it dead-ends (finding V21-R3)")

    # a plain decline needs a real lane (V21-R4)
    decline_sources = set(inbound.get("e_declined", []))
    if not decline_sources:
        reasons.append(
            "e_declined has no inbound edge, so a plain 'no thanks' has nowhere to go and the "
            "declared declined outcome is unreachable (finding V21-R4)"
        )
    else:
        for offer_node in ("n_opener_two", "n_opener_one"):
            if offer_node in by_id and offer_node not in decline_sources:
                reasons.append(f"{offer_node} has no decline edge to e_declined (finding V21-R4)")

    exempt = set(starts) | set(REQUIRED_GLOBALS)
    for node_id in by_id:
        if node_id in exempt:
            continue
        if node_id not in inbound:
            reasons.append(f"{node_id} is orphaned: no edge leads to it")

    # --- analysis schema ------------------------------------------------------
    analysis = graph.get("analysis_options") or graph.get("analysisOptions")
    if not analysis:
        reasons.append("graph has no analysis_options (defect F9)")
    else:
        blob = json.dumps(analysis).lower()
        for field in packet.get("analysis_schema", {}).get("fields", []):
            name = text_of(field.get("name")) if isinstance(field, dict) else ""
            if name and name.lower() not in blob:
                reasons.append(f"analysis_options is missing the decided field {name!r}")
        if "declined" not in blob:
            reasons.append("analysis_options outcome enum must still carry a declined value")

    if reasons:
        fail(reasons)

    print("V21 GRAPH CHECK PASSED (revision 2 contract)")
    print(f"  nodes: {len(nodes)} (ceiling {MAX_NODES})")
    print(f"  edges: {len(edges)} (ceiling {MAX_EDGES})")
    print(f"  globals: {sorted(n for n in REQUIRED_GLOBALS if node_data(by_id.get(n, {})).get('isGlobal'))}")
    print("  e_timeout wired explicitly, no tools attached, slot values gateway-derived")
    return 0


if __name__ == "__main__":
    sys.exit(main())
