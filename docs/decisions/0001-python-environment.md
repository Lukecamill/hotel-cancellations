# ADR 0001: Reproduce the notebook environment

Status: accepted for initial development, 2026-11-07.

Use Python 3.13.13, matching the supplied notebook metadata, in a project-local `.venv`. The project currently supports Python 3.13 only; additional versions require verification. System Python remains unchanged.

Match the six library versions printed in the supplied notebook: NumPy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, LightGBM 4.7.0, RDFLib 7.6.0 and pySHACL 0.40.1. These are recorded in `notebook-constraints.txt`. The notebook does not record every dependency; `requirements.txt` captures the installed environment, including transitive dependencies and notebook/development tools.

Use pip for project installation, as in Session 02. uv was used only to obtain the matching Python interpreter and create the seeded environment. Pin build tools in `pyproject.toml`; recreate using the requirements snapshot before an editable installation with dependency resolution and build isolation disabled.

On macOS Apple Silicon, the LightGBM wheel needs Homebrew libomp (installed version 23.1.5). This native dependency is separate from the Python requirements.

Validation covers package imports from outside the repository, dependency consistency, and a small LightGBM fit. It does not establish reproduction of the notebook metrics. Baseline reproduction and Linux/container portability remain later-stage checks.
