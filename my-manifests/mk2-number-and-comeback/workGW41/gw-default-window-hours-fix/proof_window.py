from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
CONTAINER = ROOT / "gwtest" / "container"
sys.path.insert(0, str(CONTAINER))
spec = importlib.util.spec_from_file_location("gw41_proof_gateway", CONTAINER / "bland_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
gateway.log.disabled = True

body = {"from": "none"}
gateway.clamp_availability_range(body)
start = gateway.datetime.strptime(body["from"], "%m/%d/%Y").strftime("%Y-%m-%d")
end = gateway.datetime.strptime(body["to"], "%m/%d/%Y").strftime("%Y-%m-%d")
print(f"CASE=default-window FROM={start} TO={end}")

# The flag is a pure function of requested clock plus slot boundaries. This
# representative offline fixture exercises that logic without claiming live
# availability or contacting EyeCloud.
slots = [{"start": f"{body['from']} 09:00 AM", "end": f"{body['from']} 09:30 AM"}]
result = {}
gateway.add_out_of_hours_flag(result, slots, {"after": "03:00 am"})
if result.get("out_of_hours") is True:
    print("CASE=oob-flag OUT_OF_HOURS=true REQUESTED=03:00 am")
else:
    print("CASE=oob-flag OFFLINE=untestable")
