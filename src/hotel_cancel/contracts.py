"""Versioned raw CSV contract: fail on structural errors, report known anomalies."""
import numpy as np
import pandas as pd

CONTRACT_VERSION = 'hotel-bookings-raw-v1'
RAW_COLUMNS = '''hotel is_canceled lead_time arrival_date_year arrival_date_month arrival_date_week_number arrival_date_day_of_month stays_in_weekend_nights stays_in_week_nights adults children babies meal country market_segment distribution_channel is_repeated_guest previous_cancellations previous_bookings_not_canceled reserved_room_type assigned_room_type booking_changes deposit_type agent company days_in_waiting_list customer_type adr required_car_parking_spaces total_of_special_requests reservation_status reservation_status_date'''.split()
NULLABLE = {'children', 'country', 'agent', 'company'}
CODES = {'hotel', 'arrival_date_month', 'meal', 'country', 'market_segment', 'distribution_channel', 'reserved_room_type', 'assigned_room_type', 'deposit_type', 'customer_type', 'reservation_status'}
INTEGER_COLUMNS = set(RAW_COLUMNS) - CODES - {'adr', 'reservation_status_date'}
MONTHS = {m: i for i, m in enumerate('January February March April May June July August September October November December'.split(), 1)}


class DataContractError(ValueError):
    pass


def validate_raw(df):
    """Return counted anomalies without modifying rows; reject invalid batches."""
    errors = []
    missing, extra = set(RAW_COLUMNS) - set(df), set(df) - set(RAW_COLUMNS)
    if missing or extra or df.columns.duplicated().any():
        raise DataContractError(f'Unexpected schema: missing={sorted(missing)}, extra={sorted(extra)}, duplicate_columns={df.columns.duplicated().any()}')
    if df.empty:
        errors.append('empty batch')
    for col in RAW_COLUMNS:
        if col not in NULLABLE and df[col].isna().any():
            errors.append(f'{col}: required values missing')
    for col in INTEGER_COLUMNS | {'adr'}:
        if not pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f'{col}: expected numeric dtype')
        values = pd.to_numeric(df[col], errors='coerce')
        invalid = (df[col].notna() & values.isna()) | (values.notna() & ~np.isfinite(values))
        if invalid.any():
            errors.append(f'{col}: non-numeric/non-finite value')
        if col in INTEGER_COLUMNS and ((values.dropna() < 0).any() or (values.dropna() % 1 != 0).any()):
            errors.append(f'{col}: expected non-negative integers')
    for col in CODES:
        if (~df[col].dropna().map(lambda v: isinstance(v, str) and bool(v.strip()))).any():
            errors.append(f'{col}: expected non-empty text codes')
    for col in ['is_canceled', 'is_repeated_guest']:
        if not df[col].isin([0, 1]).all():
            errors.append(f'{col}: expected binary values')
    for col, allowed in [('hotel', {'City Hotel', 'Resort Hotel'}), ('reservation_status', {'Canceled','Check-Out','No-Show'}), ('deposit_type', {'No Deposit','Non Refund','Refundable'})]:
        if not df[col].isin(allowed).all():
            errors.append(f'{col}: unsupported code')
    if errors:
        raise DataContractError('; '.join(errors))
    months = df.arrival_date_month.map(MONTHS)
    arrival = pd.to_datetime(pd.DataFrame({'year': df.arrival_date_year, 'month': months, 'day': df.arrival_date_day_of_month}), errors='coerce')
    if arrival.isna().any() or not arrival.between('2015-07-01','2017-08-31').all():
        errors.append('arrival: invalid date or outside frozen dataset window')
    week = pd.to_numeric(df.arrival_date_week_number, errors='coerce')
    if not week.between(1,53).all():
        errors.append('arrival_date_week_number: expected 1..53')
    if not df.reservation_status_date.astype(str).str.fullmatch(r'\d{4}-\d{2}-\d{2}').all() or pd.to_datetime(df.reservation_status_date, errors='coerce', format='%Y-%m-%d').isna().any():
        errors.append('reservation_status_date: invalid ISO date')
    status_label = df.reservation_status.isin(['Canceled','No-Show']).astype(int)
    if not status_label.eq(df.is_canceled).all():
        errors.append('reservation_status: inconsistent with label')
    if errors:
        raise DataContractError('; '.join(errors))
    guests = df.adults + df.children.fillna(0) + df.babies
    nights = df.stays_in_weekend_nights + df.stays_in_week_nights
    return {'contract_version': CONTRACT_VERSION, 'rows': len(df), 'errors': [], 'anomalies': {
        'negative_adr': int(df.adr.lt(0).sum()), 'zero_adr': int(df.adr.eq(0).sum()),
        'adr_above_1000': int(df.adr.gt(1000).sum()), 'zero_guests': int(guests.eq(0).sum()),
        'zero_nights': int(nights.eq(0).sum()), 'duplicate_extra_rows': int(df.duplicated().sum()),
        'missing_children': int(df.children.isna().sum()), 'missing_country': int(df.country.isna().sum()),
        'non_alpha3_country': int((df.country.notna() & ~df.country.fillna('').str.fullmatch('[A-Z]{3}')).sum()),
        'undefined_segment': int(df.market_segment.eq('Undefined').sum()),
        'undefined_channel': int(df.distribution_channel.eq('Undefined').sum())}}
