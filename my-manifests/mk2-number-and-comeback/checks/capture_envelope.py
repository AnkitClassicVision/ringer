#!/usr/bin/env python3
"""Capture FULL raw Bland chat envelopes plus the stored graph for one pathway version.

Platform-diff measurement (goal-loop round 6). Drives the scripted turns
["hi", "thursday please"] against a pinned pathway version and writes every
raw response body to disk. Judgment-free: PASS means the capture is complete,
never that the flow behaved.

Redaction before anything touches disk:
- dict keys matching auth/token/secret/password/api_key are replaced by a
  length+sha8 fingerprint so a differ can still tell present/absent/changed;
- digit runs of 7+ inside strings are masked to their last four.
"""

import hashlib
import json
import os
import re
import sys
import urllib.request

API = "https://api.bland.ai"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"
SENSITIVE = re.compile(r"(?i)(auth|token|secret|password|api_?key)")


def unwrap_key(raw):
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
        except Exception:
            pass
    return raw


def fingerprint(value):
    text = str(value)
    digest = hashlib.sha256(text.encode()).hexdigest()[:8]
    return f"[REDACTED:len={len(text)},sha8={digest}]"


def redact(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if SENSITIVE.search(str(k)) and isinstance(v, (str, int, float)):
                out[k] = fingerprint(v)
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, str):
        return re.sub(r"\d{7,}", lambda m: "***" + m.group(0)[-4:], obj)
    return obj


def call(method, path, api_key, payload=None):
    req = urllib.request.Request(
        API + path,
        data=(json.dumps(payload).encode() if payload is not None else None),
        method=method,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "User-Agent": "mybcat-platform-diff",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(redact(obj), f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    if len(sys.argv) != 3:
        print("usage: capture_envelope.py <pathway_version> <outdir>", file=sys.stderr)
        return 1
    version = int(sys.argv[1])
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    api_key = unwrap_key(os.environ["BLAND_API_KEY"])

    graph = call("GET", f"/v1/pathway/{PATHWAY_ID}/version/{version}", api_key)
    dump(os.path.join(outdir, "graph.json"), graph)
    print(f"GRAPH_FETCHED version={version}")

    create_body = call(
        "POST",
        "/v1/pathway/chat/create",
        api_key,
        {
            "pathway_id": PATHWAY_ID,
            "pathway_version": version,
            "request_data": {
                "recall_patient_id": os.environ["HARNESS_PATIENT_ID"],
                "recall_cell": os.environ.get("HARNESS_PATIENT_CELL"),
                "store": os.environ.get("HARNESS_STORE", "711"),
                "campaign": "harness",
            },
        },
    )
    dump(os.path.join(outdir, "create.json"), create_body)
    chat_id = create_body["data"]["chat_id"]
    print(f"CHAT_CREATED keys={sorted(create_body['data'].keys())}")

    turns = ["hi", "thursday please"]
    if os.environ.get("CAPTURE_TURNS"):
        turns = json.loads(os.environ["CAPTURE_TURNS"])
        assert isinstance(turns, list) and all(isinstance(t, str) for t in turns)
        assert not any(t.strip().lower() in ("1", "yes") for t in turns), "booking turn refused"
    for index, turn in enumerate(turns, start=1):
        resp = call("POST", f"/v1/pathway/chat/{chat_id}", api_key, {"message": turn})
        dump(os.path.join(outdir, f"turn{index}.json"), resp)
        data = resp.get("data") or {}
        print(f"TURN={index} keys={sorted(data.keys())} node={data.get('current_node_id')}")

    print(f"CAPTURE_COMPLETE version={version} turns={len(turns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
