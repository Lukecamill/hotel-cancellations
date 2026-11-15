# Session 6 model card review and response

Feedback supplied by Luke on 15 November 2026 and attributed by Luke to Jake Desira. The actual review date, exact version Jake inspected and reciprocal exchange of cards are not yet confirmed. Luke described the review as applying to his latest version today; the current City version 2 card is the target of this response. This records supplied feedback without independently verifying the reviewer or claiming completion of the reciprocal exchange.

## Supplied review text

The project demonstrates a thoughtful approach to evaluation and reproducibility. Its strongest feature is the distinction between reproducing the supplied model and establishing that it is suitable for use. Preserving the Resort model’s calibration failure makes the conclusions credible and shows why a good ranking score alone does not justify an operational decision.

From a manager’s perspective, the model card clearly explains the intended use and important limitations, including unknown hotel capacity and the difference between predicting cancellations and deciding how many rooms to oversell. However, the manager is currently the least well served reader because the exact results are stored elsewhere. I recommend adding a short opening summary identifying the registered version, hotel, evaluation results, gate outcome and permitted use. This would make the card easier to understand without inspecting technical artifacts.

From a regulator’s perspective, the discussion of historical data, potentially unavailable booking-time information and the exclusion of nationality is useful. The card also clearly limits the system’s intended use. It would benefit from identifying who is responsible for reviewing its use, investigating problems and approving changes. The relationship between model predictions and the human decision should also be explained explicitly.

For the engineer on call, the rollback commands, readiness checks and recorded model lineage provide practical guidance. The main improvement would be to explain what happens when rollback fails or the registry is unavailable. The card should identify how to select a previously passing version and what fallback applies when no eligible version can load.

The monitoring plan appropriately distinguishes input drift from predictive quality. However, the card should state its alert thresholds, outcome-maturity rules and retraining triggers directly instead of relying on references to other documents. It should also identify who receives an alert and what action they are expected to take.

My main recommended revision is therefore to make the model card self-contained and specific to the registered version. The project’s technical evidence is substantial, but the documentation should communicate its implications more directly. The remaining CI issue also needs attention: a passing coursework reproduction check that preserves the Resort failure should not be presented as a passing strict model-quality gate.

## Changes made on 15 November 2026

The manager was identified as the least well served reader. The principal change is a standalone City version 2 decision summary containing its hotel, run, clean model commit, metrics, thresholds, gate outcomes, permitted use and fallback. Values are taken from run a849c16fdb4e432fb172b8ca2f3301dc. The [version-specific card](../model-cards/task19-session6-city-booking-v2.md) is separate from the [generic registration card](../model-card-session6.md), so City results are not presented as results for every future candidate.

The cards now identify Luke as the coursework owner, explain the human decision boundary, state monitoring thresholds and maturity rules directly, and describe failed rollback, alias/process mismatches, registry outages and the no-eligible-version fallback. They distinguish proposed monitoring policy from configured external notification delivery. The current registry API requires both hotel models; City registration alone does not establish readiness.

The strict CI concern remains unresolved. This documentation revision changes neither the prescribed model nor the frozen thresholds. It does not record a manager's operating approval.

## Evidence and remaining steps

- Model: models:/task19-session6-city-booking/2 in the local diary2 registry.
- Metrics source: artifacts/diary2/mlartifacts/a849c16fdb4e432fb172b8ca2f3301dc/artifacts/eligibility.json.
- Training source: c9e3bfaf6b3d073dd9930ba60761ef932af1ab80. This card revision is a later uncommitted documentation change.
- Registry description update/readback: docs/evidence/diary2/model-card-review-update.json, once successfully executed.
- Confirm Jake's actual review date and reciprocal review of his card before claiming the required exchange is complete.
- Journal, slide and video-script drafts, speaker notes and exported PDFs/PPTX now incorporate the supplied feedback and card revisions. They retain the unconfirmed review date, reviewed-version and reciprocal-exchange limitations.
- Codex applied the supplied feedback and drafted this response record; Luke should verify the changes and attribution.
