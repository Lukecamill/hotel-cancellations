import copy,json
import pytest
from hotel_cancel import briefing_revision as module
from hotel_cancel.briefing import GUEST

def valid_interpretation(case):
 return json.dumps(dict(deposit_prepaid=case.get('kb_facts',{}).get('deposit_prepaid'),action='hold_for_calibration_review',guest_message=GUEST,human_approval_required=True))

def test_revised_local_run_meets_full_contract():
 report=module.replay()
 assert report['records']==96 and report['accepted']==95 and report['component_quality_gate']=='PASS'
 assert report['live_model_called'] is False and report['raw_llm_numeric_copy_accuracy_claimed'] is False

def test_model_cannot_inject_or_repair_numeric_fields():
 case=next(iter(module.cases().values()));answer=json.loads(valid_interpretation(case));answer['hotels']={'Resort Hotel':{'proposed_q':999}}
 with pytest.raises(ValueError,match='Invalid interpretation'):module.compose(json.dumps(answer),case)
 result,composed=module.score(json.dumps(answer),case)
 assert result['accepted'] is False and composed is None

def test_changed_prompt_requires_new_run(tmp_path,monkeypatch):
 p=tmp_path/'changed-prompt.txt';p.write_text('Changed system instructions');monkeypatch.setattr(module,'PROMPT',str(p))
 with pytest.raises(ValueError,match='Prompt/schema/context changed'):module.replay()

def test_source_owns_unseen_numeric_values_without_lookup():
 case=copy.deepcopy(next(iter(module.cases().values())))
 case['context_pack']['hotels']['Resort Hotel']['empty_room_cost_eur']=123.456
 case['context_pack']['hotels']['City Hotel']['on_books']=4321
 output=module.compose(valid_interpretation(case),case)
 assert output['hotels']==case['context_pack']['hotels']
 assert output['hotels'] is not case['context_pack']['hotels']
 assert 'hotels' not in module.INTERPRETATION_SCHEMA['properties']


def test_raw_fixture_tampering_rejected(tmp_path,monkeypatch):
 f=json.loads((module.OUT/'responses.json').read_text());answer=json.loads(f['records'][0]['raw']);answer['action']='manager_review';f['records'][0]['raw']=json.dumps(answer)
 (tmp_path/'responses.json').write_text(json.dumps(f));monkeypatch.setattr(module,'OUT',tmp_path)
 with pytest.raises(ValueError,match='Score regression'):module.replay()

def test_wrong_action_is_withheld_at_delivery_boundary():
 case=next(iter(module.cases().values()));answer=json.loads(valid_interpretation(case));answer['action']='manager_review'
 with pytest.raises(ValueError,match='withheld'):module.deliver(json.dumps(answer),case)

def test_live_entrypoint_withholds_bad_model_action(monkeypatch):
 case=next(iter(module.cases().values()));answer=json.loads(valid_interpretation(case));answer['action']='manager_review'
 monkeypatch.setattr(module,'request',lambda *a,**k: {'raw':json.dumps(answer)})
 with pytest.raises(ValueError,match='withheld'):module.generate(case,{})
