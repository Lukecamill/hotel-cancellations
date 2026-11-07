"""Unchanged LightGBM learner and parameters from notebook cell 10."""
from pathlib import Path
import joblib
import lightgbm as lgb


def model_parameters(seed):
    return dict(n_estimators=300, learning_rate=0.06, num_leaves=31, min_child_samples=50, subsample=0.8,
                  subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, random_state=seed, verbose=-1,
                  n_jobs=1)


def fit(cols, train, X_, y, *, seed):
    return lgb.LGBMClassifier(**model_parameters(seed)).fit(X_.loc[train, cols], y[train])


def save_model(model, path, *, top_agents, feature_columns):
    """Persist learned preprocessing state with the model for later scoring."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "top_agents": top_agents,
                 "feature_columns": feature_columns}, path)


def predict_bookings(bookings, bundle):
    from hotel_cancel.features import build_features
    X = build_features(bookings, bundle["top_agents"])
    return bundle["model"].predict_proba(X[bundle["feature_columns"]])[:, 1]
