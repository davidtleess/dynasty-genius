# MFL Rookie ADP Divergence Report (Increment B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone, read-only backend report that surfaces where real-draft MFL rookie ADP disagrees with our model's rookie ranking (`xvar_class_rank`) — artifact-only, never mutating model/PVO state.

**Architecture:** A narrow adapter helper exposes normalized MFL rookie ADP rows + freshness caveats. A pure builder joins them to `prospect_cards.json` (fail-closed on name+position within `draft_class==season`) and emits a divergence artifact with a coverage block. A writer mirrors the FantasyCalc divergence writer (run+latest JSON+MD). A thin script wires it. A read-only state contract test proves model/PVO files are byte-unchanged.

**Tech Stack:** Python 3.14, `pytest` (`.venv/bin/python3.14 -m pytest`), `monkeypatch`. Reuses `prospect_identity_resolver.normalize_name`.

**Spec:** `docs/superpowers/specs/2026-05-27-mfl-rookie-adp-divergence-design.md`

**Cockpit execution:** Codex test-drives each RED contract; Claude implements to green. One agent edits at a time. Run after each task:
`./.venv/bin/python3.14 -m pytest tests/test_mfl_rookie_adp_divergence.py tests/test_mfl_adp_adapter.py -q`

**Scope fences (do NOT do these):** no API endpoint / no frontend · no PVO/team-strength/trade/training feed · no mutation of `prospect_cards.json` or any model/PVO artifact · no `MarketSource.fetch()` contract change · MFL stays barred from calibration + training.

---

## File Structure

- **Modify** `src/dynasty_genius/adapters/mfl_adp_adapter.py` — add `fetch_rookie_adp_rows(season=None) -> (rows, caveats)`.
- **Create** `src/dynasty_genius/mfl_rookie_adp_divergence.py` — `_key`, `_index_unique`, `_flag`, `_coverage`, `build_mfl_rookie_adp_divergence`, `_render_md`, `write_mfl_rookie_adp_divergence_artifacts`.
- **Create** `scripts/build_mfl_rookie_adp_divergence.py` — wires fetch + `prospect_cards.json` + build + write to `app/data/valuation/`.
- **Create** `tests/test_mfl_rookie_adp_divergence.py` — builder, writer, script, and read-only state contract tests.

---

## Task 1: Adapter helper `fetch_rookie_adp_rows`

**Files:**
- Modify: `src/dynasty_genius/adapters/mfl_adp_adapter.py`
- Test: `tests/test_mfl_adp_adapter.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_mfl_adp_adapter.py`:
```python
def test_fetch_rookie_adp_rows_returns_rows_and_caveats(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    def _resp_for(url, **kwargs):
        class _R:
            def raise_for_status(self): ...
            def json(self):
                if "TYPE=players" in url:
                    return json.loads(PLAYERS_FIXTURE.read_text())
                return json.loads(ADP_FIXTURE.read_text())
        return _R()

    with patch("httpx.get", side_effect=_resp_for):
        rows, caveats = m.fetch_rookie_adp_rows(2026)
    assert isinstance(rows, list) and isinstance(caveats, list)
    assert all(r["source"] == "mfl_rookie_adp" and r["decision_supported"] is False for r in rows)
    by_id = {r["mfl_id"]: r for r in rows}
    assert by_id["17472"]["full_name"] is not None         # matched via players map
    assert by_id["99999"]["full_name"] is None             # unmatched id stays None
    # intrinsic blend caveats present on rows; transient freshness caveat present in channel
    assert "mfl_adp_format_blended_qb_count" in by_id["17472"]["caveats"]
    assert any(c.startswith("source_publish_age_h=") or c == "mfl_adp_timestamp_unavailable" for c in caveats)


def test_fetch_rookie_adp_rows_does_not_change_market_source_contract():
    # MarketSource.fetch() stays rows-only; the helper is additive.
    from src.dynasty_genius.adapters.market_source import MflAdpMarketSource
    assert hasattr(__import__("src.dynasty_genius.adapters.mfl_adp_adapter", fromlist=["x"]), "fetch_rookie_adp_rows")
    import inspect
    from src.dynasty_genius.adapters import market_source
    assert "caveats" not in inspect.getsource(market_source.MflAdpMarketSource.fetch)
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -k fetch_rookie_adp_rows -v`
Expected: FAIL (`AttributeError: ... fetch_rookie_adp_rows`).

- [ ] **Step 3: Implement** (append to `mfl_adp_adapter.py`, after `normalize_mfl_adp_entry`)

```python
def fetch_rookie_adp_rows(season: int | None = None) -> tuple[list[dict], list[str]]:
    """Normalized MFL rookie ADP rows + transient caveats — for report consumers.

    Wraps fetch_adp_with_cache + fetch_players_with_cache + normalize_mfl_adp_entry.
    Additive: does NOT change MarketSource.fetch() (which stays rows-only).
    """
    season = season or _current_season()
    adp_rows, adp_caveats = fetch_adp_with_cache(season)
    players_map, players_caveats = fetch_players_with_cache(season)
    rows = [normalize_mfl_adp_entry(r, players_map) for r in adp_rows]
    return rows, list(adp_caveats) + list(players_caveats)
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -q`
Expected: PASS (all, incl. existing).

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/mfl_adp_adapter.py tests/test_mfl_adp_adapter.py
git commit -m "feat(mfl-adp): fetch_rookie_adp_rows helper (rows + caveats; fetch() untouched)"
```

---

## Task 2: Pure builder `build_mfl_rookie_adp_divergence`

**Files:**
- Create: `src/dynasty_genius/mfl_rookie_adp_divergence.py`
- Test: `tests/test_mfl_rookie_adp_divergence.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mfl_rookie_adp_divergence.py`:
```python
from __future__ import annotations

from src.dynasty_genius.mfl_rookie_adp_divergence import build_mfl_rookie_adp_divergence


def _adp(mfl_id, name, pos, rank):
    return {"mfl_id": mfl_id, "full_name": name, "position": pos,
            "market_adp_rank": rank, "market_average_pick": float(rank),
            "source": "mfl_rookie_adp", "decision_supported": False,
            "caveats": ["mfl_adp_format_blended_qb_count", "mfl_adp_te_premium_unfiltered"]}


def _card(name, pos, draft_class, xvar_rank, dvs_rank=None):
    return {"full_name": name, "position": pos, "draft_class": draft_class,
            "xvar_class_rank": xvar_rank, "dvs_class_rank": dvs_rank,
            "xvar": 0.0, "dynasty_value_score": 0.0}


def _build(adp, cards, **kw):
    return build_mfl_rookie_adp_divergence(
        adp, cards, season=2026, captured_at="2026-05-27T00:00:00Z",
        caveats=["source_publish_age_h=1"], **kw)


def test_match_flags_and_xvar_primary():
    adp = [_adp("1", "Caleb Williams", "QB", 6),     # model_rank 8 -> gap -2 -> aligned
           _adp("2", "Big Riser", "WR", 1),          # model_rank 10 -> gap -9 -> market_higher_than_model
           _adp("3", "Model Darling", "RB", 12)]      # model_rank 2 -> gap +10 -> model_higher_than_market
    cards = [_card("Caleb Williams", "QB", 2026, 8, dvs_rank=5),
             _card("Big Riser", "WR", 2026, 10),
             _card("Model Darling", "RB", 2026, 2)]
    out = _build(adp, cards)
    by = {r["full_name"]: r for r in out["matched"]}
    assert by["Caleb Williams"]["model_rank"] == 8 and by["Caleb Williams"]["rank_gap"] == -2
    assert by["Caleb Williams"]["divergence_flag"] == "aligned"
    assert by["Caleb Williams"]["dvs_class_rank"] == 5          # dvs emitted alongside
    assert by["Big Riser"]["divergence_flag"] == "market_higher_than_model"
    assert by["Model Darling"]["divergence_flag"] == "model_higher_than_market"
    assert out["rank_source"] == "xvar_class_rank_v1" and out["aligned_band"] == 3
    assert out["decision_supported"] is False
    assert all(r["decision_supported"] is False for r in out["matched"])


def test_model_rank_unavailable_when_xvar_missing():
    adp = [_adp("1", "No Rank", "QB", 3)]
    cards = [_card("No Rank", "QB", 2026, None)]   # xvar_class_rank None
    out = _build(adp, cards)
    assert out["matched"] == []
    assert out["model_rank_unavailable"][0]["full_name"] == "No Rank"


def test_season_isolation_excludes_other_classes():
    adp = [_adp("1", "Wrong Year", "QB", 1)]
    cards = [_card("Wrong Year", "QB", 2025, 1)]   # different draft_class
    out = _build(adp, cards)
    assert out["adp_draft_class"] == 2026
    assert out["matched"] == [] and len(out["unmatched_adp"]) == 1


def test_unmatched_both_sides():
    adp = [_adp("1", "Adp Only", "WR", 1)]
    cards = [_card("Card Only", "RB", 2026, 1)]
    out = _build(adp, cards)
    assert [r["full_name"] for r in out["unmatched_adp"]] == ["Adp Only"]
    assert [r["full_name"] for r in out["unmatched_model"]] == ["Card Only"]


def test_fail_closed_ambiguous_not_matched():
    adp = [_adp("1", "Dup Name", "WR", 1), _adp("2", "Dup Name", "WR", 2)]  # dup key on ADP side
    cards = [_card("Dup Name", "WR", 2026, 1)]
    out = _build(adp, cards)
    assert out["matched"] == []                                   # never guess
    assert any(a["side"] == "adp" and a["reason"] == "adp_identity_ambiguous" for a in out["ambiguous"])


def test_coverage_block_reconciles_and_guards():
    adp = [_adp("1", "Caleb Williams", "QB", 6), _adp("2", "Adp Only", "WR", 1),
           _adp("3", "Dup", "RB", 3), _adp("4", "Dup", "RB", 4)]
    cards = [_card("Caleb Williams", "QB", 2026, 8)]
    out = _build(adp, cards)
    cov = out["coverage"]
    assert cov["total_adp_rows"] == 4
    adp_ambig = sum(1 for a in out["ambiguous"] if a["side"] == "adp")
    assert cov["matched_count"] + cov["model_rank_unavailable_count"] + cov["unmatched_adp_count"] + adp_ambig == 4
    assert cov["decision_supported_true_count"] == 0
    assert cov["banned_language_present"] == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_rookie_adp_divergence.py -q`
Expected: FAIL (`ModuleNotFoundError: ...mfl_rookie_adp_divergence`).

- [ ] **Step 3: Implement** — create `src/dynasty_genius/mfl_rookie_adp_divergence.py`

```python
"""MFL rookie ADP divergence report (Follow-up B, Increment B).

Read-only over model output. Joins normalized MFL rookie ADP rows to prospect_cards
(by normalized name + position within draft_class == season, fail-closed on ambiguity)
and emits a standalone divergence artifact. Never mutates model/PVO state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.dynasty_genius.adapters.prospect_identity_resolver import normalize_name

ALIGNED_BAND_DEFAULT = 3
_BANNED_VERDICT_WORDS = frozenset(
    {"buy", "sell", "win", "loss", "verdict", "accept", "reject", "target", "fade"}
)


def _key(name: str | None, position: str | None) -> tuple[str, str]:
    return (normalize_name(name or ""), (position or "").upper())


def _index_unique(
    items: list[dict], name_of: Callable[[dict], Any], pos_of: Callable[[dict], Any]
) -> tuple[dict[tuple[str, str], dict], list[dict]]:
    """(unique_by_key, ambiguous_rows). Keys appearing >1x are excluded from unique."""
    by_key: dict[tuple[str, str], list[dict]] = {}
    for it in items:
        by_key.setdefault(_key(name_of(it), pos_of(it)), []).append(it)
    unique = {k: v[0] for k, v in by_key.items() if len(v) == 1}
    ambiguous_rows = [it for v in by_key.values() if len(v) > 1 for it in v]
    return unique, ambiguous_rows


def _flag(rank_gap: int, aligned_band: int) -> str:
    if abs(rank_gap) <= aligned_band:
        return "aligned"
    return "model_higher_than_market" if rank_gap > aligned_band else "market_higher_than_model"


def _coverage(artifact: dict, *, total_adp_rows: int) -> dict:
    banned = sorted(
        {
            w
            for r in artifact["matched"]
            for w in _BANNED_VERDICT_WORDS
            if w in str(r.get("divergence_flag", "")).lower()
        }
    )
    return {
        "total_adp_rows": total_adp_rows,
        "matched_count": len(artifact["matched"]),
        "unmatched_adp_count": len(artifact["unmatched_adp"]),
        "unmatched_model_count": len(artifact["unmatched_model"]),
        "ambiguous_count": len(artifact["ambiguous"]),
        "model_rank_unavailable_count": len(artifact["model_rank_unavailable"]),
        "decision_supported_true_count": sum(
            1 for r in artifact["matched"] if r.get("decision_supported") is True
        ),
        "banned_language_present": banned,
    }


def build_mfl_rookie_adp_divergence(
    adp_rows: list[dict],
    prospect_cards: list[dict],
    *,
    season: int,
    captured_at: str,
    caveats: list[str],
    aligned_band: int = ALIGNED_BAND_DEFAULT,
) -> dict:
    cards = [c for c in prospect_cards if c.get("draft_class") == season]
    model_unique, model_ambiguous = _index_unique(
        cards, lambda c: c.get("full_name"), lambda c: c.get("position")
    )
    adp_unique, adp_ambiguous = _index_unique(
        adp_rows, lambda r: r.get("full_name"), lambda r: r.get("position")
    )

    matched: list[dict] = []
    model_rank_unavailable: list[dict] = []
    unmatched_adp: list[dict] = []
    matched_model_keys: set[tuple[str, str]] = set()

    for k, row in adp_unique.items():
        ident = {"mfl_id": row.get("mfl_id"), "full_name": row.get("full_name"),
                 "position": row.get("position")}
        card = model_unique.get(k)
        if card is None:
            unmatched_adp.append(ident)
            continue
        matched_model_keys.add(k)
        model_rank = card.get("xvar_class_rank")
        market_adp_rank = row.get("market_adp_rank")
        if model_rank is None or market_adp_rank is None:
            model_rank_unavailable.append({**ident, "reason": "model_rank_unavailable"})
            continue
        rank_gap = market_adp_rank - model_rank
        matched.append({
            **ident,
            "market_adp_rank": market_adp_rank,
            "market_average_pick": row.get("market_average_pick"),
            "model_rank": model_rank,
            "dvs_class_rank": card.get("dvs_class_rank"),
            "xvar": card.get("xvar"),
            "dynasty_value_score": card.get("dynasty_value_score"),
            "rank_gap": rank_gap,
            "divergence_flag": _flag(rank_gap, aligned_band),
            "decision_supported": False,
        })

    unmatched_model = [
        {"full_name": c.get("full_name"), "position": c.get("position"),
         "model_rank": c.get("xvar_class_rank")}
        for k, c in model_unique.items()
        if k not in matched_model_keys
    ]
    ambiguous = (
        [{"mfl_id": r.get("mfl_id"), "full_name": r.get("full_name"),
          "position": r.get("position"), "side": "adp", "reason": "adp_identity_ambiguous"}
         for r in adp_ambiguous]
        + [{"full_name": c.get("full_name"), "position": c.get("position"),
            "side": "model", "reason": "model_identity_ambiguous"}
           for c in model_ambiguous]
    )

    artifact = {
        "captured_at": captured_at,
        "source": "mfl_rookie_adp",
        "adp_draft_class": season,
        "rank_source": "xvar_class_rank_v1",
        "aligned_band": aligned_band,
        "decision_supported": False,
        "caveats": list(caveats),
        "matched": matched,
        "model_rank_unavailable": model_rank_unavailable,
        "unmatched_adp": unmatched_adp,
        "unmatched_model": unmatched_model,
        "ambiguous": ambiguous,
    }
    artifact["coverage"] = _coverage(artifact, total_adp_rows=len(adp_rows))
    return artifact
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_rookie_adp_divergence.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/mfl_rookie_adp_divergence.py tests/test_mfl_rookie_adp_divergence.py
git commit -m "feat(mfl-divergence): pure builder — fail-closed join, xvar primary, coverage block"
```

---

## Task 3: Artifact writer (run+latest JSON+MD)

**Files:**
- Modify: `src/dynasty_genius/mfl_rookie_adp_divergence.py`
- Test: `tests/test_mfl_rookie_adp_divergence.py`

- [ ] **Step 1: Write the failing test**

```python
def test_writer_emits_run_and_latest_json_and_md(tmp_path):
    from src.dynasty_genius.mfl_rookie_adp_divergence import (
        build_mfl_rookie_adp_divergence,
        write_mfl_rookie_adp_divergence_artifacts,
    )
    out = _build([_adp("1", "Caleb Williams", "QB", 6)],
                 [_card("Caleb Williams", "QB", 2026, 8, dvs_rank=5)])
    paths = write_mfl_rookie_adp_divergence_artifacts(out, output_dir=tmp_path, run_id="r1")
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == [
        "mfl_rookie_adp_divergence_latest.json",
        "mfl_rookie_adp_divergence_latest.md",
        "mfl_rookie_adp_divergence_r1.json",
        "mfl_rookie_adp_divergence_r1.md",
    ]
    import json as _j
    assert _j.loads(paths["latest_json"].read_text())["matched"][0]["full_name"] == "Caleb Williams"
    md = paths["latest_md"].read_text()
    assert "Caleb Williams" in md and "aligned" in md
    assert "decision_supported=False" in md or "decision_supported: false" in md.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_rookie_adp_divergence.py -k writer -v`
Expected: FAIL (`cannot import name 'write_mfl_rookie_adp_divergence_artifacts'`).

- [ ] **Step 3: Implement** (append to `mfl_rookie_adp_divergence.py`)

```python
def _render_md(divergence: dict) -> str:
    cov = divergence["coverage"]
    lines = [
        f"# MFL Rookie ADP Divergence — class {divergence['adp_draft_class']}",
        "",
        f"- captured_at: {divergence['captured_at']}",
        f"- source: {divergence['source']} | rank_source: {divergence['rank_source']} "
        f"| aligned_band: {divergence['aligned_band']}",
        f"- decision_supported: false (overlay/inference-only)",
        f"- caveats: {', '.join(divergence['caveats']) or 'none'}",
        "",
        f"Coverage: total_adp={cov['total_adp_rows']} matched={cov['matched_count']} "
        f"unmatched_adp={cov['unmatched_adp_count']} unmatched_model={cov['unmatched_model_count']} "
        f"ambiguous={cov['ambiguous_count']} model_rank_unavailable={cov['model_rank_unavailable_count']}",
        "",
        "| Rookie | Pos | Market ADP rank | Model rank (xVAR) | rank_gap | flag |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(divergence["matched"], key=lambda x: x["market_adp_rank"]):
        lines.append(
            f"| {r['full_name']} | {r['position']} | {r['market_adp_rank']} | "
            f"{r['model_rank']} | {r['rank_gap']:+d} | {r['divergence_flag']} |"
        )
    return "\n".join(lines) + "\n"


def write_mfl_rookie_adp_divergence_artifacts(
    divergence: dict, *, output_dir: Path, run_id: str | None = None
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = run_id or str(divergence["captured_at"]).replace(":", "").replace("-", "")
    json_payload = json.dumps(divergence, indent=2, sort_keys=True) + "\n"
    md_payload = _render_md(divergence)
    run_json = output_dir / f"mfl_rookie_adp_divergence_{safe}.json"
    latest_json = output_dir / "mfl_rookie_adp_divergence_latest.json"
    run_md = output_dir / f"mfl_rookie_adp_divergence_{safe}.md"
    latest_md = output_dir / "mfl_rookie_adp_divergence_latest.md"
    run_json.write_text(json_payload)
    latest_json.write_text(json_payload)
    run_md.write_text(md_payload)
    latest_md.write_text(md_payload)
    return {"run_json": run_json, "latest_json": latest_json,
            "run_md": run_md, "latest_md": latest_md}
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_rookie_adp_divergence.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/mfl_rookie_adp_divergence.py tests/test_mfl_rookie_adp_divergence.py
git commit -m "feat(mfl-divergence): artifact writer — run+latest JSON+MD"
```

---

## Task 4: Build script + read-only state contract test

**Files:**
- Create: `scripts/build_mfl_rookie_adp_divergence.py`
- Test: `tests/test_mfl_rookie_adp_divergence.py`

- [ ] **Step 1: Write the failing test (read-only state contract)**

```python
def test_script_is_read_only_and_writes_only_divergence_artifacts(tmp_path, monkeypatch):
    import hashlib
    from pathlib import Path
    import scripts.build_mfl_rookie_adp_divergence as bld

    ROOT = Path(__file__).resolve().parents[1]
    cards_path = ROOT / "resources" / "prospect_cards.json"
    pvo_path = ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (cards_path, pvo_path) if p.exists()}

    monkeypatch.setattr(bld, "_fetch_rows", lambda season: (
        [_adp("1", "Caleb Williams", "QB", 6)], ["source_publish_age_h=1"]))

    bld.main(season=2026, output_dir=tmp_path)

    after = {p: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (cards_path, pvo_path) if p.exists()}
    assert before == after                                   # model/PVO byte-identical
    written = sorted(p.name for p in tmp_path.iterdir())
    assert written == [
        "mfl_rookie_adp_divergence_latest.json",
        "mfl_rookie_adp_divergence_latest.md",
        "mfl_rookie_adp_divergence_phase-b_2026.json",
        "mfl_rookie_adp_divergence_phase-b_2026.md",
    ]
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_rookie_adp_divergence.py -k read_only -v`
Expected: FAIL (`ModuleNotFoundError: scripts.build_mfl_rookie_adp_divergence`).

- [ ] **Step 3: Implement** — create `scripts/build_mfl_rookie_adp_divergence.py`

```python
#!/usr/bin/env python3.14
"""Build the MFL rookie ADP divergence report (read-only over model output)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.dynasty_genius.adapters.mfl_adp_adapter import (  # noqa: E402
    _current_season,
    fetch_rookie_adp_rows,
)
from src.dynasty_genius.mfl_rookie_adp_divergence import (  # noqa: E402
    build_mfl_rookie_adp_divergence,
    write_mfl_rookie_adp_divergence_artifacts,
)

_CARDS_PATH = _ROOT / "resources" / "prospect_cards.json"
_OUTPUT_DIR = _ROOT / "app" / "data" / "valuation"


def _fetch_rows(season: int):
    """Seam: live read-only MFL fetch (monkeypatched in tests)."""
    return fetch_rookie_adp_rows(season)


def main(season: int | None = None, output_dir: Path | None = None) -> dict:
    season = season or _current_season()
    output_dir = Path(output_dir) if output_dir is not None else _OUTPUT_DIR
    rows, caveats = _fetch_rows(season)
    cards = json.loads(_CARDS_PATH.read_text())          # read-only
    captured_at = datetime.now(timezone.utc).isoformat()
    divergence = build_mfl_rookie_adp_divergence(
        rows, cards, season=season, captured_at=captured_at, caveats=caveats,
    )
    paths = write_mfl_rookie_adp_divergence_artifacts(
        divergence, output_dir=output_dir, run_id=f"phase-b_{season}",
    )
    cov = divergence["coverage"]
    print(
        f"Wrote {paths['latest_json']}; matched={cov['matched_count']} "
        f"unmatched_adp={cov['unmatched_adp_count']} unmatched_model={cov['unmatched_model_count']} "
        f"ambiguous={cov['ambiguous_count']} model_rank_unavailable={cov['model_rank_unavailable_count']}"
    )
    return divergence


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_rookie_adp_divergence.py -q`
Expected: PASS (read-only contract + all builder/writer tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/build_mfl_rookie_adp_divergence.py tests/test_mfl_rookie_adp_divergence.py
git commit -m "feat(mfl-divergence): build script + read-only state contract (cards/PVO byte-identical)"
```

---

## Task 5: Full-suite + governance guard + ledger

**Files:**
- Modify: `docs/agent-ledger/2026-05-27.md`
- Verify only: full suite + `validate_governance.py`

- [ ] **Step 1: Run the full suite**

Run: `./.venv/bin/python3.14 -m pytest -q`
Expected: PASS, 0 failed.

- [ ] **Step 2: Governance validation**

Run: `./.venv/bin/python3.14 scripts/validate_governance.py`
Expected: PASS.

- [ ] **Step 3: Confirm no decision-surface or model change**

Run: `git diff main --stat -- app/api src/dynasty_genius/models app/services tests/contract/test_market_overlay_pvo.py`
Expected: empty (no endpoint/PVO/model/contract changes).

- [ ] **Step 4: Ruff**

Run: `./.venv/bin/ruff check src/dynasty_genius/mfl_rookie_adp_divergence.py src/dynasty_genius/adapters/mfl_adp_adapter.py scripts/build_mfl_rookie_adp_divergence.py tests/test_mfl_rookie_adp_divergence.py`
Expected: All checks passed.

- [ ] **Step 5: Append ledger entry and commit**

Add a Claude Code build-complete entry to `docs/agent-ledger/2026-05-27.md` (divergence report shipped; read-only over prospect_cards/PVO; artifact-only; xVAR primary; fail-closed join; decision_supported=False; MFL barred from calibration/training; full suite + governance green), then:
```bash
git add docs/agent-ledger/2026-05-27.md
git commit -m "docs(ledger): MFL rookie ADP divergence report (Increment B) build complete"
```

---

## Self-Review

**1. Spec coverage:**
- §2 `fetch_rookie_adp_rows` helper (rows + caveats; fetch() untouched) → Task 1. ✓
- §3 fail-closed identity join (name+position within season; ambiguous; both unmatched) → Task 2. ✓
- §4 `model_rank=xvar_class_rank` primary, `dvs` emitted, `model_rank_unavailable`, `rank_gap`/flags, `aligned_band` in metadata, neutral flags → Task 2. ✓
- §5 components + script + run+latest JSON+MD → Tasks 3, 4. ✓
- §6 artifact shape + coverage block (incl. `decision_supported_true_count==0`, `banned_language_present==[]`) → Tasks 2, 3. ✓
- §7 read-only state contract (cards+PVO byte-identical; writes confined) → Task 4; `decision_supported=False` + banned-language guard → Task 2; no endpoint/PVO/model change → Task 5 Step 3. ✓
- §8 testing intent → Tasks 1–4 + Task 5 full-suite. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code; fixtures are concrete inline dicts.

**3. Type consistency:** `build_mfl_rookie_adp_divergence(adp_rows, prospect_cards, *, season, captured_at, caveats, aligned_band)` and `write_mfl_rookie_adp_divergence_artifacts(divergence, *, output_dir, run_id) -> {run_json, latest_json, run_md, latest_md}` consistent across Tasks 2–4; artifact keys (`matched`/`model_rank_unavailable`/`unmatched_adp`/`unmatched_model`/`ambiguous`/`coverage`) identical between builder (Task 2), writer (Task 3), and script (Task 4); `fetch_rookie_adp_rows` / `_fetch_rows` seam consistent; `_render_md` reads only keys the builder emits.
