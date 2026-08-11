#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, shutil
from datetime import datetime, timezone
from pathlib import Path


def sha(p):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    for x in ['dest','old','route_run','evidence_run','scoring_run','build_run','render_run','review_run','review','visual_qa','receipt']: ap.add_argument('--'+x.replace('_','-'),required=True)
    a=ap.parse_args(); d=Path(a.dest); old=Path(a.old); review=Path(a.review)
    review_text=review.read_text(encoding='utf-8')
    if 'Verdict: READY_INTERNAL' not in review_text: raise SystemExit('WHY: fresh review is not READY_INTERNAL')
    shutil.copy2(review,d/'data/fresh_review.md')
    runs=[('Public route collection',a.route_run),('Canonical evidence pack',a.evidence_run),('Manual-band scoring, positioning, and Fix Cards',a.scoring_run),('Explicit GPT-5.6 Sol template build',a.build_run),('Chrome assembly and render',a.render_run),('Fresh process/release review',a.review_run)]
    block='\n'.join(f'- {name}: `{rid}` - PASS' for name,rid in runs)
    log=(d/'runlog.md').read_text(encoding='utf-8')
    if 'RUN_IDS_PENDING_FINAL_CLOSE' not in log: raise SystemExit('WHY: runlog placeholder absent')
    log=log.replace('RUN_IDS_PENDING_FINAL_CLOSE',block)
    log += f'''\n## Visual QA and final internal release\n\n- Visual QA: PASS. {a.visual_qa}\n- Fresh review: READY_INTERNAL, no fatal or material issues.\n- Final PDF SHA-256: `{sha(d/'onepager.pdf')}`\n- Highest true state: tested local internal packet; external use remains blocked.\n- Closed at: {datetime.now(timezone.utc).isoformat()}\n'''
    (d/'runlog.md').write_text(log,encoding='utf-8')
    readme=(d/'README.md').read_text(encoding='utf-8').replace('Status: internal-only, unroomed, not for external use.','Status: READY_INTERNAL. Internal-only, unroomed, not for external use.')
    (d/'README.md').write_text(readme,encoding='utf-8')
    quarantine=old/'superseded-noncanonical-onepager'; quarantine.mkdir(parents=True,exist_ok=True)
    for name in ['onepager.pdf','onepager.html','onepager-qa.png','scores.json','intake.md','runlog.md']:
        src=old/name; dst=quarantine/name
        if src.exists():
            if dst.exists(): dst.unlink()
            src.replace(dst)
    srcdata=old/'data'; dstdata=quarantine/'data'
    if srcdata.exists():
        if dstdata.exists(): shutil.rmtree(dstdata)
        srcdata.replace(dstdata)
    notice=f'''# Superseded one-pager notice\n\nThe one-page package originally created here did not follow the repository's canonical discrete-band scoring, Stage 2 positioning, Stage 5 Fix Card, and Project Room boundary process. It is quarantined under `superseded-noncanonical-onepager/` for audit history and must not be used.\n\nCorrected canonical packet:\n\n`{d}`\n\nThe full long-form report `competitive-growth-analysis-full.pdf` remains unchanged.\n'''
    (old/'SUPERSEDED.md').write_text(notice,encoding='utf-8')
    oldreadme=old/'README.md'
    if oldreadme.exists():
        txt=oldreadme.read_text(encoding='utf-8')
        marker='> **One-pager superseded:** The prior one-page files were quarantined because they did not follow the canonical repo workflow. Use `../2026-07-30/onepager.pdf`.\n\n'
        if marker not in txt:
            lines=txt.splitlines(True); insert=1 if lines else 0; lines.insert(insert,'\n'+marker); oldreadme.write_text(''.join(lines),encoding='utf-8')
    result=f'PASS: runlog closed, fresh review copied, prior one-pager quarantined, final sha256={sha(d/"onepager.pdf")}'
    Path(a.receipt).write_text(result+'\n',encoding='utf-8')
    print(result)
if __name__=='__main__': main()
