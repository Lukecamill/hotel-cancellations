# ADR 0004: Guard the given baseline without rewriting the historical data

Status: accepted, 7 November 2026.

Enforce a dependency-free, versioned raw CSV contract before transformation, with batch rejection on structural/type/date/domain errors. Retain and count the supplied duplicates, zero/negative/outlier ADRs, missing allowed fields and invalid guest/stay combinations. Dropping them would change the reproduced method and could erase group evidence.

Constrain feature code to the original booking-input allowlist and ordered output schema. Guard exhaustive, disjoint forward partitions and exact-row duplicate isolation. Keep outcome fields separate. Promote the original as-of predicate and nightly median ADR rule into named functions; retain their exact boundaries and values.

Tag fitted horizon calibrators and decision forecasts with their decision lead days. Reject mismatched/untagged forecast inputs and invalid probability/block shapes at the policy boundary. This prevents accidental booking-time scores being used as remaining-cancellation scores without an explicit decision-horizon declaration. It does not certify statistical calibration or prevent a caller deliberately lying about provenance.

Replace the notebook’s unvalidated cache reuse with a source/window/transform/version and Parquet-byte identity check; validate raw input even on cache requests. This supersedes ADR 0002’s optional unchecked cache behaviour. Existing cache files without metadata are rebuilt.

No dependency or learner change. All 64 tests and exact full-data extraction equivalence pass. See docs/stage4-validation.md for evidence, conventions and limitations. No event log exists to establish the original value of mutable booking fields; full historical truth cannot be recovered. Record the assumption instead of inventing event history.
