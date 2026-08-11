#!/usr/bin/env python3
"""Offline handler-seam proof for GW46's anaphoric user_text defer."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime
from pathlib import Path


stub = types.ModuleType("capability_registry")
stub.QueryError = Exception
stub.load_manifest = lambda: {}
stub.prepare_query = lambda *args, **kwargs: None
stub.render_query_result = lambda *args, **kwargs: None
sys.modules["capability_registry"] = stub

os.environ["ECP_RAW_TEXT_DATES"] = "1"
os.environ["ECP_TENANT_ID"] = "mott"
os.environ["ECP_LLM_INTENT"] = "authoritative"

gateway_path = Path(__file__).with_name("fixed-bland_gateway.py")
spec = importlib.util.spec_from_file_location("fixed_bland_gateway", gateway_path)
gateway = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gateway)
gateway._eastern_today = lambda: datetime(2026, 8, 4)


def resolve(user_text: str, model_from: str) -> str:
    body = {"user_text": user_text, "from": model_from, "to": model_from}
    gateway.clamp_availability_range(body)
    return datetime.strptime(body["from"], "%m/%d/%Y").date().isoformat()


week = resolve("What about Monday that week?", "monday the week of 08/18/2026")
day = resolve("What's the earliest I can do that day?", "monday the week of 08/18/2026")
away = resolve("I'm going away for two weeks", "in 2 weeks")
correction = resolve("No I said two weeks not today", "today")

assert week == "2026-08-17"
assert day == "2026-08-17"
assert away == "2026-08-18"
assert correction == "2026-08-18"
for anaphoric in (
    "Monday that week",
    "Monday the same week",
    "earliest that day",
    "either of those days",
    "Monday the week we discussed",
    "Monday the week we talked about",
):
    assert gateway._defer_anaphoric_user_text(anaphoric), anaphoric
for anchored in (
    "Monday that week, 08/18/2026",
    "that day August 18",
    "that week next Monday",
    "that day in two weeks",
    "that day tomorrow",
):
    assert not gateway._defer_anaphoric_user_text(anchored), anchored

print(f"CASE=anaphora-week FROM={week}")
print(f"CASE=anaphora-day FROM={day}")
print(f"CASE=away-override DATE={away}")
