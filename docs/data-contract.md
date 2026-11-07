# Raw-data contract and failure handling

Version: `hotel-bookings-raw-v1`. Executable definition: `src/hotel_cancel/contracts.py`; generated schema summary: [raw-contract.json](evidence/stage4/raw-contract.json).

## Scope and hard failures

This contract is for the supplied historical training CSV, not the future booking-time API. Require exactly the 32 named fields (column order may differ), a non-empty frame, and no duplicated column names. Required fields cannot be missing or blank text. `children`, `country`, `agent` and `company` may be missing; existing loader behaviour is retained.

All numeric inputs must have numeric types and finite values. Integer fields, including lead time, counts and pseudonymous agent/company codes, must be non-negative integers where present. Binary label/repeated-guest fields must be 0 or 1. Week number must be 1–53; year/month/day must form a real arrival date in 1 July 2015–31 August 2017. Status dates must be valid YYYY-MM-DD dates.

Hotel codes must be City Hotel or Resort Hotel. Status must be Canceled, Check-Out or No-Show and agree with the cancellation label. Deposit type must be one of the three supplied codes. Other categorical codes must be non-empty strings; unknown segment/channel/room/country codes are retained rather than invented or silently corrected. No upper bound on booking counts or lead time is inferred from observed maxima; extreme but representable values still require review. The window is intentionally specific to this frozen dataset: a future operational contract must be versioned separately.

On failure, raise `DataContractError` before feature construction or training and stop the batch with a nonzero exit. Keep the source file unchanged for investigation. Do not silently repair or drop offending rows. No automatic quarantine copy is produced; batch rejection is the quarantine decision at this stage.

## Accepted and counted anomalies

| Condition | Count in supplied CSV | Decision |
|---|---:|---|
| Negative ADR | 1 | Retain for faithful baseline; report |
| Zero ADR | 1,959 | Retain; do not invent revenue |
| ADR above EUR1,000 | 1 | Review indicator, not a rejection threshold |
| No guests | 180 | Retain and flag |
| No nights | 715 | Retain and flag |
| Extra duplicate rows | 31,994 | Retain; may represent booking blocks |
| Missing children | 4 | Existing loader fills zero |
| Missing country | 488 | Existing loader maps to unknown; excluded from model |
| Non-alpha3 country code | 1,279 | Retain CN; KB reconciliation belongs to later work |
| Undefined segment / channel | 2 / 5 | Retain and flag |

These are acceptance exceptions for reproducing the given baseline, not endorsements of data quality. Warnings are logged and written in `make data-check` evidence. No model-input ADR clipping, deduplication or invented historical data was added. Policy room value remains max(night’s median ADR − variable cost, 0).

## Cache and reproducibility

Raw validation occurs even when requesting cache use. Reuse a Parquet only when its metadata matches the raw SHA-256, arrival window, pandas version, contract version and loader source hash, and the Parquet’s own SHA-256 matches. Missing/stale/malformed metadata or altered cache bytes trigger reconstruction from validated raw data. The complete baseline still rebuilds by default.

These metadata checks identify inputs and transformations; they do not establish historical feature availability. The contract version must change when its acceptance rules change. The tests exercise raw changes, cache tampering and malformed metadata.
