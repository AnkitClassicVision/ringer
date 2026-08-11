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
import time
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

    expected = scenario["expect_node"]
    allowed = expected if isinstance(expected, (list, tuple)) else [expected]
    if node not in allowed:
        failures.append(f"ended on {node!r}, expected one of {list(allowed)!r}")

    for name, expected in (scenario.get("expect_vars") or {}).items():
        actual = variables.get(name)
        if str(actual).strip().lower() != expected:
            failures.append(f"{name} was {actual!r}, expected {expected!r}")

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
