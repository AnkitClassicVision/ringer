#!/usr/bin/env python3
"""Deterministically rebase the four SPEC-v91 Revision 3 deltas onto v86."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = ROOT / "pathway-v86.json"
REF_PATH = ROOT / "pathway-v90.json"
OUT_PATH = Path(__file__).with_name("pathway-v91-draft.json")
CLASS_PATH = Path(__file__).with_name("v91-classification.json")


def by_id(items):
    return {item["id"]: item for item in items}


def replace_section(prompt, heading, next_heading, replacement):
    start = prompt.index(heading)
    end = prompt.index(next_heading, start)
    return prompt[:start] + replacement + "\n\n" + prompt[end:]


def edge(edge_id, source, target, label):
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": "custom",
        "animated": True,
        "sourceHandle": None,
        "targetHandle": None,
        "data": {
            "label": label,
            "isHighlighted": False,
            "description": f"Route from {source} to {target} when: {label}.",
        },
    }


def field_diff(base, ref):
    def same(a, b):
        return json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(b, sort_keys=True, separators=(",", ":"))
    out = set()
    for collection in ("nodes", "edges"):
        bm, rm = by_id(base[collection]), by_id(ref[collection])
        for ident in bm.keys() | rm.keys():
            if ident not in bm or ident not in rm:
                out.add((ident, "__object__"))
                continue
            for key in bm[ident].keys() | rm[ident].keys():
                if key == "data" and isinstance(bm[ident].get(key), dict) and isinstance(rm[ident].get(key), dict):
                    for dk in bm[ident][key].keys() | rm[ident][key].keys():
                        if not same(bm[ident][key].get(dk), rm[ident][key].get(dk)):
                            out.add((ident, "data." + dk))
                elif not same(bm[ident].get(key), rm[ident].get(key)):
                    out.add((ident, key))
    for key in base.keys() | ref.keys():
        if key not in {"nodes", "edges"} and not same(base.get(key), ref.get(key)):
            out.add(("__top__", key))
    return out


def classify(base, ref):
    d1_objects = {"e_defer", "n_appt_check"}
    d2_objects = {"n_reconcile_1", "n_reconcile_2", "e_booked_recovered", "e_book_unknown"}
    d1_edges = {
        "edge-n_identity-n_ask-count-1", "edge-n_identity-n_appt_check-count-1",
        "edge-n_confirm-n_office-change-requested-after-confirmation",
        "edge-n_confirm-e_booked-confirmation-delivered",
        "edge-n_confirm-e_defer-change-requested-after-confirmation",
        "edge-n_confirm-e_defer-anything-else-requested-after-booking",
        "edge-n_appt_check-e_defer-appt-count-1", "edge-n_appt_check-n_ask-appt-count-0",
        "edge-n_appt_check-n_ask-ok-true",
    }
    d2_edges = {
        "edge-n_book_1-e_booking_failed-book-success-true",
        "edge-n_book_2-e_booking_failed-book-success-true",
        "edge-n_book_1-n_reconcile_1-book-success-not-true",
        "edge-n_book_2-n_reconcile_2-book-success-not-true",
        "edge-n_reconcile_1-e_book_unknown-recon-ok-not-true",
        "edge-n_reconcile_1-e_booked_recovered-recon-count-ge-1",
        "edge-n_reconcile_1-e_book_unknown-recon-count-0",
        "edge-n_reconcile_2-e_book_unknown-recon-ok-not-true",
        "edge-n_reconcile_2-e_booked_recovered-recon-count-ge-1",
        "edge-n_reconcile_2-e_book_unknown-recon-count-0",
    }
    d1_fields = {
        ("n_identity", "data.responsePathways"), ("n_confirm", "data.prompt"),
        ("n_office", "data.globalLabel"), ("n_faq", "data.globalLabel"),
        ("e_existing", "data.globalLabel"),
    }
    d2_fields = {
        ("n_book_1", "data.responsePathways"), ("n_book_2", "data.responsePathways"),
        ("e_booking_failed", "data.text"),
    }
    result = {
        "open": {
            "OPEN-1": "n_faq insurance sentence stays at its v86 default",
            "OPEN-2": "analysis_options stays null",
        },
        "unclassified": {},
    }
    for ident, field in sorted(field_diff(base, ref)):
        if ident in d1_objects or ident in d1_edges or (ident, field) in d1_fields:
            bucket = "D1"
        elif ident in d2_objects or ident in d2_edges or (ident, field) in d2_fields:
            bucket = "D2"
        elif ident == "n_ask" and field == "data.prompt":
            bucket = "D3"
        elif field in {"position", "x", "y", "height"}:
            bucket = "layout"
        else:
            bucket = "stale-base residue"
        result.setdefault(ident, {})[field] = bucket
    return result


def main():
    base = json.loads(BASE_PATH.read_text())
    ref = json.loads(REF_PATH.read_text())
    graph = copy.deepcopy(base)
    nodes, ref_nodes = by_id(graph["nodes"]), by_id(ref["nodes"])

    # D1 nodes and mutations.
    for ident in ("e_defer", "n_appt_check"):
        graph["nodes"].append(copy.deepcopy(ref_nodes[ident]))
    nodes = by_id(graph["nodes"])
    nodes["n_identity"]["data"]["responsePathways"][3] = ["count", "==", "1", {"id": "n_appt_check", "name": "Identity confirmed"}]
    confirm_task = ('TASK. Confirm the appointment that was booked, in plain language, and name the booked time. '
        'For an English-language thread, the confirmation must end exactly with: "You\'re all set. If you have further questions, please call MK2 Optical at (212) 219-2219". '
        "This is one SMS bubble and must not contain any earlier duplicate 'all set' wording. "
        'For a Chinese-language thread, use this fixed close after naming the booked time: "您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219". '
        'If the patient then asks to change, cancel or move it, or asks for anything else, take the post-booking deferral path.')
    nodes["n_confirm"]["data"]["prompt"] = replace_section(nodes["n_confirm"]["data"]["prompt"], "TASK.", "NEVER.", confirm_task)
    clause = " This does not apply once a booking is confirmed."
    for ident in ("n_office", "n_faq", "n_help"):
        nodes[ident]["data"]["globalLabel"] += clause
    nodes["e_existing"]["data"]["globalLabel"] = "The patient has an appointment made outside this conversation they want to cancel or move."

    # D2 nodes and mutations.
    for ident in ("n_reconcile_1", "n_reconcile_2", "e_booked_recovered", "e_book_unknown"):
        node = copy.deepcopy(ref_nodes[ident])
        coords = {"n_reconcile_1": (7720, 3500), "n_reconcile_2": (8750, 3500),
                  "e_booked_recovered": (7720, 3720), "e_book_unknown": (8235, 3720)}[ident]
        node["x"], node["y"] = coords
        node["position"] = {"x": coords[0], "y": coords[1]}
        graph["nodes"].append(node)
    nodes = by_id(graph["nodes"])
    for ident, dest in (("n_book_1", "n_reconcile_1"), ("n_book_2", "n_reconcile_2")):
        nodes[ident]["data"]["responsePathways"][2] = ["book_success", "!=", "true", {"id": dest, "name": "Write outcome unknown - reconcile against the EMR"}]
    unknown = "I wasn't able to confirm whether that booking went through. The MK2 Optical office will double-check it and reach out to you. If you'd like, you can also call them at (212) 219-2219."
    nodes["e_booking_failed"]["data"]["text"] = unknown

    # D3: transplant only the TASK block from v90.
    ref_prompt = ref_nodes["n_ask"]["data"]["prompt"]
    greeting_task = ref_prompt[ref_prompt.index("TASK."):ref_prompt.index("\n\nNEVER.")]
    nodes["n_ask"]["data"]["prompt"] = replace_section(nodes["n_ask"]["data"]["prompt"], "TASK.", "NEVER.", greeting_task)

    # D4: the two exact Revision 3 replacements, and no routing mutation.
    offer = nodes["n_offer_3"]["data"]["prompt"]
    old_task = "These are as late as this day goes. If they want something later, say plainly that this is the latest the office has that day and offer to look at another day."
    new_task = ('These are the latest openings you have been shown for that day, and you have not been shown everything the day holds. '
        'If they ask for something later, do NOT claim this is the latest the office has and do NOT say the day has nothing later, because you have not been told that. '
        'Do not name any other time. Say you will look at another day for them, ask which day they would like, and take the path labelled "wants a different day".')
    old_never = "Never suggest there is anything later that day than these two."
    new_never = "Never say or imply that the office has nothing later that day than these two, because you have not been told that."
    assert old_task in offer and old_never in offer
    nodes["n_offer_3"]["data"]["prompt"] = offer.replace(old_task, new_task, 1).replace(old_never, new_never, 1)

    removed = {
        "edge-n_identity-n_ask-count-1", "edge-n_confirm-n_office-change-requested-after-confirmation",
        "edge-n_book_1-e_booking_failed-book-success-true", "edge-n_book_2-e_booking_failed-book-success-true",
    }
    graph["edges"] = [item for item in graph["edges"] if item["id"] not in removed]
    additions = [
        ("edge-n_identity-n_appt_check-count-1", "n_identity", "n_appt_check", "count == 1"),
        ("edge-n_appt_check-e_defer-appt-count-1", "n_appt_check", "e_defer", "appt_count >= 1"),
        ("edge-n_appt_check-n_ask-appt-count-0", "n_appt_check", "n_ask", "appt_count == 0"),
        ("edge-n_appt_check-n_ask-ok-true", "n_appt_check", "n_ask", "ok != true"),
        ("edge-n_confirm-e_booked-confirmation-delivered", "n_confirm", "e_booked", "confirmation delivered"),
        ("edge-n_confirm-e_defer-change-requested-after-confirmation", "n_confirm", "e_defer", "change requested after confirmation"),
        ("edge-n_confirm-e_defer-anything-else-requested-after-booking", "n_confirm", "e_defer", "anything else requested after booking"),
        ("edge-n_book_1-n_reconcile_1-book-success-not-true", "n_book_1", "n_reconcile_1", "book_success != true"),
        ("edge-n_book_2-n_reconcile_2-book-success-not-true", "n_book_2", "n_reconcile_2", "book_success != true"),
    ]
    for num in (1, 2):
        src = f"n_reconcile_{num}"
        additions.extend([
            (f"edge-{src}-e_book_unknown-recon-ok-not-true", src, "e_book_unknown", "recon_ok != true"),
            (f"edge-{src}-e_booked_recovered-recon-count-ge-1", src, "e_booked_recovered", "recon_count >= 1"),
            (f"edge-{src}-e_book_unknown-recon-count-0", src, "e_book_unknown", "recon_count == 0"),
        ])
    graph["edges"].extend(edge(*args) for args in additions)

    OUT_PATH.write_text(json.dumps(graph, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    CLASS_PATH.write_text(json.dumps(classify(base, ref), indent=1, sort_keys=True, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
