# Simulated manager approval workflow

Implemented 8 November 2026. This feature records a manager's decision inside the application. It is a coursework simulation with self-declared reviewer names, not an authenticated production authorisation system.

## Use the screen

With the Ubuntu VM and project Compose services running and the SSH tunnel open, visit:

**http://127.0.0.1:8080/review**

The two example recommendations have been prepared and left pending. They refer to the historical 15 August 2017 arrival night. They use the given reference baseline policies: City fixed calibration-window rate and Resort blocks with 8-week re-level. They do not promote the unsigned Stage 5 sensitivity candidates.

For each hotel:

1. Read the proposed rooms, walking probability, expected cost, cost assumptions and any failed model-quality gate.
2. Select approve, reduce or reject. Approve retains the proposed quantity; reduce must be strictly smaller; reject records zero. A zero-room recommendation cannot be reduced.
3. Enter your name and explain your own decision. The application does not supply a reason or choose for you.
4. Acknowledge the coursework simulation, then select **Record final simulated decision** and confirm.
5. Verify the saved reviewer, UTC timestamp, quantity and reason. Refresh the page to read the same database record.

The form will be replaced with a final audit record after submission. There is no edit or delete action. A second or simultaneous decision for the same recommendation is rejected with HTTP 409. Choose carefully; correcting a final decision would require a separately designed supersession workflow, not changing the audit history.

No decisions have been submitted on the student's behalf. The original candidate quantity remains distinct from the simulated approved quantity. All real operational authorisation stays at zero; there is no channel-manager integration or guest messaging.

## What is recorded

PostgreSQL tables `hotel_policy_reviews` and `hotel_policy_decisions` hold immutable application-level recommendation/decision records. The review contains the hotel, arrival and decision dates, snapshot fingerprint, model and policy hashes, proposed quantity, forecast risk/cost and economic assumptions. The final decision adds reviewer name, reason, action, simulated approved quantity, simulation acknowledgement and a server-generated UTC timestamp.

A review ID is the SHA-256 of its canonical payload. Preparing the same snapshot again does not reset or duplicate its decision. New recommendations must be rebuilt from a database snapshot matching the active model/policy pair. The server never accepts caller-supplied cost/risk estimates as the recommendation.

Timestamps use the Ubuntu server clock in UTC, not a user-entered date. Chrony was stepped during verification after detecting a stale VM clock. Check clock synchronisation after suspending/resuming the VM and before a real deployment; reviewer identity and timestamps are not a cryptographic signature.

## API and deployment

- `GET /review` (also `/`): review screen.
- `GET /reviews`: reviews, current decision states and a per-process submission token.
- `POST /reviews` with `snapshot_id`: prepare one review per hotel from the database snapshot and current runtime bundle.
- `POST /reviews/{review_id}/decision`: submit decision, quantity, reviewer, reason and `simulation_acknowledged: true`.

POST operations require the `X-Review-Token` from the review response. Browser cross-origin submissions are rejected, framing is disabled, review responses are not cached, and user text is displayed through text content rather than HTML. These controls prevent accidental/cross-site form submission; they do not provide authentication. Keep the service on localhost behind the SSH tunnel. Do not expose it publicly.

Compose supplies `DATABASE_URL` privately to the API and waits for PostgreSQL health before startup. Passwords remain in the VM's untracked `.env`; approval records remain in its existing persistent PostgreSQL volume. The packaged application includes its HTML asset, and the PostgreSQL driver is included in both project installation pins and inference pins.

## Policy sign-off remains separate

This feature implements **nightly recommendation approval**. ADR 0005 still documents policy-wide assumptions, limits and the proposed Stage 5 candidates. Recording a nightly simulated decision does not sign that ADR, establish real hotel capacity, validate business costs, or prove that a lecturer accepts simulated approval. Document the scope honestly in the submission.

## Verification

The Ubuntu Linux container suite now has **112 passing tests**, no failures and no skips. Tests include approval/reduction/rejection constraints, immutable records, persistence across store instances, concurrent reviewer conflict, submission-token/origin checks, invalid quantities and snapshot publishing with model/version preservation. Browser checks verified that City reduction caps the quantity below three and that neither displayed hotel has an approval recorded. Existing model, batch, PostgreSQL and container smoke checks still pass.

Evidence: `docs/evidence/manager-approval.json` and the updated Stage 6 JSON reports. The UI preview is stored locally under `artifacts/manager-review/` and remains excluded from Git, along with dataset-bearing fixtures and model artifacts.
