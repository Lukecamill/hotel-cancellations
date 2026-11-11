# Stage 12 — Group-block analysis and semantic representation

Current CI and submission status: see [the updated audit](submission-checklist.md) and
[coursework/release separation](coursework-and-release.md). The stage results and
old command outcomes below are historical; `make quality-gate` remains strict,
while current `make ci` verifies expected reproduction before building.

Implemented 9 November 2026. Local and Ubuntu verification are recorded separately.

## Run and outputs

```sh
make block-audit
make ci
```

The Makefile explicitly uses this checkout's src/ directory so an older installed
package cannot hide new modules. The existing pinned baseline environment is
sufficient. All reconstruction and diagnostic entry points are offline; serving,
model/policy artifacts and MLflow registry are not changed.

Versioned knowledge resources add a block vocabulary, shapes, queries and
synthetic examples. `make ci` validates those examples alongside the core graph,
then runs the unchanged quality gate (Resort calibration still fails).
`make block-audit` reconstructs every on-books block and validates the complete
generated multi-row RDF overlay combined with the core knowledge base.

Ignored artifacts/stage12/ contains all reconstructed matches (including
singletons), affected/split inferred blocks, covariance-night diagnostics,
blocks.ttl and knowledge-snapshot.ttl. Real key fields and booking memberships
are not published in Git. Versioned aggregate evidence is in docs/evidence/stage12/.

## Counts and outcomes

| Hotel | All block matches | Multi-row matches | Units in multi-row matches | Largest live match | Priority matches (>=5) |
|---|---:|---:|---:|---:|---:|
| City | 10,645 | 1,283 | 4,634 | 115 | 150 |
| Resort | 5,689 | 465 | 1,499 | 80 | 61 |

All 20,719 seven-day on-books rows are accounted for. These are arrival-cohort
matches on the notebook's 16 fields, not verified travel parties or unique people.
The key excludes nationality and outcomes. Exact duplicates are preserved and
matching can both merge unrelated bookings and split real groups. A raw Groups
segment is different from an inferred multi-row block.

There are 83 partially released multi-row matches. The RDF separates OnBooks
snapshot state from NoRecordedRelease/PartiallyReleased/FullyReleased outcomes.
The inferred availableNotBefore bound does not establish an observed PMS write
instant. SHACL rejects future outcome fields on snapshots, invalid counts/status,
verified-party claims and premature availability bounds. See
knowledge/block-competency-questions.md for query semantics and limitations.

## Walking-cost attribution

| Hotel / rule | Walked units in multi-row matches | Attributed hotel expense | Partially relocated inferred blocks |
|---|---:|---:|---:|
| City / latest booking first | 24 | EUR6,000 | 9 |
| City / lottery | 60 | EUR15,000 | 49 |
| Resort / latest booking first | 0 | EUR0 | 0 |
| Resort / lottery | 5 | EUR1,250 | 5 |

The total 154 City and 25 Resort walks is unchanged. Their block incidence depends
on the allocation rule. This retains Stage 11's conditional assumption that
hypothetical extra sales are honoured; protecting incumbents instead shifts all
walks to unobserved extra bookings. These are not records of real guest walks,
actual family separations, guest harm or causal block costs.

## Correlation diagnostic

Hold per-unit release means fixed and compare independent releases with perfect
within-block correlation, using the supplied cost/quantity rule. Both use the
same realised source releases for retrospective costing. The original selected
assumption reproduces every frozen reference q (independence for City, block
correlation for Resort). No policy is selected from the diagnostic holdout result.

| Hotel | Assumption | Total oversell q | Simulated walks | Hotel walk expense |
|---|---|---:|---:|---:|
| City | Independent | 603 | 154 | EUR38,500 |
| City | Perfect blocks | 455 | 84 | EUR21,000 |
| Resort | Independent | 105 | 34 | EUR8,500 |
| Resort | Perfect blocks | 75 | 25 | EUR6,250 |

Do not deploy the lower-cost diagnostic as a new policy. Misspecified correlation,
partial release, unknown actual capacity/pick-up/resale and unverified parties
remain. Full total-cost outcomes, including empty-unit proxy cost, are in
covariance-diagnostic.csv; they are not measured hotel profit.

## Recommendation

Use a human desk to confirm suspected party identity and review group-level
relocation. Prioritise >=5 live units (211 matches here), but review any planned
relocation that might split a party even below that threshold. Confirm inventory,
contracts, accessibility, alternatives and consent before individual treatment.
The threshold is a prespecified unapproved prioritisation assumption, not a legal
or safety boundary. See ADR 0014 and the Stage 11 governance assessment.

## Ubuntu verification

```sh
python3 scripts/verify_stage12_ubuntu.py
```

The verifier checks full source/test/knowledge/config inventories, software and
SHACL CI, original per-night quantities, Stage 11 allocation identity, complete
generated block SHACL, and aggregate values against the Mac. Counts, costs and
labels must match exactly; only declared diagnostic ratios allow absolute 1e-12
machine-precision differences. Native evidence goes to docs/evidence/stage12-ubuntu/.
Only claim verification after STAGE12_UBUNTU_VERIFIED. All earlier inventories
remain historical stage snapshots, rather than moving latest-version manifests.

## Confirmed Ubuntu result

The supplied terminal transcript confirms STAGE12_UBUNTU_VERIFIED: 202 tests
collected, 196 passed and six database integration tests skipped. All source,
test, knowledge and configuration files match. All 16,334 live block matches
were reconstructed; 1,748 multi-row matches cover 6,133 live booking units.
The complete generated block graph passes SHACL. Block identities/states,
reference quantities, Stage 11 allocations, aggregate counts, costs and labels
match exactly; only declared diagnostic ratios use the 1e-12 tolerance.
Serving, registry and the core knowledge graph are unchanged. Resort calibration
remains correctly blocked. The transcript and parsed result are saved under
docs/evidence/stage12-ubuntu; native files can be copied from Ubuntu separately.
These remain inferred matches and offline diagnostics, not verified parties or
permission for live guest handling.
