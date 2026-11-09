# ADR 0012 — Provenance, effective dates, explicit unknowns and KB ablation

Date: 9 November 2026. Status: implemented for offline coursework evaluation.

## Preserve the given reference

Package the supplied node, lookup and kb_features recipes without changing the
learner. Preserve the original 607-triple graph, notebook vocabulary and shapes
under knowledge/. Its five distinct vocabulary issues remain expected audit
evidence: CN is not an alpha-3 code; ATA/ATF have no supplied region; Undefined
segment/channel have no semantics. Do not hide them by changing the raw data.

## Extend from competency questions

Competency questions CQ1-CQ10 cover policy/segment/channel meanings, new codes,
country aliases, temporal membership, provenance, availability, predictive
ablation and fact-grounded briefing inputs. Use RDF entities and SPARQL queries;
bind external values as RDF terms rather than interpolating query strings.

The extension is a separate versioned graph. CN remains a source alias to CHN,
consistent with the notebook mapping, not a rewritten raw value. Missing
territory mappings point to an explicit unknown region. Undefined business
codes are explicitly unresolved and lack guessed boolean traits. Also define
unknown-code nodes. A coverage inventory targets required code/field entities.
A three-letter regex checks syntax, not completeness of ISO membership or
historical territorial status. Coarse regions inherit notebook assumptions.

Every mapped entity, semantic property and field includes provenance, a
qualification (notebook assumption/explicit unknown/synthetic launch), validity
interval and a knowledge-version timestamp. All source fields record their
assumed write phase, availability status and observedWriteTimestamp=false.
The source data does not supply event-level field-write timestamps; metadata
must not turn a booking-time assumption into a proven historical fact.

EU membership is country-specific and time-qualified, not permanently inferred
from a region. UK membership changes at 2020-01-31T23:00:00Z (11pm UK time),
with start-inclusive/end-exclusive intervals. The 2017 cohort remains historical
EU membership. Other ordinary mappings are scoped to the dataset window;
out-of-scope queries abstain. This source documents the withdrawal instant:
https://commonslibrary.parliament.uk/research-briefings/cbp-11529/ . Official
EU context: https://www.consilium.europa.eu/en/brexit/ . The knowledge snapshot
cutoff is 2026-11-10T00:00:00Z; no claim about later dates is made.

SHACL validates provenance, datatypes/cardinality, interval order, overlapping
membership assertions and required types. Explicit unknown business codes pass
only via an unresolved branch with no invented traits. CI runs this check
before the existing strict quality gate. A passing ontology is not proof of
source truth, booking-time availability, complete classification or model safety.
SHACL specification: https://www.w3.org/TR/shacl/ . Dataset definitions:
https://doi.org/10.1016/j.dib.2018.11.126 .

## Ablation and cold start

Use unchanged notebook training parameters, training-only agent vocabulary,
fixed arrival splits and the existing frozen holdout identity. Compare codes,
codes + policy/channel context, and KB classes replacing three business codes.
Reproduce raw-country (training top-40 vocabulary) and region experiments only
as artefact diagnostics. They do not alter production features or registries.
No model/threshold/policy is selected using these test comparisons.

The cold-start stress test renames the 4,126 held-out Non Refund codes and
actually rebuilds features through the extended graph. The hypothetical plan
is defined as prepaid/not refundable at launch, independent of outcomes. No
learner is refitted after renaming. This is an evaluation-time vocabulary shock,
not evidence of an observed natural launch cohort or exact booking-event truth.
Assert that class-only test inputs remain identical; measure rather than claim
code-model robustness. Existing-code policy semantics must match the original.
Use previously stated printed tolerances: AUPRC 0.0005 and ratio 0.005.

## Briefing factuality boundary

Evaluate 19 curated, independently specified semantic cases, unknowns, an
instruction-like code and effective-date boundaries. The renderer preserves
synthetic context numbers exactly. Without a KB it abstains from semantic claims;
report precision as undefined when there are no claims, and report coverage
separately. This avoids manufacturing a deliberately hallucinating comparator.
With temporal KB, check each boolean against the versioned golden answer.
These are typed grounding-contract results, not measured LLM performance or
the Stage 13 30-night/local-model/prompt-injection evaluation. No guest message
or operational oversell is sent, approved or changed by this experiment.
