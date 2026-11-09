# ADR 0013 — Conditional walking attribution and separated fairness audit

Date: 9 November 2026. Status: offline experiment implemented; not operationally approved.

## Decision

Prespecify latest-booking-first and a seeded nightly lottery as a benchmark in
config/stage11.json. Rank exactly unit_id and inferred booked date. Reject all
additional inputs, including nationality, segment/channel, ADR and model scores.
Keep labels only in a separate audit path and verify that permuting them does not
change selected row IDs. A source country code is not verified citizenship,
residence or ethnicity. No nationality or KB-region priority is implemented.

Reuse the unchanged saved model/calibrators/policy choices and frozen dataset.
Match every q/released/walked value for the 486 selected hotel-nights to the
original reference run before attributing burden. No new learner, calibrator or
policy selection occurs. The failed Resort is a coursework reference only.

The primary scenario protects hypothetical incremental sales and distributes
max(q-released,0) over surviving incumbent rows at arrival. Hindsight identifies
survivors for evaluation, not the earlier seven-day quantity decision or ranking
features. The alternative protects incumbents and puts all walks on the unobserved
extra sales. Report both rather than inventing country/channel attributes for those
bookings. Capacity, pick-up and actual relocation records are unknown.

Measure per hotel, market segment, channel and training-top-ten country codes
(with OTHER/UNKNOWN). Denominators are surviving incumbent booking units, not all
bookings or persons. Report exposure on walk nights, gross rate and observed walks
relative to the sum of W/S within each hotel-night. The latter distinguishes
selection from unequal exposure to overflow nights. Groups with fewer than 30
eligible rows have walking metrics withheld; flag sparse walk-night exposure too.
This is a descriptive reporting threshold, not legal/statistical certification.

Evaluate 20 prespecified lottery seeds without choosing a favourable one. Their
range is simulation variability, not a confidence interval or p-value. Keep q and
policy fixed when attributing expense at EUR100/250/500 per walk; label this as
accounting sensitivity, not a policy cost sensitivity experiment or guest welfare.
Totals and per-hotel allocations must conserve simulated overflow for both rules.

## Consequences and recommendation

The given policy yields 154 City and 25 Resort simulated walked room units over
243 nights each. Rule choice shifts aggregate burdens despite excluded nationality.
In the primary scenario, City Corporate segment has 17 latest-booking-first walks
versus a uniform nightly expectation about 1.60. PRT-coded bookings receive 35
versus about 13.02 expected. These are conditional descriptive findings; correlations,
seasonality, duplicates, channel mix and unknown real extra sales prevent causal
or legal conclusions. A different allocation assumption moves all 179 walks to
unobserved bookings, leaving their group attribution unknown.

Do not approve latest-booking-first as an operational default on this evidence.
The lottery is a benchmark, not an approved operational rule. Human handling,
verified capacity, consent/contract/accessibility considerations, suitable alternatives,
party cohesion, contest and legal/DPO review are prerequisites for any pilot.
Full inferred-block treatment follows in Stage 12. The service and registry remain
unchanged; simulated results never constitute authority to affect a guest.

Legal reasoning and authoritative source links are in docs/stage11-governance.md:
Services Directive Article 20, GDPR/meaningful human review and the current AI Act.
Nationality exclusion alone is not proof of indirect-discrimination compliance,
GDPR compliance or equal harm. Record-level traces remain ignored under artifacts/;
commit only source, configuration, governance decisions and aggregate evidence.
