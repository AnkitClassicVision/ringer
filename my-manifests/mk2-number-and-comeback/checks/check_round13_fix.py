#!/usr/bin/env python3
"""Executable check for the round-13 goal-loop fix (offered-date searches,
clock-time gate labels, per-branch verbatim confirms).

Proves, with WHY on failure:
1. worker validator PASSES the new draft and FAILS the untouched v103 draft
   with a structured assertion citation (no tracebacks);
2. structural floor (independent parse, .nodes[] iteration):
   - FIVE availability webhooks: n_goal_search (time_pref none),
     n_goal_search_latest (latest), n_goal_search_anchor (anchor={{goal_anchor}}),
     n_goal_search_offered_latest (latest, from==to=='{{slot_1_start}}'),
     n_goal_search_offered_time (none, from==to=='{{slot_1_start}}');
   - every availability body within the ten-field gateway contract;
   - edges from n_goal_response to offered_latest (label mentions offered+latest)
     and offered_time (label mentions offered + time preference);
   - gate edges (n_gate_1/2) labels include a clock-time clause;
   - per-branch confirms: n_confirm_1 copy contains {{slot_1_start}} and is the
     success target of n_book_1; n_confirm_2 contains {{slot_2_start}} for
     n_book_2; no shared LLM-freeform booked message remains (a node named
     n_confirm must not be targeted by both books);
   - user-wait feeders of each availability webhook cover its body {{vars}}
     minus runtime vars and slot_* (webhook-produced, persisted);
   - no silent Default feeding a webhook; n_goal_update absent; no 'retain'
     in any extractVars; no '[REDACTED' anywhere; five production extractors
     on n_goal_response byte-equal stored v96 n_ask.
3. DEBUG.md mentions confirm, gate, and offered-date changes.
"""

import json
import re
import subprocess
import sys

ALLOWED_BODY_FIELDS = {
    "store", "from", "to", "after", "before", "time_pref",
    "slot_minutes", "callID", "user_text", "user_verbatim",
}
RUNTIME_VARS = {"callID", "lastUserMessage", "store"}
SEARCH_SPECS = {
    "n_goal_search": {"time_pref": "none"},
    "n_goal_search_latest": {"time_pref": "latest"},
    "n_goal_search_anchor": {"time_pref": "anchor={{goal_anchor}}"},
    "n_goal_search_offered_latest": {"time_pref": "latest", "from": "{{slot_1_start}}", "to": "{{slot_1_start}}"},
    "n_goal_search_offered_time": {"time_pref": "none", "from": "{{slot_1_start}}", "to": "{{slot_1_start}}"},
}
V96_EXTRACTOR_NAMES = ["user_verbatim", "preference_from", "day_part", "time_after", "preference_to"]


def run_validator(validator, draft):
    proc = subprocess.run([sys.executable, validator, "--draft", draft],
                          capture_output=True, text=True, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def nodes_and_edges(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("nodes"), list):
            return obj["nodes"], obj.get("edges", [])
        for value in obj.values():
            found = nodes_and_edges(value)
            if found:
                return found
    return None


def extract_map(data):
    out = {}
    for item in data.get("extractVars") or []:
        if isinstance(item, (list, tuple)) and item:
            out[item[0]] = item
        elif isinstance(item, dict) and item.get("name"):
            out[item["name"]] = item
    return out


def main():
    if len(sys.argv) != 7:
        print("usage: check_round13_fix.py <validator.py> <new_draft> <v103_draft> <v96_graph.json> <DEBUG.md>")
        return 1
    validator, new_draft, v103_draft, v96_graph_path, frozen_path, debug_md = sys.argv[1:]
    failures = []

    rc_new, out_new = run_validator(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator does not pass new draft (rc={rc_new}): {out_new[-300:]}")
    rc_old, out_old = run_validator(validator, v103_draft)
    if rc_old == 0:
        failures.append("validator still PASSES the v103 draft - round-13 assertions toothless")
    elif "Traceback" in out_old:
        failures.append(f"validator crashes on v103 draft: {out_old[-200:]}")
    elif not re.search(r"(?i)assertion\s*#?\s*(6|7|8|9|10|11|12|13)", out_old):
        failures.append(f"v103 failure does not cite an assertion: {out_old[-200:]}")

    try:
        graph = json.load(open(new_draft, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: new draft unreadable: {exc}")
        return 1
    if "[REDACTED" in json.dumps(graph):
        failures.append("draft contains a leaked [REDACTED...] placeholder")

    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])
    if "n_goal_update" in nodes:
        failures.append("n_goal_update reappeared")
    for nid, node in nodes.items():
        ev = node.get("data", {}).get("extractVars")
        if ev and "retain" in json.dumps(ev).lower():
            failures.append(f"extractors on {nid} carry 'retain' semantics")

    avail = {nid: n for nid, n in nodes.items()
             if n.get("type") == "Webhook" and str(n.get("data", {}).get("url", "")).endswith("/availability")}
    if set(avail) != set(SEARCH_SPECS):
        failures.append(f"availability webhooks are {sorted(avail)}; expected {sorted(SEARCH_SPECS)}")

    for nid, want in SEARCH_SPECS.items():
        node = avail.get(nid)
        if node is None:
            continue
        data = node.get("data", {})
        body_raw = str(data.get("body", ""))
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            failures.append(f"{nid} body is not valid JSON template")
            continue
        extra = set(body) - ALLOWED_BODY_FIELDS
        if extra:
            failures.append(f"{nid} body outside gateway contract: {sorted(extra)}")
        for field, value in want.items():
            if body.get(field) != value:
                failures.append(f"{nid} {field} is {body.get(field)!r}, expected {value!r}")
        if not data.get("responseData"):
            failures.append(f"{nid} responseData missing/empty")

        consumed = set(re.findall(r"{{\s*([A-Za-z0-9_.]+)\s*}}", body_raw)) - RUNTIME_VARS
        consumed = {v for v in consumed if not v.startswith("slot_")}
        for edge in edges:
            if edge.get("target") != nid:
                continue
            src = nodes.get(edge.get("source"))
            if src is None:
                failures.append(f"edge into {nid} from unknown node {edge.get('source')}")
                continue
            if src.get("type") == "Webhook":
                continue
            sdata = src.get("data", {})
            if sdata.get("userWait") is False:
                failures.append(f"silent Default {edge.get('source')} feeds {nid}")
                continue
            missing = consumed - set(extract_map(sdata))
            if missing:
                failures.append(f"{edge.get('source')} -> {nid}: missing extractors {sorted(missing)}")

    resp_edges = {e.get("target"): e for e in edges if e.get("source") == "n_goal_response"}
    lab = lambda t: str(((resp_edges.get(t) or {}).get("data") or {}).get("label", "")).lower()
    if "n_goal_search_offered_latest" not in resp_edges:
        failures.append("no edge n_goal_response -> n_goal_search_offered_latest")
    elif "offered" not in lab("n_goal_search_offered_latest") or "latest" not in lab("n_goal_search_offered_latest"):
        failures.append(f"offered-latest label weak: {lab('n_goal_search_offered_latest')[:100]}")
    if "n_goal_search_offered_time" not in resp_edges:
        failures.append("no edge n_goal_response -> n_goal_search_offered_time")
    elif "offered" not in lab("n_goal_search_offered_time") or "time preference" not in lab("n_goal_search_offered_time"):
        failures.append(f"offered-time label weak: {lab('n_goal_search_offered_time')[:100]}")
    for gate in ("n_gate_1", "n_gate_2"):
        if gate in resp_edges and "clock time" not in lab(gate):
            failures.append(f"{gate} edge label lacks clock-time clause: {lab(gate)[:100]}")

    for idx in ("1", "2"):
        cid = f"n_confirm_{idx}"
        cnode = nodes.get(cid)
        if cnode is None:
            failures.append(f"{cid} missing")
            continue
        copy_text = json.dumps(cnode.get("data", {}))
        if f"{{{{slot_{idx}_start}}}}" not in copy_text:
            failures.append(f"{cid} copy does not template slot_{idx}_start verbatim")
        book = nodes.get(f"n_book_{idx}")
        routed = any(e.get("source") == f"n_book_{idx}" and e.get("target") == cid for e in edges)
        if book and not routed:
            rp = json.dumps(book.get("data", {}).get("responsePathways") or [])
            if cid not in rp:
                failures.append(f"n_book_{idx} success does not route to {cid}")
    both = [e for e in edges if e.get("target") == "n_confirm" and e.get("source") in ("n_book_1", "n_book_2")]
    if len(both) > 1 or ("n_confirm" in nodes and not any(f"n_confirm_{i}" in nodes for i in ("1", "2"))):
        failures.append("shared freeform n_confirm still serves both book branches")

    v96 = nodes_and_edges(json.load(open(v96_graph_path, encoding="utf-8")))
    v96_extract = extract_map(next(n for n in v96[0] if n.get("id") == "n_ask").get("data", {}))
    frozen = extract_map({"extractVars": json.load(open(frozen_path, encoding="utf-8"))})
    resp_extract = extract_map(nodes.get("n_goal_response", {}).get("data", {}))
    for name in V96_EXTRACTOR_NAMES:
        if name not in resp_extract:
            failures.append(f"n_goal_response missing extractor {name}")
        elif json.dumps(resp_extract[name], sort_keys=True) != json.dumps(frozen.get(name), sort_keys=True):
            failures.append(f"extractor {name} does not match the round-13 frozen pin")
    for name in ("user_verbatim", "day_part", "time_after"):
        if json.dumps(frozen.get(name), sort_keys=True) != json.dumps(v96_extract.get(name), sort_keys=True):
            failures.append(f"frozen {name} drifted from v96 (only preference_from/to may change)")
    for name in ("preference_from", "preference_to"):
        desc = json.dumps(frozen.get(name, "")).lower()
        if not (re.search(r"leav|away|out of town|won.t be back|unavailab", desc) and re.search(r"come in|return|available|back", desc)):
            failures.append(f"frozen {name} lacks the availability-interpretation rule (departure phrases -> date patient CAN come)")
        if "week of" not in desc or "that week" not in desc:
            failures.append(f"frozen {name} lacks the anaphoric-week rule ('monday that week' -> 'monday the week of MM/DD/YYYY')")
    if "OFFER-INTEGRITY" not in str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", "")):
        failures.append("n_goal_response prompt lacks the OFFER-INTEGRITY containment marker")
    for nid in SEARCH_SPECS:
        node = avail.get(nid)
        if node is not None and "from_unresolved" not in json.dumps(node.get("data", {}).get("responseData") or []):
            failures.append(f"{nid} responseData lacks from_unresolved mapping")
    prompt_len = len(str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", "")))
    if prompt_len > 4100:
        failures.append(f"n_goal_response prompt still {prompt_len} chars (budget 4100) - compression not achieved")
    for e in edges:
        if e.get("source") == "n_goal_response":
            lab = str((e.get("data") or {}).get("label", ""))
            if not lab.strip():
                failures.append(f"edge {e.get('id')} lost its label")

    mixed = nodes.get("n_mixed_intent")
    if mixed is None:
        failures.append("n_mixed_intent missing")
    else:
        if mixed.get("type") != "Default" or mixed.get("data", {}).get("userWait") is not True:
            failures.append("n_mixed_intent must be a user-wait Default node")
        mtargets = {e.get("target") for e in edges if e.get("source") == "n_mixed_intent"}
        for need in ("n_gate_1", "n_gate_2", "n_goal_search"):
            if need not in mtargets:
                failures.append(f"n_mixed_intent has no route to {need}")
    mi_edge = next((e for e in edges if e.get("source") == "n_goal_response" and e.get("target") == "n_mixed_intent"), None)
    if mi_edge is None:
        failures.append("no edge n_goal_response -> n_mixed_intent")
    else:
        mlab = str((mi_edge.get("data") or {}).get("label", "")).lower()
        if "both" not in mlab or "different" not in mlab:
            failures.append(f"mixed-intent edge label weak: {mlab[:100]}")
    ask = nodes.get("n_goal_ask")
    if ask is None:
        failures.append("n_goal_ask missing (stage split absent)")
    else:
        adata = ask.get("data", {})
        if ask.get("type") != "Default" or adata.get("userWait") is not True:
            failures.append("n_goal_ask must be a user-wait Default")
        if "{{slot_" in str(adata.get("prompt", "")):
            failures.append("n_goal_ask prompt contains slot templates - pre-offer node could fabricate offers")
        if len(str(adata.get("prompt", ""))) > 2200:
            failures.append("n_goal_ask prompt over 2200-char budget")
        amiss = {"user_verbatim", "preference_from", "preference_to"} - set(extract_map(adata))
        if amiss:
            failures.append(f"n_goal_ask missing extractors {sorted(amiss)}")
    ask_out = [e for e in edges if e.get("source") == "n_goal_ask"]
    resp_out = [e for e in edges if e.get("source") == "n_goal_response"]
    if len(ask_out) > 6:
        failures.append(f"n_goal_ask has {len(ask_out)} outbound edges (max 6 for router reliability)")
    if len(resp_out) > 8:
        failures.append(f"n_goal_response has {len(resp_out)} outbound edges (max 8)")
    for nid, want_min in (("n_goal_search", 1),):
        srcs = {e.get("source") for e in edges if e.get("target") == nid}
        if "n_goal_ask" not in srcs:
            failures.append("n_goal_ask has no route to n_goal_search")
    for nid in SEARCH_SPECS:
        node = avail.get(nid)
        if node is None:
            continue
        rp = json.dumps(node.get("data", {}).get("responsePathways") or [])
        if "n_goal_response" not in rp:
            failures.append(f"{nid} success path does not reach n_goal_response")
    none_lab = str(((next((e for e in edges if e.get("source") == "n_goal_ask" and e.get("target") == "n_goal_search"), {}) or {}).get("data") or {}).get("label", "")).lower()
    if "only a time" not in none_lab or ("no date" not in none_lab and "no day" not in none_lab):
        failures.append(f"none-search edge label lacks pre-offer time-only coverage: {none_lab[:140]}")
    if "works for me" not in none_lab:
        failures.append("none-search edge label lacks the agreement-phrased time example ('3pm works for me')")
    for tgt in ("n_goal_search_offered_time", "n_goal_search_offered_latest"):
        tedge = next((e for e in edges if e.get("source") == "n_goal_response" and e.get("target") == tgt), None)
        tl = str(((tedge or {}).get("data") or {}).get("label", "")).lower()
        if "after an opening has been offered" not in tl:
            failures.append(f"{tgt} edge label not conditioned on an existing offer: {tl[:120]}")
    for nid in SEARCH_SPECS:
        node = avail.get(nid)
        if node is None:
            continue
        rd = json.dumps(node.get("data", {}).get("responseData") or [])
        if "out_of_hours" not in rd:
            failures.append(f"{nid} responseData lacks out_of_hours mapping")
    if "out_of_hours" not in str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", "")):
        failures.append("n_goal_response prompt has no out_of_hours honesty branch")

    try:
        debug = open(debug_md, encoding="utf-8").read().lower()
        for word in ("extract", "prompt", "compress"):
            if word not in debug:
                failures.append(f"DEBUG.md does not document the {word} change")
    except OSError as exc:
        failures.append(f"DEBUG.md unreadable: {exc}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: round-13 fix verified (offered-date searches, clock-time gates, per-branch verbatim confirms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
