"""Shared offline loader for the GW46 gateway regression suite."""

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


def load_gateway():
    gateway_path = Path(__file__).with_name("bland_gateway.py")
    spec = importlib.util.spec_from_file_location("gwtest_bland_gateway", gateway_path)
    gateway = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(gateway)
    gateway._eastern_today = lambda: datetime(2026, 8, 4)
    return gateway

