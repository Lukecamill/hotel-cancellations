"""Immutable, simulated nightly decisions; no connection to a channel manager."""

from datetime import datetime, timezone
import hashlib
import json

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb
import psycopg

from hotel_cancel.batch import nightly_batch
from hotel_cancel.snapshot import read_postgres


class DecisionConflict(ValueError):
    pass


def validate_decision(request, candidate):
    if not isinstance(request, dict) or set(request) != {
        "decision",
        "quantity",
        "reviewer",
        "reason",
        "simulation_acknowledged",
    }:
        raise ValueError("Provide decision, quantity, reviewer, reason and simulation_acknowledged")
    if request["simulation_acknowledged"] is not True:
        raise ValueError("Acknowledge that this is a coursework simulation")
    for key, limit in [("reviewer", 120), ("reason", 2000)]:
        if not isinstance(request[key], str) or not request[key].strip() or len(request[key]) > limit:
            raise ValueError(f"{key} is required and must be at most {limit} characters")
    q, decision = request["quantity"], request["decision"]
    if type(q) is not int or not 0 <= q <= candidate:
        raise ValueError("Approved quantity must be an integer from zero to the recommendation")
    if decision == "approve" and q != candidate:
        raise ValueError("Approval must use the recommended quantity; choose reduce otherwise")
    if decision == "reduce" and not q < candidate:
        raise ValueError("Reduction must be below the recommended quantity")
    if decision == "reject" and q != 0:
        raise ValueError("Rejection must approve zero rooms")
    if decision not in ("approve", "reduce", "reject"):
        raise ValueError("Choose approve, reduce or reject")
    return dict(request, reviewer=request["reviewer"].strip(), reason=request["reason"].strip())


class ApprovalStore:
    def __init__(self, database_url):
        self.database_url = database_url
        with self.connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS hotel_policy_reviews (
                review_id TEXT PRIMARY KEY, payload JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            c.execute("""CREATE TABLE IF NOT EXISTS hotel_policy_decisions (
                review_id TEXT PRIMARY KEY REFERENCES hotel_policy_reviews(review_id),
                payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    def connect(self):
        return psycopg.connect(self.database_url, connect_timeout=10)

    def publish(self, snapshot_id, predictor):
        snapshot = read_postgres(snapshot_id, self.database_url)
        batch = nightly_batch(snapshot, predictor)
        cfg = predictor.policy["config"]
        ids = []
        with self.connect() as c:
            for result in batch["results"]:
                payload = dict(
                    schema_version=1,
                    simulation=True,
                    snapshot_id=batch["snapshot_id"],
                    decision_date=batch["decision_date"],
                    arrival=batch["arrival"],
                    lead_days=batch["lead_days"],
                    model_version=batch["model_version"],
                    policy_version=batch["policy_version"],
                    walk_cost_eur=cfg["walk_cost_eur"],
                    variable_cost_eur=cfg["variable_cost_eur"],
                    resale_rate=0,
                    recommendation=result,
                )
                encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
                identifier = hashlib.sha256(encoded.encode()).hexdigest()
                c.execute(
                    "INSERT INTO hotel_policy_reviews (review_id,payload) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (identifier, Jsonb(payload)),
                )
                ids.append(identifier)
        return ids

    def list_reviews(self):
        with self.connect() as c:
            rows = c.execute("""SELECT r.review_id,r.payload,d.payload FROM hotel_policy_reviews r
                                LEFT JOIN hotel_policy_decisions d USING (review_id)
                                ORDER BY r.created_at DESC,r.review_id""").fetchall()
        return [
            dict(
                review_id=identifier,
                **payload,
                decision=decision,
                review_status="pending" if decision is None else decision["decision"],
                simulated_approved_quantity=0 if decision is None else decision["quantity"],
                operational_authorised_oversell=0,
            )
            for identifier, payload, decision in rows
        ]

    def decide(self, identifier, request):
        try:
            with self.connect() as c:
                row = c.execute(
                    "SELECT payload FROM hotel_policy_reviews WHERE review_id=%s",
                    (identifier,),
                ).fetchone()
                if row is None:
                    raise KeyError("Review not found")
                request = validate_decision(request, row[0]["recommendation"]["candidate_oversell"])
                decision = dict(
                    request,
                    review_id=identifier,
                    simulation=True,
                    approved_at_utc=datetime.now(timezone.utc).isoformat(),
                    snapshot_id=row[0]["snapshot_id"],
                    model_version=row[0]["model_version"],
                    policy_version=row[0]["policy_version"],
                    hotel=row[0]["recommendation"]["hotel"],
                )
                c.execute(
                    "INSERT INTO hotel_policy_decisions (review_id,payload) VALUES (%s,%s)",
                    (identifier, Jsonb(decision)),
                )
            return decision
        except UniqueViolation:
            raise DecisionConflict(
                "This recommendation already has a final decision; it cannot be overwritten"
            ) from None
