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
KEEP = set("n_identity n_appt_check n_help n_office n_faq n_gate_1 n_gate_2 n_verify_1 n_verify_2 n_book_1 n_book_2 n_reconcile_1 n_reconcile_2 e_booked e_booking_failed e_book_unknown e_booked_recovered e_declined e_timeout e_stop e_not_me n_suppress_stop n_suppress_not_me n_date_conflict n_date_conflict_retry e_safe_identity e_safe_failure e_office e_existing".split())
NEW = {"n_goal_ask", "n_goal_search", "n_goal_search_latest", "n_goal_search_anchor", "n_goal_search_offered_latest", "n_goal_search_offered_time", "n_goal_response", "n_mixed_intent", "n_confirm_1", "n_confirm_2", "n_post_booking"}
SEARCH_INPUTS = {"user_verbatim", "preference_from", "preference_to", "day_part", "time_after"}
BODY_EXCLUSIONS = {"callID", "lastUserMessage", "store", "slot_1_start"}
AVAILABILITY_FIELDS = {"store", "from", "to", "after", "before", "time_pref", "slot_minutes", "callID", "user_text", "user_verbatim"}
SEARCH_NODES = {"n_goal_search", "n_goal_search_latest", "n_goal_search_anchor", "n_goal_search_offered_latest", "n_goal_search_offered_time"}
FEEDERS = {"n_goal_ask", "n_goal_response", "n_mixed_intent", "n_date_conflict", "n_date_conflict_retry", "n_gate_1", "n_gate_2"}
FROZEN_EXTRACTORS = HERE / "frozen-extractors.json"
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
        ["appt_count", ">=", "1", {"id":"n_post_booking","name":"Upcoming appointment found"}],
        ["appt_count", "==", "0", {"id":"n_goal_ask","name":"No upcoming appointment"}],
        ["ok", "!=", "true", {"id":"n_post_booking","name":"Appointment check unavailable"}],
    ], "n_appt_check entry/deferral pathways do not match the derived v92 convention")
    for e in edges:
        ck(e.get("source") in ids and e.get("target") in ids,f"edge {e.get('id')}: unresolved endpoint")
        ck(e.get("source") != e.get("target"),f"edge {e.get('id')}: self-loop/fail-stay")
    out={i:[] for i in ids}
    for e in edges: out.setdefault(e.get("source"),[]).append(e.get("target"))
    for s,t in ((sid,"n_goal_response") for sid in SEARCH_NODES):
        ck(t in out.get(s,[]),f"loop adjacency missing: {s} -> {t}")
    for t in ("n_goal_search","n_goal_search_latest","n_goal_search_anchor"):
        ck(t in out.get("n_goal_ask",[]),f"loop adjacency missing: n_goal_ask -> {t}")
    for t in ("n_goal_search","n_goal_search_offered_latest","n_goal_search_offered_time"):
        ck(t in out.get("n_goal_response",[]),f"loop adjacency missing: n_goal_response -> {t}")
    # No mid-negotiation terminal: the only allowed patient-facing terminal routes
    # are the production response's explicit decline and timeout routes.
    terminals={n["id"] for n in nodes if n.get("type")=="End Call"}
    allowed_terminal_sources={"n_identity","n_appt_check","n_confirm_1","n_confirm_2","n_post_booking","n_office","n_suppress_stop","n_suppress_not_me","n_reconcile_1","n_reconcile_2","n_goal_ask","n_goal_response","n_mixed_intent","n_gate_1","n_gate_2","n_verify_1","n_verify_2"}
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
    expected_extractors={"n_goal_ask","n_goal_response","n_mixed_intent","n_date_conflict","n_date_conflict_retry","n_gate_1","n_gate_2"}
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
        expected_response=old["n_search"]["data"]["responseData"]+[
            {"data":"$.result.out_of_hours","name":"out_of_hours"},
            {"data":"$.result.requested_clock","name":"requested_clock"},
            {"data":"$.result.from_unresolved","name":"from_unresolved"},
        ]
        ck(search_data.get("responseData")==expected_response,
           f"{search_id} responseData differs beyond the required gateway mappings")
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
                    "earliest, or whenever opening - or asks for a different day than offered - or gives only a time preference when no date has been offered yet")
    ask_routes={(e.get("target"),e.get("data",{}).get("label")) for e in edges if e.get("source")=="n_goal_ask"}
    if not any(target=="n_goal_search" and required_label.replace(" - or asks for a different day than offered", "") in (label or "") for target,label in ask_routes):
        a7.append("n_goal_ask none-search edge lacks the required day/weekday/weekend/time-preference enumeration")
    for target in ("n_goal_search","n_goal_search_latest","n_goal_search_anchor"):
        if not any(t==target for t,_ in ask_routes):
            a7.append(f"n_goal_ask lacks edge to {target}")
    try:
        frozen=json.loads(FROZEN_EXTRACTORS.read_text(encoding="utf-8"))
    except Exception as exc:
        frozen=None
        a7.append(f"frozen v96 extractor fixture unavailable: {exc}")
    if frozen is not None:
        for nid in FEEDERS:
            actual=by.get(nid,{}).get("data",{}).get("extractVars",[])
            if nid in {"n_goal_ask","n_goal_response"}:
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
        ("n_goal_search_offered_time", "gives only a time preference on the already offered date, excluding late, latest, last appointment, or end of day - or asks for the earliest, soonest, or first available time on that date"),
    }
    for route in offered_routes:
        if not any(target==route[0] and (label or "").endswith(route[1]) for target,label in edge_labels):
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
        if not any(e.get("source")==confirm_id and e.get("target")=="n_post_booking" for e in edges):
            a8.append(f"n_post_booking is unreachable from {confirm_id}")
    if a8:
        errors.extend("assertion 8: "+message for message in a8)
        checks += len(a8)
    else:
        checks += 1

    # ASSERTION #9: round-9 shared extractor pin, whole-sentence availability
    # semantics, and hot-node prompt budget.
    a9=[]
    try:
        frozen9=json.loads(FROZEN_EXTRACTORS.read_text(encoding="utf-8"))
    except Exception as exc:
        frozen9=None
        a9.append(f"frozen extractor pin unavailable: {exc}")
    if frozen9 is not None:
        if not isinstance(frozen9,list) or len(frozen9) != 5:
            a9.append("frozen-extractors.json must contain exactly five extractors")
        for nid in FEEDERS:
            actual=by.get(nid,{}).get("data",{}).get("extractVars",[])
            shared=actual[:5] if nid in {"n_goal_ask","n_goal_response"} else actual
            if shared != frozen9:
                a9.append(f"{nid} five shared extractors are not byte-equal to frozen-extractors.json")
        descriptions={x[0]:x[2] for x in frozen9 if isinstance(x,list) and len(x)>=3}
        for name in ("preference_from","preference_to"):
            desc=descriptions.get(name,"").lower()
            required=("interpret the whole sentence", "leaving", "being away", "won't be back", "their return or availability date")
            missing=[phrase for phrase in required if phrase not in desc]
            if missing:
                a9.append(f"{name} availability-interpretation rule missing {missing}")
    prompt9=by.get("n_goal_response",{}).get("data",{}).get("prompt","")
    if not isinstance(prompt9,str) or len(prompt9) > 4100:
        a9.append(f"n_goal_response prompt length is {len(prompt9) if isinstance(prompt9,str) else 'non-string'}, maximum is 4100")
    if a9:
        errors.extend("assertion 9: "+message for message in a9)
        checks += len(a9)
    else:
        checks += 1

    # ASSERTION #10: round-10 mixed-intent consent gate, out-of-hours gateway
    # response contract, honest response policy, and pre-offer time-only route.
    a10=[]
    mixed=by.get("n_mixed_intent")
    if mixed is None:
        a10.append("n_mixed_intent is absent")
    else:
        if mixed.get("type") != "Default" or mixed.get("data",{}).get("userWait") is not True:
            a10.append("n_mixed_intent must be a user-wait Default")
        if frozen9 is not None and mixed.get("data",{}).get("extractVars") != frozen9:
            a10.append("n_mixed_intent extractors are not byte-equal to frozen-extractors.json")
    mixed_label="both selects an opening and asks for a different day or time"
    if not any(e.get("source")=="n_goal_response" and e.get("target")=="n_mixed_intent" and e.get("data",{}).get("label")==mixed_label for e in edges):
        a10.append("n_goal_response lacks the exact mixed-intent clarification edge")
    mixed_targets={e.get("target") for e in edges if e.get("source")=="n_mixed_intent"}
    for target in ("n_gate_1","n_gate_2","n_goal_search","e_declined","e_timeout"):
        if target not in mixed_targets:
            a10.append(f"n_mixed_intent lacks route to {target}")
    for nid in SEARCH_NODES:
        mappings={(x.get("name"),x.get("data")) for x in by.get(nid,{}).get("data",{}).get("responseData",[]) if isinstance(x,dict)}
        if ("out_of_hours","$.result.out_of_hours") not in mappings:
            a10.append(f"{nid} does not map out_of_hours")
        if ("requested_clock","$.result.requested_clock") not in mappings:
            a10.append(f"{nid} does not map requested_clock")
    lower_prompt=prompt9.lower()
    if not all(x in lower_prompt for x in ("out_of_hours is true","{{requested_clock}}","nearest real slots","never state or imply")):
        a10.append("n_goal_response prompt lacks the required out_of_hours honesty branch")
    if len(prompt9) > 4100:
        a10.append(f"n_goal_response prompt length is {len(prompt9)}, maximum is 4100")
    time_only="or gives only a time preference when no date has been offered yet"
    none_labels=[e.get("data",{}).get("label","") for e in edges if e.get("source")=="n_goal_ask" and e.get("target")=="n_goal_search"]
    if len(none_labels) != 1 or time_only not in none_labels[0]:
        a10.append("n_goal_ask none-search edge lacks pre-offer time-only routing")
    if a10:
        errors.extend("assertion 10: "+message for message in a10)
        checks += len(a10)
    else:
        checks += 1

    # ASSERTION #11: round-11 agreement-phrased pre-offer clock routing and
    # explicit standing-offer guards on both offered-date routes.
    a11=[]
    goal_labels={
        e.get("target"): e.get("data",{}).get("label","")
        for e in edges if e.get("source")=="n_goal_ask"
    }
    if "works for me" not in goal_labels.get("n_goal_search",""):
        a11.append("n_goal_ask none-search edge lacks the agreement-phrased 'works for me' example")
    response_labels={
        e.get("target"): e.get("data",{}).get("label","")
        for e in edges if e.get("source")=="n_goal_response"
    }
    offered_prefix="after an opening has been offered, "
    for target in ("n_goal_search_offered_time","n_goal_search_offered_latest"):
        if not response_labels.get(target,"").startswith(offered_prefix):
            a11.append(f"n_goal_response {target} edge does not begin with {offered_prefix!r}")
    if a11:
        errors.extend("assertion 11: "+message for message in a11)
        checks += len(a11)
    else:
        checks += 1

    # ASSERTION #13: round-13 anaphoric-week extraction, offer integrity, and
    # unresolved-from gateway contract.
    a13=[]
    for nid in FEEDERS:
        descriptions13={x[0]:x[2].lower() for x in by.get(nid,{}).get("data",{}).get("extractVars",[]) if isinstance(x,list) and len(x)>=3}
        for name in ("preference_from","preference_to"):
            desc=descriptions13.get(name,"")
            if "that week" not in desc or "week of" not in desc:
                a13.append(f"{nid} {name} lacks the anaphoric-week 'that week'/'week of' rule")
    response_prompt13=by.get("n_goal_response",{}).get("data",{}).get("prompt","")
    if "OFFER-INTEGRITY:" not in response_prompt13:
        a13.append("n_goal_response prompt lacks OFFER-INTEGRITY marker")
    for nid in SEARCH_NODES:
        mappings={(x.get("name"),x.get("data")) for x in by.get(nid,{}).get("data",{}).get("responseData",[]) if isinstance(x,dict)}
        if ("from_unresolved","$.result.from_unresolved") not in mappings:
            a13.append(f"{nid} does not map from_unresolved")
    if a13:
        errors.extend("assertion 13: "+message for message in a13)
        checks += len(a13)
    else:
        checks += 1

    # ASSERTION #14: round-14 routes earliest-time questions about the
    # standing offered date through the offered-date search.
    a14=[]
    offered_time_edges=[
        e for e in edges
        if e.get("source")=="n_goal_response"
        and e.get("target")=="n_goal_search_offered_time"
    ]
    if len(offered_time_edges) != 1:
        a14.append(f"expected exactly one n_goal_response offered_time edge, found {len(offered_time_edges)}")
    else:
        offered_time_label=offered_time_edges[0].get("data",{}).get("label","")
        if "earliest" not in offered_time_label.lower():
            a14.append("n_goal_response offered_time edge label lacks 'earliest'")
    if a14:
        errors.extend("assertion 14: "+message for message in a14)
        checks += len(a14)
    else:
        checks += 1

    # ASSERTION #15: post-booking remains conversational, never re-enters
    # scheduling webhooks, and fully replaces the retired soft terminal.
    a15=[]
    post=by.get("n_post_booking")
    if post is None:
        a15.append("n_post_booking is absent")
    else:
        pdata=post.get("data",{})
        if post.get("type") != "Default" or pdata.get("userWait") is not True:
            a15.append("n_post_booking must be a user-wait Default")
        pprompt=pdata.get("prompt","")
        if "(212) 219-2219" not in pprompt:
            a15.append("n_post_booking lacks the office number")
        if pdata.get("extractVars"):
            a15.append("n_post_booking must not define extractVars")
        if re.search(r"{{\s*slot_",str(pprompt)):
            a15.append("n_post_booking contains a slot template")
        if not isinstance(pprompt,str) or len(pprompt) >= 1200:
            a15.append(f"n_post_booking prompt length is {len(pprompt) if isinstance(pprompt,str) else 'non-string'}, must be under 1200")
        post_edges=[e for e in edges if e.get("source")=="n_post_booking"]
        if len(post_edges) > 4:
            a15.append(f"n_post_booking has {len(post_edges)} outbound edges, maximum is 4")
        if {e.get("target") for e in post_edges} - {"e_stop","e_timeout","n_help","n_faq"}:
            a15.append("n_post_booking has a forbidden outbound target")
    webhook_ids={nid for nid,node in by.items() if node.get("type")=="Webhook" and (str(node.get("data",{}).get("url","")).endswith("/availability") or str(node.get("data",{}).get("url","")).endswith("/sign"))}
    frontier=["n_post_booking"]; seen=set()
    while frontier:
        current=frontier.pop()
        if current in seen: continue
        seen.add(current)
        frontier.extend(e.get("target") for e in edges if e.get("source")==current and e.get("target") not in seen)
    reached=sorted(webhook_ids & seen)
    if reached:
        a15.append(f"n_post_booking reaches scheduling webhook(s): {reached}")
    for confirm_id in ("n_confirm_1","n_confirm_2"):
        if not any(e.get("source")==confirm_id and e.get("target")=="n_post_booking" for e in edges):
            a15.append(f"{confirm_id} does not route onward to n_post_booking")
    for node in nodes:
        for pathway in node.get("data",{}).get("responsePathways",[]) or []:
            if isinstance(pathway,list) and len(pathway)>=4 and isinstance(pathway[3],dict) and pathway[3].get("id")=="e_defer":
                a15.append(f"{node.get('id')} responsePathway references e_defer")
    for e in edges:
        if e.get("source")=="e_defer" or e.get("target")=="e_defer":
            a15.append(f"edge {e.get('id')} references e_defer")
    if "e_defer" in ids:
        a15.append("e_defer node still exists")
    if a15:
        errors.extend("assertion 15: "+message for message in a15)
        checks += len(a15)
    else:
        checks += 1

    # ASSERTION #12: round-12 physically separates the pre-offer ask/miss
    # stage from the post-offer response stage and caps their routing load.
    a12=[]
    ask12=by.get("n_goal_ask")
    try:
        frozen12=json.loads(FROZEN_EXTRACTORS.read_text(encoding="utf-8"))
    except Exception as exc:
        frozen12=None
        a12.append(f"frozen extractor pin unavailable: {exc}")
    if ask12 is None:
        a12.append("n_goal_ask is absent")
    else:
        ask_data=ask12.get("data",{})
        if ask12.get("type") != "Default" or ask_data.get("userWait") is not True:
            a12.append("n_goal_ask must be a user-wait Default")
        actual_extractors=ask_data.get("extractVars",[])
        if frozen12 is not None and actual_extractors[:len(frozen12)] != frozen12:
            a12.append("n_goal_ask does not carry the frozen extractor set verbatim")
        ask_prompt12=ask_data.get("prompt","")
        if not isinstance(ask_prompt12,str) or len(ask_prompt12) > 2200:
            a12.append(f"n_goal_ask prompt length is {len(ask_prompt12) if isinstance(ask_prompt12,str) else 'non-string'}, maximum is 2200")
        if re.search(r"{{\s*slot_[0-9]+_",ask_prompt12):
            a12.append("n_goal_ask prompt contains a slot template")
    ask_edges12=[e for e in edges if e.get("source")=="n_goal_ask"]
    response_edges12=[e for e in edges if e.get("source")=="n_goal_response"]
    if len(ask_edges12) > 6:
        a12.append(f"n_goal_ask has {len(ask_edges12)} outbound edges, maximum is 6")
    if len(response_edges12) > 8:
        a12.append(f"n_goal_response has {len(response_edges12)} outbound edges, maximum is 8")
    enum12=[e for e in edges if e.get("target")=="n_goal_search" and "says any day, weekday, date, week, weekend, or time preference" in e.get("data",{}).get("label","")]
    if len(enum12) != 1 or enum12[0].get("source") != "n_goal_ask":
        a12.append("none-search enumeration edge must originate only at n_goal_ask")
    for nid in SEARCH_NODES:
        paths=by.get(nid,{}).get("data",{}).get("responsePathways",[]) or []
        destinations={(tuple(p[:3]),p[3].get("id")) for p in paths if isinstance(p,list) and len(p)>=4 and isinstance(p[3],dict)}
        for condition in (("slot_count",">=","2"),("slot_count","==","1")):
            if (condition,"n_goal_response") not in destinations:
                a12.append(f"{nid} success pathway {condition} does not target n_goal_response")
        for condition in (("ok","!=","true"),("slot_count","==","0"),("out_of_hours","==","true")):
            if (condition,"n_goal_ask") not in destinations:
                a12.append(f"{nid} miss/out-of-hours pathway {condition} does not target n_goal_ask")
    if a12:
        errors.extend("assertion 12: "+message for message in a12)
        checks += len(a12)
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
