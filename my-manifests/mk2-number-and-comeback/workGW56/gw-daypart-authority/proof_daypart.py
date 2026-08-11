#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "gwtest" / "container"))
spec = importlib.util.spec_from_file_location("gw56_gateway", root / "fixed-bland_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


def effective(text, after="none", before="none", pref="none"):
    return gateway.enforce_verbatim_daypart_authority(text, after, before, pref)


print(f"CASE=afternoon-dropped AFTER={effective('Friday afternoon')[0].split()[0]}")
print(f"CASE=morning-window BEFORE={effective('saturday morning')[1].split()[0]}")
print(f"CASE=evening-window AFTER={effective('Thursday evening')[0].replace('04:', '16:').split()[0]}")
print(f"CASE=explicit-after-kept AFTER={effective('Friday afternoon', '03:00 pm')[0].replace('03:', '15:').split()[0]}")
print(f"CASE=anchor-outranks AFTER={effective('friday afternoon at 2', pref='anchor=2:00')[0]}")
print(f"CASE=greeting-not-trigger AFTER={effective('good afternoon, do you have friday?')[0]}")
