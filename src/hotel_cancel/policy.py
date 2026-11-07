"""Given notebook policy, extracted from cells 14–17 without changing the method.

Notebook globals become local configuration/state; only display and plots are removed.
"""
from dataclasses import dataclass
import time
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from hotel_cancel.history import reconstruct_as_of

@dataclass
class PolicyForecast:
    probabilities: object
    block_sizes: object
    lead_days: int

    def __iter__(self):
        yield self.probabilities
        yield self.block_sizes


@dataclass
class HorizonCalibrator:
    lead_days: int
    model: object

    def predict(self, booking_probabilities, *, lead_days):
        if lead_days != self.lead_days:
            raise ValueError('Calibration horizon does not match decision horizon; refit on validation data')
        return self.model.predict_proba(logit(booking_probabilities).to_frame('z'))[:, 1]


def night_room_value(bookings, variable_cost):
    """Given median ADR rule, floored at zero; never use a global average."""
    return max(bookings.adr.median() - variable_cost, 0.0)


@dataclass
class PolicyResult:
    snapshot: pd.DataFrame
    calibrators: dict
    flat_rates: dict
    chosen: dict
    selection: pd.DataFrame
    nights: pd.DataFrame
    summary: pd.DataFrame
    tonight: dict
    runtime_seconds: float

def logit(p):
    p = np.clip(p, 0.0001, 1 - 0.0001)
    return np.log(p / (1 - p))

def released_distribution(p, n):
    """P(k rooms released) when block i holds n_i rooms and cancels, as one, with probability p_i."""
    dist = np.zeros(int(n.sum()) + 1)
    dist[0] = 1.0
    for pi, ni in zip(p, n):
        nxt = dist * (1 - pi)
        nxt[ni:] += dist[:len(dist) - ni] * pi
        dist = nxt
    return dist

def oversell(dist, empty_cost, walk_cost=250.0):
    """Newsvendor: the smallest q with P(released ≤ q) ≥ empty / (empty + walk)."""
    return int(np.searchsorted(np.cumsum(dist), empty_cost / (empty_cost + walk_cost) - 1e-12))

def run_policies(nights, policies, empty_cost_fn, eval_cost_fn=None, *, block_agg, walk_cost, decision_lead_days):
    """Decide q per night with empty_cost_fn; cost the night with eval_cost_fn (the night's true room value)."""
    eval_cost_fn = eval_cost_fn or empty_cost_fn
    rows = []
    for (hh, night), g in nights.groupby(['hotel', 'arrival']):
        b = g.groupby('block').agg(**block_agg)
        Rd, R, X_ = (empty_cost_fn(g), eval_cost_fn(g), int(g.y.sum()))
        for name, fn in policies.items():
            q, expected = (0, 0.0)
            if fn is not None:
                forecast = fn(g, b)
                if not isinstance(forecast, PolicyForecast) or forecast.lead_days != decision_lead_days:
                    raise ValueError("Policy requires probabilities calibrated/estimated for its decision horizon")
                p, n = forecast
                p = np.asarray(p, dtype=float)
                if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
                    raise ValueError('Decision probabilities must be finite values in [0, 1]')
                if n is None:
                    if len(p) != len(g):
                        raise ValueError('One probability is required per live booking')
                else:
                    sizes = np.asarray(n)
                    if sizes.shape != p.shape or (sizes <= 0).any() or (sizes % 1 != 0).any() or sizes.sum() != len(g):
                        raise ValueError('Block sizes must account for every live booking exactly once')
                dist = released_distribution(p, np.ones(len(p), int) if n is None else n)
                q, expected = (oversell(dist, Rd, walk_cost), float(dist @ np.arange(len(dist))))
            rows.append({'hotel': hh, 'night': night, 'policy': name, 'q': q, 'expected': expected, 'released': X_, 'walked': max(q - X_, 0), 'empty': max(X_ - q, 0), 'cost': walk_cost * max(q - X_, 0) + R * max(X_ - q, 0)})
    return pd.DataFrame(rows)

def summarise(pol):
    t = pol.groupby(['hotel', 'policy'], sort=False).agg(oversold=('q', 'mean'), expected=('expected', 'mean'), came_back=('released', 'mean'), walked=('walked', 'mean'), empty=('empty', 'mean'), cost_per_night=('cost', 'mean'), cost_total=('cost', 'sum'))
    none = t.xs('no overbooking', level='policy').cost_total
    t['saving vs none (€)'] = none.reindex(t.index.get_level_values(0)).values - t.cost_total.values
    return t.drop(columns='cost_total')

def run_policy_baseline(baseline, config):
    """Calibrate Jul–Sep, choose Oct–Dec, report frozen 2017 policies."""
    started = time.perf_counter()
    snap, POLICIES, BLOCK_AGG, PLATT, FLAT_RATE = prepare_policy(baseline, config)
    CALIB_END, VALID_END, TEST_END = (config[k] for k in ('calib_end', 'valid_end', 'test_end'))
    HOTELS, WALK_COST_EUR = config['hotels'], config['walk_cost_eur']
    RECAL_WEEKS_GRID, TONIGHT, h = config['recal_weeks_grid'], config['tonight'], config['decision_lead_days']
    night_cost = lambda g: night_room_value(g, config['variable_cost_eur'])

    select_nights = snap[(snap.arrival >= CALIB_END) & (snap.arrival < VALID_END)]
    sel = summarise(run_policies(select_nights, POLICIES, night_cost, block_agg=BLOCK_AGG, walk_cost=WALK_COST_EUR, decision_lead_days=h))
    CHOSEN = {hh: sel.loc[hh].cost_per_night.idxmin() for hh in HOTELS}
    sel['chosen'] = ['◀' if CHOSEN[hh] == p_ else '' for hh, p_ in sel.index]
    test_nights = snap[(snap.arrival >= VALID_END) & (snap.arrival < TEST_END)]
    pol = pd.concat([run_policies(test_nights[test_nights.hotel == hh], {'no overbooking': None, CHOSEN[hh]: POLICIES[CHOSEN[hh]]}, night_cost, block_agg=BLOCK_AGG, walk_cost=WALK_COST_EUR, decision_lead_days=h) for hh in HOTELS])
    night = TONIGHT + pd.Timedelta(days=h)
    tonight_rows = {}
    for hh in HOTELS:
        g = snap[(snap.hotel == hh) & (snap.arrival == night)]
        b = g.groupby('block').agg(**BLOCK_AGG)
        fn = POLICIES[CHOSEN[hh]] or POLICIES[f'model + blocks + re-level {RECAL_WEEKS_GRID[1]} wk']
        p, n = fn(g, b)
        dist = released_distribution(p, np.ones(len(p), int) if n is None else n)
        R = night_cost(g)
        k = np.arange(len(dist))
        qs = np.arange(0, 16)
        exp_cost = [WALK_COST_EUR * (np.clip(q - k, 0, None) @ dist) + R * (np.clip(k - q, 0, None) @ dist) for q in qs]
        q_star = oversell(dist, R, WALK_COST_EUR) if POLICIES[CHOSEN[hh]] is not None else 0
        tonight_rows[hh] = {'policy': CHOSEN[hh], 'on the books': len(g), 'rooms in blocks': int(g.groupby('block').size().pipe(lambda s_: s_[s_ > 1].sum())), 'expected releases': float(dist @ k), 'P(no release)': dist[0], 'empty-room cost €': R, 'oversell q*': q_star, 'P(walk anyone)': float(dist[:q_star].sum()), 'cost of q*±1 vs q*': max(exp_cost[max(q_star - 1, 0)], exp_cost[q_star + 1]) - exp_cost[q_star], 'released (hindsight)': int(g.y.sum())}

    return PolicyResult(snap, PLATT, FLAT_RATE, CHOSEN, sel, pol, summarise(pol), tonight_rows, time.perf_counter() - started)


def prepare_policy(baseline, config, *, fit_end=None):
    """Build horizon-specific forecasts; optional earlier calibration cutoff for causal selection."""
    DECISION_LEAD_DAYS = config["decision_lead_days"]
    TRAIN_END = config["train_end"]
    CALIB_END = config["calib_end"]
    VALID_END = config["valid_end"]
    TEST_END = config["test_end"]
    WINDOW_START = config["window_start"]
    WINDOW_END = config["window_end"]
    RECAL_WEEKS_GRID = config["recal_weeks_grid"]
    HOTELS = config["hotels"]
    WALK_COST_EUR = config["walk_cost_eur"]
    VARIABLE_COST_EUR = config["variable_cost_eur"]
    TONIGHT = config["tonight"]
    bk, outcome, p_all = baseline.bookings, baseline.outcome, baseline.probabilities
    fit_end = config["calib_end"] if fit_end is None else pd.Timestamp(fit_end)
    h = DECISION_LEAD_DAYS
    decision, on_books, late = reconstruct_as_of(bk, outcome, h)
    GROUP_KEY = ['hotel', 'arrival', 'booked', 'market_segment', 'distribution_channel', 'deposit_type', 'agent', 'company', 'reserved_room_type', 'customer_type', 'meal', 'adults', 'children', 'adr', 'stays_in_weekend_nights', 'stays_in_week_nights']
    snap = bk.loc[on_books, ['hotel', 'arrival', 'adr', 'market_segment', 'deposit_type', 'agent']].copy()
    snap['hotel'] = snap.hotel.astype(str)
    snap['y'], snap['p_booking'] = (late[on_books], p_all[on_books.values])
    snap['block'] = bk.loc[on_books].groupby(GROUP_KEY, observed=True, dropna=False).ngroup()
    snap['p_cal'] = np.nan
    PLATT, FLAT_RATE = ({}, {})
    for hh in HOTELS:
        s = snap.hotel == hh
        v = s & (snap.arrival >= TRAIN_END) & (snap.arrival < fit_end)
        PLATT[hh] = HorizonCalibrator(h, LogisticRegression().fit(logit(snap.loc[v, 'p_booking']).to_frame('z'), snap.loc[v, 'y']))
        snap.loc[s, 'p_cal'] = PLATT[hh].predict(snap.loc[s, 'p_booking'], lead_days=h)
        FLAT_RATE[hh] = snap.loc[v, 'y'].mean()
    nightly = snap.groupby(['hotel', 'arrival']).agg(y=('y', 'sum'), p=('p_cal', 'sum'), n=('y', 'size'))
    keys = pd.MultiIndex.from_arrays([snap.hotel, snap.arrival])
    for w in RECAL_WEEKS_GRID:
        trail = {}
        for hh in HOTELS:
            d = nightly.loc[hh].reindex(pd.date_range(WINDOW_START, WINDOW_END - pd.Timedelta(days=1)), fill_value=0)
            r = d.rolling(7 * w, min_periods=7).sum().shift(h + 1)
            trail[hh] = pd.DataFrame({'factor': r.y / r.p, 'rate': r.y / r.n})
        trail = pd.concat(trail, names=['hotel', 'arrival']).replace([np.inf, -np.inf], np.nan)
        snap[f'relevel_{w}'] = trail.factor.reindex(keys).fillna(1.0).values
        snap[f'rate_{w}'] = trail.rate.reindex(keys).values
    POLICIES = {'no overbooking': None, 'flat rate (Jul – Sep 2016)': lambda g, b: (np.full(len(g), FLAT_RATE[g.hotel.iat[0]]), None), **{f'flat rate (trailing {w} wk)': lambda g, b, w=w: (np.full(len(g), g[f'rate_{w}'].iat[0]), None) for w in RECAL_WEEKS_GRID}, 'model': lambda g, b: (g.p_cal.values, None), 'model + blocks': lambda g, b: (b.p.values, b.n.values), **{f'model + blocks + re-level {w} wk': lambda g, b, w=w: (np.clip(b.p.values * b[f'f_{w}'].values, 0, 1), b.n.values) for w in RECAL_WEEKS_GRID}}
    # Explicit metadata keeps booking-time probabilities out of the decision API.
    POLICIES = {name: (None if fn is None else (lambda g, b, fn=fn: PolicyForecast(*fn(g, b), h))) for name, fn in POLICIES.items()}
    BLOCK_AGG = {'p': ('p_cal', 'mean'), 'n': ('p_cal', 'size'), **{f'f_{w}': (f'relevel_{w}', 'first') for w in RECAL_WEEKS_GRID}}
    night_cost = lambda g: night_room_value(g, VARIABLE_COST_EUR)

    return snap, POLICIES, BLOCK_AGG, PLATT, FLAT_RATE
