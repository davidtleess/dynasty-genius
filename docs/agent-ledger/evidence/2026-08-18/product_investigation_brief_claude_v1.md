From Claude (write lane) — INVESTIGATION COMMISSION from David: what else is broken, and what does tonight's finding change? [w#product-investigation]

David is commissioning this directly and has asked for you specifically because your context window is
near-full and mine is nearly spent. This is an INVESTIGATION, not an implementation task. Do not
write product code. Report findings with evidence.

## The finding that prompts it (verified tonight, all figures reproduced)

The model is not missing opinions on our players. A degraded feature store is destroying them.

1. `app/data/features_runtime/engine_b_features_runtime.csv` holds feature seasons 2018, 2019, 2020,
   2021, 2022, 2023, 2025. **2024 is absent entirely.** The 2025 rows are a PARTIAL season.
2. Garrett Wilson reads `games_t=7` there, against 17 in 2022 and 17 in 2023.
3. `games_t < ENGINE_B_MIN_GAMES_T` routes him off Engine B into the dead-window blend
   (`pvo_assembler.py:394-425`). The blend needs an Engine A prior; Engine A needs draft capital;
   `nfl_draft_round` is None for every active player. No Engine A, so
   `dynasty_value_score = None` (`:458-465`) — while `projection_2y` survives untouched.
4. Three independent counts agree on **115**: 2025 feature rows with `games_t < 8`; served rows with
   `dynasty_value_score` None AND a present `projection_2y`; Studio's 1-7 game band (115 of 583,
   stable across eleven days).
5. This is the downstream half of the health defect fixed today in `62768d0`: `feature_refresh`
   graded `fresh` while its own `stream_provenance` recorded participation `loaded_empty`
   (ValueError) and `pbp` / `player_stats` / `snap_counts` all on 2025 cache.

Related and already established — do NOT re-derive these:
- **R2 (identity):** Tank Dell `sleeper_id 9502` has `dg_player_id: None`; zero rows in the model
  capture at `capture_date 2026-08-18`; market capture carries him at `1204 | rank 76`.
- **R3:** the nflverse usage store (`ff_opportunity` 47,282 weekly rows 2018-2025; snap counts) is
  read by ZERO routes. Independently found three times now.
- **R4:** `depth_charts` holds 2018-2024 only, 812,074 rows. Feed is dead.
- **A7:** the Roster Audit gate suppresses actives by design (Studio verified deliberate), so Jeanty
  (DVS 75.3) and Rasheen Ali (20.7) render blank alongside Wilson and Allen, who have no score at
  all. Two causes, one blank column, nothing distinguishing them.

## David's six questions, verbatim

1. Are there any other gaps or major problems we may have missed?
2. Now that we know we were missing all this data, what else will we need to re-think?
3. What new ideas or features need to be built?
4. Do we need to re-run all our models and findings and studies now?
5. What else can you uncover?
6. Are there improvements that are now obvious?

Question 4 deserves particular rigour. QB-1 ran on this substrate. If the study's matrix was built
from a store missing 2024 and truncating 2025, say so plainly and say what it does and does not
invalidate — its registration pins the inputs, so this is checkable rather than arguable. Do not
soften the answer if it is bad, and do not overstate it if the study's own pins show it used a
different source.

## Scope and guardrails

- **Investigate, do not implement.** No product code, no feature rebuild, no surface change, no
  migrations. Read-only probes and measurement only.
- **Do not build a governance layer.** David has said this repeatedly today. No new registry, no new
  review protocol, no process artifacts. Findings with evidence, nothing more.
- **Cite everything.** `file:line`, a query, or a reproduced count. An uncited claim is worth nothing
  here — that is how the 115 sat unexplained for eleven days.
- **Not before Week 1**, so do not propose these as priorities: market-superiority work, the
  decision-grade gate, the frontend bundle-freshness item, the grounding build, and above all any
  large unvalidated model push landing in late August.
- **David's current order:** R1 (now a feature-store rebuild plus surfacing points per game, NOT
  modelling) and R2, then A7 and the descriptive cluster (the DVS clamp, unlabelled and unitless
  projections, the do-not-use copy over data we already hold).
- The controlling insight, in his words: *a points number degrades gracefully, a score does not.* He
  can judge "Jeanty, 11.8 points a game" against fifteen years of football; he can do nothing with
  "75.3". Prefer findings that get real numbers in front of him over findings that add machinery.

## What to return

Ranked findings, most severe first, each with its evidence and its cost to David. Name explicitly
anything you could NOT verify. If a question has no real answer yet, say that rather than filling it.

Durable record of the finding: `docs/agent-ledger/2026-08-18.md`, entry 21:0x ET, and
`docs/agent-ledger/evidence/2026-08-18/r1_unscored_root_cause_wire_claude_v1.md`.
Today's shipped fixes are on `origin/feature/outcome-loop-week1` (six commits, head `b599f1b`).

[w#product-investigation]
