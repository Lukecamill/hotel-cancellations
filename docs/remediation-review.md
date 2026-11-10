# Quality remediation and coursework policy review

The user requested remediation of Resort calibration, briefing copying and policy
sign-off. The original prescribed learner, frozen lock and historical evidence
remain intact. The original demo is not rebuilt or promoted.

## Calibration correction

A separate Resort booking-horizon sigmoid calibrator reuses the notebook's
LogisticRegression-on-clipped-logit method without refitting/tuning LightGBM.
It fits 4,466 Resort rows arriving July–September 2016 whose recorded outcome
status predates 1 October. October–December validation is disjoint and passes
before the historical holdout is inspected for this fixed candidate. The plan
was recorded before fitting and thresholds are unchanged. The historic holdout
was already exposed in prior stages; this is remediation evidence, not a new
pristine test or a claim of future stability.

| Resort diagnostic | Original | Calibrated challenger |
| --- | ---: | ---: |
| Validation predicted/observed | 0.7134 | 1.1074 |
| Holdout predicted/observed | 0.6817 | 1.0302 |
| Holdout ECE | 0.0990 | 0.0142 |
| Holdout Brier | 0.1776 | 0.1660 |
| Holdout AUPRC | 0.6279 | 0.6279 |

The challenger passes all original thresholds; City predictions are untouched.
The adapter rejects wrong base-model hashes, the seven-day horizon, unknown hotels
and malformed probabilities. This corrects booking-horizon probabilities, not
capacity, inferred parties, seven-day policy risks or manager authority.

Original service/registry aliases and baseline gate are retained. A separately
named calibrated research challenger is logged to MLflow and its raw request
adapter is checked against the corrected probabilities on all 13,179 Resort test
bookings. It has no production champion promotion. Do not describe the unchanged
original model as having passed its original gate.

## Briefing correction and retained development evidence

V1 remains at 27/30 ordinary nights. V2 was stopped after 13 original-regression
responses with date/policy copying errors, before the new dates. V3 was stopped
after 44 responses with further date/string errors. V4 constrained source strings
but was stopped after 50 responses because a no-KB number was still wrong. Their
raw responses, partial-run counts and reasons are retained. None is relabelled PASS.

The accepted V5 component gives code ownership of numerical facts: it copies the
trusted context into the final fact table and asks the local model for a four-field
interpretation (action, KB prepaid status, draft message and approval requirement).
The model cannot supply replacement quantities. Extra numeric fields are rejected;
there is no hidden post-generation repair or expected-answer lookup. Unit tests
exercise previously unseen source values and reject numeric overrides.

This changes the numerical factuality claim: **delivered component exactness**,
not perfect raw-model numeric copying. The LLM still performs real local grounded
interpretation. Every raw response and assembled output is recorded separately.

V5 ran 96 requests: 30 original nights as regression, 30 different calendar dates
with KB, the same 30 without KB, and six notes attacks. New dates exclude every
date planned for V1/V3/V4, not just the dates where a response was inspected. All
90 ordinary cases passed the complete contract, including 30/30 original and
30/30 additional nights. Five attacks returned correct outputs; one raw model
action was wrong and was withheld. Thus all six delivery-safety tests pass while
the raw-model all-case gate remains FAIL (95/96 accepted). This distinction is
intentional: resistance is enforced by validation, not claimed as perfect model
behaviour. The public `briefing_revision.generate` entry point returns only
validated briefings; an invalid interpretation stops delivery.

Median component latency is 1.56 seconds and p95 2.10 seconds in this single local
run. API cost is EUR 0; energy was not measured. This is a different output
contract from V1, so it is not an equivalent-task model speed benchmark.

`make remediation-check` verifies the calibrated challenger and safe-delivery
briefing with the software tests. `make ci` still reproduces the deliberately
unchanged original reference failures. `make coursework-release-check` additionally
requires a valid, digest-bound simulation sign-off.

## Coursework review status

The concrete review packet is `reviews/coursework-policy-review-v1.json`. The user
selected coursework simulation review but asked to leave reviewer name/reason
for now. No formal sign-off record was created. The packet retains zero authorised
extra rooms, no automatic relocation and no guest messages. A real hotel manager's
operating sign-off remains a separate requirement. Do not treat an unsigned
coursework packet as that approval.

## Reproduction

The separate calibrated research model is registered as
`task19-resort-booking-calibrated`, alias `challenger`, without changing either
original hotel's aliases or its service bundle. The loaded adapter reproduced
all 13,179 Resort held-out probabilities exactly. See the calibration MLflow JSON.
The V5 run is in experiment `task19-briefing-remediation`, with all development
failures retained as artifacts. The local model was stopped after recording.

Ubuntu verification is pending. The transfer script recomputes calibration from
the original local data/model, compares metrics to Mac within 1e-12, replays V5
without any LLM/network access, and verifies that the existing demo/registry/core
KB were untouched. It reports the unsigned review as pending, not approved.

Sources: supplied notebook calibration code and
https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
(disjoint model-fitting and calibration data).

## Ubuntu confirmation

The user supplied output ending `REMEDIATION_UBUNTU_VERIFIED`. The calibrated
challenger passes with Resort ratio 1.0302477572464026 and matches Mac within
1e-12. All 234 software tests pass, six database tests skip, and SHACL conforms.
The Mac local-model fixtures replay offline: 90 ordinary cases exact; all six
attack deliveries safe, including one withheld raw action. No LLM was invoked
on Ubuntu. Existing serving/registry/core-KB files are unchanged. Original
reference failures remain visible. Coursework sign-off remains pending at the
user's request. The pasted transcript is saved and labelled; native evidence
files should now be copied back from Ubuntu.
