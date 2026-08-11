#!/usr/bin/env python3
"""Run the v94 goal-loop proof suite against an unattached pathway version."""
import json
import copy
import os
import re
import sys
import urllib.request

from goalloop_scenarios import SCENARIOS


HARNESS_DIR = "/home/ankit114/repos/mott-v21-snap/harness"
PROMISE_COPY = re.compile(
    r"(?:one moment|let me check|checking availability|please hold)", re.I
)
GOAL_FIELD_LEAK = re.compile(
    r"\b(?:scheduling_goal_v94|goal_from|goal_to|time_from|time_to|anchor|relation|"
    r"goal_status|goal_revision|goal_clarify_count|goal_ambiguity_key|last_offered_dates|"
    r"offer_id|offer_expires_at|selected_slot)\b", re.I
)
DATED_SLOT = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")


def appt_count():
    """Return upcoming appointment count, or None when the optional guard is unavailable."""
    auth = os.environ.get("GW_TOKEN", "").strip()
    if not auth:
        return None
    req = urllib.request.Request(
        "https://mott-booking-gw.mail.mybcat.com/appt-list",
        data=json.dumps({
            "patient_id": os.environ["HARNESS_PATIENT_ID"],
            "store": os.environ.get("HARNESS_STORE", "711"),
        }).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "mybcat-cli",
            "Authorization": auth if auth.lower().startswith("bearer") else "Bearer " + auth,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return ((json.loads(response.read().decode()) or {}).get("result") or {}).get("count")
    except Exception as exc:  # noqa: BLE001
        print(f"[guard] appt-list unreadable ({type(exc).__name__}); continuing unguarded")
        return None


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: phase_run_goalloop.py <pathway_version>")
    try:
        version = int(sys.argv[1])
    except ValueError:
        sys.exit("usage: phase_run_goalloop.py <pathway_version>")

    for var in ("BLAND_API_KEY", "HARNESS_PATIENT_ID", "HARNESS_PATIENT_CELL"):
        if not os.environ.get(var, "").strip():
            sys.exit(f"{var} not set — resolve through the approved secret wrapper")

    sys.path.insert(0, HARNESS_DIR)
    import pathway_harness as harness

    print(f"goalloop: {len(SCENARIOS)} scenarios against unattached pathway version {version}")
    passed = failed = 0
    guarded = bool(os.environ.get("GW_TOKEN", "").strip())
    if guarded:
        start_count = appt_count()
        print(f"[guard] subject upcoming appointments at start: {start_count}")
        if start_count:
            sys.exit(
                f"ABORT: subject already has {start_count} upcoming appointment(s); "
                "goal-loop proof requires zero"
            )

    for index, scenario in enumerate(SCENARIOS):
        if guarded and index:
            current_count = appt_count()
            if current_count:
                print(f"RESULT goalloop: passed={passed} failed={failed} waived=0 total={len(SCENARIOS)}")
                sys.exit(
                    f"ABORT before '{scenario['name']}' (scenario {index + 1}/{len(SCENARIOS)}): "
                    f"appt_count became {current_count} mid-run"
                )

        harness_scenario = copy.deepcopy(scenario)
        exact_week = harness_scenario.get("expect_week")
        if exact_week and re.fullmatch(r"\d{2}/\d{2}", exact_week):
            harness_scenario.pop("expect_week")
        ok, failures, said = harness.run_scenario(version, harness_scenario)
        blob = "\n".join(said)
        promise_hit = PROMISE_COPY.search(blob)
        if promise_hit:
            failures.append(f"used forbidden promise copy: {promise_hit.group(0)!r}")
        leak_hit = GOAL_FIELD_LEAK.search(blob)
        if leak_hit:
            failures.append(f"leaked an internal goal field: {leak_hit.group(0)!r}")
        if scenario.get("expect_dated_slots") and not DATED_SLOT.search(blob):
            failures.append("offer contained no dated slots")
        if exact_week and re.fullmatch(r"\d{2}/\d{2}", exact_week):
            if not re.search(rf"\b{re.escape(exact_week)}(?:/\d{{4}})?\b", blob):
                failures.append(f"offer contained no date in expected week/date {exact_week!r}")
        ok = ok and not failures

        if ok:
            passed += 1
            print(f"[PASS] {scenario['name']}")
        else:
            failed += 1
            print(f"[FAIL] {scenario['name']}")
            for failure in failures:
                print(f"       -> {failure}")
            for line in said[-2:]:
                print(f"       said: {line[:150]}")

    print(f"RESULT goalloop: passed={passed} failed={failed} waived=0 total={len(SCENARIOS)}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
