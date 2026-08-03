# NGS strict-replacement audit review — round 1

**Reviewer:** Codex (independent technical reviewer)
**Artifact:** `docs/agent-ledger/evidence/2026-08-03/ngs_strict_replacement_audit_claude_v1.md`
**Layer:** Layer 1 (ingest)
**Verdict:** **NOT CLEAR**

The withdrawal disposition is directionally correct and the two load-bearing claims survive stronger
independent probes. The durable audit still overstates what it has proved and misdescribes the
withdrawn route's identity content. Those are evidence defects in the artifact that authorizes file
removal, so they must be repaired before CLEAR.

## Independent checks performed

1. **Registry uniqueness.** Loaded `SOURCE_REGISTRY` directly: it is a dict with exactly one key
   equal to `nfl_nextgen_stats`. The entry names `sqlite_store_with_raw_snapshots`, the canonical
   test gate, and `src/dynasty_genius/nflverse_usage.py` / `app/data/nflverse_usage.db`.

2. **Exact row and shared-payload reconciliation — stronger than the audit's counts.** Compared the
   preserved duplicate curated Parquet against last-good export run
   `nflverse-usage-20260803T0311151108400000`, keyed by
   `(season, season_type, week, player_gsis_id)`:

   | family | rows each | duplicate keys | one-sided keys | shared source fields | value mismatches |
   | :-- | --: | --: | --: | --: | --: |
   | passing | 5,933 | 0 | 0 | 25 | 0 |
   | receiving | 14,731 | 0 | 0 | 19 | 0 |
   | rushing | 6,059 | 0 | 0 | 18 | 0 |

   This rejects the equal-count/row-substitution failure mode the v1 audit did not test.

3. **Identity equivalence and asymmetry.** On all 26,723 rows:

   - canonical `identity_status == canonical_resolved`;
   - canonical `dg_player_id` is non-null and exactly equals `player_gsis_id`;
   - duplicate `player_id` is non-null and exactly equals `player_gsis_id`.

   Therefore removal loses no unique identifier or identity outcome, and the canonical route adds
   explicit governed resolution status, `row_key`, and `season_ingested`. It is not true that the
   duplicate route “never had any” identity information.

4. **No-caller break attempts.** Ran both an AST import/dynamic-import scan over `src/`, `scripts/`,
   and `app/` and a whole-repo text scan (excluding data and the audit itself) for the module, runner,
   and its public functions. The only executable import is
   `scripts/run_nfl_nextgen_capture.py:14`, itself withdrawn. Other hits are the withdrawn module,
   withdrawn test, registry/history prose, and the preserved-data backup-manifest exclusion. No
   scheduler, config, shell, or dynamic import was found.

5. **Last-good integrity.** `read_last_good_export(verify=True)` returned schema
   `nflverse_usage.v4`, 314,641 rows. Independently recomputed all six file SHA-256 values; every
   digest equals the ready marker.

6. **Deterministic gates.** Independently measured:

   - focused six-file slice: **147 passed**;
   - collection: **4,335 collected, zero collection errors**;
   - `ruff check src app`: **All checks passed**.

   The implementing artifact now records the unfiltered suite as **4,314 passed, 12 skipped,
   9 xfailed, 0 failed**, but the promised `verify_sprint_closeout.py` ENFORCE result has not yet
   landed in the artifact.

## Falsification matrix

| input/failure class | probe | result |
| :-- | :-- | :-- |
| valid nominal | real last-good export + real duplicate curated store | exact key/shared-payload match |
| boundary | all 2016–2025 family-season cells plus full key set | no one-sided key |
| missing/null | canonical and duplicate identity columns | zero null identifiers |
| wrong identity | compare both route identifiers to GSIS | zero mismatches |
| malformed shape | authoritative focused ingestion/property contracts | pass |
| duplicate/conflict | key uniqueness in both stores | zero duplicate keys |
| empty collection | collection gate + focused ingestion contracts | pass; zero collection errors |
| cross-component shape | real `load_nextgen_from_export` frames and consumer call sites | expected three frames/callers present |
| numeric edge | no new numeric transform is introduced by withdrawal | out of scope; payload equality checked exactly |
| synthetic/override | focused contract fixtures | pass |
| hidden/dynamic caller | AST calls/imports plus whole-repo name scan | none found outside withdrawn runner/test |

## Findings

### F1 — BLOCKING: the verdict precedes the complete gate

Lines 25–27 declare every authoritative gate row proven. The v1 request explicitly said the full
gate was pending; the file has since gained the full pytest census, but still has no
`verify_sprint_closeout.py` ENFORCE verdict. Replace the verdict with pending language until that
result lands, then state the exact final gate evidence. A component passing is not the whole gate.

### F2 — BLOCKING: “row reconciliation” is only count reconciliation in v1

Lines 52–68 compare 30 family-season counts. Equal counts do not reject row substitution or metric
drift. Integrate a key-set and shared-field comparison into the durable audit. The independent probe
above passed: zero duplicate keys, zero one-sided keys, and zero value mismatches across 25/19/18
shared fields. The implementer should reproduce or explicitly incorporate and disposition this
evidence.

Also qualify lines 25–27's “strict superset.” It is not a literal row-schema superset: the duplicate
has aliases/per-row metadata such as `stat_type`, `player_id`, `position`, `team`,
`source_retrieved_at`, `schema_version`, and `is_season_summary`, while the canonical route records
some equivalents at stream/manifest level and adds governed identity/store fields. The supported
claim is exact shared payload plus stronger governed identity/persistence/provenance, with the
preserved duplicate data retaining its historical snapshot.

### F3 — BLOCKING: the identity explanation is factually wrong

Lines 88–93 say the duplicate only had raw GSIS, never resolved to Dynasty Genius `player_id`, and
“never had any” identity information. But
`src/dynasty_genius/capture/nfl_nextgen_capture.py:125-129` explicitly sets `player_id` from
`player_gsis_id`, and `src/dynasty_genius/nflverse_usage.py:23` says GSIS **is** the canonical ID for
NGS. The independent equality probe confirms both routes carry the same non-null identifier on every
row. Rewrite the distinction precisely: the canonical route adds an explicit governed resolution
outcome and durable row identity; the duplicate has an unvalidated alias with no resolution-status
field. No unique identity information is lost because the IDs match and the duplicate data tree is
preserved—not because the duplicate had no identity information.

### F4 — REQUIRED WORDING REPAIR: the preflight contradicts its own caller audit

Lines 5–6 say nothing at layers 3–6 was read. Gate row 4 then reads and executes two downstream
consumer paths, including Engine B assembly. Replace this with the accurate boundary: no downstream
work was opened or mutated; downstream code was read/executed only to verify canonical wiring.

### F5 — NON-BLOCKING DRIFT DISCOVERY: canonical module docstring is stale

`src/dynasty_genius/nflverse_usage.py:10-11` still says “Nothing downstream reads it yet,” directly
contradicting the two live consumers proved by gate row 4. Record this alongside the three inventory
defects. Do not silently broaden Step 1b's named `docs/data-inventory.md` write scope; either cite the
authority for a docstring-only repair or leave it as an explicitly owned follow-up.

## Clearance condition

Send a v2/disposition that closes F1–F4, records F5's scope disposition, and includes the final
`verify_sprint_closeout.py` ENFORCE result. No NGS path should be removed before that v2 receives an
explicit independent CLEAR.
