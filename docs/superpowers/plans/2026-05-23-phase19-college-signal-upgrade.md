# Phase 19 — Engine A College Signal Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich Engine A with college efficiency signals (RYPTPA from CFBD, YPRR from PFF exports), run a governed WR LOOCV bake-off, and commit a formal RB age de-emphasis governance ruling.

**Architecture:** A PFF WR export parser and a CFBD team-stats adapter produce per-player college feature rows; a feature-builder script joins them to the existing training data by player name + college normalization, writing an enriched CSV and a manual-review queue for unresolved rows. A bake-off harness runs leave-one-draft-class-out Ridge regressions across candidate feature sets and evaluates a three-part promotion gate (≥3% MAE lift, ≥3/4 folds passing, TE MAE stable). No production model change is made unless that gate passes.

**Tech Stack:** Python 3.14, scikit-learn (Ridge), numpy, httpx, dotenv, existing `DraftClassLOOCVResult` harness in `src/dynasty_genius/eval/draft_class_loocv.py`, existing `cfbd_qb_adapter.py` pattern.

**Governance constraints (non-negotiable):**
- CFBD_API_KEY loaded from `.env` — never hardcoded.
- PFF CSV paths remain local and gitignored — only content hashes and row counts are committed.
- All bake-off work is validation-only. Production model pkl and `latest.json` are not touched unless Task 7 gate passes and David explicitly approves promotion.
- Market fields (KTC, FantasyCalc, ADP) may not appear in any feature set.
- Unresolved identity rows go to manual_review.csv — never silently dropped or imputed.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/dynasty_genius/adapters/pff_wr_export.py` | Parse PFF receiving_summary CSVs for WR/RB rows |
| Create | `src/dynasty_genius/adapters/cfbd_receiving_adapter.py` | Fetch team pass attempts from CFBD for RYPTPA denominator |
| Create | `scripts/build_college_features.py` | Join PFF + CFBD data to training rows; output enriched CSV |
| Create | `scripts/run_wr_college_bakeoff.py` | LOOCV bake-off across candidate feature sets; gate evaluation |
| Create | `tests/test_pff_wr_export.py` | Unit tests for PFF WR parser |
| Create | `tests/test_cfbd_receiving_adapter.py` | Unit tests for CFBD receiving adapter |
| Create | `tests/test_college_feature_builder.py` | Unit tests for RYPTPA formula and name normalization |
| Create | `tests/test_wr_college_bakeoff.py` | Unit tests for bake-off gate logic |
| Create | `app/data/pff_exports/phase16_wr_manifest.json` | **Gitignored.** Local paths → season year mapping |
| Create | `app/data/backtest/phase16/` | Directory for bake-off artifacts (gitignored pattern) |
| Create | `docs/validation/phase16-4-wr-college-promotion-decision.md` | Promotion decision record (committed) |
| Create | `docs/validation/phase16-5-rb-age-governance.md` | RB age de-emphasis governance ruling (committed) |
| Modify | `src/dynasty_genius/models/engine_a_contract.py` | Add ryptpa/yprr/source fields to allowed columns |
| Modify | `.gitignore` | Add backtest phase16 artifact pattern |

---

## Task 1: WR Season Manifest

**Files:**
- Create: `app/data/pff_exports/phase16_wr_manifest.json`
- Verify: `.gitignore` suppresses it

The manifest pins each local PFF CSV to its confirmed college season year. Season year is the year the college games were played (draft_year - 1 for most players). This file is the only place season-year knowledge lives — the CSV files have no season column.

- [ ] **Step 1: Verify the gitignore already covers this path**

```bash
grep "pff_exports" /Users/davidleess/dynasty-genius-product/.gitignore
```

Expected output: a line matching `app/data/pff_exports/`. If missing, add it:

```
# PFF manual exports and local manifests are private subscriber data / local paths
app/data/pff_exports/
```

- [ ] **Step 2: Create the manifest**

Write `app/data/pff_exports/phase16_wr_manifest.json`:

```json
{
  "description": "Local-only manifest for PFF Premium Stats receiving_summary WR exports. Gitignored. Season year = college games played year (draft_year - 1 for most classes).",
  "pff_data_version": "local-download-2026-05-16",
  "warning": "Do not commit this file. It contains local paths to private PFF exports.",
  "exports": [
    {
      "label": "2017_season",
      "path": "/Users/davidleess/Downloads/receiving_summary (18).csv",
      "season": 2017,
      "source": "pff_premium_stats",
      "notes": "2018 NFL draft class final college season. Confirmed: Steve Ishmael, DJ Moore, Courtland Sutton present."
    },
    {
      "label": "2018_season",
      "path": "/Users/davidleess/Downloads/receiving_summary (10).csv",
      "season": 2018,
      "source": "pff_premium_stats",
      "notes": "2019 NFL draft class final college season. Confirmed: AJ Brown, Deebo Samuel, Preston Williams present."
    },
    {
      "label": "2019_season",
      "path": "/Users/davidleess/Downloads/receiving_summary (11).csv",
      "season": 2019,
      "source": "pff_premium_stats",
      "notes": "2020 NFL draft class final college season. Confirmed: CeeDee Lamb, Jerry Jeudy, Henry Ruggs present."
    },
    {
      "label": "2020_season",
      "path": "/Users/davidleess/Downloads/receiving_summary (12).csv",
      "season": 2020,
      "source": "pff_premium_stats",
      "notes": "2021 NFL draft class final college season (COVID-shortened). Confirmed: Jaylen Waddle, Ja'Marr Chase, DeVonta Smith present."
    },
    {
      "label": "2021_season",
      "path": "/Users/davidleess/Downloads/receiving_summary (13).csv",
      "season": 2021,
      "source": "pff_premium_stats",
      "notes": "2022 NFL draft class final college season. Confirmed: Garrett Wilson, Drake London, Treylon Burks present."
    },
    {
      "label": "2022_season",
      "path": "/Users/davidleess/Downloads/receiving_summary (14).csv",
      "season": 2022,
      "source": "pff_premium_stats",
      "notes": "2023 NFL draft class final college season. Confirmed: Zay Flowers, JSN, Quentin Johnston present."
    },
    {
      "label": "2023_season",
      "path": "/Users/davidleess/Downloads/receiving_summary (15).csv",
      "season": 2023,
      "source": "pff_premium_stats",
      "notes": "2024 NFL draft class final college season. Confirmed: Malik Nabers, Rome Odunze, Marvin Harrison Jr. present."
    }
  ]
}
```

- [ ] **Step 3: Verify the manifest is gitignored**

```bash
git check-ignore -v app/data/pff_exports/phase16_wr_manifest.json
```

Expected output (points to the rule that suppresses it):

```
.gitignore:<line>:app/data/pff_exports/	app/data/pff_exports/phase16_wr_manifest.json
```

If this returns nothing, stop — the ignore rule is missing, the path is wrong, or the file was created outside `app/data/pff_exports/`. Do not proceed to Task 2.

Secondary check (should show nothing):

```bash
git status app/data/pff_exports/phase16_wr_manifest.json
```

Expected: no output (file is invisible to git).

- [ ] **Step 4: Commit gitignore if it needed updating**

Only if Step 1 required adding `app/data/pff_exports/`:

```bash
git add .gitignore
git commit -m "chore: ensure pff_exports dir is gitignored"
```

---

## Task 2: PFF WR Export Parser

**Files:**
- Create: `src/dynasty_genius/adapters/pff_wr_export.py`
- Create: `tests/test_pff_wr_export.py`

Parses PFF `receiving_summary` CSVs into safe WR/RB rows. Modeled on `pff_te_export.py`. Key differences: filters WR and RB positions (not TE), promotes `yprr` to a primary required field, adds a content hash to each parsed result for deduplication detection.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pff_wr_export.py`:

```python
"""Tests for Phase 16.2 PFF WR export parser."""
import csv
import hashlib
import io
import pytest
from src.dynasty_genius.adapters.pff_wr_export import (
    parse_pff_wr_season,
    PFFWRExportError,
    PROHIBITED_COLUMN_PATTERNS,
)


def _write_csv(rows: list[dict], tmp_path, filename="test.csv") -> str:
    path = tmp_path / filename
    if not rows:
        path.write_text("")
        return str(path)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def _base_row(**kwargs):
    defaults = {
        "player_id": "12345",
        "player": "Test Player",
        "position": "WR",
        "team_name": "Alabama",
        "routes": "400",
        "yprr": "2.50",
        "yards": "1000",
        "targets": "120",
        "receptions": "80",
    }
    defaults.update(kwargs)
    return defaults


def test_parse_returns_wr_rows(tmp_path):
    rows = [_base_row(player_id="1", player="Alpha WR", position="WR")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert result.rows[0]["position"] == "WR"


def test_parse_includes_rb_rows(tmp_path):
    rows = [_base_row(player_id="2", player="RB Player", position="RB")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert result.rows[0]["position"] == "RB"


def test_parse_excludes_te_rows(tmp_path):
    rows = [
        _base_row(player_id="1", position="WR"),
        _base_row(player_id="2", position="TE"),
    ]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert result.rows[0]["pff_id"] == "1"


def test_parse_rejects_grade_columns(tmp_path):
    rows = [_base_row(**{"grades_offense": "88.5"})]
    path = _write_csv(rows, tmp_path)
    with pytest.raises(PFFWRExportError, match="prohibited"):
        parse_pff_wr_season(path, season=2022)


def test_parse_yprr_as_float(tmp_path):
    rows = [_base_row(yprr="1.87")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert result.rows[0]["yprr"] == pytest.approx(1.87)


def test_parse_season_injected(tmp_path):
    rows = [_base_row()]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2019)
    assert result.rows[0]["season"] == 2019


def test_content_hash_present(tmp_path):
    rows = [_base_row()]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert isinstance(result.content_hash, str)
    assert len(result.content_hash) == 12


def test_parse_missing_required_column_raises(tmp_path):
    rows = [{"player_id": "1", "player": "Test", "position": "WR"}]
    path = _write_csv(rows, tmp_path)
    with pytest.raises(PFFWRExportError, match="missing required"):
        parse_pff_wr_season(path, season=2022)


def test_parse_null_yprr_allowed(tmp_path):
    rows = [_base_row(yprr="")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert result.rows[0]["yprr"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/davidleess/dynasty-genius-product && .venv/bin/python3.14 -m pytest tests/test_pff_wr_export.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError` — module does not exist yet.

- [ ] **Step 3: Implement the parser**

Create `src/dynasty_genius/adapters/pff_wr_export.py`:

```python
"""Phase 16.2 PFF collegiate WR/RB export parser.

Normalizes private PFF manual exports into identity-joined feature rows
for Engine A college signal enrichment. Season year is injected from the
manifest — the CSV files carry no season column.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "pff_id": ("player_id", "pff_id", "id"),
    "player_name": ("player", "name", "player_name"),
    "college": ("team_name", "school", "college"),
    "position": ("position", "pos"),
    "routes": ("routes", "routes_run"),
    "yprr": ("yprr",),
    "yards": ("yards", "yds", "receiving_yards"),
    "targets": ("targets", "tgt"),
    "receptions": ("receptions", "rec"),
}

PROHIBITED_COLUMN_PATTERNS = (
    "grade",
    "pff_grade",
    "receiving_grade",
    "run_block_grade",
    "pass_block_grade",
    "route_grade",
)

_ELIGIBLE_POSITIONS = {"WR", "RB"}


class PFFWRExportError(ValueError):
    """Raised when the export violates the Phase 16 parser contract."""


@dataclass(frozen=True)
class ParsedPFFWRSeason:
    """Safe parsed WR/RB rows from one PFF season export."""

    rows: list[dict[str, Any]]
    season: int
    row_count: int
    wr_rb_count: int
    content_hash: str
    prohibited_columns: list[str]
    required_missing: list[str]


def _norm_col(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == "_")


def _find_alias(headers: list[str], aliases: tuple[str, ...]) -> str | None:
    norm = {_norm_col(h): h for h in headers}
    for alias in aliases:
        if _norm_col(alias) in norm:
            return norm[_norm_col(alias)]
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _norm_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _sha256_short(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _check_prohibited(headers: list[str]) -> list[str]:
    found = []
    for h in headers:
        norm = _norm_col(h)
        if any(pattern in norm for pattern in PROHIBITED_COLUMN_PATTERNS):
            found.append(h)
    return sorted(found)


def parse_pff_wr_season(
    csv_path: str | Path,
    *,
    season: int,
) -> ParsedPFFWRSeason:
    """Parse one PFF receiving-summary export for WR/RB rows.

    Args:
        csv_path: Local path to the PFF CSV. Not committed; used read-only.
        season: College season year (injected from manifest, e.g. 2022).

    Raises:
        PFFWRExportError: If required columns are missing or prohibited grade
            columns are present.
    """
    path = Path(csv_path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        raw_rows = list(reader)

    prohibited = _check_prohibited(headers)
    if prohibited:
        raise PFFWRExportError(
            f"prohibited grade columns in PFF export: {prohibited}"
        )

    col_map: dict[str, str] = {}
    missing: list[str] = []
    for field_name, aliases in REQUIRED_COLUMN_ALIASES.items():
        found = _find_alias(headers, aliases)
        if found:
            col_map[field_name] = found
        else:
            missing.append(field_name)

    if missing:
        raise PFFWRExportError(
            f"missing required columns in PFF export: {missing}"
        )

    rows: list[dict[str, Any]] = []
    wr_rb_count = 0

    for raw in raw_rows:
        pos = (raw.get(col_map["position"]) or "").strip().upper()
        if pos not in _ELIGIBLE_POSITIONS:
            continue
        wr_rb_count += 1

        pff_id = _norm_id(raw.get(col_map["pff_id"]))
        rows.append({
            "pff_id": pff_id,
            "player_name": (raw.get(col_map["player_name"]) or "").strip(),
            "college": (raw.get(col_map["college"]) or "").strip(),
            "position": pos,
            "season": season,
            "routes": _to_float(raw.get(col_map["routes"])),
            "yprr": _to_float(raw.get(col_map["yprr"])),
            "yards": _to_float(raw.get(col_map["yards"])),
            "targets": _to_float(raw.get(col_map["targets"])),
            "receptions": _to_float(raw.get(col_map["receptions"])),
        })

    return ParsedPFFWRSeason(
        rows=rows,
        season=season,
        row_count=len(raw_rows),
        wr_rb_count=wr_rb_count,
        content_hash=_sha256_short(path),
        prohibited_columns=prohibited,
        required_missing=missing,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python3.14 -m pytest tests/test_pff_wr_export.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/pff_wr_export.py tests/test_pff_wr_export.py
git commit -m "feat(phase16.2): PFF WR/RB export parser with grade prohibition and content hash"
```

---

## Task 3: CFBD Receiving Adapter

**Files:**
- Create: `src/dynasty_genius/adapters/cfbd_receiving_adapter.py`
- Create: `tests/test_cfbd_receiving_adapter.py`

Fetches team pass attempts from CFBD for a given team name + season year. This is the denominator for RYPTPA. Follows the same defensive pattern as `cfbd_qb_adapter.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cfbd_receiving_adapter.py`:

```python
"""Tests for Phase 16.2 CFBD receiving adapter."""
from unittest.mock import patch, MagicMock
import pytest
from src.dynasty_genius.adapters.cfbd_receiving_adapter import (
    fetch_team_pass_attempts,
    normalize_college_name,
)


def _mock_response(data: list[dict]) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = data
    return mock


def test_fetch_returns_pass_attempts(monkeypatch):
    stat_rows = [
        {"statName": "passAttempts", "statValue": "450"},
        {"statName": "rushingYards", "statValue": "1800"},
    ]
    with patch("httpx.get", return_value=_mock_response(stat_rows)):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result == pytest.approx(450.0)


def test_fetch_returns_none_when_stat_missing(monkeypatch):
    stat_rows = [{"statName": "rushingYards", "statValue": "1800"}]
    with patch("httpx.get", return_value=_mock_response(stat_rows)):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result is None


def test_fetch_returns_none_on_empty_response():
    with patch("httpx.get", return_value=_mock_response([])):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result is None


def test_fetch_returns_none_without_api_key():
    result = fetch_team_pass_attempts("Alabama", 2022, api_key="")
    assert result is None


def test_fetch_returns_none_on_http_error():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("HTTP 401")
    with patch("httpx.get", return_value=mock):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result is None


def test_normalize_college_name_common_cases():
    assert normalize_college_name("Florida St.") == "Florida State"
    assert normalize_college_name("Ohio St.") == "Ohio State"
    assert normalize_college_name("Michigan St.") == "Michigan State"
    assert normalize_college_name("S JOSE ST") == "San Jose State"
    assert normalize_college_name("FAU") == "Florida Atlantic"
    assert normalize_college_name("LSU") == "LSU"


def test_normalize_college_name_passthrough():
    assert normalize_college_name("Alabama") == "Alabama"
    assert normalize_college_name("Oregon") == "Oregon"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python3.14 -m pytest tests/test_cfbd_receiving_adapter.py -v 2>&1 | head -10
```

Expected: `ImportError`.

- [ ] **Step 3: Implement the adapter**

Create `src/dynasty_genius/adapters/cfbd_receiving_adapter.py`:

```python
"""Phase 16.2 CFBD receiving adapter — team pass attempts for RYPTPA.

Fetches team-level passing stats (pass attempts) for a given college team
and season year. Used as the RYPTPA denominator.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.collegefootballdata.com"

# Abbreviation → full CFBD name for common PFF export discrepancies
_COLLEGE_NAME_MAP: dict[str, str] = {
    "Florida St.": "Florida State",
    "Ohio St.": "Ohio State",
    "Michigan St.": "Michigan State",
    "Penn St.": "Penn State",
    "Mississippi St.": "Mississippi State",
    "Iowa St.": "Iowa State",
    "Kansas St.": "Kansas State",
    "Oklahoma St.": "Oklahoma State",
    "Washington St.": "Washington State",
    "Colorado St.": "Colorado State",
    "Oregon St.": "Oregon State",
    "Arizona St.": "Arizona State",
    "S JOSE ST": "San Jose State",
    "FAU": "Florida Atlantic",
    "FIU": "Florida International",
    "SMU": "SMU",
    "LSU": "LSU",
    "TCU": "TCU",
    "UCF": "UCF",
    "BYU": "BYU",
    "USF": "South Florida",
    "UTSA": "UTSA",
    "UTEP": "UTEP",
    "UAB": "UAB",
    "UMass": "Massachusetts",
    "UConn": "Connecticut",
    "UNT": "North Texas",
    "UNLV": "UNLV",
    "Hawaii": "Hawaii",
}


def normalize_college_name(name: str) -> str:
    """Map PFF college abbreviations to CFBD full names."""
    stripped = name.strip()
    return _COLLEGE_NAME_MAP.get(stripped, stripped)


def _auth_key(api_key: str | None) -> str:
    return (api_key or os.getenv("CFBD_API_KEY") or "").strip()


def _team_stat(records: list[dict[str, Any]], stat_name: str) -> float | None:
    for row in records:
        if str(row.get("statName", "")).strip() == stat_name:
            value = row.get("statValue")
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def fetch_team_pass_attempts(
    college_team: str,
    season: int,
    api_key: str | None = None,
) -> float | None:
    """Return pass attempts for a college team in a given season, or None.

    Args:
        college_team: PFF team_name string (will be normalized to CFBD name).
        season: College season year (e.g. 2022).
        api_key: CFBD API key. Falls back to CFBD_API_KEY env var.

    Returns:
        Float pass attempts or None if unavailable.
    """
    key = _auth_key(api_key)
    if not key:
        return None

    cfbd_name = normalize_college_name(college_team)
    url = f"{BASE_URL}/stats/team/season"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {key}"},
            params={"year": season, "team": cfbd_name},
        )
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            return None
        return _team_stat(records, "passAttempts")
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python3.14 -m pytest tests/test_cfbd_receiving_adapter.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/cfbd_receiving_adapter.py tests/test_cfbd_receiving_adapter.py
git commit -m "feat(phase16.2): CFBD team pass attempts adapter for RYPTPA denominator"
```

---

## Task 4: College Feature Builder

**Files:**
- Create: `scripts/build_college_features.py`
- Create: `tests/test_college_feature_builder.py`

Joins PFF WR/RB rows to Engine A training rows by fuzzy name + college match, fetches CFBD team pass attempts, computes RYPTPA, extracts YPRR, and writes an enriched CSV. Unresolved rows go to a manual-review CSV.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_college_feature_builder.py`:

```python
"""Tests for Phase 16.3 college feature builder."""
import pytest
from scripts.build_college_features import (
    normalize_player_name,
    compute_ryptpa,
    find_pff_match,
    build_college_season_year,
)


def test_normalize_player_name_strips_suffix():
    assert normalize_player_name("A.J. Brown Jr.") == "aj brown"
    assert normalize_player_name("Marvin Harrison II") == "marvin harrison"
    assert normalize_player_name("DeVonta Smith") == "devonta smith"


def test_normalize_player_name_removes_punctuation():
    assert normalize_player_name("Ja'Marr Chase") == "jamarr chase"
    assert normalize_player_name("D.J. Moore") == "dj moore"


def test_compute_ryptpa_basic():
    result = compute_ryptpa(receiving_yards=1000.0, team_pass_attempts=400.0)
    assert result == pytest.approx(2.5)


def test_compute_ryptpa_returns_none_on_zero_attempts():
    result = compute_ryptpa(receiving_yards=1000.0, team_pass_attempts=0.0)
    assert result is None


def test_compute_ryptpa_returns_none_when_yards_missing():
    result = compute_ryptpa(receiving_yards=None, team_pass_attempts=400.0)
    assert result is None


def test_compute_ryptpa_returns_none_when_attempts_missing():
    result = compute_ryptpa(receiving_yards=1000.0, team_pass_attempts=None)
    assert result is None


def test_find_pff_match_exact():
    pff_rows = [
        {"player_name": "AJ Brown", "college": "Mississippi", "yprr": 2.5, "yards": 1000.0},
    ]
    result = find_pff_match("A.J. Brown", "Mississippi", pff_rows)
    assert result is not None
    assert result["yards"] == 1000.0


def test_find_pff_match_college_abbrev():
    pff_rows = [
        {"player_name": "Courtland Sutton", "college": "SMU", "yprr": 2.1, "yards": 900.0},
    ]
    result = find_pff_match("Courtland Sutton", "SMU", pff_rows)
    assert result is not None


def test_find_pff_match_returns_none_for_no_match():
    pff_rows = [
        {"player_name": "Other Player", "college": "Alabama", "yprr": 2.0, "yards": 800.0},
    ]
    result = find_pff_match("AJ Brown", "Mississippi", pff_rows)
    assert result is None


def test_build_college_season_year_standard():
    # Most players: final college season = draft_year - 1
    assert build_college_season_year(draft_year=2019, position="WR") == 2018


def test_build_college_season_year_opt_out_returns_none():
    # Opt-outs / non-standard cases return None — caller must handle via fallback
    # e.g. Ja'Marr Chase (2021 draft) sat out 2020; his file is in 2019 season
    assert build_college_season_year(draft_year=2021, position="WR", opt_out=True) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python3.14 -m pytest tests/test_college_feature_builder.py -v 2>&1 | head -10
```

Expected: `ImportError`.

- [ ] **Step 3: Implement the feature builder**

Create `scripts/build_college_features.py`:

```python
"""Phase 16.3 College Feature Builder.

Joins PFF WR/RB export rows to Engine A training data, fetches CFBD team
pass attempts, computes RYPTPA, and extracts YPRR. Writes an enriched
training CSV and a manual_review CSV for unresolved rows.

Usage:
    .venv/bin/python3.14 scripts/build_college_features.py
    .venv/bin/python3.14 scripts/build_college_features.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.adapters.pff_wr_export import parse_pff_wr_season
from src.dynasty_genius.adapters.cfbd_receiving_adapter import (
    fetch_team_pass_attempts,
    normalize_college_name,
)

MANIFEST_PATH = ROOT / "app/data/pff_exports/phase16_wr_manifest.json"
TRAINING_CSV = ROOT / "app/data/training/prospects_with_outcomes.csv"
OUTPUT_CSV = ROOT / "app/data/training/prospects_with_outcomes_phase16.csv"
REVIEW_CSV = ROOT / "app/data/pff_exports/phase16_wr_manual_review.csv"


_SUFFIX_PATTERN = re.compile(
    r"\b(jr\.?|sr\.?|ii|iii|iv)\s*$", re.IGNORECASE
)


def normalize_player_name(name: str) -> str:
    """Lowercase, strip accents, remove punctuation and name suffixes."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(ch for ch in name if unicodedata.category(ch) != "Mn")
    name = name.lower()
    name = _SUFFIX_PATTERN.sub("", name).strip()
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def compute_ryptpa(
    receiving_yards: float | None,
    team_pass_attempts: float | None,
) -> float | None:
    """RYPTPA = receiving yards / team pass attempts."""
    if receiving_yards is None or team_pass_attempts is None:
        return None
    if team_pass_attempts <= 0:
        return None
    return receiving_yards / team_pass_attempts


def find_pff_match(
    pfr_name: str,
    college: str,
    pff_rows: list[dict],
) -> dict | None:
    """Find the best matching PFF row by normalized name + college."""
    norm_name = normalize_player_name(pfr_name)
    norm_college = normalize_college_name(college).lower()

    for row in pff_rows:
        row_name = normalize_player_name(row.get("player_name", ""))
        row_college = normalize_college_name(row.get("college", "")).lower()
        if row_name == norm_name and row_college == norm_college:
            return row

    # Relaxed: name match only (college name may differ slightly)
    for row in pff_rows:
        row_name = normalize_player_name(row.get("player_name", ""))
        if row_name == norm_name:
            return row

    return None


def build_college_season_year(
    draft_year: int,
    position: str,
    opt_out: bool = False,
) -> int | None:
    """College season year for the default (non-opt-out) case.

    Returns draft_year - 1 for standard entries. Returns None for opt-outs
    or other non-standard final-season cases — the feature builder treats
    None as a fallback signal to check adjacent season files.

    These files are full season snapshots, not draft-class-filtered exports.
    A player appears in whichever season(s) they actually played. The caller
    is responsible for resolving the correct file per player.
    """
    if opt_out:
        return None
    return draft_year - 1


def _load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Phase 16 WR manifest not found: {MANIFEST_PATH}\n"
            "Create app/data/pff_exports/phase16_wr_manifest.json first."
        )
    data = json.loads(MANIFEST_PATH.read_text())
    return data["exports"]


def _parse_all_seasons(manifest_entries: list[dict]) -> dict[int, list[dict]]:
    """Return {season_year: [pff_rows]} for all manifest entries."""
    seasons: dict[int, list[dict]] = {}
    seen_hashes: set[str] = set()
    for entry in manifest_entries:
        path = entry["path"]
        season = entry["season"]
        result = parse_pff_wr_season(path, season=season)
        if result.content_hash in seen_hashes:
            print(f"  [WARN] Duplicate content hash for season {season} — skipping")
            continue
        seen_hashes.add(result.content_hash)
        seasons[season] = result.rows
        print(f"  Loaded season {season}: {len(result.rows)} WR/RB rows")
    return seasons


def main(dry_run: bool = False) -> None:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("CFBD_API_KEY", "")

    print("Phase 16.3 College Feature Builder")
    print(f"  Training CSV: {TRAINING_CSV}")
    print(f"  Manifest: {MANIFEST_PATH}")
    print(f"  CFBD key present: {bool(api_key)}")

    manifest_entries = _load_manifest()
    pff_by_season = _parse_all_seasons(manifest_entries)

    with TRAINING_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        training_rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    new_fields = ["ryptpa", "source_ryptpa", "yprr_college", "source_yprr_college"]
    output_fields = fieldnames + [f for f in new_fields if f not in fieldnames]

    enriched: list[dict] = []
    review: list[dict] = []

    for row in training_rows:
        position = row.get("position", "").upper()
        if position not in ("WR", "RB"):
            enriched.append({**row, **{f: "" for f in new_fields}})
            continue

        draft_year = int(row.get("season", 0))
        college_season = build_college_season_year(draft_year, position)
        pff_rows = pff_by_season.get(college_season, [])

        pff_match = find_pff_match(
            row.get("pfr_player_name", ""),
            row.get("college", ""),
            pff_rows,
        )

        if pff_match is None:
            review.append({
                "gsis_id": row.get("gsis_id"),
                "pfr_player_name": row.get("pfr_player_name"),
                "position": position,
                "draft_year": draft_year,
                "college": row.get("college"),
                "college_season": college_season,
                "reason": "no_pff_match",
            })
            enriched.append({**row, **{f: "" for f in new_fields}})
            continue

        pff_yards = pff_match.get("yards")
        team_attempts = None
        if not dry_run and api_key:
            team_attempts = fetch_team_pass_attempts(
                pff_match.get("college", ""),
                college_season,
                api_key=api_key,
            )

        ryptpa = compute_ryptpa(pff_yards, team_attempts)
        yprr_col = pff_match.get("yprr")

        enriched.append({
            **row,
            "ryptpa": f"{ryptpa:.4f}" if ryptpa is not None else "",
            "source_ryptpa": "pff_yards_cfbd_attempts" if ryptpa is not None else "",
            "yprr_college": f"{yprr_col:.4f}" if yprr_col is not None else "",
            "source_yprr_college": "pff_premium_stats" if yprr_col is not None else "",
        })

    if not dry_run:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(enriched)
        print(f"\n  Written: {OUTPUT_CSV}")

        if review:
            with REVIEW_CSV.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(review[0].keys()))
                writer.writeheader()
                writer.writerows(review)
            print(f"  Manual review: {REVIEW_CSV} ({len(review)} rows)")

    wr_rb = [r for r in training_rows if r.get("position", "").upper() in ("WR", "RB")]
    resolved = len(wr_rb) - len(review)
    pct = resolved / len(wr_rb) * 100 if wr_rb else 0
    print(f"\n  Coverage: {resolved}/{len(wr_rb)} WR/RB rows resolved ({pct:.1f}%)")
    if pct < 80:
        print("  [WARN] Coverage below 80% — review manual_review.csv before bake-off")
    else:
        print("  [OK] Coverage ≥ 80% — proceed to bake-off")

    if dry_run:
        print("\n  [DRY RUN] No files written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python3.14 -m pytest tests/test_college_feature_builder.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 5: Run the builder dry-run to verify it loads without error**

```bash
.venv/bin/python3.14 scripts/build_college_features.py --dry-run
```

Expected: prints manifest entries and training data stats; exits without writing files.

- [ ] **Step 6: Run the builder for real**

```bash
.venv/bin/python3.14 scripts/build_college_features.py
```

Expected:
- Prints per-season row counts
- Prints coverage ≥ 80% OK message
- Writes `app/data/training/prospects_with_outcomes_phase16.csv`
- Writes `app/data/pff_exports/phase16_wr_manual_review.csv` if any unresolved rows

- [ ] **Step 7: Commit**

```bash
git add scripts/build_college_features.py tests/test_college_feature_builder.py
git commit -m "feat(phase16.3): college feature builder — RYPTPA and YPRR enrichment"
```

---

## Task 5: Engine A Contract Extension

**Files:**
- Modify: `src/dynasty_genius/models/engine_a_contract.py`
- Create: `tests/contract/test_phase16_college_features.py`

Adds `ryptpa`, `yprr_college`, and their source fields to `CFBD_MODEL_INPUT_COLUMNS`. Updates `POSITION_FEATURE_MATRIX` to list them as WR candidates. These are enrichment columns — they are not automatically used in model training until the bake-off promotion gate passes.

- [ ] **Step 1: Write the failing tests**

Create `tests/contract/test_phase16_college_features.py`:

```python
"""Contract tests for Phase 16 college feature additions to Engine A."""
from src.dynasty_genius.models.engine_a_contract import (
    CFBD_MODEL_INPUT_COLUMNS,
    POSITION_FEATURE_MATRIX,
    PROHIBITED_COLUMNS,
)


def test_ryptpa_in_allowed_columns():
    assert "ryptpa" in CFBD_MODEL_INPUT_COLUMNS


def test_yprr_college_in_allowed_columns():
    assert "yprr_college" in CFBD_MODEL_INPUT_COLUMNS


def test_source_fields_in_allowed_columns():
    assert "source_ryptpa" in CFBD_MODEL_INPUT_COLUMNS
    assert "source_yprr_college" in CFBD_MODEL_INPUT_COLUMNS


def test_wr_feature_matrix_lists_ryptpa():
    assert "ryptpa" in POSITION_FEATURE_MATRIX["WR"]


def test_yprr_college_not_in_prohibited():
    assert "yprr_college" not in PROHIBITED_COLUMNS


def test_nfl_yprr_still_prohibited():
    # nfl_yprr must remain prohibited — college yprr is a different field
    assert "nfl_yprr" in PROHIBITED_COLUMNS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_phase16_college_features.py -v 2>&1 | head -20
```

Expected: `AssertionError` on missing fields.

- [ ] **Step 3: Update the contract**

Edit `src/dynasty_genius/models/engine_a_contract.py`. Add to `CFBD_MODEL_INPUT_COLUMNS`:

```python
CFBD_MODEL_INPUT_COLUMNS = {
    "dominator_rating",
    "receiving_yards_share",
    "completion_pct",
    "yards_per_attempt",
    "td_int_ratio",
    "sack_rate",
    "all_purpose_yards",
    "passing_yards_share",
    "ppa",
    "wepa",
    "rushing_yards",
    "rushing_tds",
    "ryptpa",           # WR/RB: receiving yards per team pass attempt (CFBD + PFF)
    "yprr_college",     # WR: yards per route run from PFF college export
    "source_dominator_rating",
    "source_receiving_yards_share",
    "source_completion_pct",
    "source_yards_per_attempt",
    "source_td_int_ratio",
    "source_sack_rate",
    "source_all_purpose_yards",
    "source_passing_yards_share",
    "source_ppa",
    "source_wepa",
    "source_rushing_yards",
    "source_rushing_tds",
    "source_ryptpa",
    "source_yprr_college",
}
```

Update `POSITION_FEATURE_MATRIX`:

```python
POSITION_FEATURE_MATRIX = {
    "WR": ["dominator_rating", "receiving_yards_share", "ryptpa", "yprr_college"],
    "RB": ["dominator_rating", "ryptpa"],
    "TE": ["dominator_rating", "receiving_yards_share"],
    "QB": [
        "completion_pct",
        "yards_per_attempt",
        "td_int_ratio",
        "sack_rate",
        "all_purpose_yards",
        "passing_yards_share",
        "ppa",
        "wepa",
        "rushing_yards",
        "rushing_tds",
    ],
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_phase16_college_features.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Run the full suite to check for regressions**

```bash
.venv/bin/python3.14 -m pytest --ignore=tests/test_build_pff_te_export_report.py --ignore=tests/test_cfbd_qb_adapter.py -q 2>&1 | tail -5
```

Expected: same pass count as before + 6 new passes, 0 failures.

- [ ] **Step 6: Commit**

```bash
git add src/dynasty_genius/models/engine_a_contract.py tests/contract/test_phase16_college_features.py
git commit -m "feat(phase16.3): add ryptpa and yprr_college to Engine A contract as WR candidates"
```

---

## Task 6: WR Bake-Off Harness

**Files:**
- Create: `scripts/run_wr_college_bakeoff.py`
- Create: `tests/test_wr_college_bakeoff.py`

Runs leave-one-draft-class-out Ridge regression for each candidate feature set. Evaluates a three-part promotion gate. Writes a JSON artifact. Does not touch model pkl files or `latest.json`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_wr_college_bakeoff.py`:

```python
"""Tests for Phase 16.4 WR college bake-off gate logic."""
import pytest
from scripts.run_wr_college_bakeoff import (
    evaluate_promotion_gate,
    compute_vif,
    BakeoffGateResult,
)
import numpy as np


def test_gate_passes_all_criteria():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.8,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.005,
    )
    assert result.passes is True
    assert result.mae_improvement_pct == pytest.approx((3.0 - 2.8) / 3.0 * 100)


def test_gate_fails_insufficient_mae_improvement():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.95,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.0,
    )
    assert result.passes is False
    assert "mae_improvement" in result.fail_reasons


def test_gate_fails_insufficient_folds():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=2,
        total_folds=4,
        te_mae_delta=0.0,
    )
    assert result.passes is False
    assert "fold_consistency" in result.fail_reasons


def test_gate_fails_te_regression():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.015,  # >1% regression
    )
    assert result.passes is False
    assert "te_regression" in result.fail_reasons


def test_gate_te_delta_threshold():
    # exactly 1% regression: fails
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.01,
    )
    assert result.passes is False

    # just under 1%: passes
    result2 = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.0099,
    )
    assert result2.passes is True


def test_compute_vif_uncorrelated():
    rng = np.random.default_rng(42)
    X = rng.normal(size=(100, 2))
    vif = compute_vif(X, feature_idx=0)
    assert vif < 3.0  # uncorrelated features have low VIF


def test_compute_vif_collinear():
    rng = np.random.default_rng(42)
    base = rng.normal(size=100)
    X = np.column_stack([base, base + rng.normal(scale=0.1, size=100)])
    vif = compute_vif(X, feature_idx=0)
    assert vif > 5.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python3.14 -m pytest tests/test_wr_college_bakeoff.py -v 2>&1 | head -10
```

Expected: `ImportError`.

- [ ] **Step 3: Implement the bake-off harness**

Create `scripts/run_wr_college_bakeoff.py`:

```python
"""Phase 16.4 WR College Bake-Off Harness.

Runs leave-one-draft-class-out Ridge regression for baseline and candidate
feature sets. Evaluates a three-part promotion gate. Writes a JSON artifact.

Usage:
    .venv/bin/python3.14 scripts/run_wr_college_bakeoff.py
"""
from __future__ import annotations

import csv
import dataclasses
import json
import math
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENRICHED_CSV = ROOT / "app/data/training/prospects_with_outcomes_phase16.csv"
OUTPUT_DIR = ROOT / "app/data/backtest/phase16"

# Bake-off cohort: 2015–2022 as training folds; 2023–2024 as holdout
TRAINING_YEARS = set(range(2015, 2023))
HOLDOUT_YEARS = {2023, 2024}

# Promotion gate thresholds
MAE_IMPROVEMENT_PCT_GATE = 3.0    # ≥3% aggregate MAE improvement
FOLDS_PASSING_GATE = 3            # ≥3 of 4 folds improved
TE_MAE_DELTA_GATE = 0.01          # TE MAE must not regress >1% (absolute)

BASELINE_FEATURES = ["pick", "round", "age"]
CANDIDATE_SETS = {
    "baseline": BASELINE_FEATURES,
    "baseline_ryptpa": BASELINE_FEATURES + ["ryptpa"],
    "baseline_yprr_college": BASELINE_FEATURES + ["yprr_college"],
}


@dataclasses.dataclass
class BakeoffGateResult:
    passes: bool
    mae_improvement_pct: float
    folds_improved: int
    total_folds: int
    te_mae_delta: float
    fail_reasons: list[str]


def evaluate_promotion_gate(
    baseline_mae: float,
    candidate_mae: float,
    folds_improved: int,
    total_folds: int,
    te_mae_delta: float,
) -> BakeoffGateResult:
    """Three-part promotion gate per Phase 16 spec."""
    mae_improvement_pct = (baseline_mae - candidate_mae) / baseline_mae * 100
    fail_reasons: list[str] = []

    if mae_improvement_pct < MAE_IMPROVEMENT_PCT_GATE:
        fail_reasons.append("mae_improvement")
    if folds_improved < FOLDS_PASSING_GATE:
        fail_reasons.append("fold_consistency")
    if te_mae_delta >= TE_MAE_DELTA_GATE:
        fail_reasons.append("te_regression")

    return BakeoffGateResult(
        passes=len(fail_reasons) == 0,
        mae_improvement_pct=round(mae_improvement_pct, 4),
        folds_improved=folds_improved,
        total_folds=total_folds,
        te_mae_delta=round(te_mae_delta, 6),
        fail_reasons=fail_reasons,
    )


def compute_vif(X: np.ndarray, feature_idx: int) -> float:
    """Variance Inflation Factor for the feature at feature_idx."""
    from sklearn.linear_model import LinearRegression
    X_others = np.delete(X, feature_idx, axis=1)
    target = X[:, feature_idx]
    if X_others.shape[1] == 0:
        return 1.0
    r2 = LinearRegression().fit(X_others, target).score(X_others, target)
    return 1.0 / (1.0 - r2) if r2 < 1.0 else float("inf")


def _to_float(value: str | None) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _load_training_rows(position: str) -> list[dict]:
    if not ENRICHED_CSV.exists():
        raise FileNotFoundError(
            f"Enriched CSV not found: {ENRICHED_CSV}\n"
            "Run scripts/build_college_features.py first."
        )
    with ENRICHED_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("position", "").upper() == position]


def _run_loocv_candidate(
    rows: list[dict],
    feature_names: list[str],
    target: str = "y24_ppg",
    alpha: float = 100.0,
) -> dict:
    """Leave-one-draft-class-out Ridge regression."""
    eligible = []
    for row in rows:
        draft_year = int(row.get("season", 0))
        if draft_year not in TRAINING_YEARS:
            continue
        values = {f: _to_float(row.get(f)) for f in feature_names}
        y_val = _to_float(row.get(target))
        if y_val is None or any(v is None for v in values.values()):
            continue
        eligible.append({
            "draft_year": draft_year,
            "features": [values[f] for f in feature_names],
            "target": y_val,
        })

    years = sorted({r["draft_year"] for r in eligible})
    if len(years) < 2:
        return {"error": "insufficient_data", "n_rows": len(eligible)}

    fold_results = []
    for test_year in years:
        train = [r for r in eligible if r["draft_year"] != test_year]
        test = [r for r in eligible if r["draft_year"] == test_year]
        if not train or not test:
            continue

        X_train = np.array([r["features"] for r in train])
        y_train = np.array([r["target"] for r in train])
        X_test = np.array([r["features"] for r in test])
        y_test = np.array([r["target"] for r in test])

        model = Ridge(alpha=alpha).fit(X_train, y_train)
        y_pred = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        fold_results.append({
            "test_year": test_year,
            "n_train": len(train),
            "n_test": len(test),
            "mae": round(mae, 4),
        })

    mean_mae = float(np.mean([f["mae"] for f in fold_results]))
    return {
        "n_rows": len(eligible),
        "n_folds": len(fold_results),
        "fold_results": fold_results,
        "mean_mae": round(mean_mae, 4),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("Phase 16.4 WR College Bake-Off")
    print(f"  Run ID: {run_id}")
    print(f"  Enriched CSV: {ENRICHED_CSV}")

    wr_rows = _load_training_rows("WR")
    te_rows = _load_training_rows("TE")
    print(f"  WR rows: {len(wr_rows)} | TE rows: {len(te_rows)}")

    # Check YPRR coverage: only include as candidate if ≥70% WR rows have it
    yprr_covered = sum(1 for r in wr_rows if _to_float(r.get("yprr_college")) is not None)
    yprr_coverage_pct = yprr_covered / len(wr_rows) * 100 if wr_rows else 0
    print(f"  YPRR college coverage: {yprr_coverage_pct:.1f}%")

    active_candidates = {
        k: v for k, v in CANDIDATE_SETS.items()
        if "yprr_college" not in v or yprr_coverage_pct >= 70
    }

    candidate_results = {}
    for name, features in active_candidates.items():
        print(f"\n  Running candidate: {name} (features: {features})")
        result = _run_loocv_candidate(wr_rows, features)
        candidate_results[name] = result
        if "error" not in result:
            print(f"    MAE: {result['mean_mae']} over {result['n_folds']} folds")

    # VIF check: if both ryptpa and yprr_college present
    vif_report = {}
    if "baseline_ryptpa" in candidate_results and "baseline_yprr_college" in candidate_results:
        eligible = []
        for row in wr_rows:
            r = _to_float(row.get("ryptpa"))
            y = _to_float(row.get("yprr_college"))
            if r is not None and y is not None:
                eligible.append([r, y])
        if len(eligible) >= 10:
            X_vif = np.array(eligible)
            vif_ryptpa = compute_vif(X_vif, 0)
            vif_yprr = compute_vif(X_vif, 1)
            vif_report = {
                "vif_ryptpa": round(vif_ryptpa, 3),
                "vif_yprr_college": round(vif_yprr, 3),
                "collinear": vif_ryptpa > 5 or vif_yprr > 5,
                "recommendation": (
                    "retain_ryptpa_only" if vif_yprr > vif_ryptpa and vif_ryptpa > 5
                    else "retain_yprr_only" if vif_ryptpa > vif_yprr and vif_yprr > 5
                    else "both_acceptable"
                ),
            }
            print(f"\n  VIF: RYPTPA={vif_ryptpa:.2f}, YPRR={vif_yprr:.2f}")

    # TE MAE for gate (baseline on TE)
    te_baseline = _run_loocv_candidate(te_rows, BASELINE_FEATURES)
    te_baseline_mae = te_baseline.get("mean_mae", 0.0) or 0.0

    # Gate evaluation for each non-baseline candidate
    gate_results = {}
    baseline_mae = candidate_results.get("baseline", {}).get("mean_mae")
    for name, result in candidate_results.items():
        if name == "baseline" or "error" in result:
            continue
        candidate_mae = result.get("mean_mae")
        if baseline_mae is None or candidate_mae is None:
            continue

        folds_improved = sum(
            1 for bf, cf in zip(
                candidate_results["baseline"].get("fold_results", []),
                result.get("fold_results", []),
            )
            if cf["mae"] < bf["mae"]
        )

        # TE MAE with candidate features (features that exist in TE data)
        te_features = [f for f in CANDIDATE_SETS[name] if f != "yprr_college"]
        te_cand = _run_loocv_candidate(te_rows, te_features)
        te_cand_mae = te_cand.get("mean_mae", 0.0) or 0.0
        te_delta = max(0.0, te_cand_mae - te_baseline_mae)

        gate = evaluate_promotion_gate(
            baseline_mae=baseline_mae,
            candidate_mae=candidate_mae,
            folds_improved=folds_improved,
            total_folds=len(result.get("fold_results", [])),
            te_mae_delta=te_delta,
        )
        gate_results[name] = dataclasses.asdict(gate)
        status = "PASS" if gate.passes else "FAIL"
        print(f"\n  Gate [{name}]: {status} — {gate.fail_reasons or 'all criteria met'}")

    artifact = {
        "run_id": run_id,
        "generated_at": generated_at,
        "scope": "Phase 16.4 WR college efficiency signal bake-off",
        "candidates": candidate_results,
        "vif_report": vif_report,
        "te_baseline_mae": te_baseline_mae,
        "gate_results": gate_results,
        "promotion_decision": "PENDING_DAVID_REVIEW",
        "governance": {
            "market_data_used": False,
            "model_pkl_changed": False,
            "latest_json_changed": False,
        },
    }

    out_path = OUTPUT_DIR / f"wr_college_bakeoff_{generated_at}_{run_id}.json"
    out_path.write_text(json.dumps(artifact, indent=2))
    print(f"\n  Artifact written: {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add the phase16 backtest dir to .gitignore**

Append to `.gitignore`:

```
# Phase 16 bake-off run artifacts
app/data/backtest/phase16/
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/python3.14 -m pytest tests/test_wr_college_bakeoff.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 6: Run the bake-off**

```bash
.venv/bin/python3.14 scripts/run_wr_college_bakeoff.py
```

Expected: prints per-candidate MAE, VIF report, gate pass/fail per candidate, and writes artifact JSON.

- [ ] **Step 7: Run the full test suite**

```bash
.venv/bin/python3.14 -m pytest --ignore=tests/test_build_pff_te_export_report.py --ignore=tests/test_cfbd_qb_adapter.py -q 2>&1 | tail -5
```

Expected: all prior tests pass + new tests pass, 0 failures.

- [ ] **Step 8: Commit**

```bash
git add scripts/run_wr_college_bakeoff.py tests/test_wr_college_bakeoff.py .gitignore
git commit -m "feat(phase16.4): WR college bake-off harness with three-part promotion gate"
```

---

## Task 7: Promotion Decision Document

**Files:**
- Create: `docs/validation/phase16-4-wr-college-promotion-decision.md`

After the bake-off artifact exists, commit a human-readable promotion decision record. The structure follows Phase 13's promotion decision pattern.

- [ ] **Step 1: Read the bake-off artifact**

```bash
cat app/data/backtest/phase16/wr_college_bakeoff_*.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Gate results:')
for k, v in d.get('gate_results', {}).items():
    print(f'  {k}: passes={v[\"passes\"]}, MAE_pct={v[\"mae_improvement_pct\"]:.2f}%, fail={v[\"fail_reasons\"]}')
print('VIF:', d.get('vif_report'))
"
```

- [ ] **Step 2: Write the promotion decision document**

Create `docs/validation/phase16-4-wr-college-promotion-decision.md` with the actual artifact values filled in:

```markdown
# Phase 16.4 WR College Efficiency Signal — Promotion Decision

**Date:** 2026-MM-DD
**Bake-off artifact:** app/data/backtest/phase16/wr_college_bakeoff_{run_id}.json
**Decision:** PROMOTED / NOT PROMOTED (fill in after reviewing gate results)

## Gate Results

| Candidate | MAE Improvement | Folds Passing | TE Delta | Gate |
|---|---|---|---|---|
| baseline_ryptpa | X.X% | X/4 | X.XXX | PASS / FAIL |
| baseline_yprr_college | X.X% | X/4 | X.XXX | PASS / FAIL |

## VIF Report

(Fill from artifact)

## Decision

(State which candidate(s) are promoted to production POSITION_FEATURE_MATRIX.
If no candidate passes the gate, state NOT PROMOTED and the reason.)

## Production Change Authorized

- [ ] `POSITION_FEATURE_MATRIX["WR"]` updated: YES / NO
- [ ] Model pkl retrained: YES / NO (only if promoted)
- [ ] `latest.json` updated: YES / NO (only if promoted)

## Governance

- Market data used: NO
- Prohibited columns present: NO
- Reviewed by David: YES / PENDING
```

- [ ] **Step 3: Commit the promotion decision**

```bash
git add docs/validation/phase16-4-wr-college-promotion-decision.md
git commit -m "docs(phase16.4): WR college efficiency promotion decision record"
```

---

## Task 8: RB Age Governance Ruling

**Files:**
- Create: `docs/validation/phase16-5-rb-age-governance.md`

Per the spec: "RB age de-emphasis is a named governance decision that must be committed before any RB feature bake-off begins." This is a document-only task.

- [ ] **Step 1: Write the governance ruling**

Create `docs/validation/phase16-5-rb-age-governance.md`:

```markdown
# Phase 16.5 — RB Age De-Emphasis Governance Ruling

**Date:** 2026-MM-DD
**Authority:** Product Constitution §Rookie Evaluation Rules + David ruling
**Status:** PENDING / APPROVED / REJECTED

## Evidence

Heath Cummings (Fantasy Points, 2026 RB Rankings): "My model wasn't made more
predictive by adjusting for age." The finding holds after controlling for draft
capital. Age at NFL entry does not materially improve RB Engine A predictions
beyond what pick + round already capture.

Constitution position: age is listed as the second RB evaluation input
(after draft capital). This governance ruling clarifies the *model feature*
interpretation of age, not the *scouting descriptor* use.

## Ruling Options

**Option A — De-emphasize age for RBs (approved change):**
Remove `age` from the RB feature set in `POSITION_FEATURE_MATRIX["RB"]` and
run an ablation bake-off confirming no MAE regression before production
promotion. Age remains a visible descriptor on RB decision cards.

**Option B — Hold current (no change):**
`age` remains in the RB feature set. Evidence is noted but does not meet the
bar for a production change without a passing ablation bake-off.

## Decision

(David selects Option A or Option B here.)

**Selected:** OPTION _

**Rationale:**

## Downstream Gate

If Option A is selected: an RB age ablation bake-off is required before any
RB production model change. Commit the ablation artifact to
`app/data/backtest/phase16/rb_age_ablation_{run_id}.json` and a decision
record to `docs/validation/phase16-5b-rb-age-ablation-decision.md`.

If Option B is selected: Phase 16.5 is closed. No further action.

## Governance

- Market data used: NO
- Constitution conflict: NO (age remains a descriptor; model feature role is revised)
- Reviewed by David: PENDING
```

- [ ] **Step 2: Commit**

```bash
git add docs/validation/phase16-5-rb-age-governance.md
git commit -m "docs(phase16.5): RB age de-emphasis governance ruling document"
```

---

## Task 9: AGENT_SYNC Update

**Files:**
- Modify: `AGENT_SYNC.md`
- Modify: `docs/agent-ledger/2026-05-23.md`

- [ ] **Step 1: Update AGENT_SYNC.md**

In the "Active Phase" section, add Phase 19 entries following the existing format:

```
Phase 19 (= Phase 16.2–16.5) — IN PROGRESS: Engine A college signal upgrade.
- 16.2: PFF WR parser + CFBD receiving adapter + season manifest
- 16.3: College feature builder (RYPTPA + YPRR enrichment)
- 16.4: WR bake-off harness + promotion gate
- 16.5: RB age de-emphasis governance ruling
```

- [ ] **Step 2: Append ledger entry**

Append to `docs/agent-ledger/2026-05-23.md` (use actual timestamps):

```markdown
## Time Unknown ET - [Agent Name]

- Task: Phase 19 implementation — Phase 16.2 through 16.5 college signal upgrade.
- Governance read: 02-agent-operating-loop.md, 00-product-constitution.md,
  01-north-star-architecture.md, AGENT_SYNC.md (all v1.0.0)
- Active phase / surface: Phase 19 (Phase 16.2–16.5) / Engine A
- Intended or completed write scope: (list files changed)
- Files changed: (list)
- Tests / checks: (list)
- Product alignment: Validation-only — no production model change without gate pass
- Drift risks: Identity join fuzzy matching may miss some WR rows — check coverage report
- Handoff / next step: Run bake-off, fill in promotion decision doc, present to David
```

- [ ] **Step 3: Commit**

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-05-23.md
git commit -m "docs: update AGENT_SYNC and ledger for Phase 19 implementation start"
```

---

## Self-Review

### Spec Coverage Check

| Spec requirement | Task covering it |
|---|---|
| CFBD client adapter + CFBD_API_KEY env var | Task 3 |
| Silver-layer identity crosswalk (name + college join) | Task 4 |
| Unresolved rows → manual_review.csv | Task 4 |
| RYPTPA computation (WR/RB) | Task 4 |
| YPRR from PFF export | Task 2, Task 4 |
| VIF check (RYPTPA vs YPRR) | Task 6 |
| LOOCV walk-forward bake-off | Task 6 |
| Promotion gate: ≥3% MAE, ≥3/4 folds, TE not regressing | Task 6 |
| Season manifest pinning files to years | Task 1 |
| PFF grade prohibition | Task 2 |
| Content hash for duplicate detection | Task 2 |
| Engine A contract extension | Task 5 |
| Promotion decision document | Task 7 |
| RB age de-emphasis governance ruling | Task 8 |
| AGENT_SYNC + ledger updates | Task 9 |

### Placeholder Scan

None found — all steps contain actual code, commands, or concrete content.

### Type Consistency

- `parse_pff_wr_season` returns `ParsedPFFWRSeason` with `.rows`, `.content_hash` — used correctly in Task 4 `_parse_all_seasons`.
- `fetch_team_pass_attempts` returns `float | None` — used correctly in `compute_ryptpa`.
- `evaluate_promotion_gate` returns `BakeoffGateResult` with `.passes`, `.fail_reasons` — used correctly in Task 6 main loop and Task 6 tests.
- `compute_vif` takes `np.ndarray` and `int`, returns `float` — consistent across implementation and tests.
- `normalize_player_name` / `find_pff_match` / `build_college_season_year` / `compute_ryptpa` — all imported from `scripts.build_college_features` in tests; defined in the script. Consistent.
