# QB-1 Study Execution — Framing v5 + round-4 disposition (Claude, 2026-08-14)

**Cycle:** TW14-QB1-1 · **Supersedes:** v4 (`c96ada66…`) on R4-B1 only; v4 stands otherwise.
**Folds:** Codex round-4 review (`qb1_execution_framing_review_codex_v4.md`, `08cce347…`) —
R4-B1 ACCEPTED. **This is semantic framing round 5 of 5** — the cap round; an open BLOCKER
after this round routes to the Judge by the counters.

## R4-B1 disposition — ACCEPT; the packet is now ONE exact operation

**The chosen operation: SEVEN LITERAL CURRENT PROVIDER CALLS.** The alternative (a separate
local-provenance-reuse review to reduce the ask to six) is REJECTED as a principal position,
with the reason stated: the reuse candidate is one ~2 MB file, and a dedicated review lane
for it costs more cockpit rounds than the fetch costs bytes — while a fresh `ff_playerids`
snapshot gives all seven datasets an identical, same-day provenance envelope. The existing
pinned 2026-05-16 crosswalk copy is NOT silently re-enveloped and NOT discarded: it remains
exactly what it already is — the pinned instrument of the H5 §9.3 static join, whose
`observed_at` disclosure semantics are unchanged. Two artifacts, two roles, no aliasing.

**The corrected operation table (fetch scope = what the loader actually transfers; parsing
and filtering are downstream, in-repo, not part of the authorization):**

| # | Dataset | The literal call fetches | Downstream use (not part of the ask) | Est. transfer |
|---|---|---|---|---|
| 1 | `weekly` | full weekly all-position player stats, seasons 2015–2025 | qualifying rows, labels, H1–H3 aggregates | ~10–30 MB |
| 2 | `season_summary` | official REG season summaries, 2015–2025 | the pinned as-is CPOE source (§A1) | ~1–5 MB |
| 3 | `players` | **full player-attributes frame** | **H4 `age_at_season_start` (birth_date) — a MODEL FEATURE source — plus the §10 draft cross-check** *(v4 said "cross-check only"; that was wrong and is corrected)* | ~5–10 MB |
| 4 | `rosters` | **full seasonal roster frames, 2015–2025** (REG filtering is downstream) | cohort roster-presence rule (§4) | ~20–50 MB |
| 5 | `ff_playerids` | the current full crosswalk | D1 identity dataset (fresh envelope; the 2026-05-16 pin stays the separate §9.3 join instrument) | ~2 MB |
| 6 | `draft_picks` | **the full drafted list** (`load_draft_picks()` fetches whole; the 1980–2025 coverage pin is a downstream filter, §10) | draft-capital join | ~1–2 MB |
| 7 | `pbp` | **full play-by-play, seasons 2015–2025 — THE DOMINANT CALL** | registered EPA / `team_proe` aggregates | **~2–6 GB** |

One build pass · nflreadpy · public/free/read-only · raw snapshots written under the frozen
root `app/data/backtest/qb_validation/raw/` BEFORE parsing (§11) · `backup_manifest.json`
entry lands in the same change set (W1, path exact).

## Decision packet for David (via Tower) — final form

**THE ASK (one yes/no):** authorize the seven literal fetches in the table above — the
dominant cost is play-by-play at ~2–6 GB; everything else totals under ~100 MB. Local
substrate is 0/7; the study cannot run without this.

**KNOW BEFORE SAYING YES (unchanged from v4, corrected wording):** the H5 market lane will
likely report `unsupported_power` by the registration's frozen identity rule (advisory
pre-measurement: three of four folds breach the pinned 2% gate; binding numbers computed at
execution). Contrasts 1–10 — including the H2 rushing question — are unaffected by that
gate; their own power floors are measured at execution and are not being promised.

## Standing

Registered values untouched · H2 UNDER TEST until execution + David's ruling · no fetch
before the gate word · no push · commits via gate paths · `decision_supported=False`
recursively.
