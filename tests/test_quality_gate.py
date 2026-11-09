import json
import pytest
from hotel_cancel.quality_gate import assess, reliability, verify_identity, run


def test_reliability_edges_weighting_and_empty_bins():
    rows, ece = reliability([0, 1, 1, 0], [0, 1, .5, .5])
    assert sum(r['n'] for r in rows) == 4
    assert rows[0]['n'] == 1 and rows[9]['n'] == 1
    assert rows[1]['mean_probability'] is None
    assert ece == pytest.approx(0)
    _, ece = reliability([1, 1, 1, 0], [.2, .2, .2, .8])
    assert ece == pytest.approx(.8)


@pytest.mark.parametrize('p', [[float('nan')], [float('inf')], [-.1], [1.1]])
def test_invalid_probabilities_fail(p):
    with pytest.raises(ValueError):
        reliability([1], p)


def test_perfect_ranking_cannot_hide_bad_calibration():
    report, _ = assess([0, 0, 1, 1], [0, 0, .1, .1], min_auprc=.7,
                       ratio_band=[.85, 1.15], max_ece=.1)
    assert report['checks']['auprc']
    assert not report['checks']['calibration_ratio']
    assert not report['checks']['ece']
    assert report['gate'] == 'FAIL'


def test_gate_pass_and_exact_inclusive_thresholds():
    report, _ = assess([0, 1], [0, 1], min_auprc=1, ratio_band=[1, 1], max_ece=0)
    assert report['gate'] == 'PASS'


@pytest.mark.parametrize('labels', [[0, 0], [1, 1]])
def test_one_class_is_not_a_passing_gate(labels):
    report, _ = assess(labels, [.5, .5], min_auprc=0, ratio_band=[.1, 10], max_ece=1)
    assert report['gate'] == 'FAIL'
    assert report['auprc'] is None


def test_any_frozen_identity_change_is_rejected():
    expected = dict(raw_sha256='a', holdout_sha256='b', split_counts={'test': 2})
    verify_identity(dict(expected), expected)
    for key in expected:
        with pytest.raises(ValueError, match=key):
            verify_identity(dict(expected, **{key: 'changed'}), expected)


def test_identity_error_prevents_fit_and_removes_stale_success(tmp_path, monkeypatch):
    import hotel_cancel.quality_gate as gate
    lock = tmp_path / 'lock.json'
    lock.write_text(json.dumps(dict(schema_version=1, identity={'raw_sha256': 'old'})))
    output = tmp_path / 'out'
    output.mkdir()
    for name in ['report.json', 'reliability.csv', 'reliability.png']:
        (output / name).write_text('stale PASS')
    monkeypatch.setattr(gate, 'prepare', lambda _: (None, None, None, None, {'raw_sha256': 'new'}))
    def forbidden(*args, **kwargs):
        pytest.fail('Must not fit a model after identity failure')
    monkeypatch.setattr(gate, 'fit', forbidden)
    code, report = run({}, lock, output)
    assert code == 2 and report['status'] == 'ERROR'
    assert json.loads((output / 'report.json').read_text())['status'] == 'ERROR'
    assert not (output / 'reliability.png').exists()
    assert not (output / 'reliability.csv').exists()


@pytest.mark.parametrize('resort_p, expected_code', [([0., 1.], 0), ([0., .1], 1)])
def test_exit_status_requires_every_hotel_to_pass(tmp_path, monkeypatch, resort_p, expected_code):
    import numpy as np
    import pandas as pd
    import hotel_cancel.quality_gate as gate
    from types import SimpleNamespace
    bk = pd.DataFrame({'hotel': ['City Hotel'] * 2 + ['Resort Hotel'] * 2})
    X = pd.DataFrame({'feature': [1, 2, 3, 4]})
    y = pd.Series([0, 1, 0, 1])
    masks = {'train': pd.Series([False] * 4), 'test': pd.Series([True] * 4)}
    identity = {'test_fixture': True}
    monkeypatch.setattr(gate, 'prepare', lambda _: (bk, X, y, masks, identity))
    p = np.array([0., 1.] + resort_p)
    model = SimpleNamespace(predict_proba=lambda _: np.column_stack([1-p, p]))
    monkeypatch.setattr(gate, 'fit', lambda *args, **kwargs: model)
    monkeypatch.setattr(gate, 'plot_reliability', lambda *args: None)
    hotels = ['City Hotel', 'Resort Hotel']
    lock = tmp_path / 'lock.json'
    lock.write_text(json.dumps(dict(schema_version=1, identity=identity,
         thresholds={h: dict(min_auprc=.7, ratio_band=[.85, 1.15], max_ece=.1) for h in hotels})))
    code, report = run({'seed': 3217, 'hotels': hotels}, lock, tmp_path / 'out')
    assert code == expected_code
    assert report['hotels']['City Hotel']['gate'] == 'PASS'
    assert report['status'] == ('PASS' if code == 0 else 'FAIL')
