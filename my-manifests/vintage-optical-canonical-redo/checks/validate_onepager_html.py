#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup


def why(x): print(f'WHY: {x}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--html',required=True); ap.add_argument('--scores',required=True); ap.add_argument('--sources',required=True); a=ap.parse_args(); fail=[]
    raw=Path(a.html).read_text(encoding='utf-8'); sc=json.loads(Path(a.scores).read_text()); sr=json.loads(Path(a.sources).read_text())
    soup=BeautifulSoup(raw,'html.parser'); text=' '.join(soup.stripped_strings); low=text.lower(); scores=sc['scores']
    if '<!DOCTYPE html>' not in raw and '<!doctype html>' not in raw: fail.append('missing HTML doctype')
    for token in ['@page','Letter','8.5in','11in']:
        if token.lower() not in raw.lower(): fail.append(f'missing print contract token {token}')
    for token in ['INTERNAL-ONLY','UNROOMED','NOT FOR EXTERNAL USE','THE READ','YOUR MARKET','YOUR COMPETITION','YOUR OPPORTUNITY','FIRST 30 DAYS','higher = better','Confidence C','Public data']:
        if token.lower() not in low: fail.append(f'missing visible token {token}')
    if low.find('the read')>low.find('your market') and low.find('your market')!=-1: fail.append('The Read must precede the numbered story')
    visible={
      'room_to_win_score':'Room to Win', 'practice_competitiveness_score':'Practice Competitiveness',
      'client_opportunity_score':'Client Opportunity', 'digital_presence_score':'Digital Presence'
    }
    for k,label in visible.items():
        v=str(scores[k])
        if label.lower() not in low or not re.search(rf'{re.escape(label)}.{{0,80}}\b{v}\b',text,re.I): fail.append(f'visible score missing or mismatched: {label} {v}')
    pressure=str(scores['competitive_pressure_index'])
    if 'competitive pressure index' in low or 'competition facing score' in low: fail.append('raw high-bad pressure label is visible')
    if re.search(rf'(pressure|competition facing).{{0,50}}\b{pressure}\b',text,re.I): fail.append('raw high-bad pressure value is visible')
    if text.count('data-fix-card'):
        fail.append('data-fix-card leaked as visible text')
    cards=soup.select('[data-fix-card]')
    if len(cards)!=3: fail.append(f'exactly 3 visible Fix Cards required, got {len(cards)}')
    for c in cards:
        ct=' '.join(c.stripped_strings).lower()
        for token in ['owner','proof','math']:
            if token not in ct: fail.append(f'Fix Card missing visible {token}')
    hrefs=[]
    for node in soup.find_all('a'):
        value=node.get('href')
        if isinstance(value,str) and value:
            hrefs.append(value)
    http=[x for x in hrefs if x.startswith('http')]
    if len(set(http))<10: fail.append(f'need at least 10 unique clickable public links, got {len(set(http))}')
    known={x['url'] for x in sr.get('sources',[]) if x.get('url')}
    foreign=sorted(set(http)-known)
    allowed_foreign=[u for u in foreign if 'mybcat.com' in u or 'ankit98' in u]
    if len(foreign)!=len(allowed_foreign): fail.append(f'HTML includes unregistered source URLs: {sorted(set(foreign)-set(allowed_foreign))}')
    ids=set(re.findall(r'\b(?:S|R)\d{2}\b',text))
    if len(ids)<10: fail.append(f'only {len(ids)} visible source IDs')
    if not {'S01','S06','S09','S10','S11','S12','R01','R02','R03','R04','R05'}.intersection(ids): fail.append('core evidence IDs absent')
    for pattern in [r'—',r'(?i)lorem ipsum',r'(?i)sample',r'(?i)illustrative',r'(?i)client[- ]ready',r'(?i)prospect[- ]ready',r'(?i)guarantee',r'(?i)api[_ -]?key',r'(?i)password']:
        if re.search(pattern,raw): fail.append(f'banned pattern present: {pattern}')
    if '$' in text: fail.append('unsupported dollar claim visible in public-only one-pager')
    if len(text)<3000: fail.append(f'page text too sparse: {len(text)} chars')
    if len(text)>10000: fail.append(f'page text likely too dense: {len(text)} chars')
    if fail:
        for x in fail: why(x)
        return 1
    print(f"PASS: one-page HTML contract valid with 4 high-good scores, 3 Fix Cards, {len(ids)} visible evidence IDs, {len(set(http))} clickable links, and internal/unroomed boundary")
    return 0
if __name__=='__main__': sys.exit(main())
