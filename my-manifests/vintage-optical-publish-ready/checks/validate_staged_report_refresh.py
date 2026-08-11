#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    names=['updated-scores.json','updated-market_inputs.json','updated-sources.json','updated-evidence.md','updated-research_notes.md','updated-scoring_notes.md','updated-onepager.html','build_report.md']
    for n in names:
        p=d/n
        if not p.is_file() or p.stat().st_size<300: fail.append(f'missing or undersized {n}')
    if fail: [why(x) for x in fail]; return 1
    try:
        scores=json.loads((d/'updated-scores.json').read_text()); market=json.loads((d/'updated-market_inputs.json').read_text()); sources=json.loads((d/'updated-sources.json').read_text())
    except Exception as e: why(f'invalid staged JSON: {e}'); return 1
    src=sources.get('sources',[]); ids=[x.get('id') for x in src]
    if len(src)!=24 or len(set(ids))!=24: fail.append(f'source registry must contain 24 unique records, got {len(src)}/{len(set(ids))}')
    s17=next((x for x in src if x.get('id')=='S17'),None)
    if not s17: fail.append('S17 missing')
    else:
        if s17.get('url')!='https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/cities/totals/sub-est2025.csv': fail.append('S17 URL is not official PEP 2025 file')
        if '17,565' not in s17.get('claim_use',''): fail.append('S17 claim_use missing 17,565')
    city=market.get('city_context_only',{})
    if city.get('population')!=17565 or city.get('population_estimate_2025')!=17565: fail.append('market current population must be 17,565')
    if city.get('population_estimate_2024')!=17557: fail.append('market historical 2024 population must remain 17,557')
    if city.get('under_18_percent_2020_2024')!=25.9 or city.get('age_65_plus_percent_2020_2024')!=23.1: fail.append('market age shares changed unexpectedly')
    if 'S17' not in city.get('source_ids',[]): fail.append('market city context does not cite S17')
    sc=scores.get('scores',{})
    expected={'market_demand_supply_score':57,'competitive_pressure_index':57,'room_to_win_score':43,'practice_competitiveness_score':58,'client_opportunity_score':54,'digital_presence_score':57}
    for k,v in expected.items():
        if sc.get(k)!=v: fail.append(f'{k} changed to {sc.get(k)} expected {v}')
    flat=json.dumps(scores)
    used=set(re.findall(r'"([SRN]\d{2})"',flat))
    missing=sorted(used-set(ids))
    if missing: fail.append(f'scores reference unknown source IDs {missing}')
    if 'S17' not in used: fail.append('updated scores do not cite S17 anywhere')
    html=(d/'updated-onepager.html').read_text(); low=html.lower()
    for token in ['17,565','2025 city estimate','S17','54 / 100','43 / 100','58 / 100','57 / 100','52 / 100','51 / 100','Internal-only','Unroomed','Not for external use']:
        if token.lower() not in low: fail.append(f'updated onepager missing {token}')
    if '17,557' in html: fail.append('historical 17,557 should not remain on one-page visible HTML')
    if '—' in html or any('—' in (d/n).read_text() for n in names if n.endswith('.md')): fail.append('em dash present')
    ev=(d/'updated-evidence.md').read_text()
    for token in ['17,565','17,557','S17','4.07','city context','not a drive-time']:
        if token.lower() not in ev.lower(): fail.append(f'updated evidence missing {token}')
    if fail: [why(x) for x in fail]; return 1
    commands=[
      ['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_scores.py','--scores',str(d/'updated-scores.json'),'--sources',str(d/'updated-sources.json')],
      ['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_onepager_html.py','--html',str(d/'updated-onepager.html'),'--scores',str(d/'updated-scores.json'),'--sources',str(d/'updated-sources.json')]
    ]
    for cmd in commands:
        r=subprocess.run(cmd,text=True,capture_output=True)
        if r.returncode: print(r.stdout+r.stderr,end=''); return r.returncode
    print('PASS: staged report refresh uses current 2025 population 17,565, preserves historical 17,557 in lineage, keeps all scores unchanged, adds S17, and passes canonical score/page gates')
    return 0
if __name__=='__main__': sys.exit(main())
