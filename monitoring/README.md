# Hotel monitoring stack

The root `compose.yaml` starts Prometheus and Grafana with the API and PostgreSQL.
All published ports are on localhost; use SSH tunnels when Docker runs in Ubuntu.

- Prometheus: `prom/prometheus:v3.13.4`, five-second scrape/evaluation interval.
- Grafana: `grafana/grafana:13.2.4`, provisioned Prometheus datasource and eight-panel dashboard.
- Dashboard UID: `hotel-monitoring`; dashboard JSON is the source of truth.
- Grafana anonymous role: Viewer. There is no public admin interface.
- Alert rules are displayed in Prometheus; no external notification receiver is configured.

API request/input metrics are live counters and histograms. `hotel_replay_*` metrics
are explicitly historical dataset diagnostics. Do not infer current cancellation
quality from the service load generator. The lead-time histogram input is in days;
Grafana may display larger durations in weeks. Its p95 is a histogram-bucket
estimate; the load report contains exact sample percentiles, including client
queueing from each scheduled request arrival.

Read `docs/stage7-monitoring.md` and ADR 0008 for reproduction, thresholds, label
maturity, retention and the retraining response. Installing the Python project
requires `prometheus-client==0.26.0`, pinned in both full and serving requirements.
