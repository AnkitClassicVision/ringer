#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def why(x): print(f"WHY: {x}")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--receipts',required=True); ap.add_argument('--summary',required=True); a=ap.parse_args()
    failures=[]
    try: r=json.loads(Path(a.receipts).read_text()); s=json.loads(Path(a.summary).read_text())
    except Exception as e: why(f"route JSON parse failed: {e}"); return 1
    subject=s.get('subject',{})
    if subject.get('name')!='Vintage Optical': failures.append('subject name mismatch')
    lat,lon=subject.get('lat'),subject.get('lon')
    if not isinstance(lat,(int,float)) or not 39 <= lat <= 42: failures.append(f'implausible subject latitude {lat}')
    if not isinstance(lon,(int,float)) or not -91 <= lon <= -88: failures.append(f'implausible subject longitude {lon}')
    routes=s.get('routes',[])
    routed=[x for x in routes if x.get('status')=='routed']
    if len(routed)<5: failures.append(f'only {len(routed)} peers routed; need at least 5')
    ids={x.get('id') for x in routed}
    for required in ['R01','R03','R04','R05']:
        if required not in ids: failures.append(f'missing required routed peer {required}')
    for row in routed:
        m=row.get('route_minutes'); miles=row.get('route_miles')
        if not isinstance(m,(int,float)) or not 0 < m < 90: failures.append(f"implausible minutes for {row.get('id')}: {m}")
        if not isinstance(miles,(int,float)) or not 0 < miles < 80: failures.append(f"implausible miles for {row.get('id')}: {miles}")
        disp=(row.get('selected_display_name') or '').lower()
        if row.get('name')=='Focus On Eyes' and 'morton' not in disp: failures.append('Focus On Eyes geocode is not visibly Morton')
    if not r.get('limitations') or len(r['limitations'])<3: failures.append('route receipts lack limitations')
    if failures:
        for f in failures: why(f)
        return 1
    print(f"PASS: subject geocoded and {len(routed)} public OSRM peer routes captured with limitations")
    return 0

if __name__=='__main__': sys.exit(main())
