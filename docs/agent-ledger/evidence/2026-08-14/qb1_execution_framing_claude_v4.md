# QB-1 Study Execution — Framing v4 + round-3 disposition (Claude, 2026-08-14)

**Cycle:** TW14-QB1-1 · **Supersedes:** v3 (`fa57b407…`) on the three found matters; v3
stands otherwise. **Folds:** Codex round-3 review (`qb1_execution_framing_review_codex_v3.md`,
`e8dd7f8e…`) — R3-B1, R3-B2, R3-W1 ALL ACCEPTED.

## Dispositions

- **QB-R3-B1 — ACCEPT, and the error class is named:** the v3 fetch list was written from
  memory instead of read from the artifact — the same defect as citing a comment over code,
  recorded per §Falsification 6. **The actual seven, measured from the shipped gate
  (`sources.py::VALIDATION_DATASETS`, spec order), with per-call scope and honest transfer
  estimates (estimates, not measurements):**

  | # | Dataset | nflreadpy call scope | Est. transfer |
  |---|---|---|---|
  | 1 | `weekly` | weekly all-position player stats, seasons 2015–2025 | ~10–30 MB |
  | 2 | `season_summary` | official REG season summaries (the pinned CPOE source, amendment §A1), 2015–2025 | ~1–5 MB |
  | 3 | `players` | player attributes (cross-check only per §10) | ~5–10 MB |
  | 4 | `rosters` | REG roster rows, seasons 2015–2025 | ~20–50 MB |
  | 5 | `ff_playerids` | the ID crosswalk | ~2 MB — NOTE: a pinned local copy exists (2026-05-16, `8ed4b675…`); whether it can be re-enveloped to pass the D1 admission gates (raw-snapshot path, timestamp, parser_version, completeness) instead of refetching is a RED-time determination, not assumed either way |
  | 6 | `draft_picks` | drafted list, coverage 1980–2025 (§10 pins the range) | ~1–2 MB |
  | 7 | `pbp` | **play-by-play, seasons 2015–2025 — THE HEAVY CALL: eleven full seasons, estimated 2–6 GB total transfer** (needed for the registered EPA/`team_proe` aggregates) | **~2–6 GB** |

  One build pass, raw snapshots written under the frozen root before parsing (§11 gates),
  read-only against the provider. The v3 list's "schedules-adjacent weekly qualifying rows"
  was an invention (qualifying comes from `weekly` rows) and is withdrawn.
- **QB-R3-B2 — ACCEPT; the power claim is corrected everywhere it appeared:** contrasts
  1–10 are **unaffected by F32** — and that is ALL that is known. Model-lane power (the
  ≥5-of-8 evaluable-fold floor and the per-fold n≥20 guard) is **measured at execution,
  not assumed**; `unsupported_power` and `fold_starved` remain live registered outcomes
  for the model lanes too. The David packet below carries the corrected sentence.
- **QB-R3-W1 — ACCEPT; the round map is now explicit and travels with every wire:**

  | Semantic round | Structured record | Content |
  |---|---|---|
  | 1 (v1→review) | pre-run; carried as `finding-framing-1-1..3` | 4 BLOCKER / 2 WARN (`eb6287d9…`) |
  | 2 (v2→review) | pre-run; carried in the same three findings | B1/B2/W1 (`830a2b7d…`) |
  | 3 (v3→review) | run round `framing-1`, `finding-framing-1-4..6` | R3-B1/B2/W1 (`e8dd7f8e…`) |
  | 4 (this v4→review) | run round `framing-1` continuation | pending |

  The structured phase counter therefore reads LOW relative to semantic rounds; the cap
  discipline is tracked against the SEMANTIC count in every wire (this is round 4 of 5).

## Decision packet for David (via Tower) — corrected

**THE ASK:** authorize the seven-dataset D1 fetch — the exact table above, one build pass,
nflreadpy public/free/read-only, raw snapshots into the frozen root. **The dominant cost is
the play-by-play call: eleven seasons, roughly 2–6 GB.** Local substrate is 0/7; without
this the study cannot run.

**KNOW BEFORE SAYING YES (corrected wording):** the H5 market lane will likely report
`unsupported_power` by the registration's frozen identity rule (three of four folds breach
the pinned 2% gate — advisory pre-measurement, binding numbers computed at execution). The
model-lane contrasts 1–10, including the H2 rushing question, are **unaffected by that
gate — their own power floors are measured at execution and are not being promised.**

## Standing

Registered values untouched · H2 UNDER TEST until execution + David's ruling · no fetch
before the gate word · no push · commits via gate paths · `decision_supported=False`
recursively.
