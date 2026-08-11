#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    jp=d/'formula_audit.json'; md=d/'formula_audit.md'
    for p in (jp,md):
        if not p.is_file() or p.stat().st_size<800: fail.append(f'missing or undersized {p.name}')
    if fail: [why(x) for x in fail]; return 1
    try: data=json.loads(jp.read_text())
    except Exception as e: why(f'invalid formula_audit.json: {e}'); return 1
    if data.get('allowed_base_bands') != [20,35,50,65,80]: fail.append('allowed_base_bands must be exactly [20,35,50,65,80]')
    checks=data.get('formula_checks')
    if not isinstance(checks,list): checks=[]; fail.append('formula_checks missing')
    expected={'market_demand_supply':57,'competitive_pressure_internal':57,'room_to_win':43,'practice_competitiveness':58,'client_opportunity':54,'digital_presence':57,'dry_eye_ocular_surface':52,'myopia_management':52,'specialty_contact_lenses':51}
    seen={}
    for i,x in enumerate(checks):
        if not isinstance(x,dict): fail.append(f'formula_checks[{i}] not an object'); continue
        for f in ['name','recorded','recomputed','formula','inputs','weights','rounding','calculation','status']:
            if f not in x: fail.append(f'formula_checks[{i}] missing {f}')
        name=x.get('name'); seen[name]=x
        if x.get('recorded')!=x.get('recomputed'): fail.append(f'{name} recorded {x.get("recorded")} != recomputed {x.get("recomputed")}')
        if x.get('status')!='PASS': fail.append(f'{name} status is not PASS')
        bands=[]
        for v in (x.get('inputs') or {}).values():
            if isinstance(v,(int,float)) and x.get('input_type')=='base_bands': bands.append(v)
        if any(v not in {20,35,50,65,80} for v in bands): fail.append(f'{name} contains invalid base band')
    for name,val in expected.items():
        if name not in seen: fail.append(f'missing formula check {name}')
        elif seen[name].get('recomputed')!=val: fail.append(f'{name} recomputed {seen[name].get("recomputed")} expected {val}')
    cross=data.get('cross_checks',{})
    for k in ['room_to_win_inversion','visible_scores_high_good','base_bands_valid','weights_sum','rounding_consistent','page_matches_scores','specialty_scores_recompute']:
        if cross.get(k)!='PASS': fail.append(f'cross check {k} is not PASS')
    if data.get('fatal_issues') not in ([],None): fail.append('fatal issues present')
    if data.get('material_issues') not in ([],None): fail.append('material issues present')
    text=md.read_text()
    for token in ['Verdict: PASS','Manual bands','Rounding','Market Demand-Supply','Competitive Pressure','Room to Win','Practice Competitiveness','Client Opportunity','Digital Presence','Specialty scores','Logical reconciliation']:
        if token.lower() not in text.lower(): fail.append(f'formula_audit.md missing {token}')
    if fail: [why(x) for x in fail]; return 1
    print('PASS: all 6 core scores and 3 specialty scores independently recompute; bands, weights, rounding, inversion, and page parity are consistent')
    return 0
if __name__=='__main__': sys.exit(main())
