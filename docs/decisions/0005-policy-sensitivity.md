# ADR 0005 — validation-only policy sensitivity and manager review

Date: 7 November 2026. Status: accepted with changes following a declared AI-simulated revenue-manager review on 15 November 2026; no real operating authorisation.

## Decision

Keep the original C2 reference baseline reproducible. Extract shared horizon/block preparation into `prepare_policy`, preserving the original defaults. Run C3 experiments through a separate validation-only entry point and prespecified grid. Mature calibration labels before the first selection decision. Include a no-overbooking fallback; compare perfect block correlation with independent booking cancellation. Model resale as explicit residual-margin recovery rather than an inferred fact.

For the reference assumptions (7 days, €250 walking, €20 variable cost, zero resale), nominate the fixed calibration-window rate for City and blocks with 12-week re-level for Resort for further review. These differ from the original baseline's Resort 8-week choice because the Stage 5 calibration fit is restricted to outcomes mature at decision time. Do not replace the reference baseline or deploy these candidates.

## Evidence and trade-offs

The [Stage 5 report](../stage5-policy-evaluation.md) and its complete CSV grid record validation costs. City reference savings are €92.01 per night, with 0.25 walked rooms per night; Resort savings are €3.29 with no observed walking in these 92 nights. Zero observed walking does not establish zero risk. Both hotels' initial horizon-model calibration remains weak. Resale reduces the marginal value of overbooking and changes winners. Exhaustively selecting across these scenarios would exaggerate evidence: business settings must be supplied externally, not chosen from validation profits.

The resale approximation is transparent and inexpensive but cannot represent replacement demand, prices, capacity, multi-night availability or dependence of resale on cancellation time. The original no-resale case is retained as a comparison. The 4/8/12-week windows expose adaptation versus limited recent data without changing the booking learner or using the frozen test for tuning.

## Simulated review and selected operating point

Decision: **accepted with changes**. Signed off by: **Revenue manager (simulated with OpenAI Codex), 15 November 2026**. The professor's user-supplied guidance permits this declared coursework simulation. The assistant generated both roles from inspected evidence; this is not an independent human review or a quotation of Luke's answers.

The [review brief](0005-review-brief-2026-11-15.md) and [questions, answers and reasoned decision](0005-simulated-revenue-manager-review-2026-11-15.md) record the handoff. Retain the City fixed mature-window rate and Resort **12-week** re-level candidates for historical research, but select **q=0 additional overbooked rooms for both hotels** as the current operating fallback. Preserve h=7, walking EUR250, variable EUR20 and zero resale as declared comparison assumptions. Do not promote a candidate, change the existing demo or infer that booking-horizon calibration validates the seven-day policy.

Luke is the coursework project owner to whom the recorded decision is handed back. Reconsidering positive quantities requires the evidence below and a new versioned decision. The [digest-bound review packet](../reviews/coursework-policy-review-v2.json) and [simulation sign-off](../reviews/coursework-policy-signoff-v2.json) bind this outcome to the brief, transcript and existing Stage 5 evidence. The separate earlier 8-week reference-policy packet remains historical and unsigned.

## Preconditions for reconsidering positive additional quantities

The simulated reviewer has decided; the following are future operating prerequisites, not missing fields in the coursework simulation:


- Confirm walking and variable costs, supported by operating records.
- Confirm lead time and evidence for a resale rate or retain zero resale conservatively.
- Confirm true sellable capacity and room-night availability; validate inferred blocks with the PMS.
- Set maximum acceptable walking probability and volume, plus manual approval thresholds for large blocks.
- Approve a locked policy candidate and evaluation protocol before a new holdout evaluation or operational pilot.

The accepted-with-changes decision retains human control and no additional overbooking as the selected fallback until those prerequisites are met. Stage 6 service work can expose candidate decisions for review; it does not constitute deployment approval.
