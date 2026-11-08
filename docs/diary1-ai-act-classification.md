# Diary 1 — EU AI Act classification

Reviewed **8 November 2026**. Working coursework assessment of the specified use, not regulatory clearance for a real hotel. Legal conclusions below are reasoned interpretations of the cited provisions, not outputs of an automated compliance test.

## 1. Intended use and conclusion

The system predicts booking cancellations and produces per-hotel aggregate nightly overbooking recommendations for a human revenue manager. The implemented local demonstration uses a historical dataset, simulated approvals and no live inventory or guest-selection action. The LightGBM model generates inferred predictions, so this is an AI-system assessment rather than an assessment limited to generative AI. [Article 3(1), (12)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-3).

**Potential ordinary commercial hotel use: other/non-high-risk, often described as minimal risk, on the specified facts.** No Article 6 high-risk route has been identified. This is not a finding that the system is harmless, accurate or compliant with every law. **Current local coursework activity: assess the pre-deployment research/testing exclusion separately.** Do not equate an exclusion from scope with a low-risk classification. [Article 6](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6), [Article 2(8)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-2).

## 2. Classification reasoning

| Check | Application to this intended use | Basis |
|---|---|---|
| Scope of the current activity | The historical, local demonstration appears consistent with pre-market/pre-service testing. This depends on it not being used operationally with actual hotel customers. Article 2(8) excludes such pre-deployment activity but expressly excludes real-world testing from that exclusion. There is no blanket exemption merely because someone is a student. Do not rely automatically on the separate sole-scientific-R&D or personal-use provisions. | [Article 2(6), (8), (10)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-2) |
| Product/safety high-risk route | This cancellation/overbooking application is not identified as an Annex I regulated product or its safety component requiring third-party conformity assessment. That is the relevant product route, not the mere possibility of a costly mistake. | [Article 6(1)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6) |
| Listed-use high-risk route | Ordinary commercial cancellation forecasts and aggregate overbooking quantities are not a listed Annex III use. Its “essential private/public services” heading does not make every hotel service high-risk: point 5 specifies public-assistance eligibility, creditworthiness, life/health insurance and emergency-response/triage uses. | [Article 6(2)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6), [Annex III(5)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3) |
| Prohibited practices | No prohibited practice is identified in this aggregate planning demonstration. It does not implement manipulative persuasion, biometric inference or a social-scoring system for adverse treatment. A future cross-context or disproportionate guest-ranking practice would require a fresh Article 5 analysis; a cancellation score is not automatically prohibited social scoring. | [Article 5, particularly (1)(a)–(c)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-5) |
| Human review | Human approval is an operational safeguard, not a universal legal exemption. Our reasoning does not depend on the Article 6(3) derogation, because no Annex III use has been identified. Its profiling rule applies to systems referred to in Annex III, not every prediction concerning a person. | [Article 6(3)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6) |

The Resort's calibration failure is a model-quality finding; it does not itself turn the application into an Article 6 high-risk system. Conversely, good latency or passing calibration would not remove a genuinely listed high-risk intended use.

## 3. Provider and deployer

The definitions distinguish development from legally supplying/putting a system into service under one's name, and use under one's authority. [Article 3(3), (4), (11)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-3).

| Situation | Provider/deployer assessment |
|---|---|
| Present coursework | Luke is the developer/operator of a local demonstration; the revenue-manager role is simulated. Do not invent a real hotel deployer or treat a simulated role as proof of legal deployment. |
| Luke or a software company supplies the hotel system under its own name | That supplier would be the provider; the hotel operating it under its authority would be the deployer. This is conditional on actual supply/use. |
| Hotel has the system developed and puts it into service under its own name for its own use | The hotel could be both provider and deployer; the programmer is not automatically the legal provider. |

An employee revenue manager acts for the hotel. Supplying the teaching notebook or a software library does not alone establish provider status for the assembled hotel system.

## 4. Non-high-risk is not “no responsibilities”

For a real in-scope deployment, the amended Article 4 requires measures supporting staff AI-literacy development; it does not require guaranteeing a particular individual attainment level. Reviewers should understand probability horizons, calibration warnings and approval limits. [Current Article 4](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-4).

Article 50(1) must be assessed for direct human interaction, including the manager interface where applicable. Clearly tell the reviewer that recommendations are AI-generated; do not assume that merely lacking a chatbot removes transparency considerations. Its obviousness exception is contextual. No biometric recognition or synthetic-media feature is implemented here; the future LLM briefing needs a separate transparency assessment. [Article 50](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50).

Data-protection/privacy and consumer-protection law are not displaced by this classification. Nationality exclusion and human review are useful controls, not proof of complete compliance. GDPR decision-making and discrimination questions require the separate E2 assessment before real guest-impacting use. [Article 2(7), (9)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-2).

## 5. Changes that require reassessment

- **Remove nightly human approval, keeping the same ordinary commercial planning purpose:** changes safeguards and operational risk, but does not alone establish an Annex III category. [Article 6](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6).
- **Choose particular guests to relocate, refuse service or vary terms:** requires fresh analysis of the actual treatment, features and other applicable law; not automatically high-risk just because a guest is affected. Social scoring must be checked against its specific conditions. [Article 5](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-5).
- **Repurpose it on behalf of a public authority to decide eligibility for essential emergency-housing assistance:** may bring it within Annex III(5)(a). Merely accommodating a publicly funded guest is not the same as deciding benefit eligibility. [Annex III(5)(a)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3).
- **Add guest-facing conversational/generative functions:** reassess the relevant interaction/content transparency rules rather than carrying over this conclusion unchanged. [Article 50](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50).

The assessment must therefore follow intended purpose and actual deployment context, not the label “hotel AI” or a permanent risk tier attached to the model file.

## 6. Law version and dates — avoid the original timetable

Use Regulation (EU) 2024/1689 **as amended by Regulation (EU) 2026/1744**, in force from 27 July 2026. EUR-Lex identifies the 27 July 2026 consolidation as current when checked. The consolidation is a reference aid; the original and amending Official Journal acts are the legally authentic texts. [Consolidated AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng), [amending Regulation](https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng), [Commission Explorer notice](https://ai-act-service-desk.ec.europa.eu/en/ai-act-explorer).

Article 113 retains general application from 2 August 2026, but defers Chapter III Sections 1–3, except Article 6(5), to **2 December 2027** for Annex III systems and **2 August 2028** for the Article 6(1)/Annex I route. This note uses the adopted classification tests for prospective hotel use; it does not say all high-risk duties are already applicable in November 2026, or that all AI Act rules were postponed. [Current Article 113](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-113).

## 7. Concise line for the diary/slides

**Ordinary commercial cancellation/overbooking advice: other/non-high-risk on this intended use (Article 6(1)–(2), Annex III); provider: entity supplying it under its name; deployer: hotel operator. The present local coursework test is assessed separately under Article 2(8).**

This is a scoped conclusion, not a licence to deploy. Retain manager review, versioned audit, data-quality checks and the stated limitations. Verify the intended use, responsible entities and current law again before real operational use.

## 8. Evidence and what remains

Technical premises are supported by `docs/manager-approval.md`, `docs/diary1-architecture.md`, `src/hotel_cancel/serving.py`, `batch.py` and `approvals.py`: prediction plus per-hotel recommendations, simulated decision capture, no real inventory/guest selection action. The source register and checked provisions are saved in `docs/evidence/diary1/ai-act-classification.json`.

This completes the Diary 1 classification research note, not the later E2 fairness/legal investigation, a conformity assessment, production legal review or implementation of the future GenAI component. Reuse the legal reasoning and references, but make the final diary's reflection your own. Commit the note and source register before citing them.
