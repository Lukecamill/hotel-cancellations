# Fresh-clone verification

Verified 7 November 2026. **PASS** for committed version `39fb510d427809fa0737d9ba58970f8223f96990`.

## Procedure

Cloned the committed local Git repository using `git clone --no-local` into `/private/tmp/hotel-cancellations-fresh-39fb510`. This checked out committed files only; the source working tree was clean at the start. No original environment, processed cache, saved model, `.env` or local source-package repair link was copied.

Created a separate `.venv` using uv with Python 3.13.13 and pip. Installed all requirements with `.venv/bin/python -m pip install -r requirements.txt`, then installed the package using `.venv/bin/python -m pip install --no-deps --no-build-isolation -e '.[dev]'`. Supplied the user’s original CSV separately at the documented raw-data path. No processed data existed before baseline execution.

Ran dependency consistency checks, tests, `make baseline`, saved-run comparison and all thin-notebook cells with the new environment’s kernel. Verified imports resolved to the fresh clone and configuration resolved to its data folder. No PYTHONPATH override, hidden-flag repair or source-package symlink was needed.

## Results

| Check | Result |
|---|---|
| Pinned dependencies and editable package | Installed successfully |
| pip check | No broken requirements |
| Automated tests | 16 passed |
| Complete baseline command | PASS |
| Comparison against original notebook evidence | All 20 checks passed |
| Split counts | 49,157 / 29,546 / 40,687 |
| Test AUPRC, City / Resort | 0.785722 / 0.627908 |
| Expected / realised, City / Resort | 0.911281 / 0.681723 |
| Diagnostic gates, City / Resort | PASS / FAIL, as expected |
| Policy choices and example-night outputs | Match reference |
| Raw and holdout hashes | Match recorded identities |
| Thin notebook | All cells executed |
| Local import repair | Not required |

Complete baseline runtime: 3.076 seconds; booking pipeline 2.040 seconds and policy pipeline 0.967 seconds. These are single-run measurements, not a performance benchmark. Run ID: `20261107T122104Z-c7b6c1f6`.

Evidence: [summary](evidence/fresh-clone/summary.json), [comparison](evidence/fresh-clone/comparison.json), [run provenance](evidence/fresh-clone/run.json), [notebook check](evidence/fresh-clone/notebook.json). Dependency/package installation logs and small result files are in the same evidence directory. The executed notebook remains in the temporary clone’s ignored artifacts folder.

The thin-notebook verification harness initially tried saving into a missing artifacts folder after executing all cells. Creating that output directory and rerunning completed the capture; no committed project code was changed. The kernel launcher emitted the same TCP-encryption warning seen in the earlier reference run.

## Limits

This verifies a genuine **local Git clone** of the stated commit, not a download from GitHub. It does not establish whether that commit has been pushed. It uses a new environment while reusing the Mac’s installed Python/OpenMP runtime and pip’s downloaded-wheel cache. Kaggle download/account access, another machine and Linux/container portability are not verified.

Full C2 still includes the upcoming raw-data contract, and this does not replace the later deployment CI gate. The original full teaching notebook was not rerun here; the newly cloned complete packaged baseline and thin notebook were run and compared to the recorded original execution.

This verification report and its evidence were created after the tested commit. Commit them separately to preserve the audit trail; the tested commit identifies the code, and the later evidence commit will identify this verification record.

## Later final verification

The original 7 November report above is historical. See [Stage 14 verification](stage14-final-verification.md) for the latest 215-test independent-clone run, extended audits and explicit quality failures.
