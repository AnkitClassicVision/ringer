#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import re
import struct
import subprocess
import sys


def why(msg: str) -> None:
    print(f"WHY: {msg}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()
    dest = Path(args.dest)
    pdf, png, text, log = dest/"onepager.pdf", dest/"onepager-qa.png", dest/"data/onepager-text.txt", dest/"runlog.md"
    failures=[]
    for p, floor in [(pdf, 20000), (png, 20000), (text, 1000), (log, 500)]:
        if not p.is_file() or p.stat().st_size < floor: failures.append(f"missing or small artifact: {p}")
    if failures:
        for f in failures: why(f)
        return 1
    info=subprocess.run(["pdfinfo",str(pdf)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if info.returncode: failures.append("pdfinfo failed: "+info.stdout.strip())
    if not re.search(r"(?m)^Pages:\s+1\s*$",info.stdout): failures.append("PDF is not exactly one page")
    if not re.search(r"(?m)^Page size:\s+612 x 792 pts",info.stdout): failures.append("PDF is not US Letter")
    body=text.read_text(encoding="utf-8",errors="replace")
    for phrase in ["The Read","Your Market","Your Competition","Your Opportunity","First 30 Days","Room to Win","Confidence C","Public data only","H1","H2","H3"]:
        if phrase.lower() not in body.lower(): failures.append(f"extracted PDF text missing: {phrase}")
    for bad in ["\ufffd","Lorem ipsum","undefined","Competitive Pressure Index"]:
        if bad.lower() in body.lower(): failures.append(f"extracted PDF text contains forbidden literal: {bad}")
    urls=subprocess.run(["pdfinfo","-url",str(pdf)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    urlset=set(re.findall(r"https?://\S+",urls.stdout))
    if len(urlset)<12: failures.append(f"PDF has only {len(urlset)} unique HTTP links; need at least 12")
    if "file://" in urls.stdout: failures.append("PDF contains a local file link")
    raw=png.read_bytes()[:24]
    if raw[:8]!=b"\x89PNG\r\n\x1a\n": failures.append("QA image is not PNG")
    else:
        w,h=struct.unpack(">II",raw[16:24])
        if w<1200 or h<1500: failures.append(f"QA image dimensions too small: {w}x{h}")
    logtext=log.read_text(encoding="utf-8",errors="replace")
    for phrase in ["RINGER-RENDER-RECEIPT:START","Render status: PASS","External delivery: none"]:
        if phrase not in logtext: failures.append(f"runlog missing render receipt phrase: {phrase}")
    if failures:
        for f in failures: why(f)
        return 1
    print(f"PASS: one-page Letter PDF valid; {pdf.stat().st_size} bytes, {len(body)} text chars, {len(urlset)} unique links")
    return 0


if __name__=="__main__":
    sys.exit(main())
