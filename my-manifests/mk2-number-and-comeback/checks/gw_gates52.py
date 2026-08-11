#!/usr/bin/env python3
"""Lane-52 live probes: anaphoric-week override at the HTTP seam.

Dates are era-bound like the standing gates (valid for the 2026-08 test era):
context 08/19/2026 -> its week's Monday is 08/17/2026; today's next Monday
is 08/10/2026. Prints one GATE52= line per case. Env: GW_TOKEN.
"""

import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, verbatim, context_date
    ("anaphor-next-week-wording", "monday next week",
     "What about Monday that week?", "08/19/2026 10:30 am"),
    ("anaphor-wrong-week-of", "monday the week of 08/12/2026",
     "What about Monday that week?", "08/19/2026 10:30 am"),
    ("no-anaphor-control", "monday next week",
     "how about monday next week?", "08/19/2026 10:30 am"),
]


def auth_header():
    raw = os.environ["GW_TOKEN"].strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
    return raw if raw.lower().startswith("bearer") else "Bearer " + raw


def post(frm, verbatim, context_date):
    body = {
        "store": "711", "from": frm, "to": frm, "after": "none", "before": "none",
        "time_pref": "none", "slot_minutes": "15", "callID": "gw-gates52",
        "user_text": verbatim, "user_verbatim": verbatim, "context_date": context_date,
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
    for label, frm, verbatim, context_date in CASES:
        status, result = post(frm, verbatim, context_date)
        print("GATE52=%s STATUS=%s first=%s count=%s err=%s" % (
            label, status, result.get("first_start"), result.get("count"),
            (result.get("err") or "")[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
