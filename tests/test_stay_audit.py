import pandas as pd

from hotel_cancel.stay_audit import checkout_date_checks


def test_expected_checkout_matches_stay_including_weekends(valid_raw):
    raw = valid_raw.copy()
    raw["stays_in_weekend_nights"] = 2
    raw["stays_in_week_nights"] = 3
    raw["reservation_status_date"] = "2016-03-05"
    result = checkout_date_checks(raw)
    assert not result.checkout_date_mismatch.iat[0]
    assert result.recorded_nights.iat[0] == 5


def test_same_day_checkout_positive_stay_is_flagged_without_changing_label(valid_raw):
    raw = valid_raw.copy()
    raw["stays_in_week_nights"] = 7
    raw["reservation_status_date"] = "2016-02-29"
    before = raw.copy(deep=True)
    result = checkout_date_checks(raw)
    assert result.checkout_date_mismatch.iat[0]
    assert result.same_day_checkout_positive_nights.iat[0]
    assert raw.is_canceled.iat[0] == 0
    pd.testing.assert_frame_equal(raw, before)


def test_shorter_checkout_is_flagged_and_cancelled_booking_is_not_checkout(valid_raw):
    raw = pd.concat([valid_raw] * 2, ignore_index=True)
    raw["stays_in_week_nights"] = 9
    raw["reservation_status_date"] = ["2016-03-01", "2016-02-28"]
    raw.loc[1, "reservation_status"] = "Canceled"
    raw.loc[1, "is_canceled"] = 1
    result = checkout_date_checks(raw)
    assert result.checkout_date_mismatch.tolist() == [True, False]
    assert not result.same_day_checkout_positive_nights.any()


def test_valid_zero_night_checkout_is_not_this_additional_quirk(valid_raw):
    raw = valid_raw.copy()
    raw["stays_in_week_nights"] = 0
    raw["reservation_status_date"] = "2016-02-29"
    result = checkout_date_checks(raw)
    assert not result.checkout_date_mismatch.iat[0]
    assert not result.same_day_checkout_positive_nights.iat[0]
