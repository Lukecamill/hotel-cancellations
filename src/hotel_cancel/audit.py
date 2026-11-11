"""Count Task 19 data quirks without cleaning or changing the baseline."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd
from sklearn.model_selection import train_test_split

from hotel_cancel.config import load_config
from hotel_cancel.data import get_raw, load_bookings, separate_outcome
from hotel_cancel.evaluate import split_masks
from hotel_cancel.features import build_features, select_top_agents


def duplicate_overlap(frame, left, right):
    """Count distinct full-row signatures appearing on both sides of a split."""
    signatures = pd.util.hash_pandas_object(frame, index=False)
    return len(set(signatures.loc[left]) & set(signatures.loc[right]))


def quirk_counts(df):
    """Input is the unmodified CSV frame, before notebook normalisation."""
    cancelled = df.is_canceled.eq(1)
    portuguese = df.country.eq("PRT")
    offline = df.market_segment.eq("Offline TA/TO")
    non_ref_city = df.hotel.eq("City Hotel") & df.deposit_type.eq("Non Refund")
    status_label = df.reservation_status.isin(["Canceled", "No-Show"]).astype(int)
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "outcome_status_label_matches": int(status_label.eq(df.is_canceled).sum()),
        "no_shows": int(df.reservation_status.eq("No-Show").sum()),
        "exact_duplicate_extra_rows": int(df.duplicated().sum()),
        "offline_cancelled": int((offline & cancelled).sum()),
        "offline_cancelled_prt": int((offline & cancelled & portuguese).sum()),
        "offline_arrived": int((offline & ~cancelled).sum()),
        "offline_arrived_prt": int((offline & ~cancelled & portuguese).sum()),
        "city_non_refund": int(non_ref_city.sum()),
        "city_non_refund_cancelled": int((non_ref_city & cancelled).sum()),
        "adr_negative": int(df.adr.lt(0).sum()),
        "adr_zero": int(df.adr.eq(0).sum()),
        "adr_max": float(df.adr.max()),
        "country_blank": int(df.country.isna().sum()),
        "country_CN": int(df.country.eq("CN").sum()),
        "country_CHN": int(df.country.eq("CHN").sum()),
        "no_guests": int((df.adults + df.children.fillna(0) + df.babies).eq(0).sum()),
        "no_nights": int((df.stays_in_weekend_nights + df.stays_in_week_nights).eq(0).sum()),
    }


def run_audit(config, *, project_root):
    root = Path(project_root).resolve()
    source = get_raw("hotel_bookings.csv", config)
    df = pd.read_csv(source, na_values=["NULL"])
    counts = quirk_counts(df)
    train, test = train_test_split(df.index, test_size=0.3, random_state=config["seed"], stratify=df.is_canceled)
    counts["random_split_shared_row_signatures"] = duplicate_overlap(df, train, test)
    raw = load_bookings(config, use_cache=False)
    bk, outcome = separate_outcome(raw)
    masks = split_masks(bk, config)
    counts["temporal_train_test_shared_row_signatures"] = duplicate_overlap(
        raw.drop(columns="booked"), masks["train"], masks["test"]
    )
    X = build_features(bk, select_top_agents(bk, masks["train"]))
    forbidden = {
        "is_canceled",
        "reservation_status",
        "status_date",
        "country",
        "assigned_room_type",
        "booking_changes",
        "required_car_parking_spaces",
        "total_of_special_requests",
        "days_in_waiting_list",
    }
    assert not forbidden.intersection(X.columns), "Forbidden feature in baseline"
    assert not set(outcome.columns).intersection(bk.columns), "Outcome frame separation failed"
    assert counts["temporal_train_test_shared_row_signatures"] == 0, "Duplicate across train/test"
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    report = {
        "base_commit": revision,
        "working_tree_dirty": dirty,
        "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dataset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "seed": config["seed"],
        "counts": counts,
        "checks": {
            "forbidden_feature_names_absent": True,
            "outcome_frame_separated": True,
            "temporal_duplicate_overlap_zero": True,
        },
    }
    output = root / "docs/evidence"
    output.mkdir(parents=True, exist_ok=True)
    (output / "data-quirks.json").write_text(json.dumps(report, indent=2) + "\n")
    c = counts
    rows = [
        (
            "Outcome leakage",
            "Status reproduces the label; 1,207 no-shows",
            f"{c['outcome_status_label_matches']:,}/{c['rows']:,} status-label matches; {c['no_shows']:,} no-shows",
            "Status would reveal the answer rather than predict it",
            "Separate outcome frame; excluded from features; audit assertion and feature-mutation test",
        ),
        (
            "Duplicates",
            "31,994 extra duplicate rows",
            f"{c['exact_duplicate_extra_rows']:,} extra rows; {c['random_split_shared_row_signatures']:,} distinct signatures shared by random train/test; {c['temporal_train_test_shared_row_signatures']} shared by temporal train/test",
            "Random splitting lets copies of the same booking pattern appear on both sides; duplicates may represent blocks",
            "Forward split retained; audit fails if full-row signatures cross train/test; do not blindly deduplicate",
        ),
        (
            "Nationality artefact",
            "Offline cancelled bookings about 98% PRT; arrivals about 24%",
            f"Cancelled: {c['offline_cancelled_prt']:,}/{c['offline_cancelled']:,} ({100 * c['offline_cancelled_prt'] / c['offline_cancelled']:.2f}%); arrived: {c['offline_arrived_prt']:,}/{c['offline_arrived']:,} ({100 * c['offline_arrived_prt'] / c['offline_arrived']:.2f}%)",
            "Association supports concern about final-state completion; it does not prove when nationality was recorded",
            "Country excluded; feature-mutation test guards exclusion; timestamp provenance still needed",
        ),
        (
            "Non Refund paradox",
            "About 99.8% of City non-refundable bookings cancel",
            f"{c['city_non_refund_cancelled']:,}/{c['city_non_refund']:,} ({100 * c['city_non_refund_cancelled'] / c['city_non_refund']:.2f}%)",
            "Deposit code is not a guarantee of arrival; interpreting blocks requires care",
            "Count reported; no business rule forcing cancellation probability to zero; block analysis pending",
        ),
        (
            "ADR anomalies",
            "One negative, 1,959 zeros, maximum EUR5,400",
            f"{c['adr_negative']} negative; {c['adr_zero']:,} zero; maximum EUR{c['adr_max']:,.0f}",
            "Averages may distort room-value decisions; free rooms cannot all be treated as revenue",
            "Counting logic tested; baseline ADR unchanged; policy median/negative-ADR safeguards pending policy packaging",
        ),
        (
            "Dirty country codes",
            "488 blanks; CN beside CHN",
            f"{c['country_blank']} blanks; CN {c['country_CN']:,}; CHN {c['country_CHN']:,}",
            "Vocabulary inconsistency affects knowledge-base mapping",
            "Counts reported; loader maps blanks to unknown; code normalisation/SHACL pending",
        ),
        (
            "Invalid guest/stay combinations",
            "180 no guests; 715 no nights",
            f"{c['no_guests']} no guests; {c['no_nights']} no nights",
            "Some rows need an explicit acceptance or quarantine decision",
            "Counts tested and reported; raw-data contract and quarantine policy pending",
        ),
    ]
    lines = [
        "# Counted data quirks",
        "",
        "Generated by `python -m hotel_cancel.audit` from the supplied CSV; no rows were removed or corrected.",
        "",
        f"Baseline commit: `{revision}`. Audit working tree dirty: `{dirty}`. See the JSON companion for dataset and audit-source SHA-256 hashes. New audit changes require their own commit before submission.",
        "",
        "| Quirk | Notebook claim | Measured result | Consequence | Guard or remaining work |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines += [
        "",
        "Random overlap counts distinct complete-row signatures, not extra duplicate rows. Exact duplicates do not prove shared group identity. No cleaning, new learner, tuning or policy change was made.",
        "",
        "This is initial counted evidence for the diary, not completion of C1/C2: the full raw-data contract, six-trap suite, historical as-of reconstruction and horizon/policy checks remain pending.",
    ]
    (output / "data-quirks.md").write_text("\n".join(lines) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    result = run_audit(load_config(project_root=args.project_root), project_root=args.project_root)
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
