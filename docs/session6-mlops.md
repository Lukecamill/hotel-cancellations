# Session 6 tracking and registry workflow

> Current status, 18 November 2026: see [current-submission-status.md](current-submission-status.md). Older results below retain their historical revision. Strict `make ci` gates both hotels before building; Resort blocks it. Actual City registration/rollback and simulated q=0 policy review are recorded. Only reciprocal peer review remains unconfirmed; review date/version are not required.


Implemented 15 November 2026 from the supplied Session 6 notes. This is a separate coursework booking-prediction workflow. It preserves the original serving bundle, saved policies, historical failed runs and diary assets. Its registered names start task19-session6- to avoid rewriting the earlier research registry.

## What changed

The opt-in Compose overlay adds an MLflow server with Postgres records and a persistent artifact volume. MLflow serves artifact uploads/downloads through HTTP, avoiding the old machine-specific file URIs. Address settings live in config/registry.yaml, overridden by MLFLOW_TRACKING_URI in .env or the shell. Host access uses http://127.0.0.1:5001; containers use http://mlflow:5000. The monitoring services now have the monitoring profile; explicitly starting them still works.

The new training entry point fits the fixed notebook learner and the prespecified Resort booking calibrator, records parameters, raw/holdout fingerprints, clean/dirty source identity, validation/holdout metrics, input schema and model artifacts. It checks raw-input adapter parity on every held-out booking. Fitting exceptions remain failed runs. The historical hotel-train entry point now uses this tracked path by default; hotel-train --offline and python -m hotel_cancel.baseline remain explicit historical reproduction paths with no deployable registration. The original baseline algorithm, thresholds and frozen holdout remain unchanged. No tuning or window search is introduced.

Registration separately requires a finished run, known clean commit matching the registration checkout, frozen identity, actual numeric quality metrics and Resort validation. Failed or dirty runs stay tracked without registration. Each passing registration receives a challenger alias and a version-linked model card; champion selection is a separate explicit action. The old Stage 9 tracker now refuses fresh registrations from failed/dirty historical provenance, and its old direct calibration-registration script delegates to the gated training workflow. Historical failed registered versions are preserved as evidence and are never accepted by the new service.

The new registry-api loads both hotel champions atomically in the background. It checks gate evidence and the actual downloaded artifact hashes before becoming ready. /health reports liveness; /ready and /predict return 503 until loading succeeds. Registry outages trigger retries. After loading, exact versions stay pinned until restart. The raw booking contract runs before MLflow signature validation; nullable children and business identifiers retain the original service semantics. Every prediction reports and logs registered name/version, run, artifact hashes and code commit. PostgreSQL gains an additive model_lineage JSONB column; no prior prediction row is rewritten. APP_VERSION identifies the new code image, separately from the model version.

The new API does not execute seven-day policies or expose an approval database. Its port is 8082; the existing demo remains on 8080. Registry-based booking calibration does not approve a nightly oversell policy.

## Start the service on Ubuntu

Use a local .env with POSTGRES_PASSWORD already configured; never commit it. The shell and .env must point MLFLOW_TRACKING_URI to the appropriate machine. Passwords containing URI punctuation require a URL-safe database connection configuration rather than literal interpolation.

    make registry-up

registry-db-init creates mlflow idempotently even when the Postgres volume already exists. New volumes also initialise it from mlflow/init.sql. This command starts only the database and the two new services; it does not rebuild or restart the old demo API. The registry API initially returns 503 readiness because no eligible champions exist. Forward Mac port 5001 to VM port 5001 and 8082 to 8082 if accessing these new services through VirtualBox.

The tracking environment needs requirements-tracking.txt plus the project's dev dependencies for a full test run. The separate Docker inference image uses requirements-registry.txt, without notebooks, raw data or model weights in its image.

## Train and register after committing

Commit the completed source changes first. Do not bypass the clean-source check or change the old training provenance. A transferred archive without Git metadata cannot claim a clean training checkout: use an actual checkout of the committed revision for candidate registration.

    make registry-train

This prints one run ID per hotel. Register each explicitly:

    make registry-register RUN_ID=<city-run-id>
    make registry-register RUN_ID=<resort-run-id>
    make registry-alias HOTEL="City Hotel" V=<city-version>
    make registry-alias HOTEL="Resort Hotel" V=<resort-version>
    docker compose -f compose.yaml -f compose.registry.yaml restart registry-api
    curl -f http://127.0.0.1:8082/ready
    make registry-release-check

A later tracked training run can create another compatible version with identical prescribed parameters. Do not claim that repeating the same model creates a performance improvement. No champion is silently replaced. registry-release-check verifies the selected candidates and the delivered briefing component; it grants no operating authority and does not replace the original strict publish gate or the pending policy review.

## Rollback and version lineage

The coursework owner may move coursework aliases. A real deployment requires a model owner, reviewed clean pipeline and controlled registry access; this localhost teaching server has no production authentication.

    make registry-rollback HOTEL="City Hotel" V=<previous-passing-version>
    curl -f http://127.0.0.1:8082/ready
    curl -sS http://127.0.0.1:8082/predict -H 'Content-Type: application/json' --data-binary @examples/predict.json

The target validates the destination, creates an MLflow audit run, moves the alias and restarts only registry-api. Verify the same name/version and run in the response and database:

    docker compose exec postgres psql -U hotel -d hotel -c "SELECT model_version, model_lineage FROM hotel_predictions ORDER BY created_at DESC LIMIT 3"

Restore the intended version with the same rollback target. Two passing compatible versions must exist first. The failing historical Resort version is not a rollback option. Back up the mlflow database, hotel prediction database and mlflow-artifacts volume together; retain compatible code/dependencies and verify a restore before relying on a backup. The older SQLite stores still need their own database-and-artifact backups and are not automatically migrated.

## Verification and remaining human steps

The Mac tests use a disposable real SQLite-backed MLflow registry and real HTTP service. Synthetic fixtures exercise alias rollback and adapter loading; their metrics and clean-source metadata are test data, not eligibility claims about Task 19 models. A separate fresh training run uses the actual hotel data and reports passing numeric gates, but uncommitted code is deliberately not registered. See docs/evidence/session6-mac/verification.json for the observed result and scope.

The current CI adds a registry-integration job with a disposable PostgreSQL service and requires it before the existing main-only release job. Configure the repository's remote required status checks for both ci and registry-integration; local workflow files cannot prove branch protection is enabled. This change has not yet been pushed or verified remotely.

On Ubuntu, run python3 scripts/verify_session6_ubuntu.py. It builds disposable images and creates an isolated network, PostgreSQL volume and MLflow artifact volume. It runs the full connected-database suite, tests server-proxied artifacts, checks the real new container's liveness/readiness and executes a physical container restart rollback. It verifies persisted prediction lineage and removes only its own temporary containers/volumes. It requires the existing hotel-cancel:stage9-check test image and network access for image builds. Its synthetic test registry is never the project's actual registry. Only claim success after SESSION6_UBUNTU_VERIFIED.

Another student must review the model card; record the real review in docs/reviews/session6-model-card-peer-review.md. Policy-wide manager sign-off remains a separate pending item. No review identity, approval, new Git commit or real hotel authorisation is fabricated by these changes.

## References

Supplied Session 6 notes, Sections 3–5 and 8, and summary slides 6–13 and 16. The teaching stage numbers differ from this project's custom stage plan. Implementation follows the official MLflow tracking-server and model-registry APIs:

- https://mlflow.org/docs/latest/tracking/server/
- https://mlflow.org/docs/latest/registry/

## Ubuntu confirmation from supplied terminal output

The supplied terminal transcript confirms SESSION6_UBUNTU_VERIFIED: 275 tests passed, zero skipped, with disposable PostgreSQL and MLflow HTTP artifact transport. The container readiness, restart rollback and persisted prediction lineage checks passed; protected original demo artifacts were unchanged. These registry models were synthetic test fixtures. Actual Task 19 candidate registration still requires clean committed source and fresh tracked training; model-card peer review and new remote CI/required-check verification remain pending. Native Ubuntu evidence files still need copying back. The transcript and parsed result are preserved under docs/evidence/session6-ubuntu; the original transfer manifest remains a historical snapshot.
