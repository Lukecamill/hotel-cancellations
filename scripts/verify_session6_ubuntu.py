"""Disposable Ubuntu Docker verification; no existing demo container, registry or model is changed."""

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/session6-ubuntu"


def main():
    if platform.system() != "Linux":
        raise SystemExit("Run this verifier inside Ubuntu, where Docker is installed")
    os.chdir(ROOT)
    expected = json.loads((ROOT / "config/session6-transfer-inventory.json").read_text())
    for name, checksum in expected["files"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Transferred file differs: {name}")
    for folder, key in [("src/hotel_cancel", "source_files"), ("tests", "test_files")]:
        actual = sorted(str(p.relative_to(ROOT)) for p in (ROOT / folder).glob("*.py"))
        if actual != expected[key]:
            raise ValueError(f"Unexpected source/test inventory in {folder}")
    OUT.mkdir(parents=True, exist_ok=True)
    protected = [p for p in (ROOT / "models/serving").glob('*') if p.is_file()]
    protected += [ROOT / "knowledge/hotel.ttl"]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    if before != expected["protected_runtime_sha256"]:
        raise ValueError("Existing model/knowledge artifacts differ from the prepared reference")
    prefix = "hotel-session6-check-" + secrets.token_hex(4)
    network = prefix + "-network"
    password = secrets.token_urlsafe(24)
    names = {k: prefix + "-" + k for k in ("db", "mlflow", "api")}
    volumes = [prefix + "-db", prefix + "-artifacts"]
    containers = []

    def execute(args, filename=None, check=True):
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result.stdout = result.stdout.replace(password, "[redacted]")
        print(result.stdout, end="", flush=True)
        if filename:
            (OUT / filename).write_text(result.stdout)
        if check and result.returncode:
            raise RuntimeError(f"Command failed ({result.returncode}); inspect {filename or args[0]}")
        return result

    execute(["docker", "info"], "docker-info.txt")
    execute(["docker", "build", "-f", "mlflow/Dockerfile", "-t", "hotel-session6-mlflow-check", "mlflow"], "mlflow-build.txt")
    execute(["docker", "build", "-f", "Dockerfile.registry", "-t", "hotel-session6-api-check", "."], "api-build.txt")
    with tempfile.TemporaryDirectory(prefix="hotel-session6-build-") as temp:
        Path(temp, "Dockerfile").write_text('FROM hotel-cancel:stage9-check\nUSER root\nRUN python -m pip install --no-cache-dir "hypothesis==6.170.15" "ruff==0.17.4" "pytest==9.2.0"\n')
        execute(["docker", "build", "-t", "hotel-session6-tests-check", temp], "tests-build.txt")
    try:
        execute(["docker", "network", "create", "--internal", network])
        for volume in volumes:
            execute(["docker", "volume", "create", volume])
        execute(["docker", "run", "-d", "--name", names["db"], "--network", network, "--network-alias", "postgres",
                 "-e", "POSTGRES_PASSWORD=" + password, "-e", "POSTGRES_USER=hotel", "-e", "POSTGRES_DB=hotel",
                 "-v", volumes[0] + ":/var/lib/postgresql", "-v", str(ROOT / "mlflow/init.sql") + ":/docker-entrypoint-initdb.d/20-mlflow.sql:ro",
                 "postgres:18.1-bookworm"])
        containers.append(names["db"])
        for _ in range(60):
            status = execute(["docker", "exec", names["db"], "pg_isready", "-U", "hotel", "-d", "mlflow"], check=False)
            if status.returncode == 0:
                # pg_isready can succeed before the second database has been created.
                query = execute(["docker", "exec", names["db"], "psql", "-U", "hotel", "-d", "mlflow", "-tAc", "SELECT 1"], check=False)
                if query.returncode == 0:
                    break
            time.sleep(.5)
        else:
            raise RuntimeError("Disposable PostgreSQL did not start")
        execute(["docker", "run", "-d", "--name", names["mlflow"], "--network", network, "--network-alias", "mlflow",
                 "-e", "MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false", "-e", "MLFLOW_DISABLE_TELEMETRY=true",
                 "-v", volumes[1] + ":/mlartifacts", "hotel-session6-mlflow-check", "mlflow", "server", "--host=0.0.0.0",
                 "--port=5000", "--workers=1", "--backend-store-uri=postgresql+psycopg://hotel:" + password + "@postgres:5432/mlflow",
                 "--artifacts-destination=/mlartifacts", "--allowed-hosts=mlflow:*,localhost:*,127.0.0.1:*"])
        containers.append(names["mlflow"])
        base = ["docker", "run", "--rm", "--network", network, "--user", f"{os.getuid()}:{os.getgid()}",
                "-e", "PYTHONPATH=/project/src", "-e", "HOME=/tmp", "-e", "USER=coursework-verifier",
                "-e", "MLFLOW_TRACKING_URI=http://mlflow:5000", "-e", "SESSION6_INTEGRATION_URI=http://mlflow:5000",
                "-e", "MLFLOW_DISABLE_TELEMETRY=true", "-e", "MPLCONFIGDIR=/tmp/matplotlib",
                "-e", "HYPOTHESIS_STORAGE_DIRECTORY=/tmp/hypothesis", "-e", "TEST_DATABASE_URL=postgresql://hotel:" + password + "@postgres:5432/hotel",
                "-v", str(ROOT) + ":/project", "-w", "/project", "hotel-session6-tests-check"]
        for _ in range(60):
            ping = execute(base + ["python", "-c", "import urllib.request; urllib.request.urlopen('http://mlflow:5000/health',timeout=2)"], check=False)
            if ping.returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError("Disposable MLflow server did not start")
        execute(["docker", "run", "-d", "--name", names["api"], "--network", network, "--network-alias", "registry-api",
                 "-e", "MLFLOW_TRACKING_URI=http://mlflow:5000", "-e", "MLFLOW_DISABLE_TELEMETRY=true",
                 "-e", "DATABASE_URL=postgresql://hotel:" + password + "@postgres:5432/hotel", "hotel-session6-api-check"])
        containers.append(names["api"])
        # Before the fixture registry is populated, the actual container must be alive but not ready.
        probe = """import json,urllib.request,urllib.error
for path,expected in [('/health',200),('/ready',503)]:
 try:
  response=urllib.request.urlopen('http://registry-api:8082'+path,timeout=5)
 except urllib.error.HTTPError as response:
  assert response.code==expected
 else:
  assert response.status==expected
print('LIVENESS_READINESS_VERIFIED')
"""
        for _ in range(40):
            alive = execute(base + ["python", "-c", probe], check=False)
            if alive.returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError("API did not expose its unready state")
        execute(base + ["python", "-m", "ruff", "check", "src", "tests", "scripts/prepare_ci_data.py"], "lint.txt")
        tests = execute(base + ["python", "-m", "pytest", "-q", "-o", "cache_dir=/tmp/pytest-cache"], "tests.txt")
        count = re.search(r"(\d+) passed", tests.stdout)
        if not count or " skipped" in tests.stdout or " failed" in tests.stdout:
            raise RuntimeError("Full suite must pass with database tests connected")
        # The test models and metrics are synthetic fixtures, not hotel release candidates.
        execute(["docker", "restart", names["api"]])
        ready = """import json,urllib.request
r=json.load(urllib.request.urlopen('http://registry-api:8082/ready',timeout=5))
assert r['ready'] and all(v['model_version'].endswith('/2') for v in r['models'].values())
print(json.dumps(r))
"""
        for _ in range(50):
            response = execute(base + ["python", "-c", ready], check=False)
            if response.returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError("API did not load fixture models through server artifact proxy")
        (OUT / "ready-before-rollback.json").write_text(response.stdout)
        execute(base + ["python", "-m", "hotel_cancel.registry", "alias", "--hotel", "City Hotel", "--version", "1"], "rollback-alias.txt")
        execute(["docker", "restart", names["api"]])
        prediction = """import json,urllib.request
booking=json.load(open('examples/predict.json'))
r=urllib.request.Request('http://registry-api:8082/predict',json.dumps(booking).encode(),{'Content-Type':'application/json'})
p=json.load(urllib.request.urlopen(r,timeout=5))
assert p['model_version']=='task19-session6-city-booking/1' and p['prediction_logged']
print(json.dumps(p))
"""
        for _ in range(50):
            response = execute(base + ["python", "-c", prediction], check=False)
            if response.returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError("Container rollback prediction failed")
        (OUT / "prediction-after-rollback.json").write_text(response.stdout)
        payload = json.loads(response.stdout)
        sql = "SELECT model_version,model_lineage->>'run_id' FROM hotel_predictions WHERE prediction_id='" + payload["prediction_id"] + "'"
        row = execute(["docker", "exec", names["db"], "psql", "-U", "hotel", "-d", "hotel", "-tAc", sql], "database-lineage.txt")
        assert payload["model_version"] in row.stdout and payload["model_lineage"]["run_id"] in row.stdout
        execute(base + ["python", "-m", "hotel_cancel.registry", "alias", "--hotel", "City Hotel", "--version", "2"], "restore-alias.txt")
        result = {"status": "VERIFIED", "tests_passed": int(count[1]), "tests_skipped": 0,
                  "tracking_backend": "disposable PostgreSQL", "artifact_transport": "MLflow HTTP proxy",
                  "container_readiness_and_rollback": "PASS", "prediction_database_lineage": "PASS",
                  "models_used": "synthetic test fixtures only; no Task 19 release candidate registered",
                  "project_candidate_registration": "pending clean committed source and fresh tracked training",
                  "peer_review": "pending another student", "production_authorized": False,
                  "original_demo_unchanged": all(hashlib.sha256((ROOT / n).read_bytes()).hexdigest() == h for n, h in before.items())}
        if not result["original_demo_unchanged"]:
            raise RuntimeError("Protected runtime changed")
        (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
        print("SESSION6_UBUNTU_VERIFIED\n" + json.dumps(result, indent=2))
    finally:
        for name in reversed(containers):
            log = execute(["docker", "logs", name], check=False)
            # Backend credentials can appear in server exception messages. Never preserve them.
            (OUT / (name.rsplit('-', 1)[-1] + "-container.txt")).write_text(log.stdout.replace(password, "[redacted]"))
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for volume in volumes:
            subprocess.run(["docker", "volume", "rm", volume], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["docker", "network", "rm", network], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
