import pandas as pd
import pytest
from hotel_cancel.contracts import RAW_COLUMNS


@pytest.fixture
def valid_raw():
    row = dict.fromkeys(RAW_COLUMNS, 0)
    row.update(
        hotel="City Hotel",
        arrival_date_year=2016,
        arrival_date_month="February",
        arrival_date_day_of_month=29,
        arrival_date_week_number=9,
        lead_time=7,
        adults=2,
        stays_in_week_nights=1,
        adr=100.0,
        meal="BB",
        country="PRT",
        market_segment="Direct",
        distribution_channel="Direct",
        reserved_room_type="A",
        assigned_room_type="A",
        deposit_type="No Deposit",
        customer_type="Transient",
        reservation_status="Check-Out",
        reservation_status_date="2016-03-01",
    )
    return pd.DataFrame([row])
