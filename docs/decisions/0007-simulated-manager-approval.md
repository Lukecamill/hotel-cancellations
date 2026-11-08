# ADR 0007 — simulated nightly manager approval

Date: 8 November 2026. Status: implemented and tested; no real operational authorisation.

## Decision

Add a small browser review screen and PostgreSQL-backed approval API to the existing service. Rebuild nightly recommendations from an explicit, version-matched database snapshot. Let a named simulated manager approve the candidate quantity, reduce it, or reject it with a mandatory reason and simulation acknowledgement. A database primary key permits only one final decision per review, including concurrent submissions. Preserve the recommendation, snapshot and model/policy provenance with the decision.

Separate the simulated approved quantity from real operational authorisation, which stays zero. Keep both example reviews pending for the student to decide. Do not infer policy-wide sign-off or promote unsigned Stage 5 policies. The current demonstration still uses the reproduced reference baseline, including the Resort's 8-week policy and its visible failed diagnostic gate.

## Alternatives and limits

A pasted ADR alone would not demonstrate a nightly in-system action. A mutable approval flag would lose reviewer, reason and historical context. Instead, store an immutable final record and reject a second decision. No decision-reversal endpoint is provided; future corrections should be append-only superseding decisions with explicit provenance.

Self-declared names are sufficient for a labelled local coursework demonstration, but not real access control or a digital signature. Keep localhost/SSH access, enforce an unpredictable submission token and same-origin browser requests, and render supplied text safely. Production use needs authenticated roles, an agreed policy approval process, trustworthy clocks, capacity controls and a real channel-manager boundary. Approval does not repair weak calibration or make a model safe.

## Evidence

See `docs/manager-approval.md`, the 112-test Linux/PostgreSQL results and `docs/evidence/manager-approval.json`. No real manager decision was fabricated or entered on the student's behalf.
