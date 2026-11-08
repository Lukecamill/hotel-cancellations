# Diary 1 additional investigation — recorded stay end versus Check-Out status date

Investigated 8 November 2026. This completes the additional data-quirk investigation, not the full diary. The notebook's known-quirk list does not identify or count this cross-field relationship. It is an additional check on the final-state data limitation, not a claim to have discovered an unknown issue in the published dataset.

## Question and check

For a booking whose final status is `Check-Out`, does the date of that status agree with arrival plus recorded weekend and week nights?

```text
recorded_nights = stays_in_weekend_nights + stays_in_week_nights
derived_stay_end = arrival + recorded_nights days
flag = reservation_status == 'Check-Out'
       and reservation_status_date != derived_stay_end
```

The source paper's Table 1 defines ReservationStatusDate as the date the last status was set and explains that it can help identify checkout timing. It describes both stay-night variables as nights stayed **or booked to stay**. Therefore, equality is a diagnostic expectation if someone interprets those fields as realised occupancy, not an unquestionable database invariant. An early departure, an unamended planned duration, a status-update convention or a recording error could explain a mismatch; the CSV cannot determine the cause. [Antonio, de Almeida and Nunes (2019), Hotel booking demand datasets](https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/), DOI: 10.1016/j.dib.2018.11.126.

## Counted evidence

The supplied 119,390-row CSV contains 75,166 `Check-Out` rows.

| Finding | Count |
|---|---:|
| Check-Out status date differs from the stay-derived end date | 27 |
| Resort / City | 21 / 6 |
| Distinct complete records among flagged rows | 24 |
| Status date is arrival day despite positive recorded nights | 26 |
| Remaining case: status date one day after arrival, recorded stay nine nights | 1 |
| Flagged rows with zero recorded nights | 0 |
| Recorded stay lengths among flagged rows | 1–14 nights |

The 27 rows represent approximately **0.036% of Check-Out rows** and **0.023% of all rows**. Three are additional copies of other flagged complete records; do not interpret them as 27 proven distinct guests. One row also has zero guests, but all 27 have positive nights, so this is not merely a recount of the notebook's zero-night issue.

| Split | City | Resort | Total |
|---|---:|---:|---:|
| Train, July 2015–June 2016 | 2 | 11 | 13 |
| Validation, July–December 2016 | 0 | 10 | 10 |
| Frozen test, January–August 2017 | 4 | 0 | 4 |

An observed example is a Resort arrival on 1 July 2015 with seven recorded nights but a Check-Out status date of 1 July, rather than the derived end date of 8 July. It illustrates the discrepancy; it does not prove that no room was occupied or that the guest cancelled.

Exploratory chronology checks also found **zero** cancellation-status dates before the booking date inferred from lead time and **zero** cancelled/no-show status dates after arrival. These negative findings are recorded to show what was checked; they are not additional claimed quirks.

## Consequence and safeguard

**Cancellation model:** preserve all rows and their original `is_canceled=0` labels. A Check-Out date discrepancy is not evidence that a booking should be relabelled cancelled. No change to the given features, learner, training or policy selection is made. The status-derived audit fields remain outside model inputs. No performance improvement from removing or changing these records has been measured or claimed.

**Operational/revenue interpretation:** do not assume recorded stay length is a verified count of occupied room-nights. Such an assumption could distort an occupancy reconstruction or a realised-revenue calculation. The current project already uses an arrival-night sold-out proxy; this finding adds specific evidence for why it must not be described as a full room-night inventory system. Do not count these records as released rooms based on this check alone.

**Implemented check:** `hotel_cancel.stay_audit.checkout_date_checks` counts and flags the relationship without mutating input. Tests distinguish a consistent stay, same-day checkout with positive nights, shorter status-date gaps, cancelled records and valid zero-night cases. Relevant audit, raw-contract, history and feature tests: **38 passed**. This is a diagnostic audit safeguard, not a new production quarantine or a change to the raw contract.

**What would resolve the uncertainty:** timestamped check-in/out events, planned-versus-actual departure fields and clarification from the PMS/data owner. Those could support correcting a genuine recording error or accepting a documented operational exception. The final-state CSV alone is insufficient.

## Reproduce and commit

```sh
.venv/bin/python -m hotel_cancel.stay_audit
.venv/bin/python -m pytest -q tests/test_stay_audit.py tests/test_contracts.py tests/test_history.py tests/test_features.py
```

- `docs/evidence/diary1/additional-quirk.json`: counts, source/dataset/notebook hashes, base commit and working-tree state.
- `docs/evidence/diary1/additional-quirk-counts.csv`: aggregate hotel/split counts.
- `artifacts/diary1/checkout-date-discrepancies.csv`: local flagged records for inspection, excluded from Git.

Commit the audit module, tests, report and aggregate evidence together before citing this investigation. The JSON identifies the existing base commit and records that the investigation had uncommitted changes when generated; the subsequent commit should identify the completed investigation. This audit inspects all splits for data quality and does not use the holdout to choose a model or tune a policy.

For your own diary reflection, consider which assumption you expected to hold, why these counts challenged it, and what event-level evidence would change your interpretation. The diary's reflection should express your own reasoning rather than present a suggested reaction as something you personally experienced.
