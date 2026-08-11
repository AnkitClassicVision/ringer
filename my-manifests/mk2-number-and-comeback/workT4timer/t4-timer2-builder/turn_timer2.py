#!/usr/bin/env python3
"""Time a scripted conversation against a pinned Bland pathway version."""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


API = "https://api.bland.ai"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"
TIMEOUT_SECONDS = 180
FILLER = "one moment while i check"


def usage():
    print("usage: turn_timer2.py <pathway_version> <script.json> <label>", file=sys.stderr)


def mask_digits(value):
    """Mask digit runs of five or more, retaining only their final four digits."""
    return re.sub(r"\d{5,}", lambda match: "***" + match.group(0)[-4:], str(value))


def one_line(value):
    return " ".join(mask_digits(value).split())


def post(api_key, path, payload):
    request = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "User-Agent": "mybcat-turn-timer",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
            body = json.loads(raw or "{}")
            return response.status, body
    except urllib.error.HTTPError as exc:
        reason = exc.read().decode("utf-8", errors="replace")[:300]
        return exc.code, reason
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def main():
    # Contract step 1: parse arguments without touching the environment.
    if len(sys.argv) != 4:
        usage()
        return 1
    pathway_version, script_path, label = sys.argv[1:]

    # Contract step 2: load and validate the script.
    try:
        with open(script_path, "r", encoding="utf-8") as handle:
            script = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"script error: {one_line(exc)}", file=sys.stderr)
        return 1
    turns = script.get("turns") if isinstance(script, dict) else None
    if not isinstance(turns, list) or any(not isinstance(turn, str) for turn in turns):
        print('script error: expected {"turns": ["..."]}', file=sys.stderr)
        return 1

    # Contract step 3: refuse booking confirmations before any environment read.
    if any(turn.strip().lower() in ("1", "yes") for turn in turns):
        print("REFUSED: scripted turn '1' or 'yes' could book a real appointment")
        return 2

    # Contract step 4: only now may required harness environment be read.
    patient_id = os.environ.get("HARNESS_PATIENT_ID", "").strip()
    if not patient_id:
        print("HARNESS_PATIENT_ID missing", file=sys.stderr)
        return 1
    api_key = os.environ.get("BLAND_API_KEY", "").strip()
    if not api_key:
        print("BLAND_API_KEY missing", file=sys.stderr)
        return 1

    candidate = int(os.environ.get("USE_CANDIDATE") == "1")
    payload = {
        "pathway_id": PATHWAY_ID,
        "pathway_version": pathway_version,
        "request_data": {
            "recall_patient_id": patient_id,
            "recall_cell": os.environ.get("HARNESS_PATIENT_CELL"),
            "store": os.environ.get("HARNESS_STORE", "711"),
            "campaign": "harness",
        },
    }
    if candidate:
        payload["use_candidate_model"] = True

    print(f"CANDIDATE={candidate}")
    status, body = post(api_key, "/v1/pathway/chat/create", payload)
    if status != 200:
        print(f"chat create failed: HTTP {status} {one_line(body)}", file=sys.stderr)
        return 1
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        print("chat create failed: response missing data object", file=sys.stderr)
        return 1
    print(f"CREATE_KEYS={sorted(data.keys())}")
    try:
        chat_id = data["chat_id"]
    except KeyError:
        print("chat create failed: response missing data.chat_id", file=sys.stderr)
        return 1

    total_wall_ms = 0
    filler_hits = 0
    for index, turn in enumerate(turns, start=1):
        started = time.monotonic_ns()
        status, body = post(api_key, f"/v1/pathway/chat/{chat_id}", {"message": turn})
        wall_ms = (time.monotonic_ns() - started) // 1_000_000
        total_wall_ms += wall_ms
        if status != 200:
            print(f"TURN_FAIL turn={index} reason=HTTP {status} {one_line(body)}")
            return 1
        if not isinstance(body, dict):
            print(f"TURN_FAIL turn={index} reason=invalid JSON response")
            return 1
        data = body.get("data") or {}
        responses = data.get("assistant_responses") or []
        if not isinstance(responses, list):
            print(f"TURN_FAIL turn={index} reason=assistant_responses was not a list")
            return 1
        messages = [str(message) for message in responses]
        filler_hits += sum(FILLER in message.lower() for message in messages)
        said = mask_digits(" | ".join(messages))[:200]
        node = one_line(data.get("current_node_id"))
        print(
            f"TURN={index} WALL_MS={wall_ms} N_MSGS={len(messages)} "
            f"NODE={node} SAID={said}"
        )

    print(
        f"RESULT label={label} turns={len(turns)} total_wall_ms={total_wall_ms} "
        f"filler_hits={filler_hits} candidate={candidate}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
