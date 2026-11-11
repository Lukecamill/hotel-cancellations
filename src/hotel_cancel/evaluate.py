"""Notebook forward splits, per-hotel metrics and diagnostic gate."""

import hashlib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


def split_masks(bk, config):
    return {
        "train": bk.arrival < config["train_end"],
        "valid": (bk.arrival >= config["train_end"]) & (bk.arrival < config["valid_end"]),
        "test": (bk.arrival >= config["valid_end"]) & (bk.arrival < config["test_end"]),
    }


def per_hotel(p, mask, bk, y, hotels):
    """AUPRC, ROC-AUC, base rate and expected ÷ realised cancellations for each hotel."""
    yv, hv, rows = y[mask].values, bk.loc[mask, "hotel"].astype(str).values, {}
    for h in hotels + ["both (pooled)"]:
        s = (hv == h) if h in hotels else np.ones(len(yv), bool)
        if s.sum() and yv[s].sum():
            rows[h] = {
                "AUPRC": average_precision_score(yv[s], p[s]),
                "ROC-AUC": roc_auc_score(yv[s], p[s]),
                "base rate": yv[s].mean(),
                "expected ÷ realised": p[s].sum() / yv[s].sum(),
            }
    return pd.DataFrame(rows).T


def holdout_fingerprint(X, y, mask):
    holdout = pd.concat([X.loc[mask], y[mask]], axis=1)
    return hashlib.sha256(pd.util.hash_pandas_object(holdout, index=True).values.tobytes()).hexdigest()


def diagnostic_gate(metrics, config):
    gate = metrics.loc[config["hotels"], ["AUPRC", "expected ÷ realised"]].copy()
    gate["AUPRC ≥"] = [config["gate_min_auprc"][h] for h in config["hotels"]]
    gate["AUPRC ok"] = gate.AUPRC >= gate["AUPRC ≥"]
    gate["calibration ok"] = gate["expected ÷ realised"].between(*config["calibration_band"])
    gate["gate"] = np.where(gate["AUPRC ok"] & gate["calibration ok"], "PASS", "FAIL")
    return gate


def guard_temporal_splits(raw, masks):
    """Reject overlapping, out-of-order, incomplete or duplicated partitions."""
    if not raw.index.is_unique:
        raise ValueError("Raw rows need unique indexes")
    for name, mask in masks.items():
        if not mask.index.equals(raw.index) or mask.dtype != bool:
            raise ValueError(f"{name}: invalid split mask")
    membership = sum(mask.astype(int) for mask in masks.values())
    if not membership.eq(1).all():
        raise ValueError("Partitions must cover each row exactly once")
    signatures = pd.util.hash_pandas_object(raw.drop(columns=["booked"], errors="ignore"), index=False)
    names = ["train", "valid", "test"]
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            a, b = masks[left], masks[right]
            if a.any() and b.any() and raw.loc[a, "arrival"].max() >= raw.loc[b, "arrival"].min():
                raise ValueError(f"{left}/{right}: split is not strictly forward in time")
            if set(signatures[a]) & set(signatures[b]):
                raise ValueError(f"{left}/{right}: duplicate rows straddle partitions")
    return True
