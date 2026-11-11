"""Business invariants across generated cancellation forecasts and room blocks."""

import numpy as np
import pandas as pd
from hypothesis import given, settings, strategies as st

from hotel_cancel.policy import released_distribution, oversell, night_room_value

probability = st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False)
blocks = st.lists(st.tuples(probability, st.integers(1, 8)), min_size=1, max_size=12)


@settings(max_examples=200, deadline=None)
@given(blocks)
def test_room_release_distribution_is_valid_and_has_correct_expectation(items):
    p = np.array([item[0] for item in items])
    n = np.array([item[1] for item in items])
    distribution = released_distribution(p, n)
    assert len(distribution) == n.sum() + 1
    assert np.isfinite(distribution).all()
    assert (distribution >= 0).all()
    np.testing.assert_allclose(distribution.sum(), 1, atol=1e-12)
    np.testing.assert_allclose(distribution @ np.arange(len(distribution)), p @ n, atol=1e-10)


@settings(max_examples=200, deadline=None)
@given(blocks, st.floats(0, 5000), st.floats(1, 5000), st.floats(1, 5000))
def test_higher_walk_cost_never_increases_extra_rooms(items, empty_cost, cost_a, cost_b):
    p = np.array([item[0] for item in items])
    n = np.array([item[1] for item in items])
    distribution = released_distribution(p, n)
    low, high = sorted((cost_a, cost_b))
    q_low = oversell(distribution, empty_cost, low)
    q_high = oversell(distribution, empty_cost, high)
    assert 0 <= q_high <= q_low <= n.sum()


@settings(max_examples=200, deadline=None)
@given(st.lists(st.floats(-1000, 10000), min_size=1, max_size=30), st.floats(0, 5000), st.floats(0, 5000))
def test_room_value_is_nonnegative_and_falls_as_variable_cost_increases(prices, cost_a, cost_b):
    bookings = pd.DataFrame({"adr": prices})
    low, high = sorted((cost_a, cost_b))
    assert 0 <= night_room_value(bookings, high) <= night_room_value(bookings, low)
