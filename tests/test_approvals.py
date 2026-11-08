import copy
from datetime import datetime
import hashlib
import http.client
import json
import os
import threading
from uuid import uuid4

import pytest
from psycopg.types.json import Jsonb

from hotel_cancel.approvals import ApprovalStore,DecisionConflict,validate_decision
from hotel_cancel.service import make_server


def decision(**changes):
    return dict(decision='approve',quantity=3,reviewer='Coursework reviewer',reason='Reviewed the stated cost and walking risk.',simulation_acknowledged=True,**changes)


@pytest.mark.parametrize('choice,q', [('approve',3),('reduce',1),('reduce',0),('reject',0)])
def test_valid_decisions(choice,q):
    request=decision();request.update(decision=choice,quantity=q)
    assert validate_decision(request,3)['quantity']==q


@pytest.mark.parametrize('changes', [dict(quantity=4),dict(quantity=-1),dict(quantity=True),dict(quantity=1),
                                     dict(decision='reject',quantity=2),dict(decision='reduce',quantity=3),
                                     dict(reviewer=' '),dict(reason=''),dict(simulation_acknowledged=False),dict(decision='other')])
def test_invalid_decisions(changes):
    request=decision();request.update(changes)
    with pytest.raises(ValueError):validate_decision(request,3)


def test_zero_recommendation_can_be_rejected():
    request=decision();request.update(decision='reject',quantity=0)
    assert validate_decision(request,0)['quantity']==0


@pytest.fixture
def store_and_review():
    url=os.environ.get('TEST_DATABASE_URL')
    if not url:pytest.skip('Set TEST_DATABASE_URL for real approval database tests')
    store=ApprovalStore(url)
    identifier=hashlib.sha256(uuid4().bytes).hexdigest()
    payload=dict(schema_version=1,simulation=True,snapshot_id='test-snapshot',decision_date='2017-08-08',arrival='2017-08-15',lead_days=7,
                 model_version='model-version',policy_version='policy-version',walk_cost_eur=250,variable_cost_eur=20,resale_rate=0,
                 recommendation=dict(hotel='Test hotel',candidate_oversell=3))
    with store.connect() as c:c.execute('INSERT INTO hotel_policy_reviews (review_id,payload) VALUES (%s,%s)',(identifier,Jsonb(payload)))
    yield store,identifier
    # Remove only this unique fixture's rows, never another review's audit trail.
    with store.connect() as c:
        c.execute('DELETE FROM hotel_policy_decisions WHERE review_id=%s',(identifier,))
        c.execute('DELETE FROM hotel_policy_reviews WHERE review_id=%s',(identifier,))


def test_database_decision_survives_new_store_and_cannot_be_overwritten(store_and_review):
    store,identifier=store_and_review
    pending=next(r for r in store.list_reviews() if r['review_id']==identifier)
    assert pending['simulated_approved_quantity']==0 and pending['review_status']=='pending'
    saved=store.decide(identifier,decision())
    datetime.fromisoformat(saved['approved_at_utc'])
    assert saved['snapshot_id']=='test-snapshot' and saved['model_version']=='model-version'
    loaded=next(r for r in ApprovalStore(store.database_url).list_reviews() if r['review_id']==identifier)
    assert loaded['decision']==saved and loaded['simulated_approved_quantity']==3
    assert loaded['operational_authorised_oversell']==0
    with pytest.raises(DecisionConflict):store.decide(identifier,decision())


def test_concurrent_reviewers_cannot_both_approve(store_and_review):
    from concurrent.futures import ThreadPoolExecutor
    store,identifier=store_and_review
    def attempt():
        try:store.decide(identifier,decision());return 'saved'
        except DecisionConflict:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _:attempt(),range(2)))==['conflict','saved']


def test_http_review_requires_token_and_same_origin(store_and_review):
    store,identifier=store_and_review
    server=make_server(None,port=0,approvals=store)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    def request(method,path,body=None,extra=None):
        conn=http.client.HTTPConnection(*server.server_address,timeout=5)
        headers={'Content-Type':'application/json'};headers.update(extra or {})
        conn.request(method,path,body=json.dumps(body) if body is not None else None,headers=headers)
        response=conn.getresponse();status=response.status;value=response.read();conn.close()
        return status,value
    try:
        assert b'Coursework simulation' in request('GET','/review')[1]
        token=json.loads(request('GET','/reviews')[1])['csrf_token']
        path='/reviews/'+identifier+'/decision'
        assert request('POST',path,decision())[0]==403
        assert request('POST',path,decision(),{'X-Review-Token':token,'Origin':'http://unrelated.example'})[0]==403
        assert request('POST',path,dict(decision(),quantity=100),{'X-Review-Token':token})[0]==422
        assert request('POST',path,decision(),{'X-Review-Token':token})[0]==201
        assert request('POST',path,decision(),{'X-Review-Token':token})[0]==409
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)


def test_publish_from_snapshot_is_idempotent_and_preserves_versions(store_and_review, runtime, snapshot):
    from hotel_cancel.snapshot import seal_snapshot,write_postgres
    store,_=store_and_review
    snapshot.pop('snapshot_id')
    snapshot['test_fixture']=uuid4().hex
    snapshot=seal_snapshot(snapshot)
    write_postgres(snapshot,store.database_url)
    ids=[]
    try:
        ids=store.publish(snapshot['snapshot_id'],runtime[0])
        assert store.publish(snapshot['snapshot_id'],runtime[0])==ids
        reviews=[r for r in store.list_reviews() if r['review_id'] in ids]
        assert len(reviews)==2
        assert {r['recommendation']['hotel'] for r in reviews}=={'City Hotel','Resort Hotel'}
        assert all(r['model_version']==runtime[0].version and r['snapshot_id']==snapshot['snapshot_id'] and r['review_status']=='pending' for r in reviews)
    finally:
        with store.connect() as c:
            for identifier in ids:c.execute('DELETE FROM hotel_policy_reviews WHERE review_id=%s',(identifier,))
            c.execute('DELETE FROM hotel_snapshots WHERE snapshot_id=%s',(snapshot['snapshot_id'],))


# Use the independent model and snapshot fixtures from the serving tests.
from test_serving import runtime,records,snapshot
