#!/usr/bin/env python3
"""Reproduce the round-6 gateway 400 offline and prove the accepted body contract.

POSTs three bodies to the gateway /availability endpoint:
  A. retain-laden body exactly as the v102 runtime sent it -> expect 400, capture WHY;
  B. v96-production body (time_pref none, no invented keys) -> expect 200 with slots;
  C. v96 body with time_pref latest (lane-38 reference-point path) -> expect 200.
Writes gw-repro.txt lines: CASE=<x> STATUS=<n> BODY=<first 300 chars>.
Env: GW_TOKEN (via secret wrapper), HARNESS_STORE.
"""

import json
import os
import sys
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"


def post(body):
    auth = os.environ["GW_TOKEN"].strip()
    if auth.startswith("{"):
        try:
            parsed = json.loads(auth)
            auth = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), auth)
        except Exception:
            pass
    if not auth.lower().startswith("bearer"):
        auth = "Bearer " + auth
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": auth},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()[:300]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")[:300]


def main():
    store = os.environ.get("HARNESS_STORE", "711")
    base = {
        "store": store,
        "from": "thursday",
        "to": "thursday",
        "after": "none",
        "before": "none",
        "slot_minutes": "15",
        "callID": "gw-body-repro",
        "user_text": "thursday",
        "user_verbatim": "thursday",
    }
    retain = dict(base)
    retain.update(
        {"time_pref": "retain", "anchor": "retain", "time_from": "retain", "time_to": "retain"}
    )
    v96 = dict(base)
    v96["time_pref"] = "none"
    latest = dict(base)
    latest["time_pref"] = "latest"

    with open("gw-repro.txt", "w") as f:
        for case, body in (("retain", retain), ("v96none", v96), ("latest", latest)):
            status, text = post(body)
            line = f"CASE={case} STATUS={status} BODY={' '.join(text.split())}"
            print(line)
            f.write(line + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
