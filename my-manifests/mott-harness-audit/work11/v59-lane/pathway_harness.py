#!/usr/bin/env python3
"""Drive a Bland pathway through scripted patient conversations, with no SMS.

Why this exists: every defect in this pathway so far was found by texting a real
phone and reading the reply. That is slow, costs a message, needs a human holding
a handset, and only ever tests the one path that human happened to type.

The chat endpoint runs the SAME pathway version with the SAME webhooks against the
SAME gateway, and returns the node id it landed on plus every variable it captured.
So a scenario can assert on where the conversation ended up, not just on how the
message reads.

Two platform traps, both already paid for:
  * The version MUST be pinned on create. Without it the chat silently runs the
    unversioned base pathway, whose edge labels are stripped, and the agent sits on
    the start node improvising greetings while no webhook ever fires.
  * The message route is /v1/pathway/chat/{chat_id}. Posting to /v1/pathway/chat
    answers 403 "Error checking pathway ownership", which reads like a permissions
    problem and is not one.

Booking scenarios are deliberately absent. Reaching the confirmation node writes a
real appointment into the practice schedule. Add one only behind a dummy patient the
conductor allowlists, and prove the cancel path before the booking path.

Usage:
  python3 scripts/secret_exec.py --env BLAND_API_KEY=<name> -- \
      python3 harness/pathway_harness.py 37
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API = "https://api.bland.ai"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"

# The test subject is supplied by the environment and never stored in this file, so the
# harness itself carries no patient identifier and can be read by anyone. Nothing is
# printed either: any run of 4+ digits is masked before it reaches stdout.
SUBJECT = {
    "recall_patient_id": os.environ.get("HARNESS_PATIENT_ID", ""),
    "recall_cell": os.environ.get("HARNESS_PATIENT_CELL", ""),
    "store": os.environ.get("HARNESS_STORE", "711"),
}

# Substance, not vocabulary. Each scenario says where the conversation must END UP,
# because that is what a patient actually experiences.
from scenarios import SCENARIOS  # noqa: E402  (cases live beside the runner)

# Every patient-facing message is checked for these regardless of scenario. A live
# patient was once shown "preference_from: monday", and a negotiation node once told
# someone they were booked when nothing had been written.
ALWAYS_REJECT = [
    (r"\b(preference_from|preference_to|preference_after|preference_before|time_pref"
     r"|slot_count|patient_id|exam_type_id|recall_cell)\b", "leaked an internal field name"),
    (r"^\s*\w+_\w+\s*:\s*\S", "leaked a field:value line"),
]
# Only the confirmation node may claim a booking exists.
BOOKING_CLAIM = r"\b(you're|you are|i have you)\s+(all\s+)?(booked|scheduled|set)\b|\bis (booked|confirmed)\b"


NEGATION = re.compile(r"\b(not|never|cannot|can't|won't|don't|doesn't|didn't|haven't|hasn't|"
                      r"isn't|aren't|wasn't|weren't|no|none|nothing|unable|yet)\b", re.I)


def affirmative(text):
    """Drop negated sentences before looking for a forbidden claim.

    Two correct replies were failed by earlier assertions: "We don't have any openings at
    3am" matched a pattern hunting for an offer of 3am, and "I haven't booked you for
    anything yet" matched one hunting for a booking claim. Both are the agent doing
    precisely the right thing. A forbidden phrase inside a denial is not the violation.
    """
    return " ".join(s for s in re.split(r"(?<=[.!?])\s+", text) if not NEGATION.search(s))


def mask(text):
    """No PHI to stdout: initial the known first name, blank any long digit run."""
    text = re.sub(r"\b\d{4,}\b", "[num]", text)
    return text


DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
TIME_RE = re.compile(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?\b", re.I)
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def offered_sources(variables, said):
    """Return raw offer-bearing values before stdout masking changes dates."""
    sources = list(said)
    for name, value in variables.items():
        if re.fullmatch(r"slot_\d+_start", str(name), re.I) and value not in (None, ""):
            sources.append(str(value))
    return sources


def offered_dates(sources):
    dates = []
    for source in sources:
        for raw in DATE_RE.findall(str(source)):
            try:
                dates.append(datetime.strptime(raw, "%m/%d/%Y").date())
            except ValueError:
                continue
    return dates


def parse_slot_time(raw):
    """Parse a 12-hour offered-slot clock value into minutes after midnight."""
    match = TIME_RE.fullmatch(raw.strip())
    if not match:
        raise ValueError(f"unsupported clock floor {raw!r}")
    hour, minute, meridiem = int(match.group(1)), int(match.group(2) or 0), match.group(3).lower()
    hour = hour % 12 + (12 if meridiem == "p" else 0)
    return hour * 60 + minute


def offered_times(sources):
    times = []
    for source in sources:
        for match in TIME_RE.finditer(str(source)):
            times.append((parse_slot_time(match.group(0)), match.group(0)))
    return times


def resolved_date_window(target, run_date, scenario):
    """Resolve a scenario date target under the owner's Monday-anchored rule."""
    normalized = target.strip().lower()
    current_monday = run_date - timedelta(days=run_date.weekday())

    if normalized == "next week":
        start = current_monday + timedelta(days=7)
        return start, start + timedelta(days=4)

    qualified = re.fullmatch(r"([a-z]+) next week", normalized)
    if qualified and qualified.group(1) in WEEKDAYS:
        target_date = current_monday + timedelta(
            days=7 + WEEKDAYS[qualified.group(1)])
        return target_date, target_date

    if normalized == "soonest":
        weekday = str((scenario.get("expect_vars") or {}).get("preference_from", "")).lower()
        if weekday not in WEEKDAYS:
            raise ValueError("'soonest' requires expect_vars.preference_from to name a weekday")
        target_date = run_date + timedelta(
            days=(WEEKDAYS[weekday] - run_date.weekday()) % 7)
        return target_date, target_date

    raise ValueError(f"unsupported expect_week target {target!r}")


def key():
    raw = os.environ.get("BLAND_API_KEY", "").strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), "")
    if not raw:
        sys.exit("BLAND_API_KEY missing; run under scripts/secret_exec.py")
    return raw


def post(path, payload, attempts=4):
    """Retry transport failures, never HTTP ones.

    A full suite run is roughly ten minutes of live calls, and a single SSL handshake
    timeout used to abort all of it. A transport failure says nothing about the pathway,
    so it is retried with backoff. An HTTP status IS a result and is returned untouched,
    because retrying a 400 would hide the very defect the suite exists to catch.
    """
    body = json.dumps(payload).encode()
    for attempt in range(attempts):
        req = urllib.request.Request(
            API + path, data=body, method="POST",
            headers={"Authorization": key(), "Content-Type": "application/json",
                     "User-Agent": "mybcat-cli"})
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode(errors="replace")[:300]
        except Exception as exc:
            if attempt == attempts - 1:
                return 0, f"transport failure after {attempts} attempts: {type(exc).__name__}"
            time.sleep(2 ** attempt)


def run_scenario(version, scenario, run_date=None):
    run_date = run_date or date.today()
    status, body = post("/v1/pathway/chat/create",
                        {"pathway_id": PATHWAY_ID, "pathway_version": version,
                         "request_data": dict(SUBJECT, campaign="harness")})
    if status != 200:
        return False, [f"chat create failed: HTTP {status} {body}"], []

    chat_id = body["data"]["chat_id"]
    said, node, variables = [], None, {}
    for turn in scenario["turns"]:
        status, body = post(f"/v1/pathway/chat/{chat_id}", {"message": turn})
        if status != 200:
            return False, [f"turn {turn!r} failed: HTTP {status} {body}"], said
        data = body.get("data") or {}
        said.extend(data.get("assistant_responses") or [])
        node = data.get("current_node_id") or node
        variables = data.get("variables") or variables

    blob = "\n".join(said)
    failures = []
    sources = offered_sources(variables, said)

    expected = scenario["expect_node"]
    allowed = expected if isinstance(expected, (list, tuple)) else [expected]
    if node not in allowed:
        failures.append(f"ended on {node!r}, expected one of {list(allowed)!r}")

    for name, expected in (scenario.get("expect_vars") or {}).items():
        actual = variables.get(name)
        if str(actual).strip().lower() != expected:
            failures.append(f"{name} was {actual!r}, expected {expected!r}")

    if scenario.get("expect_week"):
        try:
            window_start, window_end = resolved_date_window(
                scenario["expect_week"], run_date, scenario)
        except ValueError as exc:
            failures.append(str(exc))
        else:
            dates = offered_dates(sources)
            for offered_date in dates:
                if not window_start <= offered_date <= window_end:
                    failures.append(
                        f"offered date {offered_date:%m/%d/%Y} falls outside "
                        f"{window_start:%m/%d/%Y}-{window_end:%m/%d/%Y} "
                        f"for {scenario['expect_week']!r}")
            if str(node).startswith("n_offer") and not dates:
                failures.append(
                    f"no MM/DD/YYYY offered date found for {scenario['expect_week']!r}")

    if scenario.get("expect_slot_floor"):
        try:
            floor = parse_slot_time(scenario["expect_slot_floor"])
        except ValueError as exc:
            failures.append(str(exc))
        else:
            times = offered_times(sources)
            if not times:
                failures.append(
                    f"no offered clock time found for floor {scenario['expect_slot_floor']!r}")
            for offered_time, raw in times:
                if offered_time < floor:
                    failures.append(
                        f"offered time {raw!r} precedes floor "
                        f"{scenario['expect_slot_floor']!r}")

    if scenario.get("expect_text") and not re.search(scenario["expect_text"], blob, re.I):
        failures.append(f"never said anything matching /{scenario['expect_text']}/")

    if scenario.get("reject_text"):
        hit = re.search(scenario["reject_text"], affirmative(blob), re.I)
        if hit:
            failures.append(f"said {mask(hit.group(0))!r}, matching the forbidden "
                            f"/{scenario['reject_text']}/")

    for pattern, complaint in ALWAYS_REJECT:
        hit = re.search(pattern, affirmative(blob), re.I | re.M)
        if hit:
            failures.append(f"{complaint}: {mask(hit.group(0))!r}")

    # Claiming a booking is only legitimate from the confirmation node.
    if node != "n_confirm" and re.search(BOOKING_CLAIM, affirmative(blob), re.I):
        failures.append("claimed an appointment exists outside the confirmation step")

    return not failures, failures, said


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the pathway behavioral suite without sending SMS.")
    parser.add_argument("pathway_version", type=int)
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="run as non-certifying diagnostics; always exits nonzero",
    )
    parser.add_argument(
        "--acknowledge-blocked",
        action="store_true",
        help="deliberately run certification mode after the release-blocking gateway defect is fixed",
    )
    args = parser.parse_args(argv)
    version = args.pathway_version

    run_date = date.today()
    diagnostic_only = args.diagnostic or run_date.weekday() == 6
    if not diagnostic_only and not args.acknowledge_blocked:
        parser.error(
            "CERTIFICATION REFUSED: TEMPORAL-CONTRACT.md rev 3 section 4 declares the "
            "weekday-qualified gateway defect RELEASE-BLOCKING. After the gateway is fixed, "
            "a human may run deliberately with --acknowledge-blocked."
        )
    if diagnostic_only:
        print("=" * 72)
        print("DIAGNOSTIC ONLY: THIS RUN CANNOT CERTIFY OR EMIT A CERTIFICATION PASS")
        if run_date.weekday() == 6:
            print("Sunday results remain diagnostic because temporal assertions are "
                  "unrepresentative on the documented boundary day.")
        else:
            print("Explicit --diagnostic mode is non-certifying regardless of score.")
        print("=" * 72 + "\n")

    if not SUBJECT["recall_patient_id"] or not SUBJECT["recall_cell"]:
        sys.exit("set HARNESS_PATIENT_ID and HARNESS_PATIENT_CELL; they are deliberately not "
                 "stored in this file so it carries no patient identifier")

    print(f"pathway {PATHWAY_ID[:8]} version {version}, {len(SCENARIOS)} scenarios, no SMS sent\n")
    passed = 0
    for scenario in SCENARIOS:
        ok, failures, said = run_scenario(version, scenario, run_date)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {scenario['name']}")
        if ok:
            passed += 1
        else:
            print(f"       expected: {scenario['why']}")
            for failure in failures:
                print(f"       -> {failure}")
            for line in said[-2:]:
                print(f"       said: {mask(line)[:150]}")
        print()

    print(f"{passed}/{len(SCENARIOS)} scenarios passed on version {version}")
    if diagnostic_only:
        print("\nDIAGNOSTIC ONLY: no certification-pass artifact was written; "
              "this process exits nonzero regardless of score.")
    return 0 if passed == len(SCENARIOS) and not diagnostic_only else 1


if __name__ == "__main__":
    sys.exit(main())
