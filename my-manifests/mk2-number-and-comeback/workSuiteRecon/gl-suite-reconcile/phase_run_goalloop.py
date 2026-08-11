#!/usr/bin/env python3
"""Run the reconciled goal-loop proof suite against an unattached pathway version."""
import json
import copy
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta

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
TIME = re.compile(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?\b", re.I)

# Populate this constant with the retired carrier literal when it is supplied.
# An empty value deliberately adds no guessed phone number to the proof contract.
RETIRED_CARRIER_NUMBER = ""
NEGATION = re.compile(
    r"\b(not|never|cannot|can't|won't|don't|doesn't|didn't|haven't|hasn't|isn't|aren't|"
    r"wasn't|weren't|no|none|nothing|unable|yet)\b", re.I
)


def _affirmative(text):
    return " ".join(
        sentence for sentence in re.split(r"(?<=[.!?])\s+", text)
        if not NEGATION.search(sentence)
    )


def _response_blob(turn_responses, check):
    turns = check.get("turns") or [check["turn"]]
    return "\n".join(
        response
        for turn in turns
        for response in turn_responses[turn - 1]
    )


def _dates(text):
    dates = []
    for raw in DATED_SLOT.findall(text):
        try:
            dates.append(datetime.strptime(raw, "%m/%d/%Y").date())
        except ValueError:
            continue
    return dates


def _normalized_date_strings(text):
    normalized = set(DATED_SLOT.findall(text))
    for raw in re.findall(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)", text):
        try:
            normalized.add(datetime.strptime(raw, "%Y-%m-%d").strftime("%m/%d/%Y"))
        except ValueError:
            continue
    return normalized


def _normalized_slots(text):
    slots = set()
    pattern = (r"(\d{2}/\d{2}/\d{4})\s+(1[0-2]|0?[1-9])"
               r"(?::([0-5]\d))?\s*([ap])\.?m\.?")
    for match in re.finditer(pattern, text, re.I):
        clock = f"{match.group(2)}:{match.group(3) or '00'} {match.group(4).lower()}m"
        slots.add((match.group(1), _minutes(clock)))
    for match in re.finditer(
            r"(?<!\d)(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?!\d)", text):
        try:
            day = datetime.strptime(match.group(1), "%Y-%m-%d").strftime("%m/%d/%Y")
        except ValueError:
            continue
        slots.add((day, int(match.group(2)) * 60 + int(match.group(3))))
    return slots


def _minutes(raw):
    match = TIME.fullmatch(raw.strip())
    if not match:
        raise ValueError(f"unsupported clock value {raw!r}")
    hour = int(match.group(1)) % 12
    if match.group(3).lower() == "p":
        hour += 12
    return hour * 60 + int(match.group(2) or 0)


def _expected_window(target, run_date, scenario):
    monday = run_date - timedelta(days=run_date.weekday())
    normalized = target.lower()
    if normalized == "next week":
        start = monday + timedelta(days=7)
        return start, start + timedelta(days=4)
    if normalized == "tuesday next week":
        target_date = monday + timedelta(days=8)
        return target_date, target_date
    if normalized == "soonest":
        requested = next(
            (day for day in ("monday", "tuesday", "wednesday", "thursday", "friday")
             if any(day in turn.lower() for turn in scenario["turns"])),
            None,
        )
        if requested is None:
            raise ValueError("soonest weekday was not present in scenario input")
        weekday = ("monday", "tuesday", "wednesday", "thursday", "friday").index(requested)
        target_date = run_date + timedelta(days=(weekday - run_date.weekday()) % 7)
        return target_date, target_date
    if re.fullmatch(r"\d{2}/\d{2}", target):
        month, day = map(int, target.split("/"))
        target_date = date(run_date.year, month, day)
        return target_date, target_date
    raise ValueError(f"unsupported date target {target!r}")


def _active_offer_text(final_variables, final_response):
    values = [final_response]
    values.extend(
        str(value) for key, value in final_variables.items()
        if re.fullmatch(r"slot_\d+_start", str(key), re.I) and value not in (None, "")
    )
    return "\n".join(values)


def scoped_failures(scenario, turn_responses, turn_variables, run_date):
    failures = []
    for check in scenario.get("response_checks", []):
        blob = _response_blob(turn_responses, check)
        label = "response to turn " + ",".join(
            str(turn) for turn in (check.get("turns") or [check["turn"]]))
        if check.get("expect_text") and not re.search(check["expect_text"], blob, re.I | re.S):
            failures.append(f"{label} did not match /{check['expect_text']}/")
        if check.get("reject_text"):
            hit = re.search(check["reject_text"], _affirmative(blob), re.I | re.S)
            if hit:
                failures.append(f"{label} matched forbidden /{check['reject_text']}/")

        dates = _dates(blob)
        if check.get("require_dated_slot") and not dates:
            failures.append(f"{label} contained no dated slot")
        if check.get("exact_dates"):
            allowed = {datetime.strptime(raw, "%m/%d/%Y").date()
                       for raw in check["exact_dates"]}
            if any(offered not in allowed for offered in dates):
                failures.append(f"{label} offered a date outside {check['exact_dates']!r}")
        if check.get("date_target"):
            try:
                start, end = _expected_window(check["date_target"], run_date, scenario)
            except ValueError as exc:
                failures.append(str(exc))
            else:
                for offered in dates:
                    if not start <= offered <= end:
                        failures.append(
                            f"{label} offered {offered:%m/%d/%Y} outside "
                            f"{start:%m/%d/%Y}-{end:%m/%d/%Y}"
                        )
        if check.get("required_weekdays"):
            present = {offered.strftime("%A").lower() for offered in dates}
            for weekday in check["required_weekdays"]:
                if weekday not in present:
                    failures.append(f"{label} contained no {weekday.title()} date")
        if check.get("allowed_weekdays"):
            allowed = set(check["allowed_weekdays"])
            for offered in dates:
                if offered.strftime("%A").lower() not in allowed:
                    failures.append(f"{label} offered non-weekday date {offered:%m/%d/%Y}")
        if check.get("slot_floor"):
            floor = _minutes(check["slot_floor"])
            times = [(_minutes(match.group(0)), match.group(0)) for match in TIME.finditer(blob)]
            if not times:
                failures.append(f"{label} contained no offered clock")
            for value, raw in times:
                if value < floor:
                    failures.append(f"{label} offered {raw!r} before {check['slot_floor']}")
        if check.get("preserve_offer_from_turn"):
            source_turn = check["preserve_offer_from_turn"]
            prior = "\n".join(turn_responses[source_turn - 1])
            prior_dates = _normalized_date_strings(prior)
            prior_slots = _normalized_slots(prior)
            active = _active_offer_text(turn_variables[-1], blob)
            if not prior_dates:
                failures.append(f"response to turn {source_turn} established no dated offer")
            elif not prior_dates.issubset(_normalized_date_strings(active)):
                failures.append("the previously offered dates were not retained in active offer state")
            if prior_slots and not prior_slots.issubset(_normalized_slots(active)):
                failures.append("the previously offered slots were not retained in active offer state")
    return failures


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
    suite_run_date = date.today()
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
        date_target = harness_scenario.pop("expect_week", None)
        slot_floor = harness_scenario.pop("expect_slot_floor", None)
        harness_scenario.pop("response_checks", None)

        # pathway_harness exposes the flat transcript only. Record each chat POST's
        # response list and variables while retaining its network behavior unchanged.
        turn_responses = []
        turn_variables = []
        original_post = harness.post

        def recording_post(path, payload, attempts=4):
            status, body = original_post(path, payload, attempts)
            if "/v1/pathway/chat/" in path and path != "/v1/pathway/chat/create" and status == 200:
                data = (body or {}).get("data") or {}
                turn_responses.append(list(data.get("assistant_responses") or []))
                turn_variables.append(dict(data.get("variables") or {}))
            return status, body

        harness.post = recording_post
        try:
            ok, failures, said = harness.run_scenario(
                version, harness_scenario, run_date=suite_run_date)
        finally:
            harness.post = original_post

        blob = "\n".join(said)
        promise_hit = PROMISE_COPY.search(blob)
        if promise_hit:
            failures.append(f"used forbidden promise copy: {promise_hit.group(0)!r}")
        leak_hit = GOAL_FIELD_LEAK.search(blob)
        if leak_hit:
            failures.append(f"leaked an internal goal field: {leak_hit.group(0)!r}")
        if scenario.get("expect_dated_slots") and not DATED_SLOT.search(blob):
            failures.append("offer contained no dated slots")
        if date_target:
            try:
                start, end = _expected_window(date_target, suite_run_date, scenario)
            except ValueError as exc:
                failures.append(str(exc))
            else:
                dates = _dates(blob)
                for offered in dates:
                    if not start <= offered <= end:
                        failures.append(
                            f"offered date {offered:%m/%d/%Y} falls outside "
                            f"{start:%m/%d/%Y}-{end:%m/%d/%Y} for {date_target!r}"
                        )
                no_slot_required = {
                    "requests a time outside office hours",
                    "dead end search then assumes a booked time",
                }
                if not dates and scenario["name"] not in no_slot_required:
                    failures.append(f"no dated slot found for {date_target!r}")
        if slot_floor:
            floor = _minutes(slot_floor)
            offered_times = [(_minutes(match.group(0)), match.group(0)) for match in TIME.finditer(blob)]
            if not offered_times:
                failures.append(f"no offered clock found for floor {slot_floor!r}")
            for value, raw in offered_times:
                if value < floor:
                    failures.append(f"offered time {raw!r} precedes floor {slot_floor!r}")

        if len(turn_responses) == len(scenario["turns"]):
            failures.extend(scoped_failures(
                scenario, turn_responses, turn_variables, suite_run_date))
        elif scenario.get("response_checks"):
            failures.append(
                f"captured {len(turn_responses)} response groups for {len(scenario['turns'])} turns"
            )

        if RETIRED_CARRIER_NUMBER and RETIRED_CARRIER_NUMBER in blob:
            failures.append("used the retired carrier number")
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
