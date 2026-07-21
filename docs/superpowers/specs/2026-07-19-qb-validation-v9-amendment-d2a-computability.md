# QB-1 Validation Program — v9 Amendment: D2a Computability + Contract Pins (REVISION 7)

**Status (r7):** DRAFT r7 for Codex exact-delta verification. **r7 = r6 + exactly the two round-1 residues Codex raised at 22:14** — (B1) the base/lineage line and Part D now name the ACTIVE frozen-v9 contract and the live H2 sequence, with the completed r1–r5 sequence retained as struck historical text (no second RED/GREEN cycle implied, ratchet stays 17 XF); (H1) the **total precedence rule** for overlapping missingness causes is pinned in §B4 and parameterized in S35 — position is tested independently of value, so a joined non-QB row counts even when its `passing_cpoe` is also null. No other section changed; the counter representation Codex accepted is untouched.

**Prior status (r6, superseded):** DRAFT r6 for Codex proportionate review — law only at Codex CLEAR + David re-freeze. **r6 = r5 + exactly the H2 closure**, on David's typed word 2026-07-20 ("claude has a good reco for the h2 amendment lets go with that"): the ratified §A3/S4 non-QB CPOE audit obligation gains its schema location, `coverage.cpoe_non_qb_joins`. Exactly four deltas: (1) §A3's non-QB row now names the audit location; (2) §B4's coverage block gains the counter; (3) the counter's semantics paragraph after §B4's schema; (4) canonical seed S35 + this label block. **No other section changed** — r5's CLEARed content (SHA-256 `b7221a7a8b69…`) is otherwise byte-preserved. Scope note: this closes the sole item Codex excluded from the 2026-07-20 22:00 GREEN CLEAR; it is a one-counter contract delta, not a new feasibility question.

**Prior status (r5, superseded by the line above):** r5 = r4 + the three round-4 literal residues (P1 seed-range `S25–S34`; P2 Part D step-1 wording; P3 S32 parameterized over the seven weekly fields). r5 earned Codex's ENUMERATED CLEAR on 2026-07-20 20:28 and was David-ratified into v9 at 20:36.
**Base (r6/r7 — corrected per R6-B1):** the ACTIVE frozen contract — **v9 spec** `2026-07-16-qb-validation-program-design.md`, git blob `8c6001f75c38…`, SHA-256 `347c2d6e30d2…`, **plus the ratified r5 amendment** (SHA-256 `b7221a7a8b69…`, incorporated as binding law at David's 2026-07-20 20:36 ratification). Slice-4 GREEN is already built and CLEARed against that contract (Codex 22:00, six axes) with H2 the sole excluded item — this revision closes H2 only. *(Historical: r1–r5 were authored against frozen v8, blob `e7571d2ec226`, freeze `8fa244c1…`; that base is superseded.)*
**Cycle record:** David's word opened the amendment (07-19). Round 1: NOT CLEAR 7B+5H → r2 (ALL-ACCEPT, verified). Round 2: NOT CLEAR 4B+5H, all round-1 closures PASS → r3 (ALL-ACCEPT, verified). Round 3 (07-20 09:42): NOT CLEAR precision-narrowed 3B+2H — **all nine round-2 dispositions PASS; no feasibility defect survives**. This revision dispositions all five round-3 items as exact deltas; settled areas untouched.

## Round-3 disposition table (all ACCEPT)

| Item | Disposition | Closed |
|---|---|---|
| R3-B1 audit-totality sentence contradicts the partition | ACCEPT — own-text defect confirmed: `no_target_season` is cohort-admitted and lives in `matrix`; audit = exactly the three non-cohort classes; count-source mapping pinned | §B4 |
| R3-B2 identity key incompatible with shipped D2 | ACCEPT — verified in code (`season` at `qb_ppg_labels.py:677,783,837,885`); **minimum closure adopted**: F28 keeps the shipped key `season`; the D2a `target_season` ↔ D2 `season` join mapping is pinned. A D2 schema migration is rejected on proportionality (cosmetic key rename of an 11-round-reviewed shipped surface) — no broader authorization sought | §B5, §B6 |
| R3-B3 canonical list regressed accepted obligations | ACCEPT — manifest ownership/consumption contract restored as §B7; canonical list extended S25–S34 (nothing silently dropped; F27 stays parked with D3) | §B7, §E |
| R3-H1 registration annotation broader than the gate | ACCEPT — pinned `dict[str, Any]`, matching the shipped gate | §B1 |
| R3-H2 null/duplicate source semantics implicit | ACCEPT — null on any consumed weekly field except expressly-paired `passing_epa` refuses `stat_value_invalid` (evidence-backed: zero nulls full-window, so a null is a corruption signal, never silently skipped); duplicate 1b (player_id, season) refuses named BEFORE the join (observed-zero-duplicates is evidence, not a law) | §A3 |

## Round-2 disposition table (all ACCEPT)

| Item | Disposition + implementer verification | Closed |
|---|---|---|
| R2-B1 ANY/A sign backwards | ACCEPT — verified live: 2024 QB-REG `sack_yards_lost` 493 neg / 171 zero / **0 pos** (full-window per Codex: 5,208/6,884 neg, range −79..0); Burrow-2024 cross-check: `+Σ` → 7.279 (correct), r2's `−Σ` → 8.073 (adds lost yards back). Pin flipped to `+Σ`, admission `≤ 0`, positive refuses. Codex's round-1 retraction noted; the row is now empirically pinned from data, not sign convention | §A2, §A3 |
| R2-B2 boundary not provenance-bearing | ACCEPT — the F1 seven-dataset gate is invoked FIRST; the withdrawn claim is object identity only | §B1 |
| R2-B3 matrix rows lack the axes | ACCEPT — every matrix row carries exact `eligibility` + `target`; audit is pinned exclusions-only; D3 re-derives nothing | §B4, §B6 |
| R2-B4 F28 change not a callable contract | ACCEPT — exact signature, row schema, total (eligibility,target)→outcome_class mapping, literal count keys, games/metrics laws enumerated | §B5 |
| R2-H1 weekly CPOE pin unused | ACCEPT — weekly `passing_cpoe` pin dropped (weekly gains three columns, not four); null routing tested hermetically on the 1b path; the 29-row window count is snapshot audit evidence, not RED contract | §A1, §A4 |
| R2-H2 rookie predicate not mechanical | ACCEPT — pinned: no prior REG weekly row AND no prior REG roster row through t−1 | §B3 |
| R2-H3 recursive-flag wording wrong | ACCEPT — verified against `guards.py:108-121`: flag required on root + LIST-ELEMENT mappings only; schema restated to the actual law; no "every mapping" claim | §B4 |
| R2-H4 enumeration/coverage incomplete | ACCEPT — `VALIDATION_DATASETS` seven-name order pinned; 1b seasons 2015–2025; `rows_per_season` semantics pinned; rosters evidence cites the actual D1 endpoint `load_rosters` (Codex-verified to carry `position`) | §A1, §B4 |
| R2-H5 falsification list not self-contained | ACCEPT — ONE canonical uniquely numbered list enumerated fully below (r3: S1–S24; r4 restores the regressed rows as S25–S34; r6 adds S35); no external references | §E |

---

## Part A — H1 computability

### A1. D1 pin extensions

**Weekly** (`VALIDATION_DATASET_COLUMNS["weekly"]`) gains exactly **three** columns:
```
completions, sack_yards_lost, passing_epa
```
(Weekly `passing_cpoe` is NOT pinned — it has no consumer; season CPOE comes from 1b.)

**NEW pinned D1 dataset 1b — `season_summary`:** loader `load_player_stats(seasons, summary_level="reg")`, **required seasons 2015–2025**, pinned columns:
```
player_id, season, position, passing_cpoe
```
Snapshot-before-parse, F14 shape class, F15 column coverage apply to 1b exactly as to the six existing datasets. `VALIDATION_DATASETS` becomes the pinned seven-name order:
```
("weekly", "season_summary", "players", "rosters", "ff_playerids", "draft_picks", "pbp")
```

**Rosters** (`VALIDATION_DATASET_COLUMNS["rosters"]`) gains `position` — present on the actual frozen D1 endpoint `load_rosters` (Codex round-2 independent confirmation; implementer additionally confirmed `position` on `load_rosters_weekly`).

### A2. Pinned H1 derivation formulas

All weekly aggregates run over **ALL of the player's t−1 REG qualifying-game rows, across all teams** (attributed-team law stays at its exact v8 scope: H2 `rush_td_share` + H3 `team_proe` only). `dropbacks_proxy = attempts + sacks_suffered` (unchanged).

| Feature | Pinned source + formula | Degenerate handling |
|---|---|---|
| `completion_pct` [t−1] | weekly: Σ completions ÷ Σ attempts | Σ attempts = 0 → null → missingness path, named |
| `sack_rate` [t−1] | weekly: Σ sacks_suffered ÷ Σ dropbacks_proxy | Σ dropbacks_proxy = 0 → null → missingness path |
| `any_a` [t−1] | weekly: **(Σ passing_yards + 20·Σ passing_tds − 45·Σ passing_interceptions + Σ sack_yards_lost) ÷ Σ dropbacks_proxy** — `sack_yards_lost` is consumed **as source-signed (≤ 0)**; constants 20/45 pinned (standard ANY/A) | same null route |
| `epa_per_dropback` [t−1] | weekly: Σ passing_epa ÷ Σ dropbacks_proxy over weeks with non-null `passing_epa` (paired per-feature exclusion — a guard: the full-window audit found zero nulls on positive-dropback rows) | all-null → null → missingness path |
| `cpoe` [t−1] | **1b: the official REG season-summary `passing_cpoe` for season t−1, consumed as-is** (official nflfastR aggregation, `R/calculate_stats.R:221-240` @ `0489133d…`); join on (player_id, season = t−1); joined row's `position` must read QB | absent/null 1b row → null → missingness path, named |

Weekly CPOE recomposition is rejected as non-exact (Codex full-window: 609/810 QB-seasons diverge, max 4.78; implementer 2024 replication: 56/75, max 0.83). No approximation is adopted.

### A3. Semantic numeric refusal table (precedes every formula)

Per the slice-3 boundary law (exact-plain scalars, named refusals, system-exception preservation):

| Condition | Refusal |
|---|---|
| non-finite value on any consumed stat | `stat_value_invalid` |
| negative value on a count stat: `attempts, completions, sacks_suffered, passing_tds, passing_interceptions` | `stat_value_invalid` |
| **positive** `sack_yards_lost` (source signs it ≤ 0; a positive value is corrupt) | `stat_value_invalid` |
| legitimately signed, admitted with any sign: `passing_yards, passing_epa`, 1b `passing_cpoe` | — |
| `completions > attempts` on a row | `stat_value_invalid` |
| non-integral value in an integral count field | `stat_value_invalid` (lossless-int law) |
| **null on any consumed weekly field** (`attempts, completions, sacks_suffered, passing_tds, passing_interceptions, sack_yards_lost, passing_yards`) — the expressly-paired `passing_epa` null route (§A2) is the sole exception | `stat_value_invalid` — never a silent dataframe-sum skip (evidence: zero nulls full-window on these fields; a null is a corruption signal) |
| **duplicate 1b `(player_id, season)` row**, checked BEFORE the one-to-one CPOE join | named `duplicate_player_season` refusal |
| 1b `position` ≠ QB on the joined CPOE row | null → missingness path, **audited via `coverage.cpoe_non_qb_joins` (§B4, r6)** — source context, not corruption |

### A4. Recorded source evidence

- Codex round-1/round-2 audits: nflreadpy **0.1.5**, 2015–2025 weekly + REG summaries: all pinned columns present every season; `completions`/`sack_yards_lost` zero QB-REG nulls; `passing_epa` zero nulls on positive-dropback rows; weekly `passing_cpoe` 29 positive-dropback null rows across the window (**snapshot audit evidence only — not a RED contract row**, per R2-H1); `season_summary` has zero duplicate QB (player_id, season) rows; `sack_yards_lost` signed ≤ 0 (5,208 neg / 6,884 QB-REG rows, range −79..0); `load_rosters` carries `position`.
- Implementer probes (07-19/07-20, project venv): 2024 column presence/non-null rates; CPOE falsification replication (56/75 > 0.01, max 0.83); 1b fix-path verification (`passing_cpoe`, `position` present); `load_rosters_weekly` `position`; sack-sign distribution (493/171/0) + Burrow ANY/A cross-check (7.279 vs 8.073).
- **RED obligation:** hermetic fixtures assert the null-ROUTING behavior (1b-absent CPOE → missingness; all-null `passing_epa` → missingness; paired-exclusion arithmetic) — no mutable upstream release count appears in any behavioral contract.

### A5. Registry

`nflreadpy_qb_validation.allowed_fields` extends with the three weekly columns, rosters `position`, and the four 1b columns. `nflreadpy_qb_context` byte-untouched; F33 wall unchanged; pbp pins NOT extended.

---

## Part B — D2a contract, universe, attrition

### B1. Public contract pin

```
build_study_matrix(
    sources: Mapping[str, Any],            # the seven D1 dataset states
    *,
    registration: dict[str, Any],          # a real dict, matching the shipped gate's
                                           # build_registration contract (R3-H1)
    expected_registration_hash: str,       # exact plain str
) -> dict[str, Any]
```

Boundary order, pinned: (1) `require_registration_hash(registration, expected_registration_hash)` (`registration.py:42` — F7/F23 mechanics reused); (2) **the seven-dataset F1 gate** — `load_validation_sources` semantics over the updated `VALIDATION_DATASETS`: state status, raw-snapshot presence, source timestamp, parser version, completeness flags — a handcrafted frame without D1 provenance refuses here; (3) F14 shape + F15 column validation per dataset; (4) all computation on defensive copies. The only claim withdrawn is **object identity**; source provenance IS enforced, by the F1 gate.

### B2. Pre-cohort candidate universe (pinned, mechanical)

```
universe(t) = label_pool(t) ∪ roster_pool_QB(t−1) ∪ cohort(t)
  label_pool(t)       = player-ids with ≥1 qualifying REG game in season t, weekly position QB
  roster_pool_QB(t−1) = player-ids with ≥1 season-t−1 REG roster row (any status), roster position QB
  cohort(t)           = ≥1 career dropbacks_proxy through t−1 AND season t−1 roster presence   (UNCHANGED)
```

### B3. Two-axis classification

- **Eligibility axis:** `cohort_admitted` | `rookie_no_priors` | `cohort_ineligible_prior`.
  - `rookie_no_priors` pinned mechanical predicate (R2-H2): **no prior REG weekly row AND no prior REG roster row through t−1**. A t−1-rostered zero-stat QB is therefore `cohort_ineligible_prior`, never a rookie.
  - `cohort_ineligible_prior` carries `reasons`: ordered lossless list, pinned order `[zero_career_dropbacks, no_prior_roster_presence]`, every triggered reason present.
- **Target axis:** `target_evaluable` (≥1 qualifying REG game in t) | `no_target_season`.

### B4. Exact return schema

Flag law — stated as the **actual frozen scanner law** (`guards.py:108-121`, verified): `decision_supported=False` is required on the **root and every list-element mapping**; plain sub-mappings do not carry the field (and if one ever does, it must be exactly False). In this schema the field appears on: root, each `matrix` row, each `audit` row, each manifest `features` entry — and nowhere else.

```
{
  "matrix_version": "qb_validation_matrix.v1",           # literal
  "decision_supported": false,
  "matrix": [ { "player_id": str, "target_season": int,
                "eligibility": "cohort_admitted",         # exact field, always this literal here
                "target": "target_evaluable"|"no_target_season",
                "decision_supported": false,
                "<feature>": float|None ... exactly the manifest names } ... ],
  "manifests": { "h1"|"h2"|"h3"|"h4": {
                   "features": [ {"name": str, "lookback": "t1"|"career"|"static",
                                  "decision_supported": false} ... ] } },
  "attrition": { "<str(target_season)>": {
                   "counts": { "no_target_season": int, "rookie_no_priors": int,
                               "cohort_ineligible_prior": int,
                               "cohort_ineligible_unobserved": int },   # literal keys, explicit zeros
                   "audit": [ { "player_id": str, "target_season": int,
                                "eligibility": str, "target": str,
                                "outcome_class": str, "reasons": [str, ...],
                                "decision_supported": false } ... ] } },
  "coverage": { "target_seasons": [2016,2017,2018,2019,2020,2021,2022,2023,2024,2025],  # literal
                "rows_per_season": { "<str(season)>": int },     # counts MATRIX rows per target season
                "cpoe_non_qb_joins": { "<str(season)>": int } }, # r6/H2: the §A3 audit fact
}
```

**`cpoe_non_qb_joins` (r6, David-ratified 2026-07-20 — the §A3/S4 audit location).** For each target season t, the count of MATRIX rows whose t−1 CPOE join found a `season_summary` row whose `position` did not read QB — the case §A3 routes to null. Explicit zeros for all ten target seasons; keys exactly `rows_per_season`'s. It counts **only** the non-QB-position case: an ABSENT 1b row and a NULL `passing_cpoe` value are different missingness causes and are NOT counted here (that separation is the whole point of the fact). A plain sub-mapping carrying no player identity — the scanner-law flag placement of §B4 is unchanged.

**Total precedence rule (r7, closes R6-H1 — position is tested independently of value).** The three causes overlap, so the rule is stated exhaustively over the joined row: **(a)** no 1b row for (player_id, t−1) → **not counted**; **(b)** a joined row whose `position` does not read QB → **counted, regardless of whether its `passing_cpoe` is null or present** (position is evaluated without reading the value); **(c)** a joined QB-position row whose `passing_cpoe` is null → **not counted**. "Null does not count" therefore means case (c) only. In all three cases the emitted `cpoe` feature is null; the counter discriminates cause (b) — a real source-context fact about the join — from the ordinary absences (a) and (c).

**Audit totality pin (R3-B1 corrected):** `audit` contains **exactly the members of the three NON-COHORT outcome classes** — `rookie_no_priors`, `cohort_ineligible_prior`, `cohort_ineligible_unobserved`. `no_target_season` rows are cohort-admitted and live in `matrix` (with `target = no_target_season`), never in audit. Matrix ∪ audit = universe, disjoint — total classification with no re-derivation surface. **Count-source mapping (pinned):** `counts.no_target_season` = the number of matrix rows with `target = no_target_season`; the other three counts = their audit rows. GREEN may not duplicate a no-target row into audit to make a count come out. Deterministic ordering: `matrix` and `audit` sorted by (target_season, player_id); season keys ascending. Duplicate (player_id, target_season) anywhere → named refusal. Missing source season → named refusal, never a gap.

### B5. F28 law amendment — exact callable contract (authorized shipped-surface change)

Signature **unchanged**: `validate_attrition_classes(rows, attrition)`.

**Classified-row schema (pinned; R3-B2 minimum closure):** `{ player_id: str, season: int, eligibility: str, target: str, outcome_class: str, qualifying_games: int, reasons: list[str], decision_supported: False }` — the identity key is the **shipped D2 key `season`** (`qb_ppg_labels.py:677,783,837,885`), whose value for a classified row IS the target season; the D2a-internal `target_season` field maps to it one-to-one (**pinned join mapping:** D2a `target_season` ↔ D2/F28 `season`; no D2 schema migration is performed or authorized). `reasons` is `[]` except on the two `cohort_ineligible_*` classes; evaluable rows may carry `ppg`/`points_total` (existing label law); attrition rows may NEVER carry them (unchanged).

**Total (eligibility, target) → outcome_class mapping (pinned):**

| eligibility | target | outcome_class | games law |
|---|---|---|---|
| cohort_admitted | target_evaluable | `evaluable` | games > 0 required |
| cohort_admitted | no_target_season | `no_target_season` | games = 0 required |
| rookie_no_priors | target_evaluable | `rookie_no_priors` | games > 0 required |
| rookie_no_priors | no_target_season | **refused** `universe_membership_violation` — unreachable by construction (a rookie enters the universe only via label_pool) | — |
| cohort_ineligible_prior | target_evaluable | `cohort_ineligible_prior` | games > 0 required |
| cohort_ineligible_prior | no_target_season | `cohort_ineligible_unobserved` | games = 0 required |

`OUTCOME_CLASSES = ("evaluable", "no_target_season", "rookie_no_priors", "cohort_ineligible_prior", "cohort_ineligible_unobserved")`; `ATTRITION_CLASSES` = the last four. **Literal attrition count keys = exactly `ATTRITION_CLASSES`**, explicit zeros; each count equals its classified rows (existing mismatch refusal). The D5 report `attrition` block gains the two new keys. Both-ways games law per the table replaces the current single-axis invariant (`qb_ppg_labels.py:990-992`); mismatched axis/class/games combinations refuse `outcome_class_conflict`; unknown classes, duplicate player-seasons, malformed games, and metrics-on-attrition refusals all unchanged. **This section authorizes the scoped modification of shipped `validate_attrition_classes`, `OUTCOME_CLASSES`/`ATTRITION_CLASSES`, and their reinforcement rows** — landing only via Codex's behavioral RED (shipped-suite deltas flagged, r20 precedent) and slice-4 GREEN review.

**Post-fix sweep at ratification:** v8 §D2 outcome classes (line 37), §D3 rookie route (line 46), §D5 attrition block (line 80), F28's matrix row, package exports.

### B6. Ownership + handoff

D2a emits the final classification on both axes — on matrix rows and audit rows per §B4. D3 consumes verbatim, re-derives nothing. Pinned consistency gate: D3 joins the D2 label table on **(player_id, season)** — the shipped D2 key — with D2a's `target_season` supplying the `season` value per the §B5 join mapping; it asserts D2-label presence ⇔ the row's emitted `target = target_evaluable`; disagreement → named `classification_label_mismatch`.

### B7. Manifest ownership + consumption contract (restored from round 1 — R3-B3)

The four feature manifests are **module-owned, immutable, lookback-tagged declarations, declared exactly once in the D2a module**: H1/H2/H3 pairwise disjoint; **H4 composed mechanically from those same three declarations plus the two identity groups** (never a fourth independent list); the emitted `manifests` section serializes these declarations verbatim. **D3 consumes the declarations by import and never redeclares them**; F27's separate partition validator stays parked with D3 and will assert against these same objects. Recursive market-alias rejection applies to manifest names AND emitted matrix keys (`ktc`, `fc`, `dp`, `adp` — F3's existing law).

---

## Part C — Explicit non-changes

H2/H3/H4 manifests, the cohort law, qualifying-game law, attributed-team law at its v8 scope, fold/comparison/report laws, the H5 market lane, F27 (parked with D3), the market-data wall, every Engine A/B surface: untouched. This amendment adds pins and one explicitly-authorized shipped-surface change (§B5); it relaxes nothing else.

## Part D — Ratchet + sequence

**D.1 — ACTIVE sequence (r7 onward; David-worded 2026-07-20).** This revision adds one coverage counter to an already-built, already-CLEARed slice. There is **no second RED/GREEN slice cycle** and no ratchet change — the **17 XF** count is already at its post-GREEN value and stays there.

1. Codex proportionate exact-delta review of THIS revision (r7) → CLEAR.
2. David's ratification word is already given for the representation; on CLEAR the **v9 spec is re-frozen** with the new amendment SHA recorded in its Status block, and the new spec SHA ledgered.
3. **Claude implements the counter** in `build_study_matrix` + the S35 regression inside the existing single F2 scenario (packet row added, ratchet untouched at 17 XF).
4. **Codex reviews the implementation delta only** → CLEAR.
5. Sprint-closeout tollgate, then David's already-granted commit word covers the coherent tree; push, merge, registration, and study execution each remain separate David words.

**D.2 — HISTORICAL sequence (r1–r5, COMPLETED and superseded; retained for audit).**

1. ~~Codex round-4 exact-delta review of THIS revision → rounds to CLEAR.~~ *(completed: r5 ENUMERATED CLEAR, 2026-07-20 20:28.)*
2. ~~David ratifies → v8 patched per this amendment, re-frozen as **v9** (new SHA recorded).~~ *(completed: 20:36; v9 blob `8c6001f75c38…`.)*
3. ~~**Codex behavioral RED first:** updates the F2 fixture to §B1 and removes its strict-xfail, proving **1 F + 18 XF**; covers the §B5 F28 change (deltas flagged) and the §E seed list.~~ *(completed: 20:48, proven 1F+18XF.)*
4. ~~**Claude GREEN:** implements `build_study_matrix` + §B5, un-marks only F3 → **17 XF**; rounds to CLEAR at full product-contract rigor.~~ *(completed: GREEN ENUMERATED CLEAR 22:00, six axes, 17 XF; H2 excluded — this revision closes it.)*

## Part E — Canonical falsification seed list (complete, self-contained; supersedes all prior numbering)

S1. Paired per-feature null-week exclusion: fixture where `epa_per_dropback` and `sack_rate` denominators legitimately differ; both correct.
S2. `any_a` exactness: hand-computed line with sacks — source-signed `sack_yards_lost` REDUCES the numerator; a positive `sack_yards_lost` refuses; a negative-ANY/A season emitted unclamped.
S3. CPOE exactness: joined 1b value byte-equals the official summary fixture; no weekly-recomposed CPOE is produced anywhere.
S4. CPOE null routing: absent 1b row → null → missingness path, named; 1b non-QB `position` on the joined row → null + audit fact.
S5. `completion_pct`/`sack_rate` zero-denominator → null → missingness path, named.
S6. Semantic refusals: non-finite stat; negative count stat; `completions > attempts`; non-integral count — each refuses `stat_value_invalid`.
S7. Registration gate: absent doc / absent hash / mismatched hash → `preregistration_missing` via the existing gate; correct pair proceeds.
S8. F1-first boundary: a handcrafted frame with valid shape but no D1 state provenance refuses at the F1 gate, before F14 runs.
S9. Defensive copies: caller mutation of `sources` after the call cannot alter the returned artifact; no object-identity behavior anywhere.
S10. Universe totality: matrix ∪ audit = universe, disjoint, across fixtures covering all five outcome classes.
S11. Zero-dropback rostered no-target veteran → (cohort_ineligible_prior, no_target_season) → `cohort_ineligible_unobserved`, in audit, absent from matrix, no metrics.
S12. Rookie predicate: no-prior-weekly + no-prior-roster with target games → `rookie_no_priors`; t−1-rostered zero-stat QB with target games → `cohort_ineligible_prior` (never rookie).
S13. Unreachable combination: a presented (rookie_no_priors, no_target_season) row refuses `universe_membership_violation`.
S14. Reasons list: both-reasons ineligible veteran carries exactly `[zero_career_dropbacks, no_prior_roster_presence]` in pinned order.
S15. F28 two-axis law: each of the six table rows exercised — conforming rows accepted; wrong games count per the games law refuses `outcome_class_conflict`; attrition row with `ppg` refuses.
S16. Count keys: attrition counts carry exactly the four literal keys with explicit zeros; a stale/extra key refuses.
S17. Matrix-row axes: every matrix row carries `eligibility="cohort_admitted"` + a valid `target`; D3-side consistency gate refuses `classification_label_mismatch` on a mismatch fixture.
S18. Coverage: target seasons exactly 2016–2025 with 2024 present; a missing source season refuses, never gaps; `rows_per_season` counts matrix rows.
S19. As-of law: any season-t value on a feature path (weekly, career aggregate, team totals, 1b CPOE joined at t) refuses.
S20. H1 all-teams aggregation: a traded player's H1 features sum across both stints; H2 share/`team_proe` use the attributed team only.
S21. F15 on each newly pinned column individually (three weekly, rosters `position`, four 1b) → `manifest_column_missing`, fail-closed.
S22. Registry wall: `nflreadpy_qb_context` byte-identical before/after; new columns appear only in the validation definition.
S23. Scanner law: emitted artifact passes `scan_banned_language`; a fixture matrix row missing `decision_supported` refuses `decision_supported_missing_on_model`.
S24. Deterministic ordering + duplicate refusal: shuffled input yields byte-identical sorted output; duplicate (player_id, target_season) refuses.
S25. Market-alias rejection: a manifest name or emitted matrix key containing `ktc`/`fc`/`dp`/`adp` refuses recursively (manifests AND matrix).
S26. Manifest ownership: H1/H2/H3 pairwise disjoint on the declared objects; H4 = exactly their union + the two identity groups, composed from the same declarations; a mutated/redeclared manifest fixture refuses or fails the assertion.
S27. Rush-TD aggregation order: all-position team rush-TD totals computed BEFORE the QB filter; zero team-TD denominator → null → named missingness route.
S28. Roster rule: any-REG-row/any-status counts as t−1 roster presence; a postseason-only roster row never qualifies.
S29. No age cliff: a 41+ player-season passes cohort admission unimpeded; no age constant appears on any eligibility or feature path (age enters only as the H4 continuous feature).
S30. Draft join: a TRIAGE-rejected draft pair never becomes imputed H4 capital; UDFA constants appear only after the F34 miss proof.
S31. Boundary hardening: exact-plain scalar-subclass normalization on every public input; `MemoryError`/`RecursionError`/`SystemError` preserved through every broad catch (slice-3 law, asserted on the new surfaces).
S32. Null-week weekly fields, parameterized over exactly `{attempts, completions, sacks_suffered, passing_tds, passing_interceptions, sack_yards_lost, passing_yards}`: a null in any of the seven refuses `stat_value_invalid` (never silently skipped by a dataframe sum); the paired `passing_epa` null route stays the sole exception.
S33. 1b duplicate refusal: a duplicated `season_summary` (player_id, season) pair refuses `duplicate_player_season` before any join.
S34. Shipped-key join: classified rows carry `season` (shipped D2 key); a `target_season`-keyed row presented to `validate_attrition_classes` refuses on the missing pinned key; the D3 gate joins on (player_id, season).
S35. `cpoe_non_qb_joins` (r6; overlap case added r7): parameterized over the total precedence rule — (a) absent 1b row → count 0, `cpoe` null; (b) joined non-QB row with a PRESENT `passing_cpoe` → counted, `cpoe` null; (b′) **joined non-QB row whose `passing_cpoe` is ALSO null → still counted** (position is tested independently of value — the overlap case); (c) joined QB-position row with null `passing_cpoe` → count 0, `cpoe` null. Each increments exactly its own target season; all ten seasons present with explicit zeros; keys identical to `rows_per_season`; the artifact still passes `scan_banned_language`.
