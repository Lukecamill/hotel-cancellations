"""Notebook data transformations, with explicit configuration."""
import hashlib
import json
import logging
import time
from pathlib import Path
import pandas as pd
from hotel_cancel.contracts import validate_raw

logger = logging.getLogger(__name__)
MONTHS = {m: i for i, m in enumerate([
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
], 1)}
OUTCOME = ["is_canceled", "reservation_status", "status_date"]

def get_raw(filename: str, config) -> Path:
    local = config["raw_dir"] / filename
    if local.exists():
        return local
    import kagglehub
    return Path(kagglehub.dataset_download(config["kaggle_handle"], path=filename))

def load_bookings(config, *, use_cache=True) -> pd.DataFrame:
    config["raw_dir"].mkdir(parents=True, exist_ok=True)
    config["processed_dir"].mkdir(parents=True, exist_ok=True)
    cache = config["processed_dir"] / "19_hotel_bookings.parquet"
    t = time.time()
    source = get_raw("hotel_bookings.csv", config)
    df = pd.read_csv(source, na_values=["NULL"])
    contract = validate_raw(df)
    logger.info("Raw contract %s accepted %s rows; anomalies: %s", contract["contract_version"], contract["rows"], contract["anomalies"])
    identity = {"raw_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "window_start": str(config["window_start"]), "window_end": str(config["window_end"]),
                "pandas": pd.__version__, "contract_version": contract["contract_version"],
                "loader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    metadata = cache.with_suffix(".json")
    if use_cache and cache.exists() and metadata.exists():
        try:
            saved = json.loads(metadata.read_text())
            if isinstance(saved, dict) and saved.get("identity") == identity and saved.get("parquet_sha256") == hashlib.sha256(cache.read_bytes()).hexdigest():
                return pd.read_parquet(cache)
        except (ValueError, OSError):
            logger.warning("Ignoring invalid cache metadata; rebuilding from validated raw input")
    df["arrival"] = pd.to_datetime(pd.DataFrame({"year": df.arrival_date_year, "day": df.arrival_date_day_of_month,
                                                 "month": df.arrival_date_month.map(MONTHS)}))
    df["booked"] = df.arrival - pd.to_timedelta(df.lead_time, unit="D")     # the day the booking entered the PMS
    df["status_date"] = pd.to_datetime(df.reservation_status_date)
    df = df[(df.arrival >= config["window_start"]) & (df.arrival < config["window_end"])]
    df = df.drop(columns=["arrival_date_year", "arrival_date_month", "arrival_date_week_number",
                          "arrival_date_day_of_month", "reservation_status_date"])
    df["children"] = df.children.fillna(0).astype(int)
    for c in ["agent", "company"]:          # pseudonymous business IDs: codes, never numbers
        df[c] = df[c].map(lambda v: "none" if pd.isna(v) else str(int(v)))
    df["country"] = df.country.fillna("unknown")
    for c in ["hotel", "meal", "country", "market_segment", "distribution_channel", "reserved_room_type",
              "assigned_room_type", "deposit_type", "customer_type", "agent", "company", "reservation_status"]:
        df[c] = df[c].astype("category")
    df = df.sort_values(["arrival", "hotel"], kind="stable").reset_index(drop=True)
    df.to_parquet(cache)
    metadata.write_text(json.dumps({"identity": identity, "parquet_sha256": hashlib.sha256(cache.read_bytes()).hexdigest()}, indent=2) + "\n")
    logger.info("Loaded and cached bookings in %.1fs", time.time() - t)
    return df


def separate_outcome(raw):
    """Keep outcome data outside the feature input frame, as in the notebook."""
    return raw.drop(columns=OUTCOME), raw[OUTCOME].copy()
