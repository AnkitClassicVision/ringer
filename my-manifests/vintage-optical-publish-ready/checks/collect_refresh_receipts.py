#!/usr/bin/env python3
from __future__ import annotations
import csv,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'MyBCAT-public-source-audit/1.0'})
    with urllib.request.urlopen(req,timeout=90) as r:
        return r.read(),dict(r.headers),r.status

def select_morton(csv_bytes,year):
    rows=csv.DictReader(csv_bytes.decode('latin-1').splitlines())
    found=[]
    for row in rows:
        name=str(row.get('NAME','')).strip().lower(); state=str(row.get('STNAME','')).strip().lower()
        if state=='illinois' and name=='morton village' and str(row.get('SUMLEV','')).strip()=='162': found.append(row)
    if len(found)!=1: raise SystemExit(f'WHY: expected one Illinois Morton village PEP {year} row, got {len(found)}')
    row=found[0]; key=f'POPESTIMATE{year}'
    if key not in row: raise SystemExit(f'WHY: PEP {year} missing {key}')
    return {'name':row['NAME'],'state':row['STNAME'],'state_fips':row.get('STATE'),'place_fips':row.get('PLACE'),'population_estimate':int(row[key]),'column':key}

def main():
    out=Path('.'); rec=out/'source_receipts'; rec.mkdir(exist_ok=True)
    pep25_url='https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/cities/totals/sub-est2025.csv'
    pep25,h25,s25=fetch(pep25_url); (rec/'census-pep-sub-est2025.csv').write_bytes(pep25); p25=select_morton(pep25,2025)
    pep24_url='https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/cities/totals/sub-est2024.csv'
    pep24,h24,s24=fetch(pep24_url); (rec/'census-pep-sub-est2024.csv').write_bytes(pep24); p24=select_morton(pep24,2024)
    source_audit=Path('/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/work-audit/challenge-sources-and-logic/source_checks.json')
    audited=json.loads(source_audit.read_text()); qcheck=next(x for x in audited['checks'] if x['source_id']=='S14')
    (rec/'quickfacts-live-audit-extract.json').write_text(json.dumps(qcheck,indent=2),encoding='utf-8')
    qv=qcheck['value']
    osrm_url='https://router.project-osrm.org/route/v1/driving/-89.4669666,40.6048878;-89.4680865,40.6196077?overview=false&steps=false&alternatives=false'
    rdata,rhdr,rstatus=fetch(osrm_url); (rec/'osrm-r01-current.json').write_bytes(rdata); route=json.loads(rdata)
    if route.get('code')!='Ok' or not route.get('routes'): raise SystemExit(f'WHY: OSRM returned {route.get("code")}')
    rr=route['routes'][0]; rvals={'duration_seconds':rr['duration'],'distance_meters':rr['distance'],'route_minutes_2dp':round(rr['duration']/60,2),'route_miles_2dp':round(rr['distance']/1609.344,2),'code':route['code']}
    summary={'schema_version':'1.1','retrieved_at':datetime.now(timezone.utc).isoformat(),'status':'PASS','census_pep_2025':{'url':pep25_url,'http_status':s25,'content_type':h25.get('Content-Type'),'values':p25},'census_pep_2024':{'url':pep24_url,'http_status':s24,'content_type':h24.get('Content-Type'),'values':p24},'quickfacts_live_audit':{'source_audit':str(source_audit),'retrieval_status':qcheck['status'],'source_url':qcheck['source_url'],'under_18_percent':qv['under_18_percent_2020_2024'],'age_65_plus_percent':qv['age_65_plus_percent_2020_2024'],'limitations':qcheck['limitations']},'osrm_r01':{'url':osrm_url,'http_status':rstatus,'values':rvals},'baseline_comparison':{'page_population_2024':17557,'frozen_population_2024':p24['population_estimate'],'current_population_2025':p25['population_estimate'],'population_update_required':p25['population_estimate']!=17557,'age_shares_unchanged':qv['under_18_percent_2020_2024']==25.9 and qv['age_65_plus_percent_2020_2024']==23.1,'page_route_minutes':4.07,'current_route_minutes':rvals['route_minutes_2dp'],'route_update_required':rvals['route_minutes_2dp']!=4.07}}
    (out/'receipt_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8'); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
