#!/usr/bin/env python3
"""Orchestrator-owned gate on the Mott v22 pathway graph.

v22 is derived from the signed state-and-procedure map, not from a defect list.
Every check here traces to a numbered rule on that map.

  R1  every silent step has exactly one unconditional failure exit
  R2  one state, one node
  R3  booking values come from webhook response mappings, never model extraction
  R4  every waiting step carries all patient-initiated exits
  R5  confirmation is reachable only from a booking success
  R6  the message shows a rendered start time only
  R7  known questions answer from a fixed list and return the patient
  R8  opted-out and wrong-number must not claim a suppression that never happens
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECRET_REFERENCE = "{{ SECRET.MottGatewayToken }}"
FALLBACK_SENTINEL = "__never__"

REQUIRED_NODES = {
    "n_identity": "silent, resolve identity",
    "n_availability": "silent, find first openings",
    "n_offer": "waiting, the single Offered state",
    "n_negotiate": "waiting global, Negotiating state",
    "n_search": "silent, search by preference",
    "n_verify_1": "silent, verify chosen opening 1",
    "n_verify_2": "silent, verify chosen opening 2",
    "n_book_1": "silent, book opening 1",
    "n_book_2": "silent, book opening 2",
    "n_confirm": "waiting, Booked state",
    "n_office": "waiting global, off-topic handoff",
    "n_faq": "waiting global with auto-return, known questions",
    "e_safe_identity": "exit, identity could not be established",
    "e_safe_failure": "exit, shared gateway failure",
    "e_booking_failed": "exit, booking did not succeed",
    "e_booked": "exit, booked",
    "e_office": "exit, office handoff delivered",
    "e_declined": "exit, patient declined",
    "e_stop": "exit, opted out",
    "e_not_me": "exit, wrong number",
    "e_existing": "exit, already has an appointment",
    "e_timeout": "exit, no reply in 72 hours",
}

# R2: nodes that represented a duplicated state and must be gone.
BANNED_NODES = {
    "n_contact_lookup": "the sender already performs this lookup",
    "n_opener_two": "Offered is one state, one node (R2)",
    "n_opener_one": "Offered is one state, one node (R2)",
    "n_negotiate_offer": "Offered is one state, one node (R2)",
    "n_mixed_clarify": "clarifying a mixed reply is the offer step doing its job (R2)",
    "n_conflict_1": "renamed to n_verify_1 in the map",
    "n_conflict_2": "renamed to n_verify_2 in the map",
    "n_sign_1": "renamed to n_book_1 in the map",
    "n_sign_2": "renamed to n_book_2 in the map",
}

# R7: n_faq is the ONLY global that hands control back.
AUTO_RETURN_GLOBALS = ["n_faq", "n_office"]
AUTO_RETURN_GLOBAL = "n_faq"
TAKEOVER_GLOBALS = ["n_negotiate", "e_stop", "e_not_me", "e_existing"]

# Only the states where we genuinely wait on the patient. n_office delivers and
# ends; n_faq answers and hands control back to whatever state the patient was
# already in, so the timeout belongs to that state, not to either of these.
WAITING_NODES = ["n_offer", "n_negotiate", "n_confirm"]
SILENT_NODES = ["n_identity", "n_availability", "n_search",
                "n_verify_1", "n_verify_2", "n_book_1", "n_book_2"]

DATE_NORMALIZATION = re.compile(r"(?i)normaliz\w*\s+(exact\s+and\s+)?relative\s+dates|to\s+MM/DD/YYYY")

MAX_NODES = 24
MAX_EDGES = 52


def adjacency_preview(edges: list, source: str) -> list[tuple[str, str]]:
    """Outgoing (target, label) pairs for one node, usable before the main pass."""
    out = []
    for edge in edges:
        if isinstance(edge, dict) and edge.get("source") == source:
            label = edge.get("label") or (edge.get("data") or {}).get("label") or ""
            out.append((str(edge.get("target")), str(label)))
    return out


def fail(reasons: list[str]) -> None:
    print("V22 GRAPH CHECK FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    sys.exit(1)


def data_of(node: dict) -> dict:
    d = node.get("data")
    return d if isinstance(d, dict) else {}


def text_of(value: object) -> str:
    return value if isinstance(value, str) else ""


def var_names(node: dict) -> list[str]:
    names: list[str] = []
    extract = data_of(node).get("extractVars")
    if isinstance(extract, list):
        for entry in extract:
            if isinstance(entry, list) and entry:
                names.append(text_of(entry[0]))
            elif isinstance(entry, dict):
                names.append(text_of(entry.get("name")))
    return names


def response_names(node: dict) -> list[str]:
    names: list[str] = []
    mapping = data_of(node).get("responseData")
    if isinstance(mapping, list):
        for entry in mapping:
            if isinstance(entry, dict):
                names.append(text_of(entry.get("name")))
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    args = parser.parse_args()

    if not args.graph.is_file():
        fail([f"graph not found: {args.graph}"])
    try:
        graph = json.loads(args.graph.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"invalid JSON: {exc}"])

    nodes, edges = graph.get("nodes"), graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        fail(["graph needs a nodes list and an edges list"])

    reasons: list[str] = []
    by_id = {n.get("id"): n for n in nodes if isinstance(n, dict)}

    # --- inventory, R2 ------------------------------------------------------
    for node_id, purpose in REQUIRED_NODES.items():
        if node_id not in by_id:
            reasons.append(f"missing required node {node_id!r} ({purpose})")
    for node_id, why in BANNED_NODES.items():
        if node_id in by_id:
            reasons.append(f"{node_id} must not exist: {why}")
    if len(nodes) > MAX_NODES:
        reasons.append(f"{len(nodes)} nodes exceeds the {MAX_NODES} ceiling")
    if len(edges) > MAX_EDGES:
        reasons.append(f"{len(edges)} edges exceeds the {MAX_EDGES} ceiling")

    ids = [text_of(e.get("id")) for e in edges if isinstance(e, dict)]
    if len(set(ids)) != len(ids):
        reasons.append("duplicate edge ids: React Flow drops all but one, silently losing routes")
    for node in nodes:
        if isinstance(node, dict) and "position" not in node:
            reasons.append(f"{node.get('id')} has no position, so the canvas cannot place it")

    starts = [n.get("id") for n in nodes if isinstance(n, dict) and data_of(n).get("isStart")]
    if starts != ["n_identity"]:
        reasons.append(f"n_identity must be the only start node, got {starts!r}")

    # --- R1 and R9, the two rules that stranded the live test --------------
    for node_id in SILENT_NODES:
        node = by_id.get(node_id)
        if node is None:
            continue
        pathways = data_of(node).get("responsePathways")
        if not isinstance(pathways, list) or not pathways:
            reasons.append(f"{node_id} has no responsePathways at all")
            continue

        # R9: every comparison value must be a string literal. A boolean or an
        # integer never matches a webhook-extracted value, so the node falls
        # through to nothing and the conversation is stranded.
        for pw in pathways:
            if not (isinstance(pw, list) and len(pw) >= 4):
                reasons.append(f"{node_id} has a malformed responsePathway: {pw!r}")
                continue
            if not isinstance(pw[2], str):
                reasons.append(
                    f"{node_id} compares {pw[0]!r} against the non-string literal {pw[2]!r} "
                    f"({type(pw[2]).__name__}). Webhook values arrive as strings, so this can "
                    f"never match (R9). Write \"{str(pw[2]).lower()}\" instead."
                )

        # R1: some condition must always match, and the complement must sit on
        # the conservative branch so an unknown value never takes a booking path.
        complements = [
            pw for pw in pathways
            if isinstance(pw, list) and len(pw) >= 4 and pw[1] == "!="
        ]
        if not complements:
            reasons.append(
                f"{node_id} has no '!=' complement, so an unexpected response matches nothing "
                f"and strands the patient with no message and no timeout (R1). A silent step is "
                f"not a waiting step, so the 72-hour timeout cannot rescue it."
            )
        else:
            risky = {"n_verify_1": "n_book_1", "n_verify_2": "n_book_2"}
            if node_id in risky:
                targets = [
                    pw[3].get("id") for pw in complements
                    if isinstance(pw[3], dict)
                ]
                if risky[node_id] in targets:
                    reasons.append(
                        f"{node_id} puts its '!=' complement on {risky[node_id]}, so a missing or "
                        f"malformed value would BOOK. The complement must sit on the conservative "
                        f"branch; only an explicit expected value may book (R1)."
                    )

    # --- R3, no tools, no model-produced slot values ------------------------
    for node in nodes:
        if isinstance(node, dict) and data_of(node).get("tools"):
            reasons.append(f"{node.get('id')} attaches a tool; booking values must come from webhooks (R3)")

    search = by_id.get("n_search")
    if search is not None:
        mapped = response_names(search)
        for required in ("slot_count", "slot_1_start", "slot_1_end", "slot_1_doctor",
                         "slot_2_start", "slot_2_end", "slot_2_doctor", "time_pref_relaxed"):
            if required not in mapped:
                reasons.append(f"n_search.responseData does not map {required!r} (R3)")
        body = text_of(data_of(search).get("body"))
        for token in ("{{preference_from}}", "{{preference_to}}"):
            if token not in body:
                reasons.append(f"n_search body must template {token}")

    negotiate = by_id.get("n_negotiate")
    if negotiate is not None:
        produced = var_names(negotiate)
        for banned in ("slot_1_start", "slot_1_end", "slot_1_doctor",
                       "slot_2_start", "slot_2_end", "slot_2_doctor"):
            if banned in produced:
                reasons.append(f"n_negotiate extracts {banned!r}; slot values come from n_search (R3)")
        for required in ("preference_from", "preference_to"):
            if required not in produced:
                reasons.append(f"n_negotiate must collect {required!r}")

    # --- globals, R7 --------------------------------------------------------
    for node_id in AUTO_RETURN_GLOBALS:
        node = by_id.get(node_id)
        if node is None:
            continue
        d = data_of(node)
        if d.get("isGlobal") is not True:
            reasons.append(f"{node_id} must be global")
        if d.get("enableGlobalAutoReturn") is not True:
            reasons.append(
                f"{node_id} must set enableGlobalAutoReturn true. It belongs to the "
                f"answer-other-requests loop, which always hands the patient back to the "
                f"find-and-book loop rather than ending the conversation (R7)"
            )
        if "get them scheduled now" not in text_of(d.get("prompt")):
            reasons.append(
                f"{node_id} does not return the patient to the goal with an explicit scheduling "
                f"ask. Every detour must come back and ask for the booking (R7)"
            )
    faq = by_id.get("n_faq")
    if faq is not None:
        d = data_of(faq)
        prompt = text_of(d.get("prompt"))
        if not re.search(r"(?i)(never|do not|don't)\s+(invent|make up|guess|generate|fabricat)", prompt):
            reasons.append(
                "n_faq prompt must explicitly forbid inventing an answer. An invented address or "
                "set of hours is a real-world harm (R7)"
            )
        if "750-6688" not in prompt:
            reasons.append("n_faq must carry the one approved fact available, the office phone number")
    for node_id in TAKEOVER_GLOBALS:
        node = by_id.get(node_id)
        if node is None:
            continue
        d = data_of(node)
        if d.get("isGlobal") is not True:
            reasons.append(f"{node_id} must be global")
        if d.get("enableGlobalAutoReturn"):
            reasons.append(f"{node_id} must NOT auto-return; only n_faq hands control back (R7)")
        if not text_of(d.get("globalLabel")).strip():
            reasons.append(f"{node_id} is global but has no globalLabel")

    timeout = by_id.get("e_timeout")
    if timeout is not None and data_of(timeout).get("isGlobal"):
        reasons.append("e_timeout cannot be global; silence produces no message for a global to match")

    # --- R6, the message ----------------------------------------------------
    offer = by_id.get("n_offer")
    if offer is not None:
        prompt = text_of(data_of(offer).get("prompt"))
        for required in ("{{patient_first}}", "{{slot_1_start}}", "{{slot_2_start}}"):
            if required not in prompt:
                reasons.append(f"n_offer prompt must reference {required}")
        for banned in ("{{slot_1_end}}", "{{slot_2_end}}"):
            if banned in prompt:
                reasons.append(
                    f"n_offer prompt references {banned}; the message shows a START time only (R6)"
                )
        if not re.search(r"(?i)new_york|new york|eastern", prompt):
            reasons.append("n_offer prompt must name the display timezone (R6)")
        if not re.search(r"(?i)mott optical", prompt):
            reasons.append("n_offer prompt must keep the approved clinic copy")
        if not re.search(r"(?i)(mix\w*|both\s+\w+\w*\s+(an?\s+)?opening|(select|choos|pick)\w*.*(and|but).*(prefer|different|time))", prompt):
            reasons.append("n_offer must handle a reply that mixes a selection with a new preference (R2)")

    for node in nodes:
        if not isinstance(node, dict):
            continue
        match = DATE_NORMALIZATION.search(text_of(data_of(node).get("prompt")))
        if match:
            reasons.append(f"{node.get('id')} still instructs date normalization ({match.group(0)!r})")

    # --- the v21 blocking finding: never book twice -------------------------
    confirm = by_id.get("n_confirm")
    if confirm is not None:
        prompt = text_of(data_of(confirm).get("prompt"))
        if not re.search(r"(?i)(cancel|reschedul|chang)", prompt):
            reasons.append(
                "n_confirm prompt does not direct a post-confirmation cancel, reschedule or change "
                "request away from booking. Omitting it is how a patient ends up holding two "
                "appointments while believing they hold one."
            )
        onward = {t for t, _ in adjacency_preview(edges, "n_confirm")}
        if not onward & {"n_office", "e_office", "e_existing"}:
            reasons.append(
                "n_confirm has no edge to a safe office destination for a post-booking change request"
            )
        for forbidden in ("n_negotiate", "n_verify_1", "n_verify_2", "n_book_1", "n_book_2"):
            if forbidden in onward:
                reasons.append(
                    f"n_confirm routes to {forbidden}, which re-enters booking after a confirmation "
                    f"and double-books the patient"
                )
    neg_label = text_of(data_of(by_id.get("n_negotiate", {})).get("globalLabel")).lower()
    if neg_label and not re.search(r"(?i)(before any booking|not.{0,30}(confirm|booked)|once.{0,30}confirm)", neg_label):
        reasons.append(
            "n_negotiate globalLabel does not exclude the post-confirmation case, so 'can we do "
            "Thursday instead' after a booking would re-enter the booking path"
        )

    # --- R12: only the confirmation node may claim a booking ----------------
    # A live patient was told "I have you down for 11:45" while nothing was ever
    # written. Structural gating stops the write; only this stops the claim.
    NO_CLAIM = re.compile(r"(?i)never\s+say\s+or\s+imply\s+that\s+an\s+appointment\s+is\s+booked")
    for node_id in ("n_offer", "n_negotiate", "n_office", "n_faq"):
        node = by_id.get(node_id)
        if node is None:
            continue
        if not NO_CLAIM.search(text_of(data_of(node).get("prompt"))):
            reasons.append(
                f"{node_id} does not forbid claiming a booking. Any patient-facing node that can "
                f"say 'I have you down for that time' can tell a patient they are booked when "
                f"nothing was written, which happened live on v27 (R12)"
            )
    confirm_node = by_id.get("n_confirm")
    if confirm_node is not None and NO_CLAIM.search(text_of(data_of(confirm_node).get("prompt"))):
        reasons.append(
            "n_confirm carries the no-claim prohibition, but it is the one node that MUST be able "
            "to confirm a booking (R12)"
        )

    # --- R8, honest labelling AND honest patient-facing text ----------------
    # A promise the system cannot keep is the defect, whatever words carry it.
    FALSE_PROMISE = re.compile(
        r"(?i)(opted?\s*out|no\s+(more|further)\s+(messages|texts)|"
        r"(will|won't|will not)\s+(not\s+)?(receive|be\s+sent|message|text)|"
        r"removed\s+from|unsubscrib|suppress)"
    )
    for node_id in ("e_stop", "e_not_me"):
        node = by_id.get(node_id)
        if node is None:
            continue
        d = data_of(node)
        for field in ("text", "name", "outcome", "globalLabel"):
            value = text_of(d.get(field))
            match = FALSE_PROMISE.search(value)
            if match:
                reasons.append(
                    f"{node_id}.{field} promises {match.group(0)!r}, which nothing in the system "
                    f"can keep: there is no suppression store, so the next campaign can text this "
                    f"person again. Acknowledge the request and route it to a human instead (R8)"
                )
        tag = d.get("tag")
        if isinstance(tag, dict) and FALSE_PROMISE.search(text_of(tag.get("name"))):
            reasons.append(f"{node_id} tag asserts a suppression that never happens (R8)")

    # --- webhook safety -----------------------------------------------------
    for node in nodes:
        if not isinstance(node, dict):
            continue
        d = data_of(node)
        if not d.get("url"):
            continue
        node_id = node.get("id")
        headers = d.get("headers") if isinstance(d.get("headers"), dict) else {}
        if headers.get("Authorization") != SECRET_REFERENCE:
            reasons.append(f"{node_id} Authorization is not the stored reference")
        options = d.get("modelOptions") if isinstance(d.get("modelOptions"), dict) else {}
        if options.get("retryAttempts") != 0:
            reasons.append(f"{node_id} must set retryAttempts 0")
        for legacy in ("/book", "/reschedule", "/cancel"):
            if text_of(d.get("url")).rstrip("/").endswith(legacy):
                reasons.append(f"{node_id} calls edge-denied legacy route {legacy}")

    for slot in ("1", "2"):
        book = by_id.get(f"n_book_{slot}")
        if book is None:
            continue
        body = text_of(data_of(book).get("body"))
        for token in ('"appt.book"', '"new-booking"'):
            if token not in body:
                reasons.append(f"n_book_{slot} body missing {token}")
        if "allow_conflict" in body:
            reasons.append(f"n_book_{slot} body contains allow_conflict")

    # --- edges --------------------------------------------------------------
    adjacency: dict[str, list[tuple[str, str]]] = {}
    inbound: dict[str, list[str]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        s, t = text_of(edge.get("source")), text_of(edge.get("target"))
        label = text_of(edge.get("label")) or text_of((edge.get("data") or {}).get("label"))
        if not label.strip():
            reasons.append(f"unlabeled edge {s} -> {t}")
        # An edge without a unique id and type "custom" is not a usable
        # transition. Webhook nodes route on responsePathways and globals on
        # their label, so this silently breaks ONLY conversational routing:
        # the node composes a reply and never moves. Observed live on v28.
        if not text_of(edge.get("id")).strip():
            reasons.append(
                f"edge {s} -> {t} ({label!r}) has no id, so it cannot be traversed and the "
                f"source node will answer the patient but never transition"
            )
        if edge.get("type") != "custom":
            reasons.append(f"edge {s} -> {t} ({label!r}) is not type 'custom'")
        adjacency.setdefault(s, []).append((t, label))
        inbound.setdefault(t, []).append(s)

    for slot in ("1", "2"):
        if f"n_book_{slot}" not in [t for t, _ in adjacency.get(f"n_verify_{slot}", [])]:
            reasons.append(f"n_verify_{slot} does not route to n_book_{slot} (R5)")
        confirm = [lbl for tgt, lbl in adjacency.get(f"n_book_{slot}", []) if tgt == "n_confirm"]
        if not confirm:
            reasons.append(f"n_book_{slot} has no edge to n_confirm")
        else:
            # R5: confirmation must be reached only by an explicit positive signal.
            # $.success is a JSON boolean and booleans never match a string literal,
            # so an integer http status is the reliable signal.
            pathways = data_of(by_id[f"n_book_{slot}"]).get("responsePathways") or []
            positive = [
                pw for pw in pathways
                if isinstance(pw, list) and len(pw) >= 4
                and isinstance(pw[3], dict) and pw[3].get("id") == "n_confirm"
            ]
            if not positive:
                reasons.append(f"n_book_{slot} has no responsePathway reaching n_confirm (R5)")
            for pw in positive:
                if pw[1] != "==":
                    reasons.append(
                        f"n_book_{slot} reaches confirmation on a {pw[1]!r} comparison. Confirmation "
                        f"must require an explicit positive match, never a complement (R5)"
                    )
            catchall = [pw for pw in pathways if isinstance(pw, list) and len(pw) >= 4 and pw[1] == "!="]
            for pw in catchall:
                if isinstance(pw[3], dict) and pw[3].get("id") == "n_confirm":
                    reasons.append(
                        f"n_book_{slot} puts its complement on n_confirm, so an unknown signer "
                        f"response would tell the patient they are booked (R5)"
                    )

    # R4: the pre-booking waiting states wire the timeout to the no-reply exit.
    timeout_sources = set(inbound.get("e_timeout", []))
    for waiting in ("n_offer", "n_negotiate"):
        if waiting in by_id and waiting not in timeout_sources:
            reasons.append(f"{waiting} has no explicit edge to e_timeout (R4)")

    # R4a: silence AFTER a booking is success, not a no-reply.
    if "n_confirm" in by_id:
        confirm_targets = {t for t, _ in adjacency.get("n_confirm", [])}
        if "e_timeout" in confirm_targets:
            reasons.append(
                "n_confirm routes its timeout to e_timeout. Most booked patients never reply to a "
                "confirmation, so the ordinary success path would record no_reply and the booking "
                "rate would read near zero (R4a). Route it to e_booked."
            )
        if "e_booked" not in confirm_targets:
            reasons.append("n_confirm has no edge to e_booked (R4a)")

    # R10: routing must cover counts above one, not sweep them into a zero-openings node.
    for node_id in ("n_availability", "n_search"):
        node = by_id.get(node_id)
        if node is None:
            continue
        ops = [
            pw[1] for pw in (data_of(node).get("responsePathways") or [])
            if isinstance(pw, list) and len(pw) >= 4 and pw[0] == "slot_count"
        ]
        if not any(op in (">=", ">") for op in ops):
            reasons.append(
                f"{node_id} has no >= or > route on slot_count, so a response reporting three or "
                f"more openings falls to whatever the complement catches, which may be a node "
                f"written for the no-openings case (R10)"
            )

    # R11: a comparison value is a plain literal, never a template.
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for pw in (data_of(node).get("responsePathways") or []):
            if isinstance(pw, list) and len(pw) >= 4 and isinstance(pw[2], str) and "{{" in pw[2]:
                reasons.append(
                    f"{node.get('id')} compares {pw[0]!r} against the template {pw[2]!r}. Whether "
                    f"the platform interpolates a template on the right-hand side of a routing "
                    f"condition is unproven, and a guard that never fires is worse than none (R11)"
                )

    if "n_office" in by_id and "e_office" not in {t for t, _ in adjacency.get("n_office", [])}:
        reasons.append("n_office has no outgoing edge to e_office")
    if not inbound.get("e_declined"):
        reasons.append("e_declined is unreachable; a plain decline has nowhere to go")
    if "n_offer" in by_id and "e_declined" not in {t for t, _ in adjacency.get("n_offer", [])}:
        reasons.append("n_offer has no decline edge to e_declined")

    exempt = set(starts) | {AUTO_RETURN_GLOBAL} | set(TAKEOVER_GLOBALS)
    for node_id in by_id:
        if node_id not in exempt and node_id not in inbound:
            reasons.append(f"{node_id} is orphaned: no edge leads to it")

    # --- telemetry ----------------------------------------------------------
    analysis = graph.get("analysis_options") or graph.get("analysisOptions")
    if not analysis:
        reasons.append("graph has no analysis_options")
    else:
        blob = json.dumps(analysis).lower()
        for value in ("declined", "faq_answered"):
            if value not in blob:
                reasons.append(f"analysis_options must carry {value!r}")

    if reasons:
        fail(reasons)

    print("V22 GRAPH CHECK PASSED (map-derived contract)")
    print(f"  nodes: {len(nodes)} (ceiling {MAX_NODES})")
    print(f"  edges: {len(edges)} (ceiling {MAX_EDGES})")
    print(f"  silent steps with a failure exit: {len(SILENT_NODES)}/{len(SILENT_NODES)}")
    print(f"  auto-return global: {AUTO_RETURN_GLOBAL}; takeover globals: {len(TAKEOVER_GLOBALS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
