# Reflective Diary Entry 2

Update 15 November 2026: feedback supplied by Luke and attributed to Jake Desira has been recorded and applied to the City version 2 model card. The journal, slides, speaker notes, script and PDF exports now include this feedback and the resulting revisions. The actual review date, exact reviewed version and reciprocal exchange remain unconfirmed. A passing strict both-hotel model-gate CI example remains outstanding.

Prepared for Luke Camilleri on 15 November 2026 from the supplied ARI3217 Entry 2 brief and the hotel's recorded project evidence. These are drafts for Luke's review, not an unconditional claim that every assessment requirement is complete.

## Files

- diary-entry-2-journal.pdf: 500-word reflection plus evidence tables, interval results and monitoring figures. The main reflection is page 1; tables, figures and references are excluded from the word count.
- diary-entry-2-slides.pdf: 8 content slides, plus an optional title slide and references slide, 10 pages total.
- diary-entry-2-slides.pptx: editable copy with native tables and time-series charts, with the matched narration in speaker notes.
- diary-entry-2-video-script.pdf: 609 spoken words, with slide-by-slide rehearsal timings targeting 4:45-4:55. It is not a recorded video. Actual pace must be rehearsed; marking stops at 5:00.
- diary2-written-entry.md and diary2-video-script.md: editable text copies.

Entry 2 covers Sessions 05-06, so these materials focus on honest evaluation, CI, tracking, registry and monitoring. The knowledge-base and GenAI investigations belong to later entries and are deliberately not crowded into this one.

## Before recording or submitting

1. Read and edit the reflection so that it accurately represents your own reasoning. Codex assisted implementation, analysis, plots and drafting; this is declared. Do not claim personal decisions or insights you cannot explain.
2. Confirm Jake Desira's actual review date, the exact card version he inspected and the reciprocal review exchange. The recorded feedback identifies the manager as least well served. The revised City version 2 card adds a results summary, responsibilities, monitoring rules and fallback instructions. The diary now reflects these changes. The AI-simulated revenue-manager review is a separate requirement.
3. Resolve the honest-gate CI requirement. Both linked workflow outcomes are real: run 43022126664 failed at the strict gate; run 43025312530 passed coursework reference-reproduction checks while retaining the Resort FAIL. The latter is not a passing strict model-gate CI example. Do not rename it or weaken the threshold to conceal that distinction. Ask the lecturer whether the preserved failed reference plus a separately passing eligible City gate suffices, or complete the permitted, justified training-window/gate decision and obtain the relevant run before making a stronger claim.
4. Review and commit the new diary source and evidence, preserve the MLflow store/artifacts separately, and update the revision reference if required. The registered City training runs were made from clean committed model code c9e3bfaf6b3d073dd9930ba60761ef932af1ab80. New random/forward analysis is separately logged with its exact script and working-tree state. No new code commit was made by Codex.
5. Rehearse in your own voice against the slides. Only read spoken paragraphs. Do not read full hashes/run IDs. Record at most five minutes and review the actual recording. Then submit the written PDF, slides PDF and your video file or link, as the brief requires. This package does not perform VLE submission.

## Registry and evidence

The new diary investigation is under docs/evidence/diary2 in the project. The actual City version URI is models:/task19-session6-city-booking/2, with a card attached. Its two versions have identical prescribed weights; the rollback demonstrates version selection/reloading, not a predictive improvement. The original Resort baseline remains unpromoted. Separate Resort calibration extensions logged by the training pipeline are excluded from this entry's given-model gate comparison.

The real local MLflow store is artifacts/diary2/mlflow.db, with its artifact tree in artifacts/diary2/mlartifacts. Neither belongs in Git. Back them up together. From the Desktop project root, inspect the recorded version on a separate localhost UI:

    .venv-tracking/bin/python -m mlflow server --host 127.0.0.1 --port 5002 --workers 1 --backend-store-uri "sqlite:///$(pwd)/artifacts/diary2/mlflow.db"

Open http://127.0.0.1:5002/#/models/task19-session6-city-booking/versions/2 . This UI is not currently started by this package and does not change the demo service. The original machine-specific local artifact URIs must stay reachable.

The metric called AUPRC uses sklearn average_precision_score. The random split is a quarantined diagnostic with a different time mixture and size; it cannot be promoted. Bootstrap samples resample 243 arrival dates per hotel, with replacement, preserving same-day dependence but not dependence between dates. Monthly replay uses final recorded labels, not observed alert timestamps. PSI thresholds and the two-month retraining-review trigger remain provisional policy choices rather than optimised guarantees.

CI links:

- https://github.com/Lukecamill/hotel-cancellations/actions/runs/43022126664
- https://github.com/Lukecamill/hotel-cancellations/actions/runs/43025312530

The PowerPoint charts include newly generated embedded workbooks from the complete chart data, rounded to six decimal places for presentation. These are chart-data snapshots, not original-source spreadsheets. Full precision remains in the investigation CSV files.
