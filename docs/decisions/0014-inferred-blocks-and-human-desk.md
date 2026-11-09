# ADR 0014 — Inferred block state, covariance diagnostics and human handling

Date: 9 November 2026. Status: offline analysis implemented; operational sign-off pending.

## Representation and inference

Preserve the notebook's exact 16-field grouping and prove partition equivalence
to the original policy block IDs. Add stable key-only hashes for reproducible
arrival-cohort entities. Nationality, outcomes and model scores are not in the key.
Do not infer that a match is a verified party: exact duplicates remain, unrelated
bookings can match, and real groups can span different keys/arrival dates.

Reconstruct all 16,334 holdout on-books block matches, including singletons.
Represent the 1,748 multi-row matches in a generated RDF overlay, with separate
InferredBookingBlock, BlockSnapshot and BlockOutcome entities. The snapshot
contains decision date, arrival, source/live sizes, OnBooks status and review
priority. Future releases/remaining counts are forbidden on snapshots by SHACL.
Outcome counts/statuses live only in the retrospective outcome entity.

`availableNotBefore` is the later of arrival plus one day and the latest source
status date. It is an inferred date-resolution availability lower bound, not an
observed ingestion timestamp or proof of complete event history. UTC midnight
is a serialization convention for source dates, not an exact PMS event time.

Keep the original 3,734-triple semantic KB unchanged. Add a versioned block
vocabulary, shapes, queries and synthetic CI examples as an overlay. Reproducibly
generate all real multi-row block entities and a combined knowledge snapshot
under ignored artifacts/stage12/. Do not commit key fields, membership traces
or a real booking-level graph. Validate the entire combined generated graph;
CI also validates the synthetic block cases with the core KB.

## Quantification

Use the saved reference learner/calibrators/policies, unchanged raw and holdout
fingerprints, and all 486 original selected hotel-night quantities. Retain the
Stage 11 allocation digest exactly. Attribute walked units and EUR250 hotel
expense to multi-row versus singleton matches under each of the two Stage 11
rules. This is incidence conditional on honoured incremental sales, not proof
that blocks caused a cost or that real guests were relocated.

City: 1,283 multi-row matches, 4,634 live units, maximum size 115; Resort:
465 matches, 1,499 units, maximum 80. There are 83 partially released multi-row
matches (71 City, 12 Resort), so perfect within-block cancellation is visibly
an assumption, not a universal observed property. Many inferred matches are
not labelled Groups (1,152 City, 332 Resort); neither that label nor matching
keys establish party identity.

With latest-booking-first, 24 City walks (EUR6,000) and no Resort walks fall on
multi-row matches. With the lottery, the counts are 60 City (EUR15,000) and five
Resort (EUR1,250). The same total 179 walks is conserved. Latest-booking-first
partially relocates nine inferred blocks; the lottery partially relocates 54.
These counts concern surviving proxy rows, not verified family separations.

Separately compare independent and perfectly correlated releases while holding
each block's per-unit marginal probability fixed. No fitting, calibration or
policy selection occurs on the holdout. Confirm that the original covariance
assumption reproduces each reference q. Report both counterfactual outcomes,
without choosing a new champion or claiming a causal block effect. City realised
walk expense changes from EUR38,500 under independence to EUR21,000 under the
block assumption; Resort changes from EUR8,500 to EUR6,250. These hypothetical
quantity decisions are not released to the operational service.

## Human handling decision

Recommend desk verification for every suspected multi-row party before guest
relocation. Prioritise five or more live units at the seven-day decision point:
150 City and 61 Resort matches meet that prespecified coursework threshold.
The threshold is not a business-approved optimum, and smaller matches are not
certified safe. Confirm actual PMS group IDs, contract terms, room-night inventory,
accessibility and party cohesion. Do not automatically split a confirmed party
or infer consent/priority from nationality, segment, ADR or model score.

Partial final release is a retrospective monitoring finding, not a feature used
for the earlier decision. Any suspected party that could be split needs human
handling regardless of size; unavailable identity/inventory facts block automation.
The allocation uncertainty from Stage 11, no-resale/sold-out proxy, missing extra
sales and Resort calibration failure remain. No service, registry alias or
policy-wide approval changes in this stage.
