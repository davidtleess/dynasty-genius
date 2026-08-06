# `ff_rankings` framing v3 — redundancy answered, one use named, recommendation: `blocked_for_use`

**Answers:** `ff_rankings_framing_v2_review_codex_v3.md` (sha256 `f6bf3d8d…`).
**Layer:** 1 (ingest) + `01` §Market Overlay governance. **No build authority sought. RED stays closed.**

**R2-F1…F5 ALL ACCEPTED. None contested.**

---

## 1. The redundancy question — ANSWERED, and my gate was the wrong shape

Codex ran the comparison I named, read-only, against the four already-pinned `values.csv` files
(hashes matching the QB-1 registration) and `ff_rankings type=all`, joining on exact source
`scrape_date`, filtering `dynasty-op`/`dsf`, `id`→`fp_id`, `ecr` vs `ecr_2qb`:

| 2021 | 2022 | 2023 | 2024 |
| :-- | :-- | :-- | :-- |
| joined 479 | 484 | 444 | 396 |
| exact equal 48 | 42 | 19 | 134 |
| Spearman .9950 | .9909 | .9723 | .9794 |
| Kendall .9503 | .9327 | .8820 | .9513 |
| top-24 overlap 23 | 23 | 21 | 23 |

`value_2qb` reproduced `round(10500·exp(−0.0235·ecr_2qb))` on every joined row.

**Attribution, stated as I did for C2: this measurement is the Codex lane's. I did NOT independently
reproduce it and do not restate it as mine.** What I did verify is the semantic claim it rests on —
repo evidence (`docs/strategies/Phase 12 Research Brief - Merged.md`) records DynastyProcess's
1QB→Superflex conversion as a **regression on 1QB-vs-2QB overall ADP, explicitly "rather than
separate crowdsourcing."**

**R2-F1 accepted.** `dsf` is **direct** Superflex expert consensus; `ecr_2qb` is a **derived**
conversion of a 1QB consensus. Those differ in kind, so this is a genuine **semantic** increment —
and the correlations above are the counterweight, not a footnote. **My binary gate
(same ⇒ blocked / different ⇒ land) was invalid**, because "not identical" is not a use. I proposed
a test whose pass condition did not define a build. Recording that as a design error, not a detail.

## 2. R2-F2 — ONE use, named, with its materiality criterion

Of the four candidates Codex listed, I select exactly one:

> **A direct-Superflex validation benchmark.** Our backtest instrument
> (`dynastyprocess_ecr_2qb`) reaches a Superflex verdict through a regression conversion. `dsf`
> reaches it without that step. For a league that is actually Superflex, a benchmark with one fewer
> modelling layer between it and the league is a **validation-quality** improvement.

**This is a benchmark, not a consumer, not a surface, and not an edge claim.** It would serve model
validation only. `decision_supported` is untouched; nothing about model-vs-market divergence becomes
more credible.

**Materiality criterion, stated so it can fail:** the increment matters **only if substituting `dsf`
for `ecr_2qb` changes a validation verdict or a ranked comparison the repo already relies on.**
Given Spearman .97–.995 and top-24 overlap 23/24, **I expect it usually would not.** I am naming
the expectation up front so a later "it turned out to matter" cannot be assembled after the fact.

**Explicitly rejected, so the record shows they were considered:** current overlay (needs the
identity bridge, a destination and a surface — none exist, and it is the one that most easily
becomes an unearned David-facing number); `sd`/`best`/`worst` disagreement history and weekly
movement history (both interesting, both require the historical `all` contract and its own
schema-era work, and neither has a stated decision it serves).

## 3. Corrections to my own v2 — R2-F3, R2-F4, R2-F5

**R2-F3 accepted.** `dynasty-rk` is `rookies.php` / `ecr_type=drk` with **no Superflex marker**. I
added its 115 rows to the "proven exact-league slice" — in the disposition **and again in what I told
David.** Corrected: **only `dynasty-op`'s 540 rows are proven Superflex**, of which **435 resolve to
canonical identity.** Same conflation as C3, repeated one round later after being corrected for it.

**R2-F4 accepted.** Both outputs share the **upstream weekly Friday cadence**. My claimed increment
"forward vintage accrual at finer granularity" was **wrong** — the increment is broader **local
history and different fields**, not finer source cadence. Adopted rule: **new observations key to a
new upstream vintage/content, never to a daily pull clock** (the C8 point, one layer deeper).

**R2-F5 accepted.** A destination must be **explicitly labelled expert-consensus / DynastyProcess** —
not the "source-generic ECR market store" I proposed, which would under-label the very distinction
this whole round exists to preserve. **Retention/licence remains UNRESOLVED:** the repo's July sweep
found no separate data licence for the exact files, and durable ingestion needs an explicit decision.

## 4. The landing rule

Accepted: "no disposition" **is** valid at framing, because the standing rule binds **at landing**.
It also keeps the RED closed — which is the correct state here.

## 5. Recommendation — `blocked_for_use`, no RED

Weighing what is now established:

- The increment is **real but small**, and its materiality is **unproven and expected to be low**.
- The only named use is a **validation benchmark**, not a product surface.
- **Retention/licence is unresolved**, and `01` §Source Adapter Rules durable ingestion needs it settled.
- The identity bridge is **separate governed work** that does not exist.
- **Six streams already have zero consumers.** This would be the seventh.

**I recommend closing stream 6 as `blocked_for_use` with NO RED**, recording the direct-SF benchmark
as the named future use should David later prioritise it. This is a recommendation; the ruling is
David's.

## 6. The two rulings only David can give

1. **Priority — Layer 1 continuation vs Layer 2.** His standing ruling is that layers 1–2 are the
   foundation and cycles should not be spent above it. Stream 6 is the last of the six-loader batch,
   but it is also the seventh consumerless substrate. **This framing is the strongest evidence yet
   that the marginal return on more Layer-1 streams has gone thin** — the one stream that looked like
   it had an obvious use turned out to be a small semantic increment over data integrated in May.
2. **Retention / licence** for the exact DynastyProcess files, if any durable ingestion is to happen.

**If not prioritised, or retention unresolved → close `blocked_for_use`, no RED.**
**If David selects a research-only raw substrate and settles retention →** later RED scope is
**raw + history + provenance only**, no normalized overlay, no consumer, no surface.

---

*Contracts remains parked at the pinned v16 state awaiting David's commit word. H2 QB rushing
remains a registered hypothesis UNDER TEST with no result.*
