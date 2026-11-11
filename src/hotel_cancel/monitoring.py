"""Per-service metrics and best-effort versioned prediction persistence."""

from datetime import datetime, timezone
import json
import logging
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    Gauge,
    generate_latest,
)

logger = logging.getLogger(__name__)


class Telemetry:
    def __init__(self, database_url=None):
        self.database_url = database_url
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "hotel_http_requests",
            "Completed application requests",
            ["route", "method", "status", "hotel"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "hotel_http_request_seconds",
            "Application response latency including database logging",
            ["route", "hotel"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
            registry=self.registry,
        )
        self.predictions = Counter(
            "hotel_predictions",
            "Successful booking predictions",
            ["hotel", "model_version"],
            registry=self.registry,
        )
        self.failures = Counter(
            "hotel_prediction_log_failures",
            "Predictions not persisted to PostgreSQL",
            registry=self.registry,
        )
        self.logged = Counter(
            "hotel_prediction_logs",
            "Predictions persisted to PostgreSQL",
            registry=self.registry,
        )
        self.lead = Histogram(
            "hotel_input_lead_days",
            "Observed booking lead time",
            ["hotel"],
            buckets=[0, 7, 14, 30, 60, 90, 180, 365, 730, 1000],
            registry=self.registry,
        )
        self.probability = Histogram(
            "hotel_cancellation_probability",
            "Booking-to-arrival probability",
            ["hotel"],
            buckets=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
            registry=self.registry,
        )
        self.segment = Counter(
            "hotel_input_segments",
            "Received market segment",
            ["hotel", "segment"],
            registry=self.registry,
        )
        self.report = Gauge(
            "hotel_replay_report_timestamp_seconds",
            "Latest historical replay import timestamp",
            registry=self.registry,
        )
        self.calibration = Gauge(
            "hotel_replay_calibration_ratio",
            "Historical expected/observed cancellations",
            ["hotel", "horizon"],
            registry=self.registry,
        )
        self.samples = Gauge(
            "hotel_replay_bookings",
            "Historical bookings in latest mature week",
            ["hotel", "horizon"],
            registry=self.registry,
        )
        self.observed = Gauge(
            "hotel_replay_observed_cancellations",
            "Historical observed cancellations in latest mature week",
            ["hotel", "horizon"],
            registry=self.registry,
        )
        self.psi = Gauge(
            "hotel_replay_psi",
            "Latest historical quarter PSI against training",
            ["hotel", "feature"],
            registry=self.registry,
        )
        self.cost = Gauge(
            "hotel_replay_policy_cost_eur",
            "Historical 2017 mean nightly policy cost",
            ["hotel", "policy"],
            registry=self.registry,
        )
        self.batch_seconds = Gauge(
            "hotel_last_batch_seconds",
            "Latest monitored batch duration",
            registry=self.registry,
        )
        if database_url:
            with self.connect() as c:
                c.execute("""CREATE TABLE IF NOT EXISTS hotel_predictions (
                    prediction_id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    hotel TEXT NOT NULL, model_version TEXT NOT NULL, horizon TEXT NOT NULL,
                    probability DOUBLE PRECISION NOT NULL CHECK (probability BETWEEN 0 AND 1),
                    inputs JSONB NOT NULL, source TEXT NOT NULL)""")
                c.execute("""CREATE TABLE IF NOT EXISTS hotel_monitoring_reports (
                    report_id TEXT PRIMARY KEY, payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
                c.execute("""CREATE TABLE IF NOT EXISTS hotel_batch_logs (
                    run_id TEXT PRIMARY KEY,payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    def connect(self):
        return psycopg.connect(self.database_url, connect_timeout=2)

    def prediction(self, booking, probability, version):
        hotel = booking["hotel"]
        self.predictions.labels(hotel, version).inc()
        self.lead.labels(hotel).observe(booking["lead_time"])
        self.probability.labels(hotel).observe(probability)
        # Finite known vocabulary keeps time-series cardinality bounded.
        segment = booking["market_segment"]
        if segment not in [
            "Direct",
            "Corporate",
            "Online TA",
            "Offline TA/TO",
            "Complementary",
            "Groups",
            "Aviation",
            "Undefined",
        ]:
            segment = "other"
        self.segment.labels(hotel, segment).inc()
        inputs = {
            k: booking[k]
            for k in [
                "arrival",
                "lead_time",
                "market_segment",
                "distribution_channel",
                "adr",
            ]
        }
        identifier = uuid4().hex
        record = dict(
            prediction_id=identifier,
            hotel=hotel,
            model_version=version,
            horizon="booking_to_arrival",
            probability=probability,
            inputs=inputs,
            source="online",
            logged_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        # Always emit structured output, even if database persistence is unavailable.
        logger.info(json.dumps(record, allow_nan=False))
        if not self.database_url:
            self.failures.inc()
            return identifier, False
        try:
            with self.connect() as c:
                c.execute(
                    "INSERT INTO hotel_predictions (prediction_id,hotel,model_version,horizon,probability,inputs,source) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (
                        identifier,
                        hotel,
                        version,
                        "booking_to_arrival",
                        probability,
                        Jsonb(inputs),
                        "online",
                    ),
                )
            self.logged.inc()
            return identifier, True
        except psycopg.Error:
            self.failures.inc()
            logger.error("Prediction persistence failed; prediction_id=%s", identifier)
            return identifier, False

    def refresh_reports(self):
        if not self.database_url:
            return
        try:
            with self.connect() as c:
                row = c.execute(
                    "SELECT payload FROM hotel_monitoring_reports ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                batch = c.execute("SELECT payload FROM hotel_batch_logs ORDER BY created_at DESC LIMIT 1").fetchone()
            if row:
                report = row[0]
                self.report.set(report["generated_at_epoch"])
                self.calibration.clear()
                self.observed.clear()
                self.samples.clear()
                self.psi.clear()
                self.cost.clear()
                for item in report["latest_week"]:
                    if item["ratio"] is not None:
                        self.calibration.labels(item["hotel"], item["horizon"]).set(item["ratio"])
                    self.observed.labels(item["hotel"], item["horizon"]).set(item["observed"])
                    self.samples.labels(item["hotel"], item["horizon"]).set(item["n"])
                for item in report["latest_drift"]:
                    self.psi.labels(item["hotel"], item["feature"]).set(item["psi"])
                for item in report["policy_costs"]:
                    self.cost.labels(item["hotel"], item["policy"]).set(item["cost_per_night"])
            if batch:
                self.batch_seconds.set(batch[0]["runtime_seconds"])
        except psycopg.Error:
            logger.error("Historical monitoring report unavailable")

    def render(self):
        self.refresh_reports()
        return generate_latest(self.registry)

    def observe_request(self, path, method, status, hotel, seconds):
        if path in ("/metrics", "/health"):
            return
        if path.startswith("/reviews/"):
            path = "/reviews/decision"
        elif path not in ["/predict", "/review", "/reviews", "/"]:
            path = "other"
        method = method if method in ["GET", "POST"] else "other"
        self.requests.labels(path, method, str(status), hotel).inc()
        self.latency.labels(path, hotel).observe(seconds)
