# Stage 8 test-count reconciliation

The initial Mac run collected 135 tests (129 passed, six database skips).
The initial Ubuntu run collected 131 (125 passed, six database skips).

The Stage 8 transfer included the new quality-gate test file but omitted the
previous Diary 1 checkout-date audit added in commit e57de9a:
`src/hotel_cancel/stay_audit.py` and `tests/test_stay_audit.py`.
The latter defines exactly four tests: expected checkout including weekends,
same-day checkout with positive nights, shorter checkout excluding cancellation
rows, and valid zero-night checkout. They are diagnostic data-audit tests;
they do not change training, features, labels, or the runtime service.

Evidence: the Ubuntu report lacks stay_audit.py from its source inventory;
every other Python source hash matches the current Mac source exactly.
The four additional Mac test identifiers account exactly for the count gap.
This was an incomplete transfer, not evidence of a platform-specific failure.

Correction prepared: transfer the two omitted files, compare all test-file
and Python source hashes plus all 135 collected test identifiers using
`scripts/verify_stage8_test_parity.py`, then rerun
`scripts/verify_stage8_ubuntu.py`. The expected final result is 129 passed,
six database skips and the unchanged Resort calibration FAIL.

Status: resolved. The supplied Ubuntu rerun confirms all 135 test identifiers,
all test files and all Python sources match the Mac inventory. Ubuntu now reports
129 passed and six database skips. City passes and Resort retains the expected
aggregate calibration failure; the demo runtime files are unchanged.

The user-supplied terminal transcript is retained as
`docs/evidence/stage8-ubuntu/parity-rerun-terminal.txt`; its parsed parity and
verification results are in `reconciliation-from-terminal.json`. The earlier
125-test report is preserved rather than relabelled. Updated native evidence
files can be copied back from Ubuntu separately. The test inventory manifest is
a reviewed snapshot; update it deliberately when future stages add tests.
