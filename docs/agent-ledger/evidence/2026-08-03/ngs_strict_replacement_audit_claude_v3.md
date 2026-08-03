# NGS strict-replacement audit — Step 1, v3

**Supersedes** `ngs_strict_replacement_audit_claude_v2.md` (which superseded v1). Both stay on disk;
every error is recorded in §Corrections rather than smoothed away.

**Author:** Claude Code (implementing lane) · **Reviewer:** Codex (independent)
**Review rounds:** `ngs_strict_replacement_review_codex_v1.md` (NOT CLEAR, F1–F4 + F5 drift) ·
`ngs_strict_replacement_review_codex_v2.md` (NOT CLEAR, F6 blocking).
**Date:** 2026-08-03 · **Layer served:** Layer 1 (ingest)

**Layers 1–2 dependency check.** This work *is* Layer 1. **No layer 3–6 work was opened and nothing
downstream was mutated;** consumer code was read and invoked read-only, solely to verify export
wiring.

**Session state:** `HEAD == origin/main == 85bf5b5f6b70cdd58a88bdfba35eaf89eb414203`.
**Write scope: NOTHING removed, NOTHING mutated.** The three NGS files remain untracked on disk; the
gitignored duplicate DATA tree is untouched.

---

## Verdict

**Strict replacement is PROVEN.** All six gate rows close, plus the row-7 question v1 and v2 never
answered correctly. `verify_sprint_closeout.py` **ENFORCE PASS**.

**Withdrawal loses no provider column.** No refetchability argument and no "cosmetic field" defense
is needed — both were artifacts of my own incomplete measurement, and both are withdrawn.

Scope, stated at its true limit: this proves **replacement**, not **value**. NGS remains
`context_signal` in the registry. Nothing here is model or feature promotion authority, and no
football claim about NGS is asserted.

---

## Gate row 1 — one registry adapter / one store ✅

Exactly one `nfl_nextgen_stats` entry (`source_registry.py:363`) naming
`src/dynasty_genius/nflverse_usage.py` + `app/data/nflverse_usage.db`. The `:381` occurrence of
`test_nfl_nextgen_capture.py` is inside a **prose note** recording the withholding — verified by
reading it, not by grep count. Codex independently confirmed exact-one; its whole-repo and **AST**
caller scans agree with the text scans.

## Gate row 2 — reconciliation at key and payload level ✅

| family | joined rows | shared fields (incl. 5 key) | duplicate keys | one-sided keys | payload mismatches |
| :-- | --: | --: | --: | --: | --: |
| passing | 5,933 | 25 | 0 | 0 | **0** |
| receiving | 14,731 | 19 | 0 | 0 | **0** |
| rushing | 6,059 | 18 | 0 | 0 | **0** |

Key sets identical on all three families; every row joins; every shared field agrees to 1e-6
numerically and exactly on strings. Per-family/season counts exact on all 30 cells.

**"Strict superset" is withdrawn** as the wrong phrase. The correct claim: **exact shared payload,
plus stronger governed identity/persistence/provenance on the canonical side** — not a literal
schema superset in either direction (see row 7).

## Gate row 3 — identity ✅

**Both routes carry the same canonical identifier.** Verified independently:

- withdrawn route's `player_id == player_gsis_id` on **26,723 / 26,723** rows;
- canonical `dg_player_id == player_gsis_id` at **100%** on all three families;
- `nflverse_usage.py:23`: *"NGS keys on `player_gsis_id`, which **is** our canonical id — so NGS
  needs no bridge."*

The canonical advantage is governance-shaped, not informational: explicit resolution status
(`identity_status = canonical_resolved`, 0 unresolved), a durable `row_key`, `season_ingested`
persistence, and membership resolution against the governed id set rather than a bare cast. That
satisfies `01` §Identity Resolution and justifies one adapter — **on governed provenance, not on the
false premise that one route had identity and the other did not.**

## Gate row 4 — canonical readers still wired ✅

`load_nextgen_from_export` (`nflverse_usage.py:1367`) called at `run_feature_refresh.py:39/:80` and
`assemble_engine_b_dataset.py:34/:230` — live call sites. Executed against the real export it returns
`nextgen_passing (5933, 29)`, `nextgen_receiving (14731, 23)`, `nextgen_rushing (6059, 22)`.

## Gate row 5 — no production caller of the withdrawn adapter ✅

Only `scripts/run_nfl_nextgen_capture.py:14`, itself one of the three withdrawn files.
`load_nextgen_stats`: 2 callers today → **1 canonical after withdrawal**. Codex's independent AST
scan agrees.

## Gate row 6 — focused + full gates ✅

- Focused six-contract slice: **147 passed** (Codex independently 147).
- Collection: **4,335 collected, ZERO collection errors**, remeasured on this tree.
- Full unfiltered suite: **4,314 passed, 12 skipped, 9 xfailed, 361 warnings, 0 failed**, exit 0.
  - `4,314 + 12 + 9 = 4,335` — matches collection exactly; nothing silently deselected.
  - 4,314 vs today's earlier 4,312: the two mutation-pilot tests per the 09:32 forward correction.
    `4,312 + 2 = 4,314`. Checked against the ledger, not reported as a discrepancy.
- `ruff check src app`: **All checks passed!**
- **`scripts/verify_sprint_closeout.py`: ENFORCE verdict PASS** — python-suite, ruff, and
  standalone-scripts all PASS.

## Gate row 7 — what withdrawal loses: NOTHING (corrected; closes F6) ✅

**The question was right; v2's answer was wrong because it stopped at the curated projection.**

Twelve columns exist in the duplicate's curated table but not in the canonical **SQLite store /
export**. Eight are derived restatements or provenance held elsewhere: `player_id` ==
`player_gsis_id`; `position` / `team` copy retained `player_position` / `team_abbr`;
`is_season_summary` is `week == 0`; `stat_type` is the table name; `source` /
`source_retrieved_at` / `schema_version` live in the canonical manifest and export provenance.

The remaining four — `player_first_name`, `player_last_name`, `player_short_name`,
`player_jersey_number` — **are retained by the canonical route in its pre-parse raw snapshots.**

**Mechanism** (`src/dynasty_genius/nflverse_usage.py`): `write_raw_snapshot` is called on the
provider payload at `:1503–1513` **before** `normalize_rows` and the store projection, so the raw
snapshot preserves upstream columns the curated projection drops.

**Measured, independently reproducing Codex:**

| check | result |
| :-- | :-- |
| canonical NGS raw files | **171** (57 passing / 57 receiving / 57 rushing), **0 empty** |
| files missing any of the four provider fields | **0 of 171** |
| latest-per-season coverage | **30 / 30 cells** |
| latest-per-season row totals | passing **5,933** · receiving **14,731** · rushing **6,059** — exact |
| non-null across 26,723 latest-snapshot rows | first_name 100% · last_name 100% · jersey_number 100% · short_name 99.89% |

The `player_short_name` gap is **30 provider-side nulls, not a route difference**: the duplicate has
**the identical 26,693 / 26,723**. The two routes match on these fields nulls-and-all.

**Correct conclusion:** the four are **curated-projection omissions, fully retained in canonical
pre-parse raw snapshots.** Withdrawal loses **no provider column**. v2's refetchability and
"cosmetic field" arguments are **withdrawn as unnecessary** — they were defending against a loss
that does not exist.

## Preserved, deliberately

`app/data/sources/nfl_nextgen_stats/` (run `20260731T030010433470Z`, 26,723 curated rows, immutable
raw Parquet per family) is **untouched and stays untouched.** Deletion is a separate retention
ruling David has not given, and the board names it NEVER authorized in any session.

**Correction to v2:** v2 said row 7 "gives an additional substantive reason to keep it." It does
not. **The preservation ruling stands entirely on its own** — it is a standing David-gated retention
decision, and it neither needs nor receives support from this audit.

---

## Findings on documentation drift

**Step 1b (`docs/data-inventory.md`) — stale on THREE counts, not the two the board names:**

1. **Line 70** — *"no product/model consumer yet"*. False; two live consumers (row 4).
2. **Line 125** — points at the **withdrawn** store and says *"NOBODY in the product/model yet"*.
   False on both clauses.
3. **NEW — lines 85–88 and line 157** say **seven** free loaders remain unwired, both listing
   `load_injuries`. False: injuries is wired (`nflverse_injury_report`, **34,812 rows**, an export
   stream with a recorded sha256). Correct count is **six** — exactly what the AGENT_SYNC board's
   "Measured open state" says. The inventory disagrees with the board; the board matches the repo.

**F5 scope disposition (Codex's non-blocking drift).** `nflverse_usage.py:10–11` still reads
*"Nothing downstream reads it yet — no model input, no surface, no scoring."* Stale by the same
measurement as inventory defect 1. **RECORDED, NOT FIXED IN STEP 1b** — it is a source docstring in
the canonical adapter, not `docs/data-inventory.md`, and fixing it inside 1b would silently widen
the step. It needs its own word.

## Consumer disposition (standing landing requirement)

NGS: **`existing_consumer`** — reader `src/dynasty_genius/nflverse_usage.py::load_nextgen_from_export`,
consumed by `scripts/run_feature_refresh.py` and `scripts/assemble_engine_b_dataset.py`.
**Permitted use: `context_signal` only**, per the registry entry. Production data consumption is not
predictive validation and is not model-promotion authority.

---

## Corrections — recorded, not smoothed

**Three review rounds, three substantive errors of mine, each killed by a probe I had not run.**

1. **v1 / F3 — the serious one.** Asserted the withdrawn route "never had any identity information."
   **False**; it carries GSIS, which *is* the canonical id. Stated to David as a load-bearing reason
   for withdrawal. Withdrawal stands on governed-provenance grounds instead.
2. **v1 / F1, F2, F4.** Verdict claimed all rows proven while the closeout gate had not landed;
   reconciliation was counts-only and mislabelled a "strict superset"; the layer statement was false
   as written.
3. **v2 / F6.** Concluded four provider columns were lost, having checked only the SQLite store and
   the 44 export artifacts — **never the 171 raw snapshots**, where they are all retained. I then
   built two defenses (refetchability, "cosmetic") for a loss that did not exist. Codex found it.

**Four broken probes across this audit — every one failing toward a wrong answer I nearly
published:**

- **Probe A**: filtered the `diagonal_relaxed` curated table per family without dropping null-padded
  cross-family columns.
- **Probe B**: compared canonical SQLite **TEXT** (the documented design at
  `nflverse_usage.py:211` — the *export* publishes real numbers, the store does not) against
  duplicate floats via `Utf8` casts, so `"434.32687097901"` diffed against a float repr →
  **~109,000 phantom mismatches**. Type-correct comparison: **0**.
- **Probe C**: read only the export artifacts and concluded the four fields were lost.
- **Probe D**: checked the raw snapshots' **envelope** keys (`schema_version`, `stream`, `season`,
  `captured_at`, `rows`, `records`) instead of `records[*]`, and reported **171 of 171 files
  missing** the four fields — the exact inverse of the truth.

None of the four numbers was reported as a finding; each was caught by inspecting the probe before
trusting its output. The pattern is worth naming: **every broken probe produced a plausible,
alarming result**, and plausibility is not evidence. The rule carried forward is the one the ledger
already records in another form — verify the instrument before believing the measurement,
especially when the measurement is the one you expected.
