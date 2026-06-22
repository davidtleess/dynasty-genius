# Subsystem 1 — Mock-Consensus Aggregation — Implementation Plan

- Status: **v4 — incorporates the targeted pre-T1 design spot-check (3-lane 8-item union U1–U8 + 2 David rulings: staleness 30d, dir `app/data/mock_consensus/`); awaiting round-4 dual-CLEAR + David commit authorization before T1 RED**
- Spec: `docs/superpowers/specs/2026-06-20-subsystem-1-mock-consensus-aggregation-design.md` (v4; see §v4 changelog + §13.7–§13.13)

## Pre-T1 spot-check union (U1–U8) — where each lands in the build
- **U1** math/policy: T1 canonical math returns raw iqr/mad only (NO `disagreement_flag`, NO threshold); the `iqr>6` flag/block is S1 consumer policy (T4) and S4 keeps its own `dispersion_threshold`.
- **U2** import isolation: T5 adds `mock_consensus/` to the S4-audit AST scan roots + reverse-import guard and runs the FULL `test_subsystem_4_audit.py` before its RED; T6 guard also bans `backtest_mock_draft`/Engine A/B/scoring imports under `mock_consensus/`.
- **U3** analyst canonical strings: T2 rejects blank/malformed `analyst`.
- **U4** Top-12 pre-join gate: T3 helper preserves unresolved rows; T4 ranks raw latest-eligible rows before the join.
- **U5** staleness 30d: T4 exact gate adds `staleness_days <= 30`.
- **U6** `internal_diagnostic` structural: carried on the T4 consensus record, not a T6 add.
- **U7** MAD diagnostic-only: T1 computes + tests `mad`; no policy consumes it.
- **U8** artifact dir `app/data/mock_consensus/`: T6 writes there with a write-isolation test vs `app/data/valuation/`.
- Branch: `feature/subsystem-1-mock-consensus-aggregation`
- Flow per task: Codex RED → Claude GREEN → Codex technical + Gemini governance dual-CLEAR → David-confirmed commit → zero-divergence audit.
- New package: `src/dynasty_genius/mock_consensus/` (S1 owns it). Tests under `tests/contract/`.

## Resolved open questions (Codex round-1 rulings)
- Package: `src/dynasty_genius/mock_consensus/` (S1 owns the domain; S4 imports the pure math). ✅
- Curated-JSON fixtures: `tests/fixtures/mock_consensus/` — NOT `resources/` (no manual sample data in `resources/` without David-approved product provenance). ✅
- **T5 reordered to run right after T1** (Codex F-order): S4 parity is the strongest test of the canonical math; harden T1 before S1 policy builds on it. New order: T1 → T5 → T2 → T3 → T4 → T6.

## Task sequence + dependencies (executable)

**T1 — Canonical consensus math (pure).** `mock_consensus/consensus_math.py`.
Typed input (Codex F1): `ConsensusObservation(pick_no: int|None, projected_round: int|None, source_id: str, analyst: str, published_date: str)`. Pure `compute_consensus_stats(observations, *, as_of: str) -> ConsensusStats` (Codex: `as_of` IS in the signature) returning: `median` (raw float, NO rounding), `min`, `max`, `iqr` (raw), `mad` (raw, **diagnostic-only — U7**), `n_sources` (distinct source_id), `n_unique_analysts` (distinct analyst), `staleness_days` (max age of `published_date` vs `as_of`). **NO `disagreement_flag`, NO threshold in the canonical return (U1)** — the `iqr>6` flag/block is consumer policy (S1 derives it in T4; S4 keeps its own `dispersion_threshold`). **IQR method LOCKED for S4 parity (Codex F2; VERIFIED against source):** `statistics.quantiles(picks, n=4)` default **exclusive**; `len>=2` else `iqr=0.0` (confirmed at `backtest_mock_draft.py:486-491` + `AGGREGATION_VERSION` note). **MAD = raw median-absolute-deviation** (unscaled), explicitly documented. NO abstention policy. NO I/O.
RED (`tests/contract/test_s1_consensus_math.py`): float-median even-count `[20,45]`→32.5 (float); IQR exclusive `[10,20,30,40]`→25.0 (S4-parity value); **raw-IQR boundary VALUES (no flag asserted here — flag derivation moved to T4 policy per U1): `[10,12,14,16]`→IQR 5.0; `[10,12,16,18]`→IQR 7.0**; MAD raw value on a known set (U7 — assert computed + serialized, no policy consumes it); `n_sources`/`n_unique_analysts` distinctness; staleness vs as_of; len==1→iqr 0.0; empty→raises/typed-empty; **assert the return shape carries NO `disagreement_flag` attribute (U1)**.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_consensus_math.py -q`. Expected RED: `ModuleNotFoundError: No module named 'src.dynasty_genius.mock_consensus.consensus_math'` (real package path).
Dependency: none (foundational).

**T5 — S4 parity rewire (right after T1).** edit `src/dynasty_genius/eval/backtest_mock_draft.py` + `tests/contract/test_subsystem_4_audit.py` (U2 scan-root addition).
S4's `aggregate_per_prospect` delegates the *raw statistics* (median/iqr/mad/min/max via the T1 module) while keeping its own `n_sources` abstention policy, its own `dispersion_threshold` comparison (`:529`), and `ProspectConsensus` shape unchanged. Behavior-preserving refactor — S4 keeps ALL policy; only the math is delegated.
**U2 import isolation (do FIRST in T5, before the parity RED):** add `src/dynasty_genius/mock_consensus` to `AST_AUDIT_SCAN_ROOTS` in `test_subsystem_4_audit.py` and add a reverse-import guard so `mock_consensus/` may NOT import `backtest_mock_draft` / Engine A/B / scoring (only the one-directional S4→math edge is allowed). Run the **FULL `test_subsystem_4_audit.py`** against the T5 surface and confirm green. (Verified: `backtest_mock_draft.py` is NOT byte-locked — `INVIOLATE_BASELINE`=Phase 10/11/12, `S3_INVIOLATE`=`college_prospect_identity.py` only — so no byte-lock trips; the isolation/AST guards are the live concern. Any scan-root amendment is David-authorized.)
RED (Codex F6 + round-2 true-RED): THREE assertions — (a) **delegation spy (the true RED)**: monkeypatch/spy `consensus_math.compute_consensus_stats` and assert `aggregate_per_prospect` CALLS it — FAILS pre-rewire, GREEN post-rewire; (b) **characterization (no-drift safety)**: exact `ProspectConsensus.model_dump()` equal pre/post across fixtures spanning **all four policy paths — abstain / round_tier_only / exact_pick / high-IQR** (Codex #3, not only nominal); plus the FULL existing `tests/contract/test_subsystem_4_aggregation.py` passes unchanged; (c) **U2 audit**: full `test_subsystem_4_audit.py` green with the new scan root + reverse-import guard.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_aggregation.py tests/contract/test_subsystem_4_audit.py tests/contract/test_s1_s4_parity.py -q`. Expected RED pre-rewire: delegation-spy fails (compute_consensus_stats not called); characterization + S4 suite + audit stay green.
Dependency: T1.

**T2 — Curated-input loader + adapter.** `mock_consensus/curated_input.py`.
Two-stage fail-closed validation (structural→semantic) of curated JSON (§3); big-board guard (§4); `projection_status` handling; `draft_class` required; **`analyst` required as a curator-canonical non-blank string (U3)**; drop-record-with-reason. Adapter (§3b): curated row → typed `NormalizedCollegeProspectRow` (synthesize S3 provenance), read-only.
RED (`tests/contract/test_s1_curated_input.py`): schema gate; semantic rejects (missing draft_class; **blank/malformed `analyst` → drop-record w/ reason (U3)**; source_type!=mock; exact_pick w/ null or out-of-range pick `>DRAFT_PICK_MAX`; round_only w/ bad round; udfa w/ pick; malformed date; dup raw_row_hash → drop-record w/ reason); big_board excluded w/ reason; adapter builds a valid `NormalizedCollegeProspectRow`.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_curated_input.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.curated_input`.
Dependency: none.

**T3 — Read-only S3 identity resolver + generic gate helper.** `mock_consensus/identity_join.py`.
Row-level resolution: normalize_name → `compute_match_key(name,pos_group,draft_class)` → registry lookup → `score_candidate`/`surface_review_candidates` → review-queue/fail-closed; alias-bridge target resolved through registry → `ConfirmedProspectUuid` (unresolvable → no-match). **Match-rate gate is a GENERIC helper that preserves UNRESOLVED rows (U4):** `apply_match_rate_gate(ranked_rows, *, top_n=12, max_unresolved=0.20)` where `ranked_rows` are the raw latest-eligible rows ranked by projected pick, each tagged resolved/unresolved — so an unresolved row in the top-N still trips the gate. The Top-12 application happens in T4 over the raw pre-join ranking (Codex F3 + U4). Mints/writes nothing.
RED (`tests/contract/test_s1_identity_join.py`): exact match; fuzzy→review-queue; common-name collision→no auto-match; **direct registry row with `verification_status != confirmed` → no-match (Codex F4)**; alias hit→ConfirmedProspectUuid (provisional/unknown target→no-match); **gate-helper both arms over ranked rows that INCLUDE unresolved entries: (i) >20% unresolved→trip; (ii) an UNRESOLVED row ranked within top-N→trip even when overall unresolved <20% (U4 paradox — proves unresolved top-12 cannot silently bypass)**; only confirmed feed aggregation.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_identity_join.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.identity_join`.
Dependency: T2 (typed rows).

**T4 — S1 aggregation + analyst abstention policy + Top-12 gate application.** `mock_consensus/aggregate.py`.
Latest-eligible-per-analyst dedup (§5 deterministic tie-break published_date→source_snapshot_id→raw_row_hash; analyst counted by curator-canonical string, U3); call T1 math (raw stats); **derive `disagreement_flag = iqr>6` HERE in S1 policy (U1 — threshold lives in the consumer, not the canonical math)**; round-tier bucketing (§8: 1-4/5-8/9-12/R2/R3/Day3/UDFA; round_only→round-median vote; udfa→UDFA tier); **S1 analyst abstention policy** (§9: <3 abstain / 3-4 round-tier-only / ≥5 exact **AND IQR≤6 AND `staleness_days`≤30 (U5)**); **`internal_diagnostic` is a structural boolean on the emitted T4 consensus record (U6)** — set True on an emitted exact pick, else the exact pick is suppressed at the record level; **applies the T3 match-rate gate over the RAW pre-join ranked rows (U4 / Codex F3)**.
RED (`tests/contract/test_s1_aggregate.py`): dedup determinism (dup versions→latest, deterministic tie-break); round-tier boundaries; **half-median mapping (Codex F5): median 4.5→round_half_up 5→R1.mid; 8.5→9→R1.late**; abstention <3/3-4/≥5; **`disagreement_flag` derived in policy from raw iqr (iqr 7.0→True, 5.0→False) — U1**; **IQR>6 hard-block at n≥5 (exact suppressed); staleness boundary `staleness_days` 30→exact allowed, 31→exact suppressed (U5)**; **`internal_diagnostic` present as a structural field on the emitted exact record, True when emitted (U6)**; round_only/udfa paths; **RAW pre-join Top-12 unresolved→artifact abstains (U4); overall >20% unresolved→abstains**.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_aggregate.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.aggregate`.
Dependency: T1, T2, T3.

**T6 — Overlay artifact writer.** `mock_consensus/artifact.py` (+ optional build script).
Write-isolated **`app/data/mock_consensus/mock_consensus_<run>.json` + `_latest` (U8 — David ruling; NOT `app/data/valuation/`)**; recursive `decision_supported=False`; serializes the T4 record's structural `internal_diagnostic` (U6 — T6 does not invent the flag, T4 already set it); intrinsic caveats; banned-language clean.
RED (`tests/contract/test_s1_artifact.py`): **write-isolation — only `app/data/mock_consensus/` written; assert NO write under `app/data/valuation/` (esp. `*_latest.json`) (U8)**; recursive decision_supported=False; internal_diagnostic serialized from the T4 record on exact pick; banned-language scan; **guard test: no `engine_a`/`engine_b`/scoring/`backtest_mock_draft` import anywhere under `mock_consensus/` (AST or import scan) (U2 reverse-import)**.
Cmd: `.venv/bin/python3.14 -m pytest tests/contract/test_s1_artifact.py -q`. Expected RED: `ModuleNotFoundError: ...mock_consensus.artifact`.
Dependency: T4.

## Cross-cutting guards (every task)
Overlay/inference-only; zero Engine-A/B/scoring/`backtest_mock_draft` import into `mock_consensus/` (U2 — only the one-directional S4→math edge is allowed); `decision_supported=False`; no banned David-facing language; local-first; frontend HOLD intact; not wired to any David-facing surface or the model this increment.

## Verification
Per-task focused tests; **at T5: run the FULL `test_subsystem_4_audit.py` (U2 isolation/AST) + full `test_subsystem_4_aggregation.py` (parity) BEFORE the T5 RED, plus the full Python suite mid-build** (T5 touches shipped S4); full Python suite again at closeout; `verify_sprint_closeout --base origin/main` ENFORCE PASS at closeout; ruff src app; FE gate N/A (no frontend touch).

## Open plan questions — RESOLVED (Codex round-1)
1. Package location → `src/dynasty_genius/mock_consensus/`. ✅
2. T5 ordering → right after T1 (parity hardens the math first). ✅
3. Curated-JSON fixtures → `tests/fixtures/mock_consensus/`. ✅
