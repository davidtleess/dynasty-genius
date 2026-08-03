# NGS strict-replacement audit — Step 1, read-only pass

**Author:** Claude Code (implementing lane) · **Reviewer:** Codex (independent, ACK received)
**Date:** 2026-08-03 · **Layer served:** Layer 1 (ingest)
**Layers 1–2 dependency check:** not applicable as a downstream question — this work *is* Layer 1.
The check performed is the audit itself; nothing at layers 3–6 was read or touched.

**Session state at preflight (measured, not recalled):**

```
HEAD == origin/main == 85bf5b5f6b70cdd58a88bdfba35eaf89eb414203
tracked tree clean; untracked == exactly the three duplicate NGS paths
```

Handoff landed; this is a genuinely fresh bootstrap, so the COLD-START ROUTER opens on Step 1.

**Write scope of this pass: NOTHING removed, NOTHING mutated.** The three NGS files are still on
disk untracked, and the gitignored duplicate DATA tree is untouched. This artifact is the read-only
proof that must clear before withdrawal is authorized to execute.

---

## Verdict

**Strict replacement is PROVEN on every row of the authoritative Step-1 gate.** The canonical route
is not merely equivalent to the withdrawn route — it is a **strict superset**, and the withdrawn
route has **no production caller other than itself**.

The one thing this audit does NOT establish, stated plainly because the board's whole discipline is
about not overclaiming: it proves **replacement**, not **value**. NGS remains `context_signal` in
the registry, and nothing here authorizes a model or feature use of it.

---

## Gate row 1 — one registry adapter / one store

`src/dynasty_genius/sources/source_registry.py` contains **exactly one** `nfl_nextgen_stats` entry
(line 363). It names the canonical adapter and store:

- `cache_policy="sqlite_store_with_raw_snapshots"`
- `test_gate="tests/contract/test_nflverse_usage_ingestion_red.py"`
- notes: `CANONICAL ADAPTER: src/dynasty_genius/nflverse_usage.py, store app/data/nflverse_usage.db`

The registry note at line 381 contains the literal string `test_nfl_nextgen_capture.py` **inside
prose** recording why the second route was withheld. This is the board's KNOWN BENIGN case: a
string in a comment is not a caller. Verified by reading the surrounding lines, not by grep alone.

`tests/test_source_registry.py` — the direct registry contract — is included in the focused slice
below precisely because the registry test cannot, by itself, detect an *unregistered* duplicate.
The import/caller checks below cover that half.

## Gate row 2 — exact family / season / row reconciliation

Canonical `app/data/nflverse_usage.db` vs the withdrawn route's curated Parquet, per family **and
per season** — all 30 cells:

| family | seasons | canonical | duplicate | result |
| :-- | :-- | --: | --: | :-- |
| passing | 2016–2025 | 5,933 | 5,933 | exact, every season |
| receiving | 2016–2025 | 14,731 | 14,731 | exact, every season |
| rushing | 2016–2025 | 6,059 | 6,059 | exact, every season |

Per-season detail (canonical == duplicate on each): passing 573/575/578/576/581/608/603/620/614/605
· receiving 1601/1422/1419/1418/1520/1575/1466/1473/1435/1402 · rushing
579/595/594/588/596/618/617/623/601/648.

**PER-FAMILY/SEASON RECONCILIATION: EXACT MATCH.** Aggregate-only agreement would have been the
weaker claim; this is the per-cell version.

## Gate row 3 — last-good export hashes + NGS identity outcomes

`read_last_good_export(verify=True)` → **VERIFY OK** (hash verification passed, not merely present):

- `run_id` `nflverse-usage-20260803T0311151108400000`, `schema_version` `nflverse_usage.v4`
- `rows_total` 314,641 · seasons 2016–2025 · export ready marker present
- five data streams + `unresolved_identity`, each with a recorded sha256:
  `injuries` `7d034011…` · `ngs_passing` `fb7bc1e9…` · `ngs_receiving` `2e3fccc5…` ·
  `ngs_rushing` `eafc15a1…` · `snap_counts` `290dea10…` · `unresolved_identity` `ce47b8a0…`

**NGS identity outcomes — the decisive asymmetry.** Canonical resolves canonical DG identity:

| family | `identity_status` | `dg_player_id` unresolved | coverage |
| :-- | :-- | --: | --: |
| passing | `canonical_resolved` 5,933 | 0 | 100.0000% |
| receiving | `canonical_resolved` 14,731 | 0 | 100.0000% |
| rushing | `canonical_resolved` 6,059 | 0 | 100.0000% |

The withdrawn route carries **none** of `dg_player_id`, `identity_status`, `row_key`,
`season_ingested`. Its `identity_coverage_by_stat_type: 1.0` means only that the raw **GSIS** id was
present — it never resolved to the canonical Dynasty Genius `player_id`. Under `01` §Identity
Resolution ("Dynasty Genius owns one canonical `player_id`"; "No adapter may invent its own
production identity logic"), the canonical store satisfies the rule and the withdrawn route does
not. **Removing it loses no identity information; it removes a route that never had any.**

## Gate row 4 — canonical readers still wired

`load_nextgen_from_export` is defined in `src/dynasty_genius/nflverse_usage.py:1367` and called by
exactly the two expected consumers, both live call sites (not dead imports):

- `scripts/run_feature_refresh.py:39` (import), `:80` (`sources.update(load_nextgen_from_export(...))`)
- `scripts/assemble_engine_b_dataset.py:34` (import), `:230` (`**_load_nextgen_from_export(...)`)

Executed against the real export, it returns all three families at exactly the reconciled counts:
`nextgen_passing (5933, 29)` · `nextgen_receiving (14731, 23)` · `nextgen_rushing (6059, 22)`.

## Gate row 5 — no production caller of the withdrawn adapter

```
rg -n "from .*nfl_nextgen_capture import|import nfl_nextgen_capture" src/ scripts/ | rg -v test
→ scripts/run_nfl_nextgen_capture.py:14   (itself one of the three withdrawn files)
```

The only importer of the withdrawn adapter is the withdrawn runner. Removing the three files
together leaves no dangling import. Caller counts for the eight free nflverse loaders, measured
across `src/ scripts/ app/` excluding tests, corroborate this:

`load_nextgen_stats` → 2 (`scripts/run_nfl_nextgen_capture.py` **withdrawn**, plus canonical
`src/dynasty_genius/nflverse_usage.py`) → **1 after withdrawal, the canonical one.**

## Gate row 6 — focused + full gates

- **Focused slice (the six authoritative contracts): 147 passed.** Matches the board exactly.
  `test_nflverse_usage_ingestion_red.py` · `test_nflverse_injuries_red.py` ·
  `test_nflverse_schema_era_replay.py` · `test_nflverse_fingerprint_preflight.py` ·
  `test_ingestion_properties_red.py` · `test_source_registry.py`
  (`test_nfl_nextgen_capture.py` deliberately excluded — it is one of the withdrawn files.)
- **Collection: 4,335 collected, ZERO collection errors** — remeasured this session on this tree,
  not inherited. The count is a property of this tree and will change when the withdrawal removes
  `tests/contract/test_nfl_nextgen_capture.py`. The invariant is zero collection errors.
- `ruff check src app` → **All checks passed!**
- **Full unfiltered suite (no `--ignore`, no filter): `4314 passed, 12 skipped, 9 xfailed,
  361 warnings, 0 failed` in 326.41s.** Exit code 0.

  **Two reconciliations, done rather than assumed:**
  1. `4314 + 12 + 9 = 4335` — equals the collected count exactly, so nothing was silently
     deselected.
  2. This session measures **4314** where today's earlier ledger entry measured **4312**. That is
     **not** a regression and not a discrepancy: the 09:32 Codex forward correction already recorded
     that the 4312 census ran *before* the two tests added for the mutation pilot's two survivors.
     `4312 + 2 = 4314`. Checked against the ledger rather than reported as a difference.

## Preserved, deliberately

The gitignored duplicate DATA tree `app/data/sources/nfl_nextgen_stats/` (manifest run
`20260731T030010433470Z`, 26,723 curated rows, immutable raw Parquet per family) is **untouched and
stays untouched.** Its deletion is a separate retention ruling that David has not given, and the
board names it as NEVER authorized in any session. Nobody deletes captured data on agent initiative.

---

## Finding beyond the gate — `docs/data-inventory.md` is stale on THREE counts, not two

Step 1b names two. A third was measured during this audit and is recorded here rather than fixed
silently:

1. **Line 70** — NGS row says *"no product/model consumer yet"*. **False.** `load_nextgen_from_export`
   has two live production consumers (gate row 4).
2. **Line 125** — points at `app/data/sources/nfl_nextgen_stats/` (the **withdrawn** store) as the
   NGS location and says *"NOBODY in the product/model yet"*. **False on both clauses**: wrong store,
   and there are consumers.
3. **NEW — lines 85–88 and line 157** say **seven** free loaders remain unwired and both list
   `load_injuries` among them. **False.** `load_injuries` is wired into the canonical adapter:
   `nflverse_injury_report` holds **34,812 rows** and `injuries` is one of the five export streams
   with a recorded sha256. The correct count is **six**: `load_depth_charts`, `load_contracts`,
   `load_ff_opportunity`, `load_ff_rankings`, `load_pfr_advstats`, `load_ftn_charting` — which is
   exactly what the AGENT_SYNC board's own "Measured open state" says. The inventory disagrees with
   the board, and the board is the one that matches the repo.

Repair of these is Step 1b — correcting text against measured fact, which needs no CLEAR.

## Consumer disposition (standing landing requirement)

NGS: **`existing_consumer`** — reader path `src/dynasty_genius/nflverse_usage.py::load_nextgen_from_export`,
consumed by `scripts/run_feature_refresh.py` and `scripts/assemble_engine_b_dataset.py`.
**Permitted use: `context_signal` only**, per the registry entry. Production data consumption is not
predictive validation and is not model-promotion authority.
