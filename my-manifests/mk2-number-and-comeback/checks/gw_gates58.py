#!/usr/bin/env python3
"""Lane-58 live probes: later-floor from context + Chinese day-parts.

Uses a Thursday probe day (08/06/2026, era-bound like the standing gates).
Prints one GATE58= line per case. Env: GW_TOKEN.
"""

import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, verbatim, context_date
    ("later-floored", "thursday", "Any other later time ?", "08/06/2026 10:30 am"),
    ("zh-afternoon", "thursday", "下午", ""),
    ("later-this-week-control", "thursday", "later this week works", "08/06/2026 10:30 am"),
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
        "time_pref": "none", "slot_minutes": "15", "callID": "gw-gates58",
        "user_text": verbatim, "user_verbatim": verbatim,
    }
    if context_date:
        body["context_date"] = context_date
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": auth_header()},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, (json.loads(resp.read().decode()).get("result") or {})
    except urllib.error.HTTPError as exc:
        return exc.code, {"err": exc.read().decode(errors="replace")[:120]}
    except Exception as exc:
        return 0, {"err": f"{type(exc).__name__}: {exc}"[:100]}


def main():
    for label, frm, verbatim, context_date in CASES:
        status, result = post(frm, verbatim, context_date)
        print("GATE58=%s STATUS=%s first=%s count=%s err=%s" % (
            label, status, result.get("first_start"), result.get("count"),
            (result.get("err") or "")[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
