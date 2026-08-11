#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, re, sys
from pathlib import Path

ALLOWED={20,35,50,65,80}
WEIGHTS={
 'market_demand_supply':({'demand_strength':.25,'supply_balance':.20,'payer_income_fit':.15,'growth_future_demand':.15,'specialty_demand_load':.15,'market_data_confidence':.10},'market_demand_supply_score'),
 'competitive_pressure':({'supply_saturation':.40,'patient_choice_pressure':.25,'competitor_strength':.20,'access_differentiation_pressure':.15},'competitive_pressure_index'),
 'practice_competitiveness':({'visibility_vs_peers':.20,'access_booking_vs_peers':.20,'review_trust_vs_peers':.20,'service_line_differentiation':.15,'website_conversion_clarity':.15,'location_convenience':.10},'practice_competitiveness_score'),
 'digital_presence':({'findability':.25,'reputation':.20,'bookability':.20,'site_quality':.15,'content_specialty_signal':.10,'social_local_proof':.10},'digital_presence_score'),
}
SPECIALTY_W={'local_demand_fit':.20,'competitive_gap':.15,'current_capability':.15,'access_capacity_fit':.15,'revenue_reimbursement_potential':.15,'referral_ecosystem_fit':.10,'evidence_confidence':.10}
CLIENT_W={'competitive_pressure_opportunity':.20,'practice_differentiation_upside':.20,'access_fixability':.15,'digital_visibility_fixability':.15,'execution_simplicity':.10}

def why(x): print(f'WHY: {x}')
def nearest(x): return math.floor(x+0.5)
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def validate_basis(name,vals,basis,allowed_sources,fail):
    if set(vals)!=set(basis): fail.append(f'{name} basis keys do not parallel value keys')
    for k,v in vals.items():
        if v not in ALLOWED: fail.append(f'{name}.{k} uses noncanonical base band {v}')
        b=basis.get(k,{})
        for req in ['band_label','rationale','source_ids','confidence','unknown_handling']:
            if not b.get(req): fail.append(f'{name}.{k} basis missing {req}')
        bad=set(b.get('source_ids',[]))-allowed_sources
        if bad: fail.append(f'{name}.{k} unresolved source IDs {sorted(bad)}')
        if v==50 and 'unknown' in b.get('band_label','').lower() and b.get('unknown_handling')!='neutral_unknown_no_directional_claim':
            fail.append(f'{name}.{k} neutral unknown lacks canonical handling')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scores',required=True); ap.add_argument('--sources',required=True); a=ap.parse_args(); fail=[]
    try: d=load(a.scores); src=load(a.sources)
    except Exception as e: why(f'JSON parse failed: {e}'); return 1
    allowed_sources={x.get('id') for x in src.get('sources',[])}
    if d.get('schema_version')!='2.0': fail.append('schema_version must be 2.0')
    if d.get('analysis_product')!='single_practice': fail.append('analysis_product must be single_practice')
    if d.get('data_mode')!='public_only': fail.append('data_mode must be public_only')
    if d.get('report_visibility')!='internal_only_unroomed_draft': fail.append('report_visibility must be internal_only_unroomed_draft')
    if d.get('scoring_method')!='manual_directional_banding_public_only': fail.append('wrong scoring_method')
    scores=d.get('scores',{}); subs=d.get('subscores',{}); basis=d.get('subscore_basis',{})
    for group,(weights,outkey) in WEIGHTS.items():
        vals=subs.get(group,{}); bs=basis.get(group,{})
        validate_basis(group,vals,bs,allowed_sources,fail)
        if set(vals)!=set(weights): fail.append(f'{group} component keys do not match formula')
        elif nearest(sum(vals[k]*w for k,w in weights.items()))!=scores.get(outkey):
            fail.append(f'{outkey} does not recompute from canonical weights')
    p=scores.get('competitive_pressure_index')
    if isinstance(p,(int,float)) and scores.get('room_to_win_score')!=100-p: fail.append('Room to Win must equal 100 - pressure')
    cv=subs.get('client_opportunity',{}); cb=basis.get('client_opportunity',{})
    validate_basis('client_opportunity',cv,cb,allowed_sources,fail)
    if set(cv)!=set(CLIENT_W): fail.append('client opportunity component keys do not match formula')
    elif isinstance(scores.get('market_demand_supply_score'),(int,float)):
        calc=.20*scores['market_demand_supply_score']+sum(cv[k]*w for k,w in CLIENT_W.items())
        if nearest(calc)!=scores.get('client_opportunity_score'): fail.append(f'client_opportunity_score does not recompute: expected {nearest(calc)}')
    co=scores.get('client_opportunity_score')
    expected_label=('dominate' if co is not None and co>=85 else 'win_more' if co is not None and co>=70 else 'vulnerable' if co is not None and co>=55 else 'at_risk' if co is not None and co>=40 else 'low_opportunity_hard_market')
    if scores.get('client_opportunity_label')!=expected_label: fail.append('client opportunity label does not match canonical bands')
    if scores.get('confidence_grade')!='C': fail.append('public-only directional run must remain Confidence C')
    specialties=d.get('specialty_options',[])
    if len(specialties)<3: fail.append('need at least three specialty options')
    for lane in specialties:
        vals=lane.get('subscores',{}); bs=lane.get('subscore_basis',{})
        validate_basis('specialty.'+str(lane.get('lane')),vals,bs,allowed_sources,fail)
        if set(vals)!=set(SPECIALTY_W): fail.append(f"specialty {lane.get('lane')} keys do not match formula")
        elif nearest(sum(vals[k]*w for k,w in SPECIALTY_W.items()))!=lane.get('specialty_opportunity_score'): fail.append(f"specialty {lane.get('lane')} does not recompute")
        for k in ['lane','read','why','source_ids','source_strength','confidence','disconfirmers']:
            if not lane.get(k): fail.append(f"specialty {lane.get('lane')} missing {k}")
    wp=d.get('website_positioning',{})
    if wp.get('digital_presence_score')!=scores.get('digital_presence_score'): fail.append('website_positioning digital score mismatch')
    if wp.get('components')!=subs.get('digital_presence'): fail.append('website_positioning components mismatch')
    if wp.get('component_basis')!=basis.get('digital_presence'): fail.append('website_positioning basis mismatch')
    for k in ['stated_position','market_position','position_vs_white_space','recommended_position','channel_gaps','source_ids','confidence']:
        if not wp.get(k): fail.append(f'website_positioning missing {k}')
    fp=d.get('fix_it_playbook',{})
    cards=fp.get('cards',[])
    if fp.get('mode')!='GROW': fail.append('Fix-It mode must be GROW')
    if not (1<=len(cards)<=3): fail.append(f'Fix-It must have 1-3 cards, got {len(cards)}')
    ids=[c.get('id') for c in cards]
    if fp.get('do_now')!=ids: fail.append('do_now must list the cards in order')
    for c in cards:
        for k in ['id','finding','lever','owner','effort','impact_grow','impact_math','time_to_value','dependency','proof','confidence','source_ids']:
            if c.get(k) in [None,'',[]]: fail.append(f"Fix Card {c.get('id')} missing {k}")
        if '$' in c.get('impact_grow','') and 'unknown' not in c.get('impact_grow','').lower() and 'sensitivity' not in c.get('impact_grow','').lower(): fail.append(f"Fix Card {c.get('id')} may present unsupported dollars")
        bad=set(c.get('source_ids',[]))-allowed_sources
        if bad: fail.append(f"Fix Card {c.get('id')} unresolved source IDs {sorted(bad)}")
    dq=d.get('data_quality',{})
    if dq.get('project_room_status') not in ['EMPTY','UNROOMED','inventory_review_required']: fail.append('data_quality project room must be EMPTY, UNROOMED, or inventory_review_required')
    if dq.get('use_boundary')!='INTERNAL-ONLY / NOT FOR EXTERNAL USE': fail.append('missing internal-only use boundary')
    if dq.get('external_actions_taken')!='none': fail.append('external_actions_taken must be none')
    for key in ['missing_to_upgrade','weak_or_missing_sources']:
        if len(dq.get(key,[]))<5: fail.append(f'data_quality.{key} too sparse')
    if len(d.get('disconfirmers',[]))<4: fail.append('need at least four disconfirmers')
    alltext=json.dumps(d,ensure_ascii=False)
    for pat in [r'—',r'(?i)lorem ipsum',r'(?i)client[- ]ready',r'(?i)prospect[- ]ready',r'(?i)api[_ -]?key\s*[:=]',r'(?i)password\s*[:=]']:
        if re.search(pat,alltext): fail.append(f'banned pattern present: {pat}')
    if fail:
        for x in fail: why(x)
        return 1
    print(f"PASS: canonical manual-band scores recompute: market {scores['market_demand_supply_score']}, pressure {scores['competitive_pressure_index']}, room {scores['room_to_win_score']}, practice {scores['practice_competitiveness_score']}, opportunity {scores['client_opportunity_score']}, digital {scores['digital_presence_score']}; {len(specialties)} specialties and {len(cards)} Fix Cards validated")
    return 0
if __name__=='__main__': sys.exit(main())
