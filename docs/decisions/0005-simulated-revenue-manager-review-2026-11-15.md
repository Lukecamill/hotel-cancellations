# Simulated revenue manager review of ADR 0005

Date: 15 November 2026. Decision: accepted with changes.

## Simulation and AI declaration

OpenAI Codex generated this role-play in the project chat after Luke supplied the professor's guidance permitting an AI-simulated revenue manager. The same assistant generated the reviewer questions and project-side answers from inspected repository evidence. These are newly authored simulated dialogue, not quotations from Luke, an independent second model or a real hotel manager. No Claude or Gemini session is claimed. No production decision or digital signature is implied.

The reviewer received [the complete brief](0005-review-brief-2026-11-15.md). This review concerns ADR 0005's mature-outcome Stage 5 candidates, including the Resort 12-week candidate. It does not retrospectively sign the different 8-week reference-policy packet.

## Questions before the decision

**Simulated revenue manager:** What proves these extra rooms are actually sellable, including multi-night stays?

**Project-side answer, generated from the evidence:** Nothing in the dataset establishes true sellable room-night capacity. The study assumes sold-out arrival nights and uses booking-room proxies. A real inventory check, existing commitments and room-type constraints would be required. We therefore retain q=0 as the fallback rather than translating the historical mean quantities into live permissions.

**Simulated revenue manager:** City saves more, but it walks 0.25 booking-rooms per night. Who accepted that disruption, and are EUR250 and zero resale actual operating values?

**Project-side answer, generated from the evidence:** No real manager accepted a walking-risk limit. EUR250, EUR20 and zero resale are explicit reference assumptions. The grid covers walking EUR100–500, variable costs 0/20/40 and resale 0/25/50 percent. They need operating evidence; we cannot choose the most profitable assumptions or claim EUR250 fully captures guest harm.

**Simulated revenue manager:** Does zero observed Resort walking prove safety, and is its EUR3.29 saving robust?

**Project-side answer, generated from the evidence:** No. It is zero observed in 92 validation nights, not a zero-risk estimate. The same nights selected and described the winner, so the saving is optimistic. Resale assumptions change the winning Resort policy. Initial seven-day calibration is weak, and the passing booking-horizon calibration cannot be substituted for it. No fresh Stage 5 holdout evaluation has been performed.

**Simulated revenue manager:** Are the blocks real parties, and what happens if someone treats an approved historical recommendation as permission to act?

**Project-side answer, generated from the evidence:** Blocks are inferred exact-key matches and may not identify actual parties. They require PMS confirmation and human handling. This review grants no automatic extra-room allocation, relocation or guest messaging. The original baseline and failures stay visible. Any future proposed change needs a new versioned decision, named owner and separately established operating constraints.

## Reviewer decision and reasons

**Revenue manager, simulated with OpenAI Codex: accepted with changes.** Accept the Stage 5 study and retain City fixed mature-window rate and Resort blocks with 12-week re-level as research candidates. Do not accept their positive additional quantities as the current operating point. Choose **q=0 additional overbooked rooms for both hotels**, with the seven-day review horizon and EUR250 walking/EUR20 variable/zero-resale reference assumptions retained solely to make the historical comparison reproducible.

The required change is to distinguish an interesting historical candidate from the selected conservative operating fallback. Unknown capacity, unverified blocks, unagreed walking tolerance, weak initial seven-day calibration and selection optimism outweigh the evidence for approving positive quantities. Zero additional overbooking does not prove existing inventory is feasible or eliminate all guest-relocation risk; it only withholds this policy's additional overbooking.

**Handoff:** Luke, as the coursework project owner, records this decision and the assumptions in ADR 0005. This transcript itself records the outcome; no claim is made that Luke separately supplied the generated answers. If a positive quantity is reconsidered, the next review must receive verified room-night inventory, supported cost/resale assumptions, an explicit walking-risk limit and group-handling thresholds, and a locked validation/evaluation plan. A real hotel owner would make any real operating decision. The coursework professor's requested simulated review is now recorded; this does not close unrelated peer review, registry setup or submission checks.

Decision: accepted with changes. Signed off by: Revenue manager (simulated with OpenAI Codex), 15 November 2026. This line records the declared AI simulation, not a human or hotel signature.
