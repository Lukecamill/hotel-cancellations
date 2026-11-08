-- Immutable dataset-derived snapshots. Exact duplicate source bookings remain
-- separate entries with synthetic row IDs in payload.bookings.
CREATE TABLE IF NOT EXISTS hotel_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    decision_date DATE NOT NULL,
    lead_days INTEGER NOT NULL CHECK (lead_days BETWEEN 0 AND 14),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Coursework-only nightly manager review and immutable final decision.
CREATE TABLE IF NOT EXISTS hotel_policy_reviews (
    review_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hotel_policy_decisions (
    review_id TEXT PRIMARY KEY REFERENCES hotel_policy_reviews(review_id),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Stage 7 operational prediction and batch logs; monitoring reports are replay-labelled.
CREATE TABLE IF NOT EXISTS hotel_predictions (
    prediction_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hotel TEXT NOT NULL,
    model_version TEXT NOT NULL,
    horizon TEXT NOT NULL,
    probability DOUBLE PRECISION NOT NULL CHECK (probability BETWEEN 0 AND 1),
    inputs JSONB NOT NULL,
    source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hotel_monitoring_reports (
    report_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hotel_batch_logs (
    run_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
