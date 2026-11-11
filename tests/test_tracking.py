from types import SimpleNamespace

import pytest

from hotel_cancel.tracking import checked_gate, assign_aliases


THRESHOLDS = dict(min_auprc=0.7, ratio_band=[0.85, 1.15], max_ece=0.1)


def result(**changes):
    return dict(
        dict(
            auprc=0.8,
            expected_observed_ratio=1.0,
            ece=0.05,
            checks={"two_classes": True},
            gate="PASS",
        ),
        **changes,
    )


class Registry:
    def __init__(self, gate="PASS", champion=None):
        self.aliases = {} if champion is None else {"champion": champion}
        self.versions = {
            "1": SimpleNamespace(tags={"quality_gate": "PASS"}),
            "2": SimpleNamespace(tags={"quality_gate": gate}),
        }

    def set_registered_model_alias(self, name, alias, version):
        self.aliases[alias] = version

    def get_registered_model(self, name):
        return SimpleNamespace(aliases=self.aliases.copy())

    def get_model_version(self, name, version):
        return self.versions[version]


def test_failing_resort_is_reviewable_but_never_bootstrapped_as_champion():
    registry = Registry(gate="FAIL")
    aliases = assign_aliases(registry, "resort", "2", result(expected_observed_ratio=0.68), THRESHOLDS)
    assert aliases == {"challenger": "2"}


def test_passing_candidate_bootstraps_champion_without_claiming_a_new_learner():
    registry = Registry()
    assert assign_aliases(registry, "city", "2", result(), THRESHOLDS) == {
        "champion": "2",
        "challenger": "2",
    }


def test_new_candidate_does_not_replace_existing_passing_champion():
    registry = Registry(champion="1")
    assert assign_aliases(registry, "city", "2", result(), THRESHOLDS) == {
        "champion": "1",
        "challenger": "2",
    }


@pytest.mark.parametrize(
    "changes",
    [
        dict(auprc=0.69),
        dict(expected_observed_ratio=0.68),
        dict(ece=0.11),
        dict(ece=float("nan")),
        dict(auprc=None),
        dict(checks={"two_classes": False}),
    ],
)
def test_pass_label_cannot_override_failed_numeric_evidence(changes):
    assert not checked_gate(result(**changes), THRESHOLDS)


def test_thresholds_are_inclusive():
    assert checked_gate(result(auprc=0.7, expected_observed_ratio=0.85, ece=0.1), THRESHOLDS)


def test_existing_failing_champion_requires_explicit_registry_review():
    registry = Registry(gate="FAIL", champion="2")
    with pytest.raises(ValueError, match="existing champion"):
        assign_aliases(registry, "resort", "2", result(expected_observed_ratio=0.68), THRESHOLDS)
