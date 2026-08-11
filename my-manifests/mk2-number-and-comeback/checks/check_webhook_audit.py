#!/usr/bin/env python3
"""Verify the webhook node settings audit (lane 4, manifestD).

Recomputes every mechanical fact per webhook node from pathway-v87.json — URL,
method, retry attempts, timeout-field presence, extracted responseData
variables, the set of variables consumed by responsePathways conditions, and
extracted-but-unconsumed variables — and requires the worker's audit to match
exactly. Judgment fields (effective-timeout note, missing-variable risks) are
checked for coverage and substantive rationale; the two /sign book nodes must
each carry at least one missing-variable risk because their routing consumes
$.success, which the measured 502 body does not contain.
Prints every failure reason; exit 0 only when all assertions hold.
"""

import argparse
import json
import sys

TIMEOUT_KEYS = ("timeout", "timeout_seconds", "timeoutSeconds")
RISK_REQUIRED = ("n_book_1", "n_book_2")


def load_json(path, label, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        errors.append(f"{label} not found at {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pathway", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    errors = []
    pathway = load_json(args.pathway, "pathway JSON", errors)
    report = load_json(args.report, "worker report", errors)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1

    webhooks = {n["id"]: n for n in pathway["nodes"] if n["type"] == "Webhook"}

    entries = report.get("webhooks")
    if not isinstance(entries, list):
        print("FAIL: report has no 'webhooks' list")
        return 1
    by_id = {e.get("id"): e for e in entries if isinstance(e, dict)}

    missing = sorted(set(webhooks) - set(by_id))
    extra = sorted(set(by_id) - set(webhooks))
    if missing:
        errors.append(f"webhooks: missing webhook nodes {missing}")
    if extra:
        errors.append(f"webhooks: ids that are not Webhook nodes in the pathway: {extra}")

    for nid, entry in by_id.items():
        if nid not in webhooks:
            continue
        data = webhooks[nid]["data"]
        ctx = f"webhooks.{nid}"

        if entry.get("url") != data.get("url"):
            errors.append(f"{ctx}: url mismatch — pathway {data.get('url')!r}, report {entry.get('url')!r}")
        if entry.get("method") != data.get("method"):
            errors.append(f"{ctx}: method mismatch — pathway {data.get('method')!r}, report {entry.get('method')!r}")

        actual_retries = (data.get("modelOptions") or {}).get("retryAttempts")
        if entry.get("retry_attempts") != actual_retries:
            errors.append(
                f"{ctx}: retry_attempts mismatch — pathway modelOptions.retryAttempts is {actual_retries!r}, "
                f"report says {entry.get('retry_attempts')!r}"
            )

        actual_timeout_present = any(k in data for k in TIMEOUT_KEYS)
        if entry.get("timeout_field_present") is not actual_timeout_present:
            errors.append(
                f"{ctx}: timeout_field_present must be {actual_timeout_present} "
                f"(checked keys {TIMEOUT_KEYS} in node data); report says {entry.get('timeout_field_present')!r}"
            )

        note = entry.get("effective_timeout_note")
        if not isinstance(note, str) or len(note.strip()) < 40:
            errors.append(f"{ctx}: 'effective_timeout_note' must be a string of at least 40 chars")

        expected_vars = [{"name": v["name"], "json_path": v["data"]} for v in data.get("responseData", [])]
        got_vars = entry.get("extracted_variables")
        if not isinstance(got_vars, list) or [
            {"name": v.get("name"), "json_path": v.get("json_path")} for v in got_vars if isinstance(v, dict)
        ] != expected_vars:
            errors.append(
                f"{ctx}: extracted_variables must match responseData in order.\n"
                f"  expected: {expected_vars}\n  reported: {got_vars!r}"
            )

        cond_vars = sorted({str(rp[0]) for rp in data.get("responsePathways", [])})
        got_cond = entry.get("condition_variables")
        if not isinstance(got_cond, list) or sorted(map(str, got_cond)) != cond_vars:
            errors.append(f"{ctx}: condition_variables must equal {cond_vars}; reported {got_cond!r}")

        extracted_names = {v["name"] for v in expected_vars}
        unused = sorted(extracted_names - set(cond_vars))
        got_unused = entry.get("unused_extracted_variables")
        if not isinstance(got_unused, list) or sorted(map(str, got_unused)) != unused:
            errors.append(f"{ctx}: unused_extracted_variables must equal {unused}; reported {got_unused!r}")

        risks = entry.get("missing_variable_risks")
        if not isinstance(risks, list):
            errors.append(f"{ctx}: 'missing_variable_risks' must be a list (may be empty)")
        else:
            if nid in RISK_REQUIRED and not risks:
                errors.append(
                    f"{ctx}: at least one missing_variable_risk is required — routing consumes $.success "
                    "and the measured 502 body {{\"error\":\"gateway_unreachable\",\"status\":502}} has no success key"
                )
            for i, risk in enumerate(risks):
                if not isinstance(risk, dict):
                    errors.append(f"{ctx}: missing_variable_risks[{i}] is not an object")
                    continue
                var = risk.get("variable")
                if var not in extracted_names and var not in cond_vars:
                    errors.append(
                        f"{ctx}: missing_variable_risks[{i}].variable {var!r} is neither extracted "
                        f"nor consumed by routing on this node"
                    )
                consequence = risk.get("consequence")
                if not isinstance(consequence, str) or len(consequence.strip()) < 80:
                    errors.append(f"{ctx}: missing_variable_risks[{i}].consequence must be at least 80 chars")

    note = report.get("catalog_default_note")
    if not isinstance(note, str) or len(note.strip()) < 80 or "10" not in note:
        errors.append(
            "'catalog_default_note' must be a string of at least 80 chars and must state the catalog "
            "default timeout_seconds value (10) so the drift against measured ~28s behavior is on record"
        )

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"\n{len(errors)} failure(s) in {args.report}")
        return 1
    print(f"PASS: all {len(webhooks)} webhook nodes audited; settings and variable flows match the pathway exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
