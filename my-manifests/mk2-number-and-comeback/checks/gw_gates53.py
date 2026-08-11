#!/usr/bin/env python3
"""Lane-53 live probes: article-less fortnight, spelled ordinals, tail-end month.

Prints one GATE53= line per case plus EXPECT53_* dates computed from today.
Env: GW_TOKEN.
"""

import datetime
import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, user_text
    ("fortnight-no-article", "fortnight from now", "not this wk, fortnight from now"),
    ("spelled-twentyseventh", "the twenty-seventh", "I meant the twenty-seventh"),
    ("tail-end-next-month", "tail end of next month", "shoot for the tail end of next month pls"),
]


def auth_header():
    raw = os.environ["GW_TOKEN"].strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
    return raw if raw.lower().startswith("bearer") else "Bearer " + raw


def post(frm, user_text):
    body = {
        "store": "711", "from": frm, "to": frm, "after": "none", "before": "none",
        "time_pref": "none", "slot_minutes": "15", "callID": "gw-gates53",
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
    print("EXPECT53_FORTNIGHT_LO=%s" % (today + datetime.timedelta(days=14)).strftime("%m/%d/%Y"))
    print("EXPECT53_FORTNIGHT_HI=%s" % (today + datetime.timedelta(days=16)).strftime("%m/%d/%Y"))
    if today.day < 27:
        o27 = today.replace(day=27)
    else:
        o27 = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=27)
    print("EXPECT53_ORD27=%s" % o27.strftime("%m/%d/%Y"))
    for label, frm, user_text in CASES:
        status, result = post(frm, user_text)
        print("GATE53=%s STATUS=%s first=%s count=%s unresolved=%s err=%s" % (
            label, status, result.get("first_start"), result.get("count"),
            result.get("from_unresolved"), (result.get("err") or "")[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
