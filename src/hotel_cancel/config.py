"""Load project settings without changing global environment or creating files."""

from pathlib import Path
import os

from dotenv import dotenv_values
import pandas as pd
import yaml

DATE_KEYS = (
    "window_start",
    "window_end",
    "train_end",
    "calib_end",
    "valid_end",
    "test_end",
    "tonight",
)
ENV_SETTINGS = {
    "DATASETS_TASKS_DATA": "data_dir",
    "MODEL_DIR": "model_dir",
    "LOG_LEVEL": "log_level",
}


def load_config(path=None, *, project_root=None):
    """Return YAML settings plus local overrides, with absolute data/model paths.

    Defaults to this source checkout. Pass project_root explicitly when using
    another project directory (for example in a container or installed wheel).
    Relative config and data paths always resolve against project_root.
    Explicit path beats CONFIG_PATH; shell beats .env; .env beats YAML.
    """
    root = (
        Path(project_root).expanduser().resolve() if project_root is not None else Path(__file__).resolve().parents[2]
    )
    env = {k: v for k, v in dotenv_values(root / ".env").items() if v is not None}
    env.update(os.environ)

    def absolute(value):
        result = Path(value).expanduser()
        return (root / result).resolve() if not result.is_absolute() else result.resolve()

    config_path = absolute(path if path is not None else env.get("CONFIG_PATH", "config/config.yaml"))
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration must be a mapping: {config_path}")
    required = set(DATE_KEYS) | {
        "seed",
        "kaggle_handle",
        "decision_lead_days",
        "walk_cost_eur",
        "variable_cost_eur",
        "recal_weeks_grid",
        "hotels",
        "gate_min_auprc",
        "calibration_band",
        "data_dir",
        "model_dir",
        "log_level",
    }
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"Missing configuration settings: {', '.join(missing)}")
    for variable, key in ENV_SETTINGS.items():
        if variable in env:
            config[key] = env[variable]
    for key in DATE_KEYS:
        config[key] = pd.Timestamp(config[key])
        if pd.isna(config[key]):
            raise ValueError(f"Invalid date: {key}")
    if not (
        config["window_start"]
        < config["train_end"]
        < config["calib_end"]
        < config["valid_end"]
        < config["test_end"]
        == config["window_end"]
    ):
        raise ValueError("Expected ordered train/calibration/validation/test boundaries within the data window")
    if type(config["seed"]) is not int or config["seed"] < 0:
        raise ValueError("seed must be a non-negative integer")
    if type(config["decision_lead_days"]) is not int or not 0 <= config["decision_lead_days"] <= 14:
        raise ValueError("decision_lead_days must be an integer from 0 to 14")
    if not config["recal_weeks_grid"] or any(type(w) is not int or w <= 0 for w in config["recal_weeks_grid"]):
        raise ValueError("recal_weeks_grid must contain positive integer weeks")
    for key in ("walk_cost_eur", "variable_cost_eur"):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value < float("inf"):
            raise ValueError(f"{key} must be a finite non-negative number")
    hotels = config["hotels"]
    if hotels != ["City Hotel", "Resort Hotel"]:
        raise ValueError("hotels must contain City Hotel and Resort Hotel in notebook order")
    gates = config["gate_min_auprc"]
    if (
        not isinstance(gates, dict)
        or set(gates) != set(hotels)
        or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in gates.values())
    ):
        raise ValueError("gate_min_auprc must contain a probability threshold for each hotel")
    band = config["calibration_band"]
    if (
        not isinstance(band, list)
        or len(band) != 2
        or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in band)
        or not 0 < band[0] <= 1 <= band[1] < float("inf")
    ):
        raise ValueError("calibration_band must be two positive finite bounds enclosing 1")
    config["log_level"] = str(config["log_level"]).upper()
    if config["log_level"] not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("Invalid log_level")
    config["data_dir"], config["model_dir"] = (
        absolute(config["data_dir"]),
        absolute(config["model_dir"]),
    )
    config["raw_dir"] = config["data_dir"] / "raw" / "hotel_bookings"
    config["processed_dir"] = config["data_dir"] / "processed"
    return config
