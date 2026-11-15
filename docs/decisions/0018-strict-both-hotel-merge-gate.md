# ADR 0018 Strict quality required before merging both hotel models

Date: 15 November 2026. Status: implemented locally; remote verification recorded separately.

## Decision

Luke selected: both hotels remain in scope, and CI stays blocked until an eligible model is justified. Do not remove Resort from deployment scope, relax the frozen thresholds, select a new training window using holdout results, or substitute the supplementary calibrator for the prescribed reference learner.

`make coursework-check` remains the explicitly named reference-reproduction check. `make ci` runs it, then invokes the strict per-hotel quality gate directly, and builds an image only if that gate succeeds. An expected Resort failure cannot produce a successful CI exit. The strict output goes to ignored artifacts/ci/strict-gate rather than overwriting historical evidence.

The GitHub job previously called ci is now pipeline. A new aggregate job retains the required check name ci, runs even when upstream jobs fail, and requires both pipeline and registry-integration to succeed. This preserves the existing main branch's required ci context and prevents a passing model/code pipeline from masking failed registry integration. Cancelled, skipped or failed upstream jobs cannot make the aggregate pass. Release still requires successful ci and registry-integration and the strict publication check.

The branch details returned by GitHub on 15 November show main protected with required context ci and enforcement level everyone. No branch protection rule is weakened or removed by this change. A failed required check is the demonstrated merge restriction; administrator bypass and other protection settings are outside the read access available here.

## Consequences

The unchanged given model still passes City and fails Resort calibration at expected/observed 0.681723 against 0.85–1.15. Therefore this change is expected to make pipeline and ci fail on GitHub while retaining a separately successful registry integration result if its tests pass. That is a functioning gate, not an unsuccessful attempt to conceal model quality.

No passing strict both-hotel CI example is claimed. Entry 2's passing example remains outstanding until a permitted candidate/window decision is independently justified before evaluation, or the lecturer explicitly approves another assessment interpretation. Training and thresholds are not changed by this CI repair. A green coursework-check remains reproducibility evidence only.

The model-card revisions and untracked diary drafts are separate working-tree changes and are not automatically included in this CI-focused commit. Its parent is the current committed project revision c9e3bfaf6b3d073dd9930ba60761ef932af1ab80, which contains the Session 6 implementation.

## Validation

The ordering test injects a model-quality failure and proves that the image build does not execute, even with parallel make enabled. Workflow checks verify that the required aggregate depends on both jobs and rejects any outcome other than success. The unchanged strict gate is run locally and remotely; see docs/evidence/strict-ci-2026-11-15 for the observed revision and results.
