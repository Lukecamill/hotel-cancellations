# Coursework verification and strict merge and release approval

The notebook requires reproducing the given learner unchanged. City passes its frozen quality gate and Resort fails calibration. Both hotels remain in scope, as Luke confirmed on 15 November 2026. [ADR 0018](decisions/0018-strict-both-hotel-merge-gate.md) restores strict model quality to the required merge check; no expected failure is accepted by `make ci`.

## Local commands

`make coursework-check` runs lint, tests, raw/split validation, SHACL and original reference/briefing reproduction. The coursework verifier compares numeric metrics, checks, frozen identity and reference failure reason. It also replays the original 66-case briefing and the V5 delivery contract without live inference. An exception or arbitrary nonzero result cannot count as correct reproduction. Its successful result explicitly says release_approved=false.

`make ci` runs coursework-check, then the strict per-hotel quality gate, then the service image build. Resort's current calibration failure makes this command fail before Docker runs. Output is kept in artifacts/ci/strict-gate; historical gate reports remain unchanged. The workflow uploads current artifacts/ci evidence even when the gate fails.

`make release-check` independently runs the strict quality gate followed by V5 delivery quality. `make publish` requires that target before any image push. The separate calibrated research challenger cannot replace the given-model evidence and is not promoted by this change.

## Required GitHub check

The GitHub pipeline job runs make ci. A separate registry-integration job exercises disposable PostgreSQL and MLflow integration. The aggregate job retains the check name ci and requires both jobs to succeed. Its always condition makes an upstream failure, cancellation or skip a failed required result rather than silently skipping the merge decision.

GitHub's main branch details on 15 November report protection enabled, required context ci, enforcement everyone. That existing context now covers both jobs without requiring a protection rename. This read does not establish every administrator-bypass or review setting. No protection is disabled.

Release runs only after the required checks succeed on a push to main. It verifies and loads the exact image archived by pipeline rather than rebuilding it, then invokes make publish. Only release has package-write permission. The current failing reference prevents reaching this path.

## Evidence and assessment boundary

Run 43025312530 at bc0d450 is a historical successful coursework reproduction and image build under the earlier policy. It is not a strict model-quality pass. Run 43022126664 is a historical failure at the strict model gate. Keep both descriptions honest in the diary.

The updated both-hotel gate is expected to fail until an eligible, permitted candidate is justified. Entry 2's passing strict CI example therefore remains outstanding. Do not tune against the exposed holdout, move its fingerprint, relax thresholds to conceal failure, or claim a lecturer-approved exception that has not been supplied.

Model/card peer review, policy approval, current live deployment readiness and VLE submission are separate requirements. This CI change does not grant hotel operating authority or automatically move model aliases.
