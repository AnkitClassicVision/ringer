#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parent / "gw" / "container" / "bland_gateway.py"
DEFAULT_PHRASES = [
    "08/06/2026 10:30 am",
    "2 weeks from today",
    "two weeks from today",
    "in 2 weeks",
    "2 weeks",
    "10 days from now",
]


def load_parser():
    spec = importlib.util.spec_from_file_location("bland_gateway_proof", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resolve_relative_date


def main() -> None:
    parse = load_parser()
    for phrase in sys.argv[1:] or DEFAULT_PHRASES:
        resolved = parse(phrase)
        if resolved is None:
            raise ValueError(f"unresolved date phrase: {phrase}")
        month, day, year = resolved.split("/")
        print(f"PHRASE={phrase} DATE={year}-{month}-{day}")


if __name__ == "__main__":
    main()
