#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path


def cp(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)

def sha(p):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--evidence',required=True); ap.add_argument('--scores',required=True); ap.add_argument('--html',required=True); ap.add_argument('--routes',required=True); ap.add_argument('--dest',required=True); ap.add_argument('--receipt',required=True)
    a=ap.parse_args(); ev=Path(a.evidence); sc=Path(a.scores); hb=Path(a.html); rt=Path(a.routes); d=Path(a.dest)
    (d/'data').mkdir(parents=True,exist_ok=True); (d/'assets').mkdir(parents=True,exist_ok=True)
    cp(ev/'intake.md',d/'intake.md'); cp(ev/'evidence.md',d/'data/evidence.md'); cp(ev/'sources.json',d/'data/sources.json'); cp(ev/'competitor_set.json',d/'data/competitor_set.json'); cp(ev/'market_inputs.json',d/'data/market_inputs.json'); cp(ev/'research_notes.md',d/'data/research_notes.md')
    cp(rt/'route_receipts.json',d/'data/route_receipts.json'); cp(rt/'routing_summary.json',d/'data/routing_summary.json')
    cp(sc/'scores.json',d/'scores.json'); cp(sc/'scoring_notes.md',d/'data/scoring_notes.md')
    cp(hb/'onepager.html',d/'onepager.html'); cp(hb/'build_notes.md',d/'data/build_notes.md')
    cp(Path('/mnt/d_drive/repos/optometry-competition-analyzer-rubric/client-onepager/assets/mybcat-logo.png'),d/'assets/mybcat-logo.png')
    chrome=['/usr/bin/google-chrome','--headless=new','--no-sandbox','--disable-gpu','--allow-file-access-from-files','--no-pdf-header-footer',f'--print-to-pdf={d / "onepager.pdf"}',(d/'onepager.html').resolve().as_uri()]
    subprocess.run(chrome,check=True,capture_output=True,text=True,timeout=120)
    subprocess.run(['/usr/bin/pdftotext','-layout',str(d/'onepager.pdf'),str(d/'data/onepager-text.txt')],check=True,timeout=60)
    subprocess.run(['/usr/bin/pdftoppm','-png','-r','150','-singlefile',str(d/'onepager.pdf'),str(d/'onepager-qa')],check=True,timeout=120)
    stamp=datetime.now(timezone.utc).isoformat()
    scores=json.loads((d/'scores.json').read_text())['scores']
    runlog=f'''# Vintage Optical canonical GROW runlog\n\nGenerated: {stamp}\nPractice: Vintage Optical, 605 S Main St, Morton, IL 61550\nProduct: single_practice\nData mode: public_only\nReport visibility: internal_only_unroomed_draft\nProject Room: EMPTY / UNROOMED\nExternal actions: none\n\n## Canonical stages\n\n1. Stage 0 intake: exact six-field GROW gate recorded in `intake.md`.\n2. Stage 1 evidence: 23-source registry, 3 Tier 1 peers, 3 Tier 2 substitutes, five successful OSRM point routes, exact fixed windows with unavailable catchment inputs kept null.\n3. Stage 1 scoring: manual public-only bands {{20, 35, 50, 65, 80}} with source-linked basis and formula recomputation.\n4. Stage 2 website and positioning: Digital Presence components plus the required four-field positioning read.\n5. Stage 5 Fix-It: exactly three GROW Fix Cards with plug-in or sensitivity math.\n6. Render: Chrome 150 headless using the approved `client-onepager/sample-onepager-b.html` contract.\n\n## Score receipt\n\n- Market Demand-Supply: {scores['market_demand_supply_score']}\n- Competitive Pressure, internal only: {scores['competitive_pressure_index']}\n- Room to Win, visible high-good: {scores['room_to_win_score']}\n- Practice Competitiveness: {scores['practice_competitiveness_score']}\n- Client Opportunity: {scores['client_opportunity_score']}\n- Digital Presence: {scores['digital_presence_score']}\n- Confidence: {scores['confidence_grade']}\n\n## Render command\n\n```text\n{' '.join(chrome)}\n```\n\nPDF SHA-256: `{sha(d/'onepager.pdf')}`\n\n## Ringer run IDs\n\nRUN_IDS_PENDING_FINAL_CLOSE\n\n## Human gate\n\nThis packet is internal-only and unroomed. Human source-authority review and Project Room promotion are required before any client/prospect send. No email, CRM write, upload, outreach, or publication occurred.\n'''
    (d/'runlog.md').write_text(runlog,encoding='utf-8')
    readme=f'''# Vintage Optical canonical GROW packet\n\nStatus: internal-only, unroomed, not for external use.\n\n- `onepager.pdf`: corrected canonical one-page PDF\n- `onepager.html`: editable source built from the approved repo template\n- `scores.json`: discrete-band score stack and Fix Cards\n- `data/`: source registry, evidence, peer tiers, routes, market inputs, and notes\n- `runlog.md`: process and QA receipt\n\nThe 2026-07-29 one-pager is superseded because it did not run the canonical discrete-band, positioning, and Fix Card workflow.\n'''
    (d/'README.md').write_text(readme,encoding='utf-8')
    result={'dest':str(d),'pdf_sha256':sha(d/'onepager.pdf'),'pdf_bytes':(d/'onepager.pdf').stat().st_size}
    Path(a.receipt).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
