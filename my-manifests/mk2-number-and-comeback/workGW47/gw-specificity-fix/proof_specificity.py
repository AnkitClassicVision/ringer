#!/usr/bin/env python3
"""Offline handler-seam proof for the GW47 date-specificity gate."""

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path


stub = types.ModuleType("capability_registry")
stub.QueryError = Exception
stub.load_manifest = lambda: {}
stub.prepare_query = lambda *args, **kwargs: None
stub.render_query_result = lambda *args, **kwargs: None
sys.modules["capability_registry"] = stub

os.environ["ECP_RAW_TEXT_DATES"] = "1"
os.environ["ECP_TENANT_ID"] = "mott"
os.environ["ECP_LLM_INTENT"] = "off"

path = Path(__file__).with_name("deployed-bland_gateway.py")
spec = importlib.util.spec_from_file_location("gw47_gateway", path)
gateway = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gateway)

frozen_now = datetime(2026, 8, 4)
gateway._eastern_today = lambda: frozen_now


def resolve(user_text, model_from):
    body = {"user_text": user_text, "from": model_from, "to": model_from}
    gateway.clamp_availability_range(body)
    return datetime.strptime(body["from"], "%m/%d/%Y").date().isoformat()


explicit = resolve("No Thursday the 27", "08/27/2026")
assert explicit == "2026-08-27"
print(f"CASE=explicit-beats-weekday FROM={explicit}")

ordinal = resolve("No Thursday the 27", "thursday the 27")
assert ordinal == "2026-08-27"
assert gateway.extract_date_from_text("No Thursday the 27") == "08/27/2026"
print(f"CASE=ordinal FROM={ordinal}")

away = resolve("leaving town today, back in 2 weeks", "in 2 weeks")
expected_away = (frozen_now + timedelta(days=14)).date().isoformat()
assert away == expected_away
print(f"CASE=away-exception DATE={away}")

anaphora = resolve(
    "What about Monday that week?", "monday the week of 08/18/2026"
)
assert anaphora == "2026-08-17"
print(f"CASE=anaphora FROM={anaphora}")

assert resolve("thursday please", "thursday") == "2026-08-06"
