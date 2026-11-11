"""Narrow cross-platform comparison for the fixed nightly policy CSV schema."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLUMNS = [
    "hotel",
    "night",
    "policy",
    "q",
    "expected",
    "released",
    "walked",
    "empty",
    "cost",
]
EXPECTED_ABSOLUTE_TOLERANCE = Decimal("1e-12")


def compare_nightly_csv(reference, actual):
    def read(path):
        with Path(path).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        if not rows or rows[0] != COLUMNS:
            raise ValueError("Nightly CSV schema differs")
        if any(len(row) != len(COLUMNS) for row in rows[1:]):
            raise ValueError("Malformed nightly CSV row")
        return rows[1:]

    left, right = read(reference), read(actual)
    if len(left) != len(right):
        raise ValueError("Nightly CSV row count differs")
    changed = 0
    maximum = Decimal(0)
    for row, (a, b) in enumerate(zip(left, right), start=2):
        for column, x, y in zip(COLUMNS, a, b):
            if column != "expected":
                if x != y:
                    raise ValueError(f"Nightly CSV {column} differs at row {row}")
                continue
            try:
                xx, yy = Decimal(x), Decimal(y)
            except InvalidOperation as error:
                raise ValueError("Invalid expected probability sum") from error
            if not xx.is_finite() or not yy.is_finite():
                raise ValueError("Nonfinite expected probability sum")
            delta = abs(xx - yy)
            maximum = max(maximum, delta)
            if delta > EXPECTED_ABSOLUTE_TOLERANCE:
                raise ValueError(f"Nightly CSV expected differs beyond 1e-12 at row {row}")
            changed += int(x != y)
    return dict(
        status="PASS",
        rows=len(left),
        all_other_columns_exact=True,
        changed_expected_cells=changed,
        maximum_absolute_expected_difference=float(maximum),
        expected_absolute_tolerance=float(EXPECTED_ABSOLUTE_TOLERANCE),
    )


AGGREGATE_FLOAT_COLUMNS = {"multirow_share", "mean_forecast_walk_probability"}


def compare_aggregate_table(reference, actual):
    """Only two declared diagnostic ratios may differ at floating precision."""
    with Path(actual).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    columns = reference["columns"]
    expected = reference["rows"]
    if not rows or rows[0] != columns or len(rows) - 1 != len(expected):
        raise ValueError("Aggregate CSV schema or row count differs")
    maximum = Decimal(0)
    changed = 0
    for number, (left, right) in enumerate(zip(expected, rows[1:]), start=2):
        if len(right) != len(columns):
            raise ValueError("Malformed aggregate CSV row")
        for column, a, b in zip(columns, left, right):
            if a == b:
                continue
            if column not in AGGREGATE_FLOAT_COLUMNS:
                raise ValueError(f"Aggregate {column} differs at row {number}")
            try:
                x, y = Decimal(a), Decimal(b)
            except InvalidOperation as error:
                raise ValueError("Invalid aggregate numeric value") from error
            if not x.is_finite() or not y.is_finite():
                raise ValueError("Nonfinite aggregate numeric value")
            delta = abs(x - y)
            maximum = max(maximum, delta)
            if delta > EXPECTED_ABSOLUTE_TOLERANCE:
                raise ValueError(f"Aggregate {column} differs beyond 1e-12")
            changed += 1
    return dict(
        status="PASS",
        rows=len(expected),
        all_counts_costs_and_labels_exact=True,
        changed_diagnostic_ratio_cells=changed,
        maximum_diagnostic_ratio_difference=float(maximum),
        absolute_tolerance=1e-12,
    )
