# Stage 14 final technical verification

Verified 10 November 2026 against committed source `3ca26fe969b7dd1e8397fe6a8af7dedda123681b`.
An independent local Git clone in `/private/tmp/hotel-stage14-clean` used a new
Python 3.13.13 virtual environment and editable installation from pinned requirements.
Only the installed Python/OpenMP runtime and downloaded dependency cache were reused.
Pip reported no broken requirements. The raw CSV was supplied separately.

The complete baseline started without an existing model or processed cache and
passed all 20 reference checks. The booking learner has identical bytes to the
original; a regenerated policy pickle differs because it includes local paths and
settings. That is documented, not represented as a failed decision comparison.
The separately fingerprinted original reference pair was then supplied for the
historical Stage 11/12 audits that pin that exact runtime.

## Results

- 215 tests passed; six PostgreSQL tests skipped without a dedicated test database.
- SHACL conforms; strict CI exits 2 for the recorded Resort calibration and briefing factuality failures.
- Offline replay: 66 records, 58 accepted, eight withheld; fixture regression PASS.
- Thin notebook: all five code cells executed with the clean environment's own kernel.
- KB learner-input ablation and 19-case semantic grounding contract rerun: VERIFIED.
- Walking audit and block audit rerun: VERIFIED, original nightly quantities preserved and full generated block RDF conforms.
- The recommendation was formatted and visually checked as a single-page PDF.

The initial restricted run could not open localhost test sockets; its failures
are retained in the logs. With the required local socket permission, all 215
tests passed. No application logic was changed to bypass the tests.

## What this establishes

This verifies the committed Stage 13 source from a genuine local clone, not a
published GitHub download. Stage 14 adds documentation, a read-only audit script
and the recommendation after that commit. The source archive labels this overlay
and records exact file hashes. Commit the final files to identify the final hand-in.

This does not rerun the live PostgreSQL deployment/load test, MLflow experiment
or local language-model inference; their earlier Mac/Ubuntu evidence is retained.
No serving file, registry alias, demo decision, diary slide or recording was
changed. No manager was impersonated and no VLE submission was made. The final
rubric/brief remains unavailable; the user's existing materials alone cannot
confirm final submission compliance. Both quality failures and manager sign-off
remain unresolved.

See `evidence/stage14/clean-clone-summary.json` and its logs,
`submission-checklist.md`, `reproduce-final.md`, and the manager recommendation.

## Later quality-remediation worktree check

The original clean-clone report above predates the remedies. The updated Mac
worktree passes 234 tests with six database skips and both current remedy gates.
Original baseline/V1 failures are still reproducible. See
`evidence/remediation/verification.json` for exact scope. New-source Ubuntu
verification remains pending; no new clean-clone result is invented here.
