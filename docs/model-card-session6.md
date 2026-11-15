# Session 6 booking prediction candidate card

This card accompanies each future Task 19 Session 6 registered version. The version's run contains eligibility.json with its exact hotel, clean source commit, dataset and holdout fingerprints, artifact identities, validation metrics and holdout metrics. Registration attaches this card to that version's description. Historical cards and registry entries remain historical evidence.

## Intended use

Coursework booking-to-arrival cancellation probability estimation for the named hotel. City uses the unchanged prescribed pooled LightGBM learner. Resort uses the same learner with the prespecified logistic-on-logit booking calibrator. No real hotel operations, seven-day policy changes, guest relocation, inventory decision or guest messaging is authorised. The registry API has no policy execution or approval store.

## Data and evaluation

Hotel Booking Demand, CC BY 4.0, Antonio et al. (2019); see dataset.md and the original model-card.md. Fixed train arrivals July 2015–June 2016; Resort calibrator uses mature July–September 2016 outcomes; validation October–December 2016; holdout January–August 2017. Fit parameters and boundaries are fixed, not chosen by holdout ranking. Each fresh run logs the parameters, row counts, seed, source revision and fingerprints. The historical holdout has already been exposed and is a regression benchmark, not a pristine new generalisation test.

AUPRC thresholds: City 0.70, Resort 0.55. Expected/observed band 0.85–1.15 and ten-bin ECE ceiling 0.10. Eligibility requires the actual numeric holdout evidence, plus the prespecified Resort validation gate. Exact version metrics live in eligibility.json, rather than being copied from an older version. Brier and adapter parity are logged too. Point estimates have no independent confidence intervals: duplicated/correlated bookings and temporal dependence make naive independent-row intervals misleading. No unsupported precision or superiority claim follows from passing these thresholds.

## Limitations

Final-state records do not prove booking-time availability; capacity, party membership, resale and actual room-night inventory remain unknown. Nationality is excluded. Data from 2015–2017 does not establish modern operating suitability. Calibration of the booking horizon must never be substituted for the saved seven-day horizon. Original reference failures and the calibrated extension remain separate evidence.

## Monitoring

Retain the original card's per-hotel mature-outcome calibration and drift triggers and label-maturity rules. Monitor request errors/latency, database persistence failures and registry readiness separately. Prediction rows include registered name/version and model_lineage (run, source commit and artifact hashes). A failed log is reported as prediction_logged=false. A /health success proves process liveness; /ready and /predict return 503 until both eligible hotel models load. Aliases resolve once at startup; outage after loading does not alter the pinned models.

## Rollback

The coursework owner may move coursework aliases; real operating promotion requires an independently authorised owner and reviewed pipeline, neither granted by this project. For a previously passing compatible version:

    make registry-rollback HOTEL="City Hotel" V=1
    curl -f http://127.0.0.1:8082/ready

The command validates numeric evidence and clean lineage, records the alias change in MLflow, then restarts only registry-api. It never rebuilds the image or restarts the original demo. Verify the selected hotel model_version on /ready, a fresh /predict response and the corresponding hotel_predictions row's model_version/model_lineage. Repeat separately for Resort when needed. Restore the intended passing version with the same command. Do not choose the failed historical Resort version. Rollback versions must retain their artifacts, input contract and dependencies; back up Postgres and mlflow-artifacts together.

## Review

Peer review by another student is pending. Record the real reviewer and findings in docs/reviews/session6-model-card-peer-review.md. This card does not substitute for policy-wide manager sign-off.
