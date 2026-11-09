# Model card — Task 19 hotel booking cancellation baseline

Version: 9 November 2026. Owner: individual coursework project; business approval pending.

## Purpose and model

Estimate whether a booking will cancel or become a no-show before arrival.
The supplied pooled LightGBM classifier serves City Hotel and Resort Hotel.
It has 300 estimators, learning rate 0.06, 31 leaves, minimum 50 samples per
leaf, row/column subsampling 0.8, lambda 1, seed 3217 and one training thread.
No model redesign, tuning or calibration fitting is introduced in Stage 9.

The registered model accepts the same 20-field booking request contract as
`examples/predict.json` and returns `cancellation_probability`. Each registry
entry enforces its named hotel; both wrap the same pooled learner. Learned
agent vocabulary, feature order and the original model bundle travel with it.
Country and all outcome/post-booking fields are rejected by the HTTP request
contract and excluded from the registered input signature. MLflow may discard
extra columns before invoking the adapter; use the HTTP contract for strict
unknown-field rejection. HTTP error handling remains in the existing service, not MLflow.

## Data, timing and provenance

Hotel Booking Demand, Kaggle `jessemostipak/hotel-booking-demand`, CC BY 4.0;
Antonio, de Almeida and Nunes (2019), *Hotel booking demand datasets*,
Data in Brief 22, 41–49. See dataset.md for attribution and acquisition.
119,390 rows; a final-state snapshot, not a booking-event history.

Arrival boundaries are inclusive at start and exclusive at end:
training Jul 2015–Jun 2016 (49,157); validation Jul–Dec 2016 (29,546);
frozen test Jan–Aug 2017 (40,687). Agent vocabulary is learned on training
only. Separate saved Platt horizon calibrators use Jul–Sep 2016; saved
policy selection uses Oct–Dec 2016. Booking-horizon probabilities must not
be treated as active-seven-day late-cancellation probabilities.

Raw SHA-256: `7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06`.
Frozen ordered feature/label SHA-256:
`ac37475750f8f24abb767a78f7775b905a6ce0dce90d364402074181a9db017b`.
Serving reference run: `20261107T124508Z-f8e71b6f`.
Model bundle SHA-256:
`b921b8c3f829e4364f84ea857e8018bf996e58165b44064288b94ff62f46eff5`.
MLflow logs effective configuration, current source hashes, Git state, original
run identity, package versions, model/policy hashes and the evaluation lock.
Current evaluation code is distinguished from original training lineage.

## Frozen evaluation

| Hotel | Test n | AUPRC | Expected/observed | ECE (10 bins) | Brier | Gate |
|---|---:|---:|---:|---:|---:|---|
| City | 27,508 | 0.785722 | 0.911281 | 0.042275 | 0.172397 | PASS |
| Resort | 13,179 | 0.627908 | 0.681723 | 0.098961 | 0.177576 | FAIL |

Thresholds: AUPRC >= 0.70 City / 0.55 Resort; expected/observed [0.85,1.15];
ECE <= 0.10 for both. ECE is count-weighted absolute error in ten fixed
equal-width bins. Empty bins do not contribute; probability 1 is in the last
bin. ADR 0010 explains its initial engineering tolerance and limitations.
Stage 9 recomputes these metrics for the saved bundle, logs validation and
test values separately, and verifies persisted ECE readback in MLflow.
Repeated use of this holdout is regression checking, not a fresh independent
generalisation claim. No test-set tuning, retraining or calibrator refitting.

## Operating policy and registry decisions

The saved seven-day policy uses per-night median ADR minus EUR20 variable
cost, floored at zero, with EUR250 walking cost and 4/8/12-week recalibration
options. City selected the Jul–Sep flat rate; Resort selected model + blocks
+ eight-week re-levelling. Historical Jan–Aug test cost proxies are about
EUR264.42/night City versus EUR278.65 with no overbooking, and EUR96.18/night
Resort versus EUR98.07; those are simulations assuming sold-out arrival nights
and no resale, not measured live profit. Save policy sensitivities separately.

Each hotel has a `challenger` alias for the tracked reference. City can
bootstrap an offline `champion` after passing all frozen gates. The initial
City champion and challenger may be the same version: no distinct improved
model is invented. Resort has **no champion** because its aggregate calibration
fails. A future passing candidate can bootstrap its champion; existing
champions are never automatically replaced. Aliases do not authorise release,
change serving or replace revenue-manager policy-wide sign-off.

## Known limitations and harms

- Final-state feature values do not prove booking-time availability. The PMS
  event history would be needed for strict event-time reconstruction.
- Nationality has a strong channel-related artefact and is excluded from
  predictions and relocation decisions. Diagnostic associations are not
  evidence of a nationality effect. Full walking fairness/legal work is Stage 11.
- Non Refund bookings have paradoxically high recorded cancellation rates;
  the label includes administrative/tour-operator block releases and no-shows,
  and does not prove lost collected revenue.
- Exact duplicates and correlated group blocks invalidate naive random-split
  confidence. Forward splits and overlap guards preserve the given baseline.
- ADR includes zero/negative anomalies; it is preserved in model features.
  Policy revenue uses a nightly median and floor, not a global average.
- Capacity, actual inventory, resale and occupied room-nights are not known.
  Arrival-night cost proxies cannot establish feasible real-world overselling.
- Resort underestimates aggregate cancellations; passing an ECE ceiling does
  not excuse that failure. Calibration can vary by season, segment and horizon.
- Snapshot vintage (2015–2017), seasonal shifts, delayed outcomes and unknown
  new codes limit use in a contemporary hotel. Human review is not itself a
  guarantee of correctness. No real guest relocation is authorised.

## Monitoring, response and lifecycle

Monitor service request count/errors/latency and prediction-log loss separately
from mature cancellation quality. Review per-hotel weekly expected/observed
outside [0.85,1.15] with at least 30 bookings and 20 observed cancellations;
report lower volume as inconclusive. PSI 0.10 prompts investigation, 0.25
prompts action review. Historical replay is labelled historical, not live.
See ADR 0008 for full triggers, latency budget and label maturity rules.

On failure: block promotion; use human handling/no-overbooking fallback;
inspect data contract, source drift and label maturity. Consider only permitted
past-data recalibration/seasonal retraining, validate separately, rerun frozen
gates and obtain policy/business approval. Never tune on the frozen test,
automatically replace champions, or promote Resort because the failure is
expected. Retain the prior version and audit trail for rollback. No production
PMS data, credentials or booking rows are uploaded by Stage 9; the registry is
local SQLite with local artifacts. Protect/backup that store separately from Git.
