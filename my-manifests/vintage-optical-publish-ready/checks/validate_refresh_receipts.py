#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    p=d/'receipt_summary.json'
    if not p.is_file(): why('receipt_summary.json missing'); return 1
    try: x=json.loads(p.read_text())
    except Exception as e: why(f'invalid receipt_summary.json: {e}'); return 1
    if x.get('status')!='PASS': fail.append('summary status not PASS')
    p25=x.get('census_pep_2025',{}); p24=x.get('census_pep_2024',{}); q=x.get('quickfacts_live_audit',{}); r=x.get('osrm_r01',{}); comp=x.get('baseline_comparison',{})
    if p25.get('http_status')!=200 or p25.get('values',{}).get('population_estimate')!=17565: fail.append('official PEP 2025 Morton population is not 17,565')
    if p24.get('http_status')!=200 or p24.get('values',{}).get('population_estimate')!=17557: fail.append('official PEP 2024 Morton population is not 17,557')
    for block in [p25,p24]:
        v=block.get('values',{})
        if v.get('name')!='Morton village' or v.get('state')!='Illinois': fail.append('PEP row is not Morton village, Illinois')
    if q.get('under_18_percent')!=25.9 or q.get('age_65_plus_percent')!=23.1: fail.append('QuickFacts live-audit age shares do not match 25.9/23.1')
    if q.get('retrieval_status') not in {'PASS','PASS_WITH_LIMITATION'}: fail.append('QuickFacts audit receipt status invalid')
    if r.get('http_status')!=200 or r.get('values',{}).get('code')!='Ok': fail.append('OSRM live receipt not Ok')
    rv=r.get('values',{})
    if not isinstance(rv.get('duration_seconds'),(int,float)) or rv.get('duration_seconds')<=0: fail.append('OSRM duration invalid')
    if comp.get('current_population_2025')!=17565 or comp.get('frozen_population_2024')!=17557 or comp.get('population_update_required') is not True: fail.append('population baseline comparison invalid')
    if comp.get('age_shares_unchanged') is not True: fail.append('age share comparison invalid')
    for f in ['source_receipts/census-pep-sub-est2025.csv','source_receipts/census-pep-sub-est2024.csv','source_receipts/quickfacts-live-audit-extract.json','source_receipts/osrm-r01-current.json']:
        if not (d/f).is_file() or (d/f).stat().st_size<20: fail.append(f'missing raw/audit receipt {f}')
    if fail: [why(z) for z in fail]; return 1
    print(f'PASS: official PEP files freeze Morton 2024=17,557 and 2025=17,565; live-audited age shares stay 25.9%/23.1%; current OSRM={rv.get("route_minutes_2dp")} minutes')
    return 0
if __name__=='__main__': sys.exit(main())
