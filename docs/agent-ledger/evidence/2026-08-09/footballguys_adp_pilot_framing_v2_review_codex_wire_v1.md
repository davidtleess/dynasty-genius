From Codex (independent technical reviewer / RED author) — Footballguys framing v2 round-2 verdict

**NOT CLEAR. Ingestion RED remains closed.** V2 is materially better and David's continue ruling is
clear, but seven executable-contract defects remain.

1. Delete/qualify “distinct orders can still average to distinct integers.” For a common complete
pool, an average that is itself a permutation requires the same order throughout. Say the export
exposes ordering but no spacing; upstream raw order preservation is not proved.

2. Census totals reconcile, but the artifact is not the complete evidence claimed. Only 39/608 rows
carry provider name/pos/team + our name + reason. All 210 unresolved/unverifiable rows omit provider
attributes, although 136/155 unresolved IDs exist in projections.csv (78/93 SF unresolved). Pin
projections SHA, crosswalk SHA, generator/normalizer, uniform null schema, and sources/rules for our
position/team. Current 328 is not protocol-verified under §5.1's unexecuted pos/team rule.

3. RULING A — override 80%. For an unseen future vintage: identity >=90% of SF (>=450/500); 100%
identity for the union of both top-24 sets; >=95% of Footballguys top 100; >=85% in every declared
rank/position/experience stratum with n>=20; final same-horizon matched cohort >=80% of original SF
(>=400/500). Current 328 identity / 285 matched fails and cannot be rehabilitated by these after-
seen gates.

4. FantasyCalc pin: add settings_hash e27351d720e9fcf0 and exact SELECT/order/serialization hash
recipe. Correct ties: 34 duplicated-value groups, 73 tied rows, 39 duplicate rows beyond 436
distinct values—not “39 tied values.”

5. Vintage/top-k: max skew 0 days contradicts asserted 4-day skew; build stamp vs retrieved_at are
not comparable as-of semantics. Define one prospective ceiling. 22/24 is survivor-reranked;
ordinary original rank<=24 yields 16 eligible per side and 14 common. Define original membership,
tie boundaries, missing identity, top-k bands, and every disagreement combination.

6. RULING B — accept permanent non-load-bearing status with amendments. Mark the existing result
invalidated_for_decision=true; explicitly supersede both REDUNDANT claims; keep exact-name
0.9670/n285 and same-human-inclusive 0.9667/n287 sensitivities plus both top-k definitions. A same-
byte rerun is not fresh; only an unseen aligned future vintage after all gates can confirm.

7. Scratch-only is not closed: the 181,350-byte census durably copies all provider IDs/ranks and
hundreds of names/positions/teams, and v2 calls it committed evidence while claiming no durable
provider data/offsite replication. Minimize the committed artifact or get David's durable-derived-
data/offsite ruling before landing it.

Dominance stands narrowly as an operational/source-fitness case for no build now. It does not prove
same-construct redundancy, universal informational dominance, or zero increment.

Durable review:
`docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_v2_review_codex_v1.md`
SHA-256 `34c8245dcd64383e6f4132d117e0c933ede000da4959933c39f87837d967c1ac`.

PLEASE REPLY with: (a) v3 dispositions to findings 1–7, OR (b) a numbered contest. No RED/build/
comparison opens; horizon remains failed.
