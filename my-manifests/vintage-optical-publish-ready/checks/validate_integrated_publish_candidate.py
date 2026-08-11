#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
import fitz

def why(m): print(f'WHY: {m}')
def run(cmd):
    r=subprocess.run(cmd,text=True,capture_output=True)
    if r.returncode: print(r.stdout+r.stderr,end=''); raise SystemExit(r.returncode)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); ap.add_argument('--receipt',required=True); a=ap.parse_args(); d=Path(a.report); fail=[]
    req=['scores.json','data/market_inputs.json','data/sources.json','data/evidence.md','data/receipt_summary.json','data/source_receipts/census-pep-sub-est2025.csv','data/source_receipts/census-pep-sub-est2024.csv','data/source_receipts/osrm-r01-current.json','onepager.html','onepager.pdf','onepager-qa.png','number-explainer.md','number-explainer.html','number-explainer.pdf','number-explainer-qa-contact-sheet.png','README.md','runlog.md']
    for f in req:
        if not (d/f).is_file() or (d/f).stat().st_size<100: fail.append(f'missing or undersized {f}')
    if fail: [why(x) for x in fail]; return 1
    market=json.loads((d/'data/market_inputs.json').read_text()); sources=json.loads((d/'data/sources.json').read_text()); scores=json.loads((d/'scores.json').read_text()); receipt=json.loads(Path(a.receipt).read_text())
    if market.get('city_context_only',{}).get('population')!=17565: fail.append('market current population is not 17,565')
    if market.get('city_context_only',{}).get('population_estimate_2024')!=17557: fail.append('historical 17,557 missing')
    if len(sources.get('sources',[]))!=25 or not any(x.get('id')=='S18' for x in sources.get('sources',[])): fail.append('25-source registry with S18 missing')
    html=(d/'onepager.html').read_text(); exp=(d/'number-explainer.html').read_text(); runlog=(d/'runlog.md').read_text()
    if '17,565' not in html or '17,557' in html: fail.append('one-page population display incorrect')
    if '17,565' not in exp or '17,557' not in exp: fail.append('explainer lacks current and historical population lineage')
    for token in ['Publish-candidate visual QA: PENDING','Project Room: inventory_review_required','External actions: none']:
        if token.lower() not in runlog.lower(): fail.append(f'runlog missing {token}')
    for p in [d/'onepager.html',d/'number-explainer.html',d/'number-explainer.md']:
        if '—' in p.read_text(): fail.append(f'em dash present in {p.name}')
    one=fitz.open(d/'onepager.pdf')
    if len(one)!=1 or abs(one[0].rect.width-612)>2 or abs(one[0].rect.height-792)>2: fail.append('onepager PDF is not one Letter page')
    if receipt.get('status')!='PASS' or receipt.get('project_room')!='inventory_review_required' or receipt.get('external_actions')!='none': fail.append('integration receipt boundary invalid')
    if fail: [why(x) for x in fail]; return 1
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_scores.py','--scores',str(d/'scores.json'),'--sources',str(d/'data/sources.json')])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_onepager_html.py','--html',str(d/'onepager.html'),'--scores',str(d/'scores.json'),'--sources',str(d/'data/sources.json')])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-canonical-redo/checks/validate_rendered_packet.py','--dest',str(d)])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_explainer_polish.py','--dir',str(d)])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_rendered_explainer.py','--dest',str(d)])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_refresh_receipts.py','--dir',str(d/'data')])
    print('PASS: integrated internal publish-candidate has current source receipts, unchanged formula-valid scores, one Letter one-pager, rendered number explainer, and pending new visual QA with external use blocked')
    return 0
if __name__=='__main__': sys.exit(main())
