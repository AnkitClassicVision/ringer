#!/usr/bin/env python3
"""Deterministically transform the v87 Bland pathway graph into the v88 draft."""

import copy
import json
from pathlib import Path


BASE = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v87.json")
OUTPUT = Path(__file__).resolve().parent / "pathway-v88-draft.json"

UNKNOWN_TEXT = (
    "I wasn't able to confirm whether that booking went through. The MK2 Optical "
    "office will double-check it and reach out to you. If you'd like, you can also "
    "call them at (212) 219-2219."
)


def route_edge(edge_id, source, target, label):
    return {
        "animated": True,
        "data": {
            "description": f"Route from {source} to {target} when: {label}.",
            "isHighlighted": False,
            "label": label,
        },
        "id": edge_id,
        "source": source,
        "sourceHandle": None,
        "target": target,
        "targetHandle": None,
        "type": "custom",
    }


def positioned_node(node_id, node_type, x, y, data):
    return {
        "data": data,
        "height": 115,
        "id": node_id,
        "position": {"x": x, "y": y},
        "sourcePosition": "bottom",
        "targetPosition": "top",
        "type": node_type,
        "width": 320,
        "x": x,
        "y": y,
    }


def main():
    with BASE.open("r", encoding="utf-8") as handle:
        graph = json.load(handle)

    nodes = {node["id"]: node for node in graph["nodes"]}

    for suffix in ("1", "2"):
        nodes[f"n_book_{suffix}"]["data"]["responsePathways"][2] = [
            "book_success",
            "!=",
            "true",
            {
                "id": f"n_reconcile_{suffix}",
                "name": "Write outcome unknown - reconcile against the EMR",
            },
        ]

    nodes["e_booking_failed"]["data"]["text"] = UNKNOWN_TEXT

    appt_check = nodes["n_appt_check"]["data"]
    for suffix, x in (("1", -560), ("2", -60)):
        graph["nodes"].append(
            positioned_node(
                f"n_reconcile_{suffix}",
                "Webhook",
                x,
                1010,
                {
                    "active": appt_check["active"],
                    "body": copy.deepcopy(appt_check["body"]),
                    "headers": copy.deepcopy(appt_check["headers"]),
                    "method": appt_check["method"],
                    "modelOptions": {"retryAttempts": 0, "skipUserResponse": True},
                    "name": f"Reconcile write outcome {suffix} (silent)",
                    "responseData": [
                        {"data": "$.ok", "name": "recon_ok"},
                        {"data": "$.result.count", "name": "recon_count"},
                    ],
                    "responsePathways": [
                        [
                            "recon_ok",
                            "!=",
                            "true",
                            {"id": "e_book_unknown", "name": "Reconcile read unavailable"},
                        ],
                        [
                            "recon_count",
                            ">=",
                            "1",
                            {"id": "e_booked_recovered", "name": "EMR shows the booking exists"},
                        ],
                        [
                            "recon_count",
                            "==",
                            "0",
                            {"id": "e_book_unknown", "name": "EMR shows no booking"},
                        ],
                    ],
                    "text": "",
                    "url": appt_check["url"],
                },
            )
        )

    end_active = nodes["e_booking_failed"]["data"]["active"]
    graph["nodes"].extend(
        [
            positioned_node(
                "e_booked_recovered",
                "End Call",
                -310,
                1160,
                {
                    "active": end_active,
                    "name": "booked_after_reconcile",
                    "outcome": "booked_after_reconcile",
                    "tag": {"color": "#455A64", "name": "outcome:booked_after_reconcile"},
                    "text": "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219",
                },
            ),
            positioned_node(
                "e_book_unknown",
                "End Call",
                -310,
                1310,
                {
                    "active": end_active,
                    "name": "booking_unverified",
                    "outcome": "booking_unverified",
                    "tag": {"color": "#455A64", "name": "outcome:booking_unverified"},
                    "text": UNKNOWN_TEXT,
                },
            ),
        ]
    )

    removed = {
        "edge-n_book_1-e_booking_failed-book-success-true",
        "edge-n_book_2-e_booking_failed-book-success-true",
    }
    graph["edges"] = [edge for edge in graph["edges"] if edge["id"] not in removed]

    graph["edges"].extend(
        [
            route_edge(
                f"edge-n_book_{suffix}-n_reconcile_{suffix}-book-success-not-true",
                f"n_book_{suffix}",
                f"n_reconcile_{suffix}",
                "book_success != true",
            )
            for suffix in ("1", "2")
        ]
    )

    for suffix in ("1", "2"):
        source = f"n_reconcile_{suffix}"
        graph["edges"].extend(
            [
                route_edge(
                    f"edge-{source}-e_book_unknown-recon-ok-not-true",
                    source,
                    "e_book_unknown",
                    "recon_ok != true",
                ),
                route_edge(
                    f"edge-{source}-e_booked_recovered-recon-count-ge-1",
                    source,
                    "e_booked_recovered",
                    "recon_count >= 1",
                ),
                route_edge(
                    f"edge-{source}-e_book_unknown-recon-count-0",
                    source,
                    "e_book_unknown",
                    "recon_count == 0",
                ),
            ]
        )

    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(graph, handle, indent=1, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
