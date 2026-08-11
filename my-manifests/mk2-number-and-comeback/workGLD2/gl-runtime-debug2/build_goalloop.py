#!/usr/bin/env python3
"""Deterministically contract pathway-v92 into the 13-node v94 goal loop."""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent.parent / "pathway-v92.json"
OUTPUT = HERE / "pathway-goalloop-draft.json"

EXTRACTION = """Read the full conversation and latest USER message. Return exactly:
user_verbatim: exact latest user text, with double quotes changed to single quotes.
intent_update: book_exam|abandon|retain.
from_update: an accepted future day/range phrase, unclear, clear, or retain.
to_update: an accepted future range end, unclear, clear, or retain.
time_from_update: 12-hour time with AM/PM, none|clear|retain.
time_to_update: 12-hour time with AM/PM, none|clear|retain.
anchor_update: day-open|day-close|noon|an explicit 12-hour time with AM/PM|clear|retain.
relation_update: nearest|before|after|clear|retain.
selection_update: 1|2|yes|no|unclear|none.

Rules: update only what the latest user changed. Never reset omitted fields. Rejections clear only the rejected value. Bare weekdays mean the next occurrence. Preserve week qualifiers. ASAP/next available/earliest means tomorrow with anchor=day-open and relation=after. First appointment means anchor=day-open and relation=after. Last/latest slot means anchor=day-close and relation=before. Around noon means anchor=noon and relation=nearest. After an explicit time sets that time as anchor and relation=after. Before an explicit time sets that time as anchor and relation=before. Morning/afternoon/late select configured anchor presets, not band bounds. A correction 'no, the following X' resolves relative to the offered date plus 7 days, never relative to today. A question is not consent. A message that selects and changes a preference is a goal update, not booking consent. Do not calculate or emit slot times, booking status, prose, or any other field."""

OPENING = """Hi {{patient_first}}, this is MK2 Optical.

We noticed that it's been awhile since your last visit with us. Staying on top of your eye health with a comprehensive eye exam is important.

Many vision insurance benefits renew yearly, so don't let your benefits go unused!

When would you like to come in? Just reply with a day and a time that works for you and I will check what we have. Reply STOP to opt out.

如需中文服务，请直接用中文回复。"""

GOAL_SCHEMA = {
    "name": "scheduling_goal_v94", "persistent": True,
    "fields": {name: "SPEC §2 typed field" for name in ("goal_intent goal_from goal_to time_from time_to anchor relation goal_status goal_revision goal_clarify_count goal_ambiguity_key last_offered_dates offer_id offer_expires_at selected_slot").split()},
    "initial": {"goal_intent":"book_exam","goal_from":"monday","goal_to":"friday","time_from":"none","time_to":"none","anchor":"day-open","relation":"after","goal_status":"unsatisfied","goal_revision":0,"goal_clarify_count":0,"goal_ambiguity_key":"none","last_offered_dates":[],"offer_id":"none","offer_expires_at":"none","selected_slot":"none"},
    "lifecycle": ["unsatisfied -> offered -> confirmed", "unsatisfied|offered -> abandoned"],
    "patch_semantics": "absence retains; explicit replacement replaces; explicit rejection clears only the rejected constraint",
    "authority": "n_availability goal_echo atomically replaces the stored object; gateway wins every disagreement",
    "persistent_objects": 1,
    "authoritative_writer": "n_availability",
}

def load_source():
    with SOURCE.open(encoding="utf-8") as f: return json.load(f)

def source_node(src, node_id):
    return copy.deepcopy(next(n for n in src["nodes"] if n["id"] == node_id))

def node(node_id, kind, name, x, y, **data):
    d = {"active": False, "name": name, **data}
    return {"data":d,"height":115,"id":node_id,"position":{"x":x,"y":y},"sourcePosition":"bottom","targetPosition":"top","type":kind,"width":320,"x":x,"y":y}

def route(var, op, value, target, name): return [var, op, value, {"id":target,"name":name}]

def edge(source, target, label):
    slug = "-".join("".join(c.lower() if c.isalnum() else " " for c in label).split())[:72]
    return {"animated":True,"data":{"description":f"Route from {source} to {target} when: {label}.","isHighlighted":False,"label":label},"id":f"edge-{source}-{target}-{slug}","source":source,"sourceHandle":None,"target":target,"targetHandle":None,"type":"custom"}

def condition_edge(source, target, var, op, value):
    """Encode routing exactly as the proven v92 Bland graph does."""
    return edge(source, target, f"{var} {op} {value}")

def webhook_data(name, url, body, response_data, pathways, retries=0):
    return {"body":json.dumps(body,separators=(",",":")),"headers":{"Authorization":"{{ SECRET.MottGatewayToken }}","Content-Type":"application/json"},"method":"POST","modelOptions":{"retryAttempts":retries,"skipUserResponse":True},"name":name,"responseData":response_data,"responsePathways":pathways,"text":"","url":url}

def rd(path, name): return {"data":path,"name":name}

def build():
    src=load_source(); nodes=[]
    identity=source_node(src,"n_identity"); identity["data"]["responsePathways"]=[route("recall_cell","==","","e_close","No mobile supplied"),route("recall_patient_id","==","","e_close","No patient id supplied"),route("store","==","","e_close","No store supplied"),route("count","==","0","e_close","Identity failed"),route("count",">=","2","e_close","Identity not unique"),route("ok","!=","true","e_close","Identity lookup unavailable"),route("count","==","1","n_appt_check","Identity confirmed")]; nodes.append(identity)
    appt=source_node(src,"n_appt_check"); appt["data"]["responsePathways"]=[route("appt_count",">=","1","e_close","Upcoming appointment found: defer to office"),route("appt_count","==","0","n_goal_response","No upcoming appointment: render opening"),route("ok","!=","true","e_close","Appointment check unavailable")]; nodes.append(appt)

    update_prompt="""SILENT PROCESSOR. Emit no patient-facing words. Apply EXTRACT_GOAL_UPDATE_V94 as a patch to the single persistent scheduling_goal_v94 object; omitted fields retain and rejected constraints alone clear. Every accepted update, including a usable date with the configured default time window, immediately advances to n_availability in this same turn. Never ask a question or announce work. Cap completed scheduling iterations at 8; the ninth routes to loop_cap close."""
    nodes.append(node("n_goal_update","Default","Update persistent scheduling goal (silent)",850,500,prompt=update_prompt,text="",userWait=False,responsePathways=[route("goal_update_v94","!=","","n_availability","Extracted update ready")],goalObject=GOAL_SCHEMA,extractionDefinition={"name":"EXTRACT_GOAL_UPDATE_V94","definition":EXTRACTION},extractVars=[["goal_update_v94","string","EXTRACT_GOAL_UPDATE_V94",False,False,True]],modelOptions={"newTemperature":0.2,"retryAttempts":0,"skipUserResponse":True},loopContract={"counter":"goal_revision","maximum_completed_iterations":8,"ninth_update_target":"e_close","ninth_update_mode":"loop_cap","guards_do_not_consume_or_reset":True}))

    availability_body={"store":"{{store}}","prior_goal":"{{scheduling_goal_v94}}","pathway_update":"{{goal_update_v94}}","raw_text":"{{lastUserMessage}}","current_offer_id":"{{offer_id}}","call_id":"{{callID}}","goal_from":"{{goal_from}}","goal_to":"{{goal_to}}","time_from":"{{time_from}}","time_to":"{{time_to}}","anchor":"{{anchor}}","relation":"{{relation}}","slot_minutes":15}
    avail_rd=[rd("$.ok","ok"),rd("$.result.goal_echo","goal_echo"),rd("$.result.pathway_read","pathway_read"),rd("$.result.gateway_read","gateway_read"),rd("$.result.decision_source","decision_source"),rd("$.result.disagreement_fields","disagreement_fields"),rd("$.result.response_kind","response_kind"),rd("$.result.question_kind","question_kind"),rd("$.result.date_candidate_1_en","date_candidate_1_en"),rd("$.result.date_candidate_2_en","date_candidate_2_en"),rd("$.result.inventory_token","inventory_token"),rd("$.result.choices","choices"),rd("$.result.choices[0].choice","slot_1_choice"),rd("$.result.choices[0].slot_id","slot_1_id"),rd("$.result.choices[0].date","slot_1_date"),rd("$.result.choices[0].day_name","slot_1_day_name"),rd("$.result.choices[0].start","slot_1_start"),rd("$.result.choices[0].store","slot_1_store"),rd("$.result.choices[1].choice","slot_2_choice"),rd("$.result.choices[1].slot_id","slot_2_id"),rd("$.result.choices[1].date","slot_2_date"),rd("$.result.choices[1].day_name","slot_2_day_name"),rd("$.result.choices[1].start","slot_2_start"),rd("$.result.choices[1].store","slot_2_store"),rd("$.result.offer_id","offer_id"),rd("$.result.offer_issued_at","offer_issued_at"),rd("$.result.offer_expires_at","offer_expires_at"),rd("$.result.goal_clarify_count","goal_clarify_count"),rd("$.result.goal_ambiguity_key","goal_ambiguity_key")]
    avail_paths=[route("ok","!=","true","n_service_guard","Availability unavailable: office/defer guard"),route("response_kind","==","offer","n_goal_response","Fresh two-choice offer"),route("response_kind","==","empty_nearest","n_goal_response","Nearest real alternatives"),route("response_kind","==","ambiguity","n_goal_response","Targeted clarification"),route("response_kind","==","reask","n_goal_response","One bounded re-ask"),route("response_kind","==","empty","n_goal_response","Empty range"),route("response_kind","==","lost_slot","n_goal_response","Lost selected slot"),route("response_kind","==","selection","n_select","Live selection candidate"),route("response_kind","==","exhausted","n_service_guard","Explicit exhaustion: office guard")]
    ad=webhook_data("Interpret goal and search once (silent)","https://mott-booking-gw.mail.mybcat.com/availability",availability_body,avail_rd,avail_paths,1); ad.update({"patch":"pathway patch {{goal_update_v94}}","goalEchoWrite":"Atomically replace scheduling_goal_v94 with complete goal_echo before routing; no pathway field overrides it.","orderingRule":"Sort each day's real slots by distance from anchor; apply the directional filter; nearest has no exclusion, before excludes at/after anchor, after excludes at/before anchor; return top two.","queryContract":"Exactly one inventory query per accepted update; bounded request with no legacy paging branches or band compensation.","offerContract":{"choice_count":2,"ttl_minutes":10,"invalid_at_expiry":True,"invalid_on_any_goal_change":True}}); nodes.append(node("n_availability","Webhook",ad.pop("name"),1225,700,**ad))

    response_prompt=f"""You are a patient-facing RESPOND node. When entered from n_appt_check with no response_kind, send exactly:\n{OPENING}\nOtherwise render exactly one response_kind using only this call's data. offer: "I have {{{{slot_1_day_name}}}} {{{{slot_1_date}}}} {{{{slot_1_start}}}} or {{{{slot_2_day_name}}}} {{{{slot_2_date}}}} {{{{slot_2_start}}}} at MK2 Optical. Reply 1 or 2 to take one, or tell me another day or time." latest: use the same standard two-choice offer pattern, ordered true latest then immediately before. ambiguity: "I want to make sure I get the right day. Did you mean {{{{date_candidate_1_en}}}} or {{{{date_candidate_2_en}}}}? You can also reply with a different date." reask: "Please reply with one specific day or date, such as August 12. I’ll search using the best date I have after this reply." empty: "I don't have anything open in that range. What other day or date range works for you?" empty_nearest: "I don't have anything open in that range. The nearest openings are {{{{slot_1_day_name}}}} {{{{slot_1_start}}}} or {{{{slot_2_day_name}}}} {{{{slot_2_start}}}} at MK2 Optical. Reply 1 or 2 to take one, or tell me another date range." lost_slot: "That opening is no longer available. What other day or date range works for you?" Only offer and empty_nearest may state clock times, and only the two choices under this response's offer_id and inventory_token. A usable date always exits to n_goal_update. Ambiguity asks once, re-asks once, then gateway fail-opens to search using the best retained non-null range. Never remain here and never claim booking."""
    nodes.append(node("n_goal_response","Default","Render offer or bounded question",1600,900,prompt=response_prompt,userWait=True,modelOptions={"newTemperature":0.2},clarifyContract={"question_limit_per_ambiguity":1,"reask_limit_per_ambiguity":1,"after_reask":"fail-open-to-search","usable_date_target":"n_goal_update","self_loop":False}))

    select_body={"operation":"bind_live_offer","offer_id":"{{offer_id}}","offer_expires_at":"{{offer_expires_at}}","raw_text":"{{lastUserMessage}}","prior_goal":"{{scheduling_goal_v94}}","choices":"{{choices}}","inventory_token":"{{inventory_token}}","call_id":"{{callID}}"}
    sd=webhook_data("Bind live offer or refresh silently","https://mott-booking-gw.mail.mybcat.com/offer-select",select_body,[rd("$.ok","select_ok"),rd("$.result.kind","select_kind"),rd("$.result.selected_slot","selected_slot"),rd("$.result.selected_slot.day_name","selected_slot_day_name"),rd("$.result.goal_patch","selection_goal_patch")],[route("select_kind","==","selected","n_consent","Live exact offer member selected"),route("select_kind","==","stale","n_availability","Silent normal refresh"),route("select_kind","==","goal_patch","n_goal_update","Preference change re-enters goal update"),route("select_ok","!=","true","n_availability","Silent safe refresh")]); sd["staleContract"]="Expired or goal-invalidated acceptance never books and produces no visible error; run one normal fresh availability attempt."; nodes.append(node("n_select","Webhook",sd.pop("name"),1975,1100,**sd))
    consent_prompt="""Send exactly: "To confirm, you want the eye exam on {{selected_slot_day_name}} at MK2 Optical. Reply YES to book it, or NO to keep looking." This is date-only: never state a clock time and never claim a booking. YES only routes to n_atomic_book. NO and every preference change route to n_goal_update. A question is not consent."""; nodes.append(node("n_consent","Default","Date-only booking consent",2350,1300,prompt=consent_prompt,userWait=True,modelOptions={"newTemperature":0.2}))

    book_body={"operation":"check_and_book","offer_id":"{{offer_id}}","slot":"{{selected_slot}}","slot_id":"{{selected_slot.slot_id}}","inventory_token":"{{selected_slot.inventory_token}}","patient_id":"{{patient_id}}","store":"{{store}}","exam_type_id":"{{exam_type_id}}","idempotency_key":"{{callID}}:{{offer_id}}"}
    bd=webhook_data("Atomic conflict check and book (silent)","https://mott-booking-gw.mail.mybcat.com/sign",book_body,[rd("$.ok","book_ok"),rd("$.success","book_success"),rd("$.slot_conflict","slot_conflict"),rd("$.outcome_known","outcome_known"),rd("$.attempted_offer","attempted_offer"),rd("$.error","book_error")],[route("slot_conflict","==","true","n_goal_update","Definite conflict returns as lost-slot update"),route("book_success","==","true","n_confirm","Atomic booking succeeded"),route("outcome_known","==","false","n_reconcile","Exhausted transport retries require exact reconciliation"),route("book_success","==","false","e_close","Definite booking failure"),route("slot_conflict","!=","false","e_close","Blank missing or non-boolean conflict fails safe")],2); bd["retryContract"]="After timeout/transport failure retry identical request and identical idempotency key with bounded backoff, at most 2 retries; never mint a key or change payload."; bd["conflictContract"]="Only boolean false permits success evaluation; blank, missing, or non-boolean fails safe."; nodes.append(node("n_atomic_book","Webhook",bd.pop("name"),2725,1500,**bd))

    recon_body={"operation":"reconcile_exact_attempt","offer_id":"{{attempted_offer.offer_id}}","slot_id":"{{attempted_offer.slot_id}}","store":"{{attempted_offer.store}}","patient_id":"{{patient_id}}","attempted_date":"{{attempted_offer.date}}","attempted_start":"{{attempted_offer.start}}"}
    rddata=webhook_data("Reconcile exact attempted offer once (silent)","https://mott-booking-gw.mail.mybcat.com/appt-list",recon_body,[rd("$.ok","recon_ok"),rd("$.result.exact_match_count","exact_match_count"),rd("$.result.exact_match","exact_match")],[route("recon_ok","!=","true","e_close","Reconciliation unavailable"),route("exact_match_count","==","1","n_confirm","Unique exact attempted appointment exists"),route("exact_match_count","==","0","e_close","No exact match"),route("exact_match_count",">=","2","e_close","Ambiguous exact matches")]); rddata["matchContract"]="Unique match must agree on offer_id, slot_id, store, patient, attempted date, and attempted start; count-only evidence is forbidden."; nodes.append(node("n_reconcile","Webhook",rddata.pop("name"),3100,1700,**rddata))

    confirm_prompt="""You are the sole affirmative booking-claim owner. On direct atomic success, name the confirmed date but no clock time, then end exactly: "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219". On recovered exact reconciliation, send exactly that fixed close. Chinese fixed close: "您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219". Any later request defers and never searches or books again."""; nodes.append(node("n_confirm","Default","Confirmed booking close",3475,1900,prompt=confirm_prompt,userWait=True,modelOptions={"newTemperature":0.2}))

    service_prompt="""Global service guard. help: "This is MK2 Optical's appointment scheduling assistant. For help, call (212) 219-2219. Reply STOP to opt out." office: give (212) 219-2219 for orders, glasses status, or medical questions. FAQ: vision insurance typically has an allowance with co-pays; cost depends on benefits; office staff can help at (212) 219-2219. Ask whether to continue scheduling, without repeating any offer or clock time. A question is never a decline. Return to n_goal_update unless the patient explicitly abandons, has an existing appointment, or needs office termination."""; nodes.append(node("n_service_guard","Default","Global help office and FAQ guard",100,700,prompt=service_prompt,userWait=True,isGlobal=True,enableGlobalAutoReturn=False,globalLabel="HELP, office, insurance, coverage, cost, contact lens, frames, sunglasses, orders, glasses status, or medical question before confirmation",modelOptions={"newTemperature":0.2}))

    stop=source_node(src,"n_suppress_stop")["data"]; wrong=source_node(src,"n_suppress_not_me")["data"]; suppress_data={"active":False,"name":"STOP or wrong-person suppression (silent)","isGlobal":True,"enableGlobalAutoReturn":False,"globalLabel":stop["globalLabel"]+" "+wrong["globalLabel"],"method":"POST","url":stop["url"],"headers":copy.deepcopy(stop["headers"]),"body":"{\"phone_e164\":\"{{recall_cell}}\",\"reason\":\"stop_or_wrong_person\",\"source\":\"sms_reply\"}","modelOptions":copy.deepcopy(stop["modelOptions"]),"responseData":copy.deepcopy(stop["responseData"]),"responsePathways":[route("suppression_ok","==","true","e_close","Suppression recorded"),route("suppression_ok","!=","true","e_close","Suppression response still closes")],"text":"","modes":{"stop":{"reason":"stop","close_mode":"stop"},"wrong_person":{"reason":"complaint","close_mode":"not_me"}}}; nodes.append(node("n_suppress","Webhook",suppress_data.pop("name"),100,1100,**suppress_data))

    close_modes={i:source_node(src,i)["data"]["text"] for i in ["e_safe_identity","e_safe_failure","e_booking_failed","e_booked","e_office","e_declined","e_stop","e_not_me","e_existing","e_timeout","e_defer","e_book_unknown"]}; close_modes.update({"loop_cap":"I’m sorry I couldn’t finish scheduling here. Please call MK2 Optical at (212) 219-2219 for help.","loop_cap_zh":"很抱歉，我无法在这里完成预约。请致电 MK2 Optical (212) 219-2219 获取帮助。","exhausted":"I’m sorry I couldn’t find another opening that works. Please call MK2 Optical at (212) 219-2219 for help."}); nodes.append(node("e_close","End Call","Safe office deferral",3850,2100,text=source_node(src,"e_defer")["data"]["text"],outcome="deferred_after_booking",modes=close_modes,terminalModes=["booked","deferred_after_booking","stop","not_me","identity_failed","gateway_failed","existing_appointment","no_reply","declined","booking_unverified","loop_cap","exhausted"]))

    edges=[]
    specs=[("n_identity","n_appt_check","identity succeeds uniquely"),("n_identity","e_close","identity fails or is unsafe"),("n_appt_check","n_goal_response","appointment check is explicitly ok and count is zero; render opening"),("n_appt_check","e_close","existing appointment or any non-true appointment-check result"),("n_goal_update","n_availability","accepted scheduling update 1 through 8, including every usable clarified date"),("n_goal_update","e_close","ninth scheduling update, abandonment, or timeout"),("n_availability","n_goal_response","offer, nearest alternatives, empty range, lost slot, ambiguity, or bounded re-ask"),("n_availability","n_select","gateway identifies a live selection candidate"),("n_availability","n_service_guard","gateway failure or explicit exhaustion routes through office/defer guard"),("n_goal_response","n_goal_update","every patient scheduling reply; abandonment and timeout are interpreted at the sole inbound update"),("n_select","n_consent","selection binds to an unexpired exact offer member"),("n_select","n_availability","stale offer silently refreshes through one normal attempt"),("n_select","n_goal_update","reply is a goal patch or mixed selection and preference"),("n_consent","n_atomic_book","explicit YES to date-only consent"),("n_consent","n_goal_update","NO, question, or changed preference"),("n_atomic_book","n_confirm","definite success with boolean false slot conflict"),("n_atomic_book","n_goal_update","definite slot conflict becomes lost-slot update"),("n_atomic_book","n_reconcile","unknown outcome after identical-key retries are exhausted"),("n_atomic_book","e_close","definite failure or invalid conflict value"),("n_reconcile","n_confirm","one unique exact attempted-offer match"),("n_reconcile","e_close","zero, ambiguous, mismatched, or unavailable reconciliation"),("n_confirm","e_close","booked close or post-booking deferral"),("n_service_guard","n_goal_update","help, office, or FAQ answer continues same goal"),("n_service_guard","e_close","explicit decline or office termination"),("n_suppress","e_close","STOP or wrong-person suppression response")]
    # Bland's runtime consumes executable condition labels on webhook edges.  Keep
    # those byte-shaped like v92, and use semantic labels only for LLM nodes.
    webhook_ids={"n_identity","n_appt_check","n_goal_update","n_availability","n_select","n_atomic_book","n_reconcile","n_suppress"}
    for s,t,l in specs:
        if s not in webhook_ids: edges.append(edge(s,t,l))
    for n in nodes:
        if n["id"] in webhook_ids:
            for var,op,value,dest in n["data"].get("responsePathways",[]):
                edges.append(condition_edge(n["id"],dest["id"],var,op,value))
    source_id_map={
        old:new for new,olds in {
            "n_identity":["n_identity"],"n_appt_check":["n_appt_check"],"n_goal_update":["n_ask","n_negotiate"],
            "n_goal_response":["n_date_conflict","n_miss_empty","n_miss_thin","n_miss_unbookable","n_clarify","n_miss_time","n_offer","n_offer_2","n_offer_3","n_offer_near","n_recheck"],
            "e_close":["n_miss_unread","e_safe_identity","e_safe_failure","e_booking_failed","e_book_unknown","e_booked","e_office","e_declined","e_stop","e_not_me","e_existing","e_timeout","e_defer"],
            "n_select":["n_which_intent"],"n_consent":["n_gate_1","n_gate_2"],"n_availability":["n_search","n_page_2","n_page_3","n_page_near"],
            "n_atomic_book":["n_verify_1","n_verify_2","n_book_1","n_book_2"],"n_confirm":["n_confirm","e_booked_recovered"],
            "n_service_guard":["n_help","n_office","n_faq"],"n_suppress":["n_suppress_stop","n_suppress_not_me"],"n_reconcile":["n_reconcile_1","n_reconcile_2"]}.items() for old in olds}
    offer_contract={"terms":"offer_id, offer_issued_at, offer_expires_at, and inventory_token bind exactly two normalized real choices; nearest choices are real inventory. Invalidate at expiry or goal change; stale acceptance silently refreshes.","ttl_minutes":10,"choices":2}
    graph={"analysis_options":src.get("analysis_options"),"edges":edges,"entity_schemas":src.get("entity_schemas",[]),"memory_enabled":src.get("memory_enabled",False),"nodes":nodes,"post_call_actions":src.get("post_call_actions",[]),"revision_number":94,"version_number":94,"source_id_map":source_id_map,"contract":{"spec":"SPEC-v94-draft4","node_target":13,"goal_object":GOAL_SCHEMA,"loop_cap":8,"ninth_update_target":"e_close","scheduling_loop":["n_goal_update","n_availability","n_goal_response","n_goal_update"],"extraction_definition":"EXTRACT_GOAL_UPDATE_V94","availability_call_sites":["n_availability"],"availability":"distance from anchor, directional filter, top two, one inventory query","offer":offer_contract,"safety":{"clarify_max_questions":2,"appt_check_fail_target":"e_close","blank_conflict_target":"e_close"},"atomic_booking":{"terms":"governed /sign check_and_book with exact offer_id and slot_id; idempotency key conversation_id + ':' + offer_id; identical request and idempotency key on retry","max_retries":2},"reconciliation":{"terms":"one read using offer_id, slot_id, store, patient, attempted date and start; confirm only a unique exact match"},"affirmative_claim_owner":"n_confirm","latency":{"max_visible_answer_seconds":15.0,"measurement_owner":"harness","p95_required":True},"source_contraction":{"source_node_count":48}}}
    assert len(nodes)==13 and len({n["id"] for n in nodes})==13
    assert all(e["source"] in {n["id"] for n in nodes} and e["target"] in {n["id"] for n in nodes} for e in edges)
    return graph

if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"wrote {OUTPUT.name}")
