-- Immutable dataset-derived snapshots. Exact duplicate source bookings remain
-- separate entries with synthetic row IDs in payload.bookings.
CREATE TABLE IF NOT EXISTS hotel_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    decision_date DATE NOT NULL,
    lead_days INTEGER NOT NULL CHECK (lead_days BETWEEN 0 AND 14),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
