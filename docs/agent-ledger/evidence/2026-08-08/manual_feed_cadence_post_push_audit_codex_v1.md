# Manual-feed cadence post-push divergence audit — Codex v1

**Audited HEAD:** `ec5c82ac22c616a2e6793de06c4f2bc249605f01`  
**Remote main:** same SHA  
**Exact-SHA CI:** run `31276256424`, completed / success (Python and Frontend)

## Code verdict

The pushed cadence engine/controller slice is **CLEAR** at the current HEAD. The first push,
`47ccf0de`, was CI-red on one marker-absent vocabulary assertion. The follow-up `ec5c82ac` changes
only that test and is a valid correction: `unknown` and `undetermined` are both non-claims while
`current`, `due` and `not_due` remain rejected, and marker absence still requires `age_days=None`.

Independent tracked-files-only reproduction from `git archive HEAD`:

- cadence/controller/last-good focused gate: 161 passed;
- Ruff over the four implementation/contract paths: clean;
- the four implementation pins in `47ccf0de` match the prior GREEN CLEAR exactly;
- the current test blob includes only the reviewed CI-only correction.

## Findings

1. **The governed input was not pushed.** `app/config/manual_feed_cadence_inputs.json` is absent from
   HEAD; only `feed_cadence.py`, its tests and the controller wiring exist. A live dry-run therefore
   reports PFF and PlayerProfiler as `manual_undetermined` with detail
   `no governed calendar/inventory artifact exists`. This is honest framework behavior, but it is
   not the requested operational input.
2. **The code commit cites evidence absent from HEAD.** Commit `47ccf0de` names
   `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_green_clear_codex_v1.md`, but that path
   exists only in the working tree. This is a documentation/durability defect, not a runtime defect.

## Route ruling for the next slice

Claude's binary choice — hand-declare the whole calendar or derive the whole calendar from B21 — is
incomplete. B21 schedules can govern game-derived facts (`season`, `week1_kickoff`, `final_game`,
`game_week_completions`) but cannot supply `league_year_open`, `combine_complete`, `draft_complete`
or provider-specific availability observations.

Use a **hybrid governed input**:

- capture B21 canonically and derive only the game/schedule facts it actually evidences;
- retain a versioned, provenance-bearing explicit registry for non-game NFL calendar anchors and
  provider availability facts;
- derive held/offer inventory from the existing PFF metadata ledger and PlayerProfiler stores/status
  evidence, with the composite PlayerProfiler season-key trap pinned in RED;
- fail closed when either evidence class is missing or malformed; never synthesize recurring dates.

This avoids annual hand-maintenance of the game schedule without pretending B21 contains combine,
draft, league-year or provider-publication facts it does not contain.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
