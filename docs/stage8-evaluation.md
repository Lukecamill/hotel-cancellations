# Stage 8 — Frozen evaluation and CI gate

Implemented 9 November 2026. See ADR 0010 for thresholds and failure handling.

From the project root with the pinned environment and attributed dataset installed:

```sh
make test
make quality-gate
make ci
```

`make ci` runs tests followed by frozen per-hotel evaluation. It currently
**fails intentionally on the supplied Resort model's calibration**, rather
than allowing promotion because its failure was expected. Do not add `|| true`
in a release pipeline. `make test` is the software correctness check.

The evaluator uses the existing fixed learner and training period, verifies the
frozen holdout identity before fitting, and writes only Stage 8 evaluation
outputs (plus the loader's processed cache). It does not change the running
API, Grafana configuration, serving model, policy, slides or Diary 1 documents.

Evidence in `docs/evidence/stage8/`:

- `report.json`: dataset, source and dependency fingerprints, fixed thresholds,
  per-hotel metrics, individual checks and overall status.
- `reliability.csv`: all ten bins per hotel, including empty bins and counts.
- `reliability.png`: separate hotel reliability diagrams.
- `verification.json`: verification summary including database skips.

| Hotel | Test bookings | AUPRC | Expected / observed | ECE | Result |
|---|---:|---:|---:|---:|---|
| City Hotel | 27,508 | 0.785722 | 0.911281 | 0.042275 | PASS |
| Resort Hotel | 13,179 | 0.627908 | 0.681723 | 0.098961 | FAIL: aggregate calibration |

Thresholds: AUPRC >= 0.70 City / 0.55 Resort; expected/observed within
[0.85,1.15]; ten-bin ECE <= 0.10 for each hotel. No test-set calibration
refitting. Brier scores are diagnostic, not additional tuned thresholds.

The full feature/label SHA-256 is
`ac37475750f8f24abb767a78f7775b905a6ce0dce90d364402074181a9db017b`.
40,687 frozen test rows cover arrivals [2017-01-01,2017-09-01). Identity also
pins raw data, date boundaries, row counts and feature order. Pandas hashing
is environment-dependent: use the pinned requirements; do not regenerate the
lock merely to accommodate a different environment.

For a separate evidence directory:

```sh
.venv/bin/python -m hotel_cancel.quality_gate --output artifacts/stage8-check
```

Exit statuses: 0 pass, 1 quality failure, 2 evaluation/input error. Make's own
exit status may differ but is nonzero for either failure. Output directories
are dedicated to evaluation: obsolete reports/plots there are removed at start.
The lock is reviewed project configuration, not a command that automatically
updates itself. Commit it with code and evidence; keep `data/` excluded.

Database tests run when `TEST_DATABASE_URL` identifies a prepared test database.
Do not point tests at production data. They are separate from this offline
quality gate. MLflow logging of ECE remains Stage 9 work; SHACL CI integration
remains Stage 10 work. This gate does not claim those tasks are complete.
