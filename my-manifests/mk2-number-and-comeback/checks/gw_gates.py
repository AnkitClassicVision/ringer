#!/usr/bin/env python3
"""Live gateway gates for the Mott booking gateway.

Prints one GATE= line per case with the fields the checks assert. Env: GW_TOKEN.
"""

import datetime
import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

CASES = [
    # label, from, time_pref, after, user_text
    ("anchor-exact", "08/07/2026", "anchor=11:15 AM", "none", "1115"),
    ("anchor-offgrid", "08/07/2026", "anchor=11:20 AM", "none", "1120"),
    ("specificity", "08/27/2026", "none", "none", "No Thursday the 27"),
    ("ordinal", "thursday the 27", "none", "none", "No Thursday the 27"),
    ("anaphora", "monday the week of 08/18/2026", "none", "none", "What about Monday that week?"),
    ("away-override", "in 2 weeks", "none", "none",
     "I'm leaving town today and won't be back for 2 weeks about then?"),
    ("week-of-reg", "monday the week of 08/18/2026", "none", "none", None),
    ("relative-reg", "2 weeks from today", "none", "none", None),
    ("latest-reg", "thursday", "latest", "none", None),
    ("default-window", "none", "none", "03:00 pm", "3pm works for me"),
    ("oob-3am", "thursday", "none", "03:00 am", "can I come at 3am"),
]


def auth_header():
    raw = os.environ["GW_TOKEN"].strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
    return raw if raw.lower().startswith("bearer") else "Bearer " + raw


def post(frm, pref, after, user_text):
    text = user_text if user_text is not None else frm
    body = {
        "store": "711", "from": frm, "to": frm, "after": after, "before": "none",
        "time_pref": pref, "slot_minutes": "15", "callID": "gw-gates",
        "user_text": text, "user_verbatim": text,
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
    for label, frm, pref, after, text in CASES:
        status, result = post(frm, pref, after, text)
        print(
            f"GATE={label} STATUS={status} first={result.get('first_start')} "
            f"count={result.get('count')} exact={result.get('anchor_exact')} "
            f"oob={result.get('out_of_hours')} unresolved={result.get('from_unresolved')} "
            f"err={result.get('err', '')}"
        )
    expected = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%m/%d/%Y")
    print(f"EXPECT_RELATIVE_DATE={expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
