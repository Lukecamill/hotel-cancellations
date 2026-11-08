# ADR 0008 — prediction persistence, separate quality signals and measured performance

Date: 8 November 2026. Status: implemented; measured results recorded in the Stage 7 report.

## Decision

Follow Session 4 with one Compose project containing the API, PostgreSQL, Prometheus and Grafana. Pin the taught Prometheus/Grafana versions and the Python client. Keep ports on localhost and use SSH tunnels from the Mac. Provision the dashboard and alert rules from version-controlled files. Grafana anonymous access is Viewer, rather than the notes' Admin, because editing is performed in the provisioned source.

Persist each successful booking API prediction with a request ID, timestamp, model hash, probability, booking-to-arrival horizon and a limited input summary. Emit the same record to structured container logs. Log batch outputs separately with snapshot/model/policy versions and runtime; do not treat seven-day policy forecasts as booking-time probabilities. Queries bind parameters. Reviewer names, nationality and full booking payloads are not prediction-log fields.

Use synchronous one-connection-per-request logging, as the course notes allow, and include its cost in measured response latency. If PostgreSQL persistence fails, return the valid prediction with `prediction_logged: false`, retain the structured log and increment an alertable failure counter. Fail-closed refusal is an alternative for mandatory-audit systems; this coursework service adopts the notes' best-effort choice and exposes the loss explicitly. `--monitor` batch persistence is explicit; database failure makes that command fail instead of silently declaring a logged batch.

Use a per-server Prometheus registry, bounded route/method/hotel/segment labels, response-latency and input-lead-time histograms. Exclude scrape and health probes from application traffic metrics. Counters reset on API restart; PostgreSQL and Prometheus data persist in volumes. Never put request IDs, names, raw paths or booking codes into unbounded metric labels.

## Quality monitoring and label delay

Keep live API counters/input metrics separate from historical quality replay. Booking outcomes mature after arrival, while seven-day predictions are conditioned on still-live bookings. Generate complete arrival-week summaries only after a conservative one-day settlement; exclude future cancellation statuses and incomplete weeks. Reuse the saved model, horizon calibrators and reference policy choices without fitting or selecting on the frozen holdout. The policy module's optional saved-calibrator inputs preserve baseline defaults.

The replay's latest complete week is 21–27 August 2017. Show both booking-to-arrival and active-seven-day ratios. The latter describes the initial saved horizon calibration, not a guarantee that every block/re-level policy is calibrated. Compare fixed reference policy costs with no overbooking on Jan–Aug 2017. These are retrospective sold-out/no-resale arrival-night proxies, not measured live revenue.

Package the notebook's PSI calculation for lead time and categorical features, adding empty-sample rejection and a constant-reference safeguard. Monitor nationality only as an offline aggregate to expose the documented source artefact; keep it excluded from predictions and walking decisions. Label 2017Q3 as July–August only and recognise seasonal confounding.

## Prespecified triggers and response

- Service unavailable for one minute or server errors: inspect containers, requests and database; use manual handling.
- Lost prediction persistence: investigate PostgreSQL and reconcile structured logs. Do not claim complete database coverage during an outage.
- p95 above 250ms for five minutes: inspect connection overhead, CPU and serialised model contention. This is a coursework booking-response budget, not an industry SLA.
- Weekly expected/observed outside 0.85–1.15: review calibration if the week has at least 30 bookings and 20 observed cancellations. Lower-volume groups are inconclusive, not a pass. The volume guard is a rough noise safeguard, not a statistical confidence guarantee.
- PSI 0.10: investigate; PSI at least 0.25: action review. Inspect seasonality, missing/unknown codes and source changes before considering retraining.

Prometheus rules display pending/firing alerts. No email, Slack or external notification delivery is configured. Historical quality alerts are explicitly labelled historical replay. Before relying on them operationally, a scheduled matured-outcome ingestion/report job is required; the final-state CSV is only a demonstration source.

## Retraining plan

Revenue manager and model owner review mature quality weekly and seasonal drift monthly. Confirm data provenance, availability and label maturity first. Propose recalibration or seasonal retraining only using the notebook's permitted learner and past mature data. Hold a separate validation quarter for policy choice, record versions and costs, and run the later Stage 8 quality gate before promotion. Require manager approval and retain the previous model/manual no-overbooking fallback. Do not use this monitoring replay to tune on the frozen 2017 holdout, automatically retrain on an alert, or silently promote a model. Refit evaluation, registry promotion and `make ci` are later stages.

## Performance experiment

Use a fixed 1,000-booking source fixture and seed, two hotel populations, twenty warmups and an open-loop offered burst of five requests/second for sixty seconds. Repeat sixty seconds with lead times changed to `min(1000, 2*lead_time+30)` to demonstrate input drift while service behaviour can remain healthy. Eight client workers allow requests to overlap; five-second timeouts and queued time count in results. This represents a sustained group-entry stress envelope, not the hotels' normal daily demand or a proven production maximum. Store exact client p50/p95/p99, errors, per-hotel p95 and database IDs. Check every successful measured response's ID in PostgreSQL and verify that Prometheus reveals the deliberate input shift. Warmups are logged but excluded from percentile calculations.

Measurements apply to this two-CPU ARM64 Ubuntu VM with 4GB allocated memory and the full four-container stack. They do not establish a public-server SLA. Model-serving calculations and approvals remain unchanged.
