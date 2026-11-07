"""Feature-boundary checks; the full six-trap suite is a later task."""
import pandas as pd
from hotel_cancel.features import build_features, select_top_agents


def bookings():
    frame = pd.DataFrame({
        "hotel": ["City Hotel", "Resort Hotel"],
        "arrival": pd.to_datetime(["2016-06-01", "2017-01-01"]),
        "booked": pd.to_datetime(["2016-05-01", "2016-12-01"]),
        "lead_time": [31, 31], "stays_in_weekend_nights": [1, 2],
        "stays_in_week_nights": [2, 3], "adults": [2, 1], "children": [0, 1],
        "babies": [0, 0], "meal": ["BB", "HB"], "market_segment": ["Direct", "Groups"],
        "distribution_channel": ["Direct", "TA/TO"], "reserved_room_type": ["A", "B"],
        "deposit_type": ["No Deposit", "Non Refund"], "customer_type": ["Transient", "Contract"],
        "is_repeated_guest": [0, 1], "previous_cancellations": [0, 1],
        "previous_bookings_not_canceled": [0, 2], "agent": ["1", "2"],
        "company": ["none", "7"], "adr": [90., 120.],
    })
    for col in frame.select_dtypes("str"):
        frame[col] = frame[col].astype("category")
    return frame


def test_agent_vocabulary_uses_only_training_rows():
    bk = bookings()
    # Pandas categories can include unused agents with zero count, matching the
    # notebook. Test exclusion using a validation-only value outside its dtype.
    bk["agent"] = bk.agent.astype(str)
    top = select_top_agents(bk, pd.Series([True, False]))
    assert list(top) == ["1"]
    assert build_features(bk, top).agent.iloc[1] == "other"


def test_features_do_not_modify_input_and_ignore_forbidden_columns():
    bk = bookings()
    before = bk.copy(deep=True)
    original = build_features(bk, ["1"])
    pd.testing.assert_frame_equal(bk, before)
    for col in ["is_canceled", "reservation_status", "status_date", "country",
                "assigned_room_type", "booking_changes", "required_car_parking_spaces",
                "total_of_special_requests", "days_in_waiting_list"]:
        bk[col] = ["forbidden-a", "forbidden-b"]
    pd.testing.assert_frame_equal(build_features(bk, ["1"]), original)


def test_outcome_separation_and_only_allowed_inputs_available():
    from hotel_cancel.data import separate_outcome, OUTCOME
    from hotel_cancel.features import BOOKING_INPUTS, FEATURE_COLUMNS
    bk=bookings()
    bk['is_canceled']=[0,1];bk['reservation_status']=['Check-Out','Canceled']
    bk['status_date']=pd.to_datetime(['2016-06-02','2016-12-15'])
    raw=bk.copy(deep=True);inputs,outcomes=separate_outcome(raw)
    assert set(outcomes)==set(OUTCOME)
    assert not set(OUTCOME)&set(inputs)
    assert list(build_features(inputs,["1"]).columns)==FEATURE_COLUMNS
    # A frame containing only approved raw inputs is sufficient: no nationality,
    # assigned room, changes, parking, requests, waiting time or outcome needed.
    pd.testing.assert_frame_equal(build_features(inputs[BOOKING_INPUTS],["1"]),build_features(inputs,["1"]))
    pd.testing.assert_frame_equal(raw,bk)


import pytest


@pytest.mark.parametrize('forbidden',['is_canceled','reservation_status','status_date','country',
    'assigned_room_type','booking_changes','required_car_parking_spaces','total_of_special_requests','days_in_waiting_list'])
def test_each_forbidden_input_cannot_change_any_feature_even_under_an_alias(forbidden):
    bk=bookings();expected=build_features(bk,['1'])
    bk[forbidden]=['first','second']
    pd.testing.assert_frame_equal(build_features(bk,['1']),expected,check_exact=True)
    bk[forbidden]=['second','first']
    pd.testing.assert_frame_equal(build_features(bk,['1']),expected,check_exact=True)
