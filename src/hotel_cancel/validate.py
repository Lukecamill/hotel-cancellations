"""Generate counted Stage 4 data/leakage evidence without fitting a learner."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from hotel_cancel.audit import duplicate_overlap, quirk_counts
from hotel_cancel.config import load_config
from hotel_cancel.contracts import validate_raw, RAW_COLUMNS, NULLABLE, INTEGER_COLUMNS
from hotel_cancel.data import get_raw, load_bookings, separate_outcome
from hotel_cancel.evaluate import split_masks, guard_temporal_splits
from hotel_cancel.features import build_features, select_top_agents
from hotel_cancel.history import reconstruct_as_of


def run_checks(config, output):
    root = Path(__file__).resolve().parents[2]
    source = get_raw("hotel_bookings.csv", config)
    csv = pd.read_csv(source, na_values=["NULL"])
    contract = validate_raw(csv)
    raw = load_bookings(config, use_cache=False)
    bk, outcome = separate_outcome(raw)
    masks = split_masks(bk, config)
    guard_temporal_splits(raw, masks)
    top_agents = select_top_agents(bk, masks["train"])
    features = build_features(bk, top_agents)
    poisoned = bk.copy(deep=True)
    forbidden = [
        "is_canceled",
        "reservation_status",
        "status_date",
        "country",
        "assigned_room_type",
        "booking_changes",
        "required_car_parking_spaces",
        "total_of_special_requests",
        "days_in_waiting_list",
    ]
    for name in forbidden:
        poisoned[name] = np.arange(len(bk)) % 2
    pd.testing.assert_frame_equal(features, build_features(poisoned, top_agents), check_exact=True)
    counts = quirk_counts(csv)
    left, right = train_test_split(csv.index, test_size=0.3, random_state=config["seed"], stratify=csv.is_canceled)
    counts["random_split_shared_signatures"] = duplicate_overlap(csv, left, right)
    counts["forward_train_test_shared_signatures"] = duplicate_overlap(raw, masks["train"], masks["test"])
    counts["forward_train_valid_vs_test_shared_signatures"] = duplicate_overlap(
        raw, masks["train"] | masks["valid"], masks["test"]
    )
    later = {
        "room_changed": bk.assigned_room_type.astype(str).ne(bk.reserved_room_type.astype(str)),
        **{
            c: bk[c].gt(0)
            for c in [
                "booking_changes",
                "required_car_parking_spaces",
                "total_of_special_requests",
                "days_in_waiting_list",
            ]
        },
    }
    counts["post_booking_positive_rows"] = {k: int(v.sum()) for k, v in later.items()}
    counts["parking_positive_cancelled"] = int(outcome.is_canceled[later["required_car_parking_spaces"]].sum())
    horizons = {}
    for horizon in range(15):
        decision, live, late = reconstruct_as_of(bk, outcome, horizon)
        assert (bk.booked[live] < decision[live]).all()
        cancelled = live & outcome.is_canceled.eq(1)
        assert (outcome.status_date[cancelled] >= decision[cancelled]).all()
        horizons[str(horizon)] = {
            hotel: {
                "live": int((live & bk.hotel.eq(hotel)).sum()),
                "late": int(late[live & bk.hotel.eq(hotel)].sum()),
            }
            for hotel in config["hotels"]
        }
    source_paths = list((root / "src/hotel_cancel").glob("*.py")) + list((root / "tests").glob("*.py"))
    report = {
        "status": "passed",
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()
        ),
        "dataset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_sha256": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_paths)
        },
        "contract": contract,
        "counts": counts,
        "asof_horizons": horizons,
        "checks": {
            "raw_contract": True,
            "forward_splits_and_duplicate_isolation": True,
            "outcome_separation": not bool(set(outcome) & set(bk)),
            "forbidden_input_mutation_preserves_features": True,
            "asof_membership_invariants_0_to_14_days": True,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "data-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    schema = {
        "version": contract["contract_version"],
        "columns": RAW_COLUMNS,
        "nullable": sorted(NULLABLE),
        "nonnegative_integer_columns": sorted(INTEGER_COLUMNS),
        "adr": "finite numeric; negatives/zeros/outliers accepted and counted",
        "failure_action": "reject entire batch before transformation/training; preserve original file; no silent row removal",
    }
    (output / "raw-contract.json").write_text(json.dumps(schema, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--output")
    args = parser.parse_args()
    config = load_config(args.config)
    output = Path(args.output) if args.output else Path(__file__).resolve().parents[2] / "docs/evidence/stage4"
    report = run_checks(config, output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "contract": report["contract"],
                "counts": report["counts"],
                "evidence": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
