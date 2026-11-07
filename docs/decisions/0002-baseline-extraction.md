# ADR 0002: Extract the booking-time baseline without changing its method

Status: accepted, 2026-11-07.

Extract reference notebook cells 4, 10 and 11 into data, features, model and evaluation modules. Replace notebook-global dependencies with explicit arguments. Preserve loading transformations, stable row ordering, categorical handling, the top-60 agent selection expression, feature order, temporal masks, learner parameters, scoring and diagnostic thresholds. The reference notebook remains byte-identical.

The CLI runs the pooled model used by the baseline. Separate per-hotel models and deliberately leaking comparison models remain educational experiments in the reference notebook; they are not additional production models. Policy, knowledge-base and monitoring functions will be packaged during their respective stages.

The default pipeline rebuilds processed data from raw input because the reference notebook's Parquet cache does not identify its source file or date window. This changes cache use, not the loading transformation. Optional cache use retains the reference behaviour. The download fallback remains KaggleHub.

Learned top-agent state and ordered feature names are saved with the model to preserve preprocessing across reloads. Training exits successfully when it executes; the displayed per-hotel gate remains diagnostic at this stage. The baseline must retain its expected Resort calibration failure.

Local check: split counts exactly 49,157 / 29,546 / 40,687. Test AUPRC City 0.785722 and Resort 0.627908; expected/realised City 0.911281 and Resort 0.681723. Comparison tolerance against the notebook's rounded printed AUPRC is 0.0005 and against its two-decimal calibration ratios is 0.005. This is initial booking-model verification, not completion of C2 policy reproduction or the frozen CI gate.


Verification completed: 11 configuration/feature tests passed; the extracted feature frame exactly matched the reference function on all supplied rows; saved-model predictions exactly matched direct model predictions; the thin notebook executed all cells using the named project kernel. The executed notebook is a local ignored artifact under `artifacts/`. The reference notebook checksum still matches the supplied file.

Local environment note: Python 3.13 ignored the editable-install `.pth` file when it carried the macOS hidden flag. Clear that flag before interpreter startup if it recurs; the README records the command. A generic Python kernel also conflicted with the project environment, so the notebook uses the dedicated `hotel-cancellations` kernel.
