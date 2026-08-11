#!/usr/bin/env python3
"""Drive adversarial fuzz scenarios against a pinned pathway version.

usage: fuzz_runner.py <pathway_version> <fuzz-scenarios.json> [start_index] [end_index]

Env: BLAND_API_KEY (JSON envelope tolerated), HARNESS_PATIENT_ID/CELL/STORE.
For each scenario: create a chat, play the turns, capture every envelope, and
apply invariant checks plus the scenario's expectation. Prints one RESULT line
per scenario and a final SUMMARY line; exits 0 only if every scenario passes.

Invariants on every turn:
- no booking claim unless the variables show a completed booking;
- no off-grid clock time outside a refusal sentence;
- spoken dates must be a subset of the live slot-variable dates when both exist;
- no negative-availability claim on a turn whose search state did not change.
"""

import json
import os
import re
import sys
import urllib.request

API = "https://api.bland.ai"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"

CLAIM = re.compile(
    r"(?i)\b(?:booked|got you down|you'?re all set|we'?ll see you then|see you then|"
    r"reserved|i'?ve scheduled|scheduled you|confirmed for)\b")
NEGATIVE = re.compile(
    r"(?i)\b(?:don'?t have any(?:thing)?|no openings?|nothing (?:available|open)|"
    r"not available|no availability|fully booked|unavailable|no match|"
    r"couldn'?t find)\b")
REFUSAL = re.compile(
    r"(?i)\b(?:not available|isn'?t available|no openings?|don'?t have|do not have|unavailable)\b")
CLOCK = re.compile(r"\b(\d{1,2}):(\d{2})\s*(?:am|pm)\b", re.I)
DATE = re.compile(r"\d{2}/\d{2}/\d{4}")
END_NODES = {"e_stop", "e_not_me", "e_declined"}


def unwrap(raw):
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), raw)
        except Exception:
            pass
    return raw


def post(key, path, payload):
    req = urllib.request.Request(
        API + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": key, "Content-Type": "application/json",
                 "User-Agent": "mybcat-fuzz"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def slot_dates(variables):
    return {
        str(variables[k]).split()[0]
        for k in ("slot_1_start", "slot_2_start") if variables.get(k)
    }


def search_state(variables):
    return json.dumps(
        {k: variables.get(k) for k in
         ("slot_1_start", "slot_2_start", "slot_count", "out_of_hours",
          "from_unresolved", "anchor_exact", "BlandStatusCode")},
        sort_keys=True)


def check_turn(said, variables, prev_state):
    problems = []
    booked = bool(variables.get("new_appt_id")) or str(
        variables.get("book_success", "")).lower() in ("true", "1")
    claim = CLAIM.search(said)
    if claim and not booked:
        problems.append(f"booking claim without booking: {claim.group(0)!r}")
    for sentence in re.split(r"(?<=[.!?])\s+|\n", said):
        refusing = REFUSAL.search(sentence)
        for hour, minute in CLOCK.findall(sentence):
            if int(minute) % 15 != 0 and not refusing:
                problems.append(f"off-grid time {hour}:{minute}")
    spoken = set(DATE.findall(said))
    slots = slot_dates(variables)
    if spoken and slots and not spoken.issubset(slots):
        problems.append(f"spoke {sorted(spoken)} while slots hold {sorted(slots)}")
    if NEGATIVE.search(said) and search_state(variables) == prev_state:
        problems.append("negative-availability claim with unchanged search state")
    return problems


def check_expect(expect, said, node):
    low = said.lower()
    kind = expect.get("kind")
    problems = []
    times = {t.lower() for t in re.findall(r"\d{1,2}:\d{2}\s*(?:am|pm)", said, re.I)}
    if kind == "offer" and not DATE.search(said):
        problems.append("expected a dated offer")
    if kind == "single_offer" and len(times) != 1:
        problems.append(f"expected exactly one time, saw {sorted(times)}")
    if kind == "confirm_gate" and not re.search(r"(?i)reply yes|to confirm", said):
        problems.append("expected a booking confirmation prompt")
    if kind == "clarify" and ("?" not in said or DATE.search(said)):
        problems.append("expected a question without a dated offer")
    if kind == "clarify_or_offer" and "?" not in said and not DATE.search(said):
        problems.append("expected a safe clarifying question or a dated offer")
    if kind == "honest_miss" and not NEGATIVE.search(said) and "?" not in said:
        problems.append("expected an honest miss or a question")
    if kind == "refusal" and not REFUSAL.search(said):
        problems.append("expected a refusal")
    if kind == "office_referral" and "219-2219" not in said:
        problems.append("expected the office number")
    if kind == "end_stop" and node not in END_NODES:
        problems.append(f"expected a terminal node, ended on {node}")
    for needle in expect.get("must_contain", []):
        if needle.lower() not in low:
            problems.append(f"missing required text {needle!r}")
    for needle in expect.get("must_not_contain", []):
        if needle.lower() in low:
            problems.append(f"contains forbidden text {needle!r}")
    return problems


def main():
    if len(sys.argv) < 3:
        print("usage: fuzz_runner.py <version> <fuzz-scenarios.json> [start] [end]")
        return 1
    version = int(sys.argv[1])
    scenarios = json.load(open(sys.argv[2], encoding="utf-8"))
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    end = int(sys.argv[4]) if len(sys.argv) > 4 else len(scenarios)
    key = unwrap(os.environ["BLAND_API_KEY"])
    request_data = {
        "recall_patient_id": os.environ["HARNESS_PATIENT_ID"],
        "recall_cell": os.environ.get("HARNESS_PATIENT_CELL"),
        "store": os.environ.get("HARNESS_STORE", "711"),
        "campaign": "harness",
    }

    passed = failed = 0
    for scenario in scenarios[start:end]:
        name = scenario.get("name", "?")
        for turn in scenario.get("turns", []):
            if str(turn).strip().lower() in ("1", "2", "yes"):
                print(f"RESULT name={name} status=SKIP reason=booking-unsafe-turn")
                break
        else:
            try:
                created = post(key, "/v1/pathway/chat/create", {
                    "pathway_id": PATHWAY_ID, "pathway_version": version,
                    "request_data": request_data})
                chat_id = created["data"]["chat_id"]
                prev = search_state({})
                problems, said, node = [], "", ""
                for turn in scenario["turns"]:
                    reply = post(key, f"/v1/pathway/chat/{chat_id}", {"message": turn})
                    data = reply.get("data") or {}
                    variables = data.get("variables") or {}
                    said = " ".join(str(x) for x in (data.get("assistant_responses") or []))
                    node = data.get("current_node_id") or ""
                    problems += check_turn(said, variables, prev)
                    prev = search_state(variables)
                problems += check_expect(scenario.get("expect", {}), said, node)
                if problems:
                    failed += 1
                    print(f"RESULT name={name} status=FAIL problems={' ; '.join(problems)[:220]} said={said[:110]!r}")
                else:
                    passed += 1
                    print(f"RESULT name={name} status=PASS said={said[:90]!r}")
            except Exception as exc:
                failed += 1
                print(f"RESULT name={name} status=ERROR reason={exc}")

    print(f"SUMMARY passed={passed} failed={failed} total={passed + failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
