#!/usr/bin/env python3
"""Send the recall opener to a CSV list of REAL patients, fail-closed on version.

External send. Coordinator-only: this is never run by a Ringer worker.
PHI discipline: reads the CSV at runtime; prints ONLY masked values (last-4 of
cell / patient id, no names). Never echoes rows.

usage:
  send_recall_list.py --csv "/path/list.csv" --agent-number +1509... --version 124 [--store 711] [--send]

Without --send: preflight + validated masked plan only.
CSV columns (header required): NAME_LAST, NAME_FIRST, MOBILE_PHONE, PATIENT_ID.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.bland.ai"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"
START_NODE = "n_identity"
TEST_CELLS = {"6157793629", "6468942428"}
TEST_PIDS = {"4362694474", "4376662466"}


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
        return e.code, e.read().decode(errors="replace")[:300]


def preflight(agent_number, want_version):
    status, body = call("/v1/sms/numbers")
    if status != 200 or not isinstance(body, dict):
        sys.exit(f"cannot read SMS numbers: HTTP {status}")
    for row in body.get("data") or []:
        if row.get("phone_number") != agent_number:
            continue
        cfg = row.get("sms_config") or {}
        got_pid, got_ver = cfg.get("pathway_id"), cfg.get("pathway_version")
        print(f"line {agent_number} -> pathway {got_pid} v{got_ver}")
        if got_pid != PATHWAY_ID:
            sys.exit(f"REFUSED: line is on unexpected pathway")
        if got_ver != want_version:
            sys.exit(f"REFUSED: line is on v{got_ver}, expected v{want_version}")
        return
    sys.exit(f"REFUSED: {agent_number} is not an SMS number on this account")


def load_rows(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    need = {"MOBILE_PHONE", "PATIENT_ID"}
    if rows and not need.issubset(rows[0].keys()):
        sys.exit(f"REFUSED: CSV missing columns {sorted(need - set(rows[0].keys()))}")
    plan, seen, skips = [], set(), []
    for i, r in enumerate(rows, start=2):
        cell = re.sub(r"\D", "", str(r.get("MOBILE_PHONE", "")))
        if len(cell) == 11 and cell.startswith("1"):
            cell = cell[1:]
        pid = re.sub(r"\D", "", str(r.get("PATIENT_ID", "")))
        m = f"cell=***{cell[-4:]} pid=***{pid[-4:]}"
        if len(cell) != 10 or not pid:
            skips.append(f"row{i}: INVALID ({m})")
            continue
        if cell in TEST_CELLS or pid in TEST_PIDS:
            skips.append(f"row{i}: TEST-IDENTITY excluded ({m})")
            continue
        if cell in seen or pid in seen:
            skips.append(f"row{i}: DUPLICATE ({m})")
            continue
        seen.add(cell)
        seen.add(pid)
        plan.append((i, pid, cell))
    return plan, skips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--agent-number", required=True)
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument("--store", default="711")
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    preflight(args.agent_number, args.version)
    plan, skips = load_rows(args.csv)
    for s in skips:
        print("SKIP", s)
    print(f"PLAN: {len(plan)} sends, {len(skips)} skipped, store={args.store}")
    for i, pid, cell in plan:
        print(f"  row{i}: cell=***{cell[-4:]} pid=***{pid[-4:]}")
    if not args.send:
        print("DRY RUN — preflight passed, nothing sent. Re-run with --send.")
        return
    if not plan:
        sys.exit("REFUSED: empty plan")
    ok = fail = 0
    for i, pid, cell in plan:
        payload = {
            "user_number": "+1" + cell,
            "agent_number": args.agent_number,
            "new_conversation": True,
            "start_node_id": START_NODE,
            "request_data": {"recall_patient_id": pid, "recall_cell": cell, "store": args.store},
        }
        status, body = call("/v1/sms/send", payload)
        conv = ""
        if isinstance(body, dict):
            conv = str(((body.get("data") or {}) if isinstance(body.get("data"), dict) else {}).get("conversation_id", ""))
        if status == 200 and conv:
            ok += 1
            print(f"SENT row{i} cell=***{cell[-4:]} conv={conv}")
        else:
            fail += 1
            print(f"SEND_FAIL row{i} cell=***{cell[-4:]} HTTP {status} {str(body)[:120]}")
        time.sleep(2)
    print(f"DONE sent={ok} failed={fail}")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
