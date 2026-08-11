#!/usr/bin/env python3
from __future__ import annotations
import argparse,re,sys
from pathlib import Path
from bs4 import BeautifulSoup

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    hp=d/'number-explainer.html'; mp=d/'number-explainer.md'
    for p,minb in [(hp,12000),(mp,8000)]:
        if not p.is_file() or p.stat().st_size<minb: fail.append(f'missing or undersized {p.name}')
    if fail: [why(x) for x in fail]; return 1
    html=hp.read_text(); md=mp.read_text(); soup=BeautifulSoup(html,'html.parser'); text=soup.get_text(' ',strip=True); low=text.lower()
    for token in ['Vintage Optical','Internal publish-candidate','Project Room review required','How to read this analysis','Number map','Headline scores','Market Demand-Supply','Room to Win','Practice Competitiveness','Client Opportunity','Digital Presence','Specialty opportunities','Public facts and routes','Fix Card formulas','What we do not know','Logical consistency checks','Source dictionary','Confidence C']:
        if token.lower() not in low: fail.append(f'explainer missing {token}')
    for token in ['54 / 100','43 / 100','58 / 100','57 / 100','52 / 100','51 / 100','17,565','17,557','25.9%','23.1%','4.07','100 - 57 = 43','20, 35, 50, 65, 80']:
        if token.lower() not in low: fail.append(f'explainer missing number/formula {token}')
    for token in ['city context','not a drive-time catchment','not a complete supply census','neutral unknown','higher = better','plug-in','not a forecast','zero denominator','S17','2025 city estimate']:
        if token.lower() not in low: fail.append(f'explainer missing logic boundary {token}')
    links=set()
    for node in soup.find_all('a'):
        href=node.get('href')
        if isinstance(href,str) and href.startswith('http'):
            links.add(href)
    if len(links)<12: fail.append(f'only {len(links)} unique public links')
    ids=[x.get('data-number-id') for x in soup.select('[data-number-id]') if x.get('data-number-id')]
    if len(set(ids))<13: fail.append(f'only {len(set(ids))} data-number-id families')
    if '@page' not in html or not re.search(r'size\s*:\s*Letter',html,re.I): fail.append('Letter print CSS missing')
    if '—' in html or '—' in md: fail.append('em dash present')
    for banned in ['client-ready','prospect-ready','publish-ready','approved for publication','cleared for publication']:
        if banned in low: fail.append(f'premature readiness language: {banned}')
    if 'CANARY' in html or 'CANARY' in md: fail.append('canary text leaked')
    if len(md)<8000: fail.append('markdown explainer too short')
    if fail: [why(x) for x in fail]; return 1
    print(f'PASS: explainer covers {len(set(ids))} number families, {len(links)} source links, formulas, limitations, and internal Project Room boundary')
    return 0
if __name__=='__main__': sys.exit(main())
