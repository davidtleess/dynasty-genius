# Roster Audit — Increment 1: API Contract Hardening — Design Spec

**Date:** 2026-06-18
**Status:** v3 (strategic-pause caveats-contract patch)
**Authored by:** Claude Code
**Cockpit design poll:** Codex (technical) CONCUR + findings F1–F6 · Gemini (governance) CONCUR + §4 fail-closed finding
**Phase:** Phase 12 (Frontend) decision-surface sequence — Roster Audit (next surface after Surface-1/2/3 + Model Trust Console)

## Round-1 findings integrated in this v2

- **G1 (Gemini, §4):** trust artifact unavailable must be **fail-closed**, not omitted — populate every position `EXPERIMENTAL`.
- **F1 (Codex, §3.2):** `dvs_engine` is `str` (`"A"|"B"|"blend"`), not float — type fixed.
- **F2 (Codex, §3.4/AC-6):** add a per-player `model_status_applicability` invariant; test an Engine-A WR under a VALIDATED WR position map.
- **F3 (Codex, §4/§5):** reconcile malformed-data handling — isolated-row drop vs systemic 503.
- **F4 (Codex, AC-1):** the primary leakage guard is an **exact allowlist** + a recursive forbidden market-key set, not only a `market_overlay` denylist.
- **F5 (Codex, §4):** trust freshness — live artifacts; missing/stale/malformed → degraded + fail-closed, never omitted keys.
- **F6 (Codex, AC-5):** banned-vocab coverage must include **all** David-facing strings, not just three fields.
- **OQ rulings (both lanes):** OQ-1 → LIVE; OQ-2 → drop-isolated / 503-systemic; OQ-3 → adopt Surface-3 wrapped fields and extend to all David-facing text.
- **SP-1 (Codex/Gemini, Task 7 strategic pause):** top-level player `caveats`
  are PVO free text, not token-only. Treating them as `SAFE_TOKENS` destroys
  uncertainty/provenance text and falsely emits `evidence_suppressed_banned_term`.
  Patch: top-level player `caveats` are free-text evidence filtered by banned
  vocabulary; `SAFE_TOKENS` remains for genuinely token-only nested/structural
  fields.

---

## 1. Motivation

Roster Audit is the decision surface for David's most frequent dynasty decisions — roster hold / sell / replace / develop (Product Constitution §"concrete dynasty decisions"). Its North Star gate ("Roster Audit remains experimental until Engine B is credible") was satisfied by Step 0.5, which validated Engine B for WR/RB/TE (QB PROVISIONAL).

The endpoint already exists (`GET /api/roster/audit`) and `run_audit_pvo()` already returns rich per-player data. The problem is the **contract**: the route returns a bare `dict`, so OpenAPI emits `additionalProperties: true` and the frontend client types it as `z.record(unknown)`. A UI over an untyped contract can silently overclaim or mishandle provisional/market caveats. So the first increment is **contract-first**: harden the API response contract before any UI.

### 1.1 Live finding this increment corrects

`app/services/roster_auditor.py` (~lines 606–617): `run_audit_pvo()` calls `enrich_pvo_list_with_market_overlay(pvos)` then returns `[pvo.dict() for pvo in pvos]`. The raw PVO serialization therefore **includes a populated `market_overlay` on every player**, while the response advertises a `"no_market_overlay"` caveat (lines 51/73). The caveat is currently inaccurate. This is not a training-leakage violation (a post-scoring overlay is permitted in decision surfaces) but is a stale-caveat + untyped-passthrough defect. Increment 1's curated, **allowlist-based** DTO excludes `market_overlay`, making the caveat true again — proven by the allowlist test (AC-1).

## 2. Scope

**In scope (Increment 1 — backend only):** typed `RosterAuditResponse` / `RosterAuditPlayer` / `QBContextCard`; `response_model` + explicit allowlist DTO mapping (no raw `pvo.dict()`); market/value exclusion; live `model_status_by_position`; fail-closed degraded contract; banned-vocab suppression on all David-facing text; OpenAPI snapshot + typed TS/Zod client + drift-guard + contract tests.

**Out of scope (deferred):** the read-only Roster Audit **UI** (Inc2); **per-player** `model_status` value (per-position map + per-player applicability flag suffice); roster-level risk summary; any scoring / Engine A/B / model-artifact / analytical-logic change.

## 3. The Contract

### 3.1 `RosterAuditResponse` (envelope)

| Field | Type | Notes |
|---|---|---|
| `status` | `Literal["active","degraded"]` | `"degraded"` per §4 |
| `engine` | `str` | e.g. `"pvo_assembler_v1"` |
| `reason` | `str` | assembler reason |
| `model_status_by_position` | `dict[str, Literal["VALIDATED","PROVISIONAL","EXPERIMENTAL"]]` | Engine-B trust per position, **sourced LIVE** from the trust-surface artifact at request time (OQ-1). **Never omits a position**: if a position's trust artifact is missing/stale/malformed, it is set `EXPERIMENTAL` (fail-closed, G1/F5) and a named caveat is added. Engine-B-trust-level only — §3.4 |
| `caveats` | `list[str]` | named tokens incl. degraded/fail-closed reasons |
| `players` | `list[RosterAuditPlayer]` | curated allowlist DTOs |
| `qb_context_cards` | `list[QBContextCard]` | typed QB-context envelopes |
| `dropped_player_count` | `int = 0` | count of rows dropped for corruption (§4) |
| `decision_supported` | `Literal[False] = False` | coerced; OpenAPI `const: false` |

### 3.2 `RosterAuditPlayer` (curated allowlist; NO market/value fields)

Built by an **explicit allowlist mapper** from `PlayerValueObject` — only the fields below are emitted; everything else (incl. `market_overlay` and any market/value field, present or future) is excluded by construction.

- **Identity:** `player_id: str`, `full_name: str`, `position: str`, `nfl_team: str | None`, `age: float | None`, `sleeper_id: str | None`, `is_prospect: bool`, `draft_class: int | None`, `nfl_draft_pick: int | None`, `nfl_draft_round: int | None`
- **Model metadata:** `engine_used: str | None`, `model_version: str | None`, `model_grade: str`, **`dvs_engine: Literal["A","B","blend"] | None`** (F1 — engine label, not a score)
- **Position-status applicability (F2):** `model_status_applies: bool` — `True` only when the player is Engine-B-scored (so the UI may apply `model_status_by_position[position]`); `False` for Engine-A rookies / non-modeled rows, which are governed solely by their own `model_grade`/`caveats`
- **Scores (nullable until decision-grade):** `dynasty_value_score`, `projection_1y/2y/3y`, `xvar`, `dvs_pct` (all `float | None`)
- **Signal:** `signal_completeness: float`, `inputs_present: list[str]`, `inputs_missing: list[str]`
- **Evidence — free-text, banned-vocab-suppressed (Surface-3 wrapped, OQ-3/F6):** `counter_argument: CounterArgumentField`, `top_drivers: EvidenceListField`, `risk_flags: EvidenceListField`
- **`caveats: list[str]`** — PVO free-text uncertainty/provenance caveats filtered
  through banned-language suppression, not token-only. Clean assembler caveats
  must survive; caveats containing banned terms are removed and replaced by
  `evidence_suppressed_banned_term` (§3.5, SP-1).
- **`roster_audit: RosterAuditSignals | None`** — existing typed age-cliff model; its free-text-ish fields (`signal_drivers`, `age_value_context`, `signal`) are token-only and constrained to the known enum set (§3.5)
- **`decision_supported: Literal[False] = False`**

### 3.3 `QBContextCard`

`player_id`, `full_name`, `identity_coverage: Literal["FULL","PARTIAL","NONE"]`, `context_role: Literal["context_signal"]`, the `QB_CONTEXT_COLUMNS` numeric stat fields, `qb_context_annotations: list[str]`, `qb_context_caveats: list[str]`, `source_qb_context_annotations: str`, `decision_supported: Literal[False] = False`. Annotations/caveats are token-only and constrained per §3.5 (F6).

### 3.4 `model_status_by_position` is Engine-B-trust-level only (F2)

The map reflects **Engine-B** position-level validation from Step 0.5. A position can be VALIDATED while an individual rookie at that position is Engine-A / `PRE_MODEL`. Therefore each player carries `model_status_applies` (§3.2): the UI may apply the position status **only** when `model_status_applies == True`. Asserted by AC-6 (an Engine-A WR under a VALIDATED WR map must have `model_status_applies == False` and render its own grade/caveats).

### 3.5 David-facing text classification (F6/OQ-3)

Every David-facing string is either:
- **Free-text → suppressed by banned vocabulary:** `counter_argument`,
  `top_drivers`, `risk_flags`, and top-level player `caveats`. `counter_argument`
  uses `CounterArgumentField`; list-like evidence uses the same banned-language
  filtering pattern as `EvidenceListField`. Clean PVO caveats such as signal
  completeness, draft-capital provenance, and model-gate disclosures must not be
  token-stripped.
- **Token-only → constrained:** `roster_audit.signal_drivers`/
  `age_value_context`/`signal`/`liquidity_risk`/nested `caveats`,
  `qb_context_annotations`/`qb_context_caveats`,
  `source_qb_context_annotations`, trust/drop caveats. These must contain only
  values from a known safe-token allowlist; AC-5 asserts no banned term and no
  unknown token appears.

## 4. Degraded-state + failure contract (G1/F3/F5)

- **Hard failure (no honest render):** missing env / roster config → **422** (`roster_config_error`); required roster snapshot / Engine-B scoring / systemic mapper failure / **all rows invalid** → **503** (`roster_dependency_unavailable`). Never silent `{}`.
- **Degraded (still renders honestly), `status="degraded"` + named caveat, `decision_supported` never flips:**
  - **Isolated corrupt player row** (some valid rows remain) → drop the row, increment `dropped_player_count`, add `player_row_dropped_corrupt` caveat (F3/OQ-2).
  - **Trust artifact missing/stale/malformed** → affected positions set `EXPERIMENTAL` (fail-closed, G1/F5) + `trust_status_unavailable` caveat; keys never omitted.
  - **Optional artifact** (universe_pvo rookie reconciliation, etc.) unavailable → named caveat.

## 5. Robustness boundary (operating-loop §8)

- **API misuse** (wrong types into the mapper) → fail loud.
- **Data corruption** (malformed PVO shape): isolated row → drop-to-caveat + count (§4); **systemic** (mapper raises, or all rows invalid) → 503 (§4). §4 and §5 share one rule — no conflict.
- **Semantic/range** (non-finite scores) → producer responsibility; the DTO passes `None` with existing completeness caveats, never invents values.

## 6. Deliverables

1. `app/api/routes/roster.py` + a `roster_audit_models.py`: the three Pydantic models + the **allowlist mapper**.
2. `response_model=RosterAuditResponse`; explicit mapping; live trust status; degraded/failure handling.
3. Regenerated `frontend/openapi.json` + TS/Zod client.
4. Drift-guard test (mirrors `test_openapi_drift_contract.py`).
5. Contract/acceptance tests (§7).

## 7. Acceptance criteria

- **AC-1 (allowlist leakage guard — primary, F4):** the DTO emits **only** the §3.2 allowlisted keys; a test injects `market_overlay` **and** a synthetic future field onto a PVO and asserts neither appears anywhere (recursive), plus an explicit forbidden-set check for `market_overlay`, `market_value`, `market_percentile`, `model_minus_market_delta`, `divergence_flag`, and any `market_`/`value_above_replacement` key.
- **AC-2 (decision_supported lock):** recursive assert no `decision_supported: true` anywhere.
- **AC-3 (typed OpenAPI):** the route no longer emits `z.record(unknown)`/`additionalProperties: true`; references `RosterAuditResponse`; snapshot drift-guard passes.
- **AC-4 (failure/degraded honesty):** isolated corrupt row → dropped + `dropped_player_count`++ + caveat, others render; trust artifact missing → positions `EXPERIMENTAL` + caveat (fail-closed); systemic/all-invalid → 503; config → 422; never silent `{}`.
- **AC-5 (banned-vocab, all David-facing text, F6/SP-1):** injected banned terms
  in free-text fields are suppressed (`evidence_suppressed_banned_term`); clean
  top-level PVO caveats survive; token-only fields reject banned + unknown
  tokens.
- **AC-6 (position-status invariant, F2):** an Engine-A WR / non-modeled player under a VALIDATED WR map has `model_status_applies == False` and renders its own `model_grade`/caveats.
- **AC-7 (no regression):** full Python suite green; `"no_market_overlay"` caveat now accurate.

## 8. Guardrails / constitution alignment

`decision_supported = False` throughout; no banned David-facing output (no buy/sell/hold imperatives, no verdict/tier/confidence fields); market overlay physically excluded from the model-lane response; no market data into Engine A/B; QB PROVISIONAL via the position map; read-only over PVO + league context; no new scoring logic.

## 9. Open questions — RESOLVED (round 1)

- **OQ-1 → LIVE** trust artifact per request (mtime-aware if cached; never outlive artifact changes).
- **OQ-2 → isolated** malformed row dropped with named caveat + count; **systemic / all-invalid → 503**.
- **OQ-3 → adopt** Surface-3 wrapped evidence fields, extended to all David-facing text via §3.5 classification.
