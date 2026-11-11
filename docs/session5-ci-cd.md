# Session 5 CI CD alignment

Current CI and submission status: see [the updated audit](submission-checklist.md) and
[coursework/release separation](coursework-and-release.md). The stage results and
old command outcomes below are historical; `make quality-gate` remains strict,
while current `make ci` verifies expected reproduction before building.

Implemented 11 November 2026. This adds release engineering to the hotel project;
it does not replace the supplied learner, change evaluation data or alter gates.

The pipeline is `lint`, `test`, `data-check`, `kb-check`, `quality-gate`,
`briefing-quality`, `build`. Every step is also available locally. Recursive make
calls enforce sequential execution, including under `make -j`. Tests verify that
data/gate failures stop before building. CI runs the same Makefile and only a
successful main push can publish the image already built in that run.

Release version 0.2.0 lives in pyproject.toml. Container builds add both the release
tag and a 12-character Git commit tag, plus OCI source/version/revision labels.
The service release version is distinct from its model artifact hash.

Ruff 0.17.4 and Hypothesis 6.170.15 are pinned. Existing source and tests were
formatted, unused imports removed and one assigned lambda converted to a named
function to satisfy E4/E7/E9/F. Test fixture re-exports remain explicit. Numerical
model logic, frozen identities and historical reports were preserved.
The requirements snapshot's macOS-only appnope dependency now has a platform
marker so a fresh Ubuntu install can use the same requirements file.

The original dataset was downloaded successfully from Kaggle and matched the
existing SHA-256. Full local tests pass except opt-in PostgreSQL integration tests
when no disposable test database is configured. GitHub provisions that database.
Docker is unavailable on this Mac, so a real container build cannot be claimed
from local verification. The strict original quality gate is expected to fail
for Resort calibration and stop before the original briefing gate and build.
Separate remediation evidence does not automatically approve an original release.

GitHub repository visibility and branch protection are verified separately during
setup. The source repository was initially private; its API reported that GitHub
Pro or public visibility is required for enforced branch protection.
