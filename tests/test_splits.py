import pandas as pd
import pytest
from hotel_cancel.evaluate import guard_temporal_splits


def fixture():
    raw = pd.DataFrame(
        {
            "arrival": pd.to_datetime(["2016-01-01", "2016-08-01", "2017-02-01"]),
            "adr": [100, 100, 100],
        }
    )
    masks = {name: pd.Series([j == i for j in range(3)]) for i, name in enumerate(["train", "valid", "test"])}
    return raw, masks


def test_forward_partitions_pass():
    raw, masks = fixture()
    assert guard_temporal_splits(raw, masks)


@pytest.mark.parametrize("problem", ["overlap", "omitted", "random", "duplicate"])
def test_bad_partitions_fail(problem):
    raw, masks = fixture()
    if problem == "overlap":
        masks["train"].iloc[2] = True
    if problem == "omitted":
        masks["test"].iloc[2] = False
    if problem == "random":
        masks["train"], masks["test"] = masks["test"], masks["train"]
    if problem == "duplicate":
        raw.iloc[2] = raw.iloc[0]
    with pytest.raises(ValueError):
        guard_temporal_splits(raw, masks)
