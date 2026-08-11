#!/usr/bin/env python3
"""Validate a round-1 Fable decision packet, including controlled QUESTION output."""

from __future__ import annotations

import sys
from pathlib import Path

from lib_packets import PacketError, WhyArgumentParser, load_json_object, print_why, validate_decision_packet


def main(argv: list[str] | None = None) -> int:
    parser = WhyArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="decision-packet.json")
    args = parser.parse_args(argv)
    try:
        data = load_json_object(args.packet)
        validate_decision_packet(data)
    except (PacketError, OSError) as exc:
        print_why(exc)
        return 1
    shape = "QUESTION" if "question" in data else "DECISION"
    print(f"PASS: valid Fable {shape} packet with executable build-unit verification")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover - fail closed on unexpected runtime errors
        print_why(exc)
        sys.exit(1)
