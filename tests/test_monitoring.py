import http.client
import json
import os
import threading
from uuid import uuid4

import numpy as np
import pandas as pd
import psycopg
import pytest

from hotel_cancel.monitoring import Telemetry
from hotel_cancel.monitor_replay import psi_num,psi_cat,weekly
from hotel_cancel.service import make_server
from test_serving import runtime,records


def test_psi_identical_shift_and_constant_reference():
    reference=np.arange(100)
    assert psi_num(reference,reference)==pytest.approx(0)
    assert psi_num(reference,reference+500)>.25
    assert psi_num(np.ones(30),np.ones(30))==pytest.approx(0)
    assert psi_num(np.ones(30),np.ones(30)*2)>0
    assert psi_cat(pd.Series(['A']*50+['B']*50),pd.Series(['A']*50+['B']*50))==pytest.approx(0)
    assert psi_cat(pd.Series(['A']*100),pd.Series(['NEW']*100))>.25


def test_weekly_excludes_unmatured_week_and_handles_zero_events():
    frame=pd.DataFrame(dict(hotel=['City Hotel']*3,arrival=pd.to_datetime(['2017-08-21','2017-08-22','2017-08-29']),p=[.2,.3,.4],y=[0,0,1]))
    result=weekly(frame,'booking_to_arrival',pd.Timestamp('2017-09-02'))
    assert len(result)==1 and result.n.iat[0]==2
    assert pd.isna(result.ratio.iat[0]) and not result.alert.iat[0]


def test_database_failure_does_not_disguise_loss(records,monkeypatch):
    t=Telemetry()
    t.database_url='test-only'
    def unavailable():raise psycopg.OperationalError('unavailable')
    monkeypatch.setattr(t,'connect',unavailable)
    identifier,logged=t.prediction(records[0],.25,'v1')
    assert identifier and logged is False
    assert t.failures._value.get()==1
    assert t.predictions.labels('City Hotel','v1')._value.get()==1


def test_bounded_label_cardinality():
    t=Telemetry()
    for i in range(20):t.observe_request('/untrusted/'+str(i),'MADEUP',404,'unknown',.01)
    text=t.render().decode()
    assert 'route="other"' in text and '/untrusted/' not in text and 'method="other"' in text


def test_online_request_persisted_and_metrics_exposed(runtime,records):
    url=os.environ.get('TEST_DATABASE_URL')
    if not url:pytest.skip('Set TEST_DATABASE_URL for monitoring persistence test')
    t=Telemetry(url)
    server=make_server(runtime[0],port=0,telemetry=t)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    identifier=None
    try:
        connection=http.client.HTTPConnection(*server.server_address,timeout=5)
        connection.request('POST','/predict',json.dumps({'booking':records[0]}),{'Content-Type':'application/json'})
        response=connection.getresponse();payload=json.loads(response.read());connection.close()
        assert response.status==200 and payload['prediction_logged'] is True
        identifier=payload['prediction_id']
        with t.connect() as c:
            saved=c.execute('SELECT hotel,model_version,horizon,probability,inputs FROM hotel_predictions WHERE prediction_id=%s',(identifier,)).fetchone()
        assert saved[0]=='City Hotel' and saved[1]==runtime[0].version and saved[2]=='booking_to_arrival'
        assert saved[3]==payload['cancellation_probability'] and 'country' not in saved[4]
        connection=http.client.HTTPConnection(*server.server_address,timeout=5)
        connection.request('GET','/metrics');response=connection.getresponse();text=response.read().decode();connection.close()
        assert 'hotel_predictions_total' in text and 'hotel_http_request_seconds_bucket' in text
        assert 'hotel_prediction_logs_total 1.0' in text
        assert '/metrics' not in text
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        if identifier:
            with t.connect() as c:c.execute('DELETE FROM hotel_predictions WHERE prediction_id=%s',(identifier,))


def test_monitoring_can_reuse_saved_calibrators_without_fitting(runtime,monkeypatch):
    from types import SimpleNamespace
    from hotel_cancel.policy import prepare_policy
    from sklearn.linear_model import LogisticRegression
    predictor,bk,model,X=runtime
    cfg=dict(predictor.policy['config'],train_end=pd.Timestamp('2016-07-01'),valid_end=pd.Timestamp('2017-01-01'),
             test_end=pd.Timestamp('2017-09-01'),window_start=pd.Timestamp('2015-07-01'),window_end=pd.Timestamp('2017-09-01'),tonight=pd.Timestamp('2017-08-08'))
    outcome=pd.DataFrame(dict(is_canceled=np.tile([0,1],len(bk)//2),status_date=bk.arrival))
    def forbidden(*args,**kwargs):raise AssertionError('Monitoring must not fit a calibrator')
    monkeypatch.setattr(LogisticRegression,'fit',forbidden)
    snap,_,_,cal,_=prepare_policy(SimpleNamespace(bookings=bk,outcome=outcome,probabilities=model.predict_proba(X)[:,1]),cfg,
                                 calibrators=predictor.policy['calibrators'],flat_rates=predictor.policy['flat_rates'])
    assert len(snap)==len(bk)
    assert all(cal[h] is predictor.policy['calibrators'][h] for h in cfg['hotels'])
