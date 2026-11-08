# Diary 1 — capability-pattern comparison

Prepared 8 November 2026. This compares one architectural choice using the existing evidence. It does not implement automatic overselling, measure a manager's performance or claim that the lecturer has accepted a simulated sign-off.

## Options being compared

**A — Current mixed pattern:** online booking prediction plus an offline nightly policy batch, with a simulated human reviewer approving, reducing or rejecting each hotel's candidate quantity. Operational authorisation remains zero in the coursework system.

**B — Hypothetical automatic nightly action:** retain the same online prediction and nightly batch, but automatically accept the candidate quantity without a nightly reviewer. A real channel-manager connector, verified sellable capacity and automatic control/failure checks would have to be added. They are not implemented or benchmarked.

Holding the model and forecast calculation constant isolates the architectural decision: **who acts on the nightly result**, rather than changing the learner or confusing booking-time cancellation probability with a seven-day decision.

The course's Session 1 main document, section 3.3, page 6, explains that real systems often combine online prediction, batch prediction and human-in-the-loop. The reflective-diary brief asks for a comparison on latency budget, daily running cost, decision ownership and failure behaviour.

## Side-by-side comparison

| Required criterion | A: nightly human approval — current system | B: automatic acceptance — hypothetical alternative |
|---|---|---|
| **Latency budget** | Common measured machine components: booking API p95 **34.25ms** during the 5-request/s burst; example nightly forecast **44.72ms** for 81 on-books records. Human review adds an **unmeasured** turnaround time. The booking API's 250ms budget passed; no human-review deadline has been established. | If the same components are reused, removing review removes the human wait, not the inference work. Machine measurements come from A; they do **not** prove B's end-to-end latency. Inventory-connector, retry and safety-check times are unmeasured. |
| **Running cost per day** | Shared local platform cost is **unmeasured**, not zero. Illustrative reviewer labour: 2 hotels × 5 minutes/day × €15/hour = **€2.50/day**, plus ongoing model/service oversight and policy losses. These minutes and rate are assumptions, not observed hotel costs. | Shares the platform/model work and may avoid that **€2.50/day assumed routine-review cost**. Extra connector, control, maintenance and incident costs are unpriced; monitoring and business accountability remain. Net savings are not established. |
| **Who owns the decision?** | Simulated revenue manager makes the nightly choice and records a name, quantity and reason. Project/model owner maintains the service and investigates alerts. Self-declared names are not production authentication. | The software would execute a manager-authorised policy without nightly review. Hotel management/deployer would still own the business policy and accountability; the algorithm does not become the accountable party. Roles and permissions would need implementation. |
| **What happens when it fails?** | No final review means no simulated approved quantity. Unavailable database/review service prevents a new approval record. Prediction-log failures are visible in metrics and response flags. The operational fallback remains zero extra rooms/manual handling; human mistakes or rubber-stamping remain possible. | Proposed controls would need to prevent action when capacity, snapshots, versions, quality or the inventory connector are invalid. Otherwise a healthy, fast service could execute a poor decision repeatedly. Such fail-closed controls and reversal/reconciliation are **design requirements, not implemented guarantees**. |

## What the measurements establish

The Stage 7 experiment sent 600 measured requests across two phases, with zero HTTP errors and every measured prediction verified in PostgreSQL. Client timings include waiting from the scheduled arrival, inference, response and synchronous database logging. The original booking-shaped phase had p95 34.25ms; the deliberate lead-time-shift phase had p95 33.62ms. These show that the tested service meets the chosen 250ms response budget under that burst envelope.

The 44.72ms batch measurement includes artifact loading and the example forecast calculation. It excludes manager interaction and a real PMS/inventory transaction. It is a single example, not a batch p95 or proof of full-job completion time. The hypothetical automatic workflow has not been run. Therefore, it would be misleading to write “automation takes 44.72ms but human review takes five minutes”: only the machine time was measured.

The system uses local LightGBM inference rather than a paid external inference endpoint. That does not make its total daily cost zero: hardware, electricity, staff time and ongoing operations have not been priced or metered. No Malta electricity tariff, real salary or actual hotel budget is claimed here.

## Quantified cost and risk trade-off

Versioned assumptions are in `config/diary1-comparison.json`:

- Two hotel reviews per day.
- Five minutes per hotel review and €15/hour of reviewer time, both **illustrative assumptions**.
- €250 per walking unit, the notebook's configured cost assumption, **not a verified hotel charge**.

Routine review cost is `2 × 5 / 60 × €15 = €2.50/day`.

If all other costs and quantities were identical, automation could save that assumed €2.50/day. One additional €250 walking event every **100 days** would consume that saving: `€250 / 100 = €2.50/day`. Equivalently, the break-even increase is **0.01 walking units/day across the two hotels**. This is a mathematical threshold, not an estimated probability that automation would cause such an event. It uses the notebook's per-room/booking walking-cost rule, not the number of individual people in a party.

The more complete condition is:

```text
automation is economically preferable only if
  extra automation/control/oversight cost
  + change in expected walking cost
  + change in expected empty-room cost
  < routine review cost saved
```

Here, each term is per day, changes are relative to human review, and the right-hand side is €2.50 only under the stated assumptions. Integration/capital cost would need an explicit amortisation period. Faster action could affect resale or missed-sales losses, but that benefit has not been measured. Review might improve, leave unchanged or worsen decisions; there is no measured human advantage.

### Sensitivity to the assumed review time and walking cost

| Assumed minutes per hotel/day | Assumed review cost/day at €15/hour | Break-even interval for one extra €250 walking event |
|---:|---:|---:|
| 2 | €1.00 | 250 days |
| 5 | €2.50 | 100 days |
| 10 | €5.00 | 50 days |

With the five-minute assumption, a €100 walking cost gives a 40-day break-even interval and €500 gives 200 days. These scenarios demonstrate sensitivity; none is a measured operating point. Full combinations are in `docs/evidence/diary1/pattern-cost-sensitivity.csv`.

## Keep policy losses separate from IT running costs

The frozen-reference 2017 replay estimates approximately €264.42 per City night and €96.18 per Resort night, versus €278.65 and €98.07 without overbooking. These are **walking plus empty-room losses**, not electricity, cloud or staffing bills. They are Jan–Aug 2017 reference-policy results, not Stage 5 validation savings.

If a human and an automatic system both accepted exactly the same quantities, those simulated losses would be identical. Adding the illustrative €2.50 review labour to the combined policy losses would give about €363.11/day versus €360.61/day before shared platform and alternative-specific costs. That arithmetic is only a same-quantity scenario; it does not demonstrate the actual total cost of either architecture, and no human decisions were simulated to generate those policy losses.

## Recommendation and evidence that could change it

Retain human approval for the coursework. Task 19 explicitly describes a person approving the nightly oversell, so automatic execution is a comparator, **not a compliant replacement for that requirement without a changed brief**. Independently, real capacity is unknown, the original Resort booking-model gate fails, the data are final-state snapshots, and no live inventory connector or production identity/permissions exist. A fast response does not resolve those deficiencies. Current evidence supports the speed of the calculation, not safe autonomous hotel control.

For a separately authorised future system, consider automation only after:

1. Verifying sellable room-night capacity, event-time snapshots and safe inventory updates/reconciliation.
2. Establishing mature per-hotel predictive/policy performance and explicit quality/failure gates.
3. Measuring actual review turnaround, staffing time, missed-deadline cost and additional automation/oversight costs.
4. Showing on separate permitted evaluation data that the **net additional daily loss and operating cost is below the measured labour saving**—€2.50/day only in our illustrative scenario.
5. Agreeing accountable roles, exception handling, audit and rollback with the business owner.

If review misses a documented nightly deadline, that would count against A; no such delay was measured here. If automatic actions satisfy the checks and remain below the risk/cost threshold, the future alternative could win. This conditional argument is stronger than claiming either that humans always improve outcomes or that automation is always cheaper.

## Reproduce and use in the diary

```sh
.venv/bin/python scripts/compare_diary1_patterns.py
```

The JSON evidence separates measured, derived and assumed values, records input/source hashes and identifies the base commit/working-tree state. Commit this report, the assumptions, calculation and aggregate evidence before citing the comparison. No model/policy code or deployed approval behaviour changes in this step.

Sources within the project: `docs/evidence/stage7/performance.json`, `batch.json`, `replay/policy-summary.csv`, `config/config.yaml`, the manager approval implementation and `docs/manager-approval.md`. Course framing: Session 1 §3.3, page 6, and Reflective Diary Entry 1 task 5. The table is reusable evidence; your final diary should explain your own judgement rather than attribute unmeasured experience or beliefs to yourself.
