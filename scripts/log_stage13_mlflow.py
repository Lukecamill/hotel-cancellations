"""Log the already recorded local run; never calls inference or changes aliases."""
import json,platform,os
os.environ["MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING"]="false"
os.environ["MLFLOW_ENABLE_ASYNC_LOGGING"]="false"
os.environ["MLFLOW_TELEMETRY_ENABLED"]="false"
from pathlib import Path
os.environ["MLFLOW_DISABLE_TELEMETRY"]="true"
os.environ["MLFLOW_DISABLE_AGENT_HINT"]="true"
import mlflow
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'docs/evidence/stage13';report=json.loads((out/'report.json').read_text())
mlflow.set_tracking_uri('sqlite:///'+str(ROOT/'artifacts/stage9/mlflow.db'))
mlflow.set_experiment('task19-stage13-briefing')
client=mlflow.MlflowClient()
def registry():
 return {m.name:dict(m.aliases) for m in client.search_registered_models()}
before=registry()
with mlflow.start_run(run_name='revenue-manager-v1-local') as run:
 mlflow.log_params(dict(provider=report['provider'],base_url=report['base_url'],model=report['model']['name'],
  model_digest=report['model']['digest'],prompt_version=report['prompt_version'],prompt_sha256=report['prompt_sha256'],
  temperature=report['temperature'],hardware=platform.platform()+' '+platform.machine(),production_authorized=False))
 metrics={k:report[k] for k in ['input_tokens','output_tokens','latency_p50_seconds','latency_p95_seconds','cost_per_1000_answers_eur']}
 for group,scores in report['groups'].items():
  for field in ['schema_valid','numeric_exact','grounded','accepted']:
   metrics[group+'_'+field+'_rate']=scores[field]/scores['n']
  metrics[group+'_schema_failure_rate']=1-scores['schema_valid']/scores['n']
 mlflow.log_metrics(metrics);mlflow.log_artifacts(str(out),artifact_path='briefing-evaluation')
 mlflow.log_artifact(str(ROOT/'prompts/revenue-manager-v1.txt'));mlflow.log_artifact(str(ROOT/'config/stage13-golden.json'))
 assert registry()==before, 'Registered aliases changed'
 (out/'mlflow-run.json').write_text(json.dumps(dict(run_id=run.info.run_id,experiment_id=run.info.experiment_id,
   registered_models_changed=False,registry_aliases_before_and_after=before,artifact_uri=run.info.artifact_uri),indent=2)+'\n')
 print(run.info.run_id)
