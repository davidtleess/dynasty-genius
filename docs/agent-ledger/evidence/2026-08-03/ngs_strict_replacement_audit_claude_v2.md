# NGS strict-replacement audit — Step 1, v2

**Supersedes** `ngs_strict_replacement_audit_claude_v1.md` (kept on disk; its errors are recorded
in §Corrections below rather than smoothed away).

**Author:** Claude Code (implementing lane) · **Reviewer:** Codex (independent)
**Round 1 review:** `ngs_strict_replacement_review_codex_v1.md` — **NOT CLEAR**, four defects.
**Date:** 2026-08-03 · **Layer served:** Layer 1 (ingest)

**Layers 1–2 dependency check — restated precisely (closes F4).** This work *is* Layer 1, so the
check is not a downstream question. **Correction to v1:** v1 said "nothing at layers 3–6 was read or
touched," which was false — gate row 4 both reads *and executes* two downstream consumers.
The accurate statement: **no layer 3–6 work was opened, and nothing downstream was mutated;
consumer code was read and invoked read-only, solely to verify export wiring.**

**Session state (measured):** `HEAD == origin/main == 85bf5b5f6b70cdd58a88bdfba35eaf89eb414203`.
**Write scope of this pass: NOTHING removed, NOTHING mutated.** The three NGS files remain on disk
untracked; the gitignored duplicate DATA tree is untouched.

---

## Verdict

**Strict replacement is PROVEN, with one qualification that v1 got wrong and one loss v1 never
measured.** All six gate rows now close, including `verify_sprint_closeout.py` **ENFORCE PASS**.

Stated at its true scope: this proves **replacement**, not **value**. NGS remains `context_signal`
in the registry. Nothing here is model or feature promotion authority, and no football claim about
NGS is asserted.

---

## Gate row 1 — one registry adapter / one store ✅

Exactly one `nfl_nextgen_stats` entry (`source_registry.py:363`), naming
`src/dynasty_genius/nflverse_usage.py` + `app/data/nflverse_usage.db`. The `:381` occurrence of
`test_nfl_nextgen_capture.py` is inside a **prose note** recording the withholding — verified by
reading the surrounding lines, not by grep count. Codex independently confirmed exact-one, and its
whole-repo + **AST** caller scans agree with the text scans below.

## Gate row 2 — reconciliation, upgraded from counts to keys and payload ✅ (closes F2)

v1 proved **30 count cells**. That was the weaker claim. Codex's stronger probe was reproduced
independently here after **two broken attempts of my own** (§Corrections):

| family | joined rows | shared fields (incl. 5 key) | duplicate keys | one-sided keys | payload mismatches |
| :-- | --: | --: | --: | --: | --: |
| passing | 5,933 | 25 | 0 | 0 | **0** |
| receiving | 14,731 | 19 | 0 | 0 | **0** |
| rushing | 6,059 | 18 | 0 | 0 | **0** |

Key sets are **identical** on all three families; every row joins; every shared field agrees to
within 1e-6 numerically and exactly on strings. Per-family/season counts remain exact on all 30
cells.

**"Strict superset" was the wrong phrase and is withdrawn.** The correct claim: **exact shared
payload, plus stronger governed identity/persistence/provenance on the canonical side.** It is
**not** a literal schema superset in either direction — see gate row 7.

## Gate row 3 — identity: v1's explanation was WRONG (closes F3) ✅

**v1 claimed the withdrawn route "never had any identity information." That is false, and I told
David so. Independently verified here, confirming Codex:**

- The withdrawn route sets `player_id` from `player_gsis_id` — equal on **26,723 / 26,723** rows.
- Canonical `dg_player_id == player_gsis_id` on **100%** of all three families
  (5,933 / 14,731 / 6,059).
- `nflverse_usage.py:23` says it outright: *"NGS keys on `player_gsis_id`, which **is** our
  canonical id — so NGS needs no bridge."*

So **both routes carry the same canonical identifier.** The real canonical advantage is narrower and
governance-shaped, not informational:

- explicit **resolution status** (`identity_status = canonical_resolved`, 0 unresolved),
- a durable **`row_key`** and **`season_ingested`** persistence identity,
- membership-resolution against the governed id set rather than a bare cast.

That still satisfies `01` §Identity Resolution and still justifies one adapter — but on governed
provenance, **not** on the false premise that one route had identity and the other didn't.

## Gate row 4 — canonical readers still wired ✅

`load_nextgen_from_export` (`nflverse_usage.py:1367`) called at `run_feature_refresh.py:39/:80` and
`assemble_engine_b_dataset.py:34/:230` — live call sites, not dead imports. Executed against the
real export it returns `nextgen_passing (5933, 29)`, `nextgen_receiving (14731, 23)`,
`nextgen_rushing (6059, 22)`.

## Gate row 5 — no production caller of the withdrawn adapter ✅

Only `scripts/run_nfl_nextgen_capture.py:14`, itself one of the three withdrawn files. Corroborated
by loader caller counts: `load_nextgen_stats` → 2 today (withdrawn runner + canonical), **1 after
withdrawal**. Codex's independent AST scan agrees with the text scan.

## Gate row 6 — focused + full gates ✅

- Focused six-contract slice: **147 passed** (matches the board; Codex independently 147).
- Collection: **4,335 collected, ZERO collection errors**, remeasured on this tree.
- Full unfiltered suite: **4,314 passed, 12 skipped, 9 xfailed, 361 warnings, 0 failed**, exit 0.
  - `4,314 + 12 + 9 = 4,335` — matches collection exactly; nothing silently deselected.
  - 4,314 vs today's earlier **4,312**: not a regression. The 09:32 forward correction records that
    4,312 ran *before* the two mutation-pilot tests were added. `4,312 + 2 = 4,314`. Checked against
    the ledger, not reported as a discrepancy.
- `ruff check src app`: **All checks passed!**
- **`scripts/verify_sprint_closeout.py`: ENFORCE verdict PASS** (closes F1) — python-suite PASS,
  ruff PASS, standalone-scripts PASS. Its REPORT block correctly lists the three untracked NGS paths
  and this audit artifact as new files.

## Gate row 7 — NEW: what withdrawal actually loses (neither v1 nor round 1 measured this)

Strict replacement was being asserted without anyone measuring the duplicate-only columns. Measured
now, counting a column as real for a family only where it is non-null (the curated table is a
`diagonal_relaxed` concat, so cross-family columns are null padding):

**Duplicate-only, all three families:** `player_id` · `stat_type` · `source` ·
`source_retrieved_at` · `schema_version` · `is_season_summary` · `position` · `team` ·
`player_first_name` · `player_last_name` · `player_short_name` · `player_jersey_number`

Eight of those twelve are **not losses** — they are derived restatements or provenance the canonical
route carries elsewhere: `player_id` == `player_gsis_id` (retained); `position` / `team` are copies
of retained `player_position` / `team_abbr`; `is_season_summary` is `week == 0`; `stat_type` is the
table name; `source` / `source_retrieved_at` / `schema_version` live in the canonical manifest and
export provenance.

**Four are genuine, and are lost from the canonical store:**
`player_first_name` · `player_last_name` · `player_short_name` · `player_jersey_number`.
Confirmed absent from the SQLite store **and** from all 44 canonical export artifacts (checked
`ngs_passing` across every run, including `backfill-20260731T192915` and the current
`nflverse-usage-20260803T0311151108400000`).

**Why this does not block the withdrawal — three independent reasons:**
1. The **duplicate DATA tree is preserved** by standing ruling, so the columns remain on disk.
2. They are **free and re-fetchable** at any time from `nflreadpy.load_nextgen_stats` — no
   credential, no cost, no licence barrier.
3. They are **cosmetic identity fields**; `player_display_name` is retained, and no consumer,
   feature, or model reads any of the four (zero callers).

Recorded rather than waved past: the honest claim is *"withdrawal loses four cosmetic upstream
columns from the canonical store, which are preserved on disk and freely re-fetchable"* — not
*"withdrawal is lossless."*

## Preserved, deliberately

`app/data/sources/nfl_nextgen_stats/` (run `20260731T030010433470Z`, 26,723 curated rows, immutable
raw Parquet per family) is **untouched and stays untouched.** Deletion is a separate retention
ruling David has not given, and the board names it NEVER authorized in any session. Gate row 7 now
gives an additional substantive reason to keep it.

---

## Findings on documentation drift

**Step 1b (`docs/data-inventory.md`) — stale on THREE counts, not the two the board names:**

1. **Line 70** — *"no product/model consumer yet"*. False; two live consumers (gate row 4).
2. **Line 125** — points at the **withdrawn** store and says *"NOBODY in the product/model yet"*.
   False on both clauses.
3. **NEW — lines 85–88 and line 157** say **seven** free loaders remain unwired, both listing
   `load_injuries`. False: injuries is wired (`nflverse_injury_report`, **34,812 rows**, an export
   stream with a recorded sha256). Correct count is **six** — exactly what the AGENT_SYNC board's
   own "Measured open state" says. The inventory disagrees with the board; the board matches the
   repo.

**F5 scope disposition — Codex's non-blocking drift discovery.** `src/dynasty_genius/nflverse_usage.py:10–11`
still reads *"Nothing downstream reads it yet — no model input, no surface, no scoring."* **This is
stale by the same measurement as inventory defect 1** — two live consumers. **Disposition:
RECORDED, NOT FIXED IN STEP 1b.** Step 1b is scoped to `docs/data-inventory.md`; this is a source
docstring in the canonical adapter and touching it would silently widen the step. It is a one-line
correction with no behavioural effect, and it needs its own word. Flagging it as a defect a reviewer
would otherwise re-find.

## Consumer disposition (standing landing requirement)

NGS: **`existing_consumer`** — reader `src/dynasty_genius/nflverse_usage.py::load_nextgen_from_export`,
consumed by `scripts/run_feature_refresh.py` and `scripts/assemble_engine_b_dataset.py`.
**Permitted use: `context_signal` only**, per the registry entry. Production data consumption is not
predictive validation and is not model-promotion authority.

---

## Corrections — v1's errors, recorded not smoothed

1. **F3, the serious one.** v1 asserted the withdrawn route "never had any identity information."
   **False** — it carries GSIS, which *is* the canonical id. I stated this to David as a
   load-bearing reason for withdrawal. The withdrawal still stands, on governed-provenance grounds
   instead. This is the same overclaim class the session has been correcting all day: I measured a
   real asymmetry (four governed columns) and inflated it into a categorical one.
2. **F1.** v1's verdict said every gate row was proven while `verify_sprint_closeout.py` had not
   landed. A pending row is not a passing row.
3. **F2.** v1's reconciliation was counts-only and called the result a "strict superset."
4. **F4.** v1's layer statement was false as written.
5. **Two of my own probes were broken before either produced a usable number** — worth recording
   because both failed *toward a scary answer*, not a reassuring one. Probe A filtered the
   `diagonal_relaxed` curated table per family without dropping null-padded cross-family columns.
   Probe B compared canonical (SQLite **TEXT**, per the documented design at `nflverse_usage.py:211`
   — the *export* publishes real numbers, the store does not) against duplicate floats via `Utf8`
   casts, so `"434.32687097901"` diffed against a float repr and produced ~109,000 phantom
   mismatches. Type-correct comparison gives **0**, reproducing Codex exactly. I did not report
   either broken number as a finding.
