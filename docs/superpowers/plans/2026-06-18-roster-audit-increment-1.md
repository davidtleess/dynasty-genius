# Roster Audit Increment 1 — API Contract Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the untyped `GET /api/roster/audit` response (`dict` → `z.record(unknown)`) with a typed, allowlist-mapped, leakage-safe contract so a future read-only UI cannot overclaim.

**Architecture:** Typed Pydantic response models + an explicit **allowlist** DTO mapper (no raw `pvo.dict()`, no `extra="allow"`); Engine-B trust status sourced **live + fail-closed** via `BacktestResult.load`; nested `decision_supported` and token-only fields coerced/validated centrally; honest 503/422/degraded contract. Backend only — UI is Increment 2.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, pytest; frontend OpenAPI codegen (`npm --prefix frontend run openapi-gen`).

**Spec:** `docs/superpowers/specs/2026-06-18-roster-audit-increment-1-contract-design.md` (dual-CLEARED, committed `a65b583`).

## Plan v4 — round-3 finding integrated

- **R3-1 scalar token-only validation:** `validate_token()` (T2) added; `_map_signals` (T3) now validates the scalar token-only fields `signal` / `age_value_context` / `liquidity_risk` against `SAFE_TOKENS` (invalid → `None` + `evidence_suppressed_banned_term`); test `test_scalar_token_fields_validated` added.

## Plan v3 — round-2 findings integrated

- **R2-1 SAFE_TOKENS seeded from REAL producers** (verified in `roster_auditor.py`) — see T2/T7; a wrong list would strip legitimate tokens.
- **R2-2 `source_qb_context_annotations` validated** through SAFE_TOKENS (holds `cfbd_qb_context_annotations`) — T4.
- **R2-3 `biological_debt_score` RETAINED** in `RosterAuditSignalsView` — T2/T3.
- **R2-4 stale-detection implemented** (manifest carries `positions.{POS}.model_version`): artifact `model_version` ≠ manifest → `EXPERIMENTAL` + `trust_status_stale` — T1.
- **R2-5 QB-card drop** → `status="degraded"` + `qb_context_card_dropped_corrupt` caveat (parallel to player rows) — T4.
- **R2-6 F6 scope corrected:** the `engine_used == "engine_b"` claim is scoped to the **`run_audit_pvo` endpoint path** (repo-wide, `pvo_assembler` can carry `engine_a_*_ridge` in `engine_used`); keep `engine_a`/None negative tests — T3.

## Plan v2 — round-1 cockpit findings integrated

- **F1/G(token) — AC-5 token-only enforced** centrally from the mapper/envelope (T2 validator, T3/T4 wiring); `SAFE_TOKENS` seeded from real `roster_auditor.py` producers + a completeness test.
- **F2/G(QB) — no `extra="allow"`**: `QBContextCard` explicitly types the 5 `QB_CONTEXT_COLUMNS`; `source_*` provenance excluded from the David-facing card (T2).
- **F3 — nested `decision_supported` leak**: curated `RosterAuditSignalsView` with `decision_supported: Literal[False]` (T2/T3) + recursive test (T5).
- **F4 — `BacktestResult.load`** used (not hand-parse); valid fixture = the real published `trust_surface/latest/backtest_result_{POS}.json` (T1).
- **F5 — stale/malformed trust**: `stale` defined as artifact `model_version` ≠ live manifest `model_version`; missing/malformed/stale → fail-closed `EXPERIMENTAL` + caveat; tests added (T1).
- **F6 — `model_status_applies`**: for the `run_audit_pvo` endpoint path `engine_used` is `engine_a`/`engine_b`, so `== "engine_b"` is exact (see R2-6 for the repo-wide scope note); negative tests for `engine_a`/None added (T3).
- **F7 — T6 RED-first** reframed: RED = snapshot drift test fails until regen; + generated-client not-`Record<unknown>` assertion.
- **F8 — T5 AC-2** strengthened: recursive JSON assertion + nested `roster_audit.decision_supported=true` fake.
- **Minor:** `Field(default_factory=list)` for all list defaults.

**Reused existing code:** `players.py` (`CounterArgumentField`, `EvidenceListField`, `_counter_argument_field`, `_evidence_list_field`, `_contains_banned`); `backtest_artifact.BacktestResult.load`; `engine_a_contract.QB_CONTEXT_COLUMNS`; `roster_auditor.run_audit_pvo`/`RosterConfigError`; `player_value_object.RosterAuditSignals` (as the source we curate).

**Verified producer tokens (F1 seed):** `signal` ∈ {`past_cliff`,`at_cliff`,`approaching_cliff`,`no_age_signal`}; `signal_drivers` ∈ {`age_past_position_cliff`,`age_at_position_cliff`,…}; `age_value_context` ∈ {`past_cliff_depreciation_risk`,`approaching_cliff_high_projection`,…}; `liquidity_risk` ∈ {`HIGH_NO_SECOND_ROUND_ESCAPE_HATCH`,`MEDIUM_LIMITED_ESCAPE_HATCH`,`LOW`}; caveats ∈ {`no_market_overlay`,`engine_b_experimental_v1_fallback`,…}. T2 seeds `SAFE_TOKENS` from these; T7 completeness test fails if a producer emits an unlisted token.

---

## File Structure

- Create `app/api/routes/roster_audit_models.py` — models (`RosterAuditResponse`, `RosterAuditPlayer`, `RosterAuditSignalsView`, `QBContextCard`), `SAFE_TOKENS` + `validate_tokens()`, `load_model_status_by_position()`, `map_player()`, `assemble_response()`.
- Modify `app/api/routes/roster.py` — `response_model` + assembler + 422/503.
- Create `tests/contract/test_roster_audit_contract.py`.
- Modify `tests/contract/test_openapi_drift_contract.py`.
- Modify `frontend/openapi.json` + `frontend/src/lib/api/*` (generated).

---

## Task 1: Live, fail-closed trust loader (BacktestResult.load)

**Files:** Create `app/api/routes/roster_audit_models.py`; Test `tests/contract/test_roster_audit_contract.py`

- [ ] **Step 1: Write failing tests (valid / missing / malformed / stale)**

```python
import json, shutil
from pathlib import Path
from app.api.routes import roster_audit_models as ram

REAL = Path("app/data/backtest/trust_surface/latest")

def test_trust_valid_from_published_artifact(monkeypatch):
    monkeypatch.setattr(ram, "TRUST_DIR", REAL)
    status, caveats = ram.load_model_status_by_position(["WR"])
    assert status["WR"] in {"VALIDATED", "PROVISIONAL", "EXPERIMENTAL"}

def test_trust_missing_is_failclosed(tmp_path, monkeypatch):
    monkeypatch.setattr(ram, "TRUST_DIR", tmp_path)
    status, caveats = ram.load_model_status_by_position(["QB"])
    assert status["QB"] == "EXPERIMENTAL" and "trust_status_unavailable" in caveats

def test_trust_malformed_is_failclosed(tmp_path, monkeypatch):
    (tmp_path / "backtest_result_RB.json").write_text("{ not json")
    monkeypatch.setattr(ram, "TRUST_DIR", tmp_path)
    status, caveats = ram.load_model_status_by_position(["RB"])
    assert status["RB"] == "EXPERIMENTAL" and "trust_status_unavailable" in caveats

def test_trust_stale_model_version_failclosed(tmp_path, monkeypatch):  # R2-4
    d = tmp_path / "t"; shutil.copytree(REAL, d)
    m = json.loads((d / "manifest.json").read_text())
    pos = next(iter(m["positions"]))
    m["positions"][pos]["model_version"] = "engine_b_vSTALE"
    (d / "manifest.json").write_text(json.dumps(m))
    monkeypatch.setattr(ram, "TRUST_DIR", d)
    status, caveats = ram.load_model_status_by_position([pos])
    assert status[pos.upper()] == "EXPERIMENTAL" and "trust_status_stale" in caveats
```

- [ ] **Step 2: Run to verify fail** — `.venv/bin/python3.14 -m pytest tests/contract/test_roster_audit_contract.py -k trust -v` → FAIL (no `load_model_status_by_position`).

- [ ] **Step 3: Implement**

```python
from __future__ import annotations
import json
from pathlib import Path
from src.dynasty_genius.eval.backtest_artifact import BacktestResult

TRUST_DIR = Path("app/data/backtest/trust_surface/latest")
_VALID = {"VALIDATED", "PROVISIONAL", "EXPERIMENTAL"}

def _manifest_versions() -> dict[str, str]:
    try:
        m = json.loads((TRUST_DIR / "manifest.json").read_text(encoding="utf-8"))
        return {k.upper(): v.get("model_version") for k, v in m.get("positions", {}).items()}
    except Exception:
        return {}

def load_model_status_by_position(positions: list[str]) -> tuple[dict[str, str], list[str]]:
    """LIVE per-position Engine-B model_status via BacktestResult.load. Fail-closed:
    missing / malformed / out-of-domain / STALE -> EXPERIMENTAL + caveat; keys NEVER
    omitted (no fail-open). Stale (R2-4) = artifact model_version != live manifest model_version."""
    manifest = _manifest_versions()
    status: dict[str, str] = {}
    caveats: set[str] = set()
    for pos in sorted({p.upper() for p in positions}):
        path = TRUST_DIR / f"backtest_result_{pos}.json"
        try:
            result = BacktestResult.load(path)
            value = result.promotion_gate.model_status
            if value not in _VALID:
                status[pos] = "EXPERIMENTAL"; caveats.add("trust_status_unavailable")
            elif pos in manifest and result.model_version != manifest[pos]:
                status[pos] = "EXPERIMENTAL"; caveats.add("trust_status_stale")
            else:
                status[pos] = value
        except Exception:
            status[pos] = "EXPERIMENTAL"; caveats.add("trust_status_unavailable")
    return status, sorted(caveats)
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(roster-audit): live fail-closed trust loader via BacktestResult.load (Inc1 T1)"`

> **Stale (R2-4) — now implemented, not deferred:** the live `manifest.json` carries `positions.{POS}.model_version` (verified). The loader compares each artifact's `model_version` to the manifest's; mismatch → `EXPERIMENTAL` + `trust_status_stale`. Covered by `test_trust_stale_model_version_failclosed`.

---

## Task 2: Contract models (no extra=allow), curated signals, token validator

**Files:** Modify `roster_audit_models.py`; Test `tests/contract/test_roster_audit_contract.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from pydantic import ValidationError
from app.api.routes.roster_audit_models import (
    RosterAuditResponse, QBContextCard, validate_tokens, SAFE_TOKENS, ROSTER_AUDIT_PLAYER_FIELDS,
)

def test_decision_supported_locked():
    with pytest.raises(ValidationError):
        RosterAuditResponse(status="active", engine="e", reason="r",
            model_status_by_position={}, decision_supported=True)  # type: ignore[arg-type]

def test_qb_card_rejects_unknown_field():  # F2: no extra=allow
    with pytest.raises(ValidationError):
        QBContextCard(player_id="q", full_name="QB", identity_coverage="FULL",
            source_qb_context_annotations="x", market_value=99)  # type: ignore[call-arg]

def test_validate_tokens_strips_unknown_and_banned():  # F1
    clean, caveats = validate_tokens(["past_cliff", "elite", "totally_unknown"])
    assert clean == ["past_cliff"] and "evidence_suppressed_banned_term" in caveats
```

- [ ] **Step 2: Run to verify fail** — `... -k "locked or qb_card or validate_tokens" -v` → FAIL.

- [ ] **Step 3: Implement**

```python
from typing import Literal
from pydantic import BaseModel, Field
from app.api.routes.players import (
    CounterArgumentField, EvidenceListField, _contains_banned,
)

# Single source of truth (Codex centralization note); seeded from roster_auditor producers.
SAFE_TOKENS: frozenset[str] = frozenset({
    # trust / model
    "trust_status_unavailable", "trust_status_stale", "negative_r2_lower_bound",
    "low_sample_holdout",
    # caveats (verified producers, roster_auditor.py)
    "no_market_overlay", "no_market_derived_inputs", "no_internal_value_signal",
    "no_usage_signal", "age_curve_only", "engine_b_experimental_v1_fallback",
    # signal (verified)
    "past_cliff", "at_cliff", "approaching_cliff", "no_age_signal",
    # signal_drivers (verified)
    "age_past_position_cliff", "age_at_position_cliff",
    "age_within_two_years_of_position_cliff", "age_not_near_position_cliff",
    # age_value_context (verified)
    "past_cliff_depreciation_risk", "no_engine_b_projection",
    "approaching_cliff_high_projection", "approaching_cliff_low_projection",
    "prime_window_high_projection", "stable_age_low_projection",
    # liquidity_risk (verified)
    "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH", "MEDIUM_LIMITED_ESCAPE_HATCH", "LOW",
    # QB context (verified): annotations / caveats / source label
    "low_td_int_ratio_bust_context", "all_purpose_yards_mobility_context",
    "missing_qb_college_context", "p2s_context_unavailable",
    "cfbd_qb_context_annotations",
    # drop reasons
    "player_row_dropped_corrupt", "qb_context_card_dropped_corrupt",
})  # NOTE: keep in sync with roster_auditor producers; T7 completeness test enforces.

def validate_tokens(raw: list[str] | None) -> tuple[list[str], list[str]]:
    """Keep only SAFE_TOKENS; drop banned/unknown with a caveat (AC-5 token-only, list)."""
    items = list(raw or [])
    clean = [t for t in items if t in SAFE_TOKENS]
    caveats = ["evidence_suppressed_banned_term"] if len(clean) != len(items) else []
    return clean, caveats

def validate_token(value: str | None) -> tuple[str | None, list[str]]:
    """Scalar token-only (R3-1): pass None or a SAFE_TOKEN; else -> None + caveat."""
    if value is None or value in SAFE_TOKENS:
        return value, []
    return None, ["evidence_suppressed_banned_term"]


class RosterAuditSignalsView(BaseModel):  # F3: curated, no nested decision_supported leak
    cliff_age: int | None = None
    years_to_cliff: int | None = None
    age_cliff_risk: float | None = None
    biological_debt_score: float | None = None  # R2-3: retained (populated + decision-relevant)
    liquidity_risk: str | None = None
    signal: str | None = None
    signal_drivers: list[str] = Field(default_factory=list)
    age_value_context: str | None = None
    caveats: list[str] = Field(default_factory=list)
    decision_supported: Literal[False] = False


class QBContextCard(BaseModel):  # F2: explicitly typed, extra forbidden
    model_config = {"extra": "forbid"}
    player_id: str
    full_name: str
    identity_coverage: Literal["FULL", "PARTIAL", "NONE"]
    context_role: Literal["context_signal"] = "context_signal"
    epa_per_dropback: float | None = None
    cpoe: float | None = None
    dakota: float | None = None
    dropback_count: float | None = None
    pass_attempts: float | None = None
    qb_context_annotations: list[str] = Field(default_factory=list)
    qb_context_caveats: list[str] = Field(default_factory=list)
    source_qb_context_annotations: str
    decision_supported: Literal[False] = False


class RosterAuditPlayer(BaseModel):
    player_id: str
    full_name: str
    position: str
    nfl_team: str | None = None
    age: float | None = None
    sleeper_id: str | None = None
    is_prospect: bool = False
    draft_class: int | None = None
    nfl_draft_pick: int | None = None
    nfl_draft_round: int | None = None
    engine_used: str | None = None
    model_version: str | None = None
    model_grade: str
    dvs_engine: Literal["A", "B", "blend"] | None = None
    model_status_applies: bool = False
    dynasty_value_score: float | None = None
    projection_1y: float | None = None
    projection_2y: float | None = None
    projection_3y: float | None = None
    xvar: float | None = None
    dvs_pct: float | None = None
    signal_completeness: float = 0.0
    inputs_present: list[str] = Field(default_factory=list)
    inputs_missing: list[str] = Field(default_factory=list)
    counter_argument: CounterArgumentField
    top_drivers: EvidenceListField
    risk_flags: EvidenceListField
    caveats: list[str] = Field(default_factory=list)
    roster_audit: RosterAuditSignalsView | None = None
    decision_supported: Literal[False] = False


ROSTER_AUDIT_PLAYER_FIELDS: frozenset[str] = frozenset(RosterAuditPlayer.model_fields)


class RosterAuditResponse(BaseModel):
    status: Literal["active", "degraded"]
    engine: str
    reason: str
    model_status_by_position: dict[str, Literal["VALIDATED", "PROVISIONAL", "EXPERIMENTAL"]]
    caveats: list[str] = Field(default_factory=list)
    players: list[RosterAuditPlayer] = Field(default_factory=list)
    qb_context_cards: list[QBContextCard] = Field(default_factory=list)
    dropped_player_count: int = 0
    decision_supported: Literal[False] = False
```

- [ ] **Step 4: Run to verify pass** — `... -k "locked or qb_card or validate_tokens" -v` → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(roster-audit): typed models, curated signals, token validator (Inc1 T2)"`

---

## Task 3: Allowlist mapper — market-safe, token-enforced, applicability

**Files:** Modify `roster_audit_models.py`; Test `tests/contract/test_roster_audit_contract.py`

- [ ] **Step 1: Write failing tests (AC-1 / AC-5 / AC-6 / F3)**

```python
from app.api.routes.roster_audit_models import map_player

def _raw(**o):
    base = {"player_id": "p", "full_name": "WR", "position": "WR",
        "engine_used": "engine_b", "model_grade": "ACTIVE_B",
        "counter_argument": "solid floor", "top_drivers": ["target_share"],
        "risk_flags": ["snap_share_below_40pct"], "caveats": ["no_market_overlay"],
        "roster_audit": {"signal": "at_cliff", "signal_drivers": ["age_at_position_cliff"],
                         "decision_supported": True},  # F3 nested-true probe
        "market_overlay": {"market_value": 123}, "market_value": 99, "future_x": "leak"}
    base.update(o); return base

def test_excludes_market_and_future():  # AC-1
    p = map_player(_raw()).model_dump()
    for f in ("market_overlay", "market_value", "future_x"):
        assert f not in p
    assert "leak" not in str(p) and "123" not in str(p)

def test_nested_decision_supported_coerced_false():  # F3
    p = map_player(_raw())
    assert p.roster_audit.decision_supported is False

def test_token_only_caveats_enforced():  # AC-5
    p = map_player(_raw(caveats=["no_market_overlay", "elite", "mystery_token"]))
    assert "elite" not in p.caveats and "mystery_token" not in p.caveats

def test_scalar_token_fields_validated():  # R3-1: AC-5 scalar (signal/age_value_context/liquidity_risk)
    p = map_player(_raw(roster_audit={"signal": "elite", "age_value_context": "must sell",
                                      "liquidity_risk": "unknown"}))
    assert p.roster_audit.signal is None
    assert p.roster_audit.age_value_context is None
    assert p.roster_audit.liquidity_risk is None
    assert "evidence_suppressed_banned_term" in p.roster_audit.caveats

def test_engine_a_not_applicable():  # AC-6 / F6
    for eng in ("engine_a", None):
        assert map_player(_raw(engine_used=eng, model_grade="PROSPECT_C")).model_status_applies is False
    assert map_player(_raw(engine_used="engine_b")).model_status_applies is True
```

- [ ] **Step 2: Run to verify fail** — `... -k "excludes_market or nested_decision or token_only or applicable" -v` → FAIL.

- [ ] **Step 3: Implement**

```python
from app.api.routes.players import _counter_argument_field, _evidence_list_field

_SCALARS = ("player_id","full_name","position","nfl_team","age","sleeper_id","is_prospect",
    "draft_class","nfl_draft_pick","nfl_draft_round","engine_used","model_version",
    "model_grade","dvs_engine","dynasty_value_score","projection_1y","projection_2y",
    "projection_3y","xvar","dvs_pct","signal_completeness","inputs_present","inputs_missing")

def _map_signals(raw: dict | None) -> RosterAuditSignalsView | None:
    if not raw:
        return None
    drivers, dc1 = validate_tokens(raw.get("signal_drivers"))
    cav, dc2 = validate_tokens(raw.get("caveats"))
    signal, sc1 = validate_token(raw.get("signal"))           # R3-1: scalar token-only
    avc, sc2 = validate_token(raw.get("age_value_context"))   # R3-1
    liq, sc3 = validate_token(raw.get("liquidity_risk"))      # R3-1
    return RosterAuditSignalsView(
        cliff_age=raw.get("cliff_age"), years_to_cliff=raw.get("years_to_cliff"),
        age_cliff_risk=raw.get("age_cliff_risk"),
        biological_debt_score=raw.get("biological_debt_score"),  # R2-3 retained
        liquidity_risk=liq, signal=signal, signal_drivers=drivers,
        age_value_context=avc, caveats=cav + dc1 + dc2 + sc1 + sc2 + sc3,
    )  # decision_supported is Literal[False] -> nested true cannot survive

def map_player(raw: dict) -> RosterAuditPlayer:
    """Explicit ALLOWLIST mapping (no raw pvo.dict()); market/value/future fields excluded
    by construction; David-facing text validated/suppressed."""
    data = {k: raw.get(k) for k in _SCALARS}
    clean_caveats, dc = validate_tokens(raw.get("caveats"))
    data["caveats"] = clean_caveats + dc
    data["counter_argument"] = _counter_argument_field(raw.get("counter_argument"))
    data["top_drivers"] = _evidence_list_field(raw.get("top_drivers"))
    data["risk_flags"] = _evidence_list_field(raw.get("risk_flags"))
    data["roster_audit"] = _map_signals(raw.get("roster_audit"))
    # R2-6: scoped to run_audit_pvo (which emits engine_a/engine_b). Repo-wide, engine_used
    # can carry engine_a_*_ridge via pvo_assembler; this mapper consumes run_audit_pvo output.
    data["model_status_applies"] = (raw.get("engine_used") == "engine_b")
    return RosterAuditPlayer(**{k: v for k, v in data.items() if v is not None})
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(roster-audit): allowlist mapper + token enforcement + curated nested signals (Inc1 T3)"`

---

## Task 4: Envelope assembler (QB token validation, isolated-drop/systemic-503)

**Files:** Modify `roster_audit_models.py`; Test `tests/contract/test_roster_audit_contract.py`

- [ ] **Step 1: Write failing tests (AC-4)**

```python
from app.api.routes.roster_audit_models import assemble_response, RosterDependencyError
import pytest

def _audit(players, qb=None):
    return {"status": "active", "engine": "pvo_assembler_v1", "reason": "ok",
        "caveats": ["no_market_overlay"], "players": players, "qb_context_cards": qb or []}

def test_isolated_corrupt_dropped():  # AC-4
    r = assemble_response(_audit([_raw(player_id="g"), {"oops": 1}]))
    assert r.dropped_player_count == 1 and "player_row_dropped_corrupt" in r.caveats
    assert len(r.players) == 1 and r.status == "degraded"

def test_all_invalid_systemic_503():
    with pytest.raises(RosterDependencyError):
        assemble_response(_audit([{"x": 1}, {"y": 2}]))

def test_qb_card_tokens_validated():  # AC-5 (QB path)
    qb = [{"player_id": "q", "full_name": "QB", "identity_coverage": "FULL",
           "source_qb_context_annotations": "cfbd_qb_context_annotations",
           "qb_context_annotations": ["elite", "low_td_int_ratio_bust_context"]}]
    r = assemble_response(_audit([_raw()], qb=qb))
    assert "elite" not in r.qb_context_cards[0].qb_context_annotations
    assert "low_td_int_ratio_bust_context" in r.qb_context_cards[0].qb_context_annotations

def test_qb_card_unsafe_source_dropped_degraded():  # R2-2 + R2-5
    qb = [{"player_id": "q", "full_name": "QB", "identity_coverage": "FULL",
           "source_qb_context_annotations": "totally_unknown_source"}]
    r = assemble_response(_audit([_raw()], qb=qb))
    assert r.qb_context_cards == [] and r.dropped_player_count == 1
    assert "qb_context_card_dropped_corrupt" in r.caveats and r.status == "degraded"
```

- [ ] **Step 2: Run to verify fail** — `... -k "isolated_corrupt or all_invalid or qb_card_tokens" -v` → FAIL.

- [ ] **Step 3: Implement**

```python
class RosterDependencyError(RuntimeError):
    """Systemic failure -> caller returns 503."""

def _map_qb(raw: dict) -> QBContextCard:
    ann, dc1 = validate_tokens(raw.get("qb_context_annotations"))
    cav, dc2 = validate_tokens(raw.get("qb_context_caveats"))
    src = raw.get("source_qb_context_annotations")
    if src not in SAFE_TOKENS:  # R2-2: source label is token-only -> unsafe drops the card
        raise ValueError(f"unsafe source token {src!r}")
    allow = {"player_id","full_name","identity_coverage",
             "epa_per_dropback","cpoe","dakota","dropback_count","pass_attempts"}
    base = {k: raw.get(k) for k in allow if raw.get(k) is not None}
    return QBContextCard(**base, source_qb_context_annotations=src,
        qb_context_annotations=ann, qb_context_caveats=cav + dc1 + dc2)

def assemble_response(audit: dict) -> RosterAuditResponse:
    raw_players = audit.get("players", [])
    mapped, dropped = [], 0
    for raw in raw_players:
        try:
            mapped.append(map_player(raw))
        except Exception:
            dropped += 1
    if raw_players and not mapped:
        raise RosterDependencyError("all roster rows failed to map")
    qb_cards, qb_dropped = [], 0
    for raw in audit.get("qb_context_cards", []):
        try:
            qb_cards.append(_map_qb(raw))
        except Exception:
            qb_dropped += 1
    status_map, trust_caveats = load_model_status_by_position([p.position for p in mapped])
    caveats = list(audit.get("caveats", [])) + trust_caveats
    status = "active"
    if dropped:
        caveats.append("player_row_dropped_corrupt"); status = "degraded"
    if qb_dropped:  # R2-5: QB-card drop is degraded + named, never silent
        caveats.append("qb_context_card_dropped_corrupt"); status = "degraded"
    if trust_caveats:
        status = "degraded"
    return RosterAuditResponse(status=status, engine=audit.get("engine", "pvo_assembler_v1"),
        reason=audit.get("reason", ""), model_status_by_position=status_map, caveats=caveats,
        players=mapped, qb_context_cards=qb_cards, dropped_player_count=dropped + qb_dropped)
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(roster-audit): envelope assembler + QB token validation + drop/503 (Inc1 T4)"`

---

## Task 5: Wire route + recursive leakage guard (AC-1 e2e, AC-2 recursive)

**Files:** Modify `app/api/routes/roster.py`; Test `tests/contract/test_roster_audit_contract.py`

- [ ] **Step 1: Write failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

def _no_true(o):  # recursive AC-2
    if isinstance(o, dict):
        return o.get("decision_supported") is not True and all(_no_true(v) for v in o.values())
    if isinstance(o, list):
        return all(_no_true(x) for x in o)
    return True

def test_route_typed_recursive_clean(monkeypatch):
    from app.api.routes import roster as route
    async def fake():  # nested decision_supported=true under roster_audit (F8)
        return _audit([_raw(roster_audit={"signal": "at_cliff", "decision_supported": True})])
    monkeypatch.setattr(route, "run_audit_pvo", fake)
    r = TestClient(app).get("/api/roster/audit")
    assert r.status_code == 200
    body = r.json()
    assert "market_overlay" not in r.text and "future_x" not in r.text
    assert _no_true(body)
```

- [ ] **Step 2: Run to verify fail** — `... -k route_typed_recursive -v` → FAIL (raw route).

- [ ] **Step 3: Implement**

```python
# app/api/routes/roster.py
from fastapi import APIRouter, HTTPException
from app.services.roster_auditor import RosterConfigError, run_audit_pvo
from app.api.routes.roster_audit_models import (
    RosterAuditResponse, RosterDependencyError, assemble_response,
)

router = APIRouter(prefix="/roster", tags=["roster"])

@router.get("/audit", response_model=RosterAuditResponse)
async def audit_roster() -> RosterAuditResponse:
    try:
        audit = await run_audit_pvo()
    except RosterConfigError as e:
        raise HTTPException(status_code=422, detail={"error": "roster_config_error", "message": str(e)})
    try:
        return assemble_response(audit)
    except RosterDependencyError as e:
        raise HTTPException(status_code=503, detail={"error": "roster_dependency_unavailable", "message": str(e)})
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(roster-audit): wire response_model + 503; recursive leakage guard (Inc1 T5)"`

---

## Task 6: OpenAPI snapshot + typed client + drift guard (AC-3, RED-first)

**Files:** Modify `frontend/openapi.json`, `frontend/src/lib/api/*` (generated); `tests/contract/test_openapi_drift_contract.py`

- [ ] **Step 1: Write the RED (the existing drift guard now fails) + the typed assertions**

After Task 5, the live app emits a typed schema but `frontend/openapi.json` is stale → the existing `test_openapi_snapshot_matches_live_app_schema()` **fails** (that is the RED). Add:

```python
def test_roster_audit_route_typed_in_live_schema() -> None:
    from app.main import app
    s = app.openapi()["paths"]["/api/roster/audit"]["get"]["responses"]["200"]
    assert s["content"]["application/json"]["schema"]["$ref"].endswith("/RosterAuditResponse")
```

- [ ] **Step 2: Run to verify RED** — `.venv/bin/python3.14 -m pytest tests/contract/test_openapi_drift_contract.py -v` → the snapshot-match test FAILS (live ≠ snapshot); the new typed assertion PASSES.

- [ ] **Step 3: Regenerate** — `npm --prefix frontend run openapi-gen` (rewrites `frontend/openapi.json` + the TS/Zod client; `AuditRosterApiRosterAuditGet` becomes a typed object, no longer `Record<string, unknown>`).

- [ ] **Step 4: Run to verify GREEN** — same pytest command → PASS; add/confirm a generated-client assertion that the roster-audit response type is not `Record<string, unknown>` (grep the generated `types.gen.ts`).

- [ ] **Step 5: Commit** — `git add frontend/openapi.json frontend/src/lib/api tests/contract/test_openapi_drift_contract.py && git commit -m "feat(roster-audit): typed OpenAPI snapshot + client regen + drift guard (Inc1 T6)"`

---

## Task 7: Full acceptance + token-completeness sweep (AC-7)

**Files:** none (verification) + one completeness test

- [ ] **Step 1: Token-completeness test** — assert every token a representative audit fixture emits in token-only fields is in `SAFE_TOKENS` (fails if a producer token is unlisted — Codex F1 guard):

```python
def test_safe_tokens_cover_producers():  # verified producers from roster_auditor.py
    from app.api.routes.roster_audit_models import SAFE_TOKENS
    producers = {
        "past_cliff","at_cliff","approaching_cliff","no_age_signal",
        "age_past_position_cliff","age_at_position_cliff",
        "age_within_two_years_of_position_cliff","age_not_near_position_cliff",
        "past_cliff_depreciation_risk","no_engine_b_projection",
        "approaching_cliff_high_projection","approaching_cliff_low_projection",
        "prime_window_high_projection","stable_age_low_projection",
        "no_market_overlay","no_market_derived_inputs","no_internal_value_signal",
        "no_usage_signal","age_curve_only","engine_b_experimental_v1_fallback",
        "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH","MEDIUM_LIMITED_ESCAPE_HATCH","LOW",
        "low_td_int_ratio_bust_context","all_purpose_yards_mobility_context",
        "missing_qb_college_context","p2s_context_unavailable","cfbd_qb_context_annotations"}
    assert producers <= SAFE_TOKENS
```

- [ ] **Step 2: Full roster-audit contract suite** — `.venv/bin/python3.14 -m pytest tests/contract/test_roster_audit_contract.py -v` → all PASS.
- [ ] **Step 3: Full Python suite (AC-7)** — `.venv/bin/python3.14 -m pytest -q` → baseline + new, 0 failed.
- [ ] **Step 4: Lint** — `.venv/bin/ruff check src app` → PASS.
- [ ] **Step 5: FE gate** — `npm --prefix frontend run typecheck && npm --prefix frontend run lint` → PASS.
- [ ] **Step 6: Verifier tollgate (binding, code change)** — `.venv/bin/python3.14 scripts/verify_sprint_closeout.py --base origin/main` → ENFORCE PASS.
- [ ] **Step 7: Confirm `"no_market_overlay"` caveat now accurate; modeled players still surface scores.**

---

## Self-Review (spec coverage)

AC-1 → T3+T5 ✓ · AC-2 (recursive) → T2+T5 ✓ · AC-3 → T6 ✓ · AC-4 → T4+T5 ✓ · AC-5 (all David-facing text, free + token-only) → T2/T3/T4 + T7 completeness ✓ · AC-6 → T3 ✓ · AC-7 → T7 ✓ · live fail-closed trust → T1 ✓ · nested decision_supported leak (F3) → T2/T3/T5 ✓ · QB extra=allow removed (F2) → T2 ✓. Out of scope (UI, per-player model_status, roster-risk summary) → no task, by design ✓.
