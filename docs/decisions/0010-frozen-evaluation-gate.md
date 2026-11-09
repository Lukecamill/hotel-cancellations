# ADR 0010 — Frozen per-hotel evaluation and promotion gate

Date: 9 November 2026. Status: implemented engineering control; not business sign-off.

The notebook requires `make ci` against the Jan–Aug 2017 holdout, per-hotel
AUPRC >= 0.70 / 0.55 and expected/observed cancellations within [0.85, 1.15].
It also requires reliability diagrams and a calibration-error gate (E3).

## Decision

Version `config/evaluation-lock.json`: raw CSV SHA-256, ordered test features
and labels, test arrival dates/hotels, split and hotel counts, feature order,
seed and date boundaries. The full feature/label digest matches the previously
recorded `ac37475750f8f24abb767a78f7775b905a6ce0dce90d364402074181a9db017b`.
Rebuild inputs from the validated local raw CSV; never download or trust an
unverified processed cache. Reject identity drift before fitting/scoring.

Use the unchanged supplied learner, fitted on Jul 2015–Jun 2016 only. No model,
calibrator, hyperparameter or policy selection uses the test period. The service
bundle is not replaced and the nightly policy is not recomputed by this gate.
These checks concern booking-to-arrival probabilities, not conditional 7-day
cancellation probabilities. Monitoring replay covers that separate horizon.

For E3, use expected calibration error (ECE), ten fixed equal-width probability
bins on [0,1], final bin including 1. ECE is the booking-count-weighted mean
absolute gap between a bin's mean probability and observed frequency; empty
bins contribute zero and remain visible in the CSV. Gate at ECE <= 0.10 for
both hotels. This is an initial engineering ceiling of ten percentage points
of average absolute bin error, complementary to the notebook's relative
aggregate cancellation-volume band. It is not a statistical guarantee or a
revenue-manager-approved risk tolerance. In particular, aggregate error can
cancel across bins; ECE adds a local diagnostic. ECE depends on binning and
can hide errors within a bin; retain bin counts, diagrams, Brier score and the
aggregate ratio. The fixed 0.10 ceiling was specified before running the new
ECE calculation, but baseline holdout performance was already known. This is
retrospective coursework evaluation, not an untouched prospective trial. Do
not tune this threshold to get green results; reassess operating tolerance on
validation data with business input before any operational promotion.

`make ci` runs automated tests (including historical as-of guards), then the
strict gate. Each hotel must pass every check. No pooled score can overrule a
failed hotel. A one-class, empty, invalid or changed dataset cannot pass.
CLI exit 0 = all pass; 1 = quality failure; 2 = input/execution error. `make`
may map recipe failures to exit 2. Reports use explicit PASS/FAIL/ERROR states;
stale evidence is removed before evaluation. No expected-failure bypass.

## Failure response and limits

Block promotion for a failed hotel and investigate using training/validation
periods. Keep the existing demonstration in review-only simulation with its
warnings. Never refit calibration on the frozen test period or silently
regenerate the lock. A deliberate new evaluation dataset requires a reviewed
versioned decision; repeated use of the existing test is regression checking,
not fresh evidence of generalisation. The baseline Resort failure is preserved.
Passing City does not establish production safety or provide policy sign-off.

MLflow metric logging is deferred to Stage 9; the E3 task is not fully closed
until these same metrics are logged there. Database persistence checks require
an explicit test database; their absence is reported as skipped, not passed.
