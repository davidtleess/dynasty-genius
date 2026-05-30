# Harness Trust Completion Implementation Plan

> **For agentic workers:** This plan executes via the **cockpit TDD loop** (Codex authors RED per the test specs below → Claude greens → independent technical CLEAR + governance CLEAR per task, per `docs/governance/02-agent-operating-loop.md` Falsification Discipline). Steps use checkbox (`- [ ]`) syntax. The test code blocks are the **RED contract** Codex authors; the impl code blocks are the **GREEN target** Claude implements.

**Goal:** Convert the faithful-but-unproven model-vs-market anchor into a *validated* one — add R² disclosure, an immutable forward-snapshot clock, a point-in-time historical backfill that runs G3 honestly, and a QB-reliability stamp — extending the EXISTING Phase 10/11 harness without touching Engine A/B features or S4.

**Architecture:** Four workstreams against named files. W3 adds R² (OOS, disclose-only). W2a makes the daily FantasyCalc snapshot collection immutable + scheduled. W1 backfills point-in-time market data, fixes two existing-code G3 defects (under-coverage false-fail; hardcoded @24 verdict), adds a paired NDCG-diff bootstrap, and runs G3. W4 stamps QB reliability on the trust surface. Market data stays strictly overlay-only.

**Tech Stack:** Python 3.14, Pydantic v2, scipy/numpy, SQLite (`MarketSnapshotStore`), FastAPI (trust surface). Tests: `.venv/bin/python3.14 -m pytest`; lint `.venv/bin/ruff`.

**Spec:** `docs/superpowers/specs/2026-05-30-harness-trust-completion-design.md` (v4, dual-CLEARed; Gate B locked). **Binding rulings:** R² = disclose-only; G3 PASS = model ≥ market at position-primary k (**QB/TE @12, RB/WR @24**) in **≥3/4 EVALUABLE folds** with the NDCG-diff bootstrap CI disclosed (not required to exclude 0); Gate-4/W2b deferred; W1 archive approved (overlay-only, point-in-time).

**Branch:** `feature/harness-trust-completion` (off `origin/main` `95345ea`; spec committed `1e57da0`).

**Plan version:** v4.
- v2 — Codex round-1 (14:12) P1–P6: P1 bind `n_test=X_test.shape[0]` (W3.2); P2 (superseded by v3/Q1); P3 `FoldResult` artifact destinations `primary_k`/`market_pool_n`/`ndcg_diff_primary_k`/`ndcg_diff_bca_ci95` + run() wiring (W1.2); P4 explicit patch of `test_backtest_gates.py::test_g3_market_superiority_logic` (W1.3); P5 plist-validation RED (W2a.3); P6 pinned archive row format + ±7-day PIT rule (W1.4). Gemini round-1 governance CLEAR.
- v3 — Codex round-2 (14:18) Q1–Q3: **Q1** restore **BCa** for the NDCG-diff CI (`scipy_stats.bootstrap(method="BCa", paired=True)`, key `ndcg_diff_bca_ci95`, `method="bca_bootstrap"`) — conforms to the Gate-B-locked spec §5; the v2 percentile rename was a spec downgrade, reverted (W1.1). **Q2** harness-level caveat-propagation RED via `WalkForwardDriver.run()` (W3.2 Step 4b). **Q3** concrete REDs replacing placeholder clauses — `_compute_market_ndcg` pool<k test (W1.2) and inline `_archive()` fixtures with the ±7-day PIT assertions (W1.4). Gemini round-2 governance CONCUR & CLEAR (14:17).
- v4 — Codex round-3 (14:23) R1–R3: **R1** W2a.3 RED that `docs/ARTIFACTS.md` documents the cadence + Gate-4 readiness clock; **R2** W1.4 RED for the two fail-closed cases the GREEN names (missing required field → skip; `updated_at` newer than capture → reject) + GREEN enumerates the 3-part accept rule; **R3** W1.1 RED asserts `method == "bca_bootstrap"` so it can't drift. Gemini round-3 governance CLEAR (14:23).

---

## File Structure

| File | Created/Modified | Responsibility |
|---|---|---|
| `src/dynasty_genius/eval/backtest_metrics.py` | Modify | + `compute_r2` (W3.1), + `compute_ndcg_diff_bootstrap` (W1.1) |
| `src/dynasty_genius/eval/backtest_artifact.py` | Modify | `FoldResult` + `r2_oos`, `metric_caveats` (W3.2) |
| `src/dynasty_genius/eval/backtest_harness.py` | Modify | wire R² in `run()` fold loop (W3.2); position-primary-k + G3 under-coverage fix in `evaluate_promotion_gates` (W1.2/W1.3) |
| `src/dynasty_genius/eval/model_card.py` | Modify | `ModelCardMetrics` + `r2_oos_mean`, `r2_oos_per_fold` (W3.3) |
| `scripts/generate_model_cards.py` | Modify | populate R² ModelCard fields (W3.3) |
| `src/dynasty_genius/eval/market_snapshot_store.py` | Modify | + `MarketSnapshotImmutabilityError`, + `append_snapshots` verify-or-raise (W2a.1) |
| `scripts/snapshot_fantasycalc.py` | Modify | switch daily write to `append_snapshots` (W2a.2) |
| `ops/launchd/com.davidleess.dynasty-fc-snapshot.plist` | Create | local daily scheduler (W2a.3) |
| `scripts/backfill_market_archive.py` | Create (or extend `ingest_market_archive.py`) | point-in-time historical backfill → `append_snapshots` (W1.4) |
| `app/api/routes/trust_surface.py` | Modify | one QB-reliability caveat field (W4.1) |
| `tests/contract/test_harness_trust_*.py` | Create | RED contracts per task (Codex-authored) |

---

# WORKSTREAM W3 — R² disclosure (OOS only)

### Task W3.1: `compute_r2` in backtest_metrics

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_metrics.py`
- Test: `tests/contract/test_harness_trust_w3_r2.py`

- [ ] **Step 1 (RED — Codex authors): failing test for the R² contract**

```python
import math
import pytest
from src.dynasty_genius.eval.backtest_metrics import compute_r2

def test_compute_r2_exact_value_on_known_fixture():
    # y_true variance = SS_tot; perfect fit → 1.0
    assert compute_r2([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.0)
    # predicting the mean → R² == 0.0
    assert compute_r2([1.0, 2.0, 3.0, 4.0], [2.5, 2.5, 2.5, 2.5]) == pytest.approx(0.0)

def test_compute_r2_negative_is_returned_not_clamped():
    # worse than predicting the mean → negative, returned as-is
    r2 = compute_r2([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0])
    assert r2 < 0.0

def test_compute_r2_zero_variance_truth_fails_closed_to_none():
    assert compute_r2([5.0, 5.0, 5.0], [5.0, 5.1, 4.9]) is None

def test_compute_r2_nan_or_inf_in_pred_fails_closed_to_none():
    assert compute_r2([1.0, 2.0, 3.0], [1.0, float("nan"), 3.0]) is None
    assert compute_r2([1.0, 2.0, 3.0], [1.0, float("inf"), 3.0]) is None

def test_compute_r2_length_mismatch_or_empty_raises():
    with pytest.raises(ValueError):
        compute_r2([1.0, 2.0], [1.0])
    with pytest.raises(ValueError):
        compute_r2([], [])
```

- [ ] **Step 2: run RED, verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_harness_trust_w3_r2.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_r2'`.

- [ ] **Step 3 (GREEN — Claude): minimal implementation**

```python
def compute_r2(y_true, y_pred) -> "Optional[float]":
    """OOS coefficient of determination 1 - SS_res/SS_tot.

    Fail-closed → None: zero-variance truth (SS_tot == 0); any non-finite value
    (NaN/inf) in either array (data corruption). Raises ValueError on API-misuse
    (length mismatch / empty). Negative R² is valid and returned as-is.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if yt.shape != yp.shape:
        raise ValueError("compute_r2: y_true and y_pred must have equal length")
    if yt.size == 0:
        raise ValueError("compute_r2: empty input")
    if not (np.isfinite(yt).all() and np.isfinite(yp).all()):
        return None
    ss_tot = float(np.sum((yt - yt.mean()) ** 2))
    if ss_tot == 0.0:
        return None
    ss_res = float(np.sum((yt - yp) ** 2))
    return 1.0 - ss_res / ss_tot
```
(`np` is already imported in this module; `Optional` is in `typing` — add to the existing import if absent.)

- [ ] **Step 4: run GREEN, verify pass + full suite green**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_harness_trust_w3_r2.py -v && .venv/bin/ruff check src/dynasty_genius/eval/backtest_metrics.py`
Expected: 5 passed; ruff clean.

- [ ] **Step 5: cockpit CLEAR + commit**

```bash
git add src/dynasty_genius/eval/backtest_metrics.py tests/contract/test_harness_trust_w3_r2.py
git commit -m "feat(harness-trust): compute_r2 (OOS, fail-closed) — W3.1"
```

---

### Task W3.2: wire `r2_oos` + `metric_caveats` into `FoldResult` and `run()`

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_artifact.py` (`FoldResult`)
- Modify: `src/dynasty_genius/eval/backtest_harness.py` (`run()` fold loop, ~`:513`)
- Test: `tests/contract/test_harness_trust_w3_foldresult.py`

- [ ] **Step 1 (RED): failing test**

```python
from src.dynasty_genius.eval.backtest_artifact import FoldResult

def test_foldresult_has_r2_oos_and_metric_caveats_with_safe_defaults():
    f = FoldResult(
        fold_index=1, train_years=[2018, 2019], test_year=2020, outcome_seasons=[2021, 2022],
        n_train=10, n_test=5, kendall_tau=0.3, kendall_tau_bca_ci95=(0.1, 0.5),
        spearman_rho=0.4, spearman_rho_bca_ci95=(0.2, 0.6), rank_ic=0.4, rmse=1.0, mae=0.8,
    )
    assert f.r2_oos is None            # optional, defaults None
    assert f.metric_caveats == []      # list, defaults empty

def test_foldresult_accepts_negative_r2_and_caveat_tokens():
    f = FoldResult(
        fold_index=1, train_years=[2018], test_year=2020, outcome_seasons=[2021],
        n_train=10, n_test=5, kendall_tau=0.3, kendall_tau_bca_ci95=(0.1, 0.5),
        spearman_rho=0.4, spearman_rho_bca_ci95=(0.2, 0.6), rank_ic=0.4, rmse=1.0, mae=0.8,
        r2_oos=-0.208, metric_caveats=["r2_oos_small_sample"],
    )
    assert f.r2_oos == -0.208
    assert "r2_oos_small_sample" in f.metric_caveats
```

- [ ] **Step 2: run RED, verify fail** (`FoldResult` rejects unknown `r2_oos`).

- [ ] **Step 3 (GREEN): add fields to `FoldResult`** (after the `mae` / error-metrics block, `backtest_artifact.py` ~`:41`):

```python
    # R² — OOS coefficient of determination (disclose-only; None when fail-closed)
    r2_oos: Optional[float] = None

    # Fixed-token fail-closed caveats (banned-language-safe); e.g. "r2_oos_unavailable"
    metric_caveats: List[str] = Field(default_factory=list)
```
(`Field` is imported from pydantic in this module; `List`/`Optional` already imported.)

- [ ] **Step 4 (GREEN): compute R² in `run()` fold loop** — in `backtest_harness.py`, alongside the existing `rmse`/`mae` computation, before the `FoldResult(...)` append at `:513`:

```python
            n_test = X_test.shape[0]          # P1: bind the var (fold loop uses X_test, not n_test)
            r2_oos = compute_r2(y_test, y_pred)
            fold_caveats: list[str] = []
            if r2_oos is None:
                fold_caveats.append("r2_oos_unavailable")
            elif n_test < 50:
                fold_caveats.append("r2_oos_small_sample")
```
(`X_test`, `y_test`, `y_pred` already exist in the fold loop — `backtest_harness.py:406/416/519`.)
Add `r2_oos=r2_oos, metric_caveats=fold_caveats,` to the `FoldResult(...)` constructor at `:513`. Add `compute_r2` to the existing `from ...backtest_metrics import (...)` block (`:29`).

- [ ] **Step 4b (RED — Q2): harness-level caveat-propagation test** — schema tests alone don't prove `run()` populates the fields. Codex authors a focused harness run against the existing fixture (`WalkForwardDriver` already has CSV-backed tests; reuse that setup):

```python
from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver

def test_run_populates_r2_oos_and_metric_caveats_on_each_fold(harness_fixture):
    # harness_fixture wires the existing engine_b features CSV the other harness tests use
    driver = WalkForwardDriver(position="QB")
    result = driver.run(**harness_fixture)
    assert len(result.folds) == 4
    for f in result.folds:
        assert isinstance(f.metric_caveats, list)       # always a list
        assert f.r2_oos is None or isinstance(f.r2_oos, float)
    # QB folds are small (n_test < 50) → the small-sample (or unavailable) caveat must propagate
    assert any(("r2_oos_small_sample" in f.metric_caveats) or
               ("r2_oos_unavailable" in f.metric_caveats) for f in result.folds)
```
Run it RED before Step 4's wiring exists (fails: folds carry no `metric_caveats` population); GREEN after.

- [ ] **Step 5: run focused + full suite**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_harness_trust_w3_foldresult.py tests/ -q -k "backtest or harness or trust" && .venv/bin/ruff check src/dynasty_genius/eval/`
Expected: new tests pass; no regression in existing harness/artifact tests.

- [ ] **Step 6: cockpit CLEAR + commit**

```bash
git add src/dynasty_genius/eval/backtest_artifact.py src/dynasty_genius/eval/backtest_harness.py tests/contract/test_harness_trust_w3_foldresult.py
git commit -m "feat(harness-trust): FoldResult.r2_oos + metric_caveats, wired in run() — W3.2"
```

---

### Task W3.3: R² in `ModelCardMetrics` (nullable types + null-mean handling)

**Files:**
- Modify: `src/dynasty_genius/eval/model_card.py` (`ModelCardMetrics`, `:28`)
- Modify: `scripts/generate_model_cards.py` (`ModelCardMetrics(...)` builder, `:285`)
- Test: `tests/contract/test_harness_trust_w3_modelcard.py`

- [ ] **Step 1 (RED): failing test** (E1 — fields must admit null)

```python
from src.dynasty_genius.eval.model_card import ModelCardMetrics

def _base(**kw):
    d = dict(rmse_mean=1.0, rmse_per_fold=[1.0], kendall_tau_mean=0.3, kendall_tau_per_fold=[0.3],
             spearman_rho_mean=0.4, spearman_rho_per_fold=[0.4], g1_pass=True, g2_pass=True,
             g3_pass="deferred", g4_pass="deferred", overall_grade="ACTIVE_B")
    d.update(kw); return d

def test_modelcard_metrics_r2_fields_accept_nulls():
    m = ModelCardMetrics(**_base(r2_oos_mean=None, r2_oos_per_fold=[0.1, None, -0.2, None]))
    assert m.r2_oos_mean is None
    assert m.r2_oos_per_fold == [0.1, None, -0.2, None]

def test_modelcard_metrics_r2_defaults_when_absent():
    m = ModelCardMetrics(**_base())
    assert m.r2_oos_mean is None and m.r2_oos_per_fold == []
```

- [ ] **Step 2: run RED, verify fail.**

- [ ] **Step 3 (GREEN): add fields to `ModelCardMetrics`** (after `ndcg_at_24_market_mean`, `:37`):

```python
    r2_oos_mean: Optional[float] = None
    r2_oos_per_fold: List[Optional[float]] = []
```

- [ ] **Step 4 (GREEN): populate in builder** — `scripts/generate_model_cards.py`, before `metrics = ModelCardMetrics(`:

```python
    r2_per_fold = [f.r2_oos for f in folds]
    _r2_present = [v for v in r2_per_fold if v is not None]
    r2_mean = (sum(_r2_present) / len(_r2_present)) if _r2_present else None
```
Add to the `ModelCardMetrics(...)` call: `r2_oos_mean=r2_mean, r2_oos_per_fold=r2_per_fold,`. (Null-handling: mean over non-null folds; `None` if all four null. Per-fold list preserves `null` positionally.)

- [ ] **Step 5: focused + suite green; Step 6: cockpit CLEAR + commit**

```bash
git add src/dynasty_genius/eval/model_card.py scripts/generate_model_cards.py tests/contract/test_harness_trust_w3_modelcard.py
git commit -m "feat(harness-trust): R² in ModelCardMetrics (nullable, null-mean) — W3.3"
```

---

# WORKSTREAM W2a — immutable forward snapshot clock

### Task W2a.1: `append_snapshots` verify-or-raise in `MarketSnapshotStore`

**Files:**
- Modify: `src/dynasty_genius/eval/market_snapshot_store.py`
- Test: `tests/contract/test_harness_trust_w2a_immutable.py`

- [ ] **Step 1 (RED): failing test**

```python
import pytest
from src.dynasty_genius.eval.market_snapshot_store import (
    MarketSnapshotStore, MarketSnapshotImmutabilityError,
)

def _row(value=100, sid="111", date="2025-09-01"):
    return dict(snapshot_date=date, league_settings_hash="h1", sleeper_id=sid, value=value,
                overall_rank=1, position_rank=1, position="QB", trend_30day=0,
                source="fc_native", inserted_at="2025-09-01T00:00:00Z")

def test_append_then_identical_reappend_is_noop(tmp_path):
    s = MarketSnapshotStore(db_path=tmp_path / "fc.db")
    assert s.append_snapshots([_row()]) == 1
    assert s.append_snapshots([_row()]) == 1          # idempotent, still 1 row
    assert s.get_coverage()["n_rows"] == 1

def test_append_changed_value_same_key_raises(tmp_path):
    s = MarketSnapshotStore(db_path=tmp_path / "fc.db")
    s.append_snapshots([_row(value=100)])
    with pytest.raises(MarketSnapshotImmutabilityError):
        s.append_snapshots([_row(value=999)])         # silent overwrite forbidden

def test_append_distinct_dates_accumulate(tmp_path):
    s = MarketSnapshotStore(db_path=tmp_path / "fc.db")
    s.append_snapshots([_row(date="2025-09-01")])
    s.append_snapshots([_row(date="2025-09-02")])
    assert s.get_coverage()["n_dates"] == 2
```

- [ ] **Step 2: run RED, verify fail** (no `MarketSnapshotImmutabilityError`, no `append_snapshots`).

- [ ] **Step 3 (GREEN): implement** — add at module level and as a method:

```python
class MarketSnapshotImmutabilityError(RuntimeError):
    """Raised when an append would change an already-recorded snapshot row."""


_IMMUTABLE_COLS = ("value", "overall_rank", "position_rank", "position", "trend_30day", "source")

    def append_snapshots(self, rows: list[dict]) -> int:
        """Append-only immutable write. Identical same-key re-write = idempotent no-op;
        a *changed* value for an existing (date, league, sleeper_id) raises
        MarketSnapshotImmutabilityError (no silent overwrite). Returns row count for the date."""
        if not rows:
            return 0
        with self._connect() as conn:
            for r in rows:
                existing = conn.execute(
                    "SELECT value, overall_rank, position_rank, position, trend_30day, source "
                    "FROM fc_snapshots WHERE snapshot_date=? AND league_settings_hash=? AND sleeper_id=?",
                    (r["snapshot_date"], r["league_settings_hash"], r["sleeper_id"]),
                ).fetchone()
                if existing is not None:
                    if any(existing[c] != r[c] for c in _IMMUTABLE_COLS):
                        raise MarketSnapshotImmutabilityError(
                            f"immutable snapshot conflict at {r['snapshot_date']}/{r['sleeper_id']}"
                        )
                    continue  # identical → no-op
                conn.execute(
                    "INSERT INTO fc_snapshots (snapshot_date, league_settings_hash, sleeper_id, value,"
                    " overall_rank, position_rank, position, trend_30day, source, inserted_at) VALUES"
                    " (:snapshot_date,:league_settings_hash,:sleeper_id,:value,:overall_rank,"
                    ":position_rank,:position,:trend_30day,:source,:inserted_at)",
                    r,
                )
            conn.commit()
        return self._row_count_for_date(rows[0]["snapshot_date"])
```
(`existing[c]` indexes by column name — `row_factory = sqlite3.Row` is already set. Leave `upsert_snapshots` in place for now; it is no longer the daily write path.)

- [ ] **Step 4: focused + suite green; Step 5: cockpit CLEAR + commit**

```bash
git add src/dynasty_genius/eval/market_snapshot_store.py tests/contract/test_harness_trust_w2a_immutable.py
git commit -m "feat(harness-trust): append_snapshots verify-or-raise immutability — W2a.1"
```

---

### Task W2a.2: route the daily script through `append_snapshots`

**Files:**
- Modify: `scripts/snapshot_fantasycalc.py`
- Test: `tests/contract/test_harness_trust_w2a_script.py`

- [ ] **Step 1 (RED): failing test** — the script must write via the immutable path and be idempotent.

```python
from pathlib import Path
import scripts.snapshot_fantasycalc as snap
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore

def test_snapshot_uses_append_not_replace(monkeypatch, tmp_path):
    # fake the FC fetch to a fixed payload
    monkeypatch.setattr(snap, "_fetch_fc_rows", lambda: [
        dict(snapshot_date="2025-09-01", league_settings_hash=snap.LEAGUE_SETTINGS_HASH,
             sleeper_id="111", value=100, overall_rank=1, position_rank=1, position="QB",
             trend_30day=0, source="fc_native", inserted_at="2025-09-01T00:00:00Z")])
    db = tmp_path / "fc.db"
    n1 = snap.snapshot_fantasycalc(db_path=db)
    n2 = snap.snapshot_fantasycalc(db_path=db)   # same-day re-run idempotent
    assert n1 == 1 and n2 == 1
    assert MarketSnapshotStore(db_path=db).get_coverage()["n_rows"] == 1
```

- [ ] **Step 2: run RED, verify fail.**

- [ ] **Step 3 (GREEN):** refactor `snapshot_fantasycalc.py` to (a) factor the FC fetch+normalize into `_fetch_fc_rows() -> list[dict]` returning rows shaped for the store (date, `LEAGUE_SETTINGS_HASH`, sleeper_id, value, ranks, position, trend, `source="fc_native"`, `inserted_at`), and (b) call `store.append_snapshots(rows)` instead of `upsert_snapshots`. Keep the existing provenance fields.

- [ ] **Step 4: focused + suite green; Step 5: cockpit CLEAR + commit**

```bash
git add scripts/snapshot_fantasycalc.py tests/contract/test_harness_trust_w2a_script.py
git commit -m "feat(harness-trust): daily FC snapshot writes immutably — W2a.2"
```

---

### Task W2a.3: schedule the daily clock (local-first)

**Files:**
- Create: `ops/launchd/com.davidleess.dynasty-fc-snapshot.plist`
- Create/Modify: `docs/ARTIFACTS.md` (document the cadence + readiness-date counter)
- Test: `tests/contract/test_harness_trust_w2a_scheduler.py`

- [ ] **Step 0 (RED — P5): failing test that validates the plist contract**

```python
import plistlib
from pathlib import Path

PLIST = Path("ops/launchd/com.davidleess.dynasty-fc-snapshot.plist")

def test_scheduler_plist_is_valid_and_runs_the_snapshot_script():
    assert PLIST.exists(), "W2a.3 scheduler plist must exist"
    data = plistlib.loads(PLIST.read_bytes())          # fails if malformed
    assert data["Label"] == "com.davidleess.dynasty-fc-snapshot"
    args = data["ProgramArguments"]
    assert args[0].endswith("python3.14")
    assert any(a.endswith("scripts/snapshot_fantasycalc.py") for a in args)
    assert "StartCalendarInterval" in data           # scheduled, not RunAtLoad-only

def test_artifacts_doc_records_cadence_and_gate4_readiness():
    # R1: the Gate-4 clock must be documented, not just scheduled
    text = Path("docs/ARTIFACTS.md").read_text(encoding="utf-8").lower()
    assert "fc_native" in text or "fantasycalc snapshot" in text  # cadence documented
    assert "gate-4" in text or "gate 4" in text                   # readiness clock documented
    assert "readiness" in text or "6 month" in text or "6-month" in text
```

- [ ] **Step 1:** Author the LaunchAgent plist (`Label`, `ProgramArguments` = `[<abs>/.venv/bin/python3.14, <abs>/scripts/snapshot_fantasycalc.py]`, `StartCalendarInterval` daily ~09:00, `StandardOut/ErrorPath` under `app/data/logs/`) so the RED passes. **No Databricks.** (Committed but **loaded manually by David** — `launchctl load`; the agent does not auto-load.)
- [ ] **Step 2:** Document in `docs/ARTIFACTS.md`: the daily cadence, the immutability contract, and that the **Gate-4 readiness date = first-collection-date + ~6 months** (W2b unblocks then; §8.3).
- [ ] **Step 3 (manual, David):** `launchctl load ~/Library/LaunchAgents/com.davidleess.dynasty-fc-snapshot.plist` to start the clock. Verify the first row lands: `.venv/bin/python3.14 -c "from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore as S; print(S().get_coverage())"`.
- [ ] **Step 4: commit**

```bash
git add ops/launchd/com.davidleess.dynasty-fc-snapshot.plist docs/ARTIFACTS.md
git commit -m "feat(harness-trust): local daily FC snapshot scheduler + Gate-4 clock doc — W2a.3"
```

---

# WORKSTREAM W1 — historical backfill → run G3 (keystone)

> **Most adversarial scrutiny.** Codex test-drives the statistical pieces (W1.1, W1.3) RED-first; point-in-time integrity (W1.4) and the leakage wall (W1.5) get explicit RED.

### Task W1.1: `compute_ndcg_diff_bootstrap` (paired player-level bootstrap)

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_metrics.py`
- Test: `tests/contract/test_harness_trust_w1_bootstrap.py`

- [ ] **Step 1 (RED — Codex authors): failing test for the contract**

```python
from src.dynasty_genius.eval.backtest_metrics import compute_ndcg_diff_bootstrap

def test_bootstrap_returns_point_diff_ci_and_pool_n_on_adequate_pool():
    # model ranks better-aligned to realized than market → positive diff likely
    model_ranks   = list(range(1, 31))
    market_ranks  = list(range(30, 0, -1))
    realized      = [30 - i for i in range(30)]   # relevance
    out = compute_ndcg_diff_bootstrap(model_ranks, market_ranks, realized, k=24,
                                      n_bootstrap=200, rng_seed=12345)
    assert out["pool_n"] == 30
    assert out["method"] == "bca_bootstrap"      # R3: method pinned so it can't drift
    assert isinstance(out["ndcg_diff"], float)
    lo, hi = out["ndcg_diff_bca_ci95"]
    assert lo <= out["ndcg_diff"] <= hi
    assert "caveat" not in out or out["caveat"] is None

def test_bootstrap_fails_closed_on_pool_below_threshold():
    out = compute_ndcg_diff_bootstrap([1, 2, 3], [3, 2, 1], [3, 2, 1], k=24,
                                      n_bootstrap=200, rng_seed=12345)
    assert out["ndcg_diff"] is None
    assert out["ndcg_diff_bca_ci95"] is None
    assert out["caveat"] == "insufficient_pool_for_bootstrap"

def test_bootstrap_is_deterministic_under_fixed_seed():
    args = (list(range(1, 31)), list(range(30, 0, -1)), [30 - i for i in range(30)])
    a = compute_ndcg_diff_bootstrap(*args, k=24, n_bootstrap=200, rng_seed=7)
    b = compute_ndcg_diff_bootstrap(*args, k=24, n_bootstrap=200, rng_seed=7)
    assert a == b
```

- [ ] **Step 2: run RED, verify fail.**

- [ ] **Step 3 (GREEN — Claude): reference implementation** (Codex finalizes the BCa specifics in review)

```python
def compute_ndcg_diff_bootstrap(
    model_ranks, market_ranks, realized_relevance, k,
    *, n_bootstrap: int = 1000, rng_seed: int = 12345, min_pool: int = 10,
) -> dict:
    """Paired player-level BCa bootstrap of NDCG@k difference (model - market).

    Resamples player indices with replacement (the SAME indices applied to model
    and market — `paired=True`) so the pairing is preserved. Returns
    {ndcg_diff, ndcg_diff_bca_ci95, pool_n, method, caveat}. Fail-closed: pool n <
    max(k, min_pool) → diff/CI None + caveat. Mirrors the existing `_bca_ci` pattern
    (scipy BCa); degenerate distribution → CI collapses to the point estimate.
    """
    n = len(realized_relevance)
    if n < max(k, min_pool):
        return {"ndcg_diff": None, "ndcg_diff_bca_ci95": None, "pool_n": n,
                "method": "bca_bootstrap", "caveat": "insufficient_pool_for_bootstrap"}
    mr = np.asarray(model_ranks, dtype=float)
    kr = np.asarray(market_ranks, dtype=float)
    rel = np.asarray(realized_relevance, dtype=float)

    def _diff(m, kk, r):
        return (compute_ndcg(m.tolist(), r.tolist(), k)
                - compute_ndcg(kk.tolist(), r.tolist(), k))

    point = float(_diff(mr, kr, rel))
    try:
        result = scipy_stats.bootstrap(
            (mr, kr, rel), _diff, n_resamples=n_bootstrap, random_state=rng_seed,
            method="BCa", paired=True, confidence_level=0.95,
        )
        lo = float(result.confidence_interval.low)
        hi = float(result.confidence_interval.high)
    except Exception:                       # degenerate (e.g. perfect agreement) → collapse
        lo = hi = point
    return {"ndcg_diff": point, "ndcg_diff_bca_ci95": (lo, hi),
            "pool_n": n, "method": "bca_bootstrap", "caveat": None}
```
**Q1 resolution (supersedes the v2 P2 change):** the CI is a real **BCa** bootstrap via `scipy_stats.bootstrap(..., method="BCa", paired=True)` — matching the dual-CLEARed/Gate-B-locked spec §5 ("BCa 95% CI, reuse the `_bca_ci` pattern"). The key `ndcg_diff_bca_ci95` and `method="bca_bootstrap"` are now honest *and* spec-conformant. (`scipy_stats` + `compute_ndcg` are already in this module.) No spec patch needed — the plan now conforms to the spec rather than downgrading it.

- [ ] **Step 4: focused + suite green; Step 5: cockpit CLEAR + commit**

```bash
git add src/dynasty_genius/eval/backtest_metrics.py tests/contract/test_harness_trust_w1_bootstrap.py
git commit -m "feat(harness-trust): paired NDCG-diff bootstrap — W1.1"
```

---

### Task W1.2: position-primary-k policy + artifact destinations for the bootstrap (P3)

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_harness.py` (`PRIMARY_NDCG_K`, `_compute_market_ndcg`, `run()` fold loop)
- Modify: `src/dynasty_genius/eval/backtest_artifact.py` (`FoldResult` — add the market-comparison destination fields)
- Test: `tests/contract/test_harness_trust_w1_primary_k.py`

- [ ] **Step 1 (RED): failing tests** — the k table AND the artifact destinations (P3: `pool_n` + NDCG-diff CI must land somewhere durable)

```python
from src.dynasty_genius.eval.backtest_harness import PRIMARY_NDCG_K
from src.dynasty_genius.eval.backtest_artifact import FoldResult

def test_primary_k_table_matches_locked_spec():
    assert PRIMARY_NDCG_K == {"QB": 12, "RB": 24, "WR": 24, "TE": 12}

def test_foldresult_carries_market_comparison_destinations():
    f = FoldResult(
        fold_index=1, train_years=[2018], test_year=2020, outcome_seasons=[2021],
        n_train=10, n_test=5, kendall_tau=0.3, kendall_tau_bca_ci95=(0.1, 0.5),
        spearman_rho=0.4, spearman_rho_bca_ci95=(0.2, 0.6), rank_ic=0.4, rmse=1.0, mae=0.8,
        primary_k=24, market_pool_n=60, ndcg_diff_primary_k=0.03, ndcg_diff_bca_ci95=(-0.01, 0.07),
    )
    assert f.primary_k == 24 and f.market_pool_n == 60
    assert f.ndcg_diff_primary_k == 0.03 and f.ndcg_diff_bca_ci95 == (-0.01, 0.07)

def test_foldresult_market_comparison_fields_default_none():
    f = FoldResult(
        fold_index=1, train_years=[2018], test_year=2020, outcome_seasons=[2021],
        n_train=10, n_test=5, kendall_tau=0.3, kendall_tau_bca_ci95=(0.1, 0.5),
        spearman_rho=0.4, spearman_rho_bca_ci95=(0.2, 0.6), rank_ic=0.4, rmse=1.0, mae=0.8,
    )
    assert f.primary_k is None and f.market_pool_n is None
    assert f.ndcg_diff_primary_k is None and f.ndcg_diff_bca_ci95 is None
```
Plus a concrete behavioral test on the helper (Codex pins the exact arg names against `_compute_market_ndcg`'s real signature at `backtest_harness.py:66`):

```python
from src.dynasty_genius.eval.backtest_harness import _compute_market_ndcg

def test_market_ndcg_returns_none_at_k_when_pool_below_k():
    # 3 matched players but @24 needs 24 → @24 must be None (feeds pool_below_k + under-coverage)
    rows = [{"sleeper_id": s, "value": v, "position_rank": r, "overall_rank": r}
            for s, v, r in [("a", 10, 1), ("b", 9, 2), ("c", 8, 3)]]
    out = _compute_market_ndcg(y_pred=[3.0, 2.0, 1.0], player_ids=["a", "b", "c"],
                               y_realized=[3.0, 2.0, 1.0], market_rows=rows,
                               id_map={"a": "a", "b": "b", "c": "c"})
    assert out["ndcg_at_24_model"] is None and out["ndcg_at_24_market"] is None
    assert out["ndcg_at_12_model"] is None  # pool 3 < 12 too
```
(The `pool_below_k` caveat onto `metric_caveats` and `ndcg_diff_primary_k=None` are asserted at the run()-level wiring via the W3.2/W1.2 harness path.)

- [ ] **Step 2: run RED, verify fail.**

- [ ] **Step 3a (GREEN): `FoldResult` destination fields** — add to `backtest_artifact.py` (after `metric_caveats`):

```python
    # Market-comparison destinations (W1) — None when market data unavailable
    primary_k: Optional[int] = None                       # position-primary k used for the verdict
    market_pool_n: Optional[int] = None                   # matched model∩market pool size
    ndcg_diff_primary_k: Optional[float] = None           # ndcg_model@k − ndcg_market@k
    ndcg_diff_bca_ci95: Optional[Tuple[float, float]] = None  # BCa bootstrap CI
```
(`Tuple`/`Optional` already imported.)

- [ ] **Step 3b (GREEN): policy + wiring** — add `PRIMARY_NDCG_K = {"QB": 12, "RB": 24, "WR": 24, "TE": 12}` to `backtest_harness.py`. Thread `position` into `_compute_market_ndcg`; when the matched pool n < primary k, append `pool_below_k` to `fold_caveats` and leave that k null. In the fold loop, when the pool supports the primary k, call `compute_ndcg_diff_bootstrap(model_ranks, market_ranks, y_realized, k=PRIMARY_NDCG_K[position])` and populate `primary_k`, `market_pool_n`, `ndcg_diff_primary_k` (its `ndcg_diff`), `ndcg_diff_bca_ci95` (its `ndcg_diff_bca_ci95`) on the `FoldResult`; if its `caveat` is set, append it to `fold_caveats`.

- [ ] **Step 4–5: focused + suite green; cockpit CLEAR + commit**

```bash
git commit -am "feat(harness-trust): primary-k policy + FoldResult bootstrap destinations — W1.2"
```

---

### Task W1.3: G3 under-coverage fix + primary-k verdict in `evaluate_promotion_gates`

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_harness.py` (`evaluate_promotion_gates`, `:182-195`)
- Test: `tests/contract/test_harness_trust_w1_g3_fix.py`

- [ ] **Step 1 (RED — Codex authors): failing tests for the two existing-code defects**

```python
# Build 4 FoldResults; vary how many are "market-available" (ndcg present at primary k).
def test_g3_under_coverage_returns_deferred_not_failed():
    # 1 evaluable fold (wins can never reach 3) MUST be "deferred", never "failed"
    gate = _eval_gates_with_market_available(position="RB", n_evaluable=1, model_wins=1)
    assert gate.g3_market_superiority_pass == "deferred"
    gate2 = _eval_gates_with_market_available(position="RB", n_evaluable=2, model_wins=2)
    assert gate2.g3_market_superiority_pass == "deferred"

def test_g3_verdict_keys_on_position_primary_k_for_qb():
    # QB keys on @12 (not @24): a QB run where @12 model≥market in 3/4 PASSES
    gate = _eval_gates_qb_primary12(model_ge_market_at_12_folds=3, at_24_folds=0)
    assert gate.g3_market_superiority_pass is True

def test_g3_fail_only_with_full_coverage_and_loss():
    # 4 evaluable folds, model loses 3 → genuine "failed"
    gate = _eval_gates_with_market_available(position="RB", n_evaluable=4, model_wins=1)
    assert gate.g3_market_superiority_pass is False
```
(Codex builds the `_eval_*` helpers from `FoldResult` fixtures; the names above are illustrative of the asserted behavior.)

- [ ] **Step 2: run RED, verify fail** (current code returns `"failed"` for 1–2 evaluable folds and keys on `@24`).

- [ ] **Step 3 (GREEN):** rewrite the G3 branch (`:182-195`):

```python
    # G3 — Market Superiority (keys on position-primary k; under-coverage → deferred)
    primary_k = PRIMARY_NDCG_K[position]
    def _ndcg_at(f, who):
        return getattr(f, f"ndcg_at_{primary_k}_{who}")
    market_available_folds = [f for f in folds if _ndcg_at(f, "market") is not None]
    if len(market_available_folds) < 3:
        g3_result: bool | str = "deferred"
        g3_status = "deferred"   # zero- or under-coverage; not a superiority failure
    else:
        wins = sum(1 for f in market_available_folds
                   if (_ndcg_at(f, "model") or 0) >= (_ndcg_at(f, "market") or 0))
        g3_result = wins >= 3
        g3_status = "passed" if g3_result else "failed"
```
(`GateResult.g3_market_superiority_pass` Literal already admits `True|False|"deferred"` — no schema change. The artifact's coverage caveat distinguishing zero vs partial coverage rides on the fold `metric_caveats` from W1.2.)

- [ ] **Step 4 (P4 — patch the existing test that encodes the OLD behavior, RED-first):** `tests/test_backtest_gates.py::test_g3_market_superiority_logic` (`:123`) keys the verdict on `ndcg_at_24_*` and (at `:159`) asserts a case `False` that, if it is a <3-evaluable-fold setup, must now be `"deferred"`. Audit it with Codex and patch RED-first:
  - Its fixture (`:31-32`) sets `ndcg_at_24_model/market`; for a position whose primary k is 12 (QB/TE) the verdict now keys on `@12`. Either pin the fixture position to RB/WR (primary k=24, so `@24` stays the verdict metric) **or** set the matching `ndcg_at_12_*` fields. Make the choice explicit.
  - The `:159` assertion: if it is full-coverage (4 evaluable folds, model loses) → still `False` (no change). If it is under-coverage (1–2 evaluable) → change the expected value to `"deferred"` (the C3 fix). Inspect and update to match the corrected semantics.
  - Other files set `g3_*="deferred"` as zero-coverage fixtures (`test_model_card.py`, `test_backtest_report.py`, `test_trust_surface_*`) — those stay valid (zero coverage → deferred unchanged); verify, don't blanket-edit.

- [ ] **Step 5: FULL suite green (shared gate fn — run everything); cockpit CLEAR + commit**

Run: `.venv/bin/python3.14 -m pytest -q`
Expected: all green, including the patched `test_g3_market_superiority_logic`.

```bash
git commit -am "fix(harness-trust): G3 under-coverage→deferred + primary-k verdict (+patch existing gate test) — W1.3"
```

---

### Task W1.4: point-in-time historical backfill → run G3

**Files:**
- Create: `scripts/backfill_market_archive.py` (or extend `scripts/ingest_market_archive.py`)
- Test: `tests/contract/test_harness_trust_w1_backfill.py`

- [ ] **Step 1 (RED): failing tests for point-in-time integrity + fail-closed**

```python
from scripts.backfill_market_archive import backfill_market_archive
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore

# An archive record = {archive_publish_date, sleeper_id, value, position, overall_rank, position_rank}
def _archive(publish_date):
    return [{"archive_publish_date": publish_date, "sleeper_id": sid, "value": v,
             "position": "QB", "overall_rank": r, "position_rank": r}
            for sid, v, r in [("111", 9000, 1), ("222", 8500, 2), ("333", 8000, 3)]]

def test_backfill_writes_via_append_with_provenance(tmp_path):
    # publish date within ±7 days of the target snapshot date → accepted, written immutably
    fake_archive = _archive("2021-09-02")   # within ±7d of 2021-09-01
    n = backfill_market_archive(archive=fake_archive, db_path=tmp_path / "fc.db",
                                snapshot_dates=["2021-09-01"])
    rows = MarketSnapshotStore(db_path=tmp_path / "fc.db").get_snapshot("2021-09-01")
    assert n == 3
    assert all(r["source"] in ("ktc_community_csv", "dp_archive") for r in rows)

def test_backfill_rejects_rows_outside_point_in_time_window(tmp_path):
    # publish date 60 days off the target → fails the ±7-day PIT rule → date stays unavailable
    revised_archive = _archive("2021-11-01")
    n = backfill_market_archive(archive=revised_archive, db_path=tmp_path / "fc.db",
                               snapshot_dates=["2021-09-01"])
    assert n == 0
    assert MarketSnapshotStore(db_path=tmp_path / "fc.db").get_snapshot("2021-09-01") == []

def test_backfill_skips_rows_missing_required_fields(tmp_path):
    # R2: a row missing `value` is malformed → skipped (fail closed), others still written
    arch = _archive("2021-09-02")
    del arch[1]["value"]                       # row 2 malformed
    n = backfill_market_archive(archive=arch, db_path=tmp_path / "fc.db",
                                snapshot_dates=["2021-09-01"])
    assert n == 2                              # 2 good rows in, malformed one dropped
    sids = {r["sleeper_id"] for r in MarketSnapshotStore(db_path=tmp_path / "fc.db").get_snapshot("2021-09-01")}
    assert sids == {"111", "333"}

def test_backfill_rejects_revised_rows_updated_after_capture(tmp_path):
    # R2: updated_at newer than archive_publish_date = post-hoc revision → not point-in-time → rejected
    arch = _archive("2021-09-02")
    for r in arch:
        r["updated_at"] = "2022-01-15"         # revised long after the capture date
    n = backfill_market_archive(archive=arch, db_path=tmp_path / "fc.db",
                                snapshot_dates=["2021-09-01"])
    assert n == 0
    assert MarketSnapshotStore(db_path=tmp_path / "fc.db").get_snapshot("2021-09-01") == []
```

- [ ] **Step 2: run RED, verify fail.**

- [ ] **Step 3 (GREEN):** implement `backfill_market_archive(archive, db_path, snapshot_dates)`. **Archive row format (P6 — pin it):** each archive record is `{archive_publish_date: "YYYY-MM-DD", sleeper_id: str, value: int, position: str, overall_rank: int|None, position_rank: int|None}` sourced from an **immutable historical capture** (a dated CSV/JSON snapshot file), NOT a live/revisable endpoint. **Point-in-time acceptance rule (fail-closed) — a row is accepted only if ALL hold (else the row is skipped):** (1) all required fields present (`sleeper_id`, `value`, `position`, `archive_publish_date`); (2) `abs(archive_publish_date − d) ≤ 7 days` (matching the store's ±7-day resolve window); (3) immutable capture — if the row carries an `updated_at`, then `updated_at ≤ archive_publish_date` (a newer `updated_at` = post-hoc revision → reject). If a target date ends with zero accepted rows → that date stays **`unavailable`** (G3 `"deferred"` for it). Map accepted rows to the store schema (`snapshot_date=d`, `league_settings_hash=<dynasty FC settings hash>`, `source` ∈ {`ktc_community_csv`,`dp_archive`}, `inserted_at=<now>`) and write via `append_snapshots` (immutable). No post-hoc revision; no survivorship filtering (busted/retired players retained at their historical value). **(External source pre-approved at Gate B §8.4; overlay-only.)**

- [ ] **Step 4 (GREEN, integration):** run the harness with `market_store` populated → G3 now evaluable; emit per-position `ndcg_model@k`, `ndcg_market@k`, per-fold win/loss, `pool_n`, and `compute_ndcg_diff_bootstrap` output into the artifact.

- [ ] **Step 5: full suite green; cockpit CLEAR (heavy adversarial — point-in-time + power) + commit**

```bash
git add scripts/backfill_market_archive.py tests/contract/test_harness_trust_w1_backfill.py
git commit -m "feat(harness-trust): point-in-time market backfill + G3 run — W1.4"
```

---

### Task W1.5: leakage wall re-verification under load

**Files:**
- Test: `tests/contract/test_harness_trust_w1_leakage.py`

- [ ] **Step 1 (RED → passes on clean tree): AST anti-laundering check** modeled on the S4 audit — assert no market/backfill field (`fc_value`, `market_*`, `ndcg_*_market`, snapshot-store imports) appears in any Engine A/B feature/training path (`engine_a*`, `engine_b*`, feature builders, `train_models.py`). The backfill increases market-data *volume*; this confirms its *role* stays overlay-only.

```python
def test_no_market_field_in_engine_feature_paths():
    offenders = scan_engine_paths_for_market_symbols()  # AST import + attribute scan
    assert offenders == [], f"market data leaked into model paths: {offenders}"
```

- [ ] **Step 2–3:** Should pass on the current tree (the wall holds); if it fails, that's a real leak to fix RED-first.
- [ ] **Step 4: cockpit governance CLEAR (Gemini lane) + commit**

```bash
git add tests/contract/test_harness_trust_w1_leakage.py
git commit -m "test(harness-trust): leakage wall re-verified under backfill load — W1.5"
```

---

# WORKSTREAM W4 — QB reliability stamp (one trust-surface field)

### Task W4.1: QB-reliability caveat field on the trust surface

**Files:**
- Modify: `app/api/routes/trust_surface.py` (`get_trust_surface`, after `:63`)
- Test: `tests/contract/test_harness_trust_w4_qb_stamp.py`

- [ ] **Step 1 (RED): failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_qb_trust_surface_carries_reliability_caveat(qb_artifact_with_r2):
    client = TestClient(app)
    data = client.get("/trust-surface/QB").json()
    rc = data["model_reliability"]
    assert rc["position"] == "QB"
    assert "r2_oos_mean" in rc and "spearman_rho_mean" in rc
    # banned-language-safe: descriptive metric caveat only, no action/verdict words
    blob = (rc["caveat"]).lower()
    assert not any(w in blob for w in
                   ["buy", "sell", "hold", "start", "drop", "verdict", "tier", "grade"])

def test_non_qb_surface_has_no_reliability_block(rb_artifact):
    client = TestClient(app)
    data = client.get("/trust-surface/RB").json()
    assert "model_reliability" not in data   # W4 is QB-only, one field
```

- [ ] **Step 2: run RED, verify fail.**

- [ ] **Step 3 (GREEN):** in `get_trust_surface`, for `pos_upper == "QB"` only, add one block sourced from the artifact's fold R²/Spearman:

```python
    if pos_upper == "QB":
        folds = result.folds
        _r2 = [f.r2_oos for f in folds if f.r2_oos is not None]
        r2_mean = (sum(_r2) / len(_r2)) if _r2 else None
        rho_mean = (sum(f.spearman_rho for f in folds) / len(folds)) if folds else None
        data["model_reliability"] = {
            "position": "QB",
            "r2_oos_mean": r2_mean,
            "spearman_rho_mean": rho_mean,
            "caveat": (
                "QB magnitude predictions carry elevated uncertainty: "
                f"OOS R²={'n/a' if r2_mean is None else round(r2_mean, 3)}, "
                f"Spearman={'n/a' if rho_mean is None else round(rho_mean, 3)}."
            ),
        }
```
Descriptive only — no buy/sell/roster-action; `decision_supported` unchanged; no frontend change (HOLD). Must pass the existing banned-language guard.

- [ ] **Step 4: focused + suite green; Step 5: governance CLEAR (banned-language) + commit**

```bash
git add app/api/routes/trust_surface.py tests/contract/test_harness_trust_w4_qb_stamp.py
git commit -m "feat(harness-trust): QB-reliability caveat on trust surface — W4.1"
```

---

## Final: PR → merge (Step 4 of the sequence)

- [ ] Full suite green (`.venv/bin/python3.14 -m pytest -q`), `.venv/bin/ruff check`, `validate_governance.py` PASS.
- [ ] Confirm inviolate boundaries: S4 modules + Engine A/B artifacts byte-unchanged; no market field in model paths (W1.5 green).
- [ ] `git push -u origin feature/harness-trust-completion` → `gh pr create` (audit-trail body: spec dual-CLEAR history, Gate B locks, build order, leakage attestation).
- [ ] Codex CLEAR + Gemini governance CLEAR on the PR → squash-merge → close-the-loop + AGENT_SYNC/ledger update.
- [ ] **Step 5 (post-merge):** run the G3 backfill + market comparison → publish the honest verdict (model beats / ties / loses the market) — the first real track record for the divergence read.

---

## Self-Review (against the spec)

- **Spec coverage:** W3 (§3) ✓ R² OOS disclose + fail-closed + null-mean. W2a (§4) ✓ immutable collection + scheduler + Gate-4 clock. W1 (§5) ✓ backfill + point-in-time + bootstrap + primary-k + under-coverage fix + leakage wall. W4 (§6) ✓ one QB field, banned-language-safe. W2b/§8.3 ✓ explicitly deferred (no task). R5 ✓ out of scope (no task).
- **Locked rulings honored:** R²=disclose (no gating task) ✓; G3 = ≥3/4 **evaluable** folds at primary-k with CI **disclosed not required-to-exclude-0** (W1.3 verdict + W1.1 CI reported, not gated) ✓; W1 archive approved/overlay-only (W1.4 + W1.5) ✓.
- **Type consistency:** `r2_oos: Optional[float]` (FoldResult) ↔ `r2_oos_per_fold: List[Optional[float]]` / `r2_oos_mean: Optional[float]` (ModelCardMetrics) ✓; `PRIMARY_NDCG_K` used identically in W1.2/W1.3 ✓; `FoldResult` market-comparison destinations (`primary_k`, `market_pool_n`, `ndcg_diff_primary_k`, `ndcg_diff_bca_ci95`) defined in W1.2, consumed in W1.3 verdict/artifact ✓; `append_snapshots` / `MarketSnapshotImmutabilityError` consistent across W2a.1/W2a.2 ✓; `compute_ndcg_diff_bootstrap` return keys (`ndcg_diff`, `ndcg_diff_bca_ci95`, `pool_n`, `method="bca_bootstrap"`, `caveat`) consistent W1.1↔W1.2 ✓ — **BCa** CI (scipy `method="BCa"`, `paired=True`), conforms to spec §5; name honest.
- **Cockpit note:** test blocks are the RED contract Codex authors; impl blocks are the GREEN target. W1.1 uses **BCa** (scipy `method="BCa"`, `paired=True`), conforming to spec §5 — no percentile downgrade.
