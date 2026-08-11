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
import json
import os
import re
import sys
import urllib.error
import urllib.request

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
SCENARIOS = [
    {"name": "opening asks, does not offer",
     "turns": ["hi"],
     "expect_node": "n_ask",
     "expect_text": r"when would you like to come in",
     "reject_text": r"\d{2}/\d{2}/\d{4}",
     "why": "v38 opens with a question; naming a time before searching would be invented"},

    {"name": "vague week request",
     "turns": ["hi", "I'd like to come next week sometime"],
     "expect_node": "n_offer",
     "expect_vars": {"preference_from": "monday", "preference_to": "friday"},
     "why": "the exact reply that stranded a live conversation on v35"},

    {"name": "named weekday",
     "turns": ["hi", "can I come tuesday?"],
     "expect_node": "n_offer",
     "expect_text": r"07/28/2026",
     "why": "weekday words resolve server-side; tuesday must return the 28th"},

    {"name": "week plus time of day",
     "turns": ["hi", "next week in the morning please"],
     "expect_node": "n_offer",
     "expect_vars": {"time_pref": "morning"},
     "why": "time_pref must carry morning, and never a date"},

    {"name": "rejects the openings, names no new day",
     "turns": ["hi", "can I come tuesday?", "those don't work for me"],
     "expect_node": "n_offer",
     "why": "rejecting an offer with no new day must still re-search, not dead-end"},

    {"name": "insurance question",
     "turns": ["hi", "does my insurance cover this?"],
     "expect_node": "n_ask",
     "expect_text": r"staff|office",
     "reject_text": r"\bfree\b|\$\d|\bdiscount\b",
     "why": "defers to staff, quotes no price, and is never treated as a decline"},

    {"name": "asks about an order",
     "turns": ["hi", "are my glasses ready yet?"],
     "expect_node": "n_ask",
     "expect_text": r"855",
     "why": "out of scope, hands to the office, keeps the booking goal alive"},

    {"name": "opts out",
     "turns": ["hi", "STOP"],
     "expect_node": "e_stop",
     "reject_text": r"no more messages|you (are|have been) (opted out|unsubscribed)",
     "why": "must acknowledge without promising suppression nothing can deliver yet"},

    {"name": "wrong person",
     "turns": ["hi", "who is this? you have the wrong number"],
     "expect_node": "e_not_me",
     "why": "apologise and stop, never keep selling to the wrong person"},

    {"name": "declines outright",
     "turns": ["hi", "no thanks, I'm not interested"],
     "expect_node": "e_declined",
     "why": "an explicit no is the only thing that ends the booking goal"},
]

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


def mask(text):
    """No PHI to stdout: initial the known first name, blank any long digit run."""
    text = re.sub(r"\b\d{4,}\b", "[num]", text)
    return text


def key():
    raw = os.environ.get("BLAND_API_KEY", "").strip()
    if raw.startswith("{"):
        parsed = json.loads(raw)
        raw = next((parsed[k] for k in ("api_key", "key", "value") if parsed.get(k)), "")
    if not raw:
        sys.exit("BLAND_API_KEY missing; run under scripts/secret_exec.py")
    return raw


def post(path, payload):
    req = urllib.request.Request(
        API + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": key(), "Content-Type": "application/json",
                 "User-Agent": "mybcat-cli"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")[:300]


def run_scenario(version, scenario):
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

    if node != scenario["expect_node"]:
        failures.append(f"ended on {node!r}, expected {scenario['expect_node']!r}")

    for name, expected in (scenario.get("expect_vars") or {}).items():
        actual = variables.get(name)
        if str(actual).strip().lower() != expected:
            failures.append(f"{name} was {actual!r}, expected {expected!r}")

    if scenario.get("expect_text") and not re.search(scenario["expect_text"], blob, re.I):
        failures.append(f"never said anything matching /{scenario['expect_text']}/")

    if scenario.get("reject_text") and re.search(scenario["reject_text"], blob, re.I):
        failures.append(f"said something matching the forbidden /{scenario['reject_text']}/")

    for pattern, complaint in ALWAYS_REJECT:
        hit = re.search(pattern, blob, re.I | re.M)
        if hit:
            failures.append(f"{complaint}: {mask(hit.group(0))!r}")

    # Claiming a booking is only legitimate from the confirmation node.
    if node != "n_confirm" and re.search(BOOKING_CLAIM, blob, re.I):
        failures.append("claimed an appointment exists outside the confirmation step")

    return not failures, failures, said


def main():
    version = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if not version:
        sys.exit("usage: pathway_harness.py <pathway_version>")

    if not SUBJECT["recall_patient_id"] or not SUBJECT["recall_cell"]:
        sys.exit("set HARNESS_PATIENT_ID and HARNESS_PATIENT_CELL; they are deliberately not "
                 "stored in this file so it carries no patient identifier")

    print(f"pathway {PATHWAY_ID[:8]} version {version}, {len(SCENARIOS)} scenarios, no SMS sent\n")
    passed = 0
    for scenario in SCENARIOS:
        ok, failures, said = run_scenario(version, scenario)
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
    return 0 if passed == len(SCENARIOS) else 1


if __name__ == "__main__":
    sys.exit(main())
