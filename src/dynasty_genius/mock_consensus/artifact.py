"""S1 overlay artifact builder + writer (spec v4 T6, U6/U8).

Builds the overlay-only mock-consensus artifact and writes it write-isolated to
``app/data/mock_consensus/`` (NEVER ``app/data/valuation/`` — the U8/G2 leakage
boundary). The artifact is recursively ``decision_supported=False``; exact-pick
fields carry the T4-set ``internal_diagnostic`` (T6 SERIALIZES it, it does not
invent it). Overlay/inference-only: not wired to any model / PVO / trade /
David-facing path this increment; banned-language clean.

Import isolation (spec v4 U2): imports only a sibling mock_consensus module and
stdlib; never Engine A/B, scoring, or backtest_mock_draft.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from src.dynasty_genius.mock_consensus.aggregate import ConsensusRecord

_ARTIFACT_SCHEMA_VERSION = "s1_mock_consensus_overlay_v1"

# run_id is interpolated into the on-disk filename, so it MUST be a safe token with
# no path separators or traversal ("..") — otherwise a crafted run_id could escape
# the app/data/mock_consensus/ quarantine and write into app/data/valuation/ (U8).
_SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str) or not _SAFE_RUN_ID_RE.match(run_id):
        raise ValueError(
            "run_id must be a safe token matching [A-Za-z0-9][A-Za-z0-9_-]* "
            f"(no path separators or traversal); got {run_id!r}"
        )

# Intrinsic, non-decision-grade caveats. No banned David-facing language.
_INTRINSIC_CAVEATS = (
    "Stacked inference: this overlay layers manual-mock curation, a read-only "
    "identity join, and consensus aggregation; errors compound across the stages.",
    "Exact-pick fields are internal diagnostics only (internal_diagnostic=True) "
    "and are never David-facing until S4 backtest evidence supports them.",
    "Projected NFL draft capital from analyst mock drafts; not a market price and "
    "not an Engine A/B model input.",
)


@dataclass(frozen=True)
class ArtifactWriteResult:
    """Paths written by :func:`write_mock_consensus_artifact`."""

    run_path: Path
    latest_path: Path


def _record_to_dict(record: ConsensusRecord) -> dict:
    payload = asdict(record)
    payload["raw_row_hashes_used"] = list(record.raw_row_hashes_used)
    # Per-record decision-support stamp (recursive decision_supported=False).
    payload["decision_supported"] = False
    return payload


def build_mock_consensus_artifact(
    records: list[ConsensusRecord],
    *,
    run_id: str,
    generated_at: str,
) -> dict:
    """Build the overlay artifact dict (pure; recursive decision_supported=False)."""
    _validate_run_id(run_id)
    return {
        "schema_version": _ARTIFACT_SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
        "decision_supported": False,
        "caveats": list(_INTRINSIC_CAVEATS),
        "records": [_record_to_dict(record) for record in records],
    }


def write_mock_consensus_artifact(
    records: list[ConsensusRecord],
    *,
    run_id: str,
    app_data_root: Path,
    generated_at: str,
) -> ArtifactWriteResult:
    """Write the artifact write-isolated to ``<app_data_root>/mock_consensus/``.

    Writes ``mock_consensus_<run_id>.json`` and ``mock_consensus_latest.json`` (with
    identical content). NEVER touches ``app/data/valuation/`` (U8). The injectable
    ``app_data_root`` keeps tests off the real data tree.
    """
    artifact = build_mock_consensus_artifact(
        records, run_id=run_id, generated_at=generated_at
    )
    out_dir = Path(app_data_root) / "mock_consensus"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_path = out_dir / f"mock_consensus_{run_id}.json"
    latest_path = out_dir / "mock_consensus_latest.json"
    serialized = json.dumps(artifact, indent=2, sort_keys=True)
    run_path.write_text(serialized, encoding="utf-8")
    latest_path.write_text(serialized, encoding="utf-8")
    return ArtifactWriteResult(run_path=run_path, latest_path=latest_path)
