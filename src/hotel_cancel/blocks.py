"""E4 inferred blocks, separated RDF state/outcomes and conditional cost attribution."""

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from rdflib import Graph, Literal, RDF, URIRef, XSD

from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings, separate_outcome
from hotel_cancel.quality_gate import prepare, verify_identity, sha
from hotel_cancel.serving import Predictor
from hotel_cancel.policy import (
    prepare_policy,
    run_policies,
    night_room_value,
    released_distribution,
    oversell,
)
from hotel_cancel.knowledge import HB, PROV, KB_DIR, timestamp, validate_graph
from hotel_cancel.walking import attribute

ROOT = Path(__file__).resolve().parents[2]
GROUP_KEY = [
    "hotel",
    "arrival",
    "booked",
    "market_segment",
    "distribution_channel",
    "deposit_type",
    "agent",
    "company",
    "reserved_room_type",
    "customer_type",
    "meal",
    "adults",
    "children",
    "adr",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
]
METHOD = "Exact notebook 16-field grouping; inferred, not verified party identity"


def block_ids(bookings):
    """Key-only identities: no outcomes, nationality, scores or input row order."""
    keys = bookings.loc[:, GROUP_KEY]

    def encode(row):
        values = []
        for value in row:
            if isinstance(value, pd.Timestamp):
                values.append(value.isoformat())
            elif isinstance(value, (float, np.floating)):
                values.append((0.0 if value == 0 else float(value)).hex())
            elif isinstance(value, np.generic):
                values.append(value.item())
            else:
                values.append(value)
        return hashlib.sha256(
            json.dumps(values, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()

    unique = keys.drop_duplicates()
    mapping = {tuple(row): encode(row) for row in unique.itertuples(index=False, name=None)}
    return pd.Series(
        [mapping[tuple(row)] for row in keys.itertuples(index=False, name=None)],
        index=bookings.index,
    )


def outcome_status(n, released):
    if type(n) is not int or type(released) is not int or n < 1 or not 0 <= released <= n:
        raise ValueError("Invalid block counts")
    return "NoRecordedRelease" if released == 0 else "FullyReleased" if released == n else "PartiallyReleased"


def block_table(nights, bookings, outcome, review_size, horizon):
    all_ids = block_ids(bookings)
    source_sizes = all_ids.value_counts()
    work = nights.copy()
    work["stable_block"] = all_ids.loc[work.index]
    # Prove the stable-key partition equals the policy's exact grouping.
    pairs = work[["stable_block", "block"]].drop_duplicates()
    assert pairs.stable_block.is_unique and pairs.block.is_unique, "Grouping differs from the given policy"
    rows = []
    for identifier, g in work.groupby("stable_block", sort=True):
        n = len(g)
        released = int(g.y.sum())
        arrival = pd.Timestamp(g.arrival.iat[0])
        observed = max(arrival + pd.Timedelta(days=1), outcome.loc[g.index, "status_date"].max())
        rows.append(
            dict(
                block_id=identifier,
                hotel=g.hotel.iat[0],
                arrival=arrival,
                as_of=arrival - pd.Timedelta(days=horizon),
                live_size=n,
                source_matched_size=int(source_sizes[identifier]),
                released_units=released,
                remaining_units=n - released,
                status=outcome_status(n, released),
                outcome_available_not_before=observed,
                multirow=n > 1,
                group_segment=bool(bookings.loc[g.index, "market_segment"].eq("Groups").any()),
                review_priority="desk-priority" if n >= review_size else "verify-party",
                verified_party=False,
            )
        )
    return pd.DataFrame(rows), work


def block_graph(table, *, source):
    """Only multi-row blocks; no raw matching-key or guest-identity triples."""
    graph = Graph()
    graph.bind("hb", HB)
    graph.bind("prov", PROV)
    for row in table.loc[table.multirow].itertuples(index=False):
        b = HB["inferred-block/" + row.block_id]
        s = HB["block-snapshot/" + row.block_id]
        o = HB["block-outcome/" + row.block_id]
        triples = [
            (b, RDF.type, HB.InferredBookingBlock),
            (b, HB.verifiedParty, Literal(False)),
            (b, HB.inferenceMethod, Literal(METHOD)),
            (b, PROV.wasDerivedFrom, source),
            (s, RDF.type, HB.BlockSnapshot),
            (s, HB.block, b),
            (s, HB.hotel, Literal(row.hotel)),
            (s, HB.asOf, timestamp(row.as_of)),
            (s, HB.arrival, timestamp(row.arrival)),
            (s, HB.liveSize, Literal(int(row.live_size), datatype=XSD.integer)),
            (
                s,
                HB.sourceMatchedSize,
                Literal(int(row.source_matched_size), datatype=XSD.integer),
            ),
            (s, HB.status, HB.OnBooks),
            (s, HB.reviewPriority, Literal(row.review_priority)),
            (o, RDF.type, HB.BlockOutcome),
            (o, HB.snapshot, s),
            (o, HB.availableNotBefore, timestamp(row.outcome_available_not_before)),
            (
                o,
                HB.releasedUnits,
                Literal(int(row.released_units), datatype=XSD.integer),
            ),
            (
                o,
                HB.remainingUnits,
                Literal(int(row.remaining_units), datatype=XSD.integer),
            ),
            (o, HB.status, HB[row.status]),
        ]
        for triple in triples:
            graph.add(triple)
    return graph


def covariance_diagnostic(nights, policies, agg, chosen, config):
    rows = []
    for (hotel, night), g in nights.groupby(["hotel", "arrival"], sort=True):
        b = g.groupby("block").agg(**agg)
        forecast = policies[chosen[hotel]](g, b)
        if forecast.block_sizes is None:
            marginal = pd.Series(forecast.probabilities, index=g.index)
            block_p = marginal.groupby(g.block).mean().to_numpy()
            sizes = g.groupby("block").size().to_numpy()
        else:
            block_p = np.asarray(forecast.probabilities)
            sizes = np.asarray(forecast.block_sizes, dtype=int)
        independent = released_distribution(np.repeat(block_p, sizes), np.ones(int(sizes.sum()), dtype=int))
        correlated = released_distribution(block_p, sizes)
        assert np.isclose(
            independent @ np.arange(len(independent)),
            correlated @ np.arange(len(correlated)),
            atol=1e-10,
            rtol=0,
        )
        released = int(g.y.sum())
        room = night_room_value(g, config["variable_cost_eur"])
        walk = config["walk_cost_eur"]
        for name, dist in [
            ("independent (means held fixed)", independent),
            ("perfect block correlation", correlated),
        ]:
            q = oversell(dist, room, walk)
            k = np.arange(len(dist))
            rows.append(
                dict(
                    hotel=hotel,
                    night=night,
                    assumption=name,
                    reference_assumption=(
                        forecast.block_sizes is None
                        if name.startswith("independent")
                        else forecast.block_sizes is not None
                    ),
                    q=q,
                    expected_releases=float(dist @ k),
                    forecast_walk_probability=float(dist[:q].sum()),
                    expected_walked_units=float(np.maximum(q - k, 0) @ dist),
                    realised_walked_units=max(q - released, 0),
                    realised_walk_cost=walk * max(q - released, 0),
                    realised_total_cost=walk * max(q - released, 0) + room * max(released - q, 0),
                )
            )
    return pd.DataFrame(rows)


def attribution_by_block(exposure, nights):
    # Membership is known only as a heuristic; this is post-hoc incidence, not causal cost.
    linked = exposure.merge(nights[["unit_id", "stable_block"]], on="unit_id", validate="many_to_one")
    sizes = nights.groupby("stable_block").size()
    linked["multirow"] = linked.stable_block.map(sizes).gt(1)
    rows = []
    splits = []
    for (hotel, rule), g in linked.groupby(["hotel", "rule"], sort=True):
        total = int(g.walked.sum())
        multi = int(g.loc[g.multirow, "walked"].sum())
        partial = 0
        affected = 0
        for identifier, block in g[g.multirow].groupby("stable_block", sort=True):
            walked = int(block.walked.sum())
            n = len(block)
            if walked:
                affected += 1
                is_split = 0 < walked < n
                partial += int(is_split)
                splits.append(
                    dict(
                        hotel=hotel,
                        rule=rule,
                        block_id=identifier,
                        surviving_units=n,
                        walked=walked,
                        partial_split=is_split,
                    )
                )
        rows.append(
            dict(
                hotel=hotel,
                rule=rule,
                total_walked=total,
                walked_in_inferred_multirow_blocks=multi,
                walked_in_singletons=total - multi,
                multirow_share=multi / total if total else None,
                affected_multirow_blocks=affected,
                partially_relocated_inferred_blocks=partial,
            )
        )
    return pd.DataFrame(rows), pd.DataFrame(splits)


def run(config, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "verification.json").unlink(missing_ok=True)
    settings = json.loads((ROOT / "config/stage12.json").read_text())
    assert settings["production_authorized"] is False
    if settings["horizon_days"] != config["decision_lead_days"]:
        raise ValueError("Stage 12 horizon differs")
    predictor = Predictor(ROOT / "models/serving")
    bk, X, y, masks, identity = prepare(config)
    verify_identity(
        identity,
        json.loads((ROOT / "config/evaluation-lock.json").read_text())["identity"],
    )
    from hotel_cancel.features import build_features

    pd.testing.assert_frame_equal(build_features(bk, predictor.bundle["top_agents"]), X)
    _, outcome = separate_outcome(load_bookings(config, use_cache=False))
    cfg = dict(
        config,
        **{
            k: predictor.policy["config"][k]
            for k in [
                "decision_lead_days",
                "recal_weeks_grid",
                "walk_cost_eur",
                "variable_cost_eur",
            ]
        },
    )
    p = predictor.bundle["model"].predict_proba(X)[:, 1]
    snap, policies, agg, _, _ = prepare_policy(
        SimpleNamespace(bookings=bk, outcome=outcome, probabilities=p),
        cfg,
        calibrators=predictor.policy["calibrators"],
        flat_rates=predictor.policy["flat_rates"],
    )
    nights = snap.loc[masks["test"].loc[snap.index]].copy()
    table, nights = block_table(nights, bk, outcome, settings["manual_review_size"], cfg["decision_lead_days"])
    nights["unit_id"] = "row-" + nights.index.astype(str)
    nights["booked"] = bk.loc[nights.index, "booked"]
    nights["distribution_channel"] = bk.loc[nights.index, "distribution_channel"].astype(str)
    nights["nationality_source_code"] = "audit-not-used"
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
    expected = pd.DataFrame(reference["rows"])
    expected["night"] = pd.to_datetime(expected.night)
    cols = ["hotel", "night", "q", "released", "walked"]
    assert reference["bundle_sha256"] == predictor.manifest["sha256"]
    pd.testing.assert_frame_equal(
        decisions[cols].sort_values(["hotel", "night"]).reset_index(drop=True),
        expected[cols].sort_values(["hotel", "night"]).reset_index(drop=True),
        check_dtype=False,
    )
    walking = json.loads((ROOT / "config/stage11.json").read_text())
    exposures = []
    for rule in [walking["primary_rule"], walking["benchmark_rule"]]:
        exposures.append(attribute(nights, decisions, rule=rule, seed=walking["seed"]))
    exposure = pd.concat(exposures, ignore_index=True)
    primary = exposure.loc[(exposure.rule == walking["primary_rule"]) & exposure.walked.eq(1)]
    digest = hashlib.sha256(
        primary[["hotel", "arrival", "unit_id"]]
        .sort_values(["hotel", "arrival", "unit_id"])
        .to_csv(index=False)
        .encode()
    ).hexdigest()
    assert digest == json.loads((ROOT / "config/stage11-run-inventory.json").read_text())["allocation_digest"]
    burden, splits = attribution_by_block(exposure, nights)
    burden["multirow_hotel_walk_cost_eur"] = burden.walked_in_inferred_multirow_blocks * cfg["walk_cost_eur"]
    burden["singleton_hotel_walk_cost_eur"] = burden.walked_in_singletons * cfg["walk_cost_eur"]
    burden.to_csv(out / "block-walking-cost.csv", index=False)
    plot_cost_attribution(burden, out)
    overview = []
    for hotel, g in table.groupby("hotel", sort=True):
        multi = g[g.multirow]
        overview.append(
            dict(
                hotel=hotel,
                all_inferred_blocks=len(g),
                singleton_blocks=int((~g.multirow).sum()),
                multirow_blocks=len(multi),
                multirow_live_units=int(multi.live_size.sum()),
                all_live_units=int(g.live_size.sum()),
                max_live_size=int(g.live_size.max()),
                priority_blocks=int(multi.review_priority.eq("desk-priority").sum()),
                fully_released_multirow=int(multi.status.eq("FullyReleased").sum()),
                partially_released_multirow=int(multi.status.eq("PartiallyReleased").sum()),
                multirow_not_group_segment=int((~multi.group_segment).sum()),
            )
        )
    pd.DataFrame(overview).to_csv(out / "block-overview.csv", index=False)
    sized = table[table.multirow].copy()
    sized["size_band"] = pd.cut(sized.live_size, [1, 2, 4, 9, np.inf], labels=["2", "3-4", "5-9", "10+"])
    sized.groupby(["hotel", "size_band"], observed=True).agg(
        blocks=("block_id", "size"), live_units=("live_size", "sum")
    ).reset_index().to_csv(out / "block-size-bands.csv", index=False)
    table.groupby(["hotel", "multirow", "group_segment", "status"], observed=True).agg(
        blocks=("block_id", "size"),
        live_units=("live_size", "sum"),
        released_units=("released_units", "sum"),
        remaining_units=("remaining_units", "sum"),
    ).reset_index().to_csv(out / "block-status-summary.csv", index=False)
    risk = covariance_diagnostic(nights, policies, agg, predictor.policy["chosen_policies"], cfg)
    selected = risk.loc[risk.reference_assumption, ["hotel", "night", "q"]]
    pd.testing.assert_frame_equal(
        selected.sort_values(["hotel", "night"]).reset_index(drop=True),
        decisions[["hotel", "night", "q"]].sort_values(["hotel", "night"]).reset_index(drop=True),
        check_dtype=False,
    )
    local = ROOT / "artifacts/stage12"
    local.mkdir(parents=True, exist_ok=True)
    risk.to_csv(local / "covariance-nights.csv", index=False)
    risk.groupby(["hotel", "assumption"], sort=True).agg(
        nights=("q", "size"),
        q_total=("q", "sum"),
        realised_walks=("realised_walked_units", "sum"),
        realised_walk_cost=("realised_walk_cost", "sum"),
        mean_forecast_walk_probability=("forecast_walk_probability", "mean"),
        realised_total_cost=("realised_total_cost", "sum"),
    ).reset_index().to_csv(out / "covariance-diagnostic.csv", index=False)
    table.to_csv(local / "inferred-blocks.csv", index=False)
    splits.to_csv(local / "split-blocks.csv", index=False)
    graph = block_graph(table, source=URIRef("urn:sha256:" + identity["raw_sha256"]))
    graph.serialize(local / "blocks.ttl", format="turtle")
    print(
        f"Validating {len(graph)} block-overlay triples for {int(table.multirow.sum())} multi-row inferred blocks",
        flush=True,
    )
    combined = Graph().parse(KB_DIR / "hotel.ttl", format="turtle")
    combined.parse(KB_DIR / "block-vocabulary.ttl", format="turtle")
    for triple in graph:
        combined.add(triple)
    conforms, report, text, violations = validate_graph(combined)
    report.serialize(out / "block-shacl.ttl", format="turtle")
    (out / "block-shacl.txt").write_text(text)
    if not conforms:
        raise ValueError("Generated inferred-block RDF fails SHACL")
    combined.serialize(local / "knowledge-snapshot.ttl", format="turtle")
    state_columns = [
        "block_id",
        "hotel",
        "arrival",
        "as_of",
        "live_size",
        "source_matched_size",
        "released_units",
        "remaining_units",
        "status",
        "outcome_available_not_before",
        "review_priority",
    ]
    state_digest = hashlib.sha256(
        table[state_columns].sort_values("block_id").to_csv(index=False, date_format="%Y-%m-%d").encode()
    ).hexdigest()
    result = dict(
        status="VERIFIED",
        scope="offline inferred-block diagnostics; no verified party identity or live handling",
        identity=identity,
        model_sha256=predictor.version,
        policy_sha256=predictor.manifest["sha256"]["policy_state.joblib"],
        settings=settings,
        block_key=GROUP_KEY,
        overview=overview,
        walking_cost_attribution=burden.to_dict(orient="records"),
        reference_nightly_quantities_exact=True,
        covariance_reference_matches_original_q=True,
        stage11_allocation_digest=digest,
        inferred_live_blocks=len(table),
        multirow_blocks=int(table.multirow.sum()),
        multirow_live_units=int(table.loc[table.multirow, "live_size"].sum()),
        block_overlay_triples=len(graph),
        combined_knowledge_triples=len(combined),
        generated_block_shacl_conforms=conforms,
        block_state_digest=state_digest,
        all_blocks_reconstructed=True,
        singletons_in_csv_not_rdf=True,
        no_model_or_calibrator_refitting=True,
        production_authorized=False,
        source_sha256={
            name: sha(Path(__file__).parent / name) for name in ["blocks.py", "policy.py", "history.py", "walking.py"]
        },
        knowledge_sha256={
            name: sha(KB_DIR / name)
            for name in [
                "block-shapes.ttl",
                "block-vocabulary.ttl",
                "blocks-example.ttl",
            ]
        },
        limitations=[
            "Exact-key blocks can merge unrelated bookings or split real parties; original duplicates are preserved",
            "One CSV row is a room proxy, not a unique person or verified room reservation",
            "Recorded release outcomes are separated from decision-time state and never used to rank or forecast earlier",
            "Attributed walks retain Stage 11 incumbent-only assumption; incremental sales and real inventory are unknown",
            "Independent/perfect-correlation diagnostics hold marginals fixed; realised cost differences are not causal block effects or model selection",
            "Five-unit review threshold is an unapproved prioritisation assumption, not a safety guarantee for smaller parties",
        ],
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def plot_cost_attribution(burden, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 4))
    labels = [r.hotel.replace(" Hotel", "") + " / " + r.rule.replace("_", " ") for r in burden.itertuples()]
    x = np.arange(len(burden))
    multi = burden.walked_in_inferred_multirow_blocks.to_numpy()
    single = burden.walked_in_singletons.to_numpy()
    ax.bar(x, multi, label="Inferred multi-row blocks")
    ax.bar(x, single, bottom=multi, label="Singleton matches")
    ax.set_xticks(x, labels, rotation=15, ha="right")
    ax.set(
        ylabel="Conditional simulated walked booking units",
        title="Block incidence depends on the allocation rule; no causal cost claim",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "block-walking-attribution.png", dpi=160)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default=str(ROOT / "docs/evidence/stage12"))
    args = p.parse_args()
    result = run(load_config(), args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
