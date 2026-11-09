# Knowledge-base competency questions and acceptance evidence

These questions define the scope before comparing model outcomes. The
notebook supplies the business semantics as coursework assumptions, not verified
contracts from a real hotel. No question uses a cancellation label to infer a
code's meaning.

| ID | Question | Representation/query | Acceptance evidence |
|---|---|---|---|
| CQ1 | Is this deposit policy prepaid and refundable at the decision date? | DepositPolicy + validFrom/Until; queries/policy.rq; policy_facts | Golden deposit cases; expired mappings abstain |
| CQ2 | Does the segment represent a group and an intermediary? | MarketSegment isGroup/viaIntermediary | Groups/Direct cases; Undefined abstains |
| CQ3 | Is the distribution channel intermediated? | Channel intermediated | TA/TO/Direct cases; Undefined abstains |
| CQ4 | Can a new plan retain known semantic classes without retraining? | Dated hypothetical new-plan contract | Cold-start recomputes real RDF lookups; before-launch case abstains |
| CQ5 | Which country codes have unresolved or noncanonical meanings? | CountryAlias, explicit unknown region, UnknownCode; queries/unresolved.rq | CN alias preserved; ATA/ATF unclassified; original five violations retained |
| CQ6 | Was the UK an EU member at the requested instant? | MembershipAssertion with country, boolean and nonoverlapping UTC interval; queries/membership.rq | 2017 true; 2020-01-31T22:59:59Z true; 23:00:00Z false |
| CQ7 | What supports each mapping, and when does it apply? | prov:wasDerivedFrom; assertionStatus; validFrom/Until | SHACL rejects missing provenance and reversed/overlapping dates |
| CQ8 | When is each source field assumed to become available? | Field writtenAtPhase/availabilityStatus/observedWriteTimestamp; queries/availability.rq | Country unverified; outcomes post-booking; no fabricated observed event timestamps |
| CQ9 | Does adding context improve today's prediction, or vocabulary robustness? | Notebook-fixed learner, forward partitions, codes/additive/classes comparisons | ablation.csv and cold-start.csv; no model selection on test |
| CQ10 | Does a briefing state only supported facts and exact supplied numbers? | Curated 19-case typed grounding contract with/without KB | Semantic precision and coverage reported separately; numeric fields copied exactly; unknowns abstain |

All intervals are [start,end). Ordinary mappings are scoped to the historical
2015-07-01 through 2017-08-31 window; outside that window the current mapping
is unknown. UK membership is specifically extended through the withdrawal
boundary and the knowledge snapshot cutoff. Future membership is not inferred.
Country/region context is an offline diagnostic, never a booking/relocation
criterion. The full local-language-model briefing evaluation is Stage 13.
