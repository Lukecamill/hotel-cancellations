# Entry 1 video script

Luke Camilleri | Draft for own-voice rehearsal | Target 4:40-4:55, maximum 5:00

Timings below are rehearsal targets, not a measured recording. Review the first-person reasoning before recording. The journal contains the same experiments and evidence. Speak only the paragraphs below each slide heading, not full run IDs or file paths.

## Slide 1 0:00-0:15 Hotel cancellations and overbooking

My first diary examines whether I can reproduce the supplied hotel cancellation model and operate it responsibly. I kept the learner unchanged and investigated the data, the container and the architecture.

## Slide 2 0:15-0:45 Baseline reproduction

City AUPRC was about point seven eight six and Resort about point six two eight. Both rank cancellations, but Resort fails the calibration band. A separate fresh clone reproduced the baseline. The new local measurement separates fitting, about half a second, from the complete booking pipeline, about one point seven seconds. The older Ubuntu pipeline observation remains separate. 

## Slide 3 0:45-1:20 Data quirks and guards

I counted nearly thirty-two thousand extra duplicate rows, nineteen hundred and fifty-nine zero prices and a strong nationality recording artefact. The full journal table links each to its consequence and guarding check. Temporal split tests reject overlap, and feature tests reject dependence on country. My additional check found twenty-seven Check-Out date discrepancies. Because recorded nights can describe planned or actual stays, the audit flags these cases without changing their labels.

## Slide 4 1:20-1:45 Container portability

The container exposed a missing PyArrow dependency that my Mac environment had concealed. Fixing it made the saved model load in Ubuntu. The historical image was about two hundred and twelve megabytes. Host and container predictions agreed within the recorded tolerance. 

## Slide 5 1:45-2:10 Service and model monitoring

The historical Ubuntu test returned all six hundred measured requests successfully and verified their database records. Its booking-phase p95 was thirty-four point two five milliseconds. Yet Resort calibration still failed. The dashboard measures current service behaviour immediately, while cancellation quality needs mature outcomes. A fast API can therefore keep returning poor probabilities.

## Slide 6 2:10-2:35 Enterprise architecture

The architecture separates the manager's business decision, the data and delayed labels, the prediction and review applications, and the containers that run them.   Label delay connects the layers because it limits what the monitoring application can know.

## Slide 7 2:35-3:00 Approval scopes

I initially confused approval of a policy with approval of one night's quantity. The review screen records approve, reduce or reject for a night. A separate declared AI-simulated policy review now selects zero additional rooms for both hotels. Neither authorises real hotel operations. 

## Slide 8 3:00-4:10 Online and batch comparison

I compared immediate and daily batch computation of the same booking scores. On three hundred and twenty-five bookings, local online p95 was twenty-two point four eight milliseconds. Batch scoring took thirteen point four six milliseconds median, including model loading. Their predictions matched exactly. This experiment excludes the database and differs from the Ubuntu load test.

I compressed a reconstructed booking day near the observed daily ninety-fifth percentile into a five-per-second stress burst. Batch is efficient but can delay a score by a day. At an assumed ten cents per allocated hour, dedicated online hosting costs two euros forty per day; a one-minute-billed batch costs about one sixth of a cent. These are billing scenarios, not observed bills. A shared running host saves no invoice cost. I retain immediate scores where needed and would switch only if daily delay is acceptable and costs are actually avoidable. Nightly policy approval remains human-controlled under both alternatives.

## Slide 9 4:10-4:40 Classification and reflection

My existing working assessment treats ordinary commercial overbooking advice as non-high-risk under Article Six and Annex Three. The prospective provider is the releasing entity and the hotel is the deployer. Coursework testing has a separate scope assessment. Changed intended use would require reassessment. My main lesson is to seek distinct evidence for reproduction, service performance and decision quality. Codex assisted implementation, analysis and drafting; I remain responsible for the interpretation.

## Slide 10 4:40-4:50 Evidence register

The written appendix contains the committed evidence references and the new measurement report. I will review the claims and rehearse this in my own voice before submission.
