---
title: Subsystem 4 — Backtest Harness (Manual-First) — Design Spec
status: BRAINSTORM CLEAR (Codex technical round-3) — awaiting David final read + Gemini governance review before writing-plans
date: 2026-05-28
author: Claude Code (brainstormed with David; technical review Codex round-3 cleared per-section)
parent: docs/strategies/2026-05-28-increment-a-reconciliation-and-go-forward.md (Increment A reconciliation, §39 binding S4 contracts)
prerequisites: Subsystem 3 — Prospect Identity Substrate (MERGED to main 2026-05-28; PR #55 `0730dcb`)
governance_hold: Frontend remains on Phase 12 HOLD; backend only. NOISE_BAND lock untouched. `decision_supported=False` throughout.
---

# Subsystem 4 — Backtest Harness (Manual-First)

## 0. What we're building

A **manual-first backtest harness** that tests whether NFL mock-draft consensus predicts realized NFL draft capital. **Backtest A only in v1**; **Backtest B is deliberately excluded** except as a documented downstream gate (always-abstain stub). The harness consumes versioned canonical-JSON mock snapshots (no source HTML parsers in v1), joins to S3's prospect identity substrate via an **at-draft-time human-reviewed bridge** to nflreadr draft truth, and emits the six metrics defined in reconciliation §39 plus a `backtest_b_gate_status` per round/position bucket.

The substrate is **substrate-only validation infrastructure**: overlay/inference-only, `decision_supported=False` throughout, no model-training feed, no market data into anything, no Engine A/B touch, no PVO touch, no Trade Lab touch. Per reconciliation §15, Increment A is identity-substrate + backtest-machinery NOW; this subsystem is the second of the two pillars.

## 1. Locked design decisions (cockpit-converged during brainstorm)

**Q1 — Scope (Codex-recommended c + Claude-refined B stub):**
- v1 = Backtest A + the prospect↔NFL bridge workflow + a B-shaped always-abstain stub
- Backtest B implementation deliberately EXCLUDED from v1; stub returns structured abstain fields
- Contract test locks the abstain behavior so future agents cannot quietly fill it in without flipping the test

**Q2 — Bridge workflow shape (A Hybrid, Codex round-2 cleared):**
- S4 owns the cross-domain artifact (`prospect_to_nfl_bridge_<draft_year>.json`) and the cross-domain semantics
- S3 contributes infrastructure PATTERNS (atomic write, review queue, decision-log replay, graph validation) — but S4 IMPLEMENTS its own helpers; no private function imports across module boundaries (`_atomic_write_jsonl` and friends stay encapsulated in S3)
- Bridge under `src/dynasty_genius/identity/` (identity infrastructure used by validation), not under `eval/` (which would conflate)

**Q3 — Ingestion contract (X canonical JSON + manual paste, Codex round-2 cleared):**
- S4 v1 accepts versioned normalized JSON snapshots with required sidecar metadata
- **NO source HTML parsers in v1** (avoids ToS-sensitive retrieval assumptions; avoids Campbell-style title-vs-body parser hazards contaminating the harness layer)
- Manual paste is the right manual-first affordance if it produces the canonical schema + provenance
- Per-source parsers are separate later increments, each with its own ToS/legal review and parser-specific contract tests

**Q4 — Historical scope (R synthetic + acceptance criteria, Codex round-2 cleared):**
- v1 ships with synthetic snapshots covering every contract path
- Real historical curation = separate follow-up workstream
- Spec includes explicit **Minimum evidence criteria to evaluate Backtest A** (Section 5) so the follow-up curation effort has a concrete target

**Module decomposition (1 Two-module split, Codex round-2 cleared):**
- `src/dynasty_genius/identity/prospect_nfl_bridge.py` — cross-domain identity (bridge schema, validation, review queue, atomic write, decision-log promotion)
- `src/dynasty_genius/eval/backtest_mock_draft.py` — snapshot schema + ingestion + Backtest A runner + 6 metrics + abstention gates + `backtest_b_gate_status` emitter + report artifact writer + B-shaped abstain library function
- 4 CLI scripts: `build_prospect_nfl_bridge.py`, `promote_bridge_candidate.py`, `run_backtest_a.py`, `run_backtest_b.py`

## 2. Architecture

```
src/dynasty_genius/
├── identity/
│   ├── __init__.py                       # existing (S3 package init)
│   ├── college_prospect_identity.py      # existing (S3)
│   └── prospect_nfl_bridge.py            # NEW: cross-domain bridge
└── eval/
    ├── backtest_harness.py               # existing (Phase 10/11 — Engine A/B walk-forward)
    └── backtest_mock_draft.py            # NEW: mock-draft consensus → realized NFL capital

scripts/
├── build_prospect_nfl_bridge.py          # NEW: discovery for a draft year (candidate matching)
├── promote_bridge_candidate.py           # NEW: ONLY blessed write path for bridge decisions
├── run_backtest_a.py                     # NEW: Backtest A CLI
└── run_backtest_b.py                     # NEW: B-shaped stub (always abstains)

app/data/
├── identity/
│   ├── (S3 artifacts — read-only by S4)
│   ├── prospect_to_nfl_bridge_<draft_year>.json                           # per-year bridge artifact
│   ├── prospect_nfl_bridge_decision_log_<draft_year>.jsonl                # per-year decision log (S3 §6.3 pattern)
│   ├── prospect_nfl_review_queue_<draft_year>_<run_id>.jsonl              # per-run discovery output
│   ├── prospect_nfl_unmatched_udfa_candidates_<draft_year>_<run_id>.jsonl # per-run UDFA queue
│   └── prospect_nfl_coverage_<draft_year>_<run_id>.json                   # per-run coverage matrix
└── backtest/
    └── mock_draft/
        ├── snapshots/<source_label>/<published_date>_<analyst-slug>_<mock_version>.json
        └── runs/<run_id>/
            └── backtest_a_result.json

tests/
├── contract/
│   ├── test_subsystem_4_schema.py
│   ├── test_subsystem_4_bridge.py
│   ├── test_subsystem_4_ingestion.py
│   ├── test_subsystem_4_aggregation.py
│   ├── test_subsystem_4_metrics.py
│   ├── test_subsystem_4_b_gate.py
│   ├── test_subsystem_4_b_stub.py
│   └── test_subsystem_4_audit.py
└── fixtures/
    └── backtest_mock_draft/
        ├── snapshots/
        ├── bridge_artifacts/
        └── nflreadr_synthetic/
```

**Dependencies:**
- `prospect_nfl_bridge.py` depends on `college_prospect_identity` for the matcher SCORING (uses S3's `score_candidate` public function directly for per-row similarity scoring; uses S3's `ConfirmedProspectUuid` to validate `prospect_uuid` inputs are confirmed). S4 implements its **own discovery wrapper** analogous to `surface_review_candidates` but with an NFL-domain position taxonomy (e.g., college EDGE → NFL OLB transitions, college S → NFL FS/SS, etc.); the S3 `surface_review_candidates` function is NOT imported directly because its hard-block + whitelist filters are college-side and would mis-handle college→NFL position migrations. S4 also implements its own atomic-write / decision-log helpers following the S3 pattern; no underscore-private cross-module imports.
- `backtest_mock_draft.py` depends on `prospect_nfl_bridge` (read bridge artifact at run time) and a thin nflreadr wrapper (draft truth)
- `nflreadpy` already in `requirements.txt` (Phase 17/18 universe-snapshot usage); no new deps

**Inviolate paths (byte-unchanged contract test extends S3's existing inviolate set):**
- All pre-S3 inviolate paths
- S3-merged committed artifacts: `app/data/identity/college_prospect_registry.json`, `app/data/identity/college_alias_bridge.json`
- Plus all of S3's source files (`src/dynasty_genius/identity/__init__.py`, `src/dynasty_genius/identity/college_prospect_identity.py`)

**Cockpit TDD pattern** (per `[[reference_review_workflow]]`): Codex authors RED contract tests for each task; Claude implements GREEN; cockpit second-round review of any non-trivial design choice; David approves before merge.

## 3. Bridge schema + workflow

### 3.1 ProspectNflBridgeEntry (Pydantic)

```python
class ProspectNflBridgeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # identity
    prospect_uuid: str                          # cpr_<uuid4> from S3; MUST be 'confirmed' at write time
    gsis_id: Optional[str] = None               # canonical NFL identifier; required for drafted; None for udfa
    pfr_id: Optional[str] = None                # nullable secondary; None acceptable for drafted

    # context
    draft_year: int                             # MUST equal S3 row's draft_class
    draft_pick_no: Optional[int] = None         # required for drafted; None for udfa
    draft_round: Optional[int] = None           # required for drafted; None for udfa
    nfl_team: Optional[str] = None              # required for drafted; None for udfa
    udfa: bool                                  # explicit boolean (not derived)

    # provenance of the nflreadr snapshot used at decision time (§32 traceability)
    nflreadr_source: str                        # e.g., "nflreadpy.draft_picks"
    nflreadr_season: int                        # typically == draft_year, explicit anyway
    draft_truth_content_hash: str               # SHA-256 of nflreadr rows considered (deterministic)
    nflreadr_fetched_at: str                    # ISO timestamp

    evidence_snapshot: Optional[dict[str, Any]] = None
    # captured nflreadr fields for the matched row (None for udfa):
    #   {"full_name", "position", "college", "fetched_at"}
    # Preserves audit even if nflreadr corrects later

    # decision audit (top-level; no nested status_history list — that's S3 vocabulary)
    event_id: str
    decided_at: str
    reviewer_id: str
    decision: Literal["confirm", "udfa"]
    note: Optional[str] = None
```

### 3.2 Validation rules

1. `prospect_uuid` must resolve to `verification_status="confirmed"` in S3 at write time
2. `draft_year` == S3 row's `draft_class`
3. **1:1 invariant within a draft_year**: each `prospect_uuid` maps to ≤1 entry; each non-null `gsis_id` maps to ≤1 entry
4. **UDFA asymmetric validation:**
   - `udfa=True` ⇒ `gsis_id`, `pfr_id`, `draft_pick_no`, `draft_round`, `nfl_team` **all None** (5 strict fields)
   - `udfa=False` ⇒ `gsis_id`, `draft_pick_no`, `draft_round`, `nfl_team` **all present** (4 required); `pfr_id` nullable secondary
5. Provenance fields all present (`nflreadr_source`, `nflreadr_season`, `draft_truth_content_hash`, `nflreadr_fetched_at`)
6. **Decision-log replay over genesis state reproduces the bridge artifact byte-identical** (S3 §6.3 pattern)
   - Genesis = **missing or empty** `prospect_to_nfl_bridge_<draft_year>.json` (no entries yet)
   - Decision log records **EVERY decision** (`confirm`, `udfa`, `reject`, `defer`) in temporal order — complete audit trail
   - Replay **applies only accepted (`confirm` and `udfa`) events** to reconstruct the bridge artifact byte-identical. `reject` and `defer` events are recorded in the log for audit but never mutate the bridge artifact
   - v1 bridge is **never pre-seeded** — no ingestion step that loads entries before the decision log

### 3.3 Workflow (3 stages; blessed-write-path discipline)

**(i) Discovery — `scripts/build_prospect_nfl_bridge.py --draft-year 2025`**
- Reads S3 prospects with `verification_status="confirmed"` AND `draft_class=2025`
- Fetches nflreadr 2025 draft snapshot
- For each prospect, runs candidate matching using S3's matcher pattern (Jaro-Winkler + token-set blend; position-relaxed since college→NFL position changes are common, e.g., college EDGE → NFL OLB)
- Writes per-run review queue: `prospect_nfl_review_queue_<draft_year>_<run_id>.jsonl`
- Writes per-run unmatched UDFA candidates: `prospect_nfl_unmatched_udfa_candidates_<draft_year>_<run_id>.jsonl` (prospects with no nflreadr match, presumed undrafted)
- Writes coverage matrix: `prospect_nfl_coverage_<draft_year>_<run_id>.json`

**(ii) Review (human-in-loop)** — David inspects the review queue + the UDFA candidates list + the coverage report. No automated writes.

**(iii) Promotion — `scripts/promote_bridge_candidate.py`**

Decisions:
- `confirm` (commits a drafted bridge entry; requires non-null `gsis_id` + 4 NFL outcome fields)
- `udfa` (commits a udfa=True entry; requires non-empty `--evidence` e.g., "verified absent from nflreadr 2025 7-day post-draft window")
- `reject` (no bridge entry written; review row gets closure marker — `decision="reject"` + `decided_at` + `event_id`)
- `defer` (no identity mutation; review row gets closure marker — `decision="defer"` + `decided_at` + `event_id` + `note`. The row IS closed for this run's review cycle; a future discovery run can re-open the question by emitting a new review entry for the same prospect)

Three-point logging (per S3 §6.3 pattern):
1. **Bridge artifact** entry (accepted only — `confirm` and `udfa` decisions)
2. **Append-only decision log**: `prospect_nfl_bridge_decision_log_<draft_year>.jsonl` (every decision, including `reject` and `defer` — complete audit trail)
3. **Review-queue closure marker** appended to the originating review row on **every decision** (`confirm`, `udfa`, `reject`, `defer` — all four close the review row for this run with `decision` + `decided_at` + `event_id`)

Per-file atomic writes in dependency-safe order: `decision_log → bridge_artifact → review_queue_closure`. NOT cross-file transactional; idempotent rerun + post-run graph validation is the recovery contract (mirrors S3 §6.4).

## 4. Mock snapshot schema + ingestion

### 4.1 Canonical JSON schema (Pydantic)

```python
class MockSnapshotPick(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pick_no: int
    prospect_uuid: str                          # string form of ConfirmedProspectUuid
    note: Optional[str] = None

class MockSnapshotMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str
    source_label: str                           # canonical label e.g. "walterfootball", "nflcom_breer"
    analyst: Optional[str] = None
    mock_version: str
    published_date: str                         # ISO YYYY-MM-DD
    fetched_at: str                             # ISO timestamp
    content_hash: str                           # SHA-256 of canonical-serialized picks ONLY
    parser_version: str                         # e.g., "manual_paste_v1" or "wf_parser_v0.3"
    parse_status: Literal["complete", "partial", "untrusted"]
    draft_year: int

class MockSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: MockSnapshotMetadata
    picks: list[MockSnapshotPick]
```

**Canonical pick serialization for content_hash** (Codex round-2 note): sort `picks` by `pick_no` ascending after within-snapshot duplicate validation; serialize JSON with `sort_keys=True` per pick. Eliminates serializer/list-order drift.

### 4.2 Storage layout

- Real-data: `app/data/backtest/mock_draft/snapshots/<source_label>/<published_date>_<analyst-slug>_<mock_version>.json`
- Synthetic (v1): `tests/fixtures/backtest_mock_draft/snapshots/...` (committed small hand-constructed)

### 4.3 Ingestion contract (read-only by Backtest A)

1. **Schema validation** via Pydantic strict mode
2. **Leakage gate (strict <)**: `published_date < draft_date`; snapshots on/after draft date excluded; counted in `leakage_excluded_snapshots`
3. **Identity validation**: every `prospect_uuid` must be `ConfirmedProspectUuid` in S3 at backtest run time. If `deprecated` with `merged_into_prospect_uuid` → **follow_redirect** to survivor (`redirect_applied` flag at pick level + counted in coverage). If redirect target is non-confirmed → exclude pick (fail-closed). If `unknown` → exclude pick + increment `unresolved_picks`
4. **`parse_status="untrusted"` excluded by default**; included only with explicit `--include-untrusted` flag for diagnostic runs
5. **`parse_status="partial"` included by default with `partial_snapshot_warning`**; preserves per-snapshot `pick_count` for metrics that need coverage accounting
6. **Within-snapshot duplicate validation**: duplicate `pick_no` → REJECT snapshot (mock order corrupted). Duplicate `prospect_uuid` → REJECT snapshot (analyst mistake)
7. **Cross-snapshot content_hash semantics**:
   - Same metadata tuple-key + **same content_hash** → **idempotent** (rerun stable)
   - Same metadata tuple-key + **different content_hash** → REJECT + emit `content_hash_collision_warning` (operator resolves manually)
8. **Snapshot files never mutated** by ingestion or backtest (read-only contract test enforces)

### 4.4 Snapshot derived ID

`snapshot_id = SHA-256(source_label || "|" || analyst || "|" || published_date || "|" || mock_version || "|" || content_hash)`

Reports reference snapshots by `snapshot_id` (path-independent).

### 4.5 Per-run coverage matrix

```json
{
  "snapshot_ids_used": ["<sha>", ...],
  "metadata_tuple_keys_used": ["wf|campbell|2025-04-15|v3.2", ...],
  "total_snapshots_found": 42,
  "leakage_excluded_snapshots": 0,
  "untrusted_excluded_snapshots": 3,
  "partial_snapshot_warnings": 2,
  "duplicate_pick_no_rejections": 0,
  "duplicate_prospect_uuid_rejections": 0,
  "content_hash_collisions": 0,
  "snapshots_used": 39,
  "total_picks": 2496,
  "redirect_applied": 7,
  "high_redirect_rate_warning": false,
  "unresolved_picks": 0,
  "unresolved_picks_ratio": 0.0,
  "draft_date_used": "2025-04-24",
  "draft_date_source": "nflreadr.draft_picks"
}
```

### 4.6 draft_date sourcing

- Production: from nflreadr (`nflreadpy` package) for each `draft_year`, cached in run metadata as `draft_date_used` + `draft_date_source="nflreadr.draft_picks"`
- Tests / synthetic: **both** `--override-draft-date YYYY-MM-DD` AND `--override-reason "..."` flags required; loud audit trail; cannot be silently applied
- Strict `published_date < draft_date` enforced regardless

## 5. Backtest A runner + 6 metrics + abstention gates + `backtest_b_gate_status`

### 5.1 Pipeline (6 stages)

1. **Ingest snapshots** (§4)
2. **Aggregate per prospect** → `ProspectConsensus` (median pick + IQR + n_sources + n_analysts + staleness_days + abstention_tier). v1 embeds aggregation in S4; S1 will replace later (without changing metric contracts)
3. **Bridge join** → `RealizedOutcome` (read bridge artifact + re-fetch nflreadr; emit `bridge_stale_warning` if `evidence_snapshot` diverges from re-fetched nflreadr; never silently overwrites bridge data)
4. **Compute 6 metrics** on the joined (consensus + realized) set
5. **Evaluate `backtest_b_gate_status`** per `(round_bucket, position)` combo
6. **Write `backtest_a_result.json` artifact**

### 5.2 ProspectConsensus

```python
class ProspectConsensus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prospect_uuid: str
    projected_pick_median: Optional[float] = None  # None if abstain tier; half-picks preserved (no truncation)
    projected_pick_iqr: Optional[float] = None
    projected_pick_min: Optional[int] = None
    projected_pick_max: Optional[int] = None
    n_sources: int                                  # distinct source_labels
    n_unique_analysts: int                          # distinct analysts
    snapshot_ids_used: list[str]
    staleness_days: Optional[float] = None          # days from most recent snapshot to draft_date
    abstention_tier: Literal["abstain", "round_tier_only", "exact_pick"]
    abstention_reason: Optional[str] = None
```

### 5.3 Abstention gates (per reconciliation §40)

- `n_sources < 3` → `abstain` (no projection emitted)
- `3 ≤ n_sources ≤ 4` → `round_tier_only` (no exact-pick claim allowed; median pick used only for round-tier mapping)
- `n_sources ≥ 5` AND `IQR ≤ dispersion_threshold` → `exact_pick` (internal diagnostic only; **never David-facing** per §40)

**`dispersion_threshold` v1 default = 6 picks IQR.** Recorded in artifact metadata for replay.

### 5.4 The 6 metrics

| Metric | Formula | Universe |
|---|---|---|
| `overall_pick_mae` | mean `\|projected_pick_median − realized_pick_no\|` | drafted-and-projected-drafted intersection (UDFA excluded) |
| `round_bucket_accuracy` | % where predicted round-bucket == realized bucket | all non-`abstain`-tier consensus prospects (includes `round_tier_only` + `exact_pick`) |
| `top_36_skill_recall` | `\|projected_top_36 ∩ realized_top_36\| / denominator` | top-36 skill players (WR/RB/TE/QB by realized_pick); **denominator = `min(36, realized_top_36_in_bridge_count)`**; emit `insufficient_truth_coverage` if < 36 |
| `udfa_false_positive_rate` | `false_positives / projected_drafted` (projected drafted but actually UDFA) | projected_drafted = consensus emitted AND `projected_pick_median ∈ [1, 257]`. Abstained prospects NOT counted as projected UDFA |
| `coverage_after_abstention` | `n_scored / n_prospects_total_in_class` | `n_prospects_total_in_class` = count of S3 prospects with `verification_status="confirmed"` AND `draft_class=<draft_year>` at run time |
| `early_pick_weighted_error` | `sum(err × 1/realized_pick_no) / sum(weights)` | drafted-and-projected-drafted intersection; weight `1/realized_pick_no` recorded as `metric_version="s4_metrics_v1"` |

Round buckets: `R1-early` (1–10), `R1-mid` (11–21), `R1-late` (22–32), `R2` (33–64), `R3` (65–105), `Day3` (R4–7), `UDFA`.

**Round-bucket assignment from float median (Codex+Gemini retrospective 2026-05-28).** Round-bucket assignment from a float `projected_pick_median` uses `round_half_up(median)` — i.e., `math.floor(median + 0.5)` — to produce an int pick number, then maps via the buckets table. `round_half_up(32.5) = 33 → R2`. The rounding policy is recorded in artifact metadata as `round_bucket_rounding_policy: "round_half_up"` for replay reproducibility.

**`udfa_false_positive_rate` predicate semantics (Codex retrospective finding 2).** The predicate `projected_pick_median ∈ [1, 257]` is applied to the raw float median (no rounding). A half-pick like `32.5` is inside the inclusive range and counts as `projected_drafted`. Bucket mapping uses `round_half_up` per the paragraph above; the `[1, 257]` predicate does not.

### 5.5 `backtest_b_gate_status` per (round_bucket, position)

For each `(round_bucket, position)` combo, compute MAE and coverage on that subset and evaluate against bucket-specific thresholds. Pass if `MAE ≤ bucket_mae_threshold` AND `coverage ≥ bucket_coverage_threshold`. Backtest B may run on passing buckets when B is later implemented.

**v1 candidate thresholds** (calibrated after first real-data run):

| Bucket | MAE ≤ | Coverage ≥ |
|---|---|---|
| R1-early | 8 picks | 0.8 |
| R1-mid + R1-late | 12 picks | 0.7 |
| R2 | 18 picks | 0.6 |
| R3 + Day3 | not gated for B (always abstain regardless of metrics) | — |

### 5.6 Synthetic-data safety hedge

Even if synthetic metrics pass v1 thresholds, `backtest_b_gate_status.overall_status` is **forced** to `always_abstain_synthetic_data` when **either**:
- `draft_date_source.startswith("override:")`, OR
- Explicit `data_mode="synthetic"` config flag set

Per-bucket entries retain the same schema shape — each shows `gate_result="not_evaluable_synthetic"` (preserves consumer schema; no special-casing).

### 5.7 Bridge top-36 — two-tier threshold

| Threshold | Purpose | Value |
|---|---|---|
| Evidence-to-evaluate-A (v1 acceptance) | Bridge coverage of realized top-36 skill for A to be considered informative | ≥0.90 (with `insufficient_truth_coverage` warning if <1.00) |
| B's actual gating criterion (when B is later implemented) | Per-bucket/position bridge coverage required before B can run on that bucket | **1.00** (complete truth coverage in the specific bucket being evaluated) |

### 5.8 Versioning fields in artifact metadata

```json
"metadata": {
  "run_id": "...",
  "draft_year": 2025,
  "ran_at": "...",
  "matcher_algorithm_version": "cpr_matcher_v1.0.0",
  "metric_version": "s4_metrics_v1",
  "aggregation_version": "s4_provisional_consensus_v1",
  "gate_version": "s4_b_gate_thresholds_v1",
  "round_bucket_rounding_policy": "round_half_up",
  "team_code_normalization_version": "s4_team_norm_v1",
  "within_source_aggregation_applied": false,
  "dispersion_threshold_used": 6,
  "bridge_artifact_path": "...",
  "draft_date_used": "2025-04-24",
  "draft_date_source": "nflreadr.draft_picks",
  "data_mode": "real" | "synthetic"
}
```

S4 v1 aggregation is **provisional by design** — clearly marked `s4_provisional_consensus_v1`. S1 lands later and replaces the aggregation step **without changing metric contracts**.

### 5.9 Artifact shape

```json
{
  "metadata": { ...as 5.8... },
  "coverage": { ...as 4.5... },
  "metrics": {
    "overall_pick_mae": 14.2,
    "round_bucket_accuracy": 0.61,
    "top_36_skill_recall": 0.78,
    "udfa_false_positive_rate": 0.12,
    "coverage_after_abstention": 0.68,
    "early_pick_weighted_error": 4.8,
    "per_bucket_breakdown": { "R1-early": {...}, "R1-mid": {...}, ... }
  },
  "abstention_summary": {
    "abstain": 47,
    "round_tier_only": 23,
    "exact_pick": 18
  },
  "backtest_b_gate_status": {
    "overall_status": "partial" | "all_pass" | "all_fail" | "always_abstain_synthetic_data",
    "per_bucket_results": {
      "R1-early|QB": { "gate_result": "pass", "mae": 5.2, "coverage": 0.92 },
      "R1-early|WR": { "gate_result": "fail", "mae": 11.5, "coverage": 0.7 },
      "R1-early|RB": { "gate_result": "not_evaluable_synthetic", "mae": null, "coverage": null },
      ...
    }
  },
  "warnings": [
    "high_redirect_rate_warning",
    "bridge_stale_warning",
    "partial_snapshot_warning",
    "insufficient_truth_coverage"
  ]
}
```

## 6. B-shaped stub + synthetic fixture coverage + acceptance criteria + testing strategy

### 6.1 B-shaped stub semantics

`scripts/run_backtest_b.py` accepts the same CLI flags as A (symmetric UX). Library function `run_backtest_b()` in `backtest_mock_draft.py` always returns structured abstain:

```python
{
    "status": "gated_on_backtest_a_per_bucket_position",
    "reason": "Backtest B v1 deliberately excluded per spec §39; gated on Backtest A clearance",
    "required_gate": "backtest_a_per_bucket_position",
    "upstream_run_id": Optional[str],     # references a Backtest A run if supplied via --upstream-run
    "decision_supported": False,
    "exit_code": 0,
}
```

The stub may write a small abstain-report file at `app/data/backtest/mock_draft/runs/<run_id>/backtest_b_abstain.json` documenting the gate status. **Contract test `test_backtest_b_remains_abstained_in_v1` locks this behavior** — the test asserts the stub never reads/writes any B-related artifact beyond this single abstain-report file.

### 6.2 Synthetic fixture coverage matrix

Must exercise every contract path:

| # | Contract path | Fixture |
|---|---|---|
| 1 | 6 metrics math | known-answer fixtures with deliberate errors and zero-error cases |
| 2 | Abstention gates §40 (n_sources boundary) | n_sources = 0, 2, 3, 4, 5, 7 |
| 3 | Bridge 1:1 invariant + UDFA asymmetric | confirmed-drafted, confirmed-UDFA, attempted-collision (rejected) |
| 4 | Within-snapshot duplicate rejection | dup pick_no, dup prospect_uuid |
| 5 | Cross-snapshot content_hash collision | same tuple-key, different hash → rejected |
| 6 | Cross-snapshot idempotency | same tuple-key, **same** hash → rerun stable |
| 7 | Sidecar provenance validation | missing field, malformed timestamp, invalid parse_status |
| 8 | Synthetic-data safety hedge | confirm B-gate forced to `always_abstain_synthetic_data` regardless of metric values |
| 9 | `insufficient_truth_coverage` | bridge missing some realized top-36 skill → warning fires |
| 10 | `bridge_stale_warning` | snapshot evidence diverges from re-fetched nflreadr |
| 11 | Redirect handling | deprecated → confirmed survivor (follows); deprecated → non-confirmed (excludes pick) |
| 12 | published_date boundary | `== draft_date` excluded; `> draft_date` excluded; `< draft_date` included |
| 13 | parse_status behavior | `partial` included with warning; `untrusted` excluded by default; `untrusted` included with `--include-untrusted` |

Fixture location: `tests/fixtures/backtest_mock_draft/{snapshots,bridge_artifacts,nflreadr_synthetic}/`

### 6.3 Minimum evidence criteria to evaluate Backtest A

These are NOT model/B-gate acceptance thresholds. They are the **pre-B-gate** criteria for whether a Backtest A run is even informative. Locked in the spec so follow-up real-data curation has a concrete target.

| Criterion | Threshold |
|---|---|
| Minimum source count per class | ≥3 distinct analyst sources (matches §40 abstention floor) |
| Minimum mock-version count per source | ≥2 mocks per source (enables staleness measurement) |
| Minimum draft-class count | ≥3 historical draft classes (e.g., 2022, 2023, 2024) |
| Coverage-after-abstention threshold | ≥0.50 |
| Bridge coverage threshold for top-36 | ≥0.90 (with `insufficient_truth_coverage` warning if <1.00 — see §5.7 two-tier table) |
| Required diagnostic on threshold failure | run completes; artifact emits `acceptance_criteria_failed: list[...]` instead of silently succeeding |

### 6.4 Testing strategy (cockpit TDD)

Codex authors RED contract tests for each task; Claude implements GREEN. 8 test files mirroring S3 §10 pattern:

| Test file | Coverage |
|---|---|
| `test_subsystem_4_schema.py` | Pydantic models, validation rules |
| `test_subsystem_4_bridge.py` | bridge artifact, decision log, replay-over-genesis |
| `test_subsystem_4_ingestion.py` | snapshot ingestion, content_hash, leakage gate, parse_status, duplicates |
| `test_subsystem_4_aggregation.py` | ProspectConsensus, abstention tiers, n_sources boundaries |
| `test_subsystem_4_metrics.py` | 6 metrics on golden fixtures with known answers |
| `test_subsystem_4_b_gate.py` | gate status logic + synthetic safety hedge + two-tier threshold |
| `test_subsystem_4_b_stub.py` | B stub always-abstain + structured abstain shape |
| `test_subsystem_4_audit.py` | provisional-leak / market-data / inviolate-paths / banned-language / `decision_supported=False` |

Estimated ~60–80 contract tests across the 8 files (similar order to S3's 75).

## 7. Governance & guardrails

- **Read-only of any external source** in v1 (synthetic + nflreadr only); no scraping; no parser code for live sources
- **Mock-data isolation rule** (tightened from earlier draft): NO mock/ADP/market data in **S3 identity registry or S4 bridge** (those are identity truth). NO market/ADP data in **S4 artifacts** (snapshots and backtest reports). Mock snapshots and Backtest A outputs DO contain mock-derived pick/prospect data + computed metrics (that's the point of Backtest A), but those artifacts are **isolated diagnostic outputs** that **never feed identity truth, Engine A/B, PVO, Trade Lab, or model-training pipelines**. Bridge stores only identity + provenance + audit; never pick predictions.
- **No Engine A/B/PVO/Trade Lab/model-training feed.** Backtest A is overlay/inference-only diagnostic infrastructure
- **Frontend HOLD intact**; NOISE_BAND lock untouched; no model .pkl / manifest / contract changes
- **`decision_supported=False`** implicit throughout (S4 has no user-facing decision surfaces; this is validation infrastructure)
- **Banned David-facing language** absent in any S4 artifact, schema, or output
- **S3 artifacts byte-unchanged** — contract test enforces (see §2 inviolate paths)
- **Cross-domain semantic separation** — bridge says "this pre-draft prospect resolved to this NFL identity"; S3 says "these college rows are the same prospect." Never conflated
- **Backtest B remains gated** — contract test asserts the stub stays abstained in v1

## 8. Testing (≈60-80 tests in v1)

Organized by module per the §6.4 split. Build plan will follow this grouping.

### 8.1 Schema / models
- `ProspectNflBridgeEntry` shape (required + nullable fields, UDFA asymmetric)
- `MockSnapshotPick`, `MockSnapshotMetadata`, `MockSnapshot` round-trip serialization
- Pydantic `extra="forbid"` blocks unknown fields

### 8.2 Bridge workflow
- Discovery emits review queue + UDFA candidates + coverage matrix
- Promotion (`confirm`, `udfa`, `reject`, `defer`) writes correct three-point trail
- 1:1 invariant violation rejection
- UDFA asymmetric validation (5 strict / 4 required)
- Decision-log replay over genesis state reproduces artifact byte-identical
- `confirm` requires populated outcome fields; `udfa` requires non-empty `--evidence`

### 8.3 Ingestion
- 13 contract paths from the §6.2 matrix
- Strict `published_date < draft_date` boundary
- Same-tuple-same-hash idempotency
- Within-snapshot duplicate rejection

### 8.4 Aggregation
- n_sources boundary tiers (0/2/3/4/5/7)
- `dispersion_threshold` IQR calculation correct
- `staleness_days` calculation with mixed snapshot dates
- `abstention_reason` populated when applicable

### 8.5 Metrics
- Each of the 6 metrics on golden fixtures with known answers
- `top_36_skill_recall` denominator handling when bridge incomplete
- `udfa_false_positive_rate` semantics (only `projected_drafted` denominator)
- `round_bucket_accuracy` excludes `abstain` tier
- `early_pick_weighted_error` weight function exactly = `1/realized_pick_no`

### 8.6 B-gate
- Per-bucket pass/fail using v1 thresholds
- Synthetic safety hedge: `data_mode="synthetic"` forces `always_abstain_synthetic_data`
- Per-bucket `not_evaluable_synthetic` entries retain schema shape
- Two-tier threshold documented; B's stricter `1.00` requirement asserted as future-only constraint

### 8.7 B stub
- `run_backtest_b()` returns structured abstain shape
- Stub writes only its abstain-report file; reads no B artifacts
- `test_backtest_b_remains_abstained_in_v1` regression guard

### 8.8 Audit / coverage / governance
- S3 inviolate artifacts byte-unchanged via SHA-256 contract test
- No mock/ADP/market fields in any S4 schema or output (leakage-gate-style)
- No banned David-facing language in any output
- `decision_supported=False` recursively absent or False on all schemas
- Coverage matrix counts reconcile (`snapshots_used + leakage_excluded + untrusted_excluded == total_snapshots_found`)

## 9. Forward notes (acknowledged, deferred)

- **Per-source HTML parsers** (WalterFootball, NFL.com authors, Grinding-the-Mocks cross-check) are separate later increments, each with explicit ToS/legal review and parser-specific contract tests. Per reconciliation §27–31, ToS posture varies per source.
- **Backtest B implementation** (projected-capital → Engine A vs Regime B) lands only after Backtest A clears by round/position bucket on real data AND bridge coverage reaches 1.00 in the specific bucket being evaluated (§5.7).
- **Subsystem 1 (consensus aggregation)** replaces S4 v1's provisional aggregation later, without changing metric contracts (`aggregation_version` field enables clean handoff).
- **Historical 2018–2026 backfill** of bridge + snapshots is the follow-up curation workstream per the §6.3 evidence criteria.
- **Live per-source adapters (Subsystem 2)** remain NO-GO until permission + maturity gates pass (≈ Dec 2026–Apr 2027 per reconciliation §23).
- **Calibrated v1 thresholds** (`dispersion_threshold`, B-gate per-bucket MAE/coverage, `early_pick_weighted_error` weight function) are starting points; first real-data run informs calibration.
- **S1 within-source aggregation — HARD acceptance blocker on real data (Codex retrospective MEDIUM finding 2).** `s4_provisional_consensus_v1` aggregation is across all normalized picks, so sources with `>=2` versions (per §6.3 evidence criteria) overweight the consensus. **Real-data Backtest A artifacts MUST emit `within_source_aggregation_missing` in `acceptance_criteria_failed`** unless EITHER: (a) `data_mode == "synthetic"` (synthetic runs are exempt), OR (b) `metadata.within_source_aggregation_applied` is `true` AND `aggregation_version != "s4_provisional_consensus_v1"`. Subsystem 1 (consensus aggregation), when written, MUST aggregate within-source first (most recent version per source OR temporal decay) before aggregating across sources, AND MUST set `metadata.within_source_aggregation_applied = true` on its emitted artifacts. The explicit boolean flag + `aggregation_version` check avoids string-substring guessing on the version identifier.
- **IQR computation method locked under `aggregation_version`.** v1 uses `statistics.quantiles(pick_nos, n=4, method="exclusive")` (Python default). Changing the method invalidates replay reproducibility and requires bumping `aggregation_version` plus a spec patch. Plan Task 8 carries contract test `test_aggregation_iqr_uses_exclusive_quantiles` that locks the choice with a fixture where exclusive and inclusive diverge.

## 10. Counter-argument (Rule 5 — mandatory)

1. **B stub adds surface area for negligible value.** A future agent could just see the stub function and assume it's the right place to drop B code without consulting the gate. *Mitigation:* contract test (`test_backtest_b_remains_abstained_in_v1`) explicitly asserts the abstain behavior — flipping it requires deliberate test edit + cockpit review. Stub docstring + spec reference embedded in the abstain reason string.

2. **Provisional aggregation in v1 risks drift before S1 calibrates.** `s4_provisional_consensus_v1` could become the de facto aggregation if S1 keeps slipping. *Mitigation:* `aggregation_version` field tags it as provisional everywhere; S1 spec when written will explicitly replace this layer; contract assert that metric contracts don't change across the swap.

3. **Synthetic-only v1 means harness shape might not match real-world data quirks.** Real mocks have things synthetic can't anticipate (e.g., named "best player available" instead of a specific player, or partial pick orderings). *Mitigation:* §6.3 acceptance criteria locked in spec; first real-data run is a milestone that surfaces shape gaps; v1 is a deliberate first iteration.

4. **Manual paste workflow may be tedious enough to discourage curation.** If curating one class is 1000 entries of manual entry, David may not actually populate real data. *Mitigation:* the contract test surface still proves harness correctness regardless; the §6.3 acceptance criteria can be reduced (e.g., 1 class with ≥3 sources first) if full curation proves prohibitive. Per-source parsers in later increments dramatically reduce curation cost.

5. **Bridge stale-warning re-fetch at every backtest run is expensive.** If nflreadr is slow or rate-limited, every Backtest A run pays the cost. *Mitigation:* nflreadr is already cached locally per existing Phase 17/18 usage patterns; re-fetch is a cache hit in normal operation; warning fires only on genuine divergence.

6. **Cross-domain bridge replay-over-genesis assumes genesis is empty.** If a future increment pre-seeds the bridge from historical research, replay precision breaks silently. *Mitigation:* spec explicitly locks "v1 bridge is never pre-seeded"; pre-seeding requires its own spec amendment with new replay-precision wording (mirrors S3 §6.3 discipline).
## 11. Architecture Decision Note — 2026-05-28 strategic pause

This section records the resolution of a mid-build strategic pause taken on 2026-05-28 after the cockpit (Codex + Gemini + Claude) identified 4 governance risks during Task 9 RED authoring. The pause was authorized by David; cockpit converged on the resolutions below before Task 9 GREEN resumed.

### 11.1 Risk A — Specialization boundary (no parallel generic harness)

S4 is a **specialized pre-draft diagnostic harness** for mock-consensus signal evaluation against realized NFL draft capital. It MUST NOT evolve into a generic backtest platform.

Locked constraints:
- **Locked two-module split.** S4's analytics engine (snapshot ingestion, normalization, ProspectConsensus aggregation, abstention gates, bridge join, metrics, B-gate evaluation, artifact writer) lives strictly in `src/dynasty_genius/eval/backtest_mock_draft.py`. S4's cross-domain identity bridge (schemas, validation, review-queue management, promotion lifecycle, replay) lives strictly in `src/dynasty_genius/identity/prospect_nfl_bridge.py` under the identity package substrate.
- **Phase 10/11 inviolate paths.** S4 code is strictly barred from modifying or importing the following Phase 10/11 + Phase 12 production assets. These remain byte-unchanged for the duration of S4 work; Task 14 audit asserts this via SHA-256 contract test:
  - `src/dynasty_genius/eval/backtest_harness.py`
  - `src/dynasty_genius/eval/backtest_artifact.py`
  - `src/dynasty_genius/eval/backtest_metrics.py`
  - `src/dynasty_genius/eval/backtest_report.py`
  - `src/dynasty_genius/eval/model_card.py`
  - `src/dynasty_genius/eval/market_snapshot_store.py`
  - `scripts/run_backtest.py`
  - `app/api/routes/trust_surface.py`
- **Idiom reuse, not code reuse.** S4 reuses Phase 10/11 design idioms for versioning-field naming (`metric_version`, `aggregation_version`, `gate_version`), metadata-recording structure, gate-evaluation shape, and report structure. S4 does NOT modify or import any Phase 10/11 asset listed above.
- New backtest needs that are NOT pre-draft mock-consensus diagnostic MUST extend the existing Phase 10/11 harness, not S4.

### 11.2 Risk B — Selection bias discipline (`tracked_confirmed_prospect_universe`)

Per S3 design, the prospect identity bridge is curated by David. ALL bridged prospects are a non-random sample. S4's metrics therefore describe signal quality only over the David-curated tracked-and-confirmed universe, NOT over all pre-draft prospects.

Locked constraints:
- **Universe naming.** All S4 artifact metadata MUST name the population: `metric_universe: "tracked_confirmed_prospect_universe"`.
- **Mandatory caveat (prominently displayed).** All S4 artifacts MUST emit `cohort_selection_bias_caveat` as a non-null string with explicit text: `"Metrics reflect signal quality only over the David-curated S3 confirmed-prospect universe, which is a non-random sample; per the constitution's 'Truth over convenience' tenet, results do not generalize to all pre-draft prospects."` Any downstream diagnostic report, CLI stdout summary, or future trust surface that displays S4 metrics MUST prominently display this caveat alongside the metrics. Hiding the caveat in nested JSON metadata is a governance violation.
- **Segmented coverage counts (no conflation).** S4 coverage reporting MUST explicitly separate:
  - `consensus_unbridged_count`: number of distinct prospects emitting a ProspectConsensus (Task 8) who do NOT have an active bridge entry for the draft year.
  - `confirmed_class_unbridged_count`: number of distinct prospects in the S3 registry for the draft year with `verification_status="confirmed"` who do NOT have a bridge entry.
  - `orphan_bridges_detected`: list of bridge entries for the draft year whose `prospect_uuid` does not resolve to an S3 entry, or resolves but is not `confirmed`. Reported as active identity drift/corruption; NEVER conflated with the unbridged counts above.
- **Hard execution block.** The S4 runner (`run_backtest_a.py` per Task 12) MUST hard-fail (exit code 1) and refuse to write metrics into `backtest_a_result.json` if any of: `consensus_unbridged_count > 0`, `confirmed_class_unbridged_count > 0`, or `len(orphan_bridges_detected) > 0`. When the hard block fires the artifact's `metrics` block MUST be `null` (or omitted); the artifact retains only the diagnostic report listing the blocking unbridged/orphan prospects. An informative run requires all three counts to be zero.
- This gate is distinct from `coverage_after_abstention` — that measures post-abstention metric coverage; this gate measures bridge coverage.

### 11.3 Risk C — Decision destination & transitive-laundering prevention

S4 is strictly trust-layer / diagnostic infrastructure. Its outputs are barred from feeding Engine A or Engine B predictive features per the constitution's locked anti-market-data ruling.

Locked constraints:
- **Allowed destinations.** S4's sole near-term decision destinations are: (i) govern mock-consensus eligibility as a pre-draft Market Overlay on future decision surfaces (e.g., Rookie Board), AND (ii) inform Backtest B gating per §5.5.
- `decision_supported=False` recursively on all S4 schemas (already locked per §6.3 + §7).
- **Anti-laundering transitive bar.** Any path — direct OR transitive (including via intermediate overlay tables, trust-surface views, feature-store tables, or Bayesian-prior shims) — from mock-consensus data, mock snapshots, or S4 backtest results into Engine A or Engine B feature extraction, training pipelines, or player scoring models is strictly, unconditionally barred by this spec and its v1 implementation. A future amendment requires a David-approved constitution-compatible spec patch plus a verified validation report proving statistically significant out-of-sample predictive lift.
- **AST scan import audit.** Task 14 MUST add a pytest contract/audit test in `tests/contract/test_subsystem_4_audit.py` using AST-based static checks. Because contract tests run in CI, this enforces the boundary without requiring changes to repo lint/pre-commit policy. The test MUST scan all Engine A, Engine B, PVO, Trade Lab, and model-training source files and FAIL on either:
  - Imports of S4 modules: `dynasty_genius.eval.backtest_mock_draft`, `dynasty_genius.identity.prospect_nfl_bridge`.
  - File reads or path references to S4 runner artifacts: `app/data/backtest/mock_draft/**/backtest_a_result.json`, `app/data/backtest/mock_draft/**/backtest_b_abstain.json`.
- **No agent amendment authority.** The boundary defined here is a locked analytical ruling. No agent has authority to relax, amend, or bypass it. Any agent plan, spec patch, or code modification that attempts to route mock or market data into Engine A/B training is an automatic escalation trigger requiring an immediate hard stop, a logged failure in the daily ledger, and rollback of the offending changes.

### 11.4 Risk D — Pace discipline

All future S4 contract decisions require deliberate cockpit debate, not RED-time casual locks. Task 9 schema is explicitly re-debated in §11.5 below.

### 11.5 Task 9 schema refinements (replaces prior provisional 14-field shape)

The Task 9 `RealizedOutcome` + `join_bridge_to_realized` contracts MUST cover the following edge cases, each as an explicit named test:

1. **Truth disappearance.** Drafted bridge entry with `gsis_id=X` but `X` absent from re-fetched `nflreadr_current` → `bridge_stale_warning=True` with `truth_row_missing` warning string (NOT silently `False`).
2. **Duplicate `gsis_id` in `nflreadr_current` (fail-closed).** If duplicate `gsis_id` rows are present, S4 MUST emit a critical `nflreadr_duplicate_gsis_id_warning`, refuse current-truth comparison for the affected prospect (no overwrite, no last-row-wins), and add the failure to `acceptance_criteria_failed`.
3. **Compound-key wrong-year truth mismatch (hard conflict).** Truth lookups MUST use the compound key `(gsis_id, draft_year)`. If the lookup returns no row, OR returns a row whose `draft_year` differs from the bridge entry's `draft_year` for that `gsis_id`, S4 MUST emit `truth_row_wrong_year_warning`, write the affected entry to the review queue for manual audit, and add `wrong_year_truth_collision` to `acceptance_criteria_failed` (hard exit block).
4. **Missing `evidence_snapshot` on drafted entry (hard block).** If `entry.udfa=False` but `evidence_snapshot is None`, S4 MUST refuse to fall back to a clean `gsis_id`-only comparison: emit `evidence_snapshot_missing_warning`, mark the comparison `stale/evidence_incomplete`, and add the failure to `acceptance_criteria_failed`.
5. **Unbridged coverage semantics.** Unbridged prospects are reported in the coverage matrix and cause the hard-block gate in §11.2; therefore metric computation is skipped entirely for nonzero unbridged counts. If a future diagnostic-only mode permits partial metrics, those prospects MUST be excluded from numerators and denominators and the run MUST remain non-informative.
6. **Pick/round/team divergence in stale tuple (with team-code normalization).** If `draft_pick_no`, `draft_round`, OR `nfl_team` divergence is detected between the bridge top-level and current `nflreadr_current`, set `bridge_stale_warning=True` with an explicit reason string indicating which field(s) diverged. To prevent false positives from team relocations/rebrandings (e.g., `"OAK"` ↔ `"LVR"`, `"SDG"` ↔ `"LAC"`, `"LAR"` ↔ `"LA"`, `"WAS"` ↔ `"WSH"`), team codes MUST pass through a dedicated `normalize_team_code` helper before comparison. The helper's whitelist of equivalence classes is recorded in artifact metadata as `team_code_normalization_version` for replay reproducibility.

### 11.6 Authorization audit trail

This patch was authored by Claude after cockpit convergence on 2026-05-28 (~22:42 ET). Codex and Gemini independently produced critical reflections on the 4 risks, then independently produced adversarial reviews of the v1 draft patch (full responses captured in `docs/agent-ledger/2026-05-28.md`).

This strategic pause was invoked under the supreme authority of the Dynasty Genius Product Constitution (`docs/governance/00-product-constitution.md`) — specifically the Prime Directive ("Be right, not fast") and the Truth-over-convenience tenet — and the North Star Architecture (`docs/governance/01-north-star-architecture.md`) which forbids "a collection of disconnected tools" and locks the market-data leakage boundary.

David authorized the strategic pause and the patch effort. Task 9 GREEN was halted at branch `feature/subsystem-4-backtest-harness` commit `a41e0c6` — which represents the Task 8 branch tip and the Task 9 RED-only test state, carrying zero Task 9 GREEN implementation code — pending commit and gating of this patch.
