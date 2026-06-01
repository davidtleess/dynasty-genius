# Subsystem 4 v2 — Real nflreadr Draft-Capital Truth Loader — Design Spec

- **Date:** 2026-06-01
- **Status:** DESIGN (pre-implementation). Cockpit-converged (Codex technical + Gemini governance, 2 review rounds; both divergences resolved). **Addendum 2026-06-01** (see §9): six fail-closed hardening contracts — five new REDs (12–16) plus the new exception `NflreadrEmptyTruthError` — added after a Codex adversarial-falsification round on the implementation plan; David-approved contract amendment; tighten-only (no contract loosened); pending dual re-CLEAR of spec + plan together.
- **Initiative:** Subsystem 4 (manual-first backtest harness) v2 — replace the empty `_load_nflreadr_truth` v1 seam with a real, hardened, verified-column draft-capital truth loader so **real-mode Backtest-A runs** instead of failing closed (`nflreadr_truth_unavailable` → metrics null).
- **Scope (locked):** the truth loader ONLY. `_compute_bridge_coverage`'s S3 confirmed-class universe (`confirmed_class_unbridged_count`, `orphan_bridges_detected`) stays defaulted as a **separate later increment**.

## 1. Purpose & what "truth" means here

Backtest-A evaluates whether the mock-consensus ranking aligned with **realized NFL draft capital** for a draft class. The "truth" is the **draft-capital outcome** (which prospect was actually drafted, at what pick/round/team) — explicitly **NOT** realized NFL production/PPG or player "success" (those remain out of scope). The loader supplies `NflTruthRow` rows for the bridge join.

`NflTruthRow` (existing, `identity/prospect_nfl_bridge.py`): `gsis_id, pfr_id?, full_name, normalized_name, position, college?, draft_year, draft_pick_no, draft_round, nfl_team, fetched_at`.

## 2. Component & placement

One shared pure-ish function in **`src/dynasty_genius/identity/prospect_nfl_bridge.py`** (next to `NflTruthRow`):

```
load_nflreadr_draft_truth(draft_year, *, data_mode, fixture_path=None, fetched_at=None)
    -> NflreadrTruthLoadResult
```

- Returns a **typed** `NflreadrTruthLoadResult(rows: list[NflTruthRow], diagnostics: NflTruthLoadDiagnostics)` (both typed; no informal side-data / no `dict` diagnostics).
- **Placement rationale:** both consumers already import `NflTruthRow` from here; avoids a new `eval/` file (which would trip the S4 `AUTHORIZED_EVAL_FILES` allowlist); `prospect_nfl_bridge.py` is **not** byte-locked (the S3 inviolate set is the registries + `prospect_identity_resolver.py` + `college_prospect_identity.py`, verified).
- **Consumers (DRY):** `eval/backtest_mock_draft.py::_load_nflreadr_truth` (the backtest seam) and `scripts/build_prospect_nfl_bridge.py` both call it; the bridge script's buggy private copy is **removed**.

## 3. Data modes (synthetic ownership lives in the loader, fail-closed)

- **`synthetic`** → loads ONLY a committed **synthetic-truth fixture** keyed to the synthetic snapshot/bridge universe, discovered by convention at `resources/synthetic_draft_truth/<draft_year>.json` (overridable via `fixture_path`), resolved package-relative (`Path(__file__).resolve().parents[3] / "resources" / "synthetic_draft_truth" / f"{draft_year}.json"`, matching the existing `resources/` convention used by `aging_curves.py`). **[Amended 2026-06-01, David-approved, cockpit-unanimous:** the convention path was moved out of `tests/fixtures/backtest_mock_draft/synthetic_truth/` because (a) that path's `mock` substring trips the `prospect_nfl_bridge.py` "mock"-isolation audit when resolved in production code, and (b) production should not read a committed artifact from the `tests/` tree. The real-mode fixture is unaffected — it reaches the loader via the `fixture_path` argument, never hardcoded in production.**] **Never** calls `nflreadpy`; **never** mixes real draft truth with synthetic predictions. Missing or schema-invalid fixture → **fail closed** with an explicit `synthetic_truth_fixture_unavailable` / schema-drift error — **never a silent `[]`**. (The b-gate still abstains for `synthetic_data`; but the join metadata stays non-degenerate/truthful — no blanket `truth_row_missing`, because the join sees real-shaped synthetic truth.)
- **`real` + `fixture_path`** → load from the committed fixture (deterministic / offline tests + CI).
- **`real`, no fixture** → `nflreadpy.load_draft_picks(seasons=[draft_year])` via a **lazy inline import** inside the real branch (keeps S3 foundational loaders + light tests free of the heavy nflreadpy/pandas/polars dependency).

> **Fixture shape (both synthetic and real fixtures):** fixtures contain **source-shaped nflreadr rows** (the raw `load_draft_picks` columns: `season, round, pick, team, gsis_id, pfr_player_id, pfr_player_name, position, college`), **NOT** pre-normalized `NflTruthRow` objects. This forces the fixture path through the **same schema-gate + mapping + row-validation** as the live path, so the loader's contract is exercised identically in tests. (This changes the existing bridge-script fixture, which loaded pre-normalized `NflTruthRow` — that shape is retired.)

> Rationale for the synthetic-fixture decision (cockpit DIV-2, both lanes converged): `backtest_a_result.json` is an **audit artifact**, not just a gate status. `synthetic → []` would serialize `truth_row_missing` for every row — a false join-failure story even though the intended abstain reason is synthetic-data safety. A committed synthetic-truth fixture keeps the join truthful while the b-gate still abstains for the right reason.

## 4. Fail-closed contract

1. **Schema gate (no guessed columns).** Required columns `{season, round, pick, team, gsis_id, pfr_player_id, pfr_player_name, position, college}` must all be present in the source → raise a typed `NflreadrSchemaDriftError` if any is missing. (`pfr_player_id` is required as a **column** — drift check — even though its per-row value may be null; resolves cockpit DIV-1.)
2. **Season integrity (fail-loud, NOT a skip).** Every source/fixture row with `season != draft_year` is **source contamination** → raise a typed `NflreadrSourceContaminationError` with the offending `(season, draft_year)` and a row identifier. This is an EXCEPTION, not a counted "skip-success" — a contaminated source must halt the load, not silently drop the bad rows and proceed. (Distinct from the join-stage `JoinDiagnostics.wrong_year_truth_collisions`, which is a separate consensus↔truth collision concern.)
3. **Column mapping.** `pfr_id ← pfr_player_id` (null/empty value allowed → `pfr_id=None`); `full_name`/`normalized_name ← pfr_player_name` (reuse S3 `normalize_name`); `pick → draft_pick_no`; `round → draft_round`; `team → nfl_team`.
4. **Per-row skips (counted, never a silent default).** Skip + tally any row with: empty/missing `gsis_id` (un-joinable); non-integer or missing `pick` or `round` (never the silent `0`); empty `pfr_player_name`; empty `position`; empty `team`. `college` may be null.
5. **No broad exception swallow.** Replaces the existing bridge script's `except Exception → []`. A fetch failure or schema drift **raises / exits nonzero** — never returns `[]` (an empty truth universe would fabricate false UDFAs in discovery and false `truth_row_missing` in the backtest).
6. **Reproducibility of `fetched_at`** (raw nflreadr rows have NO `fetched_at` column, so it is supplied deterministically — never invented per-row at runtime). The single pinned contract:
   - **Fixture file shape:** `{"metadata": {"fetched_at": "<ISO-8601 Z>"}, "rows": [<source-shaped nflreadr rows>]}`. Every `NflTruthRow` produced from that fixture takes `fetched_at` from `metadata.fetched_at` → two loads of an identical fixture are **bit-identical**. A fixture missing `metadata.fetched_at` → **raise** (unless the `fetched_at` argument is supplied as an override).
   - **Live (no fixture):** use the explicit `fetched_at` argument when provided; otherwise `datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")` — the one non-deterministic path, live-only and clearly marked.
   - **Never** `datetime.utcnow()` (deprecated in 3.12+).
7. **"mock" scrub (S4-audit landmine).** `test_mock_data_and_market_field_isolation` asserts the substring "mock" is absent from `prospect_nfl_bridge.py`. The loader's code, docstrings, parameter names, variables, and exceptions must avoid "mock" — use "synthetic" / "simulated" / "fixture" / "backtest". (The seam wrapper lives in `backtest_mock_draft.py`, where "mock" is fine.)

## 5. Diagnostics

`NflreadrTruthLoadResult.diagnostics` is a **typed Pydantic model** `NflTruthLoadDiagnostics` (NOT an informal dict), with fields: `required_columns_seen: list[str]`, `truth_rows_loaded: int`, `skipped_missing_gsis_id: int`, `skipped_bad_pick: int`, `skipped_bad_round: int`, `skipped_missing_name: int`, `skipped_missing_position: int`, `skipped_missing_team: int`. **No `skipped_wrong_season`** — wrong-season is a fail-loud exception (§4.2), never a counted skip.

**Artifact home (pinned).** `JoinDiagnostics` is `extra="forbid"`, so the load diagnostics are NOT stuffed into it. Instead the runner threads `NflTruthLoadDiagnostics` into the **`BacktestAResult` metadata** as an explicit `truth_load_diagnostics` field, serialized into `backtest_a_result.json` (auditability) — not just logged. The bridge script surfaces the same typed diagnostics in its discovery metadata. (Whether to additionally add an explicit field to `JoinDiagnostics` is left to the plan; the default home is the `BacktestAResult` metadata to avoid modifying the forbid-extra join model.)

## 6. Guardrails

Model-blind (draft data is not market data); backtest/bridge-only consumers — **no** `app/services` / `scoring` / `models` import of `prospect_nfl_bridge` (the S4 audit `BANNED_IMPORT_MODULES` bans those production imports; lazy nflreadpy keeps the dependency contained); `decision_supported` unaffected; frontend HOLD intact; no Engine A/B feature or training change.

## 7. RED contracts (for the implementation plan / cockpit-TDD)

1. `load_nflreadr_draft_truth` fixture mode (real) → deterministic `NflTruthRow` rows from a committed **source-shaped** fixture (raw nflreadr columns), exercising the full schema-gate + mapping + validation path. A pre-normalized `NflTruthRow`-shaped fixture is rejected (the gate/mapping is never bypassed).
2. Schema-drift: a source missing any required column (incl. `pfr_player_id`) → raises `NflreadrSchemaDriftError`.
3. Wrong-season fixture row (`season != draft_year`) → raises `NflreadrSourceContaminationError` (fail loud), NOT a counted skip and never silently coerced to `draft_year`.
4. Row skips + diagnostics: empty `gsis_id` / non-int `pick` / non-int `round` / empty `pfr_player_name` / empty `position` / empty `team` each → skipped + counted in diagnostics (no silent `0`, no `""` gsis_id).
5. `pfr_player_id` present-column + null value → `pfr_id=None` (optional value); missing column → schema-drift raise.
6. Synthetic mode loads the committed synthetic-truth fixture, never calls nflreadpy, and does NOT blanket-emit `truth_row_missing`; b-gate still abstains for `synthetic_data`; missing synthetic fixture → explicit `synthetic_truth_fixture_unavailable` fail-closed (not `[]`).
7. Backtest seam: real-mode `run_backtest_a` with a fixture no longer surfaces `nflreadr_truth_unavailable` (real-mode runs); diagnostics appear in the artifact.
8. Bridge script: schema drift / fetch failure propagates (raise / nonzero exit), never returns `[]`.
9. `fetched_at` reproducibility: two loads of an identical fixture (same `metadata.fetched_at`) produce bit-identical `NflTruthRow` rows (no runtime `utcnow`); a fixture missing `metadata.fetched_at` raises unless a `fetched_at` override is supplied.
10. S4 audit stays green: no "mock" substring introduced into `prospect_nfl_bridge.py`; no new banned production import; `AUTHORIZED_EVAL_FILES` untouched.
11. Diagnostics are a typed `NflTruthLoadDiagnostics` model (not a dict) and surface in the `BacktestAResult` metadata (`truth_load_diagnostics`), serialized into `backtest_a_result.json`.
12. **Empty source fails closed (not vacuous success):** a fixture with `rows == []` or a live frame with zero rows does NOT pass the schema gate vacuously. Real/live empty source → raises `NflreadrEmptyTruthError`; synthetic empty fixture → `synthetic_truth_fixture_unavailable`. Never an empty-rows success (which would re-create `nflreadr_truth_unavailable` / synthetic degeneracy).
13. **Duplicate `gsis_id` preserved (no dedupe):** two source rows with the same `gsis_id` both appear in `result.rows`; the loader does not deduplicate (the join stage `join_bridge_to_realized` owns the duplicate-`gsis_id` hard-block, and silent loader-side de-duping would erase that fail-closed evidence).
14. **Extra source columns dropped safely:** a source row carrying columns beyond `_REQUIRED_DRAFT_COLUMNS` loads successfully, and the extra keys do NOT appear in the produced `NflTruthRow.model_dump()` — the mapping constructs `NflTruthRow` from explicitly-mapped fields only and never splats the raw source row into the `extra="forbid"` model.
15. **Numeric coercion pinned to a single rule:** `pick`/`round` are valid iff `type(value) is int` (accepts the real polars/nflreadpy `int`; skips `bool`, `float`, and numeric strings → `skipped_bad_pick`/`skipped_bad_round`). `season` is valid iff `type(value) is int and value == draft_year`; a non-int season (`"2024"`, `2024.0`, `True`) → `NflreadrSourceContaminationError` (no `int()` coercion).
16. **`fetched_at` stored verbatim:** the `metadata.fetched_at` (or override) string is preserved byte-for-byte — never parsed/reformatted — so `+00:00` stays `+00:00` and `Z` stays `Z`; two loads of an identical fixture are bit-identical. Only the live no-fixture path *generates* a `…Z` string.

## 8. Out of scope

`_compute_bridge_coverage` confirmed-class universe (separate increment); realized NFL production/PPG truth; any Engine A/B model change; the W2a FantasyCalc/market path (unrelated).

## 9. Addendum (2026-06-01) — adversarial-review hardening

A Codex adversarial-falsification round on the implementation plan surfaced six contract points the original §4/§7 under-specified. David approved adding them as formal spec contracts (this §9 + RED 12–16 above). All are **tighten-only** — they strengthen the fail-closed posture of §4 and loosen nothing.

**New typed exception.** `NflreadrEmptyTruthError` (subclasses `ValueError`), raised for an empty real/live source (§4 / RED 12). This makes the loader's exception set: `NflreadrSchemaDriftError`, `NflreadrSourceContaminationError`, `NflreadrEmptyTruthError`.

**Fail-closed refinements (amend §4):**
- **§4.1a (empty source).** The schema gate must not pass vacuously on zero rows; an empty source is a fail-closed condition (RED 12), not an empty-rows success.
- **§4.3a (numeric coercion).** `pick`/`round` valid iff `type(value) is int`; `season` valid iff `type(value) is int and == draft_year` — no `int()` coercion of strings/floats/bools (RED 15). Pins a single expected outcome for RED authorship.
- **§4.4a (duplicate `gsis_id`).** Preserved, not de-duped — the join stage owns the hard-block (RED 13).
- **§4.4b (extra columns).** `NflTruthRow` is built from explicitly-mapped fields only; raw source rows are never splatted into the `extra="forbid"` model (RED 14).
- **§4.6a (`fetched_at` verbatim).** Stored byte-for-byte; no normalization (RED 16) — guarantees the §4.6 bit-identical property across `+00:00`/`Z` forms.

**Implementation-seam note (informs the plan, not a public contract):** the backtest seam `eval/backtest_mock_draft.py::_load_nflreadr_truth` returns the full `NflreadrTruthLoadResult` (not `list[NflTruthRow]`) so `run_backtest_a` can thread `diagnostics.model_dump()` into `BacktestAResult.metadata["truth_load_diagnostics"]`; `run_backtest_a`'s public signature is unchanged. Imports follow the repo convention `from src.dynasty_genius...`.
