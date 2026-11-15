# ADR 0016 Registry serving and clean registration

Accepted for coursework implementation on 15 November 2026; Ubuntu/container verification and model-card peer review remain pending.

Session 6 requires a passing candidate to enter the registry, rather than merely withholding its champion alias. ADR 0011 allowed failed research challengers and a local SQLite store. Preserve those historical entries but use a new task19-session6 namespace for deployable coursework candidates. Require finished runs, numeric frozen gates, clean known source and artifact-bound evidence before registration and alias changes. Track failures without registration.

Use a separate optional Compose MLflow service with Postgres and proxied persistent artifacts. Run a booking-only registry API beside the existing demo. Resolve each hotel's champion to an immutable version, verify its downloaded hashes, load both routes atomically, retry startup failures and distinguish liveness from readiness. Record exact model/run/hash/commit lineage with every prediction. Keep policy-state artifacts and seven-day operations separate.

Rollback validates a previously passing compatible version, creates an audit run, moves its alias and restarts only the new API. Tests use an isolated real registry and explicitly synthetic eligibility fixtures; they cannot establish that a real model was trained from clean source. Real candidate registration must wait for the completed changes to be committed and freshly trained. Another student must supply the model-card review. Production authentication/owner approval and remote branch protection are not established by this local implementation.
