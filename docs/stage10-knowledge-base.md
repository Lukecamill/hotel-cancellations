# Stage 10 — Versioned knowledge base and E1 comparisons

Implemented 9 November 2026. Local and Ubuntu verification are recorded
separately. Existing service, model bundle and MLflow aliases are unchanged.

## Artifacts and checks

- knowledge/reference.ttl: byte-versioned 607-triple notebook graph.
- knowledge/hotel.ttl: 3,734-triple extended graph, with provenance, explicit
  unknowns, source alias, per-field availability assumptions and temporal UK facts.
- knowledge/shapes.ttl and reference-shapes.ttl: extended CI contract and original audit shapes.
- knowledge/competency-questions.md: ten questions and their acceptance evidence.
- knowledge/queries/: parameterised SPARQL query patterns.
- knowledge/briefing-golden.json: 19 typed semantic/date/unknown cases.
- docs/evidence/stage10/: SHACL, ablation, cold-start and grounding-contract evidence.

From the project root with the existing pinned Python environment and raw CSV:

```sh
make kb-check
make kb-ablation
make kb-briefing-check
make ci
```

`make ci` runs software tests and extended SHACL before the unchanged per-hotel
quality gate. Resort's known calibration failure must still return nonzero.
`kb-check` needs only versioned RDF/shapes; ablation needs the attributed raw
CSV and verifies the original raw/holdout fingerprints. No added dependency
or refitted production model is required.

## Results reproduced from the notebook

| Variant | City AUPRC | Resort AUPRC | City after renamed plan | Resort after renamed plan |
|---|---:|---:|---:|---:|
| Codes only | 0.785722 | 0.627908 | 0.594617 | 0.560699 |
| Codes + KB policy context | 0.783342 | 0.632013 | 0.683816 | 0.596821 |
| KB classes replacing three codes | 0.782595 | 0.633818 | 0.782595 | 0.633818 |

Adding meanings does not establish an accuracy gain today. Under the synthetic
new-plan shock, class-only features remain identical and performance is
unchanged without retraining. All five notebook experiments, including
country/region diagnostic variants, match printed precision. Country/region
experiments expose calibration damage and remain excluded from serving.

Original SHACL issues are retained in the audit: CN (1,279 bookings), ATA/ATF
(three bookings combined), Undefined channel (five) and Undefined segment (two).
The extension passes SHACL by declaring provenance, aliases and unknowns, not
by inventing business classifications or changing the dataset.

The KB grounding contract answers all 19 cases exactly: 18 supported semantic
claims across 12 answerable cases, zero unsupported claims; seven cases abstain.
The codes-only comparator makes no semantic claims (precision undefined,
coverage zero). Both preserve numeric context in 19/19 cases. This measures
knowledge grounding and honest abstention, not language-model factuality.
The required local-model briefing and 30-night evaluation remain Stage 13.

## Boundaries and source interpretation

Policy mappings normally apply only in the historical dataset window. UK
membership is modelled at an exact UTC withdrawal instant; query historic
membership, not a static current-region boolean. The new-plan validity is a
hypothetical scenario contract. Country is diagnostic only, including its alias.
Field provenance records assumptions and uncertainty; no event-write timestamps
are supplied by the source. See ADR 0012 and the competency questions.

## Ubuntu

The supplied package contains all source/test/config/knowledge files and an
expected inventory, rather than a partial update. In the existing Ubuntu checkout:

```sh
python3 scripts/verify_stage10_ubuntu.py
```

It uses the separate Stage 9 check image, verifies source/test/knowledge hashes
and collected test identities, runs `make ci` (expecting only Resort quality
failure), then reruns ablation and briefing checks. It does not replace the
Stage 7 runtime or modify the registry. Native evidence goes to
`docs/evidence/stage10-ubuntu/`. Only claim Ubuntu verification after the
`STAGE10_UBUNTU_VERIFIED` marker. Stages 8/9 inventories remain historical snapshots.

The verifier uses dedicated QUALITY_OUTPUT and KB_OUTPUT directories, preserving
previous stage evidence. These Make overrides can also be used for local CI runs.

## Confirmed Ubuntu result

The supplied terminal transcript confirms STAGE10_UBUNTU_VERIFIED: all source,
test and knowledge files match; 162 tests collected, 156 passed and six database
tests skipped. Extended SHACL passes with 3,734 triples; notebook ablation and
the 4,126-booking renamed-code stress test reproduce. All 19 deterministic
grounding cases pass with zero unsupported claims. Serving/Compose and registry
are unchanged; Resort calibration still correctly blocks the quality gate.
The user transcript and parsed verification are retained under
docs/evidence/stage10-ubuntu. Native VM evidence can be copied back separately.
This does not complete the Stage 13 language-model briefing evaluation.
