#!/usr/bin/env python3
"""A/B the week-anaphora turns across two pathway versions, N runs each.

usage: anaphora_ab.py <version_a> <version_b> <runs_each>

Env: BLAND_API_KEY (JSON envelope tolerated), HARNESS_PATIENT_ID/CELL/STORE.
Plays: hi -> "I'm out this week how about in two weeks?" ->
"What about Monday that week?" and prints one AB= line per run with the
dates spoken on turn 3. Exits 0 when every run completed 3 turns.
"""

import json
import os
import re
import sys
import urllib.request

API = "https://api.bland.ai"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"
TURNS = ["hi", "I'm out this week how about in two weeks?",
         "What about Monday that week?"]


def unwrap(raw):
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
        except Exception:
            pass
    return raw


def post(key, path, payload):
    req = urllib.request.Request(
        API + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": key, "Content-Type": "application/json",
                 "User-Agent": "mybcat-diag"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def one_run(key, version, request_data):
    created = post(key, "/v1/pathway/chat/create", {
        "pathway_id": PATHWAY_ID, "pathway_version": version,
        "request_data": request_data})
    chat_id = created["data"]["chat_id"]
    said = ""
    for turn in TURNS:
        reply = post(key, f"/v1/pathway/chat/{chat_id}", {"message": turn})
        data = reply.get("data") or {}
        said = " ".join(str(x) for x in (data.get("assistant_responses") or []))
    return sorted(set(re.findall(r"\d{2}/\d{2}/\d{4}", said))), said


def main():
    ver_a, ver_b, runs = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    key = unwrap(os.environ["BLAND_API_KEY"])
    request_data = {
        "recall_patient_id": os.environ["HARNESS_PATIENT_ID"],
        "recall_cell": os.environ.get("HARNESS_PATIENT_CELL"),
        "store": os.environ.get("HARNESS_STORE", "711"),
        "campaign": "harness",
    }
    completed = 0
    for version in (ver_a, ver_b):
        for i in range(runs):
            try:
                dates, said = one_run(key, version, request_data)
                print(f"AB=v{version} run={i + 1} turn3_dates={dates} said={said[:120]!r}")
                completed += 1
            except Exception as exc:
                print(f"AB=v{version} run={i + 1} ERROR={exc}")
    print(f"AB_DONE completed={completed} expected={2 * runs}")
    return 0 if completed == 2 * runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
