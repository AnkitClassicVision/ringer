#!/usr/bin/env python3
"""Live v91 pathway driver. Run only with the allowlisted harness patient."""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

HARNESS_DIR = "/home/ankit114/repos/mott-v21-snap/harness"
GW = "https://mott-booking-gw.mail.mybcat.com"
OFFER_RE = re.compile(
    r"\b(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s*([ap]m)\b", re.I)
DENIAL_RE = re.compile(r"latest the office has|nothing later|different day\?", re.I)


def mask(value):
    """Mask every digit but the last four in runs of five or more."""
    return re.sub(r"\d(?=\d{4})", "*", str(value))


def gw_call(path, payload, timeout=180):
    auth = os.environ.get("GW_TOKEN", "").strip()
    if not auth:
        sys.exit("GW_TOKEN not set")
    req = urllib.request.Request(
        GW + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "mybcat-cli",
                 "Authorization": auth if auth.lower().startswith("bearer")
                 else "Bearer " + auth})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")[:300]
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def gw_count(patient_id, store):
    status, body = gw_call("/appt-list", {"patient_id": patient_id, "store": store})
    if status != 200 or not isinstance(body, dict):
        return None, []
    result = body.get("result") or {}
    return result.get("count"), result.get("appointments") or []


def gw_cleanup(patient_id, store):
    for _ in range(3):
        count, appointments = gw_count(patient_id, store)
        if count == 0:
            return 0
        if count is None:
            time.sleep(5)
            continue
        for appointment in appointments:
            appt_id = appointment.get("appointment_id")
            day = (appointment.get("start") or "")[:10]
            status, _ = gw_call("/sign", {
                "verb": "appt.cancel", "target": appt_id, "store": store,
                "reason": "patient-request",
                "params": {"appt_id": appt_id, "day": day}})
            print(f"CLEANUP cancel ...{str(appt_id)[-4:]} -> HTTP {status}")
    count, _ = gw_count(patient_id, store)
    return count


def find_appt_id(body):
    if not isinstance(body, dict):
        return None
    for key in ("appointment_id", "appt_id", "id"):
        if body.get(key):
            return body[key]
    for key in ("result", "data", "appointment"):
        found = find_appt_id(body.get(key))
        if found:
            return found
    return None


def gw_direct_book(patient_id, store):
    status, body = gw_call(
        "/availability", {"store": store, "first_available": "1", "slot_minutes": "15"})
    slots = ((body.get("result") or {}).get("slots") or []) if isinstance(body, dict) else []
    if status != 200 or not slots:
        return None, f"availability HTTP {status}, slots={len(slots)}"
    slot = slots[0]
    # Deliberately one call only. A booking write must never be retried.
    status, body = gw_call("/sign", {
        "verb": "appt.book", "target": patient_id, "store": store,
        "reason": "new-booking",
        "params": {"doctor": slot.get("doctor_id"), "start": slot.get("start"),
                   "end": slot.get("end"),
                   "type": os.environ.get("HARNESS_EXAM_TYPE", "674597395")}})
    if status != 200 or not isinstance(body, dict) or body.get("success") is not True:
        return None, f"book HTTP {status}: {mask(body)}"
    appt_id = find_appt_id(body)
    if not appt_id:
        count, appointments = gw_count(patient_id, store)
        if count == 1 and appointments:
            appt_id = appointments[0].get("appointment_id")
    return appt_id, None if appt_id else "book succeeded but appointment id was absent"


def fail(reasons):
    print("VERDICT: FAIL " + " | ".join(str(reason) for reason in reasons))
    raise SystemExit(1)


def create_chat(H, version):
    status, body = H.post(
        "/v1/pathway/chat/create",
        {"pathway_id": H.PATHWAY_ID, "pathway_version": version,
         "request_data": dict(H.SUBJECT, campaign="harness")})
    if status != 200 or not isinstance(body, dict):
        fail([f"chat create failed: HTTP {status} {mask(body)}"])
    try:
        return body["data"]["chat_id"]
    except (KeyError, TypeError):
        fail([f"chat create returned no chat_id: {mask(body)}"])


def send_turn(H, chat_id, turn):
    status, body = H.post(f"/v1/pathway/chat/{chat_id}", {"message": turn})
    if status != 200 or not isinstance(body, dict):
        fail([f"turn {turn!r} failed: HTTP {status} {mask(body)}"])
    data = body.get("data") or {}
    replies = data.get("assistant_responses") or []
    node = data.get("current_node_id")
    print(f"TURN {turn!r} -> node={node}")
    for reply in replies:
        print(f"  SAID {mask(reply)}")
    return node, data.get("variables") or {}, replies


def offered(text):
    values = []
    for date_part, clock, meridiem in OFFER_RE.findall(text):
        dt = datetime.strptime(f"{date_part} {clock} {meridiem}", "%m/%d/%Y %I:%M %p")
        values.append((dt, dt.strftime("%m/%d/%Y %I:%M %p").lower()))
    return values


def parse_inventory_start(value):
    raw = str(value).strip()
    for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %I:%M%p",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=None)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def run_gate_booked(H, version, patient_id, store):
    appt_id, error = gw_direct_book(patient_id, store)
    if error:
        fail([f"seed failed: {error}"])
    print(f"SEED_OK appt_id=...{str(appt_id)[-4:]}")
    reasons = []
    node = None
    try:
        chat_id = create_chat(H, version)
        node, _, _ = send_turn(H, chat_id, "hi")
        print(f"END_NODE={node}")
        if node != "e_defer":
            reasons.append(f"ended on {node!r}, expected 'e_defer'")
    finally:
        final = gw_cleanup(patient_id, store)
        print(f"CLEANUP_FINAL_COUNT={final}")
        if final != 0:
            reasons.append(f"cleanup left {final} appointment(s)")
    if reasons:
        fail(reasons)
    print("VERDICT: PASS mode=gate_booked")


def run_gate_clean(H, version):
    chat_id = create_chat(H, version)
    node, variables, _ = send_turn(H, chat_id, "hi")
    appt_count = variables.get("appt_count")
    print(f"END_NODE={node}")
    print(f"APPT_COUNT_VAR={appt_count}")
    reasons = []
    if node != "n_ask":
        reasons.append(f"ended on {node!r}, expected 'n_ask'")
    try:
        clean_count = int(appt_count) == 0
    except (TypeError, ValueError):
        clean_count = False
    if not clean_count:
        reasons.append(f"appt_count was {appt_count!r}, expected 0")
    if reasons:
        fail(reasons)
    print("VERDICT: PASS mode=gate_clean")


def run_incident(H, version, store):
    chat_id = create_chat(H, version)
    send_turn(H, chat_id, "hi")
    _, _, first_replies = send_turn(H, chat_id, "Friday afternoon")
    first = offered("\n".join(map(str, first_replies)))
    print("OFFER_FIRST=" + " | ".join(raw for _, raw in first))
    _, _, later_replies = send_turn(H, chat_id, "Any later time?")
    later_text = "\n".join(map(str, later_replies))
    later = offered(later_text)
    print("OFFER_LATER=" + " | ".join(raw for _, raw in later))

    later_strict = bool(first and later)
    if later_strict:
        first_date = max(dt for dt, _ in first).date()
        first_max = max(dt.time() for dt, _ in first)
        later_strict = all(dt.date() == first_date and dt.time() > first_max for dt, _ in later)

    status, body = gw_call("/availability", {
        "store": store, "from": "friday", "to": "friday", "after": "none",
        "before": "none", "time_pref": "none", "slot_minutes": "15"})
    slots = ((body.get("result") or {}).get("slots") or []) if isinstance(body, dict) else []
    inventory = {parse_inventory_start(slot.get("start")) for slot in slots}
    inventory.discard(None)
    offers_in_inventory = status == 200 and bool(first and later) and all(
        dt in inventory for dt, _ in first + later)
    never_denied = not (not later and DENIAL_RE.search(later_text))

    print(f"LATER_STRICTLY_GREATER={later_strict}")
    print(f"OFFERS_IN_INVENTORY={offers_in_inventory}")
    print(f"NEVER_DENIED={never_denied}")
    reasons = []
    if not first:
        reasons.append("first offer contained no parseable times")
    if not later:
        reasons.append(f"later reply contained no times: {mask(later_text)!r}")
    if not later_strict:
        reasons.append("later offers were not all strictly later on the same date")
    if not offers_in_inventory:
        reasons.append(f"offers were absent from inventory or availability HTTP {status}")
    if not never_denied:
        reasons.append(f"later availability was denied: {mask(later_text)!r}")
    if reasons:
        fail(reasons)
    print("VERDICT: PASS mode=incident")


def run_happy(H, version, patient_id, store):
    chat_id = create_chat(H, version)
    node = None
    for turn in ("hi", "the first available time works", "1", "yes"):
        node, _, _ = send_turn(H, chat_id, turn)
    for _ in range(2):
        if node and str(node).startswith("e_"):
            break
        node, _, _ = send_turn(H, chat_id, "thank you")
    print(f"END_NODE={node}")
    count_after, _ = gw_count(patient_id, store)
    print(f"GW_COUNT_AFTER={count_after}")
    final = gw_cleanup(patient_id, store)
    print(f"CLEANUP_FINAL_COUNT={final}")
    reasons = []
    if node != "e_booked":
        reasons.append(f"ended on {node!r}, expected 'e_booked'")
    if count_after != 1:
        reasons.append(f"GW count after was {count_after}, expected 1")
    if final != 0:
        reasons.append(f"cleanup left {final} appointment(s)")
    if reasons:
        fail(reasons)
    print("VERDICT: PASS mode=happy")


def main():
    modes = ("gate_booked", "gate_clean", "incident", "happy")
    if len(sys.argv) != 3 or sys.argv[2] not in modes:
        sys.exit("usage: v91_harness.py <pathway_version> gate_booked|gate_clean|incident|happy")
    try:
        version = int(sys.argv[1])
    except ValueError:
        sys.exit("pathway_version must be an integer")
    for name in ("BLAND_API_KEY", "GW_TOKEN", "HARNESS_PATIENT_ID",
                 "HARNESS_PATIENT_CELL", "HARNESS_STORE"):
        if not os.environ.get(name, "").strip():
            sys.exit(f"{name} not set")

    patient_id = os.environ["HARNESS_PATIENT_ID"].strip()
    store = os.environ["HARNESS_STORE"].strip()
    count_before, _ = gw_count(patient_id, store)
    print(f"GW_COUNT_BEFORE={count_before}")
    if count_before != 0:
        sys.exit(f"ABORT: subject has {count_before} upcoming appointment(s); need 0")

    sys.path.insert(0, HARNESS_DIR)
    import pathway_harness as H

    if sys.argv[2] == "gate_booked":
        run_gate_booked(H, version, patient_id, store)
    elif sys.argv[2] == "gate_clean":
        run_gate_clean(H, version)
    elif sys.argv[2] == "incident":
        run_incident(H, version, store)
    else:
        run_happy(H, version, patient_id, store)


if __name__ == "__main__":
    main()
