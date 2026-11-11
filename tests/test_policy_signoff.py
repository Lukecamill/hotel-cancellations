import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    "signoff",
    Path(__file__).resolve().parents[1] / "scripts/record_simulation_signoff.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record():
    return dict(
        packet_sha256="reviewed",
        reviewer="Test reviewer",
        reason="Coursework simulation review",
        decision="approve_simulation",
        production_authorized=False,
        max_authorized_extra_rooms=0,
        reviewer_role="coursework simulation reviewer",
    )


def test_simulation_has_no_live_authority():
    assert module.validate_record(record(), "reviewed")["production_authorized"] is False


def test_changed_packet_needs_new_approval():
    with pytest.raises(ValueError, match="packet changed"):
        module.validate_record(record(), "edited")


def test_simulation_cannot_authorize_live_extra_rooms():
    r = record()
    r["max_authorized_extra_rooms"] = 1
    with pytest.raises(ValueError, match="live authority"):
        module.validate_record(r, "reviewed")
