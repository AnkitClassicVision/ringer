#!/usr/bin/env python3
"""Executable check for the round-6 direct-webhook fix (goal-loop).

Proves, with WHY on every failure:
1. the worker's validator PASSES the new draft;
2. the worker's validator FAILS the old (round-5) draft citing assertion 6 -
   the new assertion is watched failing on the graph class it must catch;
3. structural floor on the new draft, parsed independently of the worker's
   validator, iterating .nodes[] directly (never recursive id search - stubs
   inside responsePathways shadow real nodes):
   - every edge into n_goal_search leaves a Webhook node or a user-wait
     Default node whose extractVars cover every variable the webhook body
     consumes (runtime-provided callID/lastUserMessage/store excluded);
   - no silent Default (userWait false) node has an edge into n_goal_search;
   - a direct edge n_goal_response -> n_goal_search exists;
   - the webhook itself is preserved: /availability URL, POST, non-empty
     responseData, headers present, body still consumes goal_anchor and
     goal_relation;
   - no '[REDACTED' string leaked into the draft;
4. DEBUG.md documents the convention (mentions n_goal_update and chat).
"""

import json
import re
import subprocess
import sys

RUNTIME_VARS = {"callID", "lastUserMessage", "store"}


def run_validator(validator, draft):
    proc = subprocess.run(
        [sys.executable, validator, "--draft", draft],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def extract_names(data):
    names = []
    for item in data.get("extractVars") or []:
        if isinstance(item, dict):
            names.append(item.get("name"))
        elif isinstance(item, (list, tuple)) and item:
            names.append(item[0])
    return {n for n in names if n}


def main():
    if len(sys.argv) != 5:
        print(
            "usage: check_direct_webhook_fix.py <validator.py> <new_draft.json> "
            "<old_draft.json> <DEBUG.md>"
        )
        return 1
    validator, new_draft, old_draft, debug_md = sys.argv[1:]
    failures = []

    rc_new, out_new = run_validator(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(
            f"validator does not pass the new draft (rc={rc_new}): {out_new[-300:]}"
        )
    rc_old, out_old = run_validator(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still PASSES the old round-5 draft - assertion 6 absent or toothless")
    elif "Traceback" in out_old:
        failures.append(f"validator crashes (not a structured FAIL) on old draft: {out_old[-300:]}")
    elif not re.search(r"(?i)assertion\s*#?\s*6", out_old):
        failures.append(f"old-draft failure does not cite assertion 6: {out_old[-300:]}")

    try:
        graph = json.load(open(new_draft, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: new draft unreadable: {exc}")
        return 1
    if "[REDACTED" in json.dumps(graph):
        failures.append("draft contains a leaked [REDACTED...] placeholder from capture files")

    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])
    search = nodes.get("n_goal_search")
    if search is None:
        failures.append("n_goal_search missing from .nodes[]")
    else:
        data = search.get("data", {})
        body = str(data.get("body", ""))
        consumed = set(re.findall(r"{{\s*([A-Za-z0-9_.]+)\s*}}", body)) - RUNTIME_VARS
        if not str(data.get("url", "")).endswith("/availability"):
            failures.append(f"webhook url changed: {data.get('url')}")
        if data.get("method") != "POST":
            failures.append(f"webhook method changed: {data.get('method')}")
        if not data.get("responseData"):
            failures.append("webhook responseData missing/empty")
        if not data.get("headers"):
            failures.append("webhook headers missing")
        for var in ("goal_anchor", "goal_relation"):
            if var not in consumed:
                failures.append(f"webhook body no longer consumes {var} (reference-point primitive lost)")

        sources = [e.get("source") for e in edges if e.get("target") == "n_goal_search"]
        if not sources:
            failures.append("no edges into n_goal_search at all")
        if "n_goal_response" not in sources:
            failures.append("no direct edge n_goal_response -> n_goal_search")
        for src in sources:
            node = nodes.get(src)
            if node is None:
                failures.append(f"edge into search from unknown node {src}")
                continue
            ntype = node.get("type")
            ndata = node.get("data", {})
            if ntype == "Webhook":
                continue
            if ntype == "Default" and ndata.get("userWait") is False:
                failures.append(
                    f"silent Default {src} (userWait false) still feeds n_goal_search - the dead-hop pattern"
                )
                continue
            missing = consumed - extract_names(ndata)
            if missing:
                failures.append(
                    f"user-wait source {src} does not extract webhook inputs: missing {sorted(missing)}"
                )

    try:
        debug = open(debug_md, encoding="utf-8").read().lower()
        if "n_goal_update" not in debug or "chat" not in debug:
            failures.append("DEBUG.md does not document the chat-mode dead-hop convention (must mention n_goal_update and chat)")
    except OSError as exc:
        failures.append(f"DEBUG.md unreadable: {exc}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: direct-webhook fix verified (validator green on new, assertion-6 red on old, structure sound)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
