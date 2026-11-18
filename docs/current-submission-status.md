# Current submission status

Updated 18 November 2026 against local checkout d0bae8c and the new local measurements. This page supersedes older pending-status prose; dated evidence JSON remains historical.

## Verified evidence and current behaviour

- Given model, holdout and quality thresholds remain unchanged. City passes; Resort calibration fails.
- `make coursework-check`: lint, tests, data validation, SHACL, original reference reproduction and offline briefing replay.
- `make ci`: coursework checks, then strict both-hotel quality gate, then image build. The original Resort failure blocks the build.
- `make release-check` and `make publish` retain strict release checks. No image or model promotion is authorised by reproducing an expected failure.
- Three actual clean-source training runs, registered City versions 1 and 2, attached card and rollback 2→1→2 are recorded in `docs/evidence/diary2/clean-registration.json`. Older claims that all candidate registration remains pending are stale. This does not make the both-hotel registry service ready.
- Peer feedback attributed to Jake is recorded and applied. Date and exact reviewed version are not completion requirements. Luke's reciprocal review is the only outstanding exchange evidence.
- ADR 0005 records the declared AI-simulated accepted-with-changes review on 15 November: q=0 additional rooms for both hotels. It is not actual hotel operating authority.
- Diary 1 now separates isolated fit from pipeline runtime and compares measured online and daily batch booking scores. Costs use labelled billing scenarios, not invented invoices or measured labour.
- V5 numerical exactness belongs to the delivered component. Raw-model V1 and injection failures remain visible.
- Existing Entry 2 video container duration is 229.397 seconds (3:49.397), below 5:00. This checks duration only, not voice or agreement with refreshed slides.

## Still requires external evidence or a decision

1. Diary 2 explicitly requires a passing as well as failing CI example. Historical green coursework reproduction is not a strict quality pass. Both hotels remain in scope and no permitted change to the given learner/holdout/thresholds is made. A lecturer interpretation or permitted prespecified decision is needed; see `lecturer-gate-question.md`.
2. Confirm or supply Luke's review of the other student's card. Existing incoming feedback alone does not prove both sides reviewed.
3. Luke must review the first-person drafts, record or refresh narration as needed, and submit the selected journal PDF, slides PDF and own-voice video/link. Do not submit the short course-folder Word draft.
4. Confirm task allocation/VLE announcement, uploads, final deadline and any detailed later-entry/final-project requirements outside the supplied briefs.
5. Commit reviewed source/evidence corrections before citing their new commit, then build final archives. Historical archives and a dirty-state measurement report cannot themselves prove a final clean checkout.

Actual staff time, electricity, hardware and hosting costs are unmeasured. The comparison uses measured wall/CPU time and explicitly assumed prices/billing. It makes no claim of observed monetary savings.
