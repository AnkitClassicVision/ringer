#!/usr/bin/env python3
"""Live failure-mode driver for v88's reconcile-never-lie booking path.

Drives ONE SMS chat conversation against an UNATTACHED pathway version through
Bland's chat harness (real webhooks, real gateway reads, no SMS, live line
untouched) and prints machine-checkable verdict lines. DUMMY subject only.

modes (usage: failure_mode_run.py <version> <mode>):
  unknown    v89 (book URL is a bogus path -> real nginx 404, write impossible).
             Expect the catch-all to route to reconciliation, the EMR read to
             show 0 appointments, and the conversation to end at e_book_unknown
             with the uncertainty copy. Proves: wire error + no commit -> truth.
  recovered  v89 again, but AFTER the slot offer arrives (and before 'yes') the
             driver books a real slot for the subject directly through the
             governed gateway. The pathway's book then 404s, reconciliation
             finds count>=1, and the conversation must end at e_booked_recovered
             with the mandated close. Reproduces the 2026-08-03 incident shape
             (write committed, caller saw an error) and proves the patient now
             hears the truth. The driver cancels the appointment afterward.
  happy      v88 (real /sign). Full booking: expect n_confirm's close and the
             booked outcome, an appointment in the EMR, then driver cancels it.
             Proves the mainline still works.

Prints: TURN/SAID trace, END_NODE=<id>, GW_COUNT_AFTER=<n>,
CLEANUP_FINAL_COUNT=<n> (modes that wrote), VERDICT: PASS|FAIL <reasons>.
Digit runs are masked except last 4. Exit 0 only on PASS with clean state.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HARNESS_DIR = "/home/ankit114/repos/mott-v21-snap/harness"
GW = "https://mott-booking-gw.mail.mybcat.com"
UNKNOWN_RE = r"wasn'?t able to confirm whether that booking went through"
CLOSE_RE = r"You'?re all set\. If you have further questions, please call MK2 Optical"


def mask(s):
    return re.sub(r"\d{4,}(?=\d{4})", "***", str(s))


def gw_call(path, payload, timeout=180):
    auth = os.environ.get("GW_TOKEN", "").strip()
    if not auth:
        sys.exit("GW_TOKEN not set")
    req = urllib.request.Request(
        GW + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "mybcat-cli",
                 "Authorization": auth if auth.lower().startswith("bearer") else "Bearer " + auth})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]


def gw_count(pid, store):
    status, body = gw_call("/appt-list", {"patient_id": pid, "store": store})
    if status != 200 or not isinstance(body, dict):
        return None, []
    res = body.get("result") or {}
    return res.get("count"), res.get("appointments") or []


def gw_cleanup(pid, store):
    """Cancel every upcoming appointment for the dummy subject; return final count."""
    for _ in range(3):
        count, appts = gw_count(pid, store)
        if count == 0:
            return 0
        if count is None:
            time.sleep(5)
            continue
        for a in appts:
            aid, day = a.get("appointment_id"), (a.get("start") or "")[:10]
            s, b = gw_call("/sign", {"verb": "appt.cancel", "target": aid, "store": store,
                                     "reason": "patient-request",
                                     "params": {"appt_id": aid, "day": day}})
            print(f"CLEANUP cancel ...{str(aid)[-4:]} -> HTTP {s}")
    count, _ = gw_count(pid, store)
    return count


def gw_direct_book(pid, store):
    """Book the first-available real slot for the dummy subject. Returns True on commit."""
    status, body = gw_call("/availability",
                           {"store": store, "first_available": "1", "slot_minutes": "15"})
    if status != 200 or not isinstance(body, dict):
        print(f"INJECT availability failed: HTTP {status}")
        return False
    slots = ((body.get("result") or {}).get("slots")) or []
    if not slots:
        print("INJECT no slots available")
        return False
    s0 = slots[0]
    status, body = gw_call("/sign", {
        "verb": "appt.book", "target": pid, "store": store, "reason": "new-booking",
        "params": {"doctor": s0.get("doctor_id"), "start": s0.get("start"),
                   "end": s0.get("end"), "type": os.environ.get("HARNESS_EXAM_TYPE", "674597395")}})
    ok = isinstance(body, dict) and body.get("success") is True
    print(f"INJECT direct book -> HTTP {status} success={ok}")
    if not ok:
        # a 502-with-commit is exactly the defect under study; check the source
        count, _ = gw_count(pid, store)
        ok = bool(count)
        print(f"INJECT post-book source check count={count}")
    return ok


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("unknown", "recovered", "happy"):
        sys.exit("usage: failure_mode_run.py <pathway_version> unknown|recovered|happy")
    version, mode = int(sys.argv[1]), sys.argv[2]
    for var in ("BLAND_API_KEY", "HARNESS_PATIENT_ID", "HARNESS_PATIENT_CELL"):
        if not os.environ.get(var, "").strip():
            sys.exit(f"{var} not set")
    pid = os.environ["HARNESS_PATIENT_ID"].strip()
    store = os.environ.get("HARNESS_STORE", "711").strip()

    sys.path.insert(0, HARNESS_DIR)
    import pathway_harness as H

    fails = []
    count0, _ = gw_count(pid, store)
    print(f"GW_COUNT_BEFORE={count0}")
    if count0 != 0:
        sys.exit(f"ABORT: subject has {count0} upcoming appointment(s); need 0")

    status, body = H.post("/v1/pathway/chat/create",
                          {"pathway_id": H.PATHWAY_ID, "pathway_version": version,
                           "request_data": dict(H.SUBJECT, campaign="harness")})
    if status != 200:
        sys.exit(f"chat create failed: HTTP {status} {mask(body)}")
    chat_id = body["data"]["chat_id"]

    turns = ["hi", "the first available time works", "1", "yes"]
    injected = mode != "recovered"
    node, said = None, []
    for turn in turns:
        status, body = H.post(f"/v1/pathway/chat/{chat_id}", {"message": turn})
        if status != 200:
            fails.append(f"turn {turn!r} failed: HTTP {status}")
            break
        data = body.get("data") or {}
        replies = data.get("assistant_responses") or []
        said.extend(replies)
        node = data.get("current_node_id") or node
        print(f"TURN {turn!r} -> node={node}")
        for r in replies:
            print(f"  SAID {mask(r)[:160]}")
        # recovered mode: once the offer is on the table, commit a real booking
        # behind the pathway's back, then let it 'yes' into the bogus URL.
        if not injected and turn == "1":
            if not gw_direct_book(pid, store):
                fails.append("recovered-mode injection could not create the appointment")
                break
            injected = True

    print(f"END_NODE={node}")
    blob = "\n".join(said)
    count_after, _ = gw_count(pid, store)
    print(f"GW_COUNT_AFTER={count_after}")

    expect = {"unknown": ("e_book_unknown", UNKNOWN_RE, 0),
              "recovered": ("e_booked_recovered", CLOSE_RE, 1),
              "happy": ("e_booked", CLOSE_RE, 1)}[mode]
    want_node, want_re, want_count = expect
    if node != want_node:
        fails.append(f"ended on {node!r}, expected {want_node!r}")
    if not re.search(want_re, blob, re.I):
        fails.append(f"never said anything matching /{want_re}/")
    if count_after != want_count:
        fails.append(f"GW count after = {count_after}, expected {want_count}")
    if mode == "unknown" and re.search(CLOSE_RE, blob, re.I):
        fails.append("unknown mode must never claim the patient is all set")

    if mode in ("recovered", "happy") or (count_after or 0) > 0:
        final = gw_cleanup(pid, store)
        print(f"CLEANUP_FINAL_COUNT={final}")
        if final != 0:
            fails.append(f"cleanup left {final} appointment(s) on the dummy account")

    if fails:
        print("VERDICT: FAIL " + " | ".join(fails))
        sys.exit(1)
    print(f"VERDICT: PASS mode={mode} end={node}")


if __name__ == "__main__":
    main()
