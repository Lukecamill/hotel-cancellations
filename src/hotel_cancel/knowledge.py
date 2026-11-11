"""Versioned Task 19 RDF vocabulary, temporal queries and SHACL validation."""

import argparse
import json
from pathlib import Path
from urllib.parse import quote, unquote

import pandas as pd
import pyshacl
from rdflib import Graph, Literal, Namespace, RDF, XSD, URIRef

ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "knowledge"
HB = Namespace("https://ari3217.example/hotel#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SH = Namespace("http://www.w3.org/ns/shacl#")
START = "2015-07-01T00:00:00+00:00"
END = "2017-09-01T00:00:00+00:00"
EXIT = "2020-01-31T23:00:00+00:00"
SNAPSHOT = "2026-11-10T00:00:00+00:00"
NOTEBOOK = URIRef("https://ari3217.example/sources/task19-notebook")
PAPER = URIRef("https://doi.org/10.1016/j.dib.2018.11.126")
BREXIT = URIRef("https://commonslibrary.parliament.uk/research-briefings/cbp-11529/")
DECISION = URIRef("https://ari3217.example/decisions/0012-knowledge-base")
KINDS = {
    "country": ("country", HB.Country),
    "segment": ("market_segment", HB.MarketSegment),
    "channel": ("distribution_channel", HB.Channel),
    "deposit": ("deposit_type", HB.DepositPolicy),
}
PROPERTIES = {
    "segment": ["isGroup", "viaIntermediary"],
    "channel": ["intermediated"],
    "deposit": ["prepaid", "refundable"],
}
KB_POLICY = [
    "kb_is_group",
    "kb_via_intermediary",
    "kb_channel_intermediated",
    "kb_prepaid",
    "kb_refundable",
]
KB_REGION = ["kb_region", "kb_is_eu"]


def node(kind, code):
    return HB[f"{kind}/{quote(str(code), safe='')}"]


def timestamp(value):
    t = pd.Timestamp(value)
    if pd.isna(t):
        raise ValueError("A valid as-of timestamp is required")
    return Literal(
        t.tz_localize("UTC").isoformat() if t.tzinfo is None else t.tz_convert("UTC").isoformat(),
        datatype=XSD.dateTime,
    )


def build_reference(bookings):
    values = json.loads((KB_DIR / "notebook-vocabulary.json").read_text())
    graph = Graph()
    graph.bind("hb", HB)
    for region, codes in values["REGIONS"].items():
        r = node("region", region)
        graph.add((r, RDF.type, HB.Region))
        graph.add((r, HB.label, Literal(region)))
        graph.add((r, HB.isEU, Literal(region in ("EU", "Domestic"))))
        for code in codes.split():
            graph.add((node("country", code), HB.inRegion, r))
    for code, (group, via) in values["SEGMENTS"].items():
        graph.add((node("segment", code), HB.isGroup, Literal(group)))
        graph.add((node("segment", code), HB.viaIntermediary, Literal(via)))
    for code, via in values["CHANNELS"].items():
        graph.add((node("channel", code), HB.intermediated, Literal(via)))
    for code, (pre, ref) in values["DEPOSITS"].items():
        graph.add((node("deposit", code), HB.prepaid, Literal(pre)))
        graph.add((node("deposit", code), HB.refundable, Literal(ref)))
    graph.add(
        (
            node("deposit", "Non Refund"),
            HB.observedNote,
            Literal("99.8 % of City non-refundable bookings cancelled: tour-operator blocks"),
        )
    )
    for kind, (column, cls) in KINDS.items():
        for code in bookings[column].astype(str).unique():
            if code != "unknown":
                graph.add((node(kind, code), RDF.type, cls))
                graph.add((node(kind, code), HB.code, Literal(code)))
    return graph


def annotate(
    graph,
    subject,
    *,
    source=NOTEBOOK,
    start=START,
    end=END,
    status="notebook_semantic_assumption",
):
    graph.add((subject, PROV.wasDerivedFrom, source))
    graph.add((subject, HB.validFrom, timestamp(start)))
    graph.add((subject, HB.validUntil, timestamp(end)))
    graph.add((subject, HB.assertionStatus, Literal(status)))
    graph.add((subject, PROV.generatedAtTime, timestamp("2026-11-09T00:00:00+00:00")))


def build_extended(reference):
    graph = Graph()
    graph.bind("hb", HB)
    graph.bind("prov", PROV)
    for triple in reference:
        graph.add(triple)
    # Preserve CN as an explicit source alias, never silently rewrite the raw CSV.
    cn = node("country", "CN")
    graph.remove((cn, RDF.type, HB.Country))
    graph.add((cn, RDF.type, HB.CountryAlias))
    graph.add((cn, HB.aliasOf, node("country", "CHN")))
    graph.add(
        (
            cn,
            HB.correctionStatus,
            Literal("source alias used by notebook mapping; not an ISO alpha-3 code"),
        )
    )
    for subject in list(graph.subjects(HB.inRegion, None)):
        if subject != cn:
            graph.add((subject, RDF.type, HB.Country))
            graph.add((subject, HB.code, Literal(unquote(str(subject).split("/")[-1]))))
    for subject in list(graph.subjects(RDF.type, HB.Region)):
        annotate(graph, subject)
    unknown = node("region", "unknown")
    graph.add((unknown, RDF.type, HB.Region))
    graph.add((unknown, HB.label, Literal("unknown")))
    annotate(graph, unknown, source=DECISION, status="explicit_unknown")
    for kind in ["country", "segment", "channel", "deposit"]:
        u = node(kind, "unknown")
        graph.add((u, RDF.type, HB.UnknownCode))
        graph.add((u, HB.code, Literal("unknown")))
        graph.add((u, HB.unresolved, Literal(True)))
        annotate(graph, u, source=DECISION, status="explicit_unknown")
    for code in ["ATA", "ATF"]:
        graph.add((node("country", code), HB.inRegion, unknown))
        graph.add((node("country", code), HB.unresolved, Literal(True)))
    for kind in ["segment", "channel"]:
        s = node(kind, "Undefined")
        graph.add((s, HB.unresolved, Literal(True)))
        graph.add(
            (
                s,
                HB.resolutionNote,
                Literal("Source code has no verified business classification; abstain"),
            )
        )
    for kind, (_, cls) in KINDS.items():
        for subject in graph.subjects(RDF.type, cls):
            annotate(
                graph,
                subject,
                status="explicit_unknown"
                if (subject, HB.unresolved, Literal(True)) in graph
                else "notebook_semantic_assumption",
            )
    annotate(graph, cn, source=DECISION, status="explicit_source_alias")
    # Every source field records an assumption about when it becomes known,
    # not a fabricated per-booking write timestamp.
    from hotel_cancel.contracts import RAW_COLUMNS
    from hotel_cancel.features import BOOKING_INPUTS

    post = {
        "assigned_room_type",
        "booking_changes",
        "required_car_parking_spaces",
        "total_of_special_requests",
    }
    outcome = {
        "is_canceled",
        "reservation_status",
        "reservation_status_date",
        "status_date",
    }
    for field in sorted(set(RAW_COLUMNS) | set(BOOKING_INPUTS) | {"status_date"}):
        f = node("field", field)
        graph.add((f, RDF.type, HB.Field))
        graph.add((f, HB.code, Literal(field)))
        if field in outcome:
            phase, status = "outcome", "not_booking_time"
        elif field in post:
            phase, status = "during_stay_or_amendment", "not_booking_time"
        elif field == "country":
            phase, status = "potentially_check_in", "unverified"
        elif field == "days_in_waiting_list":
            phase, status = "confirmation", "not_booking_time"
        else:
            phase, status = "booking_or_derived", "assumed_not_proven"
        graph.add((f, HB.writtenAtPhase, Literal(phase)))
        graph.add((f, HB.availabilityStatus, Literal(status)))
        graph.add((f, HB.observedWriteTimestamp, Literal(False)))
        graph.add((f, PROV.wasDerivedFrom, PAPER))
        annotate(graph, f)
    for property_name in [
        "isGroup",
        "viaIntermediary",
        "intermediated",
        "prepaid",
        "refundable",
        "inRegion",
        "isEU",
    ]:
        s = HB[property_name]
        graph.add((s, RDF.type, HB.SemanticProperty))
        graph.add((s, HB.writtenAtPhase, Literal("curated_mapping_not_PMS_event")))
        annotate(graph, s)
    # Model EU membership as country-specific, non-overlapping temporal assertions.
    for country in list(graph.subjects(RDF.type, HB.Country)):
        if (country, HB.unresolved, Literal(True)) in graph:
            continue
        region = graph.value(country, HB.inRegion)
        if region is None:
            continue
        eu = bool(graph.value(region, HB.isEU).toPython())
        code = str(graph.value(country, HB.code))
        periods = (
            [(START, EXIT, True, BREXIT), (EXIT, SNAPSHOT, False, BREXIT)]
            if code == "GBR"
            else [(START, END, eu, NOTEBOOK)]
        )
        for i, (lower, upper, value, source) in enumerate(periods):
            s = node("membership", f"{code}-{i}")
            graph.add((s, RDF.type, HB.MembershipAssertion))
            graph.add((s, HB.subject, country))
            graph.add((s, HB.isEU, Literal(value)))
            annotate(
                graph,
                s,
                source=source,
                start=lower,
                end=upper,
                status="historical_membership",
            )
    # Hypothetical launch metadata: declared in advance, never inferred from labels.
    plan = node("deposit", "Non Refund (new plan)")
    graph.add((plan, RDF.type, HB.DepositPolicy))
    graph.add((plan, HB.code, Literal("Non Refund (new plan)")))
    graph.add((plan, HB.prepaid, Literal(True)))
    graph.add((plan, HB.refundable, Literal(False)))
    annotate(
        graph,
        plan,
        source=DECISION,
        start="2017-01-01T00:00:00+00:00",
        status="hypothetical_launch_contract",
    )
    for cls in [
        HB.Country,
        HB.CountryAlias,
        HB.MarketSegment,
        HB.Channel,
        HB.DepositPolicy,
        HB.UnknownCode,
    ]:
        for subject in list(graph.subjects(RDF.type, cls)):
            graph.add((HB.Vocabulary, HB.requiresCode, subject))
    for subject in list(graph.subjects(RDF.type, HB.Field)):
        graph.add((HB.Vocabulary, HB.requiresField, subject))
    graph.add(
        (
            NOTEBOOK,
            HB.label,
            Literal("Supplied Task 19 notebook cell 34; coarse mapping assumptions"),
        )
    )
    graph.add(
        (
            DECISION,
            HB.label,
            Literal("ADR 0012; explicit unknowns and hypothetical cold-start semantics"),
        )
    )
    return graph


def lookup(graph, query):
    return pd.DataFrame([[v.toPython() for v in row] for row in graph.query(query, initNs={"hb": HB})]).set_index(0)


def policy_facts(graph, kind, code, as_of):
    if kind not in PROPERTIES:
        raise ValueError("Expected deposit, segment or channel")
    subject = node(kind, code)
    query = """SELECT ?p ?value WHERE { ?s hb:validFrom ?from ; hb:validUntil ?until ; ?p ?value .
      FILTER(?from <= ?at && ?at < ?until) }"""
    values = {
        str(p).split("#")[-1]: value.toPython()
        for p, value in graph.query(
            query,
            initNs={"hb": HB},
            initBindings={"s": subject, "at": timestamp(as_of)},
        )
    }
    if values.get("unresolved") or not all(p in values for p in PROPERTIES[kind]):
        return None
    return {p: values[p] for p in PROPERTIES[kind]}


def membership(graph, code, as_of):
    country = node("country", code)
    country = graph.value(country, HB.aliasOf) or country
    query = """SELECT ?eu WHERE { ?a a hb:MembershipAssertion ; hb:subject ?country ; hb:isEU ?eu ;
      hb:validFrom ?from ; hb:validUntil ?until . FILTER(?from <= ?at && ?at < ?until) }"""
    rows = list(
        graph.query(
            query,
            initNs={"hb": HB},
            initBindings={"country": country, "at": timestamp(as_of)},
        )
    )
    if len(rows) > 1:
        raise ValueError("Overlapping membership assertions")
    return bool(rows[0][0].toPython()) if rows else None


def kb_features(bookings, features, graph, *, temporal=False, as_of="2017-01-01"):
    """Notebook feature construction. Country context is offline diagnostic only."""
    seg = lookup(
        graph,
        "SELECT ?code ?grp ?via WHERE { ?s a hb:MarketSegment ; hb:code ?code ; hb:isGroup ?grp ; hb:viaIntermediary ?via . }",
    )
    channel = lookup(
        graph,
        "SELECT ?code ?via WHERE { ?s a hb:Channel ; hb:code ?code ; hb:intermediated ?via . }",
    )
    deposit = lookup(
        graph,
        "SELECT ?code ?pre ?ref WHERE { ?s a hb:DepositPolicy ; hb:code ?code ; hb:prepaid ?pre ; hb:refundable ?ref . }",
    )
    country = lookup(
        graph,
        "SELECT ?code ?region ?eu WHERE { ?s a hb:Country ; hb:code ?code ; hb:inRegion ?r . ?r hb:label ?region ; hb:isEU ?eu . }",
    )
    result = features.copy()
    result["kb_is_group"] = bookings.market_segment.astype(str).map(seg[1]).astype(float)
    result["kb_via_intermediary"] = bookings.market_segment.astype(str).map(seg[2]).astype(float)
    result["kb_channel_intermediated"] = bookings.distribution_channel.astype(str).map(channel[1]).astype(float)
    result["kb_prepaid"] = bookings.deposit_type.astype(str).map(deposit[1]).astype(float)
    result["kb_refundable"] = bookings.deposit_type.astype(str).map(deposit[2]).astype(float)
    result["kb_region"] = pd.Categorical(bookings.country.astype(str).map(country[1]).fillna("unknown"))
    result["kb_is_eu"] = bookings.country.astype(str).map(country[2]).astype(float)
    if temporal:
        for kind, column, names in [
            ("segment", "market_segment", ["kb_is_group", "kb_via_intermediary"]),
            ("channel", "distribution_channel", ["kb_channel_intermediated"]),
            ("deposit", "deposit_type", ["kb_prepaid", "kb_refundable"]),
        ]:
            mappings = {code: policy_facts(graph, kind, code, as_of) for code in bookings[column].astype(str).unique()}
            for prop, name in zip(PROPERTIES[kind], names):
                values = {code: None if facts is None else facts[prop] for code, facts in mappings.items()}
                result[name] = bookings[column].astype(str).map(values).astype(float)
        result["kb_is_eu"] = (
            bookings.country.astype(str)
            .map({c: membership(graph, c, as_of) for c in bookings.country.astype(str).unique()})
            .astype(float)
        )
    return result


def validate_graph(graph, shapes=None):
    if shapes is None:
        shapes = Graph().parse(KB_DIR / "shapes.ttl", format="turtle")
        if (KB_DIR / "block-shapes.ttl").exists():
            shapes.parse(KB_DIR / "block-shapes.ttl", format="turtle")
    conforms, report, text = pyshacl.validate(graph, shacl_graph=shapes, advanced=True)
    violations = []
    for r in report.subjects(RDF.type, SH.ValidationResult):
        violations.append(
            dict(
                focus=str(report.value(r, SH.focusNode)),
                path=str(report.value(r, SH.resultPath)),
                message=str(report.value(r, SH.resultMessage)),
            )
        )
    return (
        bool(conforms),
        report,
        text,
        sorted(violations, key=lambda r: (r["focus"], r["path"], r["message"])),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--graph", default=str(KB_DIR / "hotel.ttl"))
    p.add_argument("--output", default=str(ROOT / "docs/evidence/stage10/shacl"))
    args = p.parse_args()
    graph = Graph().parse(args.graph, format="turtle")
    for filename in ["block-vocabulary.ttl", "blocks-example.ttl"]:
        if (KB_DIR / filename).exists():
            graph.parse(KB_DIR / filename, format="turtle")
    conforms, report, text, violations = validate_graph(graph)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report.serialize(out / "report.ttl", format="turtle")
    (out / "report.txt").write_text(text)
    value = dict(conforms=conforms, triples=len(graph), violations=violations)
    (out / "report.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value, indent=2))
    return 0 if conforms else 1


if __name__ == "__main__":
    raise SystemExit(main())
