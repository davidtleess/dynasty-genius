# Subsystem 1 — NFL Mock-Draft Consensus Aggregation (Design Spec)

- Status: **v4 — targeted pre-T1 design spot-check patch (3 independent lanes; 8-item union + 2 David rulings); awaiting round-4 dual-CLEAR → David commit authorization (NO RED until CLEAR + David go)**
- Authorship: Claude Code authors; Gemini governance-reviews; Codex technical-reviews
- Date: 2026-06-20
- Governance: constitution 1.0.0, north-star 1.0.0, operating-loop 1.0.0, code-hygiene 1.0.0
- Sequence: step 3 (W5b ✅ → Task B ✅ → **Subsystem 1**)
- Substrate: research `docs/strategies/Mock Agg deep-research-report.md`; brief `2026-05-28-...research-brief.md`; reconciliation `2026-05-28-increment-a-reconciliation-and-go-forward.md`

## v4 changelog (targeted pre-T1 design spot-check; 3 independent lanes converged; supersedes conflicting v3 framing)
David directed a rigorous 3-opinion spot-check before T1. Each agent posted an independent, evidence-cited risk list; the union is 8 items, resolved below. **Where this conflicts with v3 prose (esp. §13.6), v4 wins.**
- **U1 — math/policy boundary (Claude C1):** the canonical engine returns **raw `iqr`/`mad`/counts/`staleness_days` ONLY**. It does **NOT** compute `disagreement_flag` and applies **no threshold** — the `IQR > 6` dispersion flag/block is **consumer POLICY** (S1 §9; S4 keeps its own `dispersion_threshold` param at `backtest_mock_draft.py:458/:529`). Baking `6` into "pure math" contradicted the v3 "extract MATH, not POLICY" resolution and risked silent divergence if S4's default ever changed. (§7, §9)
- **U2 — S1 import isolation (Claude C2):** `src/dynasty_genius/mock_consensus/` is added to the S4 audit AST/import-isolation scan roots with a reverse-import/cycle guard barring it from importing `backtest_mock_draft` / Engine A/B / scoring; the **only** allowed S1↔S4 edge is S4 importing the pure mock-consensus math (one-directional). The full `test_subsystem_4_audit.py` runs against the T5 surface **before** the T5 RED. `backtest_mock_draft.py` is **not** byte-locked (verified: byte-baselines cover only Phase 10/11/12 + S3 `college_prospect_identity.py`); the isolation/AST guards are the live concern; any scan-root amendment is David-authorized. (§11)
- **U3 — analyst-identity normalization (Claude C3):** the `analyst` field MUST be a **curator-guaranteed canonical string**; blank/malformed `analyst` is rejected (drop-record). The `n_unique_analysts >= 5` trust gate counts distinct canonical strings; fuzzy analyst identity is out of scope (a future governed mapping, never implicit). (§3, §5)
- **U4 — Top-12 gate paradox (Gemini G1 / Codex #1; Claude converged):** the match-rate gate's Top-12 arm evaluates the **raw latest-eligible ranked rows (by projected pick) BEFORE the identity join**, so an unresolved consensus-top-12 prospect still trips the gate. A resolved-only ranking would let a missing top prospect silently bypass. (§6)
- **U5 — staleness cutoff (Codex #2; David ruling):** exact-pick eligibility adds **`staleness_days <= 30`** (30-day cutoff; pre-draft mock cycle is weeks-long, retains a full refresh cycle). (§9, §13.7)
- **U6 — `internal_diagnostic` structural (Codex #4):** `internal_diagnostic` is a **structural boolean on the T4 consensus record**, set at aggregation — not a T6 serialization-only marker. (§10)
- **U7 — MAD diagnostic-only (Claude C4):** `mad` is computed + tested but **no policy consumes it** this increment; documented as surfaced-diagnostic-only. (§7)
- **U8 — artifact-leakage directory (Gemini G2; David ruling):** the overlay artifact writes to **`app/data/mock_consensus/`** (neutral; mock-draft consensus is projected NFL draft capital, NOT a market price → `market_overlay/` would mislabel it), never beside core PVO files in `app/data/valuation/`; a write-isolation test proves it never touches `app/data/valuation/*_latest.json`. (§10, §13.8)

## v3 changelog (resolves round-2 review; cockpit-converged)
- Codex defect 1 (count-basis) — RESOLVED via "extract math, not policy" (both lanes CONCUR): the canonical engine owns the shared consensus MATH only; the abstention POLICY lives per-consumer. **S1 gates on `n_unique_analysts`** (reconciliation §40, S1-scoped); **S4 keeps its `n_sources` gate** (its own backtest spec; byte-unchanged; tests pass). Gemini governance CLEARED this framing; live S1 enforces the stricter analyst rule, the S4 backtest harness keeps its looser source bound to maximize evaluation N.
- Codex defect 2 — `projected_pick_median` preserves the **raw float median** (e.g. 32.5); `round_half_up` applies ONLY when mapping a median to `round_tier` (matches S4 `:429/:835`, test `:210`).
- Codex defect 3 — alias-bridge hits are resolved through the loaded registry and constructed as `ConfirmedProspectUuid` (rejects unknown/provisional/deprecated, `:448`); only confirmed targets feed aggregation.
- Dispersion cutoff (§13.6) — **IQR > 6 picks** (S4 default `dispersion_threshold=6`, contract-tested) as BOTH `disagreement_flag=True` AND the exact-pick hard-block (Gemini §13.2). Replaces the v2 IQR>15 placeholder. *(v3 framing; **superseded by v4 U1** — the `disagreement_flag` and the `>6` threshold are consumer POLICY, not part of the canonical pure math.)*

## v2 changelog (resolves v1 review)
- Codex F1: `draft_class` added to the row contract (required + validated).
- Codex F2: added §3b concrete **curated-row → `NormalizedCollegeProspectRow` adapter**; §6 corrected to the real S3 API (`compute_match_key(normalized_name, position_group, draft_class)`; school = `score_candidate` bonus, not an exact-key component; scorers take typed rows).
- Codex F3: removed the S3-mint "alias-table→fuzzy" language; S1 uses a **read-only resolver** against the confirmed registry (+ optional read-only alias-bridge lookup); S1 never mints/writes registry/bridge state.
- Codex F4 (David ruling): **extract canonical aggregator into S1; rewire S4 to consume it** (§7b).
- Codex F5: explicit `projection_status` (`exact_pick`/`round_only`/`udfa`) + round-only/UDFA handling (§3/§8).
- Codex F6: deterministic latest-per-analyst tie-break — `published_date` → `source_snapshot_id` → `raw_row_hash` (not free-string `mock_version`).
- Codex F7: pick-max aligned to S4's shared `DRAFT_PICK_MAX` (257), year-provenanced.
- Codex F8 + §13: open decisions resolved below via David + Gemini rulings.

## 1. Scope (David-approved: "engine + manual input contract"; + F4 extraction)

IN: pure consensus-aggregation engine; fail-closed manual-curated input contract; read-only S3 identity join; overlay-only artifact; **extraction of the canonical aggregator now consumed by both S1 and S4** (F4 ruling = "extract canonical → rewire S4 now"), with S4 tests proving no behavior change.

OUT/DEFERRED: S2 live scrapers (no-go); consumer wiring into pick-valuation/Trade Lab/any David-facing surface (deferred to ~Dec 2026–Apr 2027 pending S4 incremental-value proof); any model-training use (zero mock imports into Engine A/B training); live-signal concerns (engine is fixture-testable).

## 2. Research verdict (carried, not relitigated)
S1 = conditional GO, **manual-first**; bucketed consensus with abstention; **no GTM/EDP-level claim**; exact pick is **internal diagnostic, never David-facing** until S4 MAE supports it.

## 3. Input contract (manual-curated normalized rows)
Version-controlled curated JSON (the file IS the snapshot). Row fields:
```
source_id, source_name, analyst, mock_version,
published_date (ISO; primary recency key),
source_snapshot_id, raw_row_hash, parse_status,
source_type ("mock" | "big_board"),
prospect_name_raw, position_raw, school_raw, draft_class (int, REQUIRED),   # F1
projected_pick (int|null), projected_round (int|null), nfl_team (str|null),
projection_status ("exact_pick" | "round_only" | "udfa"),                    # F5
source_rank (optional)
```
`analyst` (U3) MUST be a **curator-guaranteed canonical string** — one stable spelling per real analyst (the curator owns canonicalization; S1 does no fuzzy analyst matching). This is load-bearing: the `n_unique_analysts` trust gate (§9) counts distinct `analyst` strings, so a non-canonical duplicate ("Dan" vs "Daniel Jeremiah") would mis-count and could wrongly clear the `>= 5` exact-pick gate.

Two-stage fail-closed validation (Task-2 loader pattern): structural schema → per-row semantic. Reject/quarantine (drop-record w/ reason, never silent): missing `draft_class`; **blank/malformed `analyst` (U3)**; `source_type != "mock"`; `projection_status="exact_pick"` with null/out-of-range `projected_pick` (`1..DRAFT_PICK_MAX`); `round_only` with null/out-of-range `projected_round` (`1..7`); `udfa` carrying a pick; malformed dates; duplicate `raw_row_hash`.

## 3b. Curated-row → NormalizedCollegeProspectRow adapter (F2)
A pure adapter builds the typed S3 input the resolver requires: maps `prospect_name_raw`→name, `position_raw`→`position_group`, `school_raw`→`current_school`, `draft_class`, and synthesizes S3 provenance (`source`, `source_record_id` from `source_id`+`raw_row_hash`, `source_snapshot_id`, `id_provenance`) per `NormalizedCollegeProspectRow` (`src/dynasty_genius/identity/college_prospect_identity.py:50`). Adapter is read-only; it constructs an in-memory typed row, never writes registry/bridge.

## 4. Source-type guard (F-prior)
`big_board` rows are talent rankings, not landing spots → **excluded** from projected-capital aggregation (hard gate, explicit reason). Only `mock` rows aggregate.

## 5. Latest-eligible-pick-per-analyst dedup (F6)
One latest mock per analyst: order by `published_date`, then `source_snapshot_id`, then `raw_row_hash` (fully deterministic; `mock_version` is descriptive only). `n_unique_analysts` = distinct **canonical** `analyst` strings (curator-guaranteed, §3 / U3); `n_sources` = distinct publications used.

## 6. Identity join — read-only resolver (F2/F3)
For each curated mock prospect: build the typed row (§3b) → `normalize_name` → `compute_match_key(normalized_name, position_group, draft_class)` (`college_prospect_identity.py:191`) → look up confirmed `RegistryEntry`(s) by match_key in the loaded `CollegeProspectRegistry` (`load_registry`) → for ambiguity/fuzzy, `score_candidate`/`surface_review_candidates` (`:297/:356`) over typed rows (school contributes as a **scoring bonus**, not an exact-key component, `:328`) → **human-review queue** for low-confidence; **never auto-match common-name collisions**; transfers = soft disambiguator. Optional **read-only** alias-bridge lookup `(match_key, source_record_id)→uuid` via `load_bridge` if present; the bridge target (a string) MUST be resolved through the loaded registry and constructed as a `ConfirmedProspectUuid` (`:448`, which rejects unknown/provisional/deprecated) — an unresolvable bridge target is treated as no-match, not a silent accept (Codex defect 3). S1 **mints nothing, writes no registry/bridge state**. Only `ConfirmedProspectUuid` matches feed aggregation.

**Match-rate fail-closed gate (Gemini §13.1 ruling; U4 pre-join fix):** abstain for the affected scope if **>20% of consensus mock prospects unresolved OR any consensus Top-12 prospect unresolved** (a 1st-round consensus rookie failing to join fatally compromises artifact integrity).

**U4 — the Top-12 arm must evaluate the RAW latest-eligible ranked rows (ranked by projected pick) BEFORE the identity join**, NOT a resolved-only ranking. Rationale: an unresolved prospect has no `ConfirmedProspectUuid` and therefore no post-join consensus row — if the Top-12 ranking were built only from resolved rows, a missing top-12 prospect would silently vanish from the very gate meant to catch it (the paradox all three lanes flagged). The gate ranks by projected pick over raw eligible rows, marks which top-12 entries failed to resolve, and abstains if any did. The `>20%` arm is computed over the full eligible-prospect set (resolved / total eligible).

## 7. Aggregation methodology (canonical engine)
Per joined prospect, over latest-per-analyst eligible projections:
- `projected_pick_median` — outlier-robust median (NOT mean), `min`, `max`, over `exact_pick` rows. **Preserve the raw float median** (e.g. 32.5); `round_half_up` applies ONLY when mapping a median to `round_tier` (S4 parity, `backtest_mock_draft.py:429/835`).
- Dispersion: **raw `IQR` and `MAD` are computed and surfaced by the canonical math** (U1). The canonical math applies **no threshold and emits no `disagreement_flag`** — the `IQR > 6` flag/block is **consumer POLICY** (S1 §9 derives it; S4 keeps its own `dispersion_threshold` param). **`MAD` is diagnostic-only (U7): computed + tested, but no abstention rule or flag consumes it this increment** (all dispersion gating keys on `IQR`).
- Canonical returns: `median` (raw float), `min`, `max`, `iqr` (raw), `mad` (raw, diagnostic-only), `n_sources`, `n_unique_analysts`, `staleness_days`. **No `disagreement_flag` in the canonical return** (U1).
- `round_tier` (primary; §8). `round_only` rows contribute to round-tier voting (median of `projected_round`); `udfa` rows count toward the UDFA tier; neither contributes a pick number.
- Pick bounds via the **shared `DRAFT_PICK_MAX`** (currently 257), year-provenanced (F7).

### 7b. S1↔S4 extraction boundary (F4 ruling + count-basis convergence: "extract MATH, not POLICY")
Extract ONLY the shared consensus **math** — float-median, **raw IQR/MAD**, `n_sources`, `n_unique_analysts`, `staleness_days` — into a single pure canonical module. The module is **threshold-free (U1)**: it computes raw dispersion statistics but applies **no dispersion threshold and emits no `disagreement_flag`**. **Both the abstention policy AND the dispersion threshold/`disagreement_flag` are NOT extracted** — they stay per-consumer:
- **S1** applies the **analyst-based** policy (§9; reconciliation §40).
- **S4** keeps its **`n_sources`-based** policy AND its own **`dispersion_threshold` parameter** (`backtest_mock_draft.py:458` default `6`, applied as `iqr <= dispersion_threshold` at `:529`) **byte-unchanged** — its `aggregate_per_prospect`/`ProspectConsensus` delegate to the canonical math for the **raw statistics only** (median/iqr/mad/min/max), then apply S4's own threshold/policy. The canonical math does NOT carry S4's threshold. S4 contract tests must pass **unchanged** (behavior-preserving; verified by a dedicated parity RED + delegation spy). Rationale (cockpit-converged, Gemini-CLEARED): the reconciliation analyst-rule governs S1's live consensus; the S4 backtest harness is an independently-specified evaluation subsystem that legitimately uses a looser source bound to maximize N. Pure functions only; no I/O in the core.

## 8. Round-tier bucketing (Gemini §13.5 ruling — 12-team SF)
`round_tier` ∈ { R1.early (picks 1–4), R1.mid (5–8), R1.late (9–12), R2, R3, Day3 (R4–7), UDFA }. Round-tier is the **primary** output; exact pick is secondary + internal-only (§9).

## 9. Abstention gates — S1 POLICY (analyst-based; NOT shared with S4)
This is S1's own abstention policy (reconciliation §40), applied by the S1 consumer over the canonical math — S4 has its own separate `n_sources` policy (§7b).
This consumer layer derives `disagreement_flag = (iqr > 6)` from the canonical raw `iqr` (U1 — the threshold `6` lives HERE, in S1 policy, not in the canonical math).
- `n_unique_analysts < 3` → **abstain entirely**.
- `3 ≤ n_unique_analysts ≤ 4` → **round-tier only**, never exact pick.
- exact `projected_pick_median` only when **ALL of**: `n_unique_analysts ≥ 5` **AND** `IQR ≤ 6` (S1 policy threshold; `IQR > 6` HARD-BLOCKS exact-pick emission even at n≥5, Gemini §13.2) **AND** `staleness_days ≤ 30` (U5 / §13.7 — David ruling). Emitted exact pick always carries `internal_diagnostic=True`, never David-facing.
- Plus the §6 match-rate gate (incl. the U4 pre-join Top-12 arm).

## 10. Output artifact contract
Write-isolated overlay artifact at **`app/data/mock_consensus/mock_consensus_<run>.json` + `_latest`** (U8 / §13.8 — David ruling; a dedicated quarantine directory, NOT `app/data/valuation/` beside core PVO files, and deliberately NOT named `market_overlay/` since mock-draft consensus is projected NFL draft capital, not a market price). A **write-isolation test proves the writer never touches `app/data/valuation/*_latest.json`** (or any path outside `app/data/mock_consensus/`). NOT consumed by any model/PVO/trade/David-facing path this increment. Recursive `decision_supported=False`; stacked-inference caveats; banned-language clean.

`internal_diagnostic` is a **structural boolean on the T4 consensus record** (U6) — set at aggregation time, carried through to serialization. It is NOT a serialization-only marker added at write time; the T4 data contract itself either carries `internal_diagnostic=True` on an emitted exact pick or suppresses the exact pick entirely. T6 serializes the already-marked record.

## 11. Governance + robustness boundary
Overlay/inference-only; **zero Engine-A/B import into the aggregator/artifact** (guard test). `decision_supported=False` recursively; no banned David-facing patterns. Robustness: API-misuse → fail loud; data-corruption (malformed rows) → fail closed + drop-record; semantic/range → producer-validated. Local-first; frontend HOLD; NOISE_BAND untouched.

**U2 — S1↔S4 import isolation.** The only sanctioned cross-module edge is S4 (`backtest_mock_draft.py`) importing the **pure** mock-consensus math (one-directional). `src/dynasty_genius/mock_consensus/` is added to the S4 audit's AST/import-isolation scan roots (`tests/contract/test_subsystem_4_audit.py`, `AST_AUDIT_SCAN_ROOTS`) with a **reverse-import/cycle guard** barring `mock_consensus/` from importing `backtest_mock_draft`, Engine A/B, or scoring — closing the currently-ungoverned cycle (the audit's `BANNED_IMPORT_MODULES` would not otherwise detect a future `mock_consensus → backtest_mock_draft` edge, since `mock_consensus/` is not yet a scan root). The **full `test_subsystem_4_audit.py` is run against the T5 surface BEFORE the T5 RED**. Note (verified): `backtest_mock_draft.py` is **not** under any byte-baseline (`INVIOLATE_BASELINE` = Phase 10/11/12; `S3_INVIOLATE` = `college_prospect_identity.py` only) — so T5's edit trips no byte-lock; the isolation/AST guards are the live concern. Any AST-scan-root amendment is David-authorized.

## 12. Acceptance criteria & falsification matrix (seeds RED)
AC: deterministic robust-median aggregation (canonical, shared with S4 w/ S4 contracts intact); round-tier primary (§8 boundaries); abstention exactly §9 (incl. dispersion hard-block); big-board exclusion; latest-per-analyst deterministic dedup; read-only fail-closed S3 join + match-rate gate; projection_status handling; overlay-only + decision_supported=False + exact-pick internal-only; no Engine-A/B import; S4 tests unchanged.

Falsification rows: nominal multi-analyst exact-pick prospect; <3→abstain; 3–4→round-tier-only (no exact pick); ≥5 tight + fresh→exact pick w/ internal_diagnostic=True; ≥5 **wide dispersion (IQR>6)→exact pick hard-blocked** + `disagreement_flag` derived in S1 policy (NOT canonical math, U1); **≥5 tight but stale (`staleness_days` 31→exact suppressed; 30→exact allowed) — U5 boundary**; big_board excluded; duplicate analyst versions→latest only (deterministic tie-break); **blank/malformed `analyst`→reject (U3)**; round_only→round-tier vote; udfa→UDFA tier; missing draft_class→reject; exact_pick w/ null/out-of-range pick→reject; `>20%` unresolved or **any RAW-pre-join Top-12 unresolved→abstain (U4)**; empty input→abstain (no crash); even-count median→**raw float preserved** (e.g. 32.5; `round_half_up` only when mapping to `round_tier`); **canonical math returns NO `disagreement_flag` (U1); `mad` computed but unconsumed/diagnostic-only (U7)**; **`internal_diagnostic` is a structural field on the T4 record, not a serialization add (U6)**; **artifact writes only under `app/data/mock_consensus/`, never `app/data/valuation/` (U8)**; S4 `aggregate_per_prospect` parity (delegation spy + characterization across abstain / round_tier_only / exact_pick / high-IQR) after rewire; **full `test_subsystem_4_audit.py` green with `mock_consensus/` in scan roots + reverse-import guard (U2)**.

## 13. Open decisions — RESOLVED
- §13.1 match-rate (Gemini): >20% unresolved OR any Top-12 unresolved → abstain. ✅
- §13.2 dispersion (Gemini + Codex): wide dispersion hard-blocks exact pick even at n≥5. ✅ Numeric cutoff = **IQR > 6 picks** (S4 default `dispersion_threshold=6`, contract-tested; Codex round-2). ✅
- §13.3 input format (Claude): curated **JSON** file (not CSV `manual_export_adapter`); cockpit confirm.
- §13.4 median representation (Codex defect 2): **preserve raw float median**; `round_half_up` applies ONLY when mapping a median to `round_tier` (S4-consistent). ✅
- §13.5 round-tiers (Gemini): R1.early 1–4 / R1.mid 5–8 / R1.late 9–12 / R2 / R3 / Day3 R4–7 / UDFA. ✅
- §13.6 (Codex round-2; **amended by v4 U1**): the `IQR > 6` dispersion cutoff stands, but `disagreement_flag` and the `> 6` threshold are **CONSUMER POLICY** (S1 §9; S4's `dispersion_threshold`), **NOT** part of the canonical pure math. The canonical math returns raw `iqr` only. ✅

### v4 additions (targeted pre-T1 spot-check — 3-lane union + David rulings)
- §13.7 staleness (Codex #2; **David ruling**): exact-pick eligibility requires `staleness_days <= 30` (30-day cutoff). ✅
- §13.8 artifact directory (Gemini G2; **David ruling**): write to `app/data/mock_consensus/` (neutral; not `app/data/valuation/`, not `market_overlay/`); write-isolation test enforces. ✅
- §13.9 analyst normalization (Claude C3): `analyst` is a curator-guaranteed canonical string; blank/malformed → reject; no fuzzy analyst identity. ✅
- §13.10 Top-12 gate (Gemini G1 / Codex #1 / Claude): the Top-12 arm evaluates RAW latest-eligible ranked rows BEFORE the identity join. ✅
- §13.11 `internal_diagnostic` (Codex #4): structural boolean on the T4 consensus record, not a T6 serialization marker. ✅
- §13.12 MAD (Claude C4): computed + tested, diagnostic-only; no policy consumes it this increment. ✅
- §13.13 import isolation (Claude C2): `mock_consensus/` added to S4-audit AST scan roots + reverse-import/cycle guard; full S4 audit run against the T5 surface before T5 RED; any scan-root amendment David-authorized. ✅

## 14. Build sequence (post-approval only)
round-4 dual-CLEAR (Codex technical + Gemini governance) on this v4 spot-check patch → David commit authorization → Codex RED → Claude GREEN per task (incl. the S4-rewire parity task w/ the U2 audit run before its RED) → dual-CLEAR → David-confirmed commit → zero-divergence audit. No RED before dual-CLEAR + David's go.
