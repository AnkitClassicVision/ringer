#!/usr/bin/env python3
"""Offline validator for the production-derived goal-loop graph."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source-v93-pathway.json"
SPEC = HERE / "source-v94-spec.md"
KEEP = set("n_identity n_appt_check e_defer n_help n_office n_faq n_gate_1 n_gate_2 n_verify_1 n_verify_2 n_book_1 n_book_2 n_reconcile_1 n_reconcile_2 e_booked e_booking_failed e_book_unknown e_booked_recovered e_declined e_timeout e_stop e_not_me n_suppress_stop n_suppress_not_me n_date_conflict n_date_conflict_retry e_safe_identity e_safe_failure e_office e_existing".split())
NEW = {"n_goal_search", "n_goal_search_latest", "n_goal_search_anchor", "n_goal_search_offered_latest", "n_goal_search_offered_time", "n_goal_response", "n_confirm_1", "n_confirm_2"}
SEARCH_INPUTS = {"user_verbatim", "preference_from", "preference_to", "day_part", "time_after"}
BODY_EXCLUSIONS = {"callID", "lastUserMessage", "store", "slot_1_start"}
AVAILABILITY_FIELDS = {"store", "from", "to", "after", "before", "time_pref", "slot_minutes", "callID", "user_text", "user_verbatim"}
SEARCH_NODES = {"n_goal_search", "n_goal_search_latest", "n_goal_search_anchor", "n_goal_search_offered_latest", "n_goal_search_offered_time"}
FEEDERS = {"n_goal_response", "n_date_conflict", "n_date_conflict_retry", "n_gate_1", "n_gate_2"}
FROZEN_EXTRACTORS = HERE / "fixture-v96-n-ask-extractors.json"
BANNED = re.compile(r"one moment|let me check|checking availability|please hold|give me a (?:moment|second)", re.I)
CLOCK = re.compile(r"\b\d{1,2}:\d{2}\s*[ap]m\b", re.I)
PROMISE_SENTENCE = ("If the lookup has not returned in this turn, or the patient is nudging after a silence, "
                    "never state or estimate any date or time from memory or from the patient's words; say "
                    "'One moment while I check the schedule for you.' and run the schedule search. ")
NO_SLOT_SENTENCE = ("If the lookup has not returned in this turn, never state or estimate any date or time "
                    "from memory or from the patient's words. ")
OFFER_TEMPLATE = ("I have {{slot_1_day_name}} {{slot_1_start}} or "
                  "{{slot_2_day_name}} {{slot_2_start}} at MK2 Optical. "
                  "Reply 1 or 2 to take one, or tell me another day or time.")

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
        if not ok: errors.append("assertion 1: "+msg)
    try: g=json.loads(Path(a.draft).read_text())
    except Exception as e: print(f"FAIL: assertion 1: invalid JSON: {e}"); return 1
    src=json.loads(SOURCE.read_text()); spec=SPEC.read_text(); old={n["id"]:n for n in src["nodes"]}
    nodes=g.get("nodes",[]); edges=g.get("edges",[]); by={n.get("id"):n for n in nodes}; ids=set(by)
    ck("## 9. VALIDATOR PLAN" in spec,"authoritative spec validator plan missing")
    ck(ids == KEEP|NEW, f"node topology differs: missing={sorted((KEEP|NEW)-ids)} extra={sorted(ids-(KEEP|NEW))}")
    ck(len(nodes)==len(ids),"duplicate node id")
    extraction_sources={"n_date_conflict","n_date_conflict_retry","n_gate_1","n_gate_2"}
    scrubbed={"n_gate_1","n_gate_2","n_book_1","n_book_2","n_help","n_office","n_faq"}|extraction_sources
    for nid in KEEP - {"n_appt_check"} - scrubbed: ck(by.get(nid)==old.get(nid),f"kept-verbatim node changed: {nid}")
    for nid in scrubbed:
        expected=json.loads(json.dumps(old[nid]))
        if isinstance(expected["data"].get("prompt"),str):
            expected["data"]["prompt"]=expected["data"]["prompt"].replace(PROMISE_SENTENCE,NO_SLOT_SENTENCE)
        if nid in {"n_gate_1","n_gate_2"}:
            index=int(nid[-1])
            expected["data"]["prompt"]=expected["data"]["prompt"].replace(
                f"{{{{slot_{index}_start}}}}",f"{{{{slot_{index}_day_name}}}} {{{{slot_{index}_start}}}}")
        if nid in {"n_book_1","n_book_2"}:
            index=int(nid[-1])
            for pathway in expected["data"].get("responsePathways",[]):
                if pathway[:3] == ["book_success","==","true"]:
                    pathway[3]["id"] = f"n_confirm_{index}"
        if nid in extraction_sources and FROZEN_EXTRACTORS.exists():
            expected["data"]["extractVars"]=json.loads(FROZEN_EXTRACTORS.read_text())
        ck(by.get(nid)==expected,f"{nid} differs beyond required promise removal/date pairing")
    ap=by["n_appt_check"]["data"]
    ck(ap.get("text")=="" and ap.get("modelOptions")==old["n_appt_check"]["data"]["modelOptions"],
       "n_appt_check no longer follows v92 silent auto-advance convention")
    ck(ap.get("responsePathways")==[
        ["appt_count", ">=", "1", {"id":"e_defer","name":"Upcoming appointment found"}],
        ["appt_count", "==", "0", {"id":"n_goal_response","name":"No upcoming appointment"}],
        ["ok", "!=", "true", {"id":"e_defer","name":"Appointment check unavailable"}],
    ], "n_appt_check entry/deferral pathways do not match the derived v92 convention")
    for e in edges:
        ck(e.get("source") in ids and e.get("target") in ids,f"edge {e.get('id')}: unresolved endpoint")
        ck(e.get("source") != e.get("target"),f"edge {e.get('id')}: self-loop/fail-stay")
    out={i:[] for i in ids}
    for e in edges: out.setdefault(e.get("source"),[]).append(e.get("target"))
    for s,t in ((sid,"n_goal_response") for sid in SEARCH_NODES):
        ck(t in out.get(s,[]),f"loop adjacency missing: {s} -> {t}")
    for t in SEARCH_NODES:
        ck(t in out.get("n_goal_response",[]),f"loop adjacency missing: n_goal_response -> {t}")
    # No mid-negotiation terminal: the only allowed patient-facing terminal routes
    # are the production response's explicit decline and timeout routes.
    terminals={n["id"] for n in nodes if n.get("type")=="End Call"}
    allowed_terminal_sources={"n_identity","n_appt_check","n_confirm_1","n_confirm_2","n_office","n_suppress_stop","n_suppress_not_me","n_reconcile_1","n_reconcile_2","n_goal_response","n_gate_1","n_gate_2","n_verify_1","n_verify_2"}
    for e in edges:
        if e.get("target") in terminals: ck(e.get("source") in allowed_terminal_sources,f"edge {e.get('id')}: mid-negotiation terminal")
    # Semantic promise gate applies to newly authored/derived behavior. Locked
    # source nodes are covered by byte identity and are not rewritten here.
    for nid in ids:
        prompt=str(by[nid].get("data",{}).get("prompt","")); m=BANNED.search(prompt)
        ck(not m,f"node {nid}: banned promise {m.group(0)!r}" if m else f"node {nid}: promise clean")
    # Clock containment: only the offer response may contain renderable clock
    # placeholders. Extraction examples are internal and do not render.
    for nid,n in by.items():
        data=n.get("data",{}); visible="\n".join(str(data.get(k,"")) for k in ("prompt","text"))
        if CLOCK.search(visible) and nid not in KEEP:
            ck(nid=="n_goal_response",f"node {nid}: clock time outside respond/offer")
    expected_extractors={"n_goal_response","n_date_conflict","n_date_conflict_retry","n_gate_1","n_gate_2"}
    extract_nodes={nid for nid,n in by.items() if n.get("data",{}).get("extractVars")}
    ck(expected_extractors <= extract_nodes,f"distributed extraction missing: {sorted(expected_extractors-extract_nodes)}")
    for nid in expected_extractors & ids:
        ext={x[0] for x in by[nid].get("data",{}).get("extractVars",[]) if isinstance(x,list) and x}
        ck(SEARCH_INPUTS <= ext,f"{nid} missing extraction fields {sorted(SEARCH_INPUTS-ext)}")
    sd=by.get("n_goal_search",{}).get("data",{})
    for search_id in SEARCH_NODES:
        search_data=by.get(search_id,{}).get("data",{})
        ck(search_data.get("url")==old["n_search"]["data"]["url"],f"{search_id} endpoint differs from production")
        ck(search_data.get("modelOptions")==old["n_search"]["data"]["modelOptions"],f"{search_id} runtime options differ")
        ck(search_data.get("responseData")==old["n_search"]["data"]["responseData"],
           f"{search_id} responseData is not a verbatim copy of working n_search")
    for nid in (*SEARCH_NODES,"n_identity","n_reconcile_1","n_reconcile_2","n_suppress_stop","n_suppress_not_me"):
        if nid not in by: continue
        paths=by[nid].get("data",{}).get("responsePathways",[]) or []
        labels={(e.get("data",{}).get("label"),e.get("target")) for e in edges if e.get("source")==nid}
        for p in paths:
            if isinstance(p,list) and len(p)>=4 and isinstance(p[3],dict):
                ck((f"{p[0]} {p[1]} {p[2]}",p[3].get("id")) in labels,f"{nid}: responsePathway lacks executable condition edge {p[:3]}")
    # [20] Placeholder producer gate, ported from check_v91_graph.py and extended
    # to every renderable prompt/text as well as webhook bodies.
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
    # Respond-layer wiring: the exact protected copy must be rendered from the
    # producer owned by n_goal_search, never reconstructed generatively.
    rp=by["n_goal_response"]["data"].get("prompt","")
    ck(OFFER_TEMPLATE in rp,"n_goal_response missing exact protected offer template")
    response_names={x.get("name") for x in sd.get("responseData",[]) if isinstance(x,dict)}
    offer_vars=set(re.findall(r"{{\s*(slot_[12]_(?:start|day_name))\s*}}",OFFER_TEMPLATE))
    ck(offer_vars <= response_names,
       "n_goal_response offer placeholders lack n_goal_search responseData producers: "+str(sorted(offer_vars-response_names)))
    ck(by["n_goal_response"]["data"].get("userWait") is True,
       "n_goal_response must use n_offer single-response/userWait convention")
    ck("MM/DD/YYYY" in rp and "exactly one patient-facing message per turn" in rp,
       "n_goal_response missing date-format or single-message render discipline")

    # ASSERTION #6: Bland CHAT mode only runs extraction on the current user-wait
    # Default. Slot-producing webhooks therefore accept direct edges solely from
    # another Webhook or from a complete extraction-owning user-wait Default.
    a6=[]
    if "n_goal_update" in ids:
        a6.append("n_goal_update must be absent")
    slot_webhooks=set()
    for nid,n in by.items():
        if n.get("type")=="Webhook" and any(re.match(r"slot_[0-9]+_",str(x.get("name",""))) for x in n.get("data",{}).get("responseData",[]) if isinstance(x,dict)):
            slot_webhooks.add(nid)
    for e in edges:
        if e.get("target") not in slot_webhooks: continue
        source_id=e.get("source"); source=by.get(source_id,{})
        if source.get("type")=="Webhook": continue
        data=source.get("data",{})
        if source.get("type")!="Default" or data.get("userWait") is not True:
            a6.append(f"edge {source_id} -> {e.get('target')} originates from a Default with userWait false or a non-permitted type")
            continue
        target_data=by[e["target"]].get("data",{})
        body_vars=set(re.findall(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}",str(target_data.get("body",""))))-BODY_EXCLUSIONS
        ext={x[0] for x in data.get("extractVars",[]) if isinstance(x,list) and x}
        missing=body_vars-ext
        if missing:
            a6.append(f"edge {source_id} -> {e.get('target')} source extractVars missing {sorted(missing)}")
    if a6:
        errors.extend("assertion 6: "+message for message in a6)
        checks += len(a6)
    else:
        checks += 1

    # ASSERTION #7: round-7 semantic routing, gateway body contract, and the
    # frozen production extraction contract.
    a7=[]
    availability=[]
    for nid,node in by.items():
        data=node.get("data",{})
        if node.get("type")=="Webhook" and str(data.get("url","")).endswith("/availability"):
            availability.append(nid)
            try:
                parsed=json.loads(data.get("body",""))
            except Exception as exc:
                a7.append(f"{nid} availability body is invalid JSON: {exc}")
                continue
            if set(parsed) != AVAILABILITY_FIELDS:
                a7.append(f"{nid} availability body fields differ: missing={sorted(AVAILABILITY_FIELDS-set(parsed))} extra={sorted(set(parsed)-AVAILABILITY_FIELDS)}")
            if parsed.get("time_pref") not in {"none","latest","anchor={{goal_anchor}}"}:
                a7.append(f"{nid} invalid time_pref {parsed.get('time_pref')!r}")
    if set(availability) != SEARCH_NODES:
        a7.append(f"availability webhook set differs: expected={sorted(SEARCH_NODES)} actual={sorted(availability)}")
    expected_pref={"n_goal_search":"none","n_goal_search_latest":"latest","n_goal_search_anchor":"anchor={{goal_anchor}}","n_goal_search_offered_latest":"latest","n_goal_search_offered_time":"none"}
    for nid,want in expected_pref.items():
        try:
            actual=json.loads(by[nid]["data"]["body"]).get("time_pref")
        except Exception:
            continue
        if actual != want:
            a7.append(f"{nid} time_pref is {actual!r}, expected {want!r}")
    for nid,node in by.items():
        for extractor in node.get("data",{}).get("extractVars",[]) or []:
            if "retain" in flat(extractor).lower():
                a7.append(f"{nid} extractor contains retain")
    required_label=("says any day, weekday, date, week, weekend, or time preference - including Saturday, "
                    "this weekend, next week, or a month and day - or asks for the first available, soonest, "
                    "earliest, or whenever opening - or asks for a different day than offered")
    response_routes={(e.get("target"),e.get("data",{}).get("label")) for e in edges if e.get("source")=="n_goal_response"}
    if ("n_goal_search",required_label) not in response_routes:
        a7.append("n_goal_response none-search edge lacks the required day/weekday/weekend/time-preference enumeration")
    for target in SEARCH_NODES:
        if not any(t==target for t,_ in response_routes):
            a7.append(f"n_goal_response lacks edge to {target}")
    try:
        frozen=json.loads(FROZEN_EXTRACTORS.read_text(encoding="utf-8"))
    except Exception as exc:
        frozen=None
        a7.append(f"frozen v96 extractor fixture unavailable: {exc}")
    if frozen is not None:
        for nid in FEEDERS:
            actual=by.get(nid,{}).get("data",{}).get("extractVars",[])
            if nid=="n_goal_response":
                if actual[:5] != frozen or len(actual) != 6:
                    a7.append(f"{nid} first five extractors are not byte-equal to frozen v96 set plus one goal_anchor")
                elif actual[5][0:2] != ["goal_anchor","string"] or "retain" in flat(actual[5]).lower():
                    a7.append("n_goal_response goal_anchor extractor contract differs")
            elif actual != frozen:
                a7.append(f"{nid} extractors are not byte-equal to frozen v96 set")
    if a7:
        errors.extend("assertion 7: "+message for message in a7)
        checks += len(a7)
    else:
        checks += 1

    # ASSERTION #8: round-8 offered-date preservation, clock-time gate routing,
    # and branch-pinned template-verbatim booking confirmation.
    a8=[]
    offered_specs={
        "n_goal_search_offered_latest": "latest",
        "n_goal_search_offered_time": "none",
    }
    for nid,want_pref in offered_specs.items():
        node=by.get(nid)
        if node is None:
            a8.append(f"{nid} is absent")
            continue
        try:
            body=json.loads(node.get("data",{}).get("body",""))
        except Exception as exc:
            a8.append(f"{nid} body is invalid JSON: {exc}")
            continue
        if body.get("from") != "{{slot_1_start}}" or body.get("to") != "{{slot_1_start}}":
            a8.append(f"{nid} must pin from and to to {{{{slot_1_start}}}}")
        if body.get("time_pref") != want_pref:
            a8.append(f"{nid} time_pref is {body.get('time_pref')!r}, expected {want_pref!r}")
        if set(body) != AVAILABILITY_FIELDS:
            a8.append(f"{nid} does not use the ten-field gateway contract")
        if body.get("after") != "{{time_after}}":
            a8.append(f"{nid} after must remain {{{{time_after}}}}")
        clone_source=by.get("n_goal_search",{}).get("data",{})
        for field in ("url","method","headers","responseData","responsePathways","modelOptions","active","text"):
            if node.get("data",{}).get(field) != clone_source.get(field):
                a8.append(f"{nid} cloned {field} differs from n_goal_search")

    goal_edges=[e for e in edges if e.get("source")=="n_goal_response"]
    edge_labels={(e.get("target"),e.get("data",{}).get("label")) for e in goal_edges}
    offered_routes={
        ("n_goal_search_offered_latest", "wants late, latest, last appointment, or end of day on the offered date"),
        ("n_goal_search_offered_time", "gives only a time preference on the already offered date, excluding late, latest, last appointment, or end of day"),
        ("n_goal_search_latest", "wants late, latest, last appointment, or end of day on a NAMED day different from the offered date"),
    }
    for route in offered_routes:
        if route not in edge_labels:
            a8.append(f"n_goal_response lacks exact offered-date route {route[0]}: {route[1]}")
    for gate_id in ("n_gate_1","n_gate_2"):
        labels=[e.get("data",{}).get("label","") for e in goal_edges if e.get("target")==gate_id]
        if len(labels) != 1 or "including by naming that opening's clock time" not in labels[0]:
            a8.append(f"{gate_id} edge lacks the clock-time clause")

    if "n_confirm" in ids:
        a8.append("n_confirm must be absent")
    for index in (1,2):
        confirm_id=f"n_confirm_{index}"
        confirm=by.get(confirm_id)
        if confirm is None:
            a8.append(f"{confirm_id} is absent")
            continue
        prompt=confirm.get("data",{}).get("prompt","")
        own_day=f"{{{{slot_{index}_day_name}}}}"
        own_start=f"{{{{slot_{index}_start}}}}"
        other=2 if index==1 else 1
        if confirm.get("type") != "Default":
            a8.append(f"{confirm_id} is not a Default node")
        if "TEMPLATE-VERBATIM" not in prompt or own_day not in prompt or own_start not in prompt:
            a8.append(f"{confirm_id} lacks its template-verbatim slot_{index} day/time copy")
        if f"{{{{slot_{other}_day_name}}}}" in prompt or f"{{{{slot_{other}_start}}}}" in prompt:
            a8.append(f"{confirm_id} references the other booked branch's slot")
        book_id=f"n_book_{index}"
        success=[p for p in by.get(book_id,{}).get("data",{}).get("responsePathways",[]) if p[:3]==["book_success","==","true"]]
        if len(success) != 1 or success[0][3].get("id") != confirm_id:
            a8.append(f"{book_id} success responsePathway does not target {confirm_id}")
        success_edges=[e for e in edges if e.get("source")==book_id and e.get("data",{}).get("label")=="book_success == true"]
        if len(success_edges) != 1 or success_edges[0].get("target") != confirm_id:
            a8.append(f"{book_id} success edge does not target {confirm_id}")
        if not any(e.get("source")==confirm_id and e.get("target")=="e_booked" for e in edges):
            a8.append(f"e_booked is unreachable from {confirm_id}")
    if a8:
        errors.extend("assertion 8: "+message for message in a8)
        checks += len(a8)
    else:
        checks += 1
    # [33] A rendered slot time is unsafe without the date-bearing day-name pair.
    unpaired=[]
    for nid,n in by.items():
        for field in ("prompt","text"):
            value=n.get("data",{}).get(field)
            if not isinstance(value,str): continue
            for index in (1,2):
                if f"{{{{slot_{index}_start}}}}" in value and f"{{{{slot_{index}_day_name}}}}" not in value:
                    unpaired.append((nid,field,index))
    ck(not unpaired,"[33] slot_N_start appears without slot_N_day_name: "+str(unpaired))
    if errors:
        for x in errors: print("FAIL:",x)
        print(f"FAIL: {len(errors)} of {checks} assertions failed"); return 1
    print(f"PASS: {checks} assertions")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"FAIL: assertion 1: validator could not complete: {exc}")
        raise SystemExit(1)
