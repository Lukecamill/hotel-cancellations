"""Checks for configuration precedence and portable path handling."""
from pathlib import Path

import pytest
import yaml

from hotel_cancel.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in ("CONFIG_PATH", "DATASETS_TASKS_DATA", "MODEL_DIR", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/config.yaml").write_text((ROOT / "config/config.yaml").read_text())
    return tmp_path


def test_paths_are_independent_of_working_directory(project, tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    config = load_config(project_root=project)
    assert config["raw_dir"] == project / "data/raw/hotel_bookings"
    assert config["decision_lead_days"] == 7
    assert not config["data_dir"].exists()  # loading has no directory side effects


def test_shell_beats_dotenv_beats_yaml(project, monkeypatch):
    (project / ".env").write_text("DATASETS_TASKS_DATA=local-data\nMODEL_DIR=local-models\nLOG_LEVEL=DEBUG\n")
    assert load_config(project_root=project)["data_dir"] == project / "local-data"
    monkeypatch.setenv("DATASETS_TASKS_DATA", "shell-data")
    config = load_config(project_root=project)
    assert config["data_dir"] == project / "shell-data"
    assert config["model_dir"] == project / "local-models"
    assert config["log_level"] == "DEBUG"
    assert "MODEL_DIR" not in __import__("os").environ


def test_explicit_config_beats_environment(project, monkeypatch):
    monkeypatch.setenv("CONFIG_PATH", "missing.yaml")
    assert load_config("config/config.yaml", project_root=project)["seed"] == 3217


@pytest.mark.parametrize("key,value", [("decision_lead_days", 15), ("train_end", "2018-01-01"), ("walk_cost_eur", -1), ("recal_weeks_grid", [0]), ("gate_min_auprc", {"City Hotel": 0.7}), ("calibration_band", [1.2, 0.8])])
def test_invalid_settings_fail_early(project, key, value):
    path = project / "config/config.yaml"
    config = yaml.safe_load(path.read_text())
    config[key] = value
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError):
        load_config(project_root=project)
