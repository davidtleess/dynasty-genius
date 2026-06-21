# Subsystem 1 — Mock-Consensus Aggregation — Implementation Plan

- Status: **v3 — incorporates Codex round-2 findings (IQR-math correction, T5 true-RED, executability fixes); awaiting round-3 CLEAR before T1 RED**
- Spec: `docs/superpowers/specs/2026-06-20-subsystem-1-mock-consensus-aggregation-design.md` (v3, dual-CLEARED, committed `c96ba76`)
- Branch: `feature/subsystem-1-mock-consensus-aggregation`
- Flow per task: Codex RED → Claude GREEN → Codex technical + Gemini governance dual-CLEAR → David-confirmed commit → zero-divergence audit.
- New package: `src/dynasty_genius/mock_consensus/` (S1 owns it). Tests under `tests/contract/`.

## Resolved open questions (Codex round-1 rulings)
- Package: `src/dynasty_genius/mock_consensus/` (S1 owns the domain; S4 imports the pure math). ✅
- Curated-JSON fixtures: `tests/fixtures/mock_consensus/` — NOT `resources/` (no manual sample data in `resources/` without David-approved product provenance). ✅
- **T5 reordered to run right after T1** (Codex F-order): S4 parity is the strongest test of the canonical math; harden T1 before S1 policy builds on it. New order: T1 → T5 → T2 → T3 → T4 → T6.

## Task sequence + dependencies (executable)

**T1 — Canonical consensus math (pure).** `mock_consensus/consensus_math.py`.
Typed input (Codex F1): `ConsensusObservation(pick_no: int|None, projected_round: int|None, source_id: str, analyst: str, published_date: str)`. Pure `compute_consensus_stats(observations, *, as_of: str) -> ConsensusStats` (Codex: `as_of` IS in the signature) returning: `median` (raw float, NO rounding), `min`, `max`, `iqr`, `mad`, `n_sources` (distinct source_id), `n_unique_analysts` (distinct analyst), `staleness_days` (max age of `published_date` vs `as_of`), `disagreement_flag` (`iqr > 6`). **IQR method LOCKED for S4 parity (Codex F2):** `statistics.quantiles(picks, n=4)` default **exclusive**; `len>=2` else `iqr=0.0` (matches `backtest_mock_draft.py:485-490` + `AGGREGATION_VERSION` note). **MAD = raw median-absolute-deviation** (unscaled), explicitly documented. NO abstention policy. NO I/O.
RED (`tests/contract/test_s1_consensus_math.py`): float-median even-count `[20,45]`→32.5 (float); IQR exclusive `[10,20,30,40]`→25.0 (S4-parity value); **`iqr>6` boundary — VERIFIED values (Codex round-2 corrected my wrong two-point examples): `[10,12,14,16]`→IQR 5.0→flag False; `[10,12,16,18]`→IQR 7.0→flag True** (exact-6 unreachable with small ints under exclusive quantiles; strict `>` means 6.0 would be False); MAD raw value on a known set; `n_sources`/`n_unique_analysts` distinctness; staleness vs as_of; len==1→iqr 0.0; empty→raises/typed-empty.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_consensus_math.py -q`. Expected RED: `ModuleNotFoundError: No module named 'src.dynasty_genius.mock_consensus.consensus_math'` (real package path).
Dependency: none (foundational).

**T5 — S4 parity rewire (right after T1).** edit `src/dynasty_genius/eval/backtest_mock_draft.py`.
S4's `aggregate_per_prospect` delegates the *statistics* (median/iqr/min/max via the T1 module) while keeping its own `n_sources` abstention policy + `ProspectConsensus` shape unchanged. Behavior-preserving refactor.
RED (Codex F6 + round-2 true-RED): TWO assertions — (a) **delegation spy (the true RED)**: monkeypatch/spy `consensus_math.compute_consensus_stats` and assert `aggregate_per_prospect` CALLS it — this FAILS pre-rewire (S4 not yet delegating), goes GREEN post-rewire, proving delegation; (b) **characterization (no-drift safety)**: exact `ProspectConsensus.model_dump()` for ~3 S4 fixtures equal pre/post; plus the FULL existing `tests/contract/test_subsystem_4_aggregation.py` passes unchanged.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_aggregation.py tests/contract/test_s1_s4_parity.py -q`. Expected RED pre-rewire: the delegation-spy assertion fails (compute_consensus_stats not called); characterization + S4 suite stay green.
Dependency: T1.

**T2 — Curated-input loader + adapter.** `mock_consensus/curated_input.py`.
Two-stage fail-closed validation (structural→semantic) of curated JSON (§3); big-board guard (§4); `projection_status` handling; `draft_class` required; drop-record-with-reason. Adapter (§3b): curated row → typed `NormalizedCollegeProspectRow` (synthesize S3 provenance), read-only.
RED (`tests/contract/test_s1_curated_input.py`): schema gate; semantic rejects (missing draft_class; source_type!=mock; exact_pick w/ null or out-of-range pick `>DRAFT_PICK_MAX`; round_only w/ bad round; udfa w/ pick; malformed date; dup raw_row_hash → drop-record w/ reason); big_board excluded w/ reason; adapter builds a valid `NormalizedCollegeProspectRow`.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_curated_input.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.curated_input`.
Dependency: none.

**T3 — Read-only S3 identity resolver + generic gate helper.** `mock_consensus/identity_join.py`.
Row-level resolution: normalize_name → `compute_match_key(name,pos_group,draft_class)` → registry lookup → `score_candidate`/`surface_review_candidates` → review-queue/fail-closed; alias-bridge target resolved through registry → `ConfirmedProspectUuid` (unresolvable → no-match). **Match-rate gate is a GENERIC helper** `apply_match_rate_gate(resolutions, ranked_uuids, top_n=12, max_unresolved=0.20)` — the actual Top-12 application happens in T4 after consensus ordering exists (Codex F3). Mints/writes nothing.
RED (`tests/contract/test_s1_identity_join.py`): exact match; fuzzy→review-queue; common-name collision→no auto-match; **direct registry row with `verification_status != confirmed` → no-match (Codex F4)**; alias hit→ConfirmedProspectUuid (provisional/unknown target→no-match); gate-helper both arms (>20% unresolved; a named top-N uuid unresolved); only confirmed feed aggregation.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_identity_join.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.identity_join`.
Dependency: T2 (typed rows).

**T4 — S1 aggregation + analyst abstention policy + Top-12 gate application.** `mock_consensus/aggregate.py`.
Latest-eligible-per-analyst dedup (§5 deterministic tie-break published_date→source_snapshot_id→raw_row_hash); call T1 math; round-tier bucketing (§8: 1-4/5-8/9-12/R2/R3/Day3/UDFA; round_only→round-median vote; udfa→UDFA tier); **S1 analyst abstention policy** (§9: <3 abstain / 3-4 round-tier-only / ≥5 exact + IQR≤6 + staleness; exact carries `internal_diagnostic=True`); **applies the T3 match-rate gate over the ranked consensus** (Codex F3).
RED (`tests/contract/test_s1_aggregate.py`): dedup determinism (dup versions→latest, deterministic tie-break); round-tier boundaries; **half-median mapping (Codex F5): median 4.5→round_half_up 5→R1.mid; 8.5→9→R1.late**; abstention <3/3-4/≥5; IQR>6 hard-block at n≥5 (exact suppressed); internal_diagnostic flag on exact; round_only/udfa paths; Top-12 unresolved→artifact abstains.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_aggregate.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.aggregate`.
Dependency: T1, T2, T3.

**T6 — Overlay artifact writer.** `mock_consensus/artifact.py` (+ optional build script).
Write-isolated `app/data/valuation/mock_consensus_<run>.json` + `_latest`; recursive `decision_supported=False`; `internal_diagnostic=True` on exact-pick fields; intrinsic caveats; banned-language clean.
RED (`tests/contract/test_s1_artifact.py`): write-isolation (only the artifact path written); recursive decision_supported=False; internal_diagnostic on exact pick; banned-language scan; **guard test: no `engine_a`/`engine_b`/scoring import anywhere under `mock_consensus/` (AST or import scan)**.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_artifact.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.artifact`.
Dependency: T4.

## Cross-cutting guards (every task)
Overlay/inference-only; zero Engine-A/B import into `mock_consensus/`; `decision_supported=False`; no banned David-facing language; local-first; frontend HOLD intact; not wired to any David-facing surface or the model this increment.

## Verification
Per-task focused tests; full Python suite mid-build when touching S4 (T5) and at closeout; `verify_sprint_closeout --base origin/main` ENFORCE PASS at closeout; ruff src app; FE gate N/A (no frontend touch).

## Open plan questions — RESOLVED (Codex round-1)
1. Package location → `src/dynasty_genius/mock_consensus/`. ✅
2. T5 ordering → right after T1 (parity hardens the math first). ✅
3. Curated-JSON fixtures → `tests/fixtures/mock_consensus/`. ✅
