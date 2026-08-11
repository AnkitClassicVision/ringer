#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    jp=d/'number_inventory.json'; md=d/'numeric_audit.md'
    for p in (jp,md):
        if not p.is_file() or p.stat().st_size<500: fail.append(f'missing or undersized {p.name}')
    if fail:
        [why(x) for x in fail]; return 1
    try: data=json.loads(jp.read_text())
    except Exception as e: why(f'invalid number_inventory.json: {e}'); return 1
    if 'CANARY' in jp.read_text() or 'CANARY' in md.read_text(): fail.append('canary text leaked into artifact')
    occ=data.get('visible_occurrences'); line=data.get('substantive_lineage'); cov=data.get('coverage',{})
    if not isinstance(occ,list) or len(occ)<25: fail.append('visible_occurrences must enumerate at least 25 numeric occurrences')
    if not isinstance(line,list) or len(line)<13: fail.append('substantive_lineage must contain at least 13 explained number families')
    req_fields={'label','display_value','canonical_value','unit','category','source_ids','source_paths','formula','derivation','why_on_page','confidence','limitations','status'}
    labels=[]; vals=[]; canon=[]
    for i,x in enumerate(line or []):
        if not isinstance(x,dict): fail.append(f'lineage[{i}] is not an object'); continue
        miss=req_fields-set(x); 
        if miss: fail.append(f'lineage[{i}] missing {sorted(miss)}')
        labels.append(str(x.get('label','')).replace('_',' ').lower()); vals.append(str(x.get('display_value','')).replace(',','').replace(' ','').lower()); canon.append(str(x.get('canonical_value','')).replace(',','').replace(' ','').lower())
        status=str(x.get('status',''))
        if status!='PASS' and not status.startswith('TRACED_'): fail.append(f'lineage[{i}] status is neither PASS nor a traced status')
        if not x.get('explanation') and not x.get('derivation'): fail.append(f'lineage[{i}] lacks explanation/derivation')
    required_labels=['client opportunity','room to win','practice competitiveness','digital presence','market demand','dry eye','myopia','specialty contact','population','under 18','65 plus','focus on eyes','measurement window']
    for label in required_labels:
        if not any(label in x for x in labels): fail.append(f'missing lineage family: {label}')
    required_vals=['54','43','58','57','52','51','17557','25.9','23.1','4.07','30']
    for val in required_vals:
        if val not in canon: fail.append(f'missing canonical explained value {val}')
    if cov.get('unexplained_substantive') not in ([],None): fail.append(f'unexplained substantive numbers remain: {cov.get("unexplained_substantive")}')
    if cov.get('status')!='PASS': fail.append('coverage.status is not PASS')
    text=md.read_text()
    for token in ['Verdict: PASS','Unexplained substantive numbers: none','Structural numbers','Source identifiers','Headline scores','Raw public facts','Route values','Fix Card math']:
        if token.lower() not in text.lower(): fail.append(f'numeric_audit.md missing {token}')
    if fail:
        [why(x) for x in fail]; return 1
    print(f'PASS: {len(occ)} visible numeric occurrences classified; {len(line)} substantive number families have source/formula lineage; none unexplained')
    return 0
if __name__=='__main__': sys.exit(main())
