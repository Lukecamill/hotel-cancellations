import json

import pytest
from rdflib import Graph, Literal, RDF

from hotel_cancel.knowledge import (
    KB_DIR,
    HB,
    PROV,
    node,
    timestamp,
    membership,
    policy_facts,
    validate_graph,
)
from hotel_cancel.kb_briefing_eval import evaluate


@pytest.fixture
def graph():
    return Graph().parse(KB_DIR / "hotel.ttl", format="turtle")


def test_versioned_extension_passes_but_original_issues_remain_auditable(graph):
    assert validate_graph(graph)[0]
    original = Graph().parse(KB_DIR / "reference.ttl", format="turtle")
    shapes = Graph().parse(KB_DIR / "reference-shapes.ttl", format="turtle")
    valid, _, _, results = validate_graph(original, shapes)
    assert len(original) == 607 and not valid
    assert len({(r["focus"], r["message"]) for r in results}) == 5


@pytest.mark.parametrize(
    "at,expected",
    [
        ("2017-08-08", True),
        ("2020-01-31T22:59:59Z", True),
        ("2020-01-31T23:00:00Z", False),
        ("2020-02-01", False),
        ("2014-01-01", None),
        ("2026-11-10T00:00:00Z", None),
    ],
)
def test_uk_membership_uses_effective_instant_not_current_region(graph, at, expected):
    assert membership(graph, "GBR", at) is expected


def test_new_code_has_no_semantics_before_launch_and_unknowns_abstain(graph):
    assert policy_facts(graph, "deposit", "Non Refund (new plan)", "2016-12-31") is None
    assert policy_facts(graph, "deposit", "Non Refund (new plan)", "2017-01-01") == {
        "prepaid": True,
        "refundable": False,
    }
    assert policy_facts(graph, "segment", "Undefined", "2017-08-08") is None
    assert policy_facts(graph, "channel", "Undefined", "2017-08-08") is None
    assert policy_facts(graph, "deposit", "Non Refund", "2017-09-01") is None
    assert policy_facts(graph, "deposit", 'x" } UNION {?s ?p ?o} #', "2017-08-08") is None


def test_source_alias_is_explicit_and_unresolved_territory_is_not_guessed(graph):
    assert graph.value(node("country", "CN"), HB.code) == Literal("CN")
    assert graph.value(node("country", "CN"), HB.aliasOf) == node("country", "CHN")
    assert membership(graph, "CN", "2017-08-08") is False
    assert membership(graph, "ATA", "2017-08-08") is None


@pytest.mark.parametrize(
    "defect",
    ["missing_source", "invalid_boolean", "reversed_interval", "missing_required_type"],
)
def test_shacl_rejects_broken_semantics_and_provenance(graph, defect):
    subject = node("deposit", "Non Refund")
    if defect == "missing_source":
        graph.remove((subject, PROV.wasDerivedFrom, None))
    elif defect == "invalid_boolean":
        graph.remove((subject, HB.prepaid, None))
        graph.add((subject, HB.prepaid, Literal("yes")))
    elif defect == "reversed_interval":
        graph.remove((subject, HB.validUntil, None))
        graph.add((subject, HB.validUntil, timestamp("2014-01-01")))
    else:
        graph.remove((subject, RDF.type, HB.DepositPolicy))
    assert not validate_graph(graph)[0]


def test_overlapping_membership_is_rejected_by_shacl_and_lookup(graph):
    source = node("membership", "GBR-0")
    other = node("membership", "GBR-overlap")
    for p, o in list(graph.predicate_objects(source)):
        graph.add((other, p, o))
    assert not validate_graph(graph)[0]
    with pytest.raises(ValueError, match="Overlapping"):
        membership(graph, "GBR", "2017-01-01")


def test_field_provenance_does_not_invent_event_timestamps(graph):
    country = node("field", "country")
    assert graph.value(country, HB.availabilityStatus) == Literal("unverified")
    for field in graph.subjects(RDF.type, HB.Field):
        assert graph.value(field, HB.observedWriteTimestamp).toPython() is False
    assert graph.value(node("field", "reservation_status"), HB.availabilityStatus) == Literal("not_booking_time")


def test_grounded_fact_evaluation_separates_abstention_precision_and_coverage(graph):
    cases = json.loads((KB_DIR / "briefing-golden.json").read_text())
    reports, outputs = evaluate(graph, cases)
    kb = reports["codes + temporal KB"]
    bare = reports["codes only (abstain)"]
    assert kb["exact_case_answers"] == len(cases) and kb["unsupported_semantic_claims"] == 0
    assert kb["semantic_coverage"] == 1 and bare["semantic_coverage"] == 0
    assert bare["semantic_claim_precision"] is None
    assert all(r["numeric_context_exact_cases"] == len(cases) for r in reports.values())
    assert all(row["output"]["message_to_guest"] is None for row in outputs)
