"""Execute the unchanged reference cells with an isolated, fresh data cache."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'notebooks/reference/19_hotel_cancellations.ipynb'
OUT = ROOT / 'artifacts/reference-run'
OUT.mkdir(parents=True, exist_ok=True)
data = OUT / 'data'
raw = data / 'raw/hotel_bookings/hotel_bookings.csv'
raw.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / 'data/raw/hotel_bookings/hotel_bookings.csv', raw)
cache = data / 'processed/19_hotel_bookings.parquet'
cache.unlink(missing_ok=True)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
os.environ['DATASETS_TASKS_DATA'] = str(data)
nb = nbformat.read(SOURCE, as_version=4)
for cell in nb.cells:
    if cell.cell_type == 'code':
        cell.outputs = []
        cell.execution_count = None
# An extra evidence cell runs after every original cell; original source is untouched.
nb.cells.append(nbformat.v4.new_code_cell('''# Execution-only evidence capture, not part of the supplied method.
evidence = {
    "split_counts": {"train": int(tr.sum()), "valid": int(va.sum()), "test": int(te.sum())},
    "booking_metrics": res_base.to_dict(orient="index"),
    "gate": gate.to_dict(orient="index"),
    "holdout_sha256": fingerprint,
    "chosen_policies": CHOSEN,
    "policy_test_results": summarise(pol).reset_index().to_dict(orient="records"),
    "tonight": tonight_rows,
    "notebook_wall_seconds": time.time() - T_START,
}
Path("artifacts/reference-run/results.json").write_text(json.dumps(evidence, indent=2, default=str) + "\\n")
'''))
client = NotebookClient(nb, timeout=600, kernel_name='python3', resources={'metadata': {'path': str(ROOT)}})
# Force this project's interpreter, independent of globally installed kernel specs.
from jupyter_client import KernelManager
km = KernelManager(kernel_name='python3')
km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
client.km = km
started = time.perf_counter()
status = 'failed'
try:
    client.execute()
    status = 'passed'
finally:
    elapsed = time.perf_counter() - started
    nbformat.write(nb, OUT / 'reference.executed.ipynb')
    metadata = {
        'status': status, 'source_sha256_before': source_hash,
        'source_sha256_after': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
        'python': sys.version, 'executable': sys.executable,
        'platform': platform.platform(), 'machine': platform.machine(),
        'processor': platform.processor(), 'cpu_count': os.cpu_count(),
        'elapsed_seconds_including_kernel': elapsed,
        'cache': 'isolated processed cache removed before execution',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
        'packages': {p: importlib.metadata.version(p) for p in ['pandas','numpy','lightgbm','scikit-learn','rdflib','pyshacl','pyarrow','matplotlib','kagglehub','nbclient','ipykernel']},
    }
    (OUT / 'execution.json').write_text(json.dumps(metadata, indent=2) + '\n')
    with (OUT / 'outputs.txt').open('w') as f:
        for i, cell in enumerate(nb.cells):
            for output in cell.get('outputs', []):
                if output.output_type == 'stream':
                    f.write(f'Cell {i} [{output.name}]\n{output.text}\n')
                elif output.output_type == 'error':
                    f.write(f'Cell {i} ERROR\n' + '\n'.join(output.traceback) + '\n')
                elif 'text/plain' in output.get('data', {}):
                    f.write(f'Cell {i}\n{output.data["text/plain"]}\n')
    print(json.dumps(metadata, indent=2))
