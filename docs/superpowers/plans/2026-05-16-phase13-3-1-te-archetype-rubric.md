# Phase 13.3.1 TE Archetype Rubric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Step 0 TE archetype rubric runner that reads private local PFF exports, labels the 2018-2025 drafted TE cohort, and emits a committed redacted artifact keyed only by canonical `player_id`.

**Architecture:** Keep raw PFF data private and untracked under the existing ignored local manifest path. Add a pure rubric module that consumes already-parsed PFF TE rows, then a CLI that joins the private PFF export manifest to the canonical TE eligibility/cohort artifacts and writes a redacted JSON label artifact. The output is diagnostic only: no Engine A/B features, no TE promotion, no DVS, no market data.

**Tech Stack:** Python 3.14, stdlib `csv/json/hashlib/dataclasses`, existing `src/dynasty_genius/adapters/pff_te_export.py`, pytest.

---

## Final Synthesis Decisions

These resolve the Claude/Gemini design differences and are binding for this implementation.

| Decision | Final Choice | Rationale |
|---|---|---|
| Coverage | Proceed at 110/116 | Remaining 6 are explicit PFF coverage gaps, likely FCS/small-school. They are excluded, not imputed. |
| Taxonomy | `archetype` separate from `labeling_status` | Gemini/Codex choice. Prevents operational states from polluting analytical labels. |
| Archetypes | `receiving_leaning`, `blocking_leaning`, `ambiguous`, `null` | Phase 13-approved three-label taxonomy plus null for non-label rows. |
| Statuses | `labeled`, `low_volume`, `invalid_alignment`, `excluded` | Lowercase operational statuses, consistent with revised candidate memo. |
| Coverage status | `pff_alignment_available`, `pff_alignment_missing` | Makes missing PFF rows explicit. |
| Sample guard | `alignment_snap_total < 100` -> `low_volume`, `archetype: null` | Claude and Gemini both converged on 100 alignment snaps. Null is mandatory. |
| Receiving threshold | `detached_rate_from_snaps >= 0.40` | Gemini inclusive boundary; matches standard binning and revised candidate memo. |
| Blocking threshold | `inline_rate_from_snaps >= 0.70` | Keeps block-first label conservative; avoids Claude's looser `0.60` swallowing most non-receiving players. |
| Boundary priority | receiving first, then blocking, then ambiguous | At `detached=0.40`, `inline=0.60`, receiving wins by explicit priority. |
| Sensitivity | Emit redacted 0.40 vs 0.45 distribution summary | Supports later threshold review without changing the primary label. |
| YPRR flag | `elite_efficiency_prior = yprr_computed >= 1.80` | Gemini fixed anchor is stable across classes; use only as context, never label trigger. |
| Optional p75 | Emit `cohort_yprr_p75` in metadata when computable | Preserves Claude's useful relative context without driving labels. |
| Traceability | `source_row_hash = sha256(pff_id + selected_season + content_hash)[:12]` | Provides audit linkage without exposing raw PFF IDs or player names. Missing rows use `null`. |
| Season selection | Prefer `draft_year - 1`, fallback to `draft_year - 2`, no further fallback | Final college season only; no multi-season aggregation. |
| Route caveat | All labels use `alignment_source: "snaps_fallback"` and `threshold_basis: "snap_counts"` | Prevents route-alignment overclaiming. |

## Artifact Contract

Write the committed artifact to:

`app/data/identity/te_archetype_rubric_20260516.json`

Shape:

```json
{
  "metadata": {
    "run_id": "te_archetype_20260516",
    "rubric_version": "0.1.0",
    "generated_at": "2026-05-16T12:30:00Z",
    "eligible_count": 116,
    "coverage_count": 110,
    "missing_count": 6,
    "alignment_source": "snaps_fallback",
    "threshold_basis": "snap_counts",
    "model_features_changed": false,
    "te_promotion_changed": false,
    "market_data_used": false
  },
  "players": {
    "canonical_player_id": {
      "player_id": "canonical_player_id",
      "draft_year": 2024,
      "selected_season": 2023,
      "coverage_status": "pff_alignment_available",
      "labeling_status": "labeled",
      "archetype": "receiving_leaning",
      "source_row_hash": "abc123def456",
      "alignment_snap_total": 342.0,
      "detached_rate_from_snaps": 0.425,
      "inline_rate_from_snaps": 0.575,
      "routes": 210.0,
      "targets": 55.0,
      "receptions": 38.0,
      "yards": 410.0,
      "yprr_computed": 1.9524,
      "tprr_computed": 0.2619,
      "elite_efficiency_prior": true,
      "near_volume_threshold": false,
      "alignment_source": "snaps_fallback",
      "threshold_basis": "snap_counts"
    }
  },
  "sensitivity": {
    "receiving_threshold_0_40": {
      "receiving_leaning": 0,
      "blocking_leaning": 0,
      "ambiguous": 0,
      "low_volume": 0,
      "invalid_alignment": 0,
      "excluded": 6
    },
    "receiving_threshold_0_45": {
      "receiving_leaning": 0,
      "blocking_leaning": 0,
      "ambiguous": 0,
      "low_volume": 0,
      "invalid_alignment": 0,
      "excluded": 6
    },
    "moved_from_receiving_to_ambiguous": 0
  },
  "coverage_gap": {
    "missing_by_draft_year": {
      "2018": 1,
      "2020": 2,
      "2021": 1,
      "2022": 1,
      "2023": 1
    },
    "likely_missing_reason": "PFF collegiate coverage limitation, commonly FCS or small-school gaps.",
    "policy": "Missing PFF alignment rows are excluded from archetype assignment; do not impute or fuzzy-fill."
  }
}
```

Do not include:

- player names;
- raw PFF IDs;
- raw local file paths;
- grade columns;
- market fields.

---

### Task 1: Pure Rubric Module

**Files:**
- Create: `src/dynasty_genius/audit/te_archetype_rubric.py`
- Test: `tests/test_te_archetype_rubric.py`

- [ ] **Step 1: Write failing tests for core label rules**

Create `tests/test_te_archetype_rubric.py` with these tests:

```python
from __future__ import annotations

from src.dynasty_genius.audit.te_archetype_rubric import (
    TEArchetypeInput,
    classify_te_archetype,
)


def test_receiving_leaning_at_inclusive_detached_boundary():
    row = TEArchetypeInput(
        player_id="te_receiving",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash001",
        inline_snaps=60.0,
        slot_snaps=35.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=25.0,
        receptions=18.0,
        yards=190.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "receiving_leaning"
    assert label["labeling_status"] == "labeled"
    assert label["detached_rate_from_snaps"] == 0.4
    assert label["inline_rate_from_snaps"] == 0.6


def test_blocking_leaning_at_inclusive_inline_boundary():
    row = TEArchetypeInput(
        player_id="te_blocking",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash002",
        inline_snaps=70.0,
        slot_snaps=25.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=10.0,
        receptions=8.0,
        yards=70.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "blocking_leaning"
    assert label["labeling_status"] == "labeled"
    assert label["inline_rate_from_snaps"] == 0.7


def test_ambiguous_between_thresholds():
    row = TEArchetypeInput(
        player_id="te_ambiguous",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash003",
        inline_snaps=65.0,
        slot_snaps=30.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=15.0,
        receptions=10.0,
        yards=110.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "ambiguous"
    assert label["labeling_status"] == "labeled"


def test_low_volume_has_null_archetype():
    row = TEArchetypeInput(
        player_id="te_low_volume",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash004",
        inline_snaps=40.0,
        slot_snaps=10.0,
        wide_snaps=0.0,
        routes=20.0,
        targets=5.0,
        receptions=3.0,
        yards=40.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] is None
    assert label["labeling_status"] == "low_volume"


def test_invalid_alignment_has_null_archetype():
    row = TEArchetypeInput(
        player_id="te_invalid",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash005",
        inline_snaps=0.0,
        slot_snaps=0.0,
        wide_snaps=0.0,
        routes=80.0,
        targets=4.0,
        receptions=2.0,
        yards=20.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] is None
    assert label["labeling_status"] == "invalid_alignment"


def test_efficiency_flags_are_context_only():
    row = TEArchetypeInput(
        player_id="te_efficient_blocker",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash006",
        inline_snaps=80.0,
        slot_snaps=15.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=30.0,
        receptions=20.0,
        yards=200.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "blocking_leaning"
    assert label["elite_efficiency_prior"] is True
    assert label["yprr_computed"] == 2.0
    assert label["tprr_computed"] == 0.3
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_rubric.py
```

Expected: collection/import failure for missing `src.dynasty_genius.audit.te_archetype_rubric`.

- [ ] **Step 3: Implement minimal pure rubric module**

Create `src/dynasty_genius/audit/te_archetype_rubric.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RUBRIC_VERSION = "0.1.0"
DEFAULT_RECEIVING_THRESHOLD = 0.40
SENSITIVITY_RECEIVING_THRESHOLD = 0.45
BLOCKING_INLINE_THRESHOLD = 0.70
MIN_ALIGNMENT_SNAPS = 100.0
ELITE_YPRR_ANCHOR = 1.80


@dataclass(frozen=True)
class TEArchetypeInput:
    player_id: str
    draft_year: int
    selected_season: int | None
    source_row_hash: str | None
    inline_snaps: float | None
    slot_snaps: float | None
    wide_snaps: float | None
    routes: float | None
    targets: float | None
    receptions: float | None
    yards: float | None


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _safe_float(value: float | None) -> float:
    return float(value or 0.0)


def classify_te_archetype(
    row: TEArchetypeInput,
    *,
    receiving_threshold: float = DEFAULT_RECEIVING_THRESHOLD,
) -> dict[str, Any]:
    inline = _safe_float(row.inline_snaps)
    slot = _safe_float(row.slot_snaps)
    wide = _safe_float(row.wide_snaps)
    total = inline + slot + wide

    base = {
        "player_id": row.player_id,
        "draft_year": row.draft_year,
        "selected_season": row.selected_season,
        "coverage_status": "pff_alignment_available",
        "source_row_hash": row.source_row_hash,
        "alignment_snap_total": _round(total),
        "routes": _round(row.routes),
        "targets": _round(row.targets),
        "receptions": _round(row.receptions),
        "yards": _round(row.yards),
        "alignment_source": "snaps_fallback",
        "threshold_basis": "snap_counts",
    }

    if total <= 0:
        return {
            **base,
            "labeling_status": "invalid_alignment",
            "archetype": None,
            "detached_rate_from_snaps": None,
            "inline_rate_from_snaps": None,
            "yprr_computed": None,
            "tprr_computed": None,
            "elite_efficiency_prior": False,
            "near_volume_threshold": False,
        }

    detached_rate = (slot + wide) / total
    inline_rate = inline / total
    routes = _safe_float(row.routes)
    targets = _safe_float(row.targets)
    yards = _safe_float(row.yards)
    yprr = yards / routes if routes > 0 else None
    tprr = targets / routes if routes > 0 else None

    if total < MIN_ALIGNMENT_SNAPS:
        status = "low_volume"
        archetype = None
    elif detached_rate >= receiving_threshold:
        status = "labeled"
        archetype = "receiving_leaning"
    elif inline_rate >= BLOCKING_INLINE_THRESHOLD:
        status = "labeled"
        archetype = "blocking_leaning"
    else:
        status = "labeled"
        archetype = "ambiguous"

    return {
        **base,
        "labeling_status": status,
        "archetype": archetype,
        "detached_rate_from_snaps": _round(detached_rate),
        "inline_rate_from_snaps": _round(inline_rate),
        "yprr_computed": _round(yprr),
        "tprr_computed": _round(tprr),
        "elite_efficiency_prior": bool(yprr is not None and yprr >= ELITE_YPRR_ANCHOR),
        "near_volume_threshold": 80.0 <= total <= 120.0,
    }
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_rubric.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/audit/te_archetype_rubric.py tests/test_te_archetype_rubric.py
git commit -m "feat(phase13): add TE archetype rubric classifier"
```

---

### Task 2: Build Cohort Label Artifact Runner

**Files:**
- Create: `scripts/build_te_archetype_rubric.py`
- Modify: `tests/test_te_archetype_rubric.py`

- [ ] **Step 1: Add failing tests for artifact assembly**

Append to `tests/test_te_archetype_rubric.py`:

```python
import json
from pathlib import Path

from scripts.build_te_archetype_rubric import build_te_archetype_artifact


def test_build_artifact_includes_all_players_and_excludes_missing_rows(tmp_path: Path):
    parsed_rows = [
        {
            "player_id": "te_labeled",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2023,
            "source_label": "synthetic_2023",
            "routes": 100.0,
            "inline_snaps": 60.0,
            "slot_snaps": 35.0,
            "wide_snaps": 5.0,
            "targets": 25.0,
            "receptions": 18.0,
            "yards": 190.0,
        }
    ]
    eligible_rows = [
        {"player_id": "te_labeled", "pff_id": "9001", "draft_year": 2024},
        {"player_id": "te_missing", "pff_id": "9002", "draft_year": 2024},
    ]
    file_summaries = [{"source_label": "synthetic_2023", "season": 2023, "content_hash": "contenthash01"}]

    artifact = build_te_archetype_artifact(
        parsed_rows,
        eligible_rows=eligible_rows,
        file_summaries=file_summaries,
        run_id="test_run",
        generated_at="2026-05-16T12:30:00Z",
    )

    assert artifact["metadata"]["eligible_count"] == 2
    assert artifact["metadata"]["coverage_count"] == 1
    assert artifact["metadata"]["missing_count"] == 1
    assert set(artifact["players"]) == {"te_labeled", "te_missing"}
    assert artifact["players"]["te_labeled"]["archetype"] == "receiving_leaning"
    assert artifact["players"]["te_labeled"]["source_row_hash"]
    assert artifact["players"]["te_missing"]["archetype"] is None
    assert artifact["players"]["te_missing"]["coverage_status"] == "pff_alignment_missing"
    assert artifact["players"]["te_missing"]["labeling_status"] == "excluded"
    rendered = json.dumps(artifact)
    assert "9001" not in rendered
    assert "9002" not in rendered


def test_build_artifact_selects_final_college_season_before_fallback():
    parsed_rows = [
        {
            "player_id": "te_multi",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2022,
            "source_label": "synthetic_2022",
            "routes": 100.0,
            "inline_snaps": 90.0,
            "slot_snaps": 5.0,
            "wide_snaps": 5.0,
            "targets": 10.0,
            "receptions": 7.0,
            "yards": 80.0,
        },
        {
            "player_id": "te_multi",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2023,
            "source_label": "synthetic_2023",
            "routes": 100.0,
            "inline_snaps": 50.0,
            "slot_snaps": 40.0,
            "wide_snaps": 10.0,
            "targets": 30.0,
            "receptions": 20.0,
            "yards": 220.0,
        },
    ]
    eligible_rows = [{"player_id": "te_multi", "pff_id": "9001", "draft_year": 2024}]
    file_summaries = [
        {"source_label": "synthetic_2022", "season": 2022, "content_hash": "hash2022"},
        {"source_label": "synthetic_2023", "season": 2023, "content_hash": "hash2023"},
    ]

    artifact = build_te_archetype_artifact(
        parsed_rows,
        eligible_rows=eligible_rows,
        file_summaries=file_summaries,
        run_id="test_run",
        generated_at="2026-05-16T12:30:00Z",
    )

    row = artifact["players"]["te_multi"]
    assert row["selected_season"] == 2023
    assert row["archetype"] == "receiving_leaning"
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_rubric.py
```

Expected: failure importing missing `scripts.build_te_archetype_rubric`.

- [ ] **Step 3: Implement artifact builder and CLI**

Create `scripts/build_te_archetype_rubric.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_pff_te_export_report import (  # noqa: E402
    _load_cohort_draft_years,
    _load_eligible_rows,
    _load_manifest,
    _merge_cohort_draft_years,
)
from src.dynasty_genius.adapters.pff_te_export import parse_pff_te_export  # noqa: E402
from src.dynasty_genius.audit.te_archetype_rubric import (  # noqa: E402
    DEFAULT_RECEIVING_THRESHOLD,
    RUBRIC_VERSION,
    SENSITIVITY_RECEIVING_THRESHOLD,
    TEArchetypeInput,
    classify_te_archetype,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_id(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def _source_row_hash(pff_id: str | None, season: int | None, content_hash: str | None) -> str | None:
    if not pff_id or season is None or not content_hash:
        return None
    return hashlib.sha256(f"{pff_id}|{season}|{content_hash}".encode("utf-8")).hexdigest()[:12]


def _content_hash_by_source_label(file_summaries: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(row["source_label"]): str(row["content_hash"])
        for row in file_summaries
        if row.get("source_label") and row.get("content_hash")
    }


def _select_final_season(rows: list[dict[str, Any]], draft_year: int) -> dict[str, Any] | None:
    by_season = {int(row["season"]): row for row in rows if row.get("season") is not None}
    for season in (draft_year - 1, draft_year - 2):
        if season in by_season:
            return by_season[season]
    return None


def _excluded_row(player_id: str, draft_year: int | None) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "draft_year": draft_year,
        "selected_season": None,
        "coverage_status": "pff_alignment_missing",
        "labeling_status": "excluded",
        "archetype": None,
        "source_row_hash": None,
        "alignment_snap_total": None,
        "detached_rate_from_snaps": None,
        "inline_rate_from_snaps": None,
        "routes": None,
        "targets": None,
        "receptions": None,
        "yards": None,
        "yprr_computed": None,
        "tprr_computed": None,
        "elite_efficiency_prior": False,
        "near_volume_threshold": False,
        "alignment_source": None,
        "threshold_basis": None,
    }


def _sensitivity_counts(players: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {
        "receiving_leaning": 0,
        "blocking_leaning": 0,
        "ambiguous": 0,
        "low_volume": 0,
        "invalid_alignment": 0,
        "excluded": 0,
    }
    for row in players.values():
        status = row["labeling_status"]
        if status != "labeled":
            counts[status] += 1
        else:
            counts[row["archetype"]] += 1
    return counts


def build_te_archetype_artifact(
    parsed_rows: list[dict[str, Any]],
    *,
    eligible_rows: list[dict[str, Any]],
    file_summaries: list[dict[str, Any]],
    run_id: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _utc_timestamp()
    content_hash_by_source = _content_hash_by_source_label(file_summaries)
    by_player: dict[str, list[dict[str, Any]]] = {}
    for row in parsed_rows:
        by_player.setdefault(str(row["player_id"]), []).append(row)

    players_040: dict[str, dict[str, Any]] = {}
    players_045: dict[str, dict[str, Any]] = {}
    missing_by_draft_year: dict[str, int] = {}

    for eligible in sorted(eligible_rows, key=lambda r: str(r.get("player_id") or "")):
        player_id = str(eligible["player_id"])
        draft_year = int(eligible["draft_year"]) if eligible.get("draft_year") is not None else None
        selected = _select_final_season(by_player.get(player_id, []), draft_year) if draft_year else None
        if selected is None:
            players_040[player_id] = _excluded_row(player_id, draft_year)
            players_045[player_id] = _excluded_row(player_id, draft_year)
            missing_by_draft_year[str(draft_year)] = missing_by_draft_year.get(str(draft_year), 0) + 1
            continue

        source_hash = _source_row_hash(
            _norm_id(selected.get("pff_id")),
            int(selected["season"]),
            content_hash_by_source.get(str(selected.get("source_label"))),
        )
        input_row = TEArchetypeInput(
            player_id=player_id,
            draft_year=draft_year,
            selected_season=int(selected["season"]),
            source_row_hash=source_hash,
            inline_snaps=selected.get("inline_snaps"),
            slot_snaps=selected.get("slot_snaps"),
            wide_snaps=selected.get("wide_snaps"),
            routes=selected.get("routes"),
            targets=selected.get("targets"),
            receptions=selected.get("receptions"),
            yards=selected.get("yards"),
        )
        players_040[player_id] = classify_te_archetype(
            input_row,
            receiving_threshold=DEFAULT_RECEIVING_THRESHOLD,
        )
        players_045[player_id] = classify_te_archetype(
            input_row,
            receiving_threshold=SENSITIVITY_RECEIVING_THRESHOLD,
        )

    moved = sum(
        1
        for player_id, row in players_040.items()
        if row.get("archetype") == "receiving_leaning"
        and players_045[player_id].get("archetype") == "ambiguous"
    )
    yprr_values = [
        row["yprr_computed"]
        for row in players_040.values()
        if row.get("yprr_computed") is not None and row.get("labeling_status") == "labeled"
    ]
    yprr_values = sorted(yprr_values)
    yprr_p75 = None
    if yprr_values:
        yprr_p75 = yprr_values[int((len(yprr_values) - 1) * 0.75)]

    coverage_count = sum(1 for row in players_040.values() if row["coverage_status"] == "pff_alignment_available")
    return {
        "metadata": {
            "run_id": run_id,
            "rubric_version": RUBRIC_VERSION,
            "generated_at": generated_at,
            "eligible_count": len(eligible_rows),
            "coverage_count": coverage_count,
            "missing_count": len(eligible_rows) - coverage_count,
            "alignment_source": "snaps_fallback",
            "threshold_basis": "snap_counts",
            "cohort_yprr_p75": yprr_p75,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
        },
        "players": players_040,
        "sensitivity": {
            "receiving_threshold_0_40": _sensitivity_counts(players_040),
            "receiving_threshold_0_45": _sensitivity_counts(players_045),
            "moved_from_receiving_to_ambiguous": moved,
        },
        "coverage_gap": {
            "missing_by_draft_year": dict(sorted(missing_by_draft_year.items())),
            "likely_missing_reason": "PFF collegiate coverage limitation, commonly FCS or small-school gaps.",
            "policy": "Missing PFF alignment rows are excluded from archetype assignment; do not impute or fuzzy-fill.",
        },
    }


def _parse_private_exports(manifest_path: Path, eligible_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = _load_manifest(manifest_path)
    by_pff = {
        str(row["pff_id"]): row
        for row in eligible_rows
        if row.get("pff_id") and row.get("player_id")
    }
    parsed_rows: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []
    for entry in entries:
        parsed = parse_pff_te_export(
            entry.path,
            season=entry.season,
            eligible_by_pff_id=by_pff,
            source_label=entry.label,
        )
        parsed_rows.extend(parsed.rows)
        file_summaries.append(parsed.file_summary)
    return parsed_rows, file_summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 13.3.1 TE archetype rubric artifact.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_archetype_20260516")
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    eligible_rows = _merge_cohort_draft_years(
        _load_eligible_rows(args.eligible_manifest),
        args.cohort,
    )
    parsed_rows, file_summaries = _parse_private_exports(args.manifest, eligible_rows)
    artifact = build_te_archetype_artifact(
        parsed_rows,
        eligible_rows=eligible_rows,
        file_summaries=file_summaries,
        run_id=args.run_id,
        generated_at=args.generated_at,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metadata = artifact["metadata"]
    print(
        f"TE archetype rubric written: {args.out} "
        f"coverage={metadata['coverage_count']}/{metadata['eligible_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_rubric.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_te_archetype_rubric.py tests/test_te_archetype_rubric.py
git commit -m "feat(phase13): build TE archetype artifact runner"
```

---

### Task 3: Generate Real Redacted Artifact and Add Contract Tests

**Files:**
- Modify: `tests/test_te_archetype_rubric.py`
- Create: `app/data/identity/te_archetype_rubric_20260516.json`

- [ ] **Step 1: Add artifact contract tests**

Append:

```python
def test_committed_te_archetype_artifact_contract():
    path = Path("app/data/identity/te_archetype_rubric_20260516.json")
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert artifact["metadata"]["eligible_count"] == 116
    assert len(artifact["players"]) == 116
    assert artifact["metadata"]["coverage_count"] == 110
    assert artifact["metadata"]["missing_count"] == 6
    assert artifact["coverage_gap"]["missing_by_draft_year"] == {
        "2018": 1,
        "2020": 2,
        "2021": 1,
        "2022": 1,
        "2023": 1,
    }
    assert artifact["metadata"]["model_features_changed"] is False
    assert artifact["metadata"]["te_promotion_changed"] is False
    assert artifact["metadata"]["market_data_used"] is False

    rendered = json.dumps(artifact).lower()
    assert "pff_id" not in rendered
    assert "grades_" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered

    statuses = {row["labeling_status"] for row in artifact["players"].values()}
    assert statuses <= {"labeled", "low_volume", "invalid_alignment", "excluded"}
    excluded = [
        row for row in artifact["players"].values()
        if row["labeling_status"] == "excluded"
    ]
    assert len(excluded) == 6
    assert all(row["archetype"] is None for row in excluded)
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_rubric.py::test_committed_te_archetype_artifact_contract
```

Expected: fails because `app/data/identity/te_archetype_rubric_20260516.json` does not exist yet.

- [ ] **Step 3: Generate artifact from private ignored manifest**

Run:

```bash
.venv/bin/python3.14 scripts/build_te_archetype_rubric.py \
  --manifest app/data/pff_exports/phase13_te_v10_plus_manifest.json \
  --eligible-manifest app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json \
  --cohort app/data/identity/_runs/te_cohort_2018_2025.json \
  --out app/data/identity/te_archetype_rubric_20260516.json \
  --run-id te_archetype_20260516
```

Expected output:

```text
TE archetype rubric written: app/data/identity/te_archetype_rubric_20260516.json coverage=110/116
```

- [ ] **Step 4: Run contract and focused tests**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_rubric.py tests/test_pff_te_export_parser.py tests/test_build_pff_te_export_report.py
```

Expected: all tests pass.

- [ ] **Step 5: Run redaction and JSON checks**

Run:

```bash
python -m json.tool app/data/identity/te_archetype_rubric_20260516.json >/dev/null
rg -n "David|Hayden|Brock|/Users/davidleess|Downloads|pff_id|grades_" app/data/identity/te_archetype_rubric_20260516.json || true
```

Expected: JSON command exits 0; `rg` prints no matches.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_te_archetype_rubric.py src/dynasty_genius/audit/te_archetype_rubric.py tests/test_te_archetype_rubric.py app/data/identity/te_archetype_rubric_20260516.json
git commit -m "feat(phase13): emit TE archetype rubric artifact"
```

---

### Task 4: Governance Updates and Full Verification

**Files:**
- Modify: `AGENT_SYNC.md`
- Modify: `docs/agent-ledger/2026-05-16.md`

- [ ] **Step 1: Update AGENT_SYNC**

In `AGENT_SYNC.md`, update Phase 13.3.1 from `READY_WITH_CAVEATS` to `COMPLETE` after artifact generation. Include:

```md
- Task 13.3.1 COMPLETE: TE Archetype Rubric Step 0 artifact generated at `app/data/identity/te_archetype_rubric_20260516.json`.
    - Artifact accounts for all 116 drafted TEs: 110 with PFF alignment coverage, 6 excluded as PFF coverage gaps.
    - Labels are snap-alignment based (`snaps_fallback`), not route-alignment. PFF remains context_signal only.
    - No raw PFF IDs, names, local paths, PFF grades, Engine A/B feature changes, model training, TE promotion, DVS, or market data.
```

- [ ] **Step 2: Update daily ledger**

Append to `docs/agent-ledger/2026-05-16.md`:

```md
## HH:MM ET - Agent Name

- Task: Implement Phase 13.3.1 TE Archetype Rubric Step 0 artifact.
- Governance read: docs/governance/02-agent-operating-loop.md, docs/governance/00-product-constitution.md, docs/governance/01-north-star-architecture.md, AGENT_SYNC.md, daily ledger, Phase 13 final spec, Claude/Gemini rubric memos.
- Active phase / surface: Phase 13.3 TE Remodel Step 0.
- Intended or completed write scope: TE rubric classifier, build script, tests, redacted artifact, AGENT_SYNC, daily ledger.
- Files changed: list exact files.
- Tests / checks: include focused tests, full suite, JSON validation, redaction scan.
- Product alignment: Step 0 artifact-only. PFF context_signal only. No Engine A/B feature changes, model training, TE promotion, DVS, or market data.
- Drift risks: Snap-alignment fallback, not route-alignment; remaining 6 PFF coverage gaps excluded.
- Handoff / next step: Human review of label distribution and sensitivity summary.
```

- [ ] **Step 3: Run focused governance checks**

Run:

```bash
.venv/bin/python3.14 -m pytest -q \
  tests/test_te_archetype_rubric.py \
  tests/test_pff_te_export_parser.py \
  tests/test_build_pff_te_export_report.py \
  tests/test_manual_export_adapter.py \
  tests/test_source_registry.py \
  tests/test_identity_materialization_gate.py
```

Expected: all pass; existing skipped tests may remain skipped.

- [ ] **Step 4: Run full suite**

Run:

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: all tests pass. Record exact pass/skip/warning counts in ledger and final response.

- [ ] **Step 5: Final redaction check**

Run:

```bash
rg -n "David|Hayden|Brock|/Users/davidleess|Downloads|pff_id|grades_" app/data/identity/te_archetype_rubric_20260516.json || true
git status --short --branch --ignored=matching app/data/pff_exports
```

Expected: redaction scan prints no matches. Git status shows ignored `app/data/pff_exports/` only, plus intended tracked changes before commit.

- [ ] **Step 6: Commit and push**

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-05-16.md app/data/identity/te_archetype_rubric_20260516.json src/dynasty_genius/audit/te_archetype_rubric.py scripts/build_te_archetype_rubric.py tests/test_te_archetype_rubric.py
git commit -m "feat(phase13): complete TE archetype rubric artifact"
git push
```

---

## Self-Review

Spec coverage:

- Identity and coverage gates preserved: uses canonical eligibility manifest and all 116 players.
- PFF privacy preserved: raw CSVs and local manifest remain ignored; committed artifact has no names, PFF IDs, or local paths.
- Taxonomy resolved: analytical `archetype` separate from operational `labeling_status`.
- Missing 6 handled: explicit exclusions, no imputation or fuzzy fill.
- Snap fallback disclosed: row-level `alignment_source` and `threshold_basis`.
- Sensitivity required: 0.40 vs 0.45 summary emitted.
- Scope preserved: no Engine A/B, TE promotion, DVS, or market data.

No placeholders remain. Function names and paths are consistent across tasks.
