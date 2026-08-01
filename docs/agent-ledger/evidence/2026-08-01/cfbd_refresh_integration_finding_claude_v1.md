# CFBD foundation blocker — Claude independent reproduction

**Lane:** Claude Code (source-pipeline implementation)
**Responding to:** `docs/agent-ledger/evidence/2026-08-01/cfbd_refresh_integration_finding_codex_v1.md`
**Verdict: CONFIRM.** Every Codex figure reproduced independently. Two further defects found that
the Codex packet does not name, and one honest limit on what either lane can prove from disk.

**Write scope:** this document only. No live CFBD call, no code change, no model input touched, no
promotion or copy of the isolated curated CSV.

**Layer served: 1 (ingest), presenting.** Layers 1-2 dependency check not applicable — this *is*
layer 1. The defect is at the layer that causes it.

---

## 1. Reproduced from Codex's packet

| Codex claim | Claude independent result | Status |
| :-- | :-- | :-- |
| 251 changed cells vs the active input | **251** | reproduced |
| across 44 QBs | **44 distinct `gsis_id`, all position QB** | reproduced |
| no WR/RB/TE changes | **0 non-QB players changed** | reproduced |
| identical payloads across players, groups of 5-14 | **8-15 per season, both vintages** | reproduced |
| 2016 cohort shares `completion_pct=0.00594 / YPA=6.2 / TD:INT=1.0909` | **exact match, 9 QBs** | reproduced |
| wrapper publishes `ok` without identity/collision/range/retention gates | confirmed by reading `_validate_curated` | reproduced |

Method: keyed on `gsis_id` (verified unique, 874/874) rather than row position. Row order was
independently verified identical between the two files, so a positional read gives the same answer
here — but the keyed comparison is the one reported.

**Files compared**
- active input: `app/data/training/prospects_with_outcomes_v3.csv`
- isolated run: `app/data/sources/cfbd_foundation/curated/prospects_with_outcomes_v3.csv`
  (run `20260731T165930158823Z`, `status: ok`, 874 rows, identity coverage 1.0)

**Where the two counts come from** — the 44 is driven by provenance columns, the 15 by values:

| column | changed rows |
| :-- | --: |
| `qb_completion_pct_final_source` | 44 |
| `qb_yards_per_attempt_final_source` | 44 |
| `qb_td_int_ratio_final_source` | 44 |
| `qb_sack_rate_final_source` | 29 |
| `qb_completion_pct_final` (+`_missing`) | 15 |
| `qb_yards_per_attempt_final` (+`_missing`) | 15 |
| `qb_td_int_ratio_final` (+`_missing`) | 15 |

## 2. The collision, stated concretely

Byte-identical normalized QB payloads are shared across many players in the same season, in **both**
the legacy active cache and the fresh isolated run.

Largest groups, isolated run: 2015 **14 QBs** · 2022 **10** · 2020 **10** · 2017 **10** · 2024 **9** · 2023 **8**
Largest groups, legacy cache: 2015 **15 QBs** · 2024 **10** · 2020 **10** · 2018 **9** · 2016 **9** · 2019 **8**

The 2016 group of nine — Mahomes, Watson, Trubisky, Kizer, Beathard, Dobbs, Peterman, Kaaya, Kelly —
every one carrying:

```
completion_pct 0.00594 · yards_per_attempt 6.2 · td_int_ratio 1.0909090909090908
all_purpose_yards 2923.0 · pass_attempts 374 · rushing_yards 600.0 · rushing_tds 8.0
```

The 2020 group of ten includes Trevor Lawrence, Justin Fields, Mac Jones, Kyle Trask, Davis Mills,
Ian Book, Kellen Mond and Sam Ehlinger on one line. In the curated table these collapse to a single
value per draft class: 2015 → 7.5, 2017 → 6.2, 2021 → 6.4, 2023 → 6.7.

**Season-label reconciliation — not a disagreement between lanes.** Codex's "2016 rows" is the
college-season year in the cache filename; the CSV `season` column for the same nine players reads
2017 (draft year). Same players, two different columns. Recorded so a later reader does not mistake
it for a conflict.

## 3. Two defects the Codex packet does not name

**3.1 `completion_pct` is out of range for every populated row — an independent computation defect.**
Across the 62 populated QB payloads in the fresh run: min `0.0`, max `0.01`, distinct values
`{0.0, 0.00572, 0.00576, 0.0058, 0.00594, 0.00618, 0.01}`. A completion percentage cannot be 0.006 on
any scale (0-1 or 0-100). **0 of 62 fall in a plausible band.** This is not only misattribution — the
field is also computed wrong, and would still be wrong after the collision is fixed. `sack_rate` is
**0/126 populated — fully dark** — and the run still published `ok`.

**3.2 The `raw/` snapshot is not raw for two of its four file families.** Measured over the 572 files:

| family | count | on-disk shape | raw? |
| :-- | --: | :-- | :-- |
| `tpa_*` | 404 | bare float scalar (e.g. `382.0`) | **no** |
| `qb_stats_*` | 126 | post-normalization contract dict, 11 canonical keys | **no** |
| `player_*` | 28 | API response list (`season`,`playerId`,`player`,…) | yes |
| `sp_ratings_*` | 14 | API response list (`year`,`team`,`rating`,…) | yes |

This violates `01-north-star-architecture.md` §Source Adapter Rules — *"write a raw snapshot before
parsing when feasible"* — and it has a direct evidentiary cost, below.

## 4. Root-cause status — stated as proven vs inferred

**PROVEN from artifacts on disk:**
1. Distinct players carry byte-identical full stat vectors, in both cache vintages (§2).
2. `completion_pct` is outside any valid range for 62/62 populated rows (§3.1).
3. `sack_rate` is 0/126 populated and published `ok` (§3.1).
4. The publication contract has no response-identity, cross-player-collision, semantic-range, or
   feature-retention gate. `_validate_curated`
   (`src/dynasty_genius/capture/cfbd_foundation_refresh.py:97-139`) checks required columns, the
   `w2b_cfbd_degraded` flag, identity coverage ≥ 0.99, and the presence of a populated `_source`
   column — none of which any of defects 1-3 trips.
5. The defect is in the **active** input Engine A reads today, not only in the isolated run. The
   isolated run redistributes and partially drops the bad payload; it does not introduce it.

**INFERRED — strongly supported by code, NOT proven from disk:** the mechanism is that
`fetch_qb_college_stats` queries `/stats/player/season` with a fuzzy `playerName`
(`src/dynasty_genius/adapters/cfbd_qb_adapter.py:129-133`), and `_first_stat` (`:58-68`) returns the
first record whose `statType == "YPA"` **without checking that the record belongs to the requested
player, team, or season**; `_request_json` (`:40-48`) swallows every exception into `[]`, making a
rate-limit or timeout indistinguishable from "no data" — which also explains why a larger live run
produced *fewer* populated values than the cache.

**Why it cannot be closed from disk (§3.2's cost):** because `qb_stats_*` files store the
post-normalization dict, **no on-disk artifact records which player CFBD actually returned.** The
evidence needed to attribute the collision was discarded before it was written. Proving the mechanism
needs one live single-player call — outside the constraint of this exchange and requiring David's
word. The repair below does not depend on that confirmation: every gate is justified by the proven
items alone.

## 5. Proposed repair / RED contract boundary

Codex owns the failing RED; Claude owns the source-pipeline GREEN.

**Adapter (`cfbd_qb_adapter.py`)**
- **G1 — response identity binding.** A payload is accepted only when bound to the requested player
  (plus team/season where available). An unattributable response yields an explicit refusal, never a
  value.
- **G2 — no silent exception swallowing.** Transport/HTTP failure must be distinguishable from "no
  data" in the returned contract and in the persisted record.

**Publication contract (`cfbd_foundation_refresh.py::_validate_curated`)**
- **G3 — cross-player collision gate.** Refuse publication when distinct players within a season
  carry an identical full stat vector. Observed maximum today is 15; any N > 1 for a complete vector
  is indefensible.
- **G4 — semantic range gate.** Per-field declared valid ranges, refusing on violation.
  `completion_pct ∈ [0,1]` alone rejects all 62 current rows.
- **G5 — feature-retention / coverage gate.** Refuse when a declared family is 0% populated
  (`sack_rate`), or when coverage regresses materially against the previous manifest.

**Snapshot fidelity**
- **G6 — persist the unmodified API response** under `raw/` before normalization; normalized output
  belongs in the curated tier. Without G6 the next occurrence is equally unprovable.

**Explicitly NOT in this boundary** (each needs David's word, and none is opened here):
- Any promotion or copy of the isolated curated CSV into the active input.
- Any further live/paid full refresh.
- Any model remediation. **See §7 — the original text here was wrong and is corrected there.**

## 6. Agreement with Codex's operational read

Confirmed independently: the active Engine A scripts read
`app/data/training/prospects_with_outcomes_v3.csv`; nothing reads the isolated curated path. A
further paid full fetch through the current adapter would not fix the active-consumer problem — it
would redistribute the same defect. **The refresh is not the unit of work; the adapter is.**

---

## 7. CORRECTION — my error, and the corrected blast radius

**I misread a field and it propagated.** §5 of this document originally stated that the three
`qb_*_final` columns carried **"importance 39.5"** and that a past bakeoff **"consumed a feature on
which nine quarterbacks share one line."** Both clauses are **wrong**. Caught by Codex
(`w#cfbdblast1`); correction artifact
`docs/agent-ledger/evidence/2026-08-01/cfbd_blast_radius_correction_codex_v1.md`.

**What the artifact actually says**, verified by me directly at
`app/data/backtest/phase20/phase20_bakeoff_20260524T183807Z_db568d44.json`, `positions.QB`:

- `coverage_pct` is a **dict of coverage percentages**, not importances:
  `nfl_pick 100.0 · nfl_round 100.0 · final_college_age 100.0 · qb_completion_pct_final 39.5 ·
  qb_yards_per_attempt_final 39.5 · qb_td_int_ratio_final 39.5 · qb_sack_rate_final 0.0`.
- `dropped_features` = **all four** CFBD QB fields. `available_features` = `nfl_pick`, `nfl_round`,
  `final_college_age` only.
- `gate_results`: ridge and gbt both `skipped: true`, `reason: enriched_features_equal_baseline`.
- `passing_candidates: []`; `model_pkl_changed: false`; `latest_json_changed: false`.
- `app/data/models/QB_model.pkl` is dated **Apr 30**, predating the May 24 run.

**The four fields were dropped by a coverage gate before any fit. No model consumed them.**

**Reconciliation, recorded because it corroborates rather than excuses:** 39.5% of the
`n_eligible_rows = 38` is **15 rows** — the exact count of rows I independently measured as differing
in the three value columns (§1). The number was right; my reading of what it measured was wrong.
`qb_sack_rate_final 0.0` likewise matches my independent 0/126 dark-field finding.

**Corrected blast radius:** the defect is presently confined to the **ingestion / data-artifact
layer** — the cache and the training CSV. It is a **future-candidate hazard**, not a past
contamination. No promoted model, no live surface, no fit.

**How the error happened, for calibration (`02` §Falsification #6):** I ran a `grep` that returned
`"qb_completion_pct_final": 39.5` and inferred "importance" from the shape of the line without
reading the enclosing key. The enclosing key was three lines up. The falsification I skipped was
free: three distinct features sharing an identical value to one decimal is far more consistent with
coverage than with importance, and I had already measured `sack_rate` at 0/126 — which sits in that
same dict as `0.0` and would have named the field for me.

**Note on the sent message.** `msg_codex_cfbd_confirm_claude_v1.txt` in this directory carries the
erroneous sentence. It is **deliberately left unedited** — it is the record of what was actually
sent, and rewriting it would falsify the wire history. This section supersedes it.

**One substantive refinement this correction produces, not a defense of the error:** the Phase-20
runner *already had* a coverage gate, and that gate worked — it dropped the four fields rather than
fitting on them. The missing gate is at **ingestion**, which is exactly where G3-G5 place it. It
also suggests a cheap tripwire worth naming: `enriched_features_equal_baseline` should be treated as
a **defect signal**, not silently reported inside a null result. That is a model/bakeoff-layer
change, outside this boundary and needing David's word.
