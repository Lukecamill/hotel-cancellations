# ADR 0015 — local, bounded and validated manager briefing

Status: accepted for coursework simulation; no production authorisation.
Date: 2026-11-10.

S1 requires a genuine local open-weight baseline, 30 exact-number nights, versioned
structured prompts, injection testing, cost evidence and human-approved guest drafts.
Use Ollama's configurable OpenAI-compatible endpoint with pinned Qwen3 4B Instruct
weights. Keep the existing predictive learner, selected policies and live demo fixed.

The LLM copies numerical context and retrieves one temporally grounded KB fact into
a strict JSON contract; it does not optimise overbooking or decide who is relocated.
Render validated fields into readable text. Arbitrary narrative is excluded because
its unsupported claims would evade exhaustive field-level validation. Guest wording
is a conservative fixed draft, never an automated communication. Digest-bound human
approval records are local evidence only; dispatch and live PMS integration are
outside this stage. Resort calibration failure and policy-wide sign-off remain open.

Reject rather than repair invalid output. Record all failures and replay exact raw
fixtures in CI without a live model. A separate strict quality gate fails if any
recorded briefing is invalid; replay agreement never turns a known failure into
a passing model. Use matched KB/without-KB nights, prespecified
calendar sampling and adversarial notes; do not select successful nights or conceal
schema failures. Log the full run to the existing local MLflow store without
registry changes. No model training or prompt tuning on golden responses is planned.

An unavailable provider stops live generation, retains replay, and exposes the
failure; it never silently moves data to a hosted endpoint. A marker can install
Ollama, pull the pinned tag, verify its digest and rerun locally without payment.

## 11 November 2026 delivery contract clarification

The paragraphs above record the original V1 numerical-copying contract and its
failed 27/30 result. V5 is a separately versioned design, described in
[the revised briefing explanation](../revised-briefing.md): code copies source facts,
and the model supplies only four interpretation fields. V5 delivered all 90 ordinary
cases exactly; one of six injected interpretations was withheld. Component safety
passes while raw-model all-case acceptance remains 95/96, FAIL. No raw numerical
copying improvement is claimed. Prompt/schema/context/model fingerprints and both
sets of failures remain preserved. Coursework replay verifies this distinction;
strict model release approval remains separate.
