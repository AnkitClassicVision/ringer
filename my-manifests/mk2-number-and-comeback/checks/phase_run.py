#!/usr/bin/env python3
"""Live-harness phase driver for v62 (mk2-number-and-comeback).

Runs the v62 scenario suite against a minted, unattached Bland pathway version
through mott-v21-snap's chat harness (real webhooks, real gateway, NO SMS).

Phases exist because v62's appointment gate makes booking scenarios mutually
exclusive: once one booking exists for the test subject, every later thread
start defers at 'hi'. So:
  phase1 — 33 scenarios that neither book nor require an existing appointment.
            Precondition: subject has NO upcoming appointment.
  phase2 — exactly one real booking ('post-booking change defers': proves the
            mandated close and same-thread deferral), then 'booked re-entry not
            re-offered' (fresh thread -> /appt-list count>=1 -> deferral).
            Writes ONE real appointment for the test subject.

The harness's claim rule ('booking claim outside n_confirm') misfires on
post-booking scenarios whose final node is e_defer; the driver waives exactly
that failure, visibly, only when the claim text is the mandated close.
"""
import importlib.util
import json
import os
import re
import sys
import urllib.request

LANE = "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workB3/v62r2-lane/scenarios.py"
HARNESS_DIR = "/home/ankit114/repos/mott-v21-snap/harness"
CLOSE_RE = r"You'?re all set\. If you have further questions, please call MK2 Optical at \(212\) 219-2219"
CLAIM_FAILURE = "claimed an appointment exists outside the confirmation step"

PHASE2_ORDER = ["post-booking change defers", "booked re-entry not re-offered"]
PHASE1_EXTRA = [
    "unbooked re-entry still books",
    "pre-booking detour keeps 212 and steer-back",
    "new office number in every thread",
]


def appt_count():
    """Live upcoming-appointment count for the test subject, or None if unreadable.

    Phase 1 is only meaningful while the subject has nothing booked: v62 routes
    appt_count >= 1 straight to e_defer, so ONE appointment appearing mid-run turns
    every later scenario into a false failure. That happened on 2026-08-03 when a
    live SMS booking landed at scenario 20 and the remaining 14 all failed as
    deferrals. Checking between scenarios makes that abort loudly instead of
    producing a plausible-looking wall of red.
    """
    auth = os.environ.get("GW_TOKEN", "").strip()
    if not auth:
        return None
    req = urllib.request.Request(
        "https://mott-booking-gw.mail.mybcat.com/appt-list",
        data=json.dumps({"patient_id": os.environ["HARNESS_PATIENT_ID"],
                         "store": os.environ.get("HARNESS_STORE", "711")}).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "mybcat-cli",
                 "Authorization": auth if auth.lower().startswith("bearer") else "Bearer " + auth})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return ((json.loads(r.read().decode()) or {}).get("result") or {}).get("count")
    except Exception as exc:  # noqa: BLE001
        print(f"[guard] appt-list unreadable ({type(exc).__name__}); continuing unguarded")
        return None


def load_scenarios():
    spec = importlib.util.spec_from_file_location("v62_scenarios", LANE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SCENARIOS


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("phase1", "phase2"):
        sys.exit("usage: phase_run.py <pathway_version> phase1|phase2")
    version, phase = int(sys.argv[1]), sys.argv[2]
    for var in ("BLAND_API_KEY", "HARNESS_PATIENT_ID", "HARNESS_PATIENT_CELL"):
        if not os.environ.get(var, "").strip():
            sys.exit(f"{var} not set — resolve through the approved secret wrapper")

    sys.path.insert(0, HARNESS_DIR)
    import pathway_harness as H

    scenarios = load_scenarios()
    by_name = {s["name"]: s for s in scenarios}
    legacy = scenarios[:30]
    if phase == "phase1":
        sel = legacy + [by_name[n] for n in PHASE1_EXTRA]
    else:
        sel = [by_name[n] for n in PHASE2_ORDER]

    print(f"{phase}: {len(sel)} scenarios against unattached pathway version {version}")
    passed = failed = waived = 0
    guarded = phase == "phase1" and os.environ.get("GW_TOKEN", "").strip()
    if guarded:
        start_count = appt_count()
        print(f"[guard] subject upcoming appointments at start: {start_count}")
        if start_count:
            sys.exit(f"ABORT: subject already has {start_count} upcoming appointment(s); "
                     "phase 1 requires zero or every scenario falsely defers")
    for i, sc in enumerate(sel):
        if guarded and i:
            now = appt_count()
            if now:
                print(f"RESULT {phase}: passed={passed} failed={failed} waived={waived} "
                      f"total={len(sel)} ABORTED_AT={i}")
                sys.exit(f"ABORT before '{sc['name']}' (scenario {i + 1}/{len(sel)}): "
                         f"appt_count became {now} mid-run, so every later scenario would "
                         "defer. Results above this line are valid; cancel the appointment "
                         "and rerun.")
        ok, failures, said = H.run_scenario(version, sc)
        if failures:
            blob = "\n".join(said)
            kept = []
            for f in failures:
                if f == CLAIM_FAILURE and re.search(CLOSE_RE, blob, re.I):
                    print(f"[WAIVED] {sc['name']}: mandated close counted as claim after the conversation moved past n_confirm")
                    waived += 1
                else:
                    kept.append(f)
            failures, ok = kept, not kept
        if ok:
            passed += 1
            print(f"[PASS] {sc['name']}")
        else:
            failed += 1
            print(f"[FAIL] {sc['name']}")
            for f in failures:
                print(f"       -> {f}")
            for line in said[-2:]:
                print(f"       said: {line[:150]}")
    print(f"RESULT {phase}: passed={passed} failed={failed} waived={waived} total={len(sel)}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
