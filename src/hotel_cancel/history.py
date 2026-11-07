"""Retrospective day-resolution reconstruction, not an event-sourced PMS."""
import pandas as pd


def reconstruct_as_of(bookings, outcome, lead_days):
    if type(lead_days) is not int or not 0 <= lead_days <= 14:
        raise ValueError('lead_days must be an integer in 0..14')
    if not bookings.index.equals(outcome.index) or not bookings.index.is_unique:
        raise ValueError('Booking/outcome rows must have identical unique ordered indexes')
    decision = bookings.arrival - pd.Timedelta(days=lead_days)
    # Same-day entries excluded; same-day cancellations remain live and late.
    live = (bookings.booked < decision) & ((outcome.is_canceled == 0) | (outcome.status_date >= decision))
    late = ((outcome.is_canceled == 1) & (outcome.status_date >= decision)).astype(int)
    return decision, live, late
