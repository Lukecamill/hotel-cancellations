"""Log/register an isolated calibrated research challenger; no champion promotion."""
import os
os.environ['MLFLOW_DISABLE_TELEMETRY']='true';os.environ['MLFLOW_DISABLE_AGENT_HINT']='true'
import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,joblib
import mlflow
from mlflow.models import infer_signature
from hotel_cancel.calibrated_registry_model import CalibratedHotelBookingModel
from hotel_cancel.calibration_challenger import verify_saved,apply_calibration
from hotel_cancel.config import load_config
from hotel_cancel.quality_gate import prepare
from hotel_cancel.serving import Predictor
from hotel_cancel.features import BOOKING_INPUTS
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/evidence/remediation/calibration'
verify_saved();report=json.loads((out/'report.json').read_text());config=load_config();pred=Predictor(ROOT/'models/serving')
mlflow.set_tracking_uri('sqlite:///'+str(ROOT/'artifacts/stage9/mlflow.db'));mlflow.set_experiment('task19-calibration-remediation')
client=mlflow.MlflowClient();old_names=['task19-city-booking','task19-resort-booking']
before={name:dict(client.get_registered_model(name).aliases) for name in old_names}
cal=ROOT/'artifacts/remediation/booking-calibrator.joblib'
with mlflow.start_run(run_name='resort-booking-calibration-v1') as run:
 mlflow.log_params(dict(method=report['plan']['method'],fit_start=report['plan']['fit_start'],fit_end=report['plan']['fit_end'],
   fit_rows=report['fit_rows'],base_model_sha256=pred.version,calibrator_sha256=report['calibrator_sha256'],production_authorized=False))
 mlflow.log_metrics({k:report['hotels']['Resort Hotel'][k] for k in ['auprc','expected_observed_ratio','ece','brier']})
 mlflow.log_artifacts(str(out),artifact_path='calibration-evidence')
 example=dict(json.loads((ROOT/'examples/predict.json').read_text())['booking'],hotel='Resort Hotel',agent='none',company='none')
 sample=pd.DataFrame([example]);output=pd.DataFrame({'cancellation_probability':[.5]})
 info=mlflow.pyfunc.log_model(name='calibrated-booking-model',python_model=CalibratedHotelBookingModel('Resort Hotel'),
  artifacts=dict(booking_bundle=str(ROOT/'models/serving/booking_model.joblib'),booking_calibrator=str(cal)),
  code_paths=[str(ROOT/'src/hotel_cancel')],signature=infer_signature(sample,output),
  pip_requirements=[s for s in (ROOT/'requirements-tracking.txt').read_text().splitlines() if s and not s.startswith(('#','-'))],
  metadata=dict(horizon='booking_to_arrival',production_authorized=False,baseline_reference_unchanged=True))
 loaded=mlflow.pyfunc.load_model(info.model_uri)
 bk,X,y,masks,identity=prepare(config);mask=masks['test'] & bk.hotel.astype(str).eq('Resort Hotel')
 frame=bk.loc[mask,[c for c in BOOKING_INPUTS if c!='booked']].copy();frame['arrival']=frame.arrival.dt.strftime('%Y-%m-%d')
 for c in frame.select_dtypes(include='category').columns:frame[c]=frame[c].astype(object)
 expected=apply_calibration(pred.bundle['model'].predict_proba(X.loc[mask])[:,1],frame.hotel.to_numpy(),joblib.load(cal),base_model_sha256=pred.version)
 actual=loaded.predict(frame)['cancellation_probability'].to_numpy();error=float(np.max(np.abs(actual-expected)))
 if error>1e-12:raise ValueError('Registered calibrator preprocessing mismatch')
 name='task19-resort-booking-calibrated';version=mlflow.register_model(info.model_uri,name)
 client.set_registered_model_alias(name,'challenger',version.version)
 assert {n:dict(client.get_registered_model(n).aliases) for n in old_names}==before
 result=dict(run_id=run.info.run_id,registered_name=name,version=int(version.version),alias='challenger',champion_set=False,
  holdout_booking_adapter_parity_rows=len(frame),maximum_probability_difference=error,original_aliases_unchanged=True,
  original_aliases=before,serving_unchanged=True,production_authorized=False)
 (out/'mlflow-run.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
