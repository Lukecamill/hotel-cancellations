# Stage 4: data validation and leakage guards

Completed 7 November 2026 against the supplied 119,390-row dataset. **64 tests passed**, the all-data baseline-equivalence check passed exactly, and the complete guarded baseline ran successfully with all 20 saved-output comparisons passing. No dependencies, features, model settings or baseline result values changed.

## Six traps and guards

| Trap | Measured evidence | Guard and tests |
|---|---|---|
| 1. Outcome leakage | Status matches the label in 119,390/119,390 rows; 1,207 no-shows | Outcome frame separated; feature function restricts access to approved raw inputs; exact output schema and individual forbidden-input mutation tests |
| 2. Random-split duplicates | 31,994 extra duplicates; 4,743 distinct shared signatures in random train/test; zero forward overlap | Training validates ordered, disjoint, exhaustive temporal masks and duplicate isolation across every partition pair; deliberate bad-split tests |
| 3. Post-booking fields | 7,416 parking-positive rows, zero cancelled; other positive-field counts saved | Assigned room, changes, parking, requests and waiting time unavailable inside feature construction; mutation and approved-input-only tests guard even derived aliases |
| 4. Nationality artefact | Offline cancelled: 8,121/8,311 PRT (97.71%); arrived: 3,864/15,908 (24.29%) | Country excluded from allowed inputs; mutation test changes it independently; no ethnicity/nationality proxy features added |
| 5. Incorrect ADR | One negative, 1,959 zero rates, maximum EUR5,400 | Extracted named nightly-median room-value helper; tests distinguish local medians from global means and floor nonpositive contribution to zero |
| 6. Wrong-horizon probability | Booking cancellation and remaining cancellation are separate quantities | Calibrator carries lead time and rejects reuse at a different horizon; policy boundary requires an explicit decision-horizon forecast, rejecting untagged booking probabilities, mismatched horizons, invalid probabilities and inconsistent block sizes |

The 4,743 duplicate statistic counts distinct shared full-row signatures, not the fraction of held-out rows with twins. It is not the 31,994 extra-row count. Exact duplicates are evidence of dependence, not proof of a shared group identity.

The horizon tag is a programming contract, not proof that numbers are calibrated: a caller could deliberately mislabel values. The packaged model policy obtains them from the fitted horizon calibrator, and equivalence checks preserve the supplied recipe. Statistical calibration monitoring and acceptance thresholds remain later work.

## Historical as-of reconstruction

`history.reconstruct_as_of` separates membership and retrospective late labels from the booking-feature frame. It preserves the notebook’s exact boundaries:

- Decision date = arrival minus configured lead days.
- Only bookings entered strictly before the decision date are live.
- Cancellations strictly before the decision date are removed.
- Cancellation/no-show on the decision date is retained and counted as late.
- Noncancelled bookings remain live if entered earlier.
- Bookings/outcomes must have identical unique ordered indexes.

Boundary tests cover entries before/on/after the cutoff; cancellations before/on/after it; no-show-equivalent cancellation labels on arrival; outcomes changing after the cutoff; horizons 0, 7 and 14; invalid horizons and index misalignment. The full dataset also passes membership invariants for every horizon from 0 through 14 days. Counts per hotel/horizon are in [data-checks.json](evidence/stage4/data-checks.json).

At the baseline seven-day horizon, reconstruction retains 61,761 bookings, matching the original snapshot. This tests the implemented retrospective convention, not the truth of a historical PMS state. Dates have day resolution, so intraday ordering is unknowable; same-day treatment is an explicit convention. Lead time, arrival/stay/price and retained categories may themselves reflect later changes. The file has no booking ID or event history to recover their earlier values. Status dates are used only to reconstruct membership and late evaluation labels, never as prediction features. Prospective reconstruction requires timestamped PMS events and stable booking IDs.

## Raw-data contract and handling

See [data-contract.md](data-contract.md) for exact hard checks, accepted anomalies and failure response. Invalid batches fail before training; known notebook anomalies are counted and retained rather than silently dropped. Cache reuse now verifies raw/transform/window identity and cached bytes, and never bypasses raw validation.

## Reproduce the checks

From the working repository:

```bash
.venv/bin/python -m pytest -q
make data-check
.venv/bin/python scripts/verify_extraction.py
make baseline
```

`make data-check` writes the versioned contract summary, counted quirks, temporal overlap results, forbidden-input mutation results, horizon counts and source provenance under `docs/evidence/stage4/`. It does not fit a learner. `make baseline` now enforces raw contract, feature boundaries, temporal partition guards and probability-horizon checks automatically. The test suite does not require the dataset; the counted audit and equivalence commands do.

## Evidence and remaining boundaries

- [Test output](evidence/stage4/tests.txt): 64 passed.
- [Raw/data checks](evidence/stage4/data-checks.json): passed with counted exceptions.
- [Baseline equivalence](evidence/stage4/baseline-equivalence.json): original feature frame, metrics, fingerprint, summaries and example-night fields match exactly.
- [Guarded saved-run comparison](evidence/stage4/baseline-comparison.json): 20 passed for run `20261107T124508Z-f8e71b6f`.

Base commit: `e3605b4fe930f87ad16f9750f5248eb379dd5fcd`. Stage 4 implementation/evidence were uncommitted at verification; per-source hashes are recorded. Commit these changes before citing the code and evidence as a checkpoint. Stage 3’s previously committed evidence is preserved.

This stage adds reproducible checks and explicitly documents what cannot be established from this snapshot. It does not claim verified event-level history, verified group identity or production approval. The Resort’s diagnostic calibration failure remains unchanged. Cost/horizon sensitivity and resale belong to Stage 5; live API/database and deployment gate belong to later stages.
