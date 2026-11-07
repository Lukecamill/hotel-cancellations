# Stage 3 Step 3: original notebook execution

Completed 7 November 2026 in the existing project virtual environment. All 38 original cells executed successfully, without changing their source. A final execution-only evidence cell exports full-precision results; it does not train or alter the supplied method. This is the original-notebook run, not yet a fresh comparison with the packaged pipeline.

## Results

| Measure | City Hotel | Resort Hotel |
|---|---:|---:|
| Test AUPRC | 0.785722 | 0.627908 |
| Test ROC-AUC | 0.798905 | 0.780415 |
| Expected / realised cancellations | 0.911281 | 0.681723 |
| Diagnostic gate | PASS | FAIL (calibration) |
| Selected policy | Flat Jul–Sep 2016 rate | Model + blocks + 8-week re-levelling |
| 2017 selected-policy cost/night | EUR264.424650 | EUR96.183128 |
| No-overbooking cost/night | EUR278.649465 | EUR98.068539 |
| 2017 savings | EUR3,456.63 | EUR458.155 |
| Oversell for 15 August 2017 | 3 rooms | 0 rooms |

Split counts match exactly: 49,157 training, 29,546 validation, 40,687 test. AUPRC and expected/realised match the supplied printed values within the existing ADR tolerances (0.0005 and 0.005 absolute). Policy choices, rounded nightly costs, rounded savings and integer oversell decisions match the supplied outputs. No model tuning or new policy selection was performed beyond executing the supplied code. Resort FAIL is expected, not an execution error or permission to deploy it.

Full holdout SHA-256: `ac37475750f8f24abb767a78f7775b905a6ce0dce90d364402074181a9db017b`, matching the reference’s printed prefix.

## Runtime and environment

Notebook timer: approximately 19.38 seconds; execution including kernel startup: 22.09 seconds. The notebook’s fitting cell printed 2 seconds, including pooled and separate-hotel comparison fits. Supplied full-notebook reference time: 85 seconds. These are single-run observations on different machines, not a speedup benchmark.

Python 3.13.13; macOS arm64, 10 logical CPUs. pandas 3.1.0, NumPy 2.5.4, LightGBM 4.7.0, scikit-learn 1.9.1, rdflib 7.6.0, pyshacl 0.40.1 match the versions printed by the supplied notebook. Additional package versions and platform details are in execution.json.

No notebook-cell stderr or error outputs were captured. The kernel launcher emitted a TCP-encryption warning, preserved in runner.log. The notebook itself suppresses FutureWarning, so absence of captured warnings does not establish absence of suppressed warnings.

## Reproduce and inspect

From the repository root with the existing environment and pinned CSV available:

```bash
.venv/bin/python scripts/run_reference.py
```

The runner forces the project interpreter, sets the notebook’s data-directory environment variable and copies the verified local raw file into an isolated ignored run directory. It removes that run’s processed cache before execution, preserving the original notebook’s loading behaviour without reusing an old Parquet. Re-running overwrites these local run artifacts.

- Executed notebook, including plots: `artifacts/reference-run/reference.executed.ipynb` (ignored).
- Full-precision captured results: [results.json](evidence/reference-run/results.json).
- Environment, timing, source/raw hashes and starting repository state: [execution.json](evidence/reference-run/execution.json).
- Text outputs: [outputs.txt](evidence/reference-run/outputs.txt).
- Launcher output: [runner.log](evidence/reference-run/runner.log).

The evidence records base commit `9f8659f691088eae7b1c314ceedfac5d5dce6d68` and a dirty working tree. These new files are not yet committed, so do not describe the base commit alone as containing this evidence. Source hashes before and after are identical to the supplied original. A cosmetic runner simplification after execution removed an unused conditional expression; the execution path is unchanged.

Next: review the existing packaged booking method against the original, then run and compare it. Packaging and reproducing policy functions remains necessary before full Stage 3 completion.
