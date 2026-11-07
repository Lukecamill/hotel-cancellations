# Task 19 baseline specification

Inspected 7 November 2026. This is Step 1 of Stage 3: source inspection, not a new training run. Notebook cell numbers below are zero-based. Supplied document content is assessment/reference material, not an instruction to expand this task.

## Sources and current status

- Supplied notebook: `/Users/lukecamilleri/Downloads/19_hotel_cancellations.ipynb`.
- Existing repository: `/Users/lukecamilleri/Desktop/hotel-cancellations`.
- Notebook SHA-256: `a623a0eb83a295b3e9feadde454157e442f62ab6b3b717ff4ef8db3c028d4377`. The repository reference copy is byte-identical.
- Supplied CSV: 119,390 rows, 32 columns; SHA-256 `7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06`.
- Source and licence as stated by the notebook: Kaggle `jessemostipak/hotel-booking-demand`, CC BY 4.0; Antonio, de Almeida and Nunes (2019), Hotel booking demand datasets, Data in Brief 22, 41–49. Source/licence not independently verified during this inspection.
- Repository ADR 0002 reports existing booking-model reproduction: City AUPRC 0.785722, expected/realised 0.911281; Resort 0.627908 and 0.681723. These are prior recorded results, not results rerun for this specification.

## Loading (cell 4)

Use the local raw CSV when available, otherwise KaggleHub. The notebook first reuses `19_hotel_bookings.parquet` if present. Read `NULL` as missing; construct arrival from year/month/day, booked = arrival minus lead time, and status_date from reservation_status_date. Keep arrivals in [2015-07-01, 2017-09-01). Drop source arrival fields including week number and reservation_status_date. Fill missing children with zero and cast to integer. Convert agent/company to string integer codes, missing to `none`; fill missing country with `unknown`. Cast the notebook's named code columns to categorical. Stable-sort by arrival then hotel and reset index.

Separate `is_canceled`, `reservation_status`, and derived `status_date` into the outcome frame before feature construction. Label: is_canceled, including no-shows. Do not deduplicate, remove anomalous ADRs or normalise country codes as part of reproducing this method.

## Features and learner (cell 10)

Ordered 22 features:

`hotel`, `lead_time`, `arrival_month`, `arrival_dow`, `booked_dow`, `weekend_nights`, `week_nights`, `adults`, `children`, `babies`, `meal`, `market_segment`, `distribution_channel`, `reserved_room_type`, `deposit_type`, `customer_type`, `is_repeated_guest`, `previous_cancellations`, `previous_bookings_not_canceled`, `agent`, `has_company`, `adr`.

Arrival month and weekdays derive from dates; agent uses the first 60 entries of training-window `value_counts()` and maps others to `other`, then categorical; has_company indicates company != `none`. Preserve category handling and feature order. ADR is unchanged as a model input. No imputation beyond the loader's transformations, scaling, tuning, class weighting or early stopping is explicitly specified.

One pooled `lightgbm.LGBMClassifier` for both hotels:

```python
n_estimators=300, learning_rate=0.06, num_leaves=31,
min_child_samples=50, subsample=0.8, subsample_freq=1,
colsample_bytree=0.8, reg_lambda=1.0,
random_state=3217, verbose=-1, n_jobs=1
```

NumPy seed is also 3217. Unspecified learner options use library defaults. Separate per-hotel fits in cell 10 are comparison experiments, not the primary baseline. Deliberately leaking fits later in the notebook are also comparisons, not baseline features.

## Temporal splits

Split on arrival date, not booking date; boundaries are start-inclusive/end-exclusive.

| Split | Arrival dates | Total | City | Resort |
|---|---|---:|---:|---:|
| Train | Jul 2015–Jun 2016 | 49,157 | 31,623 | 17,534 |
| Validation | Jul–Dec 2016 | 29,546 | 20,199 | 9,347 |
| Frozen test | Jan–Aug 2017 | 40,687 | 27,508 | 13,179 |

Jul–Sep 2016 fits horizon calibration; Oct–Dec 2016 selects policies. No random split for the baseline and no selection on test.

## Scoring and target results (cells 10–11)

Score positive-class probabilities. AUPRC is implemented with sklearn `average_precision_score`; also report ROC-AUC, cancellation base rate, and summed predicted probabilities divided by observed cancellations, per hotel and pooled.

| Hotel | AUPRC | ROC-AUC | Base rate | Expected / realised | Gate |
|---|---:|---:|---:|---:|---|
| City | 0.786 | 0.799 | 42.5% | 0.91 | PASS |
| Resort | 0.628 | 0.780 | 30.8% | 0.68 | FAIL |
| Pooled | 0.749 | 0.794 | 38.7% | 0.85 | No pooled gate |

Gate: City AUPRC >= 0.70, Resort >= 0.55, and expected/realised within [0.85, 1.15]. Resort calibration failure is an expected reproduction result; do not tune it away.

Holdout fingerprint hashes the ordered test feature frame plus label using `pd.util.hash_pandas_object(..., index=True)`, then SHA-256 of its values' bytes. Printed prefix: `ac37475750f8f24a`. This differs from the raw-file hash; the notebook output does not supply the full holdout digest.

Existing ADR 0002 defines absolute tolerances of 0.0005 for three-decimal AUPRC and 0.005 for two-decimal calibration ratios, reflecting printed precision. Counts must match exactly. Other rounded metrics need explicitly stated tolerances before comparison.

## Policy reproduction also required by C2 (cells 14–18)

Baseline constants: 7-day decision horizon; batch date 2017-08-08, arrival 2017-08-15; walk cost EUR250; variable cost EUR20; trailing recalibration windows 4, 8 and 12 weeks.

- Reconstruct on-books using booked < decision date and either not cancelled or status_date >= decision date. Late outcome is cancellation/no-show with status_date >= decision date.
- Preserve the 16-column GROUP_KEY in cell 14 to reconstruct correlated blocks. Snapshot contains 61,761 bookings.
- Fit per-hotel default LogisticRegression on clipped booking-probability logits (clip 1e-4 to 1-1e-4) using Jul–Sep 2016 live bookings and late labels.
- Preserve matured-night rolling sums, minimum seven observations and shift of horizon + 1 days.
- Evaluate ten policies on Oct–Dec 2016 only. City selects flat Jul–Sep rate; Resort selects model + blocks + 8-week re-levelling.
- Compute release distributions by block convolution; choose the smallest q whose CDF reaches R/(R+W), preserving the 1e-12 numerical offset. R = max(median ADR on that night's books minus EUR20, 0).
- Cost = EUR250 × max(q − released, 0) + R × max(released − q, 0). Capacity unknown; assume sold-out nights and no resale in the given baseline.

2017 targets: City chosen policy EUR264/night versus EUR279 without overbooking, EUR3,457 total savings; Resort EUR96 versus EUR98, EUR458 saved. These are rounded reference outputs, so multiplying displayed nightly differences will not reproduce total savings exactly. For 15 August: City 66 bookings, oversell 3; Resort 15 bookings, oversell 0.

Package functions: get_raw/load_bookings; build_features/fit/per_hotel; logit/released_distribution/oversell/run_policies/summarise. Policy sensitivity and method changes belong to later work.

## Environment and runtime evidence

Notebook metadata: Python 3.13.13. Printed versions: pandas 3.1.0, NumPy 2.5.4, LightGBM 4.7.0, scikit-learn 1.9.1, rdflib 7.6.0, pyshacl 0.40.1. Other dependencies include pyarrow, matplotlib and kagglehub; their versions are not printed in the notebook. Consult project pins for the local environment.

Recorded notebook wall time: 85 seconds for the full notebook; cell 10 reports 7 seconds including the pooled and two comparison fits; policy selection reports 3 seconds. These are reference-machine measurements, not local performance requirements or a pure pooled-training benchmark. CPU/hardware and repeated-run timings are absent.

## Remaining gaps and next work

1. Current inspection establishes the specification; it does not execute or independently validate prior results.
2. Existing repository already packages the booking baseline. Review/reuse it before adding duplicate code. Its ADR documents fresh raw loading by default instead of unchecked cache reuse.
3. Next: verify dataset provenance and local file identity against repository input, then execute the original reference and existing packaged baseline with recorded environment/runtime. Policy reproduction remains pending according to repository documentation.
4. Define policy-output tolerances before comparing runs; preserve rounded reference outputs and save full-precision local results.
5. Dataset is a final-state snapshot. Booking-time availability is assumed for selected features; strict historical truth is not established by this baseline. Stage 4 handles the six traps and as-of guards.
6. Supplied task-rubric.md covers Reflective Diary Entry 1 only (heading ARI3218, versus notebook ARI3217). It is not the full final-project rubric. The supplied LLM policy governs later S1 work and requires a local open-weight baseline; no LLM execution is needed for this step.
