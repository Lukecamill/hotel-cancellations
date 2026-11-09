import pandas as pd
import pytest
from rdflib import Graph,Literal,RDF,URIRef

from hotel_cancel.blocks import GROUP_KEY,block_ids,outcome_status,block_graph,attribution_by_block
from hotel_cancel.knowledge import KB_DIR,HB,timestamp,validate_graph


def keys():
    values={c:['code','code'] for c in GROUP_KEY}
    for c in ['arrival','booked']:values[c]=pd.to_datetime(['2017-08-15']*2 if c=='arrival' else ['2017-07-01']*2)
    for c in ['adults','children','stays_in_weekend_nights','stays_in_week_nights']:values[c]=[1,1]
    values['adr']=[100.,100.];values['hotel']=['City Hotel']*2
    return pd.DataFrame(values)


def test_block_identity_ignores_audit_labels_outcomes_and_row_order():
    frame=keys();ids=block_ids(frame)
    assert ids.nunique()==1
    changed=frame.assign(country=['PRT','GBR'],is_canceled=[0,1],reservation_status=['Check-Out','Canceled'])
    assert block_ids(changed).tolist()==ids.tolist()
    assert block_ids(changed.iloc[::-1]).sort_index().tolist()==ids.tolist()
    changed.loc[1,'booked']=pd.Timestamp('2017-07-02')
    assert block_ids(changed).nunique()==2


@pytest.mark.parametrize('n,released,status',[(3,0,'NoRecordedRelease'),(3,1,'PartiallyReleased'),(3,3,'FullyReleased')])
def test_outcome_states_are_counts_not_verified_party_assertions(n,released,status):
    assert outcome_status(n,released)==status


def test_invalid_release_counts_fail():
    with pytest.raises(ValueError):outcome_status(3,4)


@pytest.fixture
def fixture_graph():
    return Graph().parse(KB_DIR/'blocks-example.ttl',format='turtle')


def validate_blocks(graph):
    return validate_graph(graph,Graph().parse(KB_DIR/'block-shapes.ttl',format='turtle'))[0]


def test_block_fixtures_validate_and_decision_snapshots_have_no_future_counts(fixture_graph):
    assert validate_blocks(fixture_graph)
    for s in fixture_graph.subjects(RDF.type,HB.BlockSnapshot):
        assert fixture_graph.value(s,HB.releasedUnits) is None
        assert fixture_graph.value(s,HB.remainingUnits) is None
        assert fixture_graph.value(s,HB.status)==HB.OnBooks
    for b in fixture_graph.subjects(RDF.type,HB.InferredBookingBlock):
        assert fixture_graph.value(b,HB.verifiedParty).toPython() is False


@pytest.mark.parametrize('defect',['future_count_in_snapshot','negative_size','premature_outcome','invalid_status','claims_verified_party'])
def test_shacl_rejects_inconsistent_or_leaking_block_metadata(fixture_graph,defect):
    snapshot=HB['block-snapshot/synthetic-partial'];outcome=HB['block-outcome/synthetic-partial'];block=HB['inferred-block/synthetic-partial']
    if defect=='future_count_in_snapshot':fixture_graph.add((snapshot,HB.releasedUnits,Literal(2)))
    elif defect=='negative_size':
        fixture_graph.remove((snapshot,HB.liveSize,None));fixture_graph.add((snapshot,HB.liveSize,Literal(-1)))
    elif defect=='premature_outcome':
        fixture_graph.remove((outcome,HB.availableNotBefore,None));fixture_graph.add((outcome,HB.availableNotBefore,timestamp('2017-08-08')))
    elif defect=='invalid_status':
        fixture_graph.remove((outcome,HB.status,None));fixture_graph.add((outcome,HB.status,HB.FullyReleased))
    else:
        fixture_graph.remove((block,HB.verifiedParty,None));fixture_graph.add((block,HB.verifiedParty,Literal(True)))
    assert not validate_blocks(fixture_graph)


def test_cost_attribution_detects_partial_relocation_without_inventing_more_walks():
    nights=pd.DataFrame(dict(unit_id=['a','b','c'],stable_block=['group','group','single']))
    exposure=pd.DataFrame(dict(unit_id=['a','b','c'],hotel=['City Hotel']*3,rule=['seeded_lottery']*3,walked=[1,0,1]))
    summary,splits=attribution_by_block(exposure,nights)
    assert summary.total_walked.iat[0]==2
    assert summary.walked_in_inferred_multirow_blocks.iat[0]==1
    assert summary.partially_relocated_inferred_blocks.iat[0]==1
    assert splits.partial_split.iat[0]


def test_signed_zero_keys_preserve_policy_equivalence_and_row_order():
    frame=keys();frame['adr']=[0.0,-0.0]
    assert block_ids(frame).nunique()==1
    assert block_ids(frame).tolist()==block_ids(frame.iloc[::-1]).sort_index().tolist()
