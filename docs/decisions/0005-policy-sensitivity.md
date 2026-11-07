# ADR 0005 — validation-only policy sensitivity and manager review

Date: 7 November 2026. Status: proposed for revenue-manager sign-off; implementation and evaluation complete.

## Decision

Keep the original C2 reference baseline reproducible. Extract shared horizon/block preparation into `prepare_policy`, preserving the original defaults. Run C3 experiments through a separate validation-only entry point and prespecified grid. Mature calibration labels before the first selection decision. Include a no-overbooking fallback; compare perfect block correlation with independent booking cancellation. Model resale as explicit residual-margin recovery rather than an inferred fact.

For the reference assumptions (7 days, €250 walking, €20 variable cost, zero resale), nominate the fixed calibration-window rate for City and blocks with 12-week re-level for Resort for further review. These differ from the original baseline's Resort 8-week choice because the Stage 5 calibration fit is restricted to outcomes mature at decision time. Do not replace the reference baseline or deploy these candidates.

## Evidence and trade-offs

The [Stage 5 report](../stage5-policy-evaluation.md) and its complete CSV grid record validation costs. City reference savings are €92.01 per night, with 0.25 walked rooms per night; Resort savings are €3.29 with no observed walking in these 92 nights. Zero observed walking does not establish zero risk. Both hotels' initial horizon-model calibration remains weak. Resale reduces the marginal value of overbooking and changes winners. Exhaustively selecting across these scenarios would exaggerate evidence: business settings must be supplied externally, not chosen from validation profits.

The resale approximation is transparent and inexpensive but cannot represent replacement demand, prices, capacity, multi-night availability or dependence of resale on cancellation time. The original no-resale case is retained as a comparison. The 4/8/12-week windows expose adaptation versus limited recent data without changing the booking learner or using the frozen test for tuning.

## Required sign-off fields

Revenue manager: pending. Date: pending. Hotel: pending.

- Confirm walking and variable costs, supported by operating records.
- Confirm lead time and evidence for a resale rate or retain zero resale conservatively.
- Confirm true sellable capacity and room-night availability; validate inferred blocks with the PMS.
- Set maximum acceptable walking probability and volume, plus manual approval thresholds for large blocks.
- Approve a locked policy candidate and evaluation protocol before a new holdout evaluation or operational pilot.

Until those fields are agreed, retain human control and no-overbooking as the operational fallback. Stage 6 service work can expose candidate decisions for review; it does not constitute deployment approval.
