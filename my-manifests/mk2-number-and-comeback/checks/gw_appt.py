#!/usr/bin/env python3
"""Read/cancel helper against the live Mott booking gateway for the DUMMY test
account only. Auth comes from the environment (injected by the approved secret
wrapper); nothing is printed except appointment metadata for the dummy patient.

usage:
  gw_appt.py list <patient_id> <store> [--include-past]
  gw_appt.py cancel <patient_id> <store> <appt_id> <day>
"""
import json
import os
import sys
import urllib.request

BASE = "https://mott-booking-gw.mail.mybcat.com"


def call(path, payload):
    auth = os.environ.get("GW_TOKEN", "").strip()
    if not auth:
        sys.exit("GW_TOKEN not set — run through the approved secret wrapper")
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": auth if auth.lower().startswith("bearer") else "Bearer " + auth,
                 "User-Agent": "mybcat-cli"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]


def main():
    mode = sys.argv[1]
    if mode == "list":
        pid, store = sys.argv[2], sys.argv[3]
        payload = {"patient_id": pid, "store": store}
        if "--include-past" in sys.argv:
            payload["include_past"] = True
        status, body = call("/appt-list", payload)
        print("HTTP", status)
        if isinstance(body, dict):
            res = body.get("result") or {}
            print("ok:", body.get("ok"), "count:", res.get("count"))
            for a in (res.get("appointments") or [])[:10]:
                print({k: a.get(k) for k in ("id", "start", "store", "status", "type")})
        else:
            print(body)
    elif mode == "cancel":
        pid, store, appt_id, day = sys.argv[2:6]
        status, body = call("/cancel", {"store": store, "appt_id": appt_id, "day": day})
        print("HTTP", status)
        print(json.dumps(body, indent=1)[:600] if isinstance(body, dict) else body)
    else:
        sys.exit("unknown mode")


if __name__ == "__main__":
    main()
