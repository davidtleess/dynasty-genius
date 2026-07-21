"""QB-1 study-side source loading: the seven-dataset fail-closed gate (F1).

Spec rows implemented here (v9, SHA-256 347c2d6e30d2… + amendment b7221a7a…):
D1 pins exactly seven nflverse datasets (weekly all-position player stats, the
1b official REG season summaries, players, rosters, the ff_playerids
crosswalk, draft_picks, pbp). ``load_validation_sources`` is the study's single
entry to them: every dataset must be present with an ``ok`` status — an
unavailable, stale, or absent dataset is a NAMED fail-closed refusal
(``source_unavailable``), never a silent substitution and never a partial pool.

Ingestion itself lives in the shared adapter's ``load_validation_*`` functions
(`src/dynasty_genius/adapters/nflreadpy_qb_adapter.py`) — the single-adapter
law. This module consumes their (frame, metadata) outputs or injected hermetic
fixtures shaped the same way.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure

# The pinned D1 dataset set, in spec order (v9: seven names — dataset 1b
# `season_summary` per amendment §A1, the official REG season CPOE source).
VALIDATION_DATASETS = (
    "weekly",
    "season_summary",
    "players",
    "rosters",
    "ff_playerids",
    "draft_picks",
    "pbp",
)


def _dataset_problem(dataset: str, state: Any) -> str | None:
    """One dataset's admission check; a string return is the named defect."""
    if not isinstance(state, Mapping):
        return f"{dataset}: state is {type(state).__name__}, not a mapping"
    if state.get("status") != "ok":
        return f"{dataset}: status {state.get('status')!r}"
    frame = state.get("frame")
    if frame is None:
        return f"{dataset}: no parsed frame"
    # A parsed frame is dataframe-shaped: length alone is not shape — a list
    # or string has len() but is not a frame (round-2 B1).
    if getattr(frame, "columns", None) is None:
        return f"{dataset}: frame is {type(frame).__name__}, not a dataframe"
    try:
        if len(frame) == 0:
            return f"{dataset}: empty parsed frame"
    except TypeError:
        return f"{dataset}: frame has no length ({type(frame).__name__})"
    metadata = state.get("metadata")
    if not isinstance(metadata, Mapping):
        return f"{dataset}: missing provenance metadata"
    snapshot = metadata.get("raw_snapshot_path")
    if not snapshot:
        return f"{dataset}: raw snapshot absent — no parsed rows may be used"
    # Provenance must point at a snapshot that EXISTS: a path string for a
    # file that was never written is not a raw snapshot (round-2 B1).
    if not Path(str(snapshot)).is_file():
        return f"{dataset}: raw snapshot absent at {snapshot!r} — no parsed rows may be used"
    for field in ("source_timestamp", "parser_version"):
        if not metadata.get(field):
            return f"{dataset}: metadata lacks {field}"
    if metadata.get("completeness") != "ok":
        return f"{dataset}: completeness {metadata.get('completeness')!r}"
    return None


def load_validation_sources(
    sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    """Gate the study's source pool: seven USABLE, provenance-bearing datasets (F1).

    A status string is not proof. Each dataset must be a mapping with
    ``status == "ok"``, a non-empty parsed frame, and provenance metadata
    carrying a raw-snapshot path, source timestamp, parser version, and
    ``completeness == "ok"`` — the D1 "raw snapshot absent ⇒ no parsed rows"
    guarantee, enforced. Any defect refuses the WHOLE pool with the named
    ``source_unavailable`` reason — fail closed, no partial study.
    """
    if not isinstance(sources, Mapping):
        raise QBValidationFailure(
            "source_unavailable",
            f"sources must be a mapping, got {type(sources).__name__} (fail_closed)",
        )
    problems: list[str] = []
    for dataset in VALIDATION_DATASETS:
        if dataset not in sources:
            problems.append(f"{dataset}: absent")
            continue
        problem = _dataset_problem(dataset, sources[dataset])
        if problem is not None:
            problems.append(problem)
    if problems:
        raise QBValidationFailure(
            "source_unavailable",
            "; ".join(problems) + " — stale or unavailable input, fail_closed, "
            "no parsed rows are used",
        )
    return {dataset: sources[dataset] for dataset in VALIDATION_DATASETS}
