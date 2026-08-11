#!/usr/bin/env python3
"""Validate the Fable decision packet for the Mott v21 recall pathway rebuild.

Substance-strict, format-tolerant. Every failure prints the exact reason so the
retry prompt has something concrete to fix.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "mott-v21-decisions.v1"
ALL_DEFECTS = [f"F{n}" for n in range(1, 15)]

# Defects the approved plan committed to fixing in this build. Fable may add more
# to in_scope, but may not silently drop one of these into deferred.
MUST_BE_IN_SCOPE = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"]

REQUIRED_GLOBAL_NODES = {
    "negotiate": ("negotiat", "preference", "availability"),
    "office": ("office",),
    "stop": ("stop",),
    "not_me": ("not_me", "not me", "wrong"),
    "existing": ("existing",),
    "timeout": ("timeout",),
}

SLOT_PLACEHOLDERS = ["slot_1_start", "slot_1_end", "slot_2_start", "slot_2_end"]

# Field names that would put patient-identifying data into the analysis schema.
PHI_FIELD_PATTERN = re.compile(
    r"(?i)(patient_id|mrn|first_name|last_name|name_first|name_last|\bdob\b|birth|"
    r"phone|mobile|cell|email|address|insurance|ssn|recall_cell)"
)

MIN_RATIONALE_CHARS = 40


def fail(reasons: list[str]) -> None:
    print("DECISION PACKET CHECK FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    sys.exit(1)


def as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def as_blob(value: object) -> str:
    """Flatten a field that may legitimately be a string or a list of strings.

    Iterating a str yields characters, so a naive join over a string field
    produces character-spaced text that no phrase regex can match. Be tolerant
    on format and strict on substance.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(item for item in value if isinstance(item, str))
    return ""


def flatten(value: object, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for nested in value.values():
            flatten(nested, out)
    elif isinstance(value, list):
        for nested in value:
            flatten(nested, out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    args = parser.parse_args()

    if not args.packet.is_file():
        fail([f"decision packet not found: {args.packet}"])

    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail([f"decision packet is not valid JSON: {exc}"])
    if not isinstance(packet, dict):
        fail(["decision packet must be a JSON object"])

    reasons: list[str] = []

    if packet.get("schema_version") != SCHEMA_VERSION:
        reasons.append(
            f"schema_version must be exactly {SCHEMA_VERSION!r}, "
            f"got {packet.get('schema_version')!r}"
        )

    # --- defect coverage -------------------------------------------------
    in_scope = packet.get("in_scope")
    deferred = packet.get("deferred")
    if not isinstance(in_scope, list):
        reasons.append("in_scope must be a list of defect ids such as [\"F1\", \"F3\"]")
        in_scope = []
    if not isinstance(deferred, list):
        reasons.append(
            "deferred must be a list of objects, each {\"id\": \"F11\", \"why\": \"...\"}"
        )
        deferred = []

    deferred_ids = []
    for item in deferred:
        if not isinstance(item, dict):
            reasons.append(f"deferred entry is not an object: {item!r}")
            continue
        deferred_ids.append(as_text(item.get("id")))
        if len(as_text(item.get("why")).strip()) < MIN_RATIONALE_CHARS:
            reasons.append(
                f"deferred {item.get('id')!r} needs a 'why' of at least "
                f"{MIN_RATIONALE_CHARS} characters explaining the deferral"
            )

    covered = [d for d in in_scope if isinstance(d, str)] + deferred_ids
    for defect in ALL_DEFECTS:
        appearances = covered.count(defect)
        if appearances == 0:
            reasons.append(f"{defect} appears in neither in_scope nor deferred")
        elif appearances > 1:
            reasons.append(f"{defect} appears more than once across in_scope and deferred")

    for defect in MUST_BE_IN_SCOPE:
        if defect in deferred_ids:
            reasons.append(
                f"{defect} was deferred, but the approved plan commits to fixing it in this build"
            )

    # --- global node contract --------------------------------------------
    globals_list = packet.get("globals")
    if not isinstance(globals_list, list) or not globals_list:
        reasons.append("globals must be a non-empty list of global-node decisions")
        globals_list = []

    global_blob = " ".join(
        f"{as_text(g.get('node'))} {as_text(g.get('trigger'))}"
        for g in globals_list
        if isinstance(g, dict)
    ).lower()
    for role, hints in REQUIRED_GLOBAL_NODES.items():
        if not any(hint in global_blob for hint in hints):
            reasons.append(
                f"no global-node decision covers the {role!r} role "
                f"(expected one of {hints} in a node name or trigger)"
            )

    for entry in globals_list:
        if not isinstance(entry, dict):
            reasons.append(f"globals entry is not an object: {entry!r}")
            continue
        node = as_text(entry.get("node")) or "<unnamed>"
        if not isinstance(entry.get("autoReturn"), bool):
            reasons.append(
                f"global {node!r} must declare autoReturn as a boolean, "
                "because a global that auto-returns cannot own the negotiation loop"
            )
        if len(as_text(entry.get("trigger")).strip()) < 15:
            reasons.append(f"global {node!r} needs a concrete trigger description")
        if len(as_text(entry.get("why")).strip()) < MIN_RATIONALE_CHARS:
            reasons.append(
                f"global {node!r} needs a 'why' of at least {MIN_RATIONALE_CHARS} characters"
            )

    # --- opener ------------------------------------------------------------
    opener = packet.get("opener")
    if not isinstance(opener, dict):
        reasons.append("opener must be an object with template, slot_render_rule, one_slot_rule")
        opener = {}
    template = as_text(opener.get("template"))
    for placeholder in SLOT_PLACEHOLDERS:
        if placeholder not in template:
            reasons.append(
                f"opener.template never references {{{{{placeholder}}}}}; "
                "that omission is the original defect F1"
            )
    if "patient_first" not in template:
        reasons.append("opener.template must still personalize with patient_first")
    render_rule = as_text(opener.get("slot_render_rule"))
    if not re.search(r"(?i)new[_ ]?york|eastern|america/new_york", render_rule):
        reasons.append(
            "opener.slot_render_rule must name the display timezone explicitly "
            "(America/New_York), otherwise F2 is unfixed"
        )
    if len(as_text(opener.get("one_slot_rule")).strip()) < 20:
        reasons.append("opener.one_slot_rule must say what the message does when only one slot exists")

    # --- date contract ------------------------------------------------------
    date_contract = packet.get("date_contract")
    if not isinstance(date_contract, dict):
        reasons.append("date_contract must be an object")
        date_contract = {}
    if date_contract.get("passthrough_allowed") is not True:
        reasons.append(
            "date_contract.passthrough_allowed must be true; the gateway owns a "
            "deterministic relative-date resolver and the model must not compute dates"
        )
    must_not = as_blob(date_contract.get("model_must_not")).lower()
    if not re.search(r"mm/dd|normaliz|comput|calculat|resolve.*date", must_not):
        reasons.append(
            "date_contract.model_must_not must explicitly forbid the model from "
            "normalizing or computing calendar dates (defect F3)"
        )

    # --- booking invariants --------------------------------------------------
    invariants = packet.get("booking_invariants")
    if not isinstance(invariants, list) or len(invariants) < 3:
        reasons.append("booking_invariants must list at least three invariants")
        invariants = []
    invariant_blob = as_blob(invariants).lower()
    for needle, label in (("/sign", "booking goes through /sign only"),
                          ("conflict", "conflict check precedes booking"),
                          ("book_success", "confirmation gated on book_success")):
        if needle not in invariant_blob:
            reasons.append(f"booking_invariants never states that {label}")

    # --- analysis schema -----------------------------------------------------
    analysis = packet.get("analysis_schema")
    if not isinstance(analysis, dict):
        reasons.append("analysis_schema must be an object with a fields list")
        analysis = {}
    fields = analysis.get("fields")
    if not isinstance(fields, list) or not fields:
        reasons.append("analysis_schema.fields must be a non-empty list")
        fields = []
    field_names = [as_text(f.get("name")) for f in fields if isinstance(f, dict)]
    if not any("outcome" in n.lower() for n in field_names):
        reasons.append("analysis_schema needs an outcome field; that is the point of F9")
    # Only field names and enum values are scanned. Free-text descriptions may
    # legitimately say things like "no phone number is captured", and failing
    # those would be a format failure, not a substance failure.
    for field in fields:
        if not isinstance(field, dict):
            reasons.append(f"analysis_schema field is not an object: {field!r}")
            continue
        candidates: list[str] = [as_text(field.get("name"))]
        values = field.get("values")
        if isinstance(values, list):
            candidates.extend(v for v in values if isinstance(v, str))
        for text in candidates:
            match = PHI_FIELD_PATTERN.search(text)
            if match:
                reasons.append(
                    f"analysis_schema captures patient-identifying data: {match.group(0)!r} "
                    f"appears in field name or enum value {text!r}. The outcome schema "
                    "must stay PHI-free."
                )

    # --- start guard ---------------------------------------------------------
    start_guard = packet.get("start_guard")
    if not isinstance(start_guard, dict):
        reasons.append("start_guard must be an object")
        start_guard = {}
    if len(as_text(start_guard.get("on_missing_patient_id")).strip()) < 20:
        reasons.append(
            "start_guard.on_missing_patient_id must say what happens when the sender "
            "supplies no patient id (defect F8)"
        )

    # --- ownership and verification -------------------------------------------
    owned = packet.get("owned_paths")
    expected_owned = {
        "scripts/build_v21_recall_lanes.py",
        "scripts/validate_v21.py",
        "tests/test_v21_scenarios.py",
    }
    if not isinstance(owned, list) or set(owned) != expected_owned:
        reasons.append(f"owned_paths must be exactly {sorted(expected_owned)}, got {owned!r}")

    commands = packet.get("verification_commands")
    if not isinstance(commands, list) or not commands:
        reasons.append("verification_commands must be a non-empty list of executable commands")
        commands = []
    for command in commands:
        text = as_text(command)
        if not text.strip():
            reasons.append("verification_commands contains an empty command")
            continue
        if re.search(r"(?i)\b(curl|wget|git\s+push|pip\s+install|npm\s+install|ssh|aws|terraform)\b", text):
            reasons.append(
                f"verification command grants network, install, or deploy authority: {text!r}"
            )
        if text.strip() in {"true", "exit 0", ":"} or text.strip().startswith("echo "):
            reasons.append(f"verification command cannot fail, so it verifies nothing: {text!r}")

    # --- additional findings ------------------------------------------------------
    # The scout surfaced defects beyond F1..F14. These are the material ones; each
    # needs an explicit in-scope or deferred decision rather than silent omission.
    must_decide = ["AD5", "AD9", "AD11", "AD12", "AD13", "AD15"]
    additional = packet.get("additional_findings")
    if not isinstance(additional, list):
        reasons.append(
            "additional_findings must be a list of objects, each "
            "{\"id\": \"AD9\", \"decision\": \"in_scope\"|\"deferred\", \"why\": \"...\"}"
        )
        additional = []
    decided_ids = set()
    for item in additional:
        if not isinstance(item, dict):
            reasons.append(f"additional_findings entry is not an object: {item!r}")
            continue
        item_id = as_text(item.get("id"))
        decided_ids.add(item_id)
        if as_text(item.get("decision")).strip().lower() not in {"in_scope", "deferred"}:
            reasons.append(
                f"additional finding {item_id!r} needs decision 'in_scope' or 'deferred', "
                f"got {item.get('decision')!r}"
            )
        if len(as_text(item.get("why")).strip()) < MIN_RATIONALE_CHARS:
            reasons.append(
                f"additional finding {item_id!r} needs a 'why' of at least "
                f"{MIN_RATIONALE_CHARS} characters"
            )
    for item_id in must_decide:
        if item_id not in decided_ids:
            reasons.append(
                f"{item_id} from the verified defect ledger has no decision in "
                "additional_findings; decide it explicitly rather than dropping it"
            )

    # --- decision residue -------------------------------------------------------
    for key in ("hardest_decision", "least_confident_assumption"):
        if len(as_text(packet.get(key)).strip()) < MIN_RATIONALE_CHARS:
            reasons.append(f"{key} must be at least {MIN_RATIONALE_CHARS} characters of real reasoning")
    rejected = packet.get("alternatives_rejected")
    if not isinstance(rejected, list) or len(rejected) < 2:
        reasons.append("alternatives_rejected must name at least two rejected alternatives")

    if reasons:
        fail(reasons)

    print("DECISION PACKET CHECK PASSED")
    print(f"  in_scope: {len(in_scope)}  deferred: {len(deferred_ids)}")
    print(f"  globals: {len(globals_list)}")
    print(f"  analysis fields: {len(field_names)}")
    print(f"  verification commands: {len(commands)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
