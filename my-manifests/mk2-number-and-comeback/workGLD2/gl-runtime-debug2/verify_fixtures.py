#!/usr/bin/env python3
import copy,json,subprocess,sys
from pathlib import Path
ids="n_identity n_appt_check n_goal_update n_availability n_goal_response n_select n_consent n_atomic_book n_reconcile n_confirm n_service_guard n_suppress e_close".split()
src="n_identity n_ask n_date_conflict n_miss_empty n_miss_thin n_miss_unbookable n_clarify n_miss_time n_offer n_offer_2 n_offer_3 n_offer_near n_recheck n_miss_unread n_which_intent n_gate_1 n_gate_2 n_negotiate n_search n_page_2 n_page_3 n_page_near n_verify_1 n_verify_2 n_book_1 n_book_2 n_confirm n_help n_office n_faq e_safe_identity e_safe_failure e_booking_failed e_book_unknown e_booked e_office e_declined e_stop e_not_me e_existing e_timeout e_defer n_suppress_stop n_suppress_not_me n_appt_check n_reconcile_1 n_reconcile_2 e_booked_recovered".split()
fields="goal_intent goal_from goal_to time_from time_to anchor relation goal_status goal_revision goal_clarify_count goal_ambiguity_key last_offered_dates offer_id offer_expires_at selected_slot".split()
nodes=[]
for i in ids:
 d={"prompt":"safe"}
 typ="Default"
 if i in ("n_identity","n_appt_check","n_availability","n_select","n_atomic_book","n_reconcile","n_suppress"):
  typ="Webhook"; d["url"]="/x"; d["renders_result"]=True
 if i=="n_goal_update": d["extraction"]="EXTRACT_GOAL_UPDATE_V94 user_verbatim intent_update from_update to_update time_from_update time_to_update anchor_update relation_update selection_update"
 if i=="n_availability": d["body"]="goal_from goal_to time_from time_to anchor relation prior_goal patch raw_text goal_echo decision_source disagreement pathway_read gateway_read slot_minutes distance directional top two one inventory query"
 if i=="n_confirm": d["prompt"]="You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219\n您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219"
 if i=="e_close": d["text"]="For that you'll have to contact the MK2 Optical office at (212) 219-2219\nI’m sorry I couldn’t finish scheduling here. Please call MK2 Optical at (212) 219-2219 for help."
 nodes.append({"id":i,"type":typ,"data":d})
by={n["id"]:n for n in nodes}
for i in ("n_identity","n_appt_check","n_goal_update","n_availability","n_select","n_atomic_book","n_reconcile","n_suppress"):
 by[i]["data"].update({"text":"","userWait":False,"modelOptions":{"retryAttempts":0,"skipUserResponse":True}})
by["n_identity"]["data"].update({"isStart":True,"modelOptions":{"retryAttempts":0,"skipUserResponse":True},"responsePathways":[["count","==","1",{"id":"n_appt_check"}]]})
by["n_appt_check"]["data"].update({"modelOptions":{"retryAttempts":0,"skipUserResponse":True},"responsePathways":[["appt_count","==","0",{"id":"n_goal_response"}]]})
by["n_goal_update"]["data"].update({"prompt":"SILENT PROCESSOR. Apply EXTRACT_GOAL_UPDATE_V94 without speaking.","responsePathways":[["goal_update_v94","!=","",{"id":"n_availability"}]]})
edges=[]
def edge(s,t,label=None):
 e={"id":f"e{len(edges)}-{s}-{t}","source":s,"target":t}
 if label is not None: e["data"]={"label":label,"description":f"Route from {s} to {t} when: {label}."}
 edges.append(e)
for s,t in [("n_identity","n_appt_check"),("n_appt_check","n_goal_response"),("n_goal_update","n_availability"),("n_availability","n_goal_response"),("n_goal_response","n_goal_update"),("n_goal_response","n_select"),("n_select","n_consent"),("n_select","n_goal_update"),("n_consent","n_atomic_book"),("n_atomic_book","n_confirm"),("n_atomic_book","n_reconcile"),("n_atomic_book","n_goal_update"),("n_reconcile","n_confirm"),("n_reconcile","e_close"),("n_confirm","e_close"),("n_service_guard","n_goal_update"),("n_service_guard","e_close"),("n_suppress","e_close"),("n_appt_check","e_close"),("n_identity","e_close"),("n_goal_update","e_close")]: edge(s,t)
for e in edges:
 if e["source"]=="n_identity" and e["target"]=="n_appt_check": e["data"]={"label":"count == 1","description":"Route from n_identity to n_appt_check when: count == 1."}
 if e["source"]=="n_appt_check" and e["target"]=="n_goal_response": e["data"]={"label":"appt_count == 0","description":"Route from n_appt_check to n_goal_response when: appt_count == 0."}
 if e["source"]=="n_goal_update" and e["target"]=="n_availability": e["data"]={"label":"goal_update_v94 != ","description":"Route from n_goal_update to n_availability when: goal_update_v94 != ."}
g={"nodes":nodes,"edges":edges,"source_id_map":{x:"mapped" for x in src},"contract":{"goal_object":{"name":"scheduling_goal_v94","fields":{x:"typed" for x in fields},"semantics":"retain replace clear unsatisfied offered confirmed abandoned","persistent_objects":1,"authoritative_writer":"n_availability"},"loop_cap":8,"ninth_update_target":"e_close","offer":{"terms":"offer_id offer_issued_at offer_expires_at inventory_token exactly two normalized invalidates goal change silent stale refresh nearest real","ttl_minutes":10},"safety":{"clarify_max_questions":2,"appt_check_fail_target":"e_close","blank_conflict_target":"e_close"},"atomic_booking":{"terms":"check_and_book /sign offer_id slot_id conversation_id + ':' + offer_id identical idempotency","max_retries":2},"reconciliation":{"terms":"one read offer_id slot_id store patient date start unique exact match"},"affirmative_claim_owner":"n_confirm","latency":{"max_visible_answer_seconds":15.0,"measurement_owner":"harness","p95_required":True},"availability":"distance directional top two one inventory query"}}

def run(name,obj,needle,should_pass=False):
 p=Path(f"fixture-{name}.json"); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 r=subprocess.run([sys.executable,"check_goalloop_graph.py","--draft",str(p)],text=True,capture_output=True)
 ok=(r.returncode==0) if should_pass else (r.returncode!=0 and needle.lower() in r.stdout.lower())
 print(("PASS" if ok else "BAD"),name,":",r.stdout.splitlines()[0] if r.stdout else "no output")
 return ok
ok=[]; ok.append(run("conformant",g,"",True))
x=copy.deepcopy(g); edge0={"id":"tamper-wait","source":"n_consent","target":"n_consent"}; x["edges"].append(edge0); x["nodes"][ids.index("n_consent")]["data"]["userWait"]=True; ok.append(run("A-wait-self-loop",x,"self-loop"))
x=copy.deepcopy(g); x["edges"].append({"id":"tamper-terminal","source":"n_select","target":"e_close"}); ok.append(run("B-negotiation-terminal",x,"mid-negotiation"))
x=copy.deepcopy(g); x["nodes"][ids.index("n_goal_update")]["data"]["prompt"]="Checking availability for you"; ok.append(run("C-banned-promise",x,"banned promise"))
x=copy.deepcopy(g); x["nodes"][ids.index("n_consent")]["data"]["prompt"]="Come at 3:15 pm"; ok.append(run("D-clock-containment",x,"clock time outside"))
x=copy.deepcopy(g); x["nodes"][ids.index("n_consent")]["data"]["extraction"]="EXTRACT_GOAL_UPDATE_V94"; ok.append(run("E-duplicate-extraction",x,"exactly one"))
raise SystemExit(0 if all(ok) else 1)
