# Stage 5 — overbooking policy evaluation

Implemented 7 November 2026. Status: computational evaluation complete; revenue-manager sign-off pending. These are retrospective validation results, not a live operating authorisation.

## Reproduce

From the repository root, after installing the pinned requirements and obtaining the attributed raw dataset:

```sh
make policy-sensitivity
.venv/bin/python -m pytest -q
```

`config/stage5.yaml` fixes the sensitivity grid. `config/config.yaml` supplies the existing training and validation boundaries. The command refits the unchanged booking learner using arrivals before July 2016; removes 2017 rows and unused category levels before feature construction, prediction and policy evaluation; and writes CSV and JSON evidence under `docs/evidence/stage5/`. The loader still validates the full source CSV and writes its ordinary local cache. No test metrics or test policy costs are consulted by the sensitivity command.

## Experiments and temporal safety

- Lead times: every integer from 0 to 14 days, with a separate horizon calibrator for each hotel and horizon.
- Walking costs: €100, €200, €250, €300 and €500 per excess guest-room booking.
- Variable costs: €0, €20 and €40 per occupied room-night.
- Resale rates: 0%, 25% and 50% recovery of residual empty-room margin.
- Rolling recalibration windows: 4, 8 and 12 weeks; compare fixed rate, trailing rates, independent model, correlated blocks and re-levelled blocks against no overbooking. Ten candidates per scenario.
- Select separately for each hotel and scenario on 1 October–31 December 2016: 92 arrival nights per hotel. There are 675 economic/horizon scenarios, 1,350 hotel/scenario selections and 13,500 candidate summaries.

For horizon h, the initial calibration period begins 1 July and ends **exclusively at 1 October minus (h + 1) days**. This conservatively ensures its arrival-night outcomes have matured before the earliest October decision. At h=7, the cutoff is 23 September. Rolling sums retain the notebook's h+1 day shift and minimum seven daily observations. Same-day bookings remain excluded and same-day cancellations remain live/late, as defined in Stage 4. The fixed-rate candidate retains the original “Jul – Sep 2016” name, but uses this shorter mature calibration window.

At each night, q is the smallest quantity minimising forecast expected walking plus empty-room cost. Blocks share a single cancellation event, with mean member probability, preserving the notebook's perfect within-block dependence assumption. q=0 is included in selection and wins equal-cost ties. Actual validation releases score each candidate. Horizons are reported as separate business scenarios: they have different on-books populations, so their absolute costs must not be ranked as equivalent operating interventions.

## Resale model

Let R = max(nightly median ADR − variable cost, 0), W = walking cost, X = released rooms, and s = resale rate. Use effective empty-room loss R' = (1−s)R:

`cost(q, X) = W max(q−X, 0) + R' max(X−q, 0)`

The decision quantile is R'/(R'+W). This relaxes the no-resale assumption through an exogenous expected margin recovery on residual empty rooms. It assumes replacement bookings earn the same margin and do not themselves cancel; there is no resale of already filled rooms and no added demand model. The CSV cannot estimate s, its lead-time dependence or replacement prices. The grid is scenario analysis, not measured resale performance. At s=1 the rule selects q=0; at s=0 it recovers the original cost equation.

## Reference scenario results

Validation only, h=7, W=€250, variable cost=€20, no resale. Values are per arrival night, rounded here; full precision is in the CSVs.

| Hotel | Selected candidate | Cost | Cost without overbooking | Saving | Walked rooms/night |
|---|---|---:|---:|---:|---:|
| City | Fixed calibration-window rate | €331.41 | €423.43 | €92.01 | 0.250 |
| Resort | Model + blocks + 12-week re-level | €38.92 | €42.21 | €3.29 | 0.000 |

At 25% resale, selected savings are €54.74/night for City and €1.26/night for Resort. At 50%, they fall to €24.17 and €0.84. Resort's winner changes to the independent model at 25% and the fixed rate at 50%. City switches to blocks with 12-week re-level at 50%. This instability and small Resort margin argue for conservative human review.

The un-relevelled horizon model's predicted/observed cancellation ratios at h=7 are approximately 0.46 (City) and 0.76 (Resort), with Brier scores 0.0915 and 0.0319. Horizon matching therefore does not establish reliable calibration. These diagnostics describe the initial horizon model, not each rolling policy's final probabilities.

## Evidence and interpretation

- `all-policies.csv`: every candidate's mean cost, walking, empty rooms, quantity and saving within its scenario.
- `selected-policies.csv`: deterministic per-hotel minimum-cost validation candidates.
- `calibration.csv`: per-hotel and horizon validation Brier score, rates and calibration ratio.
- `reference-validation-nights.csv`: all candidate nightly decisions and realised costs for the reference scenario, enabling paired comparisons.
- `run.json`: grid, data and source hashes, environment, runtime and explicit holdout exclusion.
- `baseline-regression.json`: the unchanged original baseline reproduces all 20 reference checks. That separate regression run scores the already specified baseline holdout; it does not select or assess these new Stage 5 candidates.

The same validation nights select and describe winners. Reported savings are optimistically selected and are not out-of-sample estimates, confidence bounds or evidence that any policy is safe. Do not choose economic assumptions to maximise reported savings. A manager must supply costs, resale evidence, acceptable walking risk and operational lead time before the selected candidate can be locked. No fresh Stage 5 holdout evaluation has been performed.

Capacity is unavailable; evaluation retains the sold-out-night assumption. The data represent arrival bookings rather than a full room-night inventory across multi-night stays. Final-state feature history and true group membership remain unverified; inferred blocks can overstate or understate dependence. ADR is a nightly median proxy, not realised incremental revenue. No guest relocation allocation rule is implemented here (Stage 11). These limits prevent a live overbooking recommendation.

See [decision record](decisions/0005-policy-sensitivity.md) for the manager review decision.
