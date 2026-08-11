#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
import fitz
from bs4 import BeautifulSoup

def why(m): print(f'WHY: {m}')
def run(cmd):
    r=subprocess.run(cmd,text=True,capture_output=True)
    if r.returncode: print(r.stdout+r.stderr,end=''); raise SystemExit(r.returncode)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); ap.add_argument('--receipt',required=True); a=ap.parse_args(); d=Path(a.report); fail=[]
    scores=json.loads((d/'scores.json').read_text()); sources=json.loads((d/'data/sources.json').read_text()); market=json.loads((d/'data/market_inputs.json').read_text()); receipt=json.loads(Path(a.receipt).read_text())
    if len(sources.get('sources',[]))!=25 or not any(x.get('id')=='S18' for x in sources.get('sources',[])): fail.append('25-source registry/S18 missing')
    if scores.get('project_room',{}).get('status')!='inventory_review_required' or scores.get('data_quality',{}).get('project_room_status')!='inventory_review_required': fail.append('Project Room statuses do not reconcile')
    if 'S18' not in market.get('city_context_only',{}).get('source_ids',[]): fail.append('market historical lineage missing S18')
    html=(d/'number-explainer.html').read_text(); md=(d/'number-explainer.md').read_text(); runlog=(d/'runlog.md').read_text(); soup=BeautifulSoup(html,'html.parser')
    if '25 unique source IDs' not in html or '25 unique source IDs' not in md: fail.append('25-source count missing from explainer')
    if '24 unique source IDs' in html or '24 unique source IDs' in md: fail.append('stale 24-source count remains')
    hist=soup.select_one('[data-number-id="population-historical-17557"]')
    if not hist or 'S18' not in hist.get_text(' ',strip=True): fail.append('historical row does not cite S18')
    if 'Post-S18 visual QA: PASS' not in runlog and 'Post-S18 visual QA: PENDING' not in runlog: fail.append('runlog missing post-S18 visual QA state')
    doc=fitz.open(d/'number-explainer.pdf')
    if len(doc)!=11: fail.append(f'explainer pages={len(doc)}, expected 11')
    imgs=sorted(d.glob('number-explainer-page-*.png'),key=lambda x:int(x.stem.rsplit('-',1)[1]))
    if len(imgs)!=len(doc): fail.append(f'page image count {len(imgs)} != PDF pages {len(doc)}')
    if receipt.get('source_count')!=25 or receipt.get('explainer_pages')!=11: fail.append('integration receipt invalid')
    if fail: [why(x) for x in fail]; return 1
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_scores.py','--scores',str(d/'scores.json'),'--sources',str(d/'data/sources.json')])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_onepager_html.py','--html',str(d/'onepager.html'),'--scores',str(d/'scores.json'),'--sources',str(d/'data/sources.json')])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_explainer_polish.py','--dir',str(d)])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_rendered_explainer.py','--dest',str(d)])
    print('PASS: integrated S18 correction has 25-source lineage, reconciled Project Room status, 11-page Chrome explainer, exact page-image set, and recorded post-S18 visual QA state')
    return 0
if __name__=='__main__': sys.exit(main())
