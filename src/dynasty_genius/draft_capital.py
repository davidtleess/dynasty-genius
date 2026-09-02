"""Draft capital for veterans — the Engine A prior's inputs, read from a governed offline snapshot.

DG-128 (2026-09-01). Engine A is a draft-capital model: it scores a player from his overall
`pick`, his `round` and his DRAFT-season age. Prospects carry those on their cards; veterans
never did, which is why the Phase 15 blend has fired zero times in production. This module
supplies them for veterans from nflverse `draft_picks` — the SAME table Engine A was trained
from (app/data/pipeline/collect_draft_prospects.py) — so `pick` is the overall selection,
`round` is 1–7, and `age` is the exact training variable.

Three properties are load-bearing:

* Offline by design. The serving batch never touches the network. A snapshot is captured once
  (scripts/capture_draft_capital.py), content-hashed, and committed under resources/; the batch
  reads it and records the hash in every PVO's source_versions.
* Nothing is derived and nothing is imputed. A player with no draft row is undrafted and gets
  no prior; a draft row with no age yields pick and round only, and the assembler then declines
  the prior rather than guess.
* Conflicts fail closed with a count, never a pick. A gsis_id with two draft rows excludes BOTH
  rows and increments `gsis_conflict_rows`; a row without a gsis_id cannot be joined and
  increments `gsis_missing_rows`. Last-write-wins is exactly the silence TW28 removed from the
  identity join, and it is not reintroduced here.

Errors raise a BARE machine token as their message, the convention of build_universe_pvo_batch:
`run_pvo_refresh` copies `str(exc)` into the governed report's `aborted_reason`.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = "dynasty_genius.draft_capital.v1"
SKILL_POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE")
DRAFT_CAPITAL_SNAPSHOT_PATH = ROOT / "resources" / "draft_capital" / "nflverse_draft_picks.json"

# The columns the snapshot keeps, in the order they are written. `age` is nullable at the source.
_ROW_COLUMNS: tuple[str, ...] = ("gsis_id", "season", "round", "pick", "age", "position")


class DraftCapitalError(ValueError):
    """Raised with a bare machine token; see the module docstring."""


@dataclass(frozen=True)
class DraftCapital:
    gsis_id: str
    season: int
    round: int
    pick: int
    age: float | None
    position: str

    def engine_a_features(self) -> dict[str, float]:
        """The assembler's Engine A keys for a VETERAN.

        `age_at_nfl_entry`, never `age`: a veteran's feature row already carries `age` as his
        current age, and pvo_assembler reads the draft-season age from its own key with no
        fallback. A null source age is simply absent — the assembler then withholds the prior.
        """
        features = {"pick": float(self.pick), "round": float(self.round)}
        if self.age is not None:
            features["age_at_nfl_entry"] = float(self.age)
        return features


@dataclass(frozen=True)
class DraftCapitalIndex:
    path: Path
    content_sha256: str
    accounting: dict[str, int]
    _by_gsis: Mapping[str, DraftCapital] = field(default_factory=dict, repr=False)

    def get(self, gsis_id: str | None) -> DraftCapital | None:
        if gsis_id is None:
            return None
        return self._by_gsis.get(str(gsis_id))

    def __len__(self) -> int:
        return len(self._by_gsis)


def content_sha256(rows: list[dict[str, Any]]) -> str:
    """Hash of the rows alone, in canonical form, so `pulled_at` cannot mint a new content hash."""
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _none_if_missing(value: Any) -> Any:
    # nflverse rows arrive through polars/pandas; a missing cell may be None or a float NaN.
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    return value


def build_snapshot(
    source_rows: Iterable[Mapping[str, Any]],
    *,
    seasons: tuple[int, int],
    pulled_at: str,
    source: str,
) -> dict[str, Any]:
    """Reduce raw nflverse draft rows to the pinned columns for the skill positions.

    Pure: no I/O, no network. Rows are sorted by (season, pick) so the content hash is stable
    across pulls that return the same picks in a different order.
    """
    rows: list[dict[str, Any]] = []
    for raw in source_rows:
        position = _none_if_missing(raw.get("position"))
        if position not in SKILL_POSITIONS:
            continue
        rows.append({column: _none_if_missing(raw.get(column)) for column in _ROW_COLUMNS})
    rows.sort(key=lambda row: (int(row["season"]), int(row["pick"])))
    return {
        "schema": SCHEMA,
        "source": source,
        "pulled_at": pulled_at,
        "seasons": [int(seasons[0]), int(seasons[1])],
        "positions": list(SKILL_POSITIONS),
        "content_sha256": content_sha256(rows),
        "rows": rows,
    }


def write_snapshot(snapshot: Mapping[str, Any], path: Path) -> None:
    """Atomic: a reader never sees a half-written snapshot (tmp + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(snapshot, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_draft_capital(path: Path = DRAFT_CAPITAL_SNAPSHOT_PATH) -> DraftCapitalIndex:
    if not path.exists():
        raise DraftCapitalError("draft_capital_snapshot_missing")
    snapshot = json.loads(path.read_text())
    if snapshot.get("schema") != SCHEMA:
        raise DraftCapitalError("draft_capital_schema_mismatch")
    rows = snapshot.get("rows")
    if not isinstance(rows, list):
        raise DraftCapitalError("draft_capital_rows_missing")
    if content_sha256(rows) != snapshot.get("content_sha256"):
        raise DraftCapitalError("draft_capital_sha_mismatch")

    by_gsis: dict[str, DraftCapital] = {}
    conflicted: set[str] = set()
    gsis_missing = 0
    for row in rows:
        gsis_id = row.get("gsis_id")
        if gsis_id is None:
            gsis_missing += 1
            continue
        gsis_id = str(gsis_id)
        if gsis_id in conflicted:
            continue
        if gsis_id in by_gsis:
            del by_gsis[gsis_id]
            conflicted.add(gsis_id)
            continue
        age = row.get("age")
        by_gsis[gsis_id] = DraftCapital(
            gsis_id=gsis_id,
            season=int(row["season"]),
            round=int(row["round"]),
            pick=int(row["pick"]),
            age=None if age is None else float(age),
            position=str(row["position"]),
        )

    conflict_rows = sum(1 for row in rows if str(row.get("gsis_id")) in conflicted)
    return DraftCapitalIndex(
        path=path,
        content_sha256=snapshot["content_sha256"],
        accounting={
            "snapshot_rows": len(rows),
            "indexed_players": len(by_gsis),
            "gsis_missing_rows": gsis_missing,
            "gsis_conflict_rows": conflict_rows,
        },
        _by_gsis=by_gsis,
    )
