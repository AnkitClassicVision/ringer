#!/usr/bin/env python3
from __future__ import annotations
import argparse,re,sys
from pathlib import Path
import fitz

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dest',required=True); a=ap.parse_args(); d=Path(a.dest); fail=[]
    req=['number-explainer.pdf','number-explainer.html','number-explainer.md','data/number-explainer-text.txt','number-explainer-qa-contact-sheet.png']
    for f in req:
        if not (d/f).is_file() or (d/f).stat().st_size<1000: fail.append(f'missing or undersized {f}')
    if fail: [why(x) for x in fail]; return 1
    doc=fitz.open(d/'number-explainer.pdf')
    if not 4<=len(doc)<=15: fail.append(f'page count {len(doc)} outside 4..15')
    links=set(); text=''; out=0
    for i,p in enumerate(doc):
        if abs(p.rect.width-612)>2 or abs(p.rect.height-792)>2: fail.append(f'page {i+1} not Letter: {p.rect.width}x{p.rect.height}')
        text+=p.get_text()
        for l in p.get_links():
            if l.get('uri'): links.add(l['uri'])
        for s in p.get_text('dict').get('blocks',[]):
            if 'lines' not in s: continue
            for line in s['lines']:
                for span in line['spans']:
                    x0,y0,x1,y1=span['bbox']
                    if x0<-1 or y0<-1 or x1>p.rect.width+1 or y1>p.rect.height+1: out+=1
    low=text.lower(); compact=re.sub(r'\s+','',low)
    for token in ['Vintage Optical','Project Room review required','How to read this analysis','Headline scores','Logical consistency checks','Source dictionary','17,557','25.9%','23.1%','4.07','100 - 57 = 43']:
        if re.sub(r'\s+','',token.lower()) not in compact: fail.append(f'PDF text missing {token}')
    if len(links)<12: fail.append(f'only {len(links)} unique PDF links')
    if len(text)<10000: fail.append(f'PDF extracted text too short: {len(text)}')
    if out: fail.append(f'{out} text spans outside page bounds')
    for banned in ['client-ready','prospect-ready','publish-ready','approved for publication','cleared for publication']:
        if banned in low: fail.append(f'premature readiness language in PDF: {banned}')
    if fail: [why(x) for x in fail]; return 1
    print(f'PASS: explainer renders as {len(doc)} Letter pages with {len(links)} links, {len(text)} extracted characters, and no out-of-bounds text')
    return 0
if __name__=='__main__': sys.exit(main())
