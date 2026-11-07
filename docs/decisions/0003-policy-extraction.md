# ADR 0003: Extract the given policy without changing the method

Status: accepted, 7 November 2026.

## Decision

Preserve the original notebook as reference. Reuse the existing data, features, model, evaluation and training modules from ADR 0002. Add `hotel_cancel.policy` for the supplied cells 14–17, replacing notebook-global dependencies with explicit baseline/configuration arguments and returning a PolicyResult. Keep the notebook as imports, pipeline calls and displays.

Module-level functions expose logit, released_distribution, oversell, run_policies and summarise. run_policy_baseline orchestrates the original on-books reconstruction, per-hotel Platt fits, block aggregation, trailing recalibration, ten validation candidates, chosen-policy test scoring and example-night calculation. Policy calibrators and flat rates are returned alongside snapshots and results for later persistence.

Preserve formulae, row/group order, clipping, default logistic-regression settings, group keys, temporal boundaries and selection logic. Explicitly pass configured walking costs into helpers, replacing the notebook's global/default binding. Remove plots, print formatting and unused diagnostic aggregates only. No new features, learner, tuning, resale model or changed ADR treatment.

## Verification

16 automated checks passed, including analytical examples proving block correlation differs from independent-room releases and that walking cost changes the optimum. A full-data verification compared all 119,390 feature rows (including dtype/order), split counts, holdout fingerprint, booking metrics, policy choices, every policy-summary value and every example-night field against the original notebook function or captured full-precision execution evidence. All comparisons were exact. See docs/evidence/extraction-verification.json. This is extraction validation; the final Stage 3 report/command remains subsequent work.

The Mac editable-install hidden-file issue recorded in the README recurred. Verification used an explicit PYTHONPATH=src rather than changing model logic. The thin notebook was executed with an absolute project source path inherited by its kernel. No dependencies were changed.

## Boundaries

This preserves the supplied baseline's assumptions and limitations, including sold-out/no-resale nights, proxy booking blocks, diagnostic Resort failure and example-night cost curve restricted to q=0..15. This is a reproduction module, not the operational nightly batch or API. Historical reconstruction guards, sensitivity experiments, production persistence and the deploy-blocking gate belong to later work.
