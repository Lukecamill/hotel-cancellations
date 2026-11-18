# Measured online and batch capability comparison

Updated 18 November 2026. This supersedes the earlier illustrative human-versus-automation comparison for Diary 1 task 5. It does not change the model, live service, nightly policy or human approval. The earlier version remains in Git history.

The decision being compared is when to compute **booking-to-arrival scores**: immediately through HTTP, or in one daily batch. Both consume identical raw records through Predictor.predict and the same trusted model. The task's seven-day nightly policy is a separate calculation and remains human-approved.

## Side-by-side evidence Online versus daily batch booking scores

Both alternatives produce the same booking-to-arrival probabilities. The seven-day overbooking policy and human approval remain separate.

| Criterion | Online booking prediction | Daily batch booking prediction |
| --- | --- | --- |
| Latency budget | Existing 250 ms response budget; new loopback p95 22.48 ms on 325 requests at 5/s | 0.013 s median to load and score the same 325 records over five repeats; up to 24 hours scheduling wait, requiring an owner-approved deadline |
| Running cost/day | Dedicated 24-hour allocation: EUR2.40 at assumed EUR0.10/hour; measured CPU 4.978 s for this workload | One-minute-minimum on-demand scenario: EUR0.0017/day at the same assumed rate; measured CPU 0.013 s. Shared always-running host gives EUR0 invoice saving |
| Decision owner | Model/service owner maintains score path; revenue manager still approves nightly oversell | Same accountable owners; batch scheduler publishes scores, never authorises oversell |
| Failure behaviour | Invalid/unavailable request fails visibly; standalone logging is best effort; no approved quantity follows from a score | Failed/missing job leaves scores unavailable or stale; prospective consumer must reject stale versions; no automated approval |

Measured fit, online and batch values: E8. Batch and HTTP predictions match within 1e-12. New local tests exclude PostgreSQL, external networks, live PMS and human review; historical Ubuntu p95 remains 34.25 ms with database logging. Observed reconstructed 2016 entries/day: mean 160.0, p95 324.5, maximum 818. The selected actual day has 325 entries. Compressing it to 5/s is a stress envelope, not observed interarrival timing. Pricing, billing minimum and dedicated/on-demand hosting are explicit assumptions, not measured bills; labour, energy and ownership costs are unmeasured. Switching requires both an acceptable daily deadline and actual avoidable costs.



## Reproduction

Run `.venv/bin/python scripts/measure_diary1.py --output docs/evidence/diary1/review-measurements.json` from the project root. A temporary processed cache avoids rewriting the original cache. The script retrains once with the prescribed recipe, times only fit, verifies reference metrics, runs an isolated localhost HTTP server on an ephemeral port, and compares the same records with five batch repeats. No database or live model endpoint is contacted. It checks serving hashes before/after and does not save or promote the fitted learner. Keep historical Stage 7 persistence/load evidence separate.

## Decision and reversal condition

Retain online scores where an immediate response is needed, because the measured p95 fits the 250 ms budget. A batch-only score path becomes appropriate only if its owner accepts up to a day of staleness and actual avoidable compute costs exceed scheduling/operations costs. At the stated illustrative rate, the dedicated-versus-on-demand difference is EUR2.3983/day; on the same running VM, the assumed invoice saving is zero. This is a conditional architecture estimate grounded in measured time, not an observed hosting or staffing bill. Human-versus-automation economics cannot be claimed without measured review effort and outcomes.
