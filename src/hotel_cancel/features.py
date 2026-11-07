"""The supplied booking-time feature recipe; no new features."""
import pandas as pd

BOOKING_INPUTS = "hotel lead_time arrival booked stays_in_weekend_nights stays_in_week_nights adults children babies meal market_segment distribution_channel reserved_room_type deposit_type customer_type is_repeated_guest previous_cancellations previous_bookings_not_canceled agent company adr".split()
FEATURE_COLUMNS = "hotel lead_time arrival_month arrival_dow booked_dow weekend_nights week_nights adults children babies meal market_segment distribution_channel reserved_room_type deposit_type customer_type is_repeated_guest previous_cancellations previous_bookings_not_canceled agent has_company adr".split()



def select_top_agents(bookings, train_mask):
    return bookings.loc[train_mask, "agent"].value_counts().index[:60]


def build_features(bk: pd.DataFrame, top_agents) -> pd.DataFrame:
    # Make forbidden raw inputs unavailable even under a derived feature name.
    bk = bk.loc[:, BOOKING_INPUTS]
    X = pd.DataFrame(index=bk.index)
    X["hotel"] = bk.hotel
    X["lead_time"] = bk.lead_time
    X["arrival_month"] = bk.arrival.dt.month
    X["arrival_dow"] = bk.arrival.dt.day_of_week
    X["booked_dow"] = bk.booked.dt.day_of_week
    X["weekend_nights"], X["week_nights"] = bk.stays_in_weekend_nights, bk.stays_in_week_nights
    X["adults"], X["children"], X["babies"] = bk.adults, bk.children, bk.babies
    for c in ["meal", "market_segment", "distribution_channel", "reserved_room_type", "deposit_type", "customer_type"]:
        X[c] = bk[c]
    X["is_repeated_guest"] = bk.is_repeated_guest
    X["previous_cancellations"] = bk.previous_cancellations
    X["previous_bookings_not_canceled"] = bk.previous_bookings_not_canceled
    X["agent"] = pd.Categorical(bk.agent.astype(str).where(bk.agent.isin(top_agents), "other"))
    X["has_company"] = (bk.company != "none").astype(int)
    X["adr"] = bk.adr
    if list(X.columns) != FEATURE_COLUMNS:
        raise ValueError("Booking-time feature schema changed")
    return X
