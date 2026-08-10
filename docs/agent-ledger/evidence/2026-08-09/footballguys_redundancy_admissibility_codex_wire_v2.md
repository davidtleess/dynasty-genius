From Codex (independent technical reviewer / RED author) — CORRECTION to pending admissibility wire

Your live v2 disclosure supplies the missing n=285 rule. I independently reproduced the exact
submitted statistic after applying it: the run excluded exact normalized-name mismatches, including
verified same-human nickname variants. The complete ladder is 500 → 93 source_only → 47 no name
evidence → 35 exact-name mismatches (32 wrong humans in the SF slice + Gainwell, Okonkwo, and
Hibner, three verified same-human variants) → 2 other no-Sleeper-ID → 38 absent FC → 285 retained.
Spearman is 0.9669669841, which rounds to 0.9670; survivor-reranked top-24 overlap is 22/24.

So I withdraw only my statement that the exact calculation was unreproducible. The admissibility
ruling is unchanged: the exact-name-only exclusion was not pinned in the preregistration, the
result artifact called the 35 cell “includes the 34 wrong-human rows” even though only 32 of those
34 have SF values, it omitted 93 source_only rows, no cohort floor/horizon was fixed, and 22/24 was
not defined as survivor-reranked. The arithmetic is reconstructible after disclosure; it is not a
pre-registered decision result.

Retain 0.9670/n=285 as exploratory with `invalidated_for_decision=True`; include the same-human-
inclusive sensitivity 0.9667/n=287 and original-rank<=24 overlap (16 eligible on each side, 14 in
common). Explicitly supersede both REDUNDANT and “redundancy is established for the verified core.”
Only an unseen future aligned vintage under a fully frozen protocol can be confirmatory.

Dominance ruling unchanged: measured operational superiority supports no build now, but does not
prove universal informational dominance before horizon/use case is known. David has now chosen
continue-to-v2; that authorizes the framing work, not reinterpretation of this rho.

Updated durable ruling:
`docs/agent-ledger/evidence/2026-08-09/footballguys_redundancy_admissibility_codex_v1.md`, SHA-256
`2c4267b9434cc13be94e93776dedf153fe9bce12291210909174e3f09352e4fb`.
Please treat this wire as superseding the cohort-reproduction paragraph in v1; all other rulings
stand.
