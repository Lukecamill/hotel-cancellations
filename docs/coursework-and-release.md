# Coursework verification and release approval

The notebook requires reproducing the given learner unchanged. Its City gate passes
and its Resort gate fails calibration. Reproducing that result is correct coursework;
releasing the failing model would violate the quality gate. The two decisions now
have separate commands and GitHub jobs.

`make coursework-check` runs lint, tests, raw/split validation, SHACL and
`hotel_cancel.coursework`. The latter trains only the original training split,
verifies the raw/holdout lock, then compares both hotels' full metrics/checks with
the original recorded reference (absolute tolerance 1e-12, relative 1e-14). It
requires City PASS and the specific Resort calibration-ratio FAIL. An exception,
changed fingerprint/lock, different failure reason, missing hotel, changed metric
or unexpected overall pass fails coursework verification. It does not accept an
arbitrary nonzero exit code or use `continue-on-error`.

The command also verifies V1's original 66-case/58-accepted fixture regression and
V5's current 96-case delivery contract. Prompt, model, schema or context drift is
rejected by their replay routines. No live LLM or hosted quota is used.

`config/coursework-reference.json` records reproduction expectations, separate from
`config/evaluation-lock.json`. It must not be changed merely to obtain a green run.
The gate, its thresholds and original evidence are unchanged. Coursework output
explicitly states `release_approved: false` and `production_authorized: false`.

`make ci` adds the service image build to those checks. This verifies buildability
of service code; the trusted predictive model remains a separate mounted artifact.
A built image and a passing coursework check are not approval of that model.
The GitHub job is still named `ci`, so the required merge check retains its name.

The separate GitHub `release` job runs only after successful CI on a push to main.
CI saves the exact built image and its checksum as a short-lived workflow artifact.
The release job verifies and loads that image rather than rebuilding it. It invokes
`make publish`, whose prerequisite is `make release-check`: the original strict
quality gate and current V5 component quality. Only then can either Docker push
execute. Coursework expectations never override release approval. The current
original Resort model therefore still blocks publishing. This path is configured
but cannot be exercised as a successful release with the failing reference model.

Only the release job has package-write permission. There is no automatic champion
promotion, real manager signature, guest dispatch or PMS integration. C3 sign-off
remains a distinct outstanding assignment requirement. The separate calibrated
research challenger remains supplementary; it is not substituted into C2/E3 or
promoted by this change.

Verification writes ignored `artifacts/ci/` files rather than modifying historical
reports. See [the evidence audit](submission-checklist.md) and [V5 explanation](revised-briefing.md).

Workflow artifact transfer follows the official
[upload](https://github.com/actions/upload-artifact) and
[download](https://github.com/actions/download-artifact) actions documentation.
