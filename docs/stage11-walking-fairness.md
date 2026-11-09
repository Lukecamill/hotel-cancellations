# Stage 11 — Who bears the walking cost?

Implemented 9 November 2026. Mac and Ubuntu verification are separate. This is a
conditional historical simulation, not a record of real guest relocation.

## Run

```sh
make walking-audit
```

The existing pinned environment is sufficient. The command checks the original
raw/holdout identity, reuses the saved baseline model and policy state, and verifies
all 486 selected reference hotel-night quantities. It fits/chooses nothing and does
not change the service, knowledge graph, MLflow registry or guest-review interface.

## Simulation and findings

Primary assumption: hypothetical additional sales are honoured; when q exceeds
realised releases, assign the resulting walks to surviving recorded booking rows.
Compare latest-booking-first against a reproducible within-night lottery. The
ranking interface accepts only row identifier and inferred booking date. Audit
labels are excluded by construction; an actual label-permutation check preserves
allocation. Selection is simulated at arrival, when survivors are known, never fed
back into the seven-day quantity forecast.

| Hotel | Nights | Nights with overflow | Surviving incumbent units | Simulated walks | Hotel expense at EUR250/walk |
|---|---:|---:|---:|---:|---:|
| City | 243 | 83 | 13,214 | 154 | EUR38,500 |
| Resort | 243 | 25 | 6,418 | 25 | EUR6,250 |

Walk totals are identical across rules; their distribution is not. At City,
latest-booking-first assigns 17 walks among 238 Corporate segment survivors
(7.14%), compared with a within-night uniform expectation of about 1.60 walks.
It assigns 35 among 1,325 PRT-coded survivors (2.64%), compared with about 13.02
expected. These examples demonstrate concentration under the stated scenario;
they do not establish actual treatment, ethnicity, legal nationality or causation.
The source has a documented nationality/channel artefact.

The lottery's 20 predeclared seeds expose allocation variability without selecting
a favourable seed. Report gross walking rates and conditional uniform expectations
separately: a group can face more overflow nights even with neutral within-night
allocation. Ratios with zero expected exposure are undefined. Small groups below
30 eligible rows have their walking metrics withheld, and sparse walk-night
exposure is flagged. OTHER can hide country-specific disparities.

Alternative assumption: protect all recorded incumbents and assign the walks to
unobserved incremental sales. Then incumbent group walking is zero and all 179
walks have unknown incremental-booking group membership. This is a key limitation,
not a measured fairness improvement. We cannot know who actually gets walked from
this final-state dataset.

EUR100/250/500 attribution keeps decisions fixed and measures hotel expense only.
It does not measure guest disruption, loss, accessibility or family/party harm.
Each retained CSV row is a room proxy, not a unique person; duplicates and inferred
booking dates remain baseline limitations. Inferred group-block cohesion and its
cost contribution are Stage 12 work.

## Evidence

- nightly-overflow.csv: frozen per-night quantities/releases/walks.
- hotel-summary.csv: population, exposure, walks and expense by hotel.
- group-burden.csv: segment, channel and audit-only source-country groups by rule.
- lottery-seeds.csv / lottery-sensitivity.csv: seed-level results and ranges.
- allocation-assumptions.csv: attribution under the two explicit assumptions.
- cost-attribution.csv: fixed-quantity expense scenarios.
- group-burden.png: descriptive segment/channel comparison.
- verification.json: fingerprints, rule settings, conservation and limitations.

Only row-level traces go to ignored artifacts/stage11/. Aggregate evidence is in
docs/evidence/stage11/. Suppression means published subgroup sums may omit cells;
conservation checks are run on the unsuppressed simulation.

## Governance and operational boundary

See stage11-governance.md for researched Services Directive Article 20, GDPR and
current AI Act reasoning, and ADR 0013 for the decision. Neither rule is released
for automatic guest-impacting use. Keep human handling/no-overbooking as the
operational fallback, obtain policy-wide sign-off, verify inventory and consider
voluntary alternatives, suitable accommodation, contracts, accessibility, party
cohesion and contest routes. Resort's known calibration failure stays blocked.

## Ubuntu

```sh
python3 scripts/verify_stage11_ubuntu.py
```

The packaged verifier checks complete source/test/knowledge/config inventories,
runs CI and this simulation in the existing Stage 9 check image, compares all
aggregate outputs to the Mac digests and verifies runtime/registry files unchanged.
Native evidence goes to docs/evidence/stage11-ubuntu/. Only claim Ubuntu verification
after STAGE11_UBUNTU_VERIFIED. Earlier stage inventories remain historical snapshots.

## Initial Ubuntu parity discrepancy

The initial Ubuntu run passed 173 tests (six database skips), preserved all
486 reference quantities and produced the identical allocation digest. Six
aggregate CSV files were byte-identical. Only nightly-overflow.csv differed,
in its floating-point expected-release sums at approximately 1e-15 precision.
Policies, counts, realised walks, empty units and costs matched exactly.
The initial verifier stopped before its final runtime-protection checks; that
attempt is not labelled fully verified.

The corrected comparator retains exact checks for every other column and file.
Only the nightly expected column permits absolute difference <= 1e-12, matching
the project's existing full-precision numerical tolerance. It rejects material
forecast differences, nonfinite values and any changed decision/cost/policy field.
A pinned Mac nightly reference and csv-comparison.json expose the comparisons.
The VM's future-timestamp warnings indicate host/guest clock skew; these checks
use content fingerprints and historical arrival dates, not archive mtimes.
Corrected Ubuntu verification is confirmed below.

## Confirmed corrected Ubuntu result

The supplied corrected transcript confirms STAGE11_UBUNTU_VERIFIED: 185 tests
collected, 179 passed and six database integration tests skipped. All source,
test, knowledge and configuration files match. Every reference nightly quantity,
allocation ID, decision, cost and subgroup field matches exactly. Only nightly
expected-release sums use the documented 1e-12 absolute numerical tolerance.
Runtime/Compose and registry files are unchanged; Resort calibration remains
correctly blocked. The corrected transcript and parsed verification are saved
in docs/evidence/stage11-ubuntu/. Native files can be copied from the VM.
These are conditional simulations, not real guest relocations or legal clearance.
