#!/usr/bin/env python3
"""Fire ONE real sample SMS to the dummy test subject, fail-closed on version.

External send. Coordinator-only: this is never run by a Ringer worker.

Preflight refuses unless the agent number is actually bound to the Mott
pathway at the version we mean to test, because /v1/sms/send takes no
pathway_version -- the text runs whatever is live on the line, so an
unverified binding silently tests the wrong version.

usage:
  send_rachel_sample.py --agent-number +14158778905 --version 87 [--send]

Without --send it stops after the preflight and prints the payload.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.bland.ai"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"
START_NODE = "n_identity"


def key():
    raw = os.environ.get("BLAND_API_KEY", "").strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), "")
    if not raw:
        sys.exit("BLAND_API_KEY missing; run under the approved secret wrapper")
    return raw


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path, data=data, method="POST" if data else "GET",
        headers={"Authorization": key(), "Content-Type": "application/json",
                 "User-Agent": "mybcat-cli"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]


def preflight(agent_number, want_version):
    status, body = call("/v1/sms/numbers")
    if status != 200 or not isinstance(body, dict):
        sys.exit(f"cannot read SMS numbers: HTTP {status} {str(body)[:200]}")
    for row in body.get("data") or []:
        if row.get("phone_number") != agent_number:
            continue
        cfg = row.get("sms_config") or {}
        got_pid, got_ver = cfg.get("pathway_id"), cfg.get("pathway_version")
        print(f"line {agent_number} ({row.get('label')}) -> pathway {got_pid} v{got_ver}")
        if got_pid != PATHWAY_ID:
            sys.exit(f"REFUSED: line is on pathway {got_pid}, expected {PATHWAY_ID}")
        if got_ver != want_version:
            sys.exit(f"REFUSED: line is on v{got_ver}, expected v{want_version} — "
                     "repoint it in the Bland dashboard first (/v1/sms/update is 500)")
        return
    sys.exit(f"REFUSED: {agent_number} is not an SMS number on this account")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-number", required=True)
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    for var in ("HARNESS_PATIENT_ID", "HARNESS_PATIENT_CELL", "HARNESS_STORE"):
        if not os.environ.get(var, "").strip():
            sys.exit(f"{var} not set")
    pid = os.environ["HARNESS_PATIENT_ID"].strip()
    cell = os.environ["HARNESS_PATIENT_CELL"].strip()
    store = os.environ["HARNESS_STORE"].strip()

    preflight(args.agent_number, args.version)

    payload = {
        "user_number": "+1" + cell if not cell.startswith("+") else cell,
        "agent_number": args.agent_number,
        "new_conversation": True,
        "start_node_id": START_NODE,
        "request_data": {"recall_patient_id": pid, "recall_cell": cell, "store": store},
    }
    redacted = json.loads(json.dumps(payload))
    redacted["user_number"] = "***" + cell[-4:]
    redacted["request_data"] = {"recall_patient_id": "***", "recall_cell": "***", "store": store}
    print("payload:", json.dumps(redacted))

    if not args.send:
        print("DRY RUN — preflight passed, nothing sent. Re-run with --send.")
        return

    status, body = call("/v1/sms/send", payload)
    print("HTTP", status)
    print(json.dumps(body, indent=1)[:600] if isinstance(body, dict) else str(body)[:400])
    ok = isinstance(body, dict) and not body.get("errors")
    data = body.get("data") if isinstance(body, dict) else None
    ok = ok and isinstance(data, dict) and (
        data.get("status") in {"processing", "queued", "success", "created"}
        or data.get("conversation_id"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
