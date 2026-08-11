#!/usr/bin/env python3
"""Lane-51 live probes: meridiem inference, midnight OOB, spelled-number relative.

Prints one GATE51= line per case plus EXPECT51_ELEVEN_LO/HI dates. Env: GW_TOKEN.
"""

import datetime
import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, time_pref, after, user_text
    ("around-five", "none", "anchor=5:00", "none", "around 5"),
    ("midnight", "thursday", "none", "12:00 am", "can I come at midnight"),
    ("eleven-days", "in eleven days", "none", "none", "I can do it in eleven days"),
]


def auth_header():
    raw = os.environ["GW_TOKEN"].strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
    return raw if raw.lower().startswith("bearer") else "Bearer " + raw


def post(frm, pref, after, user_text):
    body = {
        "store": "711", "from": frm, "to": frm, "after": after, "before": "none",
        "time_pref": pref, "slot_minutes": "15", "callID": "gw-gates51",
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
    today = datetime.date.today()
    print("EXPECT51_ELEVEN_LO=%s" % (today + datetime.timedelta(days=11)).strftime("%m/%d/%Y"))
    print("EXPECT51_ELEVEN_HI=%s" % (today + datetime.timedelta(days=13)).strftime("%m/%d/%Y"))
    for label, frm, pref, after, text in CASES:
        status, result = post(frm, pref, after, text)
        print("GATE51=%s STATUS=%s first=%s count=%s oob=%s unresolved=%s route=%s err=%s" % (
            label, status, result.get("first_start"), result.get("count"),
            result.get("out_of_hours"), result.get("from_unresolved"),
            result.get("anchor_route"), (result.get("err") or "")[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
