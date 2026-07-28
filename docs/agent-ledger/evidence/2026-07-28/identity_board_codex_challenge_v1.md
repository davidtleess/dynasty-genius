# TW28-IDENTITY-1 — Codex adversarial challenge of identity board v1

**Reviewer:** Codex (independent technical lane)  
**Artifact reviewed:** `docs/agent-ledger/evidence/2026-07-28/identity_board_claude_v1.md`  
**Reviewed artifact SHA-256:** `9c873fded2632a3207eac629d6dccfa7a0d636fdf45efaa4e9abd465e36df18b`  
**Disposition:** **NOT CLEAR — 8 corrections required.** No repair was attempted.

All player and league claims below are local-artifact state. During the review, the scheduled
09:30 PVO refresh replaced the 2026-07-27 runtime artifact with a 2026-07-28 artifact. The counts
at issue remained identical: 12,203 total; 581 resolved DG ids; 11,621 Sleeper-only; 1 unresolved;
501 GSIS-shaped DG ids; 80 slug-shaped DG ids.

## Enumerated challenge

1. **Measurement 1 — 12,203 / 581 / 11,621 / 1 and 501 / 80: REPRODUCED.**
   - Probe: direct `jq` grouping of
     `app/data/valuation_runtime/universe_pvo_runtime.json`.
   - Result: exact match. Crosswalk probe also reproduced 7,952 entries, 6,117 non-null unique
     Sleeper ids, zero duplicate GSIS ids, and zero duplicate non-null Sleeper ids.

2. **Measurement 2 — “no bridge between the two vocabularies in production”: OVERSTATED.**
   - There is no direct slug↔GSIS mapping and `dg_player_id` is not canonical; that part stands.
   - But the shipped production path bridges both Engine A and Engine B PVOs through Sleeper id:
     `src/dynasty_genius/universe_pvo_batch.py:64-70,135` indexes both engine lists by
     `sleeper_id`; because active PVOs follow prospect PVOs, an active row replaces the prospect
     row for the same Sleeper player.
   - The longitudinal production key also already crosses the engine transition:
     `src/dynasty_genius/capture/model_forward_capture_store.py:81-103` chooses
     `sleeper:<id>` before `dg:<id>`.
   - Required correction: distinguish “no canonical DG-id bridge” from “no production continuity
     bridge.” The latter is false.

3. **Measurement 3 — Kallerup/Williams and exhaustiveness: REPRODUCED.**
   - Probe: resolved the same runtime feature source as production, scored the inference
     partition read-only, and compared every prediction id to the crosswalk.
   - Result: 503 inference rows, 503 unique predictions, zero prediction ids missing from the
     crosswalk, and exactly two crosswalk entries with null Sleeper ids:
     `00-0040058` Nick Kallerup and `00-0040534` Ke'Shawn Williams.
   - Both live PVO rows reproduce `dg_player_id=null`, `dvs_engine=null`, `caveats=null`.
   - Board line 114 is internally wrong: not all 9,480 PRE_MODEL rows lack Engine B features.
     These two have them. The defensible count is **9,478 of 9,480**.

4. **Measurement 4 — missing crosswalk fail-open: CORE CLAIM REPRODUCED; blast radius
   OVERSTATED.**
   - Probe: called `_load_ff_playerids` with a nonexistent path, then monkeypatched the loader
     in memory and ran the read-only assembly functions (no artifact write).
   - Result: `_load_ff_playerids` returned `({}, {})`; active Engine B PVOs fell from 501 to 0;
     all Phase 17.2 exit booleans still passed.
   - But 80 Engine A PVOs survived with non-null DVS. Board lines 57-58 and 124-126 therefore
     cannot say “every model value” / “zero model values.” The exact claim is **zero Engine B
     rows; 80 Engine A rows remain**.
   - “No error anywhere” is also too broad. The scheduled runner would compute an Engine B
     coverage delta far beyond its `>=10` seed-staleness review threshold
     (`scripts/run_pvo_refresh.py:156-176`), and Daily What-Changed is wired to surface that
     block. That is still not fail-closed—the bad candidate publishes—but it is an observable
     review signal.

5. **Measurement 5 — 12,201 / 12,202 / 12,203 vintage explanation: REPRODUCED; withdrawal
   was correct.**
   - Probe: exact Sleeper-id set differences across the seed, divergence, and runtime PVO;
     duplicate counts computed independently.
   - Result: seed→divergence adds only `14061` Jeremiah Franklin; divergence→runtime adds only
     `14062` Tyler Moore; zero removals and zero duplicates. The row-count spread is vintage,
     not identity corruption.

6. **Measurement 6 — fuzzy matcher callers: CORE CLAIM REPRODUCED; supporting sentence false.**
   - Probe: symbol/caller search for `IdentityResolver`, `resolve_by_name`,
     `compute_name_confidence`, and imports from `src.dynasty_genius.identity` across
     `src/`, `app/`, and `scripts/`.
   - Result: zero production callers of the fuzzy matcher.
   - But production does not import “only `generate_dg_id`.” For example,
     `scripts/build_nflreadpy_qb_identity_bridge.py:16,87,119` imports and calls
     `normalize_player_name`, and `scripts/backfill_te_canonical_ids.py:25` imports
     `assign_collision_suffixes`. Narrow the sentence to the fuzzy symbols themselves.

7. **§2 missed a present pseudo-player defect.**
   - Sleeper id `"0"` is an empty-starter sentinel, not a human player. The snapshot builder
     admits it because string `"0"` is truthy in the roster-context comprehensions
     (`src/dynasty_genius/sleeper_universe.py:90-107`).
   - Local artifact state marks it rostered, in starters, `UNRESOLVED_IDENTITY`, and carries it
     into the divergence artifact as its own signal. `GET /api/players/0` returns HTTP 200.
   - This contradicts “the whole visible cost today is two players.” It is a separate ingestion
     shape/identity-hygiene defect and should be named, while making clear it should be filtered
     as a sentinel rather than sent to human identity triage.

8. **§2 understates what David sees for the two real players.**
   - Read-only TestClient probes of `GET /api/players/12971` and `/13151` both returned HTTP 200,
     `model_status="experimental"`, no model, no caveats, and:
     `"No active model score for this player category."`
   - That is not merely a blank cell; it positively misattributes an identity-join failure to
     player category (`app/api/routes/players.py:285-310`). I-1 must cover the player-detail
     degradation contract, not only raw PVO caveats.

9. **I-1 is not one cheap/no-repair unit.**
   - Missing-file abort is cheap and deterministic.
   - A skipped-GSIS report keyed by GSIS/name is also straightforward.
   - Attaching a caveat to the matching Sleeper row is not currently possible by identifier:
     the broken crosswalk has no Sleeper id and the materialized universe snapshot discards the
     Sleeper payload's GSIS id (`src/dynasty_genius/sleeper_universe.py:235-250`).
   - Doing that safely needs deterministic snapshot enrichment/bridge input. Name matching would
     recreate the prohibited failure mode. Split I-1 into fail-closed publication, orphan
     reporting, and deterministic row attachment.

10. **The I-4 “copy-pasted normalizers” / cheap consolidation claim is false.**
    - The functions have different contracts:
      `build_college_features` strips accents/suffixes and keeps spaces;
      `build_w2b_cfbd` strips every non-alpha character and spaces but keeps suffix letters;
      the root identity normalizer adds first-name aliases and underscore tokenization.
    - Example: `A.J. Brown Jr.` becomes `aj brown`, `ajbrownjr`, and `aj_brown`,
      respectively; `Josh Allen` becomes `josh allen`, `joshallen`, and `joshua_allen`.
    - Centralization can change joins and cache keys. It needs an explicit semantic contract and
      regression fixtures, and should follow—not precede—the canonical identity decision.

11. **§2's claimed compounding blocker describes the wrong join.**
    - The shipped model-forward capture is already Sleeper-keyed across Engine A/B
      (`model_forward_capture_store.py:81-103`).
    - The realized-outcome scorer resolves `prediction.sleeper_id` at capture date to GSIS
      (`src/dynasty_genius/outcome_loop/realized_outcome_scorer.py:217-228`).
    - The empty default identity-snapshot loader is real
      (`scripts/run_realized_outcome_scoring.py:398-401`), but the missing input is a
      point-in-time Sleeper→GSIS mapping. It is not proof that slug-vs-GSIS blocks model-history
      continuity. Reframe I-6 independently from I-5.

12. **Manifest-law wrinkle: honest, but unresolved—not an exemption.**
    - `nflreadpy.load_ff_playerids()` pulls mutable GitHub `master`:
      `https://github.com/dynastyprocess/data/raw/master/files/db_playerids.csv`.
    - A current repull restores operability but not necessarily the exact 2026-05-16 bytes.
      The local snapshot records a pull timestamp, not an upstream commit SHA.
    - “Arguably outside the law's letter” is not a dodge if presented as an ambiguity for David.
      Stronger wording: public-source regenerability may put it outside the narrow disaster-loss
      mandate, while lack of an immutable upstream pin makes the exact operational input
      reproducibility-critical. Do not state a settled exemption.

## Leverage disposition

- **Keep** fail-closed publication ahead of backup and ahead of canonical-key migration.
- **Split** I-1 as described above; the deterministic row-attachment portion is bridge work.
- **Add** the `"0"` sentinel exclusion/validation near the immediate containment work.
- **Keep** exact-vintage protection near the top; backup vs committed upstream-SHA pin is a
  David choice.
- **Move** I-4 behind the canonical semantic decision. It is not cleanup.
- **Do not use** I-3 as evidence that present production is unsafe; it is preventive hygiene with
  zero callers, lower leverage than the current defects.

## Required v2 corrections before CLEAR

1. Replace zero/every-model wording with zero Engine B / 80 Engine A.
2. Correct 9,480 to 9,478 when claiming PRE_MODEL rows without Engine B features.
3. Separate absent canonical DG bridge from the shipped Sleeper-id continuity bridge.
4. Add the `"0"` sentinel defect.
5. Add the player-detail endpoint's misleading category message.
6. Split I-1 so deterministic row attachment is not presented as already-cheap.
7. Reclassify I-4 as semantic migration, not normalizer deduplication.
8. Reframe the realized-outcome input gap as Sleeper→GSIS PIT input, independent of DG vocabulary.
