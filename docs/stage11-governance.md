# Stage 11 — Walking allocation: fairness and governance

Reviewed 9 November 2026. This is a reasoned coursework assessment of the stated
simulation and a possible future hotel deployment. It is not regulatory clearance,
a signed hotel policy, or a finding that real guests were discriminated against.

## What the experiment can establish

The existing reference policy produces an overflow proxy for each arrival night.
It does not identify the extra bookings sold through overbooking or provide actual
capacity, guest consent, accessible alternatives, contractual priority, party
membership or actual relocation records. The primary scenario assumes incremental
sales are honoured and assigns the overflow to surviving recorded booking rows.
The alternative protects those incumbents and puts every walk on unobserved extra
sales. Neither scenario is an observed operational event.

The simulator ranks only an immutable dataset-row identifier and inferred booking
date. Nationality, channel, segment, ADR and model scores cannot enter the ranking
interface. Audit labels are joined for aggregate measurement and their permutation
does not alter allocation. Nevertheless, booking date is correlated with customer
mix. Excluding a protected attribute is a useful boundary, not proof of fairness.

The hotel pays the configured relocation expense; guests may bear disruption,
accessibility, separation, transport or lost-time harms. EUR250 allocated per
simulated walked row measures hotel expense only. It does not price guest harm.
A row is not a person and may not even be a unique real booking; duplicates are
retained to preserve the supplied baseline.

## Nationality and access to services

Article 20 of the Services Directive addresses nationality/residence discrimination
in access to services. The Commission explains that provider differences in general
conditions need direct objective justification. Its application is through national
implementation and depends on provider/recipient scope and the particular access
conditions. We do not assume every source country code identifies legal nationality,
residence or eligibility under the Directive. [Commission Services Directive guidance](https://single-market-economy.ec.europa.eu/single-market/services/directive_en).

Our interpretation is that nationality-based relocation priority would need serious
legal scrutiny as potentially adverse access treatment. Nothing in cancellation
correlations, a cheaper expected walk or the source's domestic-booking artefact
establishes a valid justification. The project therefore excludes nationality,
residence and region from allocation, including indirect nationality classes from
the KB. This is the adopted project control, not a claim that every possible legal
exception is absent. Differences by channel or booking date also require evaluation;
neutral labels do not answer the justification question. General service terms,
consumer/contract duties and relevant Portuguese or Maltese implementation must be
reviewed for the actual operator before any live use.

No disparity ratio in this report is a legal threshold. The top-ten training-code
plus OTHER audit can miss within-OTHER effects; sparse cells and 20 lottery seeds
cannot establish absence of harm or causation. A real audit needs suitable cohort
coverage and context, not nationality in the ranking function.

## GDPR: lawful purpose, minimisation and individual effects

Removed names do not establish that a booking extract is truly anonymous. A live
PMS clearly raises a different privacy assessment from a local historical exercise.
For live use, identify the controller/processor roles, purposes, appropriate legal
basis, access controls and retention before processing. An Article 6 basis must fit
the specific processing and necessity; a commercial benefit does not automatically
make guest ranking necessary for a contract. [DPC legal-bases guidance](https://www.dataprotection.ie/sites/default/files/uploads/2020-04/Guidance%20on%20Legal%20Bases.pdf).

Apply purpose limitation, minimisation, accuracy, confidentiality and accountability.
Keep audit-only attributes separate from decision inputs and restrict row-level
traces. The project commits aggregate evidence, uses a prespecified denominator
threshold of 30 for reporting, and keeps row allocations under ignored artifacts/.
Those engineering measures do not prove anonymisation or GDPR compliance. A hotel
must set an approved retention period, information/rights process and restricted
audit access. [DPC Article 5 principles](https://www.dataprotection.ie/en/individuals/data-protection-basics/principles-data-protection).

Guest-specific refusal/relocation could affect contractual rights or have similarly
significant practical effects. Whether Article 22 applies depends on the actual
significance and whether the decision is solely automated. A lawful exception and
safeguards would need assessment where applicable; a booking cancellation forecast
is not by itself the same thing as an individual relocation decision. [DPC Article 22 guidance](https://www.dataprotection.ie/en/individuals/know-your-rights/your-rights-relation-automated-decision-making-including-profiling).

A person clicking approve routinely is not meaningful review. Our recommended
process requires a competent reviewer with authority to change the outcome before
the guest is affected, consideration of relevant circumstances, a recorded reason
and a contest/escalation route. This is a governance recommendation, not a claim
that the existing nightly quantity-review screen implements guest-level protection.
[WP29/EDPB-endorsed automated-decision guidance, p.21](https://www.aepd.es/sites/default/files/2019-12/wp251rev01-en.pdf).

Screen for a DPIA before a guest-impacting pilot; perform one when likely high risk
to rights/freedoms is established. Involve the DPO where appointed. Nationality
statistics should not be used to infer ethnicity; assess separately any special-
category data or sensitive inferences. The AI Act's high-risk classification and
GDPR's DPIA risk test are different questions. [DPC DPIA guidance](https://www.dataprotection.ie/en/organisations/know-your-obligations/data-protection-impact-assessments).

## AI Act: classification follows the intended use

Assess the predictive system and its integrated use, not just the deterministic
ranking function or the label “hotel AI”. Our working assessment finds no Article 6
high-risk route for ordinary commercial cancellation forecasting and this specified
simulation. Article 6 identifies the regulated-product/safety route and Annex III
listed uses; costly mistakes alone do not satisfy those routes. [Commission AI Act Explorer, Article 6](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6).

Annex III's essential-services heading is not a general classification for all
accommodation. A system acting for a public authority to decide essential housing
assistance eligibility would need reassessment; merely accommodating a publicly
funded guest is not the same intended use. Article 6's profiling rule concerns
Annex III systems, not every prediction about a person. [Annex III](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3).

No prohibited practice is demonstrated by this offline allocation experiment. Future
social scoring or exploitative uses require their own Article 5 test. A cancellation
score is not automatically prohibited social scoring; nor does commercial context
immunise a system that actually satisfies the prohibition. [Article 5](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-5).

The Commission Explorer identifies its text as the consolidation at 27 July 2026.
Its amended Article 4 requires measures supporting staff AI-literacy development,
without guaranteeing individual attainment. Reviewers must understand the horizon,
calibration, inventory uncertainty and override limits. [Current Article 4](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-4).

Assess direct-human-interaction transparency for the manager/guest interface and
later generated briefings; do not carry over a blanket “not a chatbot” exemption.
Our current output is offline analytical evidence, with no guest communication.
[Article 50](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50).

Use current application dates: the Council's 2026 timeline records most rules applying
from 2 August 2026, with high-risk timing deferred to 2 December 2027 for stand-alone
systems and 2 August 2028 for embedded-product systems. Delay of high-risk rules is
not a general exemption from other applicable duties. We do not make a research-
exemption finding merely because this is student work. [Council timeline](https://www.consilium.europa.eu/en/policies/artificial-intelligence-act/timeline-artificial-intelligence/).

## Decision and conditions before any guest-impacting use

Retain the offline experiment; do not deploy either ranking automatically. Reject
latest-booking-first as the project's default operational rule on the present
evidence. Use the lottery as a comparison, not a fairness certificate or released
fallback. Continue the existing manual/no-overbooking operational fallback and keep
Resort's champion withheld. Neither hotel has policy-wide live sign-off.

Before a pilot, the revenue manager must verify sellable capacity and room-night
feasibility; seek genuinely voluntary alternatives where appropriate; consider
contractual duties, accessibility and party cohesion without inventing missing
traits; arrange suitable alternatives and guest support; and permit meaningful
individual review and contest. The DPO/legal owner must assess the processing,
local consumer/service rules and any necessary DPIA. Do not collect extra sensitive
traits merely because they might be convenient for optimisation. Validate inferred
blocks separately in Stage 12. These are pending design conditions, not completed
compliance controls or permission to relocate a real guest.
