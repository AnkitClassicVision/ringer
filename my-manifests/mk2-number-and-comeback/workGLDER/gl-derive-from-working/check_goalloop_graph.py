#!/usr/bin/env python3
"""Offline validator for the production-derived goal-loop graph."""
import argparse
import json
import re
import sys
from pathlib import Path

SOURCE = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workV93/build-v93/pathway-v93-draft.json")
SPEC = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workV94d4/amend-reference-point/SPEC-v94-draft4.md")
KEEP = set("n_identity n_appt_check e_defer n_help n_office n_faq n_gate_1 n_gate_2 n_confirm n_verify_1 n_verify_2 n_book_1 n_book_2 n_reconcile_1 n_reconcile_2 e_booked e_booking_failed e_book_unknown e_booked_recovered e_declined e_timeout e_stop e_not_me n_suppress_stop n_suppress_not_me n_date_conflict n_date_conflict_retry e_safe_identity e_safe_failure e_office e_existing".split())
NEW = {"n_goal_update", "n_goal_search", "n_goal_response"}
BANNED = re.compile(r"one moment|let me check|checking availability|please hold|give me a (?:moment|second)", re.I)
CLOCK = re.compile(r"\b\d{1,2}:\d{2}\s*[ap]m\b", re.I)

def flat(x):
    if isinstance(x, str): return x
    if isinstance(x, dict): return "\n".join(flat(v) for v in x.values())
    if isinstance(x, list): return "\n".join(flat(v) for v in x)
    return ""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--draft", required=True); a = ap.parse_args()
    errors=[]; checks=0
    def ck(ok,msg):
        nonlocal checks; checks += 1
        if not ok: errors.append(msg)
    try: g=json.loads(Path(a.draft).read_text())
    except Exception as e: print(f"FAIL: invalid JSON: {e}"); return 1
    src=json.loads(SOURCE.read_text()); spec=SPEC.read_text(); old={n["id"]:n for n in src["nodes"]}
    nodes=g.get("nodes",[]); edges=g.get("edges",[]); by={n.get("id"):n for n in nodes}; ids=set(by)
    ck("## 9. VALIDATOR PLAN" in spec,"authoritative spec validator plan missing")
    ck(ids == KEEP|NEW, f"node topology differs: missing={sorted((KEEP|NEW)-ids)} extra={sorted(ids-(KEEP|NEW))}")
    ck(len(nodes)==len(ids),"duplicate node id")
    for nid in KEEP: ck(by.get(nid)==old.get(nid),f"kept-verbatim node changed: {nid}")
    for e in edges:
        ck(e.get("source") in ids and e.get("target") in ids,f"edge {e.get('id')}: unresolved endpoint")
        ck(e.get("source") != e.get("target"),f"edge {e.get('id')}: self-loop/fail-stay")
    out={i:[] for i in ids}
    for e in edges: out.setdefault(e.get("source"),[]).append(e.get("target"))
    for s,t in (("n_goal_update","n_goal_search"),("n_goal_search","n_goal_response"),("n_goal_response","n_goal_update")):
        ck(t in out.get(s,[]),f"loop adjacency missing: {s} -> {t}")
    # No mid-negotiation terminal: the only allowed patient-facing terminal routes
    # are the production response's explicit decline and timeout routes.
    terminals={n["id"] for n in nodes if n.get("type")=="End Call"}
    allowed_terminal_sources={"n_identity","n_appt_check","n_confirm","n_office","n_suppress_stop","n_suppress_not_me","n_reconcile_1","n_reconcile_2","n_goal_response","n_gate_1","n_gate_2","n_verify_1","n_verify_2"}
    for e in edges:
        if e.get("target") in terminals: ck(e.get("source") in allowed_terminal_sources,f"edge {e.get('id')}: mid-negotiation terminal")
    # Semantic promise gate applies to newly authored/derived behavior. Locked
    # source nodes are covered by byte identity and are not rewritten here.
    for nid in NEW:
        prompt=str(by[nid].get("data",{}).get("prompt","")); m=BANNED.search(prompt)
        ck(not m,f"node {nid}: banned promise {m.group(0)!r}" if m else f"node {nid}: promise clean")
    # Clock containment: only the offer response may contain renderable clock
    # placeholders. Extraction examples are internal and do not render.
    for nid,n in by.items():
        data=n.get("data",{}); visible="\n".join(str(data.get(k,"")) for k in ("prompt","text"))
        if CLOCK.search(visible) and nid not in KEEP:
            ck(nid=="n_goal_response",f"node {nid}: clock time outside respond/offer")
    # D6's two byte-locked clarification nodes retain their narrow local date
    # extractors. The only full scheduling-goal extraction config is UPDATE.
    extract_nodes=[nid for nid,n in by.items() if n.get("data",{}).get("extractVars") and nid not in {"n_date_conflict","n_date_conflict_retry"}]
    ck(extract_nodes==["n_goal_update"],f"single extraction violated: {extract_nodes}")
    ud=by["n_goal_update"]["data"]
    ck(ud.get("text")=="" and ud.get("userWait") is False,"n_goal_update is not silent")
    ck(ud.get("modelOptions")==old["n_appt_check"]["data"]["modelOptions"],"n_goal_update silent modelOptions not copied exactly")
    ext={x[0] for x in ud.get("extractVars",[]) if isinstance(x,list) and x}
    for name in ("user_verbatim","preference_from","preference_to","day_part","time_after","goal_anchor","goal_relation","time_from","time_to"):
        ck(name in ext,f"n_goal_update missing extraction field {name}")
    sd=by["n_goal_search"]["data"]
    ck(sd.get("url")==old["n_search"]["data"]["url"],"n_goal_search endpoint differs from production")
    ck(sd.get("modelOptions")==old["n_search"]["data"]["modelOptions"],"n_goal_search runtime options differ")
    body=sd.get("body","")
    for name in ("time_pref","goal_relation","anchor","goal_anchor","time_from","time_to"):
        ck(name in body,f"n_goal_search body missing {name}")
    for nid in ("n_goal_update","n_goal_search","n_identity","n_reconcile_1","n_reconcile_2","n_suppress_stop","n_suppress_not_me"):
        paths=by[nid].get("data",{}).get("responsePathways",[]) or []
        labels={(e.get("data",{}).get("label"),e.get("target")) for e in edges if e.get("source")==nid}
        for p in paths:
            if isinstance(p,list) and len(p)>=4 and isinstance(p[3],dict):
                ck((f"{p[0]} {p[1]} {p[2]}",p[3].get("id")) in labels,f"{nid}: responsePathway lacks executable condition edge {p[:3]}")
    # Placeholder producer gate, using production webhook outputs plus extraction.
    produced={"recall_cell","recall_patient_id","store","campaign","callID","lastUserMessage","patient_first","patient_id","exam_type_id"}
    for n in nodes:
        d=n.get("data",{})
        produced.update(x[0] for x in d.get("extractVars",[]) or [] if isinstance(x,list) and x)
        produced.update(x.get("name") for x in d.get("responseData",[]) or [] if isinstance(x,dict) and x.get("name"))
    unresolved=[]
    for nid,n in by.items():
        for field in ("prompt","text","body"):
            v=n.get("data",{}).get(field)
            if isinstance(v,str):
                for var in re.findall(r"{{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*}}",v):
                    if var.split('.',1)[0] not in produced and not var.startswith("SECRET."): unresolved.append((nid,field,var))
    ck(not unresolved,"placeholder producers: "+", ".join(f"{n}.{f} {{{{{v}}}}}" for n,f,v in unresolved))
    if errors:
        for x in errors: print("FAIL:",x)
        print(f"FAIL: {len(errors)} of {checks} assertions failed"); return 1
    print(f"PASS: {checks} assertions")
    return 0

if __name__=="__main__": raise SystemExit(main())
