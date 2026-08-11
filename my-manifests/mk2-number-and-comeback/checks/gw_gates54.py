#!/usr/bin/env python3
"""Lane-54 live probes: verbatim meridiem authority + closed_day flag.

Era-bound dates like the other standing gates (2026-08 test era): Friday
08/07/2026 has afternoon slots; 08/15/2026 is a Saturday (clinic closed).
Prints one GATE54= line per case. Env: GW_TOKEN.
"""

import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, time_pref, user_text
    ("strip-invented-am", "08/07/2026", "anchor=3:00 am", "What about either 3 or 4"),
    ("keep-stated-am", "08/07/2026", "anchor=11:00 am", "11 am works"),
    ("closed-day-saturday", "08/15/2026", "none", "The 15th? Evening?"),
]


def auth_header():
    raw = os.environ["GW_TOKEN"].strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
    return raw if raw.lower().startswith("bearer") else "Bearer " + raw


def post(frm, pref, user_text):
    body = {
        "store": "711", "from": frm, "to": frm, "after": "none", "before": "none",
        "time_pref": pref, "slot_minutes": "15", "callID": "gw-gates54",
        "user_text": user_text, "user_verbatim": user_text,
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
    for label, frm, pref, user_text in CASES:
        status, result = post(frm, pref, user_text)
        print("GATE54=%s STATUS=%s first=%s count=%s closed=%s route=%s err=%s" % (
            label, status, result.get("first_start"), result.get("count"),
            result.get("closed_day"), result.get("anchor_route"),
            (result.get("err") or "")[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
