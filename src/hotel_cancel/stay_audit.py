"""Diary 1 additional quirk: compare Check-Out status dates with recorded stay ends.

Diagnostic only: no filtering, relabelling, feature construction or model changes.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd

from hotel_cancel.config import load_config
from hotel_cancel.contracts import MONTHS, validate_raw
from hotel_cancel.data import get_raw


def checkout_date_checks(raw):
    arrival = pd.to_datetime(
        dict(
            year=raw.arrival_date_year,
            month=raw.arrival_date_month.map(MONTHS),
            day=raw.arrival_date_day_of_month,
        )
    )
    status = pd.to_datetime(raw.reservation_status_date)
    nights = raw.stays_in_weekend_nights + raw.stays_in_week_nights
    derived_end = arrival + pd.to_timedelta(nights, unit="D")
    checkout = raw.reservation_status.eq("Check-Out")
    return pd.DataFrame(
        dict(
            arrival=arrival,
            recorded_nights=nights,
            status_date=status,
            derived_stay_end=derived_end,
            status_date_gap_days=(status - arrival).dt.days,
            checkout_date_mismatch=checkout & status.ne(derived_end),
            same_day_checkout_positive_nights=checkout & status.eq(arrival) & nights.gt(0),
        ),
        index=raw.index,
    )


def run(config):
    source = get_raw("hotel_bookings.csv", config)
    raw = pd.read_csv(source, na_values=["NULL"])
    validate_raw(raw)
    checks = checkout_date_checks(raw)
    flag = checks.checkout_date_mismatch
    rows = []
    for split, lower, upper in [
        ("train", config["window_start"], config["train_end"]),
        ("validation", config["train_end"], config["valid_end"]),
        ("test", config["valid_end"], config["test_end"]),
    ]:
        for hotel in config["hotels"]:
            scope = raw.hotel.eq(hotel) & checks.arrival.ge(lower) & checks.arrival.lt(upper)
            rows.append(
                dict(
                    hotel=hotel,
                    split=split,
                    rows=int(scope.sum()),
                    check_out_rows=int((scope & raw.reservation_status.eq("Check-Out")).sum()),
                    mismatches=int((scope & flag).sum()),
                    same_day_positive_nights=int((scope & checks.same_day_checkout_positive_nights).sum()),
                )
            )
    root = Path(__file__).resolve().parents[2]
    note = root / "notebooks/reference/19_hotel_cancellations.ipynb"
    report = dict(
        raw_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        notebook_sha256=hashlib.sha256(note.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()),
        counts=dict(
            rows=len(raw),
            check_out_rows=int(raw.reservation_status.eq("Check-Out").sum()),
            mismatches=int(flag.sum()),
            distinct_flagged_rows=len(raw.loc[flag].drop_duplicates()),
            same_day_positive_nights=int(checks.same_day_checkout_positive_nights.sum()),
            zero_nights_among_flagged=int(checks.loc[flag, "recorded_nights"].eq(0).sum()),
            zero_guests_among_flagged=int(
                (raw.loc[flag, "adults"] + raw.loc[flag, "children"].fillna(0) + raw.loc[flag, "babies"]).eq(0).sum()
            ),
            minimum_recorded_nights=int(checks.loc[flag, "recorded_nights"].min()),
            maximum_recorded_nights=int(checks.loc[flag, "recorded_nights"].max()),
        ),
        by_hotel_and_split=rows,
        exploratory_negative_checks=dict(
            cancel_status_before_inferred_booking=int(
                (
                    raw.is_canceled.eq(1)
                    & checks.status_date.lt(checks.arrival - pd.to_timedelta(raw.lead_time, unit="D"))
                ).sum()
            ),
            cancel_status_after_arrival=int((raw.is_canceled.eq(1) & checks.status_date.gt(checks.arrival)).sum()),
        ),
        source_definition="ReservationStatusDate is the date the last status was set; stay fields describe stayed or booked-to-stay nights.",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/",
        interpretation="Cross-field discrepancy for review, not proof of corruption or cancellation. Causes are not identifiable from this CSV.",
        safeguard="Count and flag offline; preserve rows and labels; never use outcome dates in booking-time features or infer realised occupancy/revenue from this relation alone.",
    )
    output = root / "docs/evidence/diary1"
    output.mkdir(parents=True, exist_ok=True)
    (output / "additional-quirk.json").write_text(json.dumps(report, indent=2) + "\n")
    pd.DataFrame(rows).to_csv(output / "additional-quirk-counts.csv", index=False)
    local = root / "artifacts/diary1"
    local.mkdir(parents=True, exist_ok=True)
    raw.loc[flag].join(checks.loc[flag]).to_csv(
        local / "checkout-date-discrepancies.csv", index_label="source_row_index"
    )
    print(json.dumps(report["counts"], indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config")
    args = p.parse_args()
    run(load_config(args.config))


if __name__ == "__main__":
    main()
