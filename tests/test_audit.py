"""Small examples verify audit counts without requiring the private local CSV."""

import pandas as pd
from hotel_cancel.audit import duplicate_overlap, quirk_counts


def test_duplicate_overlap_detects_copies_but_not_similar_rows():
    df = pd.DataFrame({"hotel": ["A", "A", "A"], "adr": [100, 100, 101]})
    assert duplicate_overlap(df, [0], [1, 2]) == 1
    assert duplicate_overlap(df, [0, 1], [2]) == 0


def test_quirk_counts_preserve_anomalies_and_use_correct_denominators():
    df = pd.DataFrame(
        {
            "hotel": ["City Hotel"] * 4,
            "is_canceled": [1, 0, 1, 0],
            "reservation_status": ["Canceled", "Check-Out", "No-Show", "Check-Out"],
            "country": ["PRT", "CHN", "CN", None],
            "market_segment": ["Offline TA/TO"] * 4,
            "deposit_type": ["Non Refund", "No Deposit", "Non Refund", "No Deposit"],
            "adr": [-1.0, 0.0, 5400.0, 100.0],
            "adults": [0, 1, 2, 1],
            "children": [None, 0, 0, 0],
            "babies": [0] * 4,
            "stays_in_weekend_nights": [0, 1, 0, 0],
            "stays_in_week_nights": [0, 0, 1, 2],
        }
    )
    before = df.copy(deep=True)
    c = quirk_counts(df)
    assert c["outcome_status_label_matches"] == 4
    assert c["offline_cancelled"] == 2 and c["offline_cancelled_prt"] == 1
    assert c["offline_arrived"] == 2 and c["offline_arrived_prt"] == 0
    assert c["city_non_refund"] == c["city_non_refund_cancelled"] == 2
    assert c["adr_negative"] == c["adr_zero"] == c["no_guests"] == c["no_nights"] == 1
    assert c["adr_max"] == 5400
    assert c["country_blank"] == c["country_CN"] == c["country_CHN"] == 1
    pd.testing.assert_frame_equal(df, before)
