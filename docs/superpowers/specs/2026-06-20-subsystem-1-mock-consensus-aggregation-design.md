# Subsystem 1 — NFL Mock-Draft Consensus Aggregation (Design Spec)

- Status: **v3 — count-basis divergence resolved (cockpit-converged "extract math, not policy"); awaiting round-3 dual-CLEAR → David final approval (NO RED until both)**
- Authorship: Claude Code authors; Gemini governance-reviews; Codex technical-reviews
- Date: 2026-06-20
- Governance: constitution 1.0.0, north-star 1.0.0, operating-loop 1.0.0, code-hygiene 1.0.0
- Sequence: step 3 (W5b ✅ → Task B ✅ → **Subsystem 1**)
- Substrate: research `docs/strategies/Mock Agg deep-research-report.md`; brief `2026-05-28-...research-brief.md`; reconciliation `2026-05-28-increment-a-reconciliation-and-go-forward.md`

## v3 changelog (resolves round-2 review; cockpit-converged)
- Codex defect 1 (count-basis) — RESOLVED via "extract math, not policy" (both lanes CONCUR): the canonical engine owns the shared consensus MATH only; the abstention POLICY lives per-consumer. **S1 gates on `n_unique_analysts`** (reconciliation §40, S1-scoped); **S4 keeps its `n_sources` gate** (its own backtest spec; byte-unchanged; tests pass). Gemini governance CLEARED this framing; live S1 enforces the stricter analyst rule, the S4 backtest harness keeps its looser source bound to maximize evaluation N.
- Codex defect 2 — `projected_pick_median` preserves the **raw float median** (e.g. 32.5); `round_half_up` applies ONLY when mapping a median to `round_tier` (matches S4 `:429/:835`, test `:210`).
- Codex defect 3 — alias-bridge hits are resolved through the loaded registry and constructed as `ConfirmedProspectUuid` (rejects unknown/provisional/deprecated, `:448`); only confirmed targets feed aggregation.
- Dispersion cutoff (§13.6) — **IQR > 6 picks** (S4 default `dispersion_threshold=6`, contract-tested) as BOTH `disagreement_flag=True` AND the exact-pick hard-block (Gemini §13.2). Replaces the v2 IQR>15 placeholder.

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
Two-stage fail-closed validation (Task-2 loader pattern): structural schema → per-row semantic. Reject/quarantine (drop-record w/ reason, never silent): missing `draft_class`; `source_type != "mock"`; `projection_status="exact_pick"` with null/out-of-range `projected_pick` (`1..DRAFT_PICK_MAX`); `round_only` with null/out-of-range `projected_round` (`1..7`); `udfa` carrying a pick; malformed dates; duplicate `raw_row_hash`.

## 3b. Curated-row → NormalizedCollegeProspectRow adapter (F2)
A pure adapter builds the typed S3 input the resolver requires: maps `prospect_name_raw`→name, `position_raw`→`position_group`, `school_raw`→`current_school`, `draft_class`, and synthesizes S3 provenance (`source`, `source_record_id` from `source_id`+`raw_row_hash`, `source_snapshot_id`, `id_provenance`) per `NormalizedCollegeProspectRow` (`src/dynasty_genius/identity/college_prospect_identity.py:50`). Adapter is read-only; it constructs an in-memory typed row, never writes registry/bridge.

## 4. Source-type guard (F-prior)
`big_board` rows are talent rankings, not landing spots → **excluded** from projected-capital aggregation (hard gate, explicit reason). Only `mock` rows aggregate.

## 5. Latest-eligible-pick-per-analyst dedup (F6)
One latest mock per analyst: order by `published_date`, then `source_snapshot_id`, then `raw_row_hash` (fully deterministic; `mock_version` is descriptive only). `n_unique_analysts` = distinct analysts; `n_sources` = distinct publications used.

## 6. Identity join — read-only resolver (F2/F3)
For each curated mock prospect: build the typed row (§3b) → `normalize_name` → `compute_match_key(normalized_name, position_group, draft_class)` (`college_prospect_identity.py:191`) → look up confirmed `RegistryEntry`(s) by match_key in the loaded `CollegeProspectRegistry` (`load_registry`) → for ambiguity/fuzzy, `score_candidate`/`surface_review_candidates` (`:297/:356`) over typed rows (school contributes as a **scoring bonus**, not an exact-key component, `:328`) → **human-review queue** for low-confidence; **never auto-match common-name collisions**; transfers = soft disambiguator. Optional **read-only** alias-bridge lookup `(match_key, source_record_id)→uuid` via `load_bridge` if present; the bridge target (a string) MUST be resolved through the loaded registry and constructed as a `ConfirmedProspectUuid` (`:448`, which rejects unknown/provisional/deprecated) — an unresolvable bridge target is treated as no-match, not a silent accept (Codex defect 3). S1 **mints nothing, writes no registry/bridge state**. Only `ConfirmedProspectUuid` matches feed aggregation.

**Match-rate fail-closed gate (Gemini §13.1 ruling):** abstain for the affected scope if **>20% of consensus mock prospects unresolved OR any consensus Top-12 prospect unresolved** (a 1st-round consensus rookie failing to join fatally compromises artifact integrity).

## 7. Aggregation methodology (canonical engine)
Per joined prospect, over latest-per-analyst eligible projections:
- `projected_pick_median` — outlier-robust median (NOT mean), `min`, `max`, over `exact_pick` rows. **Preserve the raw float median** (e.g. 32.5); `round_half_up` applies ONLY when mapping a median to `round_tier` (S4 parity, `backtest_mock_draft.py:429/835`).
- Dispersion: **IQR** (+ MAD) surfaced; **IQR > 6 picks** sets `disagreement_flag=True` (S4 default).
- `n_sources`, `n_unique_analysts`, `staleness_days`, `disagreement_flag`.
- `round_tier` (primary; §8). `round_only` rows contribute to round-tier voting (median of `projected_round`); `udfa` rows count toward the UDFA tier; neither contributes a pick number.
- Pick bounds via the **shared `DRAFT_PICK_MAX`** (currently 257), year-provenanced (F7).

### 7b. S1↔S4 extraction boundary (F4 ruling + count-basis convergence: "extract MATH, not POLICY")
Extract ONLY the shared consensus **math** (float-median, IQR/MAD, `n_sources`, `n_unique_analysts`, staleness, dispersion) into a single pure canonical module. **Abstention policy is NOT extracted** — it stays per-consumer:
- **S1** applies the **analyst-based** policy (§9; reconciliation §40).
- **S4** keeps its **`n_sources`-based** policy (`backtest_mock_draft.py:420/493`) **byte-unchanged** — its `aggregate_per_prospect`/`ProspectConsensus` delegate to the canonical math for the statistics but retain their own gate. S4 contract tests must pass **unchanged** (behavior-preserving; verified by a dedicated parity RED). Rationale (cockpit-converged, Gemini-CLEARED): the reconciliation analyst-rule governs S1's live consensus; the S4 backtest harness is an independently-specified evaluation subsystem that legitimately uses a looser source bound to maximize N. Pure functions only; no I/O in the core.

## 8. Round-tier bucketing (Gemini §13.5 ruling — 12-team SF)
`round_tier` ∈ { R1.early (picks 1–4), R1.mid (5–8), R1.late (9–12), R2, R3, Day3 (R4–7), UDFA }. Round-tier is the **primary** output; exact pick is secondary + internal-only (§9).

## 9. Abstention gates — S1 POLICY (analyst-based; NOT shared with S4)
This is S1's own abstention policy (reconciliation §40), applied by the S1 consumer over the canonical math — S4 has its own separate `n_sources` policy (§7b).
- `n_unique_analysts < 3` → **abstain entirely**.
- `3 ≤ n_unique_analysts ≤ 4` → **round-tier only**, never exact pick.
- exact `projected_pick_median` only at `n_unique_analysts ≥ 5` + acceptable staleness + tight dispersion — and **IQR > 6 picks HARD-BLOCKS exact-pick emission even at n≥5** (Gemini §13.2). Emitted exact pick always carries `internal_diagnostic=True`, never David-facing.
- Plus the §6 match-rate gate.

## 10. Output artifact contract
Write-isolated overlay artifact (`app/data/valuation/mock_consensus_<run>.json` + `_latest`); NOT consumed by any model/PVO/trade/David-facing path this increment. Recursive `decision_supported=False`; stacked-inference caveats; banned-language clean; exact-pick fields carry `internal_diagnostic=True`.

## 11. Governance + robustness boundary
Overlay/inference-only; **zero Engine-A/B import into the aggregator/artifact** (guard test). `decision_supported=False` recursively; no banned David-facing patterns. Robustness: API-misuse → fail loud; data-corruption (malformed rows) → fail closed + drop-record; semantic/range → producer-validated. Local-first; frontend HOLD; NOISE_BAND untouched.

## 12. Acceptance criteria & falsification matrix (seeds RED)
AC: deterministic robust-median aggregation (canonical, shared with S4 w/ S4 contracts intact); round-tier primary (§8 boundaries); abstention exactly §9 (incl. dispersion hard-block); big-board exclusion; latest-per-analyst deterministic dedup; read-only fail-closed S3 join + match-rate gate; projection_status handling; overlay-only + decision_supported=False + exact-pick internal-only; no Engine-A/B import; S4 tests unchanged.

Falsification rows: nominal multi-analyst exact-pick prospect; <3→abstain; 3–4→round-tier-only (no exact pick); ≥5 tight→exact pick w/ internal_diagnostic=True; ≥5 **wide dispersion→exact pick hard-blocked** + disagreement_flag; big_board excluded; duplicate analyst versions→latest only (deterministic tie-break); round_only→round-tier vote; udfa→UDFA tier; missing draft_class→reject; exact_pick w/ null/out-of-range pick→reject; unresolved>20% or Top-12 unresolved→abstain; empty input→abstain (no crash); even-count median→**raw float preserved** (e.g. 32.5; `round_half_up` only when mapping to `round_tier`); S4 `aggregate_per_prospect` parity after rewire.

## 13. Open decisions — RESOLVED
- §13.1 match-rate (Gemini): >20% unresolved OR any Top-12 unresolved → abstain. ✅
- §13.2 dispersion (Gemini + Codex): wide dispersion hard-blocks exact pick even at n≥5. ✅ Numeric cutoff = **IQR > 6 picks** (S4 default `dispersion_threshold=6`, contract-tested; Codex round-2). ✅
- §13.3 input format (Claude): curated **JSON** file (not CSV `manual_export_adapter`); cockpit confirm.
- §13.4 median representation (Codex defect 2): **preserve raw float median**; `round_half_up` applies ONLY when mapping a median to `round_tier` (S4-consistent). ✅
- §13.5 round-tiers (Gemini): R1.early 1–4 / R1.mid 5–8 / R1.late 9–12 / R2 / R3 / Day3 R4–7 / UDFA. ✅
- §13.6 (Codex round-2): `disagreement_flag` / exact-pick-block cutoff = **IQR > 6 picks**. ✅

## 14. Build sequence (post-approval only)
round-2 dual-CLEAR (Codex technical + Gemini governance) → David final approval (incl. §13.2/§13.6 cutoff) → Codex RED → Claude GREEN per task (incl. the S4-rewire parity task) → dual-CLEAR → David-confirmed commit → zero-divergence audit. No RED before dual-CLEAR + David approval.
