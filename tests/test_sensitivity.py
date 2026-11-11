import itertools
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from hotel_cancel.sensitivity import (
    check_grid,
    choose_quantity,
    effective_room_value,
    select_winners,
    run_sensitivity,
)
from hotel_cancel.policy import released_distribution


def test_quantile_minimises_expected_cost():
    for walk, variable, resale in itertools.product([100, 250, 500], [0, 20, 40], [0, 0.25, 1]):
        d = released_distribution(np.array([0.2, 0.4]), np.array([2, 1]))
        room = effective_room_value(120, variable, resale)
        k = np.arange(len(d))
        costs = [walk * (np.maximum(q - k, 0) @ d) + room * (np.maximum(k - q, 0) @ d) for q in k]
        assert choose_quantity(d, room, walk) == int(np.argmin(costs))


def test_resale_and_cost_monotonicity():
    d = released_distribution(np.array([0.4, 0.7]), np.array([2, 3]))
    assert choose_quantity(d, 80, 100) >= choose_quantity(d, 80, 500)
    assert effective_room_value(10, 20, 0.5) == 0
    assert choose_quantity(d, effective_room_value(120, 20, 1), 250) == 0


def test_blocks_preserve_mean_increase_variance():
    grouped = released_distribution(np.array([0.3]), np.array([4]))
    independent = released_distribution(np.full(4, 0.3), np.ones(4, int))
    k = np.arange(5)
    assert grouped @ k == pytest.approx(independent @ k)
    assert grouped @ (k * k) > independent @ (k * k)


def test_selection_tie_prefers_no_overbooking():
    s = pd.DataFrame(
        [
            dict(
                lead_days=7,
                walk_cost_eur=250,
                variable_cost_eur=20,
                resale_rate=0,
                hotel="City Hotel",
                policy=p,
                cost_per_night=10,
            )
            for p in ["model", "no overbooking"]
        ]
    )
    assert select_winners(s).policy.iat[0] == "no overbooking"


def test_test_period_rejected():
    b = SimpleNamespace(bookings=pd.DataFrame({"arrival": [pd.Timestamp("2017-01-01")]}))
    grid = dict(
        lead_days=[7],
        walk_costs_eur=[250],
        variable_costs_eur=[20],
        resale_rates=[0],
        recal_weeks=[4],
    )
    with pytest.raises(ValueError, match="frozen test"):
        run_sensitivity(b, {"valid_end": pd.Timestamp("2017-01-01")}, grid)


@pytest.mark.parametrize(
    "key,value",
    [
        ("lead_days", [15]),
        ("walk_costs_eur", [0]),
        ("resale_rates", [1.1]),
        ("recal_weeks", [0]),
        ("variable_costs_eur", [float("nan")]),
    ],
)
def test_invalid_grid(key, value):
    grid = dict(
        lead_days=[7],
        walk_costs_eur=[250],
        variable_costs_eur=[20],
        resale_rates=[0],
        recal_weeks=[4],
    )
    grid[key] = value
    with pytest.raises(ValueError):
        check_grid(grid)


def test_calibration_and_rolling_features_ignore_unmatured_labels():
    from hotel_cancel.policy import prepare_policy

    dates = pd.date_range("2016-07-01", "2016-12-31")
    bk = pd.DataFrame({"arrival": np.repeat(dates, 4)})
    bk["hotel"] = np.tile(["City Hotel", "City Hotel", "Resort Hotel", "Resort Hotel"], len(dates))
    bk["booked"] = bk.arrival - pd.Timedelta(days=40)
    for key in [
        "market_segment",
        "distribution_channel",
        "deposit_type",
        "agent",
        "company",
        "reserved_room_type",
        "customer_type",
        "meal",
    ]:
        bk[key] = "A"
    bk["adr"], bk["adults"], bk["children"] = 100.0, 2, 0
    bk["stays_in_weekend_nights"], bk["stays_in_week_nights"] = 0, 1
    out = pd.DataFrame({"is_canceled": np.tile([0, 1, 0, 1], len(dates)), "status_date": bk.arrival})
    b = SimpleNamespace(
        bookings=bk,
        outcome=out,
        probabilities=np.tile([0.2, 0.8, 0.2, 0.8], len(dates)),
    )
    cfg = dict(
        decision_lead_days=14,
        train_end=pd.Timestamp("2016-07-01"),
        calib_end=pd.Timestamp("2016-10-01"),
        valid_end=pd.Timestamp("2017-01-01"),
        test_end=pd.Timestamp("2017-09-01"),
        window_start=pd.Timestamp("2016-07-01"),
        window_end=pd.Timestamp("2017-09-01"),
        recal_weeks_grid=[4, 8, 12],
        hotels=["City Hotel", "Resort Hotel"],
        walk_cost_eur=250,
        variable_cost_eur=20,
        tonight=pd.Timestamp("2017-08-08"),
    )
    cutoff = cfg["calib_end"] - pd.Timedelta(days=15)
    snap1, _, _, cal1, _ = prepare_policy(b, cfg, fit_end=cutoff)
    # Mutate labels not yet mature at the first selection decision.
    changed = out.copy()
    changed.loc[bk.arrival >= cutoff, "is_canceled"] = 1 - changed.loc[bk.arrival >= cutoff, "is_canceled"]
    b.outcome = changed
    snap2, _, _, cal2, _ = prepare_policy(b, cfg, fit_end=cutoff)
    for hh in cfg["hotels"]:
        np.testing.assert_array_equal(cal1[hh].model.coef_, cal2[hh].model.coef_)
    fields = [
        "p_cal",
        "relevel_4",
        "relevel_8",
        "relevel_12",
        "rate_4",
        "rate_8",
        "rate_12",
    ]
    first1 = snap1.loc[snap1.arrival == cfg["calib_end"], fields]
    first2 = snap2.loc[snap2.arrival == cfg["calib_end"], fields]
    pd.testing.assert_frame_equal(first1, first2)
