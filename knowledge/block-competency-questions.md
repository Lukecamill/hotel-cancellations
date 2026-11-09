# E4 block competency questions

| Question | Representation / check |
|---|---|
| Which booking rows share the notebook's 16-field block key? | Stable key-only hash; partition must equal the original policy's block grouping |
| What size/status was reconstructed at the seven-day decision date? | BlockSnapshot with asOf, arrival, liveSize, sourceMatchedSize, OnBooks |
| Which matches warrant desk priority? | Prespecified >=5 live units; smaller matches still require party verification before relocation |
| What was the later final-status release outcome? | Separate BlockOutcome, released/remaining counts and status; no outcome fields in BlockSnapshot |
| When could the final outcome have become available? | availableNotBefore = max(arrival+1 day, latest source status date); an inferred lower bound, not an observed event-write time |
| How many simulated walks/costs fall on inferred multi-row matches? | Fixed Stage 11 allocation, separate incidence by rule and hotel; no causal claim |
| Would individual allocation split a suspected party? | Post-hoc partial relocation among surviving rows; not proof of a real party |
| What does the correlation assumption change when release means are fixed? | Independent vs perfect block-correlation distributions, supplied cost rule, no fitting/selection on holdout |

Source dates are date-only and serialized as UTC midnight by convention. They do
not establish exact PMS event times. Keys include arrival/hotel, so these are
arrival-cohort matches, not persistent verified party IDs spanning multiple stays.
Country and outcome fields are excluded from the block key. Matching keys can
merge unrelated bookings or split actual parties. All real inferred blocks are
reconstructed in ignored CSV; multi-row matches form an ignored generated RDF
overlay and combined knowledge snapshot. Only synthetic block examples are
committed for deterministic CI validation. Do not publish real key fields or
mislabel an inferred hash as a hotel-issued group identifier.
