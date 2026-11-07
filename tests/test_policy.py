"""Analytical checks of correlated releases and the operating point."""
import numpy as np
from hotel_cancel.policy import released_distribution, oversell


def test_two_room_block_cannot_release_only_one_room():
    np.testing.assert_allclose(released_distribution(np.array([0.25]), np.array([2])), [.75, 0, .25])


def test_independent_rooms_have_partial_release_probability():
    np.testing.assert_allclose(released_distribution(np.array([.5, .5]), np.array([1, 1])), [.25, .5, .25])


def test_walk_cost_changes_optimal_quantity_and_ties_choose_smallest():
    dist = np.array([.2, .3, .5])
    assert oversell(dist, 100, 400) == 0
    assert oversell(dist, 100, 100) == 1
    assert oversell(dist, 400, 100) == 2
