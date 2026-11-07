# Setup verification

Verified on 7 November 2026 using macOS Apple Silicon, Python 3.13.13 and Homebrew libomp 23.1.5.

## Method

Copied only project source, configuration, documentation, tests, dependency files and notebooks into a new temporary directory. Excluded the existing virtual environment, model artifacts, processed data, Python caches and local secrets. Supplied the original CSV separately in the documented raw-data path, then created a new environment using `python3.13 -m venv .venv`.

Installed `requirements.txt`, then installed the package with `--no-deps --no-build-isolation -e ".[dev]"`, as documented. Ran dependency consistency checks, tests, the installed `hotel-train` entry point, an import/configuration check from outside the source folder, and all thin-notebook cells using a kernel belonging to the new environment.

## Results

| Check | Result |
| --- | --- |
| Pinned dependency installation | PASS |
| Editable package installation | PASS |
| `pip check` | No broken requirements |
| Automated tests | 11 passed |
| Imports outside project folder | PASS; configuration resolved to the clean copy |
| Training entry point | PASS |
| Training / validation / test rows | 49,157 / 29,546 / 40,687 |
| Test AUPRC, City / Resort | 0.785722 / 0.627908 |
| Expected / realised, City / Resort | 0.911281 / 0.681723 |
| Diagnostic gate, City / Resort | PASS / FAIL, as expected |
| Metrics against original local environment | Exact match |
| Thin notebook, all cells | PASS |

Clean-copy training runtime: 1.41 seconds for loading, feature construction, pooled fitting and scoring; this excludes environment installation and notebook presentation.

Holdout SHA-256: `ac37475750f8f24abb767a78f7775b905a6ce0dce90d364402074181a9db017b`.

The preserved reference notebook is byte-identical to the supplied original. Git ignore checks cover raw data, models, virtual environments, local secrets and executed notebook artifacts.

## Limits

This verifies a clean **source copy** of the current local work, not a GitHub clone: the implementation is not committed or pushed yet. After publication, repeat setup from an actual clone to confirm all required files were included. The test uses an existing local CSV; it does not exercise Kaggle download or account access. It reuses the Mac's installed Python and OpenMP runtime; Linux/container portability remains pending. Policy reproduction, six-trap coverage and deployment CI gates are later stages.

The fresh environment needed no hidden-file repair. The original local environment's macOS hidden `.pth` issue remains documented in the README as troubleshooting.
