#!/usr/bin/env python3
"""Executable check for the round-7 goal-loop fix (edge labels + gateway contract).

Proves, with WHY on failure:
1. worker validator PASSES the new draft;
2. worker validator FAILS both prior drafts (v101-class and v102-class) with a
   structured 'assertion N' citation, no tracebacks;
3. structural floor, parsed independently via .nodes[] iteration:
   - exactly three availability search webhooks: n_goal_search (time_pref
     "none"), n_goal_search_latest ("latest"), n_goal_search_anchor
     ("anchor={{goal_anchor}}");
   - every availability body's fields are a subset of the gateway contract
     {store,from,to,after,before,time_pref,slot_minutes,callID,user_text,
     user_verbatim} - the round-6 400 came from an invented 'anchor' field;
   - the literal string 'retain' appears nowhere in the draft;
   - n_goal_response has edges to all three searches; the none-search edge
     label carries the proven v96 enumeration markers (weekday/weekend/time
     preference), the latest edge says latest;
   - every user-wait Default feeding an availability webhook owns extractVars
     covering that body's {{vars}} (minus runtime callID/lastUserMessage/
     store); no silent Default (userWait false) feeds one; n_goal_update absent;
   - the five production extractors on n_goal_response are BYTE-EQUAL to
     stored v96 n_ask's (fabrication discipline is inherited, not rewritten);
   - responseData non-empty on all three searches; no '[REDACTED' leak.
4. DEBUG.md mentions the body contract and edge labels.
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
SEARCHES = {
    "n_goal_search": "none",
    "n_goal_search_latest": "latest",
    "n_goal_search_anchor": "anchor={{goal_anchor}}",
}
V96_EXTRACTOR_NAMES = ["user_verbatim", "preference_from", "day_part", "time_after", "preference_to"]


def run_validator(validator, draft):
    proc = subprocess.run(
        [sys.executable, validator, "--draft", draft],
        capture_output=True, text=True, timeout=300,
    )
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
        print(
            "usage: check_round7_fix.py <validator.py> <new_draft> <v101_draft> "
            "<v102_draft> <v96_graph.json> <DEBUG.md>"
        )
        return 1
    validator, new_draft, v101_draft, v102_draft, v96_graph_path, debug_md = sys.argv[1:]
    failures = []

    rc_new, out_new = run_validator(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator does not pass new draft (rc={rc_new}): {out_new[-300:]}")
    for label, path in (("v101", v101_draft), ("v102", v102_draft)):
        rc, out = run_validator(validator, path)
        if rc == 0:
            failures.append(f"validator still PASSES the {label} draft - new assertions toothless")
        elif "Traceback" in out:
            failures.append(f"validator crashes on {label} draft: {out[-200:]}")
        elif not re.search(r"(?i)assertion\s*#?\s*[67]", out):
            failures.append(f"{label} failure does not cite assertion 6/7: {out[-200:]}")

    try:
        graph = json.load(open(new_draft, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: new draft unreadable: {exc}")
        return 1
    serialized = json.dumps(graph)
    if "[REDACTED" in serialized:
        failures.append("draft contains a leaked [REDACTED...] placeholder")

    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    for nid, node in nodes.items():
        ev = node.get("data", {}).get("extractVars")
        if ev and "retain" in json.dumps(ev).lower():
            failures.append(f"extractors on {nid} still carry 'retain' semantics (gateway rejects the sentinel)")
    edges = graph.get("edges", [])
    if "n_goal_update" in nodes:
        failures.append("n_goal_update reappeared")

    avail_nodes = {
        nid: n for nid, n in nodes.items()
        if n.get("type") == "Webhook" and str(n.get("data", {}).get("url", "")).endswith("/availability")
    }
    if set(avail_nodes) != set(SEARCHES):
        failures.append(f"availability webhooks are {sorted(avail_nodes)}; expected {sorted(SEARCHES)}")

    for nid, want_pref in SEARCHES.items():
        node = avail_nodes.get(nid)
        if node is None:
            continue
        data = node.get("data", {})
        body_raw = str(data.get("body", ""))
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            failures.append(f"{nid} body is not valid JSON template: {body_raw[:120]}")
            continue
        extra = set(body) - ALLOWED_BODY_FIELDS
        if extra:
            failures.append(f"{nid} body has fields outside the gateway contract: {sorted(extra)}")
        if body.get("time_pref") != want_pref:
            failures.append(f"{nid} time_pref is {body.get('time_pref')!r}, expected {want_pref!r}")
        if not data.get("responseData"):
            failures.append(f"{nid} responseData missing/empty")
        for target in [p.get("id") for p in data.get("responsePathways", []) if isinstance(p, dict)]:
            if target and target not in nodes:
                failures.append(f"{nid} responsePathway targets unknown node {target}")

        consumed = set(re.findall(r"{{\s*([A-Za-z0-9_.]+)\s*}}", body_raw)) - RUNTIME_VARS
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
                failures.append(f"silent Default {edge.get('source')} feeds {nid} - dead-hop pattern")
                continue
            missing = consumed - set(extract_map(sdata))
            if missing:
                failures.append(f"{edge.get('source')} -> {nid}: missing extractors {sorted(missing)}")

    resp_edges = {e.get("target"): e for e in edges if e.get("source") == "n_goal_response"}
    for nid in SEARCHES:
        if nid not in resp_edges:
            failures.append(f"no edge n_goal_response -> {nid}")
    none_label = str(((resp_edges.get("n_goal_search") or {}).get("data") or {}).get("label", "")).lower()
    for marker in ("weekday", "weekend", "time preference"):
        if marker not in none_label:
            failures.append(f"none-search edge label lacks proven v96 marker '{marker}': {none_label[:120]}")
    latest_label = str(((resp_edges.get("n_goal_search_latest") or {}).get("data") or {}).get("label", "")).lower()
    if "latest" not in latest_label:
        failures.append(f"latest-search edge label lacks 'latest': {latest_label[:120]}")

    v96 = nodes_and_edges(json.load(open(v96_graph_path, encoding="utf-8")))
    v96_ask = next(n for n in v96[0] if n.get("id") == "n_ask")
    v96_extract = extract_map(v96_ask.get("data", {}))
    resp_extract = extract_map(nodes.get("n_goal_response", {}).get("data", {})) if "n_goal_response" in nodes else {}
    for name in V96_EXTRACTOR_NAMES:
        if name not in resp_extract:
            failures.append(f"n_goal_response missing production extractor {name}")
        elif json.dumps(resp_extract[name], sort_keys=True) != json.dumps(v96_extract.get(name), sort_keys=True):
            failures.append(f"extractor {name} on n_goal_response is not byte-equal to stored v96 n_ask's")

    try:
        debug = open(debug_md, encoding="utf-8").read().lower()
        if "body" not in debug or "label" not in debug:
            failures.append("DEBUG.md does not document the body contract and edge labels")
    except OSError as exc:
        failures.append(f"DEBUG.md unreadable: {exc}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: round-7 fix verified (contract bodies, proven labels, production extractors, both old drafts rejected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
