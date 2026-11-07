# Stage 6 — operational service and snapshots

Implemented and container-verified 7 November 2026. **Stage 6 technical checks pass.** HTTP serving, nightly batch, dataset-derived PostgreSQL snapshots and training/serving parity were verified on the Mac and in the Linux container. Production use and overbooking approval remain outside this sign-off.

## Course environment and measured results

Following the supplied Session 3 and Docker setup notes, verification ran with Docker Engine 29.1.3 and Compose 2.40.3 inside the existing **Ubuntu 26.04.1 LTS ARM64 VirtualBox VM**. Docker Desktop was not installed. The VM hosts Docker; the image uses Debian-based Python slim, as illustrated by the notes.

- Docker-reported application image size: **212,158,181 bytes** (212.16 MB, 202.33 MiB), model bundle mounted separately.
- Clean SIGTERM stop: **0.219 seconds**, exit code **0**.
- **93 tests passed**, zero skipped, inside the Linux image with real PostgreSQL enabled.
- Compose PostgreSQL: **18.1**. Snapshot round trip, idempotent insertion and file/database batch equality passed.
- Across 1,000 bookings, maximum Mac-training versus Linux-serving probability difference: **2.78e-17**, within the declared **1e-12 absolute tolerance**.
- Nightly hotel, policy and integer quantities match exactly. Cross-platform floating-point outputs use absolute and relative tolerance **1e-12**; observed differences were at roundoff scale.

The first container run found a missing PyArrow dependency needed to deserialize pandas metadata in the saved model. Adding pinned `pyarrow==26.0.1` fixed startup. The service now handles SIGTERM explicitly; the smoke check verifies clean, prompt shutdown. These are resolved findings from the portability test.

Evidence: `docs/evidence/stage6/container.json`, `linux-postgres.json`, `tests-linux.json` and consolidated `verification.json`. The earlier 92-test Mac result remains a historical record in `tests.json`.

The running VM project is `/home/luke/hotel-stage6`; PostgreSQL data persists in its `hotel-stage6_hotel-postgres` volume. Its generated password is in that VM folder's private `.env`, excluded from Git. A dataset-only PostgreSQL 18 dump is saved on the Mac at `artifacts/stage6/snapshot-postgres18.sql`.

The API is currently exposed to the Mac at `http://127.0.0.1:8080/health` through the authenticated SSH connection. Keep that Terminal connection open while using it. To reconnect later, first start the Ubuntu VM, then run on the Mac:

```sh
ssh -p 2222 -L 127.0.0.1:8080:127.0.0.1:8080 luke@127.0.0.1
```

In the Ubuntu shell:

```sh
cd ~/hotel-stage6
docker compose -p hotel-stage6 up -d --wait
```

Compose keeps published ports on the VM's loopback interface; the SSH tunnel makes the API reachable locally on the Mac. To stop the project without deleting its database volume, run `docker compose -p hotel-stage6 stop` in the VM project folder.

## Components

| Component | Entry point | Purpose |
|---|---|---|
| Runtime export | `python -m hotel_cancel.serving` | Export an explicitly chosen completed baseline run, with model/policy hashes |
| Booking API | `python -m hotel_cancel.service` | `POST /predict` and `GET /health` |
| Snapshot export | `python -m hotel_cancel.snapshot` | Reconstruct a dataset-based as-of snapshot; save JSON and optionally PostgreSQL |
| Nightly batch | `python -m hotel_cancel.batch` | Read an explicit immutable snapshot and produce review recommendations |
| PostgreSQL | `database/schema.sql` | Content-addressed snapshot table, preserving duplicate bookings |
| Container | `Dockerfile`, `compose.yaml` | Slim inference/batch image, external read-only model bundle and local PostgreSQL |

The existing booking learner, feature builder and baseline are unchanged. Model selection and tuning are not performed by any serving entry point. Runtime export uses the C2 reference policies, not the unsigned Stage 5 candidates. See [ADR 0006](decisions/0006-serving-and-snapshots.md).

## Host setup and booking API

Run from the repository root in the existing Python 3.13 environment. The full project requirements are needed for raw-data export; the inference image uses the smaller `requirements-serving.txt` instead.

```sh
.venv/bin/python -m pip install -r requirements-serving.txt
# Pick a completed baseline run explicitly. From a fresh clone run make baseline first.
.venv/bin/python -m hotel_cancel.serving \
  --run models/baseline/<run-id> --output models/serving
make serve
```

Export refuses to overwrite an existing runtime directory. Keep the previous artifact version, choose a new output directory, and pass `--bundle` explicitly if exporting another version. The locally prepared demonstration bundle is `models/serving` and its source run/hash are recorded in its manifest. It is excluded from Git.

In another terminal:

```sh
curl -s http://127.0.0.1:8080/health
curl -s -H 'Content-Type: application/json' \
  --data-binary @examples/predict.json http://127.0.0.1:8080/predict
```

The synthetic example contains the complete contract. The request must contain one `booking` object with exactly those fields. Arrival is a date; lead time and counts are integers; ADR is finite; agent/company accept string codes, integer IDs or null. Null children become zero and null agent/company become `none`, as in training. Negative and zero ADR retain the baseline treatment. Derive booked date from arrival minus lead time. Nationality, outcome and post-booking columns are rejected. Unknown categorical codes use the learner's established unknown-category handling; an unseen agent maps to `other`.

A successful response contains `cancellation_probability`, `horizon: booking_to_arrival`, a model fingerprint and `decision_authorised: false`. **This probability must not be passed directly to a seven-day overbooking decision.** Malformed bookings return 422, wrong content type 415, oversized bodies 413, unknown paths 404 and unexpected inference errors 500. Maximum body size is 64 KiB and each socket has a ten-second timeout. The service binds localhost by default; it is a demonstration service, with no public authentication/TLS or bounded request concurrency. `health: ready` means artifacts loaded, not that the per-hotel quality gate passed.

## Create and replay the dataset snapshot

The student authorised a project-owned snapshot because no supplied PostgreSQL dump/schema was available. The source remains the attributed Hotel Booking Demand CSV; this is not a live PMS connection.

```sh
.venv/bin/python -m hotel_cancel.snapshot \
  --bundle models/serving --decision-date 2017-08-08 \
  --output artifacts/stage6/snapshot.json
.venv/bin/python -m hotel_cancel.batch \
  --bundle models/serving --snapshot-file artifacts/stage6/snapshot.json \
  --output artifacts/stage6/batch.json
```

The baseline artifact supplies the seven-day horizon, making target arrival 15 August 2017. The snapshot contains 85 live booking records, inferred blocks and 84 mature daily history entries per hotel. Row-based synthetic IDs preserve exact duplicates. Arrival/booked cutoffs follow Stage 4. History excludes status outcomes dated on/after the decision day; target records contain booking inputs only, with no target outcome labels. The final-state CSV still cannot prove that every feature had its recorded value at the historical decision date.

The batch checks snapshot contents, artifact fingerprints and horizon, then applies the saved hotel calibrator and policy. Rolling re-levels use mature historical observed/predicted sums, ending the day before the decision. Re-running an identical snapshot and artifact pair produces identical output. Empty hotel populations produce a zero-quantity status instead of an inference error. Results are written through a temporary file and atomic replacement.

## PostgreSQL path

On a machine with Docker/Compose, set a local password and start the database:

```sh
# Set POSTGRES_PASSWORD and DATABASE_URL in your shell, using a private local value.
# Example DATABASE_URL form: postgresql://hotel:<password>@127.0.0.1:5432/hotel
# URL-encode reserved characters in the password.
docker compose up -d postgres
.venv/bin/python -m hotel_cancel.snapshot \
  --decision-date 2017-08-08 --output artifacts/stage6/snapshot.json --postgres
# The exporter prints the content-addressed snapshot ID.
.venv/bin/python -m hotel_cancel.batch \
  --snapshot-id <printed-snapshot-id> --output artifacts/stage6/postgres-batch.json
```

`DATABASE_URL` is read from the process environment; these commands do not automatically source a `.env` file. Compose does read its local `.env`. Never put actual credentials in a shared file. Database insertion creates the table transactionally, verifies identical contents on repeat insertion and does not overwrite snapshots. Batch retrieval uses an explicit ID and a read-only transaction. SQL parameters are bound rather than interpolated. Local JSON replay supports testing but does not replace PostgreSQL integration.

For a portable database dump:

```sh
docker compose exec -T postgres pg_dump -U hotel -d hotel \
  --table=hotel_snapshots --no-owner --no-privileges > artifacts/stage6/snapshot.sql
```

Restore into a prepared database using `psql` or the matching Compose database. Dataset-bearing JSON, SQL dumps, database volumes and generated models remain untracked. Schema, code, synthetic requests and aggregate verification evidence are committed.

## Container verification

```sh
make container
docker compose up -d api
python3 scripts/container_smoke.py
# On the prepared Ubuntu VM, also run:
python3 scripts/verify_stage6_containers.py --tests
```

The automated smoke script builds the image, tests health and booking prediction through a localhost port, runs the batch in that image, compares its output with the host using the documented float tolerance, verifies clean shutdown and records the actual image size in `docs/evidence/stage6/container.json`. It removes the test API container afterward. Run the host snapshot/batch example first. Image serving consumes the exported bundle through a read-only mount; training and raw snapshot creation run outside the minimal image.

The build context excludes datasets, artifacts, environments and secrets. Python dependencies are pinned; the base uses `python:3.13.13-slim-bookworm`, plus `libgomp1`. The application runs as UID 10001. Compose sets a read-only API root, temporary `/tmp`, dropped capabilities, localhost ports and `no-new-privileges`. The PostgreSQL service uses a separate persistent volume. The container smoke command passed on Ubuntu ARM64, as did the PostgreSQL 18.1 Compose checks. The earlier temporary Mac PostgreSQL instance was version 16.2.

## Verified evidence

The actual model was checked on 1,000 sampled source bookings across hotels and periods: maximum training/serving probability difference **0.0**. A real HTTP request matched direct scoring exactly. PostgreSQL insertion/readback, repeat insertion and file-versus-database batch equivalence passed. The saved example output is in [example-batch.json](evidence/stage6/example-batch.json), with hashes and checks in [verification.json](evidence/stage6/verification.json).

| Example target night | On books | Candidate oversell | Authorised oversell |
|---|---:|---:|---:|
| City, 15 August 2017 | 66 | 3 | 0 |
| Resort, 15 August 2017 | 15 | 0 | 0 |

The candidates reproduce the notebook's example quantities. City walking-anyone probability is approximately 19.2%; Resort still displays its diagnostic calibration FAIL. Neither output is authorisation to accept additional reservations. Human approval remains required; guest selection, live capacity validation and the Stage 5 policy sign-off are outstanding governance work.

The test suite now has 93 tests, all passing inside the Linux container with PostgreSQL enabled. To repeat:

```sh
# Set TEST_DATABASE_URL to a dedicated disposable PostgreSQL database.
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_stage6.py
```

The PostgreSQL test is explicitly skipped if `TEST_DATABASE_URL` is absent; do not report that run as database verification. The original host verification script uses the prepared local bundle and dataset. The container verifier uses the saved snapshot and a 1,000-booking reference fixture at `artifacts/stage6/parity.json`, generated from the training-side feature path; this dataset-bearing fixture stays outside Git. `requirements-test-container.txt` installs only test additions into a disposable temporary filesystem, leaving the inference image unchanged. Tests cover exact feature/prediction parity, request failures, unseen codes, tampered artifacts/snapshots, horizon/model mismatch, matured history and approval flags. Local network permissions are required for HTTP/database tests. Monitoring and load-performance measurements belong to Stage 7, and `make ci`/holdout gates remain Stage 8.

Database adapter implementation follows the [Psycopg connection/transaction documentation](https://www.psycopg.org/psycopg3/docs/api/connections.html); the pinned driver version is recorded in `requirements-serving.txt`.
