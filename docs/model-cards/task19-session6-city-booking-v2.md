# City Hotel booking cancellation model version 2

Revised 15 November 2026 following supplied review feedback attributed to Jake Desira.

## Decision summary

This version passed the frozen historical City booking gates and is suitable for the stated coursework demonstration. It estimates whether a booking will cancel by arrival. It does not authorise room overselling, guest relocation or real hotel operation. Luke Camilleri owns coursework monitoring, investigation and alias decisions.

| Version fact | Recorded value |
| --- | --- |
| Registered version | `models:/task19-session6-city-booking/2` |
| Hotel and horizon | City Hotel; booking-to-arrival cancellation |
| Training run | `a849c16fdb4e432fb172b8ca2f3301dc` |
| Clean model source | `c9e3bfaf6b3d073dd9930ba60761ef932af1ab80` |
| Learner | Unchanged prescribed pooled LightGBM; no City post-calibrator |
| Holdout | 27,508 City bookings, January–August 2017; 11,691 cancellations |
| AUPRC | 0.785722; minimum 0.70; PASS. Prevalence baseline 0.425004. |
| Expected/observed cancellations | 0.911281; accepted band 0.85–1.15; PASS |
| Ten-bin ECE | 0.042275; maximum 0.10; PASS |
| Brier score | 0.172397; descriptive, not a separate gate |
| Raw adapter parity | Maximum error 0.0 on the recorded held-out adapter comparison |
| Alias history | Recorded champion selection 2 → 1 → 2; last confirmed in the diary evidence, not a live deployment claim |
| Registry location | Local `artifacts/diary2/mlflow.db` and matching `mlartifacts` tree |
| Prior rollback destination | City version 1, subject to eligibility and artifact checks |

The exact version metrics above come from its training run's eligibility.json. Separate arrival-date cluster bootstrap analysis gives City AUPRC interval 0.752263–0.813284 and ratio interval 0.892527–0.931058 (1,000 replicates, historical conditional 95% intervals; analysis run 574ffcbae4774ceda7d4e677216e5d20). These do not establish future operating performance or retain dependence across arrival dates.

Raw CSV SHA-256: `7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06`. Frozen feature/label SHA-256: `ac37475750f8f24abb767a78f7775b905a6ce0dce90d364402074181a9db017b`. Prediction artifact SHA-256: `b921b8c3f829e4364f84ea857e8018bf996e58165b44064288b94ff62f46eff5`.

The original Resort reference remains FAIL at ratio 0.681723 and is not covered by this City PASS. Coursework CI reproducing that failure is distinct from passing strict release quality. No threshold or model changed for this card revision.

## Intended use

Coursework booking-to-arrival cancellation probability estimation for the named hotel. City uses the unchanged prescribed pooled LightGBM learner. Resort uses the same learner with the prespecified logistic-on-logit booking calibrator. No real hotel operations, seven-day policy changes, guest relocation, inventory decision or guest messaging is authorised. The registry API has no policy execution or approval store.

## Data and evaluation

Hotel Booking Demand, CC BY 4.0, Antonio et al. (2019); see ../dataset.md and ../model-card.md. Fixed train arrivals July 2015–June 2016; Resort calibrator uses mature July–September 2016 outcomes; validation October–December 2016; holdout January–August 2017. Fit parameters and boundaries are fixed, not chosen by holdout ranking. Each fresh run logs the parameters, row counts, seed, source revision and fingerprints. The historical holdout has already been exposed and is a regression benchmark, not a pristine new generalisation test.

AUPRC thresholds: City 0.70, Resort 0.55. Expected/observed band 0.85–1.15 and ten-bin ECE ceiling 0.10. Eligibility requires the actual numeric holdout evidence, plus the prespecified Resort validation gate. Exact City version metrics are reproduced above from its eligibility.json; future candidates require their own evidence. Brier and adapter parity are logged too. The separate historical cluster intervals are reported above; naive independent-booking intervals would ignore duplicated/correlated bookings. No unsupported precision or superiority claim follows from passing these thresholds.

## Limitations

Final-state records do not prove booking-time availability; capacity, party membership, resale and actual room-night inventory remain unknown. Nationality is excluded. Data from 2015–2017 does not establish modern operating suitability. Calibration of the booking horizon must never be substituted for the saved seven-day horizon. Original reference failures and the calibrated extension remain separate evidence.

## Responsibility and human decisions

Luke Camilleri is the coursework model owner: he reviews intended use, investigates quality/data alerts, records decisions and controls coursework champion aliases. No real hotel operator, on-call team or operational approver is appointed by this coursework. In a real deployment those roles and notification routes must be assigned before use. A booking probability can inform a human review; it cannot set inventory or select a guest for relocation. The separate nightly workflow requires a revenue manager's explicit decision and verified business inputs. A registered booking model does not grant that authority.

## Monitoring

The following are review policies, not a claim that scheduled outcome ingestion and notification delivery are running:

| Signal | Threshold and maturity | Owner and response |
| --- | --- | --- |
| Booking calibration | Weekly expected/observed outside 0.85–1.15; at least 30 bookings and 20 observed cancellations. Complete arrival weeks only after arrival plus a conservative one-day settlement and confirmation of final labels; incomplete or lower-volume cohorts are inconclusive. | Luke checks label completeness, source changes and wcalibration; blocks new promotion while investigated. Booking-to-arrival labels can take the booking lead time to mature. |
| Input drift | PSI above 0.10 prompts investigation; at least 0.25 prompts action review, against the training reference. | Luke examines seasonality, missing values and changed codes; PSI alone does not establish prediction failure. |
| Retraining review | Two consecutive mature monthly booking-ratio breaches, with the same minimum-volume guards, or a season-boundary review. | Luke reviews past mature data and separate validation evidence before proposing permitted retraining. No automatic training or alias change. This monthly trigger supplements the weekly investigation rule. |
| Service availability | Unavailable for one minute or server errors. | Luke inspects readiness, registry/artifacts and database; uses manual handling. |
| Latency | p95 above 250 ms for five minutes. | Luke inspects CPU, loading and persistence overhead. This is a coursework budget. |
| Persistence | Any reported prediction-log failure. | Luke investigates the database and reconciles structured logs; audit completeness cannot be assumed. |

Alerts are visible in the coursework monitoring interface; no email, Slack or external on-call delivery is configured. Historical monthly figures use final recorded outcomes, not observed live alert times. The one-day rule is a replay assumption requiring validation against a real PMS label process. PSI levels and the two-month trigger are provisional, not optimised guarantees. For this booking card, monitor booking-to-arrival outcomes; the nightly policy has a separate seven-day population and calibration.

Monitor request errors/latency, database persistence failures and registry readiness separately. Prediction rows include registered name/version and model_lineage (run, source commit and artifact hashes). A failed log is reported as prediction_logged=false. A /health success proves process liveness; /ready and /predict return 503 until both eligible hotel models load. Aliases resolve once at startup; outage after loading does not alter the pinned models.

## Rollback

The coursework owner may move coursework aliases; real operating promotion requires an independently authorised owner and reviewed pipeline, neither granted by this project. For a previously passing compatible version:

    make registry-rollback HOTEL="City Hotel" V=1
    curl -f http://127.0.0.1:8082/ready

The command validates numeric evidence and clean lineage, records the alias change in MLflow, then restarts only registry-api. It never rebuilds the image or restarts the original demo. Verify the selected hotel model_version on /ready, a fresh /predict response and the corresponding hotel_predictions row's model_version/model_lineage. Repeat separately for Resort when needed. Restore the intended passing version with the same command. Do not choose the failed historical Resort version. Rollback versions must retain their artifacts, input contract and dependencies; back up Postgres and mlflow-artifacts together.

## Recovery when rollback cannot complete

Before moving an alias, inspect candidate versions and their eligibility evidence. Select a READY version for the same hotel with a finished run, clean known source, matching data/holdout identity, passing numeric gates, retained artifact hashes and compatible input contract/dependencies. A low version number or a PASS tag alone is insufficient. The recorded City version 1 is a candidate, subject to re-verification in the intended store.

If the rollback command fails, do not assume it left the alias unchanged: the move can succeed before the container restart fails. Read back the alias, inspect /ready, and compare its loaded version with a fresh prediction and persisted lineage. Startup pins models, so an alias move alone does not change the running process. Restore a verified destination and restart only registry-api when resources are available; record the failure and recovery.

If the registry is unreachable before loading, the service remains unready, returns 503 for readiness/predictions and retries loading. If both models were already loaded, it continues with those pinned versions; registry unavailability alone does not replace them. If either hotel lacks an eligible champion, the current two-hotel API remains wholly unready, even if City has a passing version. The recorded City-only registry demonstration must not be described as a ready deployment of that API.

If no eligible version can load, keep scoring unavailable and use manual handling with no additional overbooking. Do not bypass eligibility or activate the failing historical Resort reference. After data/artifact loss, restore the tracking database and matching artifact tree together from a verified backup, then verify readiness and prediction lineage before resuming. Local SQLite and Compose PostgreSQL stores require their own matching backups.

## Review

On 15 November 2026 Luke supplied feedback attributed to Jake Desira. It identified the manager as the least well served reader and requested version-specific results, ownership, self-contained monitoring and failure recovery. This revision addresses those points; see [review and change record](../reviews/session6-model-card-peer-review.md). The date of Jake's review and reciprocal card exchange remain unconfirmed. This card does not substitute for policy-wide manager sign-off.
