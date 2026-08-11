#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    jp=d/'source_checks.json'; md=d/'source_logic_audit.md'
    for p in (jp,md):
        if not p.is_file() or p.stat().st_size<800: fail.append(f'missing or undersized {p.name}')
    if fail: [why(x) for x in fail]; return 1
    try: data=json.loads(jp.read_text())
    except Exception as e: why(f'invalid source_checks.json: {e}'); return 1
    checks=data.get('checks')
    if not isinstance(checks,list) or len(checks)<8: fail.append('need at least 8 source checks')
    ids=set()
    for i,x in enumerate(checks or []):
        if not isinstance(x,dict): fail.append(f'checks[{i}] not object'); continue
        for f in ['source_id','claim','value','source_url','retrieval','result','limitations','status']:
            if f not in x: fail.append(f'checks[{i}] missing {f}')
        ids.add(x.get('source_id'))
        if x.get('status') not in {'PASS','PASS_WITH_LIMITATION'}: fail.append(f'checks[{i}] status not acceptable')
    for sid in ['S01','S07','S08','S10','S11','S12','S14','S15','R01']:
        if sid not in ids: fail.append(f'missing current source check {sid}')
    logic=data.get('logic_checks',{})
    required=['city_context_not_catchment','routes_not_complete_supply','unknowns_neutral_not_measured','all_visible_scores_high_good','raw_pressure_hidden','no_operating_forecasts','specialty_reads_research_next','fix_card_math_not_forecast','peer_tiers_bounded','claims_resolve_to_registry']
    for k in required:
        if logic.get(k)!='PASS': fail.append(f'logic check {k} is not PASS')
    if data.get('fatal_issues') not in ([],None): fail.append('fatal issues present')
    if data.get('material_issues') not in ([],None): fail.append('material issues present')
    text=md.read_text()
    for token in ['Verdict: PASS','Disconfirming checks','City context','Catchment','Route limitations','Unknown handling','Score direction','Peer tiers','Fix Card math','Publication boundary']:
        if token.lower() not in text.lower(): fail.append(f'source_logic_audit.md missing {token}')
    if 'CANARY' in text or 'CANARY' in jp.read_text(): fail.append('canary text leaked into artifact')
    if fail: [why(x) for x in fail]; return 1
    print(f'PASS: {len(checks)} current source checks and {len(required)} logic checks passed with no fatal/material inconsistency')
    return 0
if __name__=='__main__': sys.exit(main())
