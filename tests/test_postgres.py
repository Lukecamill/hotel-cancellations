"""Opt-in real PostgreSQL round trip: TEST_DATABASE_URL must point to a test database."""

import os

import pytest

from hotel_cancel.snapshot import read_postgres, seal_snapshot, write_postgres


def test_postgres_snapshot_roundtrip():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL integration")
    snapshot = seal_snapshot(
        dict(
            schema_version=1,
            decision_date="2017-08-08",
            lead_days=7,
            bookings=[],
            history=[],
            test_fixture="stage6-roundtrip",
        )
    )
    write_postgres(snapshot, url)
    write_postgres(snapshot, url)  # Idempotent; duplicates are preserved inside the payload.
    assert read_postgres(snapshot["snapshot_id"], url) == snapshot
    with pytest.raises(ValueError, match="not found"):
        read_postgres("missing' OR 1=1 --", url)
