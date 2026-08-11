#!/usr/bin/env python3
from __future__ import annotations
import argparse,re,subprocess,sys
from pathlib import Path
from bs4 import BeautifulSoup

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    r=subprocess.run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_explainer.py','--dir',str(d)],text=True,capture_output=True)
    if r.returncode: print(r.stdout+r.stderr,end=''); return r.returncode
    html=(d/'number-explainer.html').read_text(); md=(d/'number-explainer.md').read_text(); soup=BeautifulSoup(html,'html.parser'); text=soup.get_text(' ',strip=True)
    for banned in ['/home/','/mnt/','work-refresh','work-audit','work-stage','work-explainer','freeze-current-public-number-receipts']:
        if banned in text or banned in md: fail.append(f'internal workspace path leaked: {banned}')
    for token in ['data/receipt_summary.json','data/source_receipts/census-pep-sub-est2025.csv','data/source_receipts/census-pep-sub-est2024.csv','data/source_receipts/osrm-r01-current.json']:
        if token not in text or token not in md: fail.append(f'package-relative receipt path missing: {token}')
    if not re.search(r'thead\s*\{[^}]*display\s*:\s*table-header-group',html,re.I|re.S): fail.append('print CSS does not repeat table headers')
    if not soup.select_one('[data-section="room-to-win"]'): fail.append('Room to Win keep-together section marker missing')
    room=soup.select_one('[data-section="room-to-win"]')
    if room and 'avoid-break' not in str(room.get('class','')): fail.append('Room to Win section lacks avoid-break class')
    headings=[h.get_text(' ',strip=True).lower() for h in soup.find_all(['h1','h2','h3'])]
    for token in ['source dictionary: public sources','source dictionary: receipts and routes','final interpretation']:
        if not any(token in h for h in headings): fail.append(f'balanced final-section heading missing: {token}')
    if len(soup.find_all('thead'))<10: fail.append('too few semantic table headers for repeated-header print layout')
    if fail: [why(x) for x in fail]; return 1
    print('PASS: polished explainer has no internal path leaks, uses package-relative receipts, protects Room to Win pagination, repeats table headers, and balances the final source/receipt sections')
    return 0
if __name__=='__main__': sys.exit(main())
