#!/usr/bin/env python3
"""Offline proof through build_argv, the resolution entry called by Handler.do_POST."""

import datetime
import importlib.util
import sys
import types
from pathlib import Path


registry = types.ModuleType("capability_registry")
registry.QueryError = type("QueryError", (Exception,), {})
registry.load_manifest = lambda: {}
registry.prepare_query = lambda *args, **kwargs: None
registry.render_query_result = lambda *args, **kwargs: None
sys.modules["capability_registry"] = registry

gateway_path = Path(__file__).with_name("fixed-bland_gateway.py")
spec = importlib.util.spec_from_file_location("gw44b_fixed_gateway", gateway_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {gateway_path.name}")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)
gateway._RAW_TEXT_DATES = True
gateway.TENANT_ID = "mott"


def resolve_via_live_entry(from_text, to_text=None):
    body = {
        "store": "711",
        "from": from_text,
        "to": to_text or from_text,
        "user_text": from_text,
    }
    argv, _ = gateway.build_argv("/availability", body)
    return body, argv[argv.index("--from") + 1]


week_body, week_from = resolve_via_live_entry("monday the week of 08/18/2026")
gibberish_body, _ = resolve_via_live_entry("xyzzy gibberish plugh")
next_body, next_from = resolve_via_live_entry("monday next week")

assert week_from == "08/17/2026"
assert gibberish_body.get("from_unresolved") is True
assert next_from == "08/10/2026"
print(f"CASE=week-of-18th FROM={datetime.datetime.strptime(week_from, '%m/%d/%Y'):%Y-%m-%d}")
print("CASE=gibberish UNRESOLVED=true")
print(f"CASE=monday-next-week FROM={datetime.datetime.strptime(next_from, '%m/%d/%Y'):%Y-%m-%d}")
