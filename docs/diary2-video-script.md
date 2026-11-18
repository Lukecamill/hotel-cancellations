# Entry 2 video script

Luke Camilleri | Own-voice recording | Target 4:45-4:55, maximum 5:00

Draft for rehearsal: 607 spoken words. Timings are targets, not a measured recording. Read only the spoken paragraphs. Show the slides in order; do not read full run IDs. Rehearse at roughly 130-140 words per minute and stop by 5:00. The slides and script introduce no investigation beyond the journal evidence. Review all first-person statements before recording. Peer feedback and card revisions are recorded. Reciprocal card review and a strict passing-gate CI example remain pending.

## Slide 1 | 0:00-0:15 | The honest gate and registered model

Hello, I’m Luke Camilleri. My second diary examines whether my hotel cancellation model earns confidence. I focus on evaluation, release controls and the evidence needed before promotion.

## Slide 2 | 0:15-0:55 | Random and forward evaluation

The random split gave City an AUPRC of about point eight seven nine, compared with point seven eight six forward in time. Resort fell from point seven four eight to point six two eight. The random split also shared four thousand six hundred and twenty-six full-row signatures between training and test, while the forward split shared none. Random training included future-era bookings. I therefore retained the later frozen window for release decisions. Different time mixtures also contribute to the gap.

## Slide 3 | 0:55-1:35 | The metric that changed the decision

Ranking performance alone gave the wrong impression. Resort passed its AUPRC floor, but its expected-to-observed cancellation ratio was only point six eight two. The bootstrap interval stayed entirely below the accepted band. This is why I retained calibration alongside discrimination. Accuracy would also hide the problem because most Resort bookings do not cancel. The date-cluster bootstrap retains same-day dependence, but misses dependence between dates. I did not change the given model or the gate to obtain a better result.

## Slide 4 | 1:35-2:05 | What green CI actually proves

These are two real GitHub runs. The first stopped at the failed quality gate. The later run passed the revised coursework checks, which verify that the expected reference failure reproduces. That green result does not mean Resort passed the strict release gate. I now distinguish reproducible software from acceptable model quality. A passing strict model-gate CI example remains an open requirement.

## Slide 5 | 2:05-2:40 | Tracked versions and rollback

I recorded three fresh training runs from committed source. For City, I registered two passing versions, attached the model card and moved the champion from version two to one and back. Loading each selected version produced the same probability for the same example. That confirms the version-control and reload path, rather than demonstrating a better model. The original Resort baseline stayed unpromoted. The appendix records the commit and run identifiers.

## Slide 6 | 2:40-3:10 | City drift and calibration

The City plot uses the same arrival-month axis for drift and calibration. June and August had similar lead-time PSI values, roughly point four two and point four three. However, calibration moved from about point nine seven to point seven one. A high drift statistic therefore does not tell me how much predictive harm occurred. These retrospective cohorts do not demonstrate live alerts.

## Slide 7 | 3:10-3:40 | Resort drift and calibration

Resort shows the opposite problem. In April, lead-time PSI was only point zero eight two, below the investigation threshold, while the cancellation ratio was already about point seven two four. A rule watching only lead-time drift could miss this failure. Looking at both input change and mature model outcomes is therefore necessary. I would investigate the data and label process before assuming retraining alone would solve the issue.

## Slide 8 | 3:40-4:15 | Monitoring policy and model card

My proposed policy investigates PSI above point one and requests action review above point two five. Two consecutive mature monthly calibration breaches trigger a retraining review, with minimum sample requirements. Neither condition moves the champion automatically. The coursework owner controls alias changes. Feedback attributed to Jake Desira identified managers as the least well served readers. I added a City version two results summary and permitted use, clearer responsibilities and rollback fallbacks. This made the evidence more accessible.

## Slide 9 | 4:15-4:45 | Lessons and remaining evidence

My main lesson is that reproducibility, useful ranking and safe economic decisions require different evidence. Random splitting can flatter performance, calibration can fail despite acceptable ranking, and input drift may not track the model's errors. Before submission, the reciprocal card review need confirmation, and strict passing-gate evidence remains outstanding. Codex helped with implementation, analysis and drafting. I am responsible for checking the claims and explaining the reasoning in my own voice.

## Slide 10 | 4:45-4:55 | Evidence register

The written appendix contains the evidence files, run identifiers and GitHub links.

