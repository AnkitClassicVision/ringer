#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REQUIRED_FILES = ["intake.md","evidence.md","sources.json","competitor_set.json","market_inputs.json","research_notes.md"]
REQUIRED_WINDOWS = [5,10,15,20,30]


def why(x): print(f"WHY: {x}")

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def walk_source_ids(obj):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k=='source_ids' and isinstance(v,list): out.extend(str(x) for x in v)
            else: out.extend(walk_source_ids(v))
    elif isinstance(obj,list):
        for v in obj: out.extend(walk_source_ids(v))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir)
    fail=[]
    for f in REQUIRED_FILES:
        if not (d/f).is_file() or (d/f).stat().st_size<50: fail.append(f'missing or empty {f}')
    if fail:
        for x in fail: why(x)
        return 1
    intake=(d/'intake.md').read_text()
    for token in ['practice_name: Vintage Optical','website_url: https://www.vintageopt.com/','locations: 605 S Main St, Morton, IL 61550','owner_intent: grow','data_mode: public_only','existing_client_check: yes-checked','relationship_result: prospect / not an existing MyBCAT client']:
        if token not in intake: fail.append(f'intake missing exact token: {token}')
    try:
        sources=load(d/'sources.json'); comp=load(d/'competitor_set.json'); market=load(d/'market_inputs.json')
    except Exception as e:
        why(f'JSON parse failed: {e}'); return 1
    source_rows=sources.get('sources',[])
    ids=[x.get('id') for x in source_rows if isinstance(x,dict)]
    if len(ids)<15: fail.append(f'only {len(ids)} source rows; need subject, peer, market, review-attempt, and route receipts')
    if len(ids)!=len(set(ids)): fail.append('duplicate source IDs')
    for row in source_rows:
        for k in ['id','url','source_family','accessed','claim_use','confidence','status','limitation']:
            if not row.get(k): fail.append(f"source {row.get('id')} missing {k}")
    allowed=set(ids)
    for obj_name,obj in [('competitor_set',comp),('market_inputs',market)]:
        missing=sorted(set(walk_source_ids(obj))-allowed)
        if missing: fail.append(f'{obj_name} has unresolved source IDs: {missing}')
    if comp.get('report_visibility')!='internal_only_unroomed_draft': fail.append('competitor_set visibility must be internal_only_unroomed_draft')
    if comp.get('project_room_status') not in ['EMPTY','UNROOMED']: fail.append('project room status must be EMPTY or UNROOMED')
    tiers=comp.get('tiers',{})
    t1=tiers.get('tier_1_direct_peers',[]); t2=tiers.get('tier_2_substitutes',[])
    if len(t1)<3: fail.append(f'need at least 3 Tier 1 peers, got {len(t1)}')
    if len(t2)<2: fail.append(f'need at least 2 Tier 2 substitutes, got {len(t2)}')
    allp=t1+t2
    names={x.get('name') for x in allp}
    for n in ['Focus On Eyes','Tri-County Eye Center Washington','Vision Care Center Washington','Walmart Vision Center Morton','Bard Optical East Peoria']:
        if n not in names: fail.append(f'missing required peer {n}')
    routed=[x for x in allp if isinstance(x.get('travel_time_minutes'),(int,float))]
    if len(routed)<5: fail.append(f'only {len(routed)} tiered peers carry route minutes')
    for p in allp:
        for k in ['name','category','address','match_basis','confidence','source_ids','website_url','public_evidence']:
            if not p.get(k): fail.append(f"peer {p.get('name')} missing {k}")
    if market.get('market_type') not in ['rural_small_town','exurban']:
        fail.append(f"market_type not canonically classified: {market.get('market_type')}")
    if market.get('catchment_method')!='rubric_selected_windows_without_measured_isochrones': fail.append('catchment method must declare no measured isochrones')
    windows=market.get('fixed_windows',[])
    if [x.get('minutes') for x in windows]!=REQUIRED_WINDOWS: fail.append('fixed windows must be exactly 5,10,15,20,30')
    for w in windows:
        for k in ['population','households','vision_demand_units','eye_care_offices','weighted_eye_care_offices','vdu_per_office']:
            if w.get(k) is not None: fail.append(f"window {w.get('minutes')} {k} must be null without polygon/dedupe proof")
        if 'known_routed_alternatives' not in w or 'unavailable_reason' not in w: fail.append(f"window {w.get('minutes')} lacks known-route context or unavailable reason")
    for k in ['population','median_household_income','under_18_percent','age_65_plus_percent']:
        if market.get('city_context_only',{}).get(k) is None: fail.append(f'city context missing {k}')
    text=(d/'evidence.md').read_text()
    if len(re.findall(r'\bS\d{2}\b|\bR\d{2}\b',text))<15: fail.append('evidence.md lacks source-ID density')
    for token in ['VERIFIED','INFERRED','UNKNOWN','Project Room','internal-only','review count','drive-time']:
        if token.lower() not in text.lower(): fail.append(f'evidence.md missing {token}')
    notes=(d/'research_notes.md').read_text().lower()
    for token in ['complete supply census','independent review','polygon isochrone','owned conversion','external actions: none']:
        if token not in notes: fail.append(f'research_notes missing {token}')
    banned=' '.join((d/f).read_text(errors='ignore') for f in REQUIRED_FILES)
    for pat in [r'(?i)lorem ipsum',r'(?i)api[_ -]?key\s*[:=]',r'(?i)password\s*[:=]',r'—']:
        if re.search(pat,banned): fail.append(f'banned pattern present: {pat}')
    if fail:
        for x in fail: why(x)
        return 1
    print(f'PASS: canonical evidence pack has {len(source_rows)} sources, {len(t1)} Tier 1 peers, {len(t2)} Tier 2 substitutes, {len(routed)} route-linked peers, fixed-window unknown handling, and internal/unroomed status')
    return 0

if __name__=='__main__': sys.exit(main())
