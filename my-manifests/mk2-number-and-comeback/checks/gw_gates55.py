#!/usr/bin/env python3
"""Lane-55 live probes: verbatim ordinal authority + that-weekday anaphor.

Era-bound (2026-08 test era): context 08/26/2026 (Wednesday) -> its week's
Thursday is 08/27/2026; the nearest future 27th is also 08/27/2026.
Prints one GATE55= line per case. Env: GW_TOKEN.
"""

import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, verbatim, context_date
    ("ordinal-dropped", "thursday next week", "No Thursday the 27", "08/26/2026 10:30 am"),
    ("that-weekday", "thursday", "How late can I come in that Thursday", "08/26/2026 10:30 am"),
    ("bare-weekday-control", "thursday", "how about thursday?", "08/26/2026 10:30 am"),
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
        "time_pref": "none", "slot_minutes": "15", "callID": "gw-gates55",
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
        print("GATE55=%s STATUS=%s first=%s count=%s err=%s" % (
            label, status, result.get("first_start"), result.get("count"),
            (result.get("err") or "")[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
