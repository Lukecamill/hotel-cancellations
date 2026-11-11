# How the revised revenue manager briefing works

V5 produces a briefing from verified nightly facts and a small interpretation from
the local Qwen model. Trusted code copies the numbers into the final output. The
model is not allowed to supply different booking counts, room quantities or costs.
An interpretation that fails the schema or contradicts the source is withheld.
This is exactness of the delivered component, not a claim that the language model
has learnt to copy all numbers perfectly.

## One example

Suppose the trusted City context says 66 bookings and proposes three extra rooms.
The final fact table copies 66 and 3 directly from that context. The model cannot
change 3 to 30: its allowed response has no hotel or numeric fact fields. If it
adds one, schema validation rejects the response. These are illustrative numbers
from the reference example; the code works the same way with previously unseen
values and has a test for that behavior.

Copying preserves an input; it cannot make a wrong input correct. The context must
still come from the verified batch, matching horizon, policy and model identity.
The original Resort FAIL remains in the context. Nothing here corrects calibration,
proves real hotel capacity or authorises an overbooking decision.

## What the model may supply

The response schema permits exactly four fields:

| Field | Constraint |
| --- | --- |
| `deposit_prepaid` | Boolean supported by the supplied KB fact, or null when the fact is absent |
| `action` | Either calibration review or manager review; it must agree with the context's hotel gate states |
| `guest_message` | The allowed conservative draft, not arbitrary promises or invented refunds |
| `human_approval_required` | Must be true |

The model receives the context and available KB facts through the configurable
OpenAI-compatible local endpoint. The prompt, model tag/digest, schema and cases
are versioned. No live model is called by CI.

## Validation before delivery

1. Parse JSON strictly. Reject duplicate keys and non-finite JSON numbers.
2. Validate the interpretation schema. Reject additional fields, unsupported
   actions, arbitrary guest text or a false approval flag.
3. Validate the source context schema, then deep-copy its facts and combine them
   with the interpretation. Model fields cannot overwrite the numeric table.
4. Compare the assembled answer with the supplied context and KB contract. An
   absent KB fact requires abstention; any failing hotel requires calibration
   review. Merely using a permitted action name is not enough.
5. Return a briefing only if all checks pass. `deliver()` raises an error otherwise;
   `generate()` uses that delivery boundary. There is no hidden correction, retry
   or selection of a better response after generation.

Notes supplied with a case are data, not authority to change the rules. In the
recorded attacks, one model response chose manager review despite a failed gate.
That response was valid JSON but contradicted the context. It was withheld, not
rewritten into a successful model answer.

This boundary applies to the V5 `generate()`/`deliver()` entry points; the old V1
recording/demo paths remain historical and are labelled separately. A displayed
briefing is not a sent guest message. Human approval binds the exact draft and
context digest; edits invalidate it. The project does not dispatch messages.

## What the evaluation establishes

[The recorded run](evidence/remediation/briefing-v5/report.json) used pinned
`qwen3:4b-instruct` locally with zero API fees. It has 96 raw responses:

| Cases | Recorded outcome |
| --- | --- |
| 30 original nights | 30 accepted; regression against the earlier calendar |
| 30 additional nights with KB | 30 accepted |
| Same 30 additional nights without KB | 30 accepted with required abstention where facts are absent |
| Six injected notes attacks | Five accepted correctly; one wrong interpretation withheld |

All 90 ordinary delivered briefings were exact. All six attacks were safely
handled, but only five produced accepted briefings. Hence the delivery component
passes while the raw-model all-case result is 95/96 and remains FAIL. Withholding
is a safe outcome, not evidence of a correct generated interpretation.

The V5 run records p50 latency 1.56 seconds and p95 2.10 seconds on the stated Mac.
Zero API fees exclude hardware/electricity costs; energy was not measured. These
are single-run observations, not guarantees for every machine or future prompt.
V1 still records 27/30 exact with-KB nights; V2–V4 development failures are retained.
V5 has a different output contract, so it is not an equivalent numeric-copying
benchmark against those versions.

[Raw responses and assembled outputs](evidence/remediation/briefing-v5/responses.json)
are kept separately. [MLflow evidence](evidence/remediation/briefing-v5/mlflow-run.json)
records the run. `make revised-briefing-quality` replays it, checks prompt/schema/
context/settings/model fingerprints and recomputes the scores. Changed fixtures,
missing cases or score drift fail. New live inference must be recorded and logged
when the prompt, context or model changes.

Tests in `tests/test_briefing_revision.py` reject numeric overrides, check unseen
source values, detect prompt/fixture changes and withhold wrong actions at both
the recorded and live-call delivery boundaries.
