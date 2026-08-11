#!/usr/bin/env python3
"""Lane-56 live probes: verbatim day-part authority. Env: GW_TOKEN."""

import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, after, verbatim
    ("afternoon-dropped", "friday", "none", "Friday afternoon"),
    ("morning-control", "friday", "none", "friday morning"),
    ("greeting-guard", "friday", "none", "good afternoon, do you have friday?"),
]


def auth_header():
    raw = os.environ["GW_TOKEN"].strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
    return raw if raw.lower().startswith("bearer") else "Bearer " + raw


def post(frm, after, verbatim):
    body = {
        "store": "711", "from": frm, "to": frm, "after": after, "before": "none",
        "time_pref": "none", "slot_minutes": "15", "callID": "gw-gates56",
        "user_text": verbatim, "user_verbatim": verbatim,
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": auth_header()},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, (json.loads(resp.read().decode()).get("result") or {})
    except urllib.error.HTTPError as exc:
        return exc.code, {"err": exc.read().decode(errors="replace")[:120]}


def main():
    for label, frm, after, verbatim in CASES:
        status, result = post(frm, after, verbatim)
        print("GATE56=%s STATUS=%s first=%s count=%s err=%s" % (
            label, status, result.get("first_start"), result.get("count"),
            (result.get("err") or "")[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
