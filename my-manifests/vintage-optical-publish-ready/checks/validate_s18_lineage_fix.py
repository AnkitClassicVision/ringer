#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
from bs4 import BeautifulSoup

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    names=['scores.json','sources.json','market_inputs.json','evidence.md','research_notes.md','scoring_notes.md','number-explainer.md','number-explainer.html','README.md','runlog.md']
    for n in names:
        if not (d/n).is_file() or (d/n).stat().st_size<100: fail.append(f'missing or undersized {n}')
    if fail: [why(x) for x in fail]; return 1
    scores=json.loads((d/'scores.json').read_text()); sources=json.loads((d/'sources.json').read_text()); market=json.loads((d/'market_inputs.json').read_text())
    src=sources.get('sources',[]); ids=[x.get('id') for x in src]
    if len(src)!=25 or len(set(ids))!=25: fail.append(f'expected 25 unique sources, got {len(src)}/{len(set(ids))}')
    s18=next((x for x in src if x.get('id')=='S18'),None)
    url='https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/cities/totals/sub-est2024.csv'
    if not s18: fail.append('S18 missing')
    else:
        if s18.get('url')!=url: fail.append('S18 URL incorrect')
        if '17,557' not in s18.get('claim_use',''): fail.append('S18 claim does not name 17,557')
        if s18.get('status') not in {'fetched_frozen','frozen'}: fail.append('S18 not marked frozen')
    if scores.get('project_room',{}).get('status')!='inventory_review_required': fail.append('top project_room status invalid')
    if scores.get('data_quality',{}).get('project_room_status')!='inventory_review_required': fail.append('data_quality project_room_status stale')
    city=market.get('city_context_only',{})
    if city.get('population_estimate_2024')!=17557 or city.get('population_estimate_2025')!=17565: fail.append('population vintages changed')
    if 'S18' not in city.get('source_ids',[]): fail.append('market historical lineage does not cite S18')
    ev=(d/'evidence.md').read_text(); rn=(d/'research_notes.md').read_text(); sn=(d/'scoring_notes.md').read_text(); md=(d/'number-explainer.md').read_text(); html=(d/'number-explainer.html').read_text(); readme=(d/'README.md').read_text(); runlog=(d/'runlog.md').read_text()
    for name,text in [('evidence',ev),('research_notes',rn),('scoring_notes',sn)]:
        if 'S18' not in text or '17,557' not in text: fail.append(f'{name} lacks S18 historical lineage')
    for text_name,text in [('markdown',md),('html',html)]:
        for token in ['25 unique source IDs','S01-S18','S18','17,557',url]:
            if token not in text: fail.append(f'{text_name} missing {token}')
        if '24 unique source IDs' in text: fail.append(f'{text_name} retains stale 24-source count')
    soup=BeautifulSoup(html,'html.parser'); links={a.get_text(' ',strip=True):a.get('href') for a in soup.find_all('a') if a.get_text(' ',strip=True)}
    if links.get('S18')!=url: fail.append('HTML S18 link missing or wrong')
    hist=soup.select_one('[data-number-id="population-historical-17557"]')
    if not hist or 'S18' not in hist.get_text(' ',strip=True): fail.append('historical number-map row does not cite S18')
    pop=soup.select_one('[data-number-id="population-vintages"]')
    parent=pop.parent if pop else None
    if not parent or 'S18' not in parent.get_text(' ',strip=True): fail.append('population section does not cite S18')
    if '25-record source registry' not in readme: fail.append('README source count not 25')
    if '25-source registry' not in runlog or 'S18' not in runlog: fail.append('runlog source count/lineage not updated')
    if '—' in ''.join([ev,rn,sn,md,html,readme,runlog]): fail.append('em dash present')
    if fail: [why(x) for x in fail]; return 1
    r=subprocess.run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_scores.py','--scores',str(d/'scores.json'),'--sources',str(d/'sources.json')],text=True,capture_output=True)
    if r.returncode: print(r.stdout+r.stderr,end=''); return r.returncode
    r=subprocess.run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_explainer_polish.py','--dir',str(d)],text=True,capture_output=True)
    if r.returncode: print(r.stdout+r.stderr,end=''); return r.returncode
    print('PASS: S18 separately registers frozen 2024 PEP 17,557 lineage, all 25 sources reconcile, stale Project Room status is fixed, and explainer/score gates pass')
    return 0
if __name__=='__main__': sys.exit(main())
