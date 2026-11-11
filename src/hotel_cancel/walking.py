"""Offline E2 burden attribution. No live guest selection or new model fitting."""

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings, separate_outcome
from hotel_cancel.policy import prepare_policy, run_policies, night_room_value
from hotel_cancel.quality_gate import prepare, verify_identity, sha
from hotel_cancel.serving import Predictor

ROOT = Path(__file__).resolve().parents[2]
SELECTOR_FIELDS = {"unit_id", "booked"}
RULES = {"latest_booking_first", "seeded_lottery"}
AUDIT_DIMENSIONS = ["market_segment", "distribution_channel", "nationality_source_code"]


def select_units(units, count, *, rule, seed, night_key):
    """Strict projection keeps audit labels, revenue and risk scores out of ranking."""
    if set(units.columns) != SELECTOR_FIELDS:
        raise ValueError("Selector accepts exactly unit_id and booked; audit attributes are forbidden")
    if rule not in RULES:
        raise ValueError("Unknown relocation rule")
    if type(count) is not int or not 0 <= count <= len(units):
        raise ValueError("Invalid allocation count")
    if type(seed) is not int or seed < 0:
        raise ValueError("Invalid seed")
    if not isinstance(night_key, str) or not night_key:
        raise ValueError("Night key is required")
    if not units.unit_id.map(lambda v: isinstance(v, str) and bool(v)).all() or units.unit_id.duplicated().any():
        raise ValueError("Unit identifiers must be unique nonempty strings")
    frame = units.copy()
    frame["booked"] = pd.to_datetime(frame.booked, errors="raise")
    if frame.booked.isna().any():
        raise ValueError("Missing booking date")
    frame["_tie"] = frame.unit_id.map(
        lambda v: hashlib.sha256(json.dumps([seed, night_key, v], separators=(",", ":")).encode()).hexdigest()
    )
    columns = ["_tie", "unit_id"] if rule == "seeded_lottery" else ["booked", "_tie", "unit_id"]
    ascending = [True, True] if rule == "seeded_lottery" else [False, True, True]
    return frame.sort_values(columns, ascending=ascending, kind="stable").head(count).unit_id.tolist()


def attribute(nights, decisions, *, rule, seed):
    """Use realised survivors only to attribute realised simulated overflow at arrival.

    Hindsight determines the simulated survivor set, never the earlier forecast q.
    """
    if decisions.empty or decisions.duplicated(["hotel", "night"]).any():
        raise ValueError("Need unique hotel-night decisions")
    if not nights.unit_id.is_unique or not nights.y.isin([0, 1]).all():
        raise ValueError("Need unique unit identifiers and binary realised release labels")
    rows = []
    for decision in decisions.itertuples(index=False):
        g = nights[(nights.hotel == decision.hotel) & (nights.arrival == decision.night)]
        survivors = g.loc[g.y.eq(0)].copy()
        if (
            isinstance(decision.walked, (bool, np.bool_))
            or not np.isfinite(decision.walked)
            or decision.walked != int(decision.walked)
            or decision.walked < 0
        ):
            raise ValueError("Realised overflow must be a non-negative integer")
        count = int(decision.walked)
        if count > len(survivors):
            raise ValueError("Overflow exceeds attributable incumbent survivors")
        key = str(decision.hotel) + "|" + str(pd.Timestamp(decision.night).date())
        chosen = set(
            select_units(
                survivors.loc[:, ["unit_id", "booked"]],
                count,
                rule=rule,
                seed=seed,
                night_key=key,
            )
        )
        survivors["walked"] = survivors.unit_id.isin(chosen).astype(int)
        survivors["uniform_expected_walks"] = count / len(survivors) if len(survivors) else 0.0
        survivors["walk_night"] = count > 0
        survivors["rule"] = rule
        rows.append(
            survivors[
                [
                    "unit_id",
                    "hotel",
                    "arrival",
                    "booked",
                    "market_segment",
                    "distribution_channel",
                    "nationality_source_code",
                    "walked",
                    "uniform_expected_walks",
                    "walk_night",
                    "rule",
                ]
            ]
        )
    result = pd.concat(rows, ignore_index=True)
    assert int(result.walked.sum()) == int(decisions.walked.sum())
    return result


def group_summary(exposure, *, minimum, walk_cost):
    rows = []
    for (hotel, rule), population in exposure.groupby(["hotel", "rule"], sort=True):
        total_walks = int(population.walked.sum())
        total = len(population)
        for dimension in AUDIT_DIMENSIONS:
            for category, g in population.groupby(dimension, observed=True, sort=True):
                n = len(g)
                walks = int(g.walked.sum())
                expected = float(g.uniform_expected_walks.sum())
                enough = n >= minimum
                rows.append(
                    dict(
                        hotel=hotel,
                        rule=rule,
                        dimension=dimension,
                        category=str(category),
                        eligible_surviving_booking_units=n,
                        eligible_on_walk_nights=int(g.walk_night.sum()),
                        reportable=enough,
                        walked=walks if enough else None,
                        walking_rate=walks / n if enough else None,
                        hotel_walking_rate=total_walks / total if total else None,
                        expected_under_uniform_nightly_allocation=expected if enough else None,
                        actual_to_nightly_uniform_ratio=walks / expected if enough and expected > 0 else None,
                        hotel_relocation_cost_eur=walks * walk_cost if enough else None,
                        sparse_walk_night_exposure=int(g.walk_night.sum()) < minimum,
                    )
                )
    return pd.DataFrame(rows)


def lottery_sensitivity(nights, decisions, base_exposure, seeds, minimum):
    walking = decisions[decisions.walked > 0]
    candidates = []
    for d in walking.itertuples(index=False):
        g = nights[(nights.hotel == d.hotel) & (nights.arrival == d.night) & nights.y.eq(0)]
        candidates.append((g, int(d.walked), str(d.hotel) + "|" + str(pd.Timestamp(d.night).date())))
    denominators = []
    for hotel, pop in base_exposure.groupby("hotel", sort=True):
        for dimension in AUDIT_DIMENSIONS:
            for category, g in pop.groupby(dimension, observed=True, sort=True):
                if len(g) >= minimum:
                    denominators.append(
                        (
                            str(hotel),
                            dimension,
                            str(category),
                            len(g),
                            float(g.uniform_expected_walks.sum()),
                        )
                    )
    records = []
    lookup = nights.set_index("unit_id")
    for seed in seeds:
        ids = []
        for g, count, key in candidates:
            ids.extend(
                select_units(
                    g.loc[:, ["unit_id", "booked"]],
                    count,
                    rule="seeded_lottery",
                    seed=seed,
                    night_key=key,
                )
            )
        assert len(ids) == int(decisions.walked.sum()) and len(ids) == len(set(ids))
        selected = lookup.loc[ids]
        for hotel, dimension, category, n, expected in denominators:
            k = int(((selected.hotel == hotel) & selected[dimension].astype(str).eq(category)).sum())
            records.append(
                dict(
                    seed=seed,
                    hotel=hotel,
                    dimension=dimension,
                    category=category,
                    walked=k,
                    eligible=n,
                    walking_rate=k / n,
                    actual_to_nightly_uniform_ratio=k / expected if expected else None,
                )
            )
    return pd.DataFrame(records)


def run(config, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "verification.json").unlink(missing_ok=True)
    settings = json.loads((ROOT / "config/stage11.json").read_text())
    if settings["production_authorized"] is not False:
        raise ValueError("This command is offline only")
    predictor = Predictor(ROOT / "models/serving")
    bk, X, y, masks, identity = prepare(config)
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    verify_identity(identity, lock["identity"])
    if predictor.manifest["raw_sha256"] != identity["raw_sha256"]:
        raise ValueError("Bundle/data identity mismatch")
    from hotel_cancel.features import build_features

    pd.testing.assert_frame_equal(build_features(bk, predictor.bundle["top_agents"]), X)
    _, outcome = separate_outcome(load_bookings(config, use_cache=False))
    p = predictor.bundle["model"].predict_proba(X)[:, 1]
    cfg = dict(
        config,
        **{
            key: predictor.policy["config"][key]
            for key in [
                "decision_lead_days",
                "recal_weeks_grid",
                "walk_cost_eur",
                "variable_cost_eur",
            ]
        },
    )
    snap, policies, agg, _, _ = prepare_policy(
        SimpleNamespace(bookings=bk, outcome=outcome, probabilities=p),
        cfg,
        calibrators=predictor.policy["calibrators"],
        flat_rates=predictor.policy["flat_rates"],
    )
    nights = snap.loc[(snap.arrival >= config["valid_end"]) & (snap.arrival < config["test_end"])].copy()
    # Only audit labels are joined here. The selector receives its strict projection later.
    for column in ["booked", "distribution_channel", "country"]:
        nights[column] = bk.loc[nights.index, column]
    nights["unit_id"] = "row-" + nights.index.astype(str)
    nights["market_segment"] = nights.market_segment.astype(str)
    nights["distribution_channel"] = nights.distribution_channel.astype(str)
    nights["nationality_source_code"] = ""
    top_codes = {}
    for hotel in config["hotels"]:
        train = masks["train"] & bk.hotel.astype(str).eq(hotel)
        top = (
            bk.loc[train, "country"]
            .astype(str)
            .loc[lambda s: s != "unknown"]
            .value_counts()
            .head(settings["nationality_top_training_codes_per_hotel"])
            .index.tolist()
        )
        top_codes[hotel] = top
        select = nights.hotel == hotel
        codes = nights.loc[select, "country"].astype(str)
        nights.loc[select, "nationality_source_code"] = codes.where(codes.isin(top), "OTHER").where(
            codes != "unknown", "UNKNOWN"
        )
    decisions = []
    for hotel in config["hotels"]:
        name = predictor.policy["chosen_policies"][hotel]
        decisions.append(
            run_policies(
                nights[nights.hotel == hotel],
                {name: policies[name]},
                lambda g: night_room_value(g, cfg["variable_cost_eur"]),
                block_agg=agg,
                walk_cost=cfg["walk_cost_eur"],
                decision_lead_days=cfg["decision_lead_days"],
            )
        )
    decisions = pd.concat(decisions, ignore_index=True)
    reference = json.loads((ROOT / "config/stage11-policy-reference.json").read_text())
    if (
        reference["bundle_sha256"] != predictor.manifest["sha256"]
        or reference["source_run"] != predictor.manifest["source_run"]
    ):
        raise ValueError("Reference policy provenance differs from serving bundle")
    expected = pd.DataFrame(reference["rows"])
    expected["night"] = pd.to_datetime(expected.night)
    columns = ["hotel", "night", "q", "released", "walked"]
    pd.testing.assert_frame_equal(
        decisions[columns].sort_values(["hotel", "night"]).reset_index(drop=True),
        expected[columns].sort_values(["hotel", "night"]).reset_index(drop=True),
        check_dtype=False,
    )
    decisions.to_csv(output / "nightly-overflow.csv", index=False)
    latest = attribute(nights, decisions, rule=settings["primary_rule"], seed=settings["seed"])
    lottery = attribute(nights, decisions, rule=settings["benchmark_rule"], seed=settings["seed"])
    exposure = pd.concat([latest, lottery], ignore_index=True)
    # Actual counterfactual audit-label permutation: allocation must be identical.
    swapped = nights.copy()
    for field in [
        "country",
        "market_segment",
        "distribution_channel",
        "nationality_source_code",
    ]:
        swapped[field] = swapped[field].astype(str).iloc[::-1].to_numpy()
    counter = attribute(swapped, decisions, rule=settings["primary_rule"], seed=settings["seed"])
    assert set(latest.loc[latest.walked.eq(1), "unit_id"]) == set(counter.loc[counter.walked.eq(1), "unit_id"])
    summary = group_summary(
        exposure,
        minimum=settings["minimum_eligible_for_reporting"],
        walk_cost=cfg["walk_cost_eur"],
    )
    summary.to_csv(output / "group-burden.csv", index=False)
    sensitivity = lottery_sensitivity(
        nights,
        decisions,
        lottery,
        settings["lottery_sensitivity_seeds"],
        settings["minimum_eligible_for_reporting"],
    )
    sensitivity.to_csv(output / "lottery-seeds.csv", index=False)
    seed_summary = (
        sensitivity.groupby(["hotel", "dimension", "category"], sort=True)
        .agg(
            seed_count=("seed", "size"),
            walks_min=("walked", "min"),
            walks_mean=("walked", "mean"),
            walks_max=("walked", "max"),
            rate_min=("walking_rate", "min"),
            rate_max=("walking_rate", "max"),
        )
        .reset_index()
    )
    seed_summary.to_csv(output / "lottery-sensitivity.csv", index=False)
    hotel_rows = []
    assumptions = []
    costs = []
    for hotel, g in decisions.groupby("hotel", sort=True):
        walks = int(g.walked.sum())
        eligible = len(latest[latest.hotel == hotel])
        assert int(latest.loc[latest.hotel == hotel, "walked"].sum()) == walks
        assert int(lottery.loc[lottery.hotel == hotel, "walked"].sum()) == walks
        hotel_rows.append(
            dict(
                hotel=hotel,
                nights=len(g),
                overflow_nights=int(g.walked.gt(0).sum()),
                oversold_units=int(g.q.sum()),
                released_units=int(g.released.sum()),
                eligible_incumbent_survivors=eligible,
                walked_units=walks,
                walking_rate=walks / eligible,
                hotel_relocation_cost_eur=walks * cfg["walk_cost_eur"],
            )
        )
        assumptions.extend(
            [
                dict(
                    hotel=hotel,
                    assumption="incremental sales honoured",
                    incumbent_walks=walks,
                    unobserved_extra_walks=0,
                ),
                dict(
                    hotel=hotel,
                    assumption="incumbents protected",
                    incumbent_walks=0,
                    unobserved_extra_walks=walks,
                ),
            ]
        )
        for cost in settings["cost_attribution_eur"]:
            costs.append(
                dict(
                    hotel=hotel,
                    cost_per_walk_eur=cost,
                    walked_units_fixed=walks,
                    hotel_relocation_cost_eur=walks * cost,
                    scope="accounting sensitivity only; q and policy are held fixed",
                )
            )
    pd.DataFrame(hotel_rows).to_csv(output / "hotel-summary.csv", index=False)
    pd.DataFrame(assumptions).to_csv(output / "allocation-assumptions.csv", index=False)
    pd.DataFrame(costs).to_csv(output / "cost-attribution.csv", index=False)
    # Row-level allocations stay ignored, never in committed fairness evidence.
    local = ROOT / "artifacts/stage11"
    local.mkdir(parents=True, exist_ok=True)
    exposure.to_csv(local / "simulated-incumbent-allocations.csv", index=False)
    plot_burden(summary, output)
    fingerprint = hashlib.sha256(
        latest.loc[latest.walked.eq(1), ["hotel", "arrival", "unit_id"]]
        .sort_values(["hotel", "arrival", "unit_id"])
        .to_csv(index=False)
        .encode()
    ).hexdigest()
    result = dict(
        status="VERIFIED",
        scope="retrospective conditional simulation; not realised guest walks or release approval",
        identity=identity,
        model_sha256=predictor.version,
        policy_sha256=predictor.manifest["sha256"]["policy_state.joblib"],
        selected_policies=predictor.policy["chosen_policies"],
        settings=settings,
        hotel_summaries=hotel_rows,
        nationality_reporting_codes_from_training_only=top_codes,
        allocation_digest=fingerprint,
        reference_nightly_quantities_exact=True,
        total_simulated_walks=int(decisions.walked.sum()),
        selector_fields=sorted(SELECTOR_FIELDS),
        audit_attribute_permutation_does_not_change_selection=True,
        allocation_conserved_per_hotel=True,
        lottery_seed_count=len(settings["lottery_sensitivity_seeds"]),
        no_model_or_policy_refitting=True,
        country_never_used_for_ranking=True,
        production_authorized=False,
        source_sha256={
            name: sha(Path(__file__).parent / name) for name in ["walking.py", "policy.py", "history.py", "features.py"]
        },
        config_sha256=sha(ROOT / "config/stage11.json"),
        policy_reference_sha256=sha(ROOT / "config/stage11-policy-reference.json"),
        legal_sources_sha256=sha(ROOT / "config/stage11-legal-sources.json"),
        limitations=[
            "Unknown capacity; given sold-out arrival-night/no-resale proxy, not a real occupancy reconstruction",
            "Incremental sales are unobserved; primary burden assumes they are honoured; alternative shifts all walks to those unknown bookings",
            "CSV row treated as one room unit, not a guest; party size, accessibility, consent and contract priority are unknown",
            "Exact duplicates are retained as in the supplied baseline; rows cannot establish unique people",
            "Final-state data and inferred booking date do not prove event-time availability or actual check-in order",
            "Source country codes are audit proxies, not verified citizenship or ethnicity; nationality effects can reflect channel/night mix",
            "Seed range is simulation variation, not a confidence interval; small cells are descriptive and suppressed below the stated denominator",
            "Allocated hotel expense is not a valuation of guest harm; no automatic ranking is recommended for production",
            "Resort calibration still fails; reference exposure is evaluated only for coursework, with no registry promotion",
        ],
    )
    (output / "verification.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def plot_burden(summary, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, dimension in zip(axes, ["market_segment", "distribution_channel"]):
        data = summary[(summary.dimension == dimension) & summary.reportable]
        labels = sorted(data.category.unique())
        x = np.arange(len(labels))
        width = 0.18
        for i, (hotel, rule) in enumerate(data.groupby(["hotel", "rule"], sort=True).groups):
            rows = data[(data.hotel == hotel) & (data.rule == rule)].set_index("category")
            values = [100 * rows.loc[c, "walking_rate"] if c in rows.index else np.nan for c in labels]
            ax.bar(
                x + (i - 1.5) * width,
                values,
                width,
                label=hotel.replace(" Hotel", "") + " / " + rule.replace("_", " "),
            )
        ax.set_xticks(x, labels, rotation=25, ha="right")
        ax.set(
            ylabel="Simulated walks / surviving booking units (%)",
            title=dimension.replace("_", " ").title(),
        )
    axes[0].legend(fontsize=7)
    fig.suptitle("Conditional incumbent burden · fixed reference policy · Jan–Aug 2017")
    fig.tight_layout()
    fig.savefig(output / "group-burden.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "docs/evidence/stage11"))
    args = parser.parse_args()
    result = run(load_config(), args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
