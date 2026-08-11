from __future__ import annotations

import datetime
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "gwtest" / "container" / "bland_gateway.py"
spec = importlib.util.spec_from_file_location("gw40_gateway_proof", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load {MODULE_PATH}")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)

cases = (
    ("away-sentence", "I'm leaving town today and won't be back for 2 weeks about then?"),
    ("until-18th", "I'm out of town until the 18th"),
    ("gone-10-days", "gone for 10 days"),
    ("plain-today", "I can come in today"),
    ("thursday", "thursday please"),
)

for label, sentence in cases:
    resolved = gateway.extract_date_from_text(sentence)
    parsed = datetime.datetime.strptime(resolved, "%m/%d/%Y")
    print(f"CASE={label} DATE={parsed:%Y-%m-%d}")
