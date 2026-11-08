# Stage 7 — monitoring and performance

Implemented 8 November 2026. Measurement results and verification evidence are listed below after the Ubuntu run.

## Run the system

The existing Ubuntu project is `/home/luke/hotel-stage6`; its Compose project name stays `hotel-stage6` to preserve database and approval volumes. The API image is now `hotel-cancel:stage7`.

In Ubuntu:

```sh
cd ~/hotel-stage6
docker compose -p hotel-stage6 up -d --build --wait
```

From a Mac Terminal, keep the tunnel open (use free local ports if these are already forwarded):

```sh
ssh -p 2222 -L 8080:127.0.0.1:8080 -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 luke@127.0.0.1
```

- Grafana: `http://127.0.0.1:3000/d/hotel-monitoring`
- Prometheus targets/alerts: `http://127.0.0.1:9090/targets`, `/alerts`
- API metrics: `http://127.0.0.1:8080/metrics`
- Manager review: `http://127.0.0.1:8080/review`

The dashboard has eight provisioned panels for request rate, p50/p95 latency, lead-time input mean, errors/persistence loss, historical mature-week calibration, historical PSI, historical policy costs and stored-prediction/batch measurements. The dashboard source and Prometheus rules live under `monitoring/`. Grafana is a read-only anonymous Viewer on localhost, not an exposed public admin interface. Definitions survive container replacement; Prometheus history and the existing PostgreSQL data use persistent volumes.

## What is logged

Every successful `/predict` response gets a prediction ID and `prediction_logged` flag. Operational Compose mode writes one PostgreSQL row and structured stdout record with model version, hotel, timestamp, horizon, probability and a limited input summary. Optional standalone mode without `DATABASE_URL` still predicts, but reports false and increments the unpersisted counter. Database failures are visible rather than silently counted as successful persistence. No nationality, reviewer name, agent/company IDs or complete booking payload is placed in prediction logs. Refer to [ADR 0008](decisions/0008-monitoring-and-performance.md) for the best-effort trade-off.

To log a nightly batch, pass the explicit flag and a private process `DATABASE_URL`:

```sh
python -m hotel_cancel.batch --snapshot-file artifacts/stage6/snapshot.json \
  --output artifacts/stage7/batch.json --monitor
```

This stores the versioned batch forecast and runtime separately. Actual walking/empty-room cost requires subsequent realised releases and a settled costing rule; forecast cost is not labelled as realised cost.

## Historical quality replay

On the full host environment with the dataset and runtime bundle:

```sh
make monitoring-replay
# Optional direct persistence with DATABASE_URL set:
python -m hotel_cancel.monitor_replay --as-of 2017-09-02 --postgres
```

The default report is a **historical dataset replay**, not model quality inferred from current load traffic. It reuses the saved model/calibrators/policy choices, uses no new fitting or policy selection, and records data/model/policy/source fingerprints. Complete arrival weeks require settlement before the replay cutoff; zero-event ratios are undefined, not fabricated as one. Latest mature calibration is for 21–27 August 2017. Low-volume seven-day counts are shown with caution and do not trigger the volume-qualified calibration rule.

Quarterly PSI uses the notebook method against Jul 2015–Jun 2016, with explicit guards for empty/constant samples. Latest 2017Q3 is **July–August**, not a full quarter. Country is an offline aggregate only, because the notebook's nationality artefact must not become a model or relocation criterion. Seasonality, final-state feature history and unknown capacity limit interpretation.

Frozen reference policy costs reproduce approximately €264/night City versus €279 without overbooking, and €96/night Resort versus €98. These are Jan–Aug 2017 sold-out/no-resale arrival-night simulations. They do not represent current earnings or a newly optimised operating policy.

## Alerts and retraining

Prometheus evaluates the committed service and historical-quality rules; view their state in `/alerts`. Rules cover unavailable service, server errors, database-log loss, p95 above 250ms, volume-qualified weekly calibration outside 0.85–1.15, and historical PSI at least 0.25. No external notification delivery is configured. Warning/action responses, low-volume caveats and the retraining plan are in ADR 0008. Retraining and policy promotion require a separate validation/gate/manager process and are not automatic consequences of an alert.

## Repeat the evidence run

The prepared Ubuntu VM has the private `.env`, dataset-derived snapshot and 1,000-booking reference fixture under ignored `artifacts/`. No credentials or dataset fixtures are committed. Generate the fixture from the training-side feature path as in the Stage 6 parity verification; it contains booking objects and their reference probabilities.

```sh
python3 scripts/container_smoke.py --image hotel-cancel:stage7 \
  --output docs/evidence/stage7/container.json
HOTEL_IMAGE=hotel-cancel:stage7 HOTEL_EVIDENCE_DIR=docs/evidence/stage7 \
  python3 scripts/verify_stage6_containers.py --tests
python3 scripts/verify_stage7.py
python3 scripts/load_stage7.py
python3 scripts/verify_stage7.py --after-load
```

The generator offers five requests/second with eight workers for two sixty-second phases, after twenty warmups. The second phase deliberately shifts lead times. This is a booking-block stress envelope, not normal hotel demand. Client latency includes HTTP round trip, inference/queueing and database logging. Warmups are excluded from percentiles but still logged. Exact sample percentiles complement the bucket-estimated Grafana p95. The verifier checks individual measured prediction IDs in PostgreSQL, monitoring targets, provisioned dashboard, alert-rule health and visibility of the input shift.

The source fixture stays in ignored artifacts. Committed aggregate evidence is under `docs/evidence/stage7/`: performance, batch, verification, container and Linux test JSON; replay calibration, drift and nightly-cost CSVs. Timestamped dashboard links/screenshots should use the VM experiment interval when host and VM clocks differ. Production audit time still depends on correct OS clock synchronisation.

Stage 8 adds `make ci`, the frozen per-hotel deployment gate and E3 calibration-error checks. This Stage 7 report does not claim those are complete.

## Measured results

All checks passed in the prepared Ubuntu ARM64 VM with two CPUs and 4GB allocated RAM, running API, PostgreSQL 18.1, Prometheus and Grafana together.

| Phase | Measured requests | HTTP errors | Verified database records | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|
| booking_block_burst | 300 | 0 | 300 | 29.59 ms | 34.25 ms | 36.13 ms |
| lead_time_shift | 300 | 0 | 300 | 29.36 ms | 33.62 ms | 36.80 ms |

Both phases met the prespecified 250ms p95 budget at approximately five successful requests/second. Each phase included 160 City and 140 Resort requests. The slowest per-hotel p95 was 34.57ms. Timing begins at each scheduled arrival, so client-side waiting is included. This is a successful burst-envelope test, not a measurement of maximum sustainable capacity. A preliminary pilot and its warmups remain in persistent logs; the final report identifies its own 600 measured response IDs and verifies every one in PostgreSQL. Dashboard cumulative counts therefore exceed 600.

Prometheus mean input lead time increased from **73.25** to **168.05 days** in the deliberate shift. Grafana may auto-format those durations as weeks. Service-error, persistence-loss and latency alerts were inactive; historical calibration and drift alerts were firing. All six rule expressions were healthy. The eight provisioned panels rendered in Grafana.

**118 Linux/PostgreSQL tests passed with zero skips. All 20 original baseline reproduction checks passed.** The monitored example batch took approximately 44.7ms for the 81 live booking records; that measures forecast computation/artifact loading, not a full nightly PMS job. Its output and versions were persisted.

The latest complete historical week had booking-model calibration ratios of about **0.74 City** (206 observed cancellations) and **0.58 Resort** (142 observed). Initial seven-day ratios were about **2.01 City** (13 observed) and **1.04 Resort** (5 observed); those late-event counts are below the alert guard and must not be treated as reliable evidence of good calibration. These weekly values differ from full-season baseline gate metrics by design.

[Open the dashboard at the measured experiment interval](http://127.0.0.1:3000/d/hotel-monitoring?from=1794074853771&to=1794074993431). The SSH tunnel and running VM are required. The timestamped link uses the VM's experiment interval rather than assuming the Mac/browser clock agrees with it. No live-quality outcome feed exists: a production PMS must retain the prediction-ID/booking association and supply mature outcomes before current calibration/cost can be monitored. This project demonstrates that path with the labelled historical dataset replay.
