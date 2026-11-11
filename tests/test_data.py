import pandas as pd
import pytest
from hotel_cancel.data import load_bookings
from hotel_cancel.contracts import DataContractError


def config_at(tmp_path):
    return {
        "raw_dir": tmp_path / "raw",
        "processed_dir": tmp_path / "processed",
        "window_start": pd.Timestamp("2015-07-01"),
        "window_end": pd.Timestamp("2017-09-01"),
    }


def test_cache_is_rebuilt_after_raw_change_and_tampering(tmp_path, valid_raw):
    config = config_at(tmp_path)
    config["raw_dir"].mkdir()
    path = config["raw_dir"] / "hotel_bookings.csv"
    valid_raw.to_csv(path, index=False)
    first = load_bookings(config, use_cache=True)
    pd.testing.assert_frame_equal(first, load_bookings(config, use_cache=True))
    valid_raw["adr"] = 222.0
    valid_raw.to_csv(path, index=False)
    second = load_bookings(config, use_cache=True)
    assert second.adr.iloc[0] == 222.0
    cache = config["processed_dir"] / "19_hotel_bookings.parquet"
    altered = second.copy()
    altered["adr"] = 999.0
    altered.to_parquet(cache)
    assert load_bookings(config, use_cache=True).adr.iloc[0] == 222.0
    # A malformed metadata document also forces reconstruction.
    cache.with_suffix(".json").write_text("[]")
    assert load_bookings(config, use_cache=True).adr.iloc[0] == 222.0


def test_cache_never_bypasses_raw_contract(tmp_path, valid_raw):
    config = config_at(tmp_path)
    config["raw_dir"].mkdir()
    path = config["raw_dir"] / "hotel_bookings.csv"
    valid_raw.to_csv(path, index=False)
    load_bookings(config, use_cache=True)
    valid_raw["adults"] = -1
    valid_raw.to_csv(path, index=False)
    with pytest.raises(DataContractError):
        load_bookings(config, use_cache=True)
