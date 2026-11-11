"""MLflow-only adapter: reuse the service's booking contract and preprocessing."""

import joblib
import mlflow.pyfunc
import pandas as pd

from hotel_cancel.features import build_features
from hotel_cancel.serving import booking_frame


class HotelBookingModel(mlflow.pyfunc.PythonModel):
    def __init__(self, hotel):
        self.hotel = hotel

    def load_context(self, context):
        self.bundle = joblib.load(context.artifacts["booking_bundle"])

    def predict(self, context, model_input, params=None):
        frame = booking_frame(model_input.to_dict(orient="records"))
        if not frame.hotel.astype(str).eq(self.hotel).all():
            raise ValueError(f"This registered model accepts {self.hotel} only")
        features = build_features(frame, self.bundle["top_agents"])
        p = self.bundle["model"].predict_proba(features[self.bundle["feature_columns"]])[:, 1]
        return pd.DataFrame({"cancellation_probability": p}, index=model_input.index)
