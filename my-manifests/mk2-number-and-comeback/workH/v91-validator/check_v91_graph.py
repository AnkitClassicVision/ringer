#!/usr/bin/env python3
"""Mechanical validator for the SPEC-v91 pathway graph."""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque


ALLOWED_BUCKETS = {"D1", "D2", "D3", "D4", "layout", "stale-base residue"}
NEW_IDS = {"e_defer", "n_appt_check", "n_reconcile_1", "n_reconcile_2",
           "e_booked_recovered", "e_book_unknown"}
MUTABLE_NODES = {"n_identity", "n_confirm", "n_office", "n_faq", "e_existing",
                 "n_book_1", "n_book_2", "e_booking_failed", "n_ask", "n_offer_3"}
MUTABLE_EDGES = {
    "edge-n_identity-n_ask-count-1",
    "edge-n_confirm-n_office-change-requested-after-confirmation",
    "edge-n_book_1-e_booking_failed-book-success-true",
    "edge-n_book_2-e_booking_failed-book-success-true",
}
AVAIL = ("n_search", "n_page_2", "n_page_3", "n_page_near")
EXTRACT_NODES = {"n_ask", "n_date_conflict", "n_miss_empty", "n_miss_unread",
                 "n_miss_thin", "n_miss_unbookable", "n_miss_time", "n_negotiate", "n_clarify"}
PHONE_NODES = {"e_book_unknown", "e_booked_recovered", "e_booking_failed", "e_declined",
               "e_defer", "e_existing", "e_not_me", "e_office", "e_safe_failure",
               "e_safe_identity", "e_stop", "n_confirm", "n_faq", "n_help",
               "n_miss_empty", "n_miss_unread", "n_office"}
CLOSE = "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"
DEFER = "For that you'll have to contact the MK2 Optical office at (212) 219-2219"
D4 = ("These are the latest openings you have been shown for that day, and you have not been shown "
      "everything the day holds. If they ask for something later, do NOT claim this is the latest "
      "the office has and do NOT say the day has nothing later, because you have not been told that. "
      "Do not name any other time. Offer to look at another day instead, and take the path for a different day.")


def same(a, b):
    return json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(b, sort_keys=True, separators=(",", ":"))


def load(path, failures, label):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        failures.append(f"{label}: cannot read valid JSON at {path}: {exc}")
        return {}


def field_diff(base, ref):
    """Return spec classification keys at node/edge top-field and data-field granularity."""
    out = set()
    for collection in ("nodes", "edges"):
        bm = {x.get("id"): x for x in base.get(collection, []) if isinstance(x, dict)}
        rm = {x.get("id"): x for x in ref.get(collection, []) if isinstance(x, dict)}
        for ident in bm.keys() | rm.keys():
            if ident not in bm or ident not in rm:
                out.add((ident, "__object__"))
                continue
            for key in bm[ident].keys() | rm[ident].keys():
                if key == "data" and isinstance(bm[ident].get(key), dict) and isinstance(rm[ident].get(key), dict):
                    for dk in bm[ident][key].keys() | rm[ident][key].keys():
                        if not same(bm[ident][key].get(dk), rm[ident][key].get(dk)):
                            out.add((ident, "data." + dk))
                elif not same(bm[ident].get(key), rm[ident].get(key)):
                    out.add((ident, key))
    for key in base.keys() | ref.keys():
        if key not in {"nodes", "edges"} and not same(base.get(key), ref.get(key)):
            out.add(("__top__", key))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--v88-ref", required=True)
    parser.add_argument("--classification", required=True)
    args = parser.parse_args()
    failures, warnings = [], []
    base = load(args.base, failures, "base")
    draft = load(args.draft, failures, "draft")
    ref = load(args.v88_ref, failures, "v88 reference")
    classification = load(args.classification, failures, "classification")
    bn = {n.get("id"): n for n in base.get("nodes", []) if isinstance(n, dict)}
    dn = {n.get("id"): n for n in draft.get("nodes", []) if isinstance(n, dict)}
    rn = {n.get("id"): n for n in ref.get("nodes", []) if isinstance(n, dict)}
    be = {e.get("id"): e for e in base.get("edges", []) if isinstance(e, dict)}
    de = {e.get("id"): e for e in draft.get("edges", []) if isinstance(e, dict)}

    # 1-3 structure and required nodes.
    if len(draft.get("nodes", [])) != 48: failures.append(f"[1] nodes: expected count 48, got {len(draft.get('nodes', []))}")
    if len(draft.get("edges", [])) != 125: failures.append(f"[1] edges: expected count 125, got {len(draft.get('edges', []))}")
    missing = sorted(set(bn) - set(dn)); extras = sorted(set(dn) - set(bn))
    if missing: failures.append(f"[2] nodes: missing v86 node ids {missing}")
    if set(extras) != NEW_IDS: failures.append(f"[2] nodes: new ids expected {sorted(NEW_IDS)}, got {extras}")
    for ident in ("n_date_conflict", "n_help"):
        if ident not in dn: failures.append(f"[3] node {ident}: required node is missing")
    if "n_help" in dn:
        data = dn["n_help"].get("data", {})
        for field in ("isGlobal", "enableGlobalAutoReturn"):
            if data.get(field) is not True: failures.append(f"[3] node n_help data.{field}: expected true, got {data.get(field)!r}")
        if any(e.get("source") == "n_help" for e in draft.get("edges", [])): failures.append("[3] node n_help: expected zero outgoing edges")
        if "(212) 219-2219" not in json.dumps(data, ensure_ascii=False): failures.append("[3] node n_help data: office number is missing")

    # 4-6 immutable objects and edge integrity.
    for ident in sorted(set(bn) - MUTABLE_NODES):
        if ident in dn and not same(bn[ident], dn[ident]): failures.append(f"[4] node {ident}: immutable v86 node differs (including layout fields)")
    for ident in sorted(set(be) - MUTABLE_EDGES):
        if ident not in de: failures.append(f"[5] edge {ident}: immutable v86 edge is missing")
        elif not same(be[ident], de[ident]): failures.append(f"[5] edge {ident}: immutable v86 edge differs")
    edge_ids = [e.get("id") for e in draft.get("edges", []) if isinstance(e, dict)]
    for ident, count in Counter(edge_ids).items():
        if count > 1: failures.append(f"[6] edge id {ident}: duplicate appears {count} times")
    for i, edge in enumerate(draft.get("edges", [])):
        loc = edge.get("id", f"index {i}") if isinstance(edge, dict) else f"index {i}"
        if not isinstance(edge, dict): failures.append(f"[6] edge {loc}: must be an object"); continue
        if edge.get("type") != "custom": failures.append(f"[6] edge {loc} field type: expected 'custom', got {edge.get('type')!r}")
        for field in ("source", "target"):
            if edge.get(field) not in dn: failures.append(f"[6] edge {loc} field {field}: unresolved node id {edge.get(field)!r}")

    # 7-9 pathway/edge consistency, literal typing, top-level preservation.
    edges_by_pair = defaultdict(list)
    for edge in draft.get("edges", []):
        if isinstance(edge, dict): edges_by_pair[(edge.get("source"), edge.get("target"))].append(edge)
    for ident, node in dn.items():
        for i, path in enumerate(node.get("data", {}).get("responsePathways", []) or []):
            if not isinstance(path, list) or len(path) < 4 or not isinstance(path[3], dict):
                failures.append(f"[7] node {ident} data.responsePathways[{i}]: malformed pathway"); continue
            dest = path[3].get("id"); label = f"{path[0]} {path[1]} {path[2]}"
            matches = edges_by_pair[(ident, dest)]
            if not any(e.get("data", {}).get("label") == label for e in matches): failures.append(f"[7] node {ident} data.responsePathways[{i}]: no edge to {dest!r} with label {label!r}")
            if not isinstance(path[2], str): failures.append(f"[8] node {ident} data.responsePathways[{i}][2]: comparison literal must be JSON string, got {type(path[2]).__name__}")
    for field in ("analysis_options", "entity_schemas", "memory_enabled", "post_call_actions"):
        if not same(base.get(field), draft.get(field)): failures.append(f"[9] top-level {field}: differs from v86")

    # 10-16 availability and retry semantics.
    bodies = {}
    for ident in AVAIL:
        raw = dn.get(ident, {}).get("data", {}).get("body")
        try: bodies[ident] = json.loads(raw)
        except Exception as exc: failures.append(f"[10] node {ident} data.body: invalid JSON: {exc}"); bodies[ident] = {}
        for field, value in (("callID", "{{callID}}"), ("after", "{{time_after}}"), ("user_text", "{{lastUserMessage}}"), ("user_verbatim", "{{user_verbatim}}")):
            if bodies[ident].get(field) != value: failures.append(f"[10] node {ident} data.body field {field}: expected {value!r}, got {bodies[ident].get(field)!r}")
    prefs = {"n_search": "none", "n_page_2": "afternoon", "n_page_3": "late", "n_page_near": "afternoon"}
    for ident, expected in prefs.items():
        if bodies.get(ident, {}).get("time_pref") != expected: failures.append(f"[11] node {ident} data.body field time_pref: expected {expected!r}, got {bodies.get(ident, {}).get('time_pref')!r}")
    for ident, node in dn.items():
        raw = node.get("data", {}).get("body")
        if isinstance(raw, str):
            try:
                if json.loads(raw).get("after") == "none": failures.append(f"[11] node {ident} data.body field after: must not be 'none'")
            except Exception: pass
        for j, entry in enumerate(node.get("data", {}).get("responseData", []) or []):
            path = entry.get("data") if isinstance(entry, dict) else None
            if isinstance(path, str) and re.search(r"slots\[(?!0\]|1\])\d+\]", path): failures.append(f"[12] node {ident} data.responseData[{j}].data: forbidden hardcoded slot index in {path!r}")
    for ident in AVAIL:
        response = {x.get("name"): x.get("data") for x in dn.get(ident, {}).get("data", {}).get("responseData", []) if isinstance(x, dict)}
        for name, path in (("slot_1_day_name", "$.result.slots[0].day_name"), ("slot_2_day_name", "$.result.slots[1].day_name")):
            if response.get(name) != path: failures.append(f"[13] node {ident} data.responseData {name}: expected {path!r}, got {response.get(name)!r}")
    def has_path(src, var, op, val, dest):
        return any(p[:3] == [var, op, val] and len(p) >= 4 and p[3].get("id") == dest for p in dn.get(src, {}).get("data", {}).get("responsePathways", []) if isinstance(p, list) and len(p) >= 4 and isinstance(p[3], dict))
    for requirement in (("n_search", "date_conflict_detected", "==", "conflict", "n_date_conflict"), ("n_date_conflict", None, None, None, "n_search")):
        src, var, op, val, dest = requirement
        ok = has_path(src, var, op, val, dest) if var else any(p[3].get("id") == dest for p in dn.get(src, {}).get("data", {}).get("responsePathways", []) if isinstance(p, list) and len(p) >= 4 and isinstance(p[3], dict))
        if not ok: failures.append(f"[14] node {src} data.responsePathways: required route to {dest} is missing")
    response = {x.get("name"): x.get("data") for x in dn.get("n_search", {}).get("data", {}).get("responseData", []) if isinstance(x, dict)}
    for name in ("date_conflict_detected", "conflict_option_1", "conflict_option_2"):
        if name not in response: failures.append(f"[14] node n_search data.responseData: missing extraction {name}")
    for ident in ("n_page_2", "n_page_3"):
        if not has_path(ident, "time_pref_relaxed", "!=", "", "n_offer_near"): failures.append(f"[15] node {ident} data.responsePathways: missing time_pref_relaxed != '' route to n_offer_near")
    retries = {**{x: 1 for x in AVAIL}, **{x: 0 for x in ("n_book_1", "n_book_2", "n_reconcile_1", "n_reconcile_2", "n_appt_check", "n_identity", "n_verify_1", "n_verify_2")}}
    for ident, expected in retries.items():
        got = dn.get(ident, {}).get("data", {}).get("modelOptions", {}).get("retryAttempts")
        if got != expected: failures.append(f"[16] node {ident} data.modelOptions.retryAttempts: expected {expected}, got {got!r}")
    for ident, node in dn.items():
        if '"verb":"appt.book"' in (node.get("data", {}).get("body") or "") and node.get("data", {}).get("modelOptions", {}).get("retryAttempts", 0) != 0: failures.append(f"[16] node {ident} data.modelOptions.retryAttempts: booking webhook must be 0")

    # 17-20 extraction and variable wiring.
    actual_extract = {ident for ident, node in dn.items() if "extractVars" in node.get("data", {})}
    if actual_extract != EXTRACT_NODES: failures.append(f"[17] nodes with data.extractVars: expected {sorted(EXTRACT_NODES)}, got {sorted(actual_extract)}")
    produced = set()
    for ident, node in dn.items():
        for entry in node.get("data", {}).get("extractVars", []) or []:
            if isinstance(entry, list) and entry: produced.add(entry[0])
        for entry in node.get("data", {}).get("responseData", []) or []:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str): produced.add(entry["name"])
    for ident in sorted(EXTRACT_NODES):
        entries = dn.get(ident, {}).get("data", {}).get("extractVars", []) or []
        by_name = {x[0]: x for x in entries if isinstance(x, list) and x}
        needed = {"user_verbatim"} | (set() if ident == "n_clarify" else {"time_after"})
        for name in needed:
            if name not in by_name: failures.append(f"[18] node {ident} data.extractVars: missing {name}")
            else:
                expected = next((x for x in bn.get(ident, {}).get("data", {}).get("extractVars", []) if x[0] == name), None)
                if expected is None or not same(by_name[name], expected): failures.append(f"[18] node {ident} data.extractVars entry {name}: not byte-identical to v86")
        if "time_after" in by_name and "Use none when no specific clock time was named" not in str(by_name["time_after"]): failures.append(f"[19] node {ident} data.extractVars entry time_after: required null-default sentence missing")
    builtins = {"callID", "lastUserMessage"}
    for ident, node in dn.items():
        body = node.get("data", {}).get("body")
        if isinstance(body, str):
            for var in re.findall(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}", body):
                if var not in builtins | produced: failures.append(f"[20] node {ident} data.body placeholder {{{{{var}}}}}: no extractVars/responseData producer and not a Bland built-in")

    # 21-25 SPEC-v88 invariants and graph reachability.
    for ident, dest in (("n_book_1", "n_reconcile_1"), ("n_book_2", "n_reconcile_2")):
        paths = dn.get(ident, {}).get("data", {}).get("responsePathways", [])
        if len(paths) < 3 or paths[2][:3] != ["book_success", "!=", "true"] or paths[2][3].get("id") != dest: failures.append(f"[21] node {ident} data.responsePathways[2]: expected book_success != true to {dest}")
        for i in (0, 1):
            bp = bn.get(ident, {}).get("data", {}).get("responsePathways", [])
            if len(paths) <= i or len(bp) <= i or not same(paths[i], bp[i]): failures.append(f"[21] node {ident} data.responsePathways[{i}]: differs from v86")
    expected_rd = [{"data": "$.ok", "name": "recon_ok"}, {"data": "$.result.count", "name": "recon_count"}]
    expected_rp = [["recon_ok", "!=", "true", {"id": "e_book_unknown", "name": "Reconcile read unavailable"}], ["recon_count", ">=", "1", {"id": "e_booked_recovered", "name": "EMR shows the booking exists"}], ["recon_count", "==", "0", {"id": "e_book_unknown", "name": "EMR shows no booking"}]]
    appt = dn.get("n_appt_check", {}).get("data", {})
    for ident in ("n_reconcile_1", "n_reconcile_2"):
        data = dn.get(ident, {}).get("data", {})
        for field in ("url", "headers", "body"):
            if not same(data.get(field), appt.get(field)): failures.append(f"[22] node {ident} data.{field}: differs from n_appt_check")
        if not same(data.get("responseData"), expected_rd): failures.append(f"[22] node {ident} data.responseData: expected exact recon_ok/recon_count mapping")
        if not same(data.get("responsePathways"), expected_rp): failures.append(f"[22] node {ident} data.responsePathways: expected conservative-first exact ordering")
    for ident in ("e_booked_recovered", "e_book_unknown"):
        expected = rn.get(ident, {}).get("data", {}).get("text")
        if dn.get(ident, {}).get("data", {}).get("text") != expected: failures.append(f"[23] node {ident} data.text: differs from SPEC-v88 reference")
    unknown_text = dn.get("e_book_unknown", {}).get("data", {}).get("text")
    if dn.get("e_booking_failed", {}).get("data", {}).get("text") != unknown_text: failures.append("[23] node e_booking_failed data.text: must equal e_book_unknown data.text")
    inbound = defaultdict(list)
    outgoing = defaultdict(list)
    for edge in draft.get("edges", []):
        if isinstance(edge, dict): inbound[edge.get("target")].append(edge.get("source")); outgoing[edge.get("source")].append(edge.get("target"))
    if inbound["e_booking_failed"]: failures.append(f"[23] node e_booking_failed: expected zero inbound edges, got sources {inbound['e_booking_failed']}")
    paths = appt.get("responsePathways", [])
    if not paths or paths[0][:3] != ["appt_count", ">=", "1"] or paths[0][3].get("id") != "e_defer": failures.append("[24] node n_appt_check data.responsePathways[0]: must be first and route appt_count >= 1 to e_defer")
    if set(inbound["e_booked_recovered"]) != {"n_reconcile_1", "n_reconcile_2"}: failures.append(f"[25] node e_booked_recovered: inbound/reaching sources must be only reconciles, got {sorted(set(inbound['e_booked_recovered']))}")
    if outgoing["e_defer"]: failures.append(f"[25] node e_defer: expected zero outgoing edges, got {outgoing['e_defer']}")
    if set(outgoing["n_confirm"]) != {"e_booked", "e_defer"}: failures.append(f"[25] node n_confirm adjacency: expected ['e_booked', 'e_defer'], got {sorted(set(outgoing['n_confirm']))}")
    forbidden = re.compile(r"^(n_search|n_page_|n_offer|n_verify_|n_book_|n_office$|n_faq$)")
    for start in ("n_confirm", "e_defer"):
        seen, q = set(), deque([start])
        while q:
            cur = q.popleft()
            for nxt in outgoing[cur]:
                if nxt not in seen: seen.add(nxt); q.append(nxt)
        bad = sorted(x for x in seen if forbidden.match(x))
        if bad: failures.append(f"[25] node {start}: forbidden path reaches {bad}")

    # 26-33 copy invariants.
    serialized = json.dumps(draft, ensure_ascii=False, sort_keys=True)
    if "855" in serialized: failures.append("[26] graph serialization: forbidden string '855' appears")
    carriers = {ident for ident, node in dn.items() if "(212) 219-2219" in json.dumps(node.get("data", {}), ensure_ascii=False)}
    if carriers != PHONE_NODES: failures.append(f"[27] office-number carrier nodes: expected {sorted(PHONE_NODES)}, got {sorted(carriers)}")
    if "e_booked" in carriers: failures.append("[27] node e_booked data: must not contain office number")
    close_nodes = {ident for ident, node in dn.items() if CLOSE in json.dumps(node, ensure_ascii=False)}
    if close_nodes != {"n_confirm", "e_booked_recovered"}: failures.append(f"[28] v62 CLOSE carrier nodes: expected ['e_booked_recovered', 'n_confirm'], got {sorted(close_nodes)}")
    defer_nodes = {ident for ident, node in dn.items() if DEFER in json.dumps(node, ensure_ascii=False)}
    if defer_nodes != {"e_defer"}: failures.append(f"[28] v62 DEFER carrier nodes: expected ['e_defer'], got {sorted(defer_nodes)}")
    ref_prompt = rn.get("n_ask", {}).get("data", {}).get("prompt", "")
    marker_a, marker_b = "TASK. Send this message with the patient's first name filled in:", "\n\nNEVER."
    greeting = ref_prompt[ref_prompt.find(marker_a):ref_prompt.find(marker_b)] if marker_a in ref_prompt and marker_b in ref_prompt else ""
    ask_prompt = dn.get("n_ask", {}).get("data", {}).get("prompt", "")
    if not greeting or greeting not in ask_prompt: failures.append("[29] node n_ask data.prompt: exact five-paragraph greeting block from v90 is missing")
    for phrase in ("ABSOLUTE RULE ON TIMES", "CONFLICT RULE"):
        if phrase not in ask_prompt: failures.append(f"[29] node n_ask data.prompt: missing {phrase!r}")
    absolute_v86 = {ident: node.get("data", {}).get("prompt") for ident, node in bn.items() if "ABSOLUTE RULE ON TIMES" in (node.get("data", {}).get("prompt") or "")}
    if len(absolute_v86) != 17: failures.append(f"[30] base fixture: expected 17 ABSOLUTE RULE prompts, found {len(absolute_v86)}")
    for ident, prompt in absolute_v86.items():
        expected_paragraphs = [p for p in prompt.split("\n\n") if "ABSOLUTE RULE ON TIMES" in p]
        actual = dn.get(ident, {}).get("data", {}).get("prompt") or ""
        for paragraph in expected_paragraphs:
            if paragraph not in actual: failures.append(f"[30] node {ident} data.prompt: v86 ABSOLUTE RULE ON TIMES paragraph is missing or changed")
    if "at MK2." in serialized: failures.append("[31] graph serialization: forbidden literal 'at MK2.' appears")
    count_brand = serialized.count("MK2 Optical")
    if count_brand < 60: failures.append(f"[31] graph serialization: expected at least 60 occurrences of 'MK2 Optical', got {count_brand}")
    offer3 = dn.get("n_offer_3", {}).get("data", {}).get("prompt", "")
    for phrase in ("as late as this day goes", "this is the latest", "the latest the office has"):
        if phrase in offer3: failures.append(f"[32] node n_offer_3 data.prompt: forbidden phrase {phrase!r} remains")
    if D4 not in offer3: failures.append("[32] node n_offer_3 data.prompt: exact D4 replacement sentence is missing")
    for ident in ("n_offer", "n_offer_2", "n_offer_3", "n_offer_near"):
        prompt = dn.get(ident, {}).get("data", {}).get("prompt", "")
        for num in (1, 2):
            if f"{{{{slot_{num}_start}}}}" in prompt and f"{{{{slot_{num}_day_name}}}}" not in prompt: failures.append(f"[33] node {ident} data.prompt: slot_{num}_start appears without slot_{num}_day_name")

    # 34 classification gate. OPEN entries warn separately and are pre-approved, not failures.
    expected_diffs = field_diff(base, ref)
    covered = set()
    if not isinstance(classification, dict): failures.append("[34] classification root: expected JSON object")
    else:
        open_items = classification.get("open", {})
        if open_items and not isinstance(open_items, dict):
            failures.append("[34] classification open: expected object keyed by OPEN-1/OPEN-2")
        for name in (open_items if isinstance(open_items, dict) else []):
            if name in {"OPEN-1", "OPEN-2"}:
                warnings.append(f"OPEN item {name}: listed separately; pre-approved item warns but does not automatically fail")
            else:
                failures.append(f"[34] classification open.{name}: only pre-approved OPEN-1 and OPEN-2 may remain open")
        for ident, fields in classification.items():
            if ident in {"open", "unclassified"}: continue
            if not isinstance(fields, dict): failures.append(f"[34] classification {ident}: expected field-to-bucket object"); continue
            for field, bucket in fields.items():
                if bucket not in ALLOWED_BUCKETS: failures.append(f"[34] classification {ident}.{field}: invalid bucket {bucket!r}; allowed {sorted(ALLOWED_BUCKETS)}")
                else: covered.add((ident, field))
        missing_cov = sorted(expected_diffs - covered)
        extra_cov = sorted(covered - expected_diffs)
        if missing_cov: failures.append(f"[34] classification coverage: missing {len(missing_cov)} v86-v90 field differences; first entries {missing_cov[:8]}")
        if extra_cov: failures.append(f"[34] classification coverage: {len(extra_cov)} entries do not correspond to v86-v90 differences; first entries {extra_cov[:8]}")
        unclassified = classification.get("unclassified", {})
        if unclassified: failures.append("[34] classification unclassified: must be empty")

    for warning in warnings: print(f" ! {warning}")
    for failure in failures: print(f" - {failure}")
    if failures:
        print(f"FAIL: {len(failures)} assertion failure(s)")
        return 1
    print("PASS: all 34 numbered assertions satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
