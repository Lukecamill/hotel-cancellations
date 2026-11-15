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


def copied_review(tmp_path):
    import json
    import shutil
    root = Path(__file__).resolve().parents[1]
    packet_name = 'docs/reviews/coursework-policy-review-v2.json'
    record_name = 'docs/reviews/coursework-policy-signoff-v2.json'
    packet = json.loads((root / packet_name).read_text())
    for name in [packet_name, record_name, *packet['evidence_sha256']]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
    return packet


def test_declared_ai_review_has_specific_zero_quantity_scope(tmp_path):
    copied_review(tmp_path)
    result = module.verify_saved_review(tmp_path)
    assert result['status'] == 'PASS' and result['ai_simulated'] is True
    assert result['review_outcome'] == 'accepted_with_changes'
    assert result['max_authorized_extra_rooms'] == 0


def test_editing_the_review_transcript_invalidates_signoff(tmp_path):
    import json
    copied_review(tmp_path)
    record = json.loads((tmp_path / 'docs/reviews/coursework-policy-signoff-v2.json').read_text())
    transcript = tmp_path / record['transcript']
    transcript.write_text(transcript.read_text() + '\nChanged decision\n')
    with pytest.raises(ValueError, match='Reviewed evidence changed'):
        module.verify_saved_review(tmp_path)


def test_a_rehashed_packet_cannot_expand_the_reviewed_policy_scope(tmp_path):
    import json
    packet = copied_review(tmp_path)
    packet['hotel_policies']['City Hotel'] = 'automatically overbook one extra room'
    path = tmp_path / 'docs/reviews/coursework-policy-review-v2.json'
    path.write_text(json.dumps(packet))
    record_path = tmp_path / 'docs/reviews/coursework-policy-signoff-v2.json'
    record = json.loads(record_path.read_text())
    record['packet_sha256'] = module.sha(path)
    record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='decision scope'):
        module.verify_saved_review(tmp_path)
