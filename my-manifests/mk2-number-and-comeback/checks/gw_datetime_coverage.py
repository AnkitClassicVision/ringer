#!/usr/bin/env python3
"""Date/time verbiage coverage sweep against the live Mott gateway.

One line per case: DT=<label> cat=<category> first=<slot> n=<count>
unres=<from_unresolved> oob=<out_of_hours> closed=<closed_day> err=<...>
Then DT_DONE total=<n> http_ok=<n>. Env: GW_TOKEN.

This is a measurement probe: the checker asserts completeness (every case
answered HTTP 200); interpretation of the matrix is the coordinator's job.
Each case mirrors how the pathway calls /availability: extraction-style
`frm`/`pref`/`after` plus the patient's raw words in user_text/user_verbatim.
"""

import json
import os
import urllib.error
import urllib.request

URL = "https://mott-booking-gw.mail.mybcat.com/availability"

# label, category, from, time_pref, after, verbatim, context_date
CASES = [
    # --- absolute dates ---
    ("slash-date", "absolute", "8/27", "none", "none", "how about 8/27", ""),
    ("month-name", "absolute", "august 27", "none", "none", "august 27 works", ""),
    ("ordinal-th", "absolute", "the 27th", "none", "none", "the 27th", ""),
    ("spelled-ordinal", "absolute", "the twenty-seventh", "none", "none", "I meant the twenty-seventh", ""),
    ("ordinal-dropped-ex", "absolute", "thursday next week", "none", "none", "No Thursday the 27", "08/26/2026 10:30 am"),
    # --- weekdays ---
    ("bare-weekday", "weekday", "friday", "none", "none", "how about friday", ""),
    ("this-weekday", "weekday", "this friday", "none", "none", "this friday?", ""),
    ("next-weekday", "weekday", "next friday", "none", "none", "next friday pls", ""),
    ("abbrev-weekday", "weekday", "fri", "none", "none", "fri works", ""),
    # --- relative ---
    ("tomorrow", "relative", "tomorrow", "none", "none", "tomorrow", ""),
    ("day-after-tomorrow", "relative", "day after tomorrow", "none", "none", "day after tomorrow", ""),
    ("in-3-days", "relative", "in 3 days", "none", "none", "in 3 days", ""),
    ("in-2-weeks", "relative", "in 2 weeks", "none", "none", "in 2 weeks", ""),
    ("next-week", "relative", "next week", "none", "none", "sometime next week", ""),
    ("week-after-next", "relative", "week after next", "none", "none", "week after next", ""),
    ("fortnight-bare", "relative", "fortnight from now", "none", "none", "not this wk, fortnight from now", ""),
    ("in-a-month", "relative", "in a month", "none", "none", "in a month or so", ""),
    ("end-of-month", "relative", "end of the month", "none", "none", "end of the month", ""),
    ("beginning-next-month", "relative", "beginning of next month", "none", "none", "beginning of next month", ""),
    ("mid-month", "relative", "middle of next month", "none", "none", "middle of next month", ""),
    ("after-holiday", "relative", "after labor day", "none", "none", "after labor day", ""),
    # --- anaphoric (context = offered Wednesday 08/26) ---
    ("that-week", "anaphora", "monday next week", "none", "none", "What about Monday that week?", "08/26/2026 10:30 am"),
    ("that-weekday", "anaphora", "thursday", "none", "none", "How late can I come in that Thursday", "08/26/2026 10:30 am"),
    ("following-week", "anaphora", "the following week", "none", "none", "anything the following week?", "08/26/2026 10:30 am"),
    ("same-day-next-week", "anaphora", "same day next week", "none", "none", "same day next week?", "08/26/2026 10:30 am"),
    # --- clock times (Friday probe day) ---
    ("clock-pm", "clock", "friday", "anchor=3:00 pm", "none", "friday 3pm", ""),
    ("clock-colon", "clock", "friday", "anchor=4:30 pm", "none", "friday at 4:30", ""),
    ("bare-digits-1115", "clock", "friday", "anchor=11:15 AM", "none", "1115", ""),
    ("bare-hour-3", "clock", "friday", "anchor=3:00", "none", "What about either 3 or 4", ""),
    ("invented-am", "clock", "friday", "anchor=3:00 am", "none", "What about either 3 or 4", ""),
    ("military-1500", "clock", "friday", "anchor=15:00", "none", "1500 works", ""),
    ("noon", "clock", "friday", "anchor=12:00 pm", "none", "noon", ""),
    ("spelled-three", "clock", "friday", "anchor=3:00 am", "none", "three works for me", ""),
    ("half-past-four", "clock", "friday", "none", "none", "half past four", ""),
    ("quarter-to-five", "clock", "friday", "none", "none", "quarter to five", ""),
    # --- day parts ---
    ("afternoon-dropped", "daypart", "friday", "none", "none", "Friday afternoon", ""),
    ("morning", "daypart", "friday", "none", "none", "friday morning", ""),
    ("evening", "daypart", "thursday", "none", "none", "Thursday evening", ""),
    ("tonight", "daypart", "today", "none", "none", "tonight?", ""),
    ("after-lunch", "daypart", "friday", "none", "none", "friday after lunch", ""),
    ("first-thing", "daypart", "friday", "none", "none", "first thing friday", ""),
    ("after-work", "daypart", "friday", "none", "none", "friday after work", ""),
    ("lunchtime", "daypart", "friday", "none", "none", "around lunchtime friday", ""),
    # --- windows ---
    ("after-3", "window", "friday", "none", "03:00 pm", "friday after 3", ""),
    ("before-noon", "window", "friday", "none", "none", "friday before noon", ""),
    ("between-2-and-4", "window", "friday", "none", "none", "friday between 2 and 4", ""),
    ("no-earlier-than-3", "window", "friday", "none", "none", "friday no earlier than 3", ""),
    # --- earliest / latest ---
    ("earliest", "edge", "friday", "none", "none", "earliest you have", ""),
    ("latest", "edge", "friday", "latest", "none", "last appointment friday", ""),
    # --- exclusions / negation ---
    ("not-friday", "negation", "not friday", "none", "none", "any day but friday", ""),
    ("anything-but-monday", "negation", "anything but monday", "none", "none", "anything but monday", ""),
]


def auth_header():
    raw = os.environ["GW_TOKEN"].strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
    return raw if raw.lower().startswith("bearer") else "Bearer " + raw


def post(frm, pref, after, verbatim, context_date):
    body = {
        "store": "711", "from": frm, "to": frm, "after": after, "before": "none",
        "time_pref": pref, "slot_minutes": "15", "callID": "gw-dt-coverage",
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
        return exc.code, {"err": exc.read().decode(errors="replace")[:100]}
    except Exception as exc:  # timeouts/resets must yield a row, not kill the sweep
        return 0, {"err": f"{type(exc).__name__}: {exc}"[:100]}


def main():
    ok = 0
    for label, cat, frm, pref, after, verbatim, ctx in CASES:
        status, r = post(frm, pref, after, verbatim, ctx)
        if status == 200:
            ok += 1
        print("DT=%s cat=%s first=%s n=%s unres=%s oob=%s closed=%s err=%s" % (
            label, cat, r.get("first_start"), r.get("count"),
            r.get("from_unresolved"), r.get("out_of_hours"),
            r.get("closed_day"), (r.get("err") or "")[:60]))
    print("DT_DONE total=%d http_ok=%d" % (len(CASES), ok))
    return 0 if ok == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
