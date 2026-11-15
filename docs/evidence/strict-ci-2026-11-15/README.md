# Strict CI verification on 15 November 2026

The strict both-hotel merge check is implemented and remotely verified on [draft PR 2](https://github.com/Lukecamill/hotel-cancellations/pull/2), commit 79e9ddaa53a2455073ecb3b599e783fb9490bfa1. It remains unmerged; main still contains its earlier workflow.

The [PR run](https://github.com/Lukecamill/hotel-cancellations/actions/runs/43712971999) and [push run](https://github.com/Lukecamill/hotel-cancellations/actions/runs/43712963948) both passed registry integration and failed the strict pipeline at Resort calibration after software/data checks passed. The required ci aggregate failed and release was skipped. GitHub reports main protected with ci required, and the PR merge state blocked. No model, threshold or holdout changed.

The pipeline ran 283 passing tests with real PostgreSQL; its one skip is optional MLflow, exercised in the separate 16-test passing registry job. The pipeline-evidence Actions artifact contains current validation and gate results. Local full make ci ran 277 passing tests with seven environment-related skips and correctly exited before any image build. See verification.json and local-ci.log.

This verifies rejection, not a passing strict model. Luke explicitly retained both hotels and the block until an eligible model is justified. Entry 2's passing strict CI example remains outstanding. The local model-card and diary drafts are separate changes excluded from this CI-specific remote commit.
