"""Dual Daily PIT Capture — model-output forward-capture T2 driver (artifact-read).

Reads the published PVO artifacts through injected byte readers, computes the 3-hash
vintage model (artifact_sha256 audit / semantic_output_hash / provenance_hash),
resolves the read-only provenance block, maps rows into the T1 store, and emits the
§5 capture report. It does NOT refresh PVO, touch the real filesystem, use wall-clock
time, or do scheduler work (T3+). Market fields are excluded from the store (counted).

Vintage = semantic_output_hash + provenance_hash. Both EXCLUDE volatile fields
(captured_at/assembled_at/pipeline_run_id) and provenance_hash also EXCLUDES git_sha
(audit-only) and the literal artifact_sha256 — so a daily re-score on unchanged
inputs reports vintage_changed=false (no false new vintage).

Design spec: docs/superpowers/specs/2026-06-24-model-output-forward-capture-brick-design.md
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Optional

from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    MODEL_SUPPORTED_ENGINE_PATHS,
    ModelForwardCaptureConflictError,
    ModelForwardCaptureStore,
    ModelForwardCaptureValidationError,
    build_model_player_key,
)

# Module-level so the capture driver can write the companion prediction snapshot in the
# same transaction as the core row (and so tests can monkeypatch it).
from src.dynasty_genius.capture.prediction_snapshot_store import (
    CANONICAL_UTIL_FIELDS,
    PredictionSnapshotStore,
)
from src.dynasty_genius.features.feature_source import resolve_feature_source
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_FEATURES_BY_POSITION

PRODUCER_PATH = Path("scripts/build_universe_pvo_batch.py")
ENGINE_B_MANIFEST_PATH = Path("app/data/models/engine_b/v2_manifest.json")
# The committed seed + the runtime publish dir; the resolver picks a verified runtime when
# published, else the seed. The vintage-defining feature_csv_sha256 follows whichever is
# served, so a published runtime yields a DISTINCT provenance_hash (the whole point of T3).
ENGINE_B_FEATURE_SEED_PATH = Path("app/data/training/engine_b_features_v2.csv")
ENGINE_B_FEATURES_RUNTIME_DIR = Path("app/data/features_runtime")
ENGINE_A_LATEST_PATH = Path("app/data/models/latest.json")
HEAD_A_V3_MANIFEST_PATH = Path("app/data/models/head_a/v3_manifest.json")

_VOLATILE_ROW_KEYS = frozenset({"captured_at", "assembled_at", "pipeline_run_id"})
_MARKET_ROW_KEYS = frozenset({"market_overlay", "divergence"})


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _semantic_projection(row: dict) -> dict:
    """Row content that defines the model vintage: excludes volatile + market keys."""
    return {
        k: v
        for k, v in row.items()
        if k not in _VOLATILE_ROW_KEYS and k not in _MARKET_ROW_KEYS
    }


def _derived_training_cutoff(feature_csv_bytes: bytes) -> Optional[int]:
    lines = feature_csv_bytes.decode().strip().splitlines()
    if not lines:
        return None
    header = [c.strip() for c in lines[0].split(",")]
    seasons: list[int] = []
    for line in lines[1:]:
        record = dict(zip(header, [c.strip() for c in line.split(",")]))
        if record.get("training_eligible", "").lower() == "true":
            try:
                seasons.append(int(record["season"]))
            except (KeyError, ValueError):
                continue
    return max(seasons) if seasons else None


def resolve_provenance_subset(
    pvo: dict,
    *,
    read_artifact: Callable[[Any], bytes],
    feature_source: Optional[Any] = None,
) -> dict[str, Any]:
    """The vintage-defining lineage subset that feeds provenance_hash — SHARED by T2
    capture and T4 refresh so both compute the identical hash. Reads model artifacts
    READ-ONLY; raises FileNotFoundError on a missing REQUIRED artifact (per the engines
    present among model-supported rows). EXCLUDES git_sha / artifact_sha256 / dates /
    row_lineage (those are kept out of the vintage hash).

    ``feature_source`` may be a pinned ``ResolvedFeatureSource`` so injected-artifact-reader
    tests do not depend on ambient gitignored runtime files after a feature-refresh catch-up;
    when None the ambient resolver is used (production picks up the published runtime)."""
    players = pvo.get("players") or []
    engines = {
        r.get("valuation", {}).get("engine_path")
        for r in players
        if r.get("valuation", {}).get("engine_path") in MODEL_SUPPORTED_ENGINE_PATHS
    }
    needs_b = bool(engines & {"ENGINE_B", "BLEND_AB"})
    needs_a = bool(engines & {"ENGINE_A", "BLEND_AB"})

    subset: dict[str, Any] = {
        "pvo_schema_version": pvo.get("schema_version"),
        "source_snapshot_captured_at": pvo.get("source_snapshot_captured_at"),
        "pvo_producer_hash": _sha(read_artifact(PRODUCER_PATH)),
    }
    if needs_b:
        manifest_bytes = read_artifact(ENGINE_B_MANIFEST_PATH)
        manifest = json.loads(manifest_bytes)
        # Hash the RESOLVED feature source (runtime when published, else seed) so the
        # vintage changes day-over-day once a refreshed runtime is published. Subset shape
        # is unchanged — only the bytes behind feature_csv_sha256 follow the resolver.
        resolved = (
            feature_source
            if feature_source is not None
            else resolve_feature_source(
                seed_path=ENGINE_B_FEATURE_SEED_PATH,
                runtime_dir=ENGINE_B_FEATURES_RUNTIME_DIR,
            )
        )
        feature_bytes = read_artifact(resolved.path)
        subset["engine_b"] = {
            "manifest_sha256": _sha(manifest_bytes),
            "per_position": {
                position: _sha(read_artifact(Path(pkl_path)))
                for position, pkl_path in manifest.items()
            },
            "derived_training_cutoff": {
                "value": _derived_training_cutoff(feature_bytes),
                "status": "derived",
            },
            "feature_csv_sha256": _sha(feature_bytes),
        }
    if needs_a:
        latest_bytes = read_artifact(ENGINE_A_LATEST_PATH)
        latest = json.loads(latest_bytes)
        head_a_bytes = read_artifact(HEAD_A_V3_MANIFEST_PATH)
        head_a = json.loads(head_a_bytes)
        te_meta_bytes = read_artifact(Path(head_a["TE"]).parent / "te_v3_metadata.json")
        subset["engine_a"] = {
            "pointer_model_version": latest.get("model_version"),
            "pointer_sha256": _sha(latest_bytes),
            "head_a_sha256": _sha(head_a_bytes),
            "te_metadata_sha256": _sha(te_meta_bytes),
        }
    return subset


def _resolve_provenance(
    players: list[dict],
    *,
    read_artifact: Callable[[Any], bytes],
    git_sha_fn: Callable[[], str],
    pvo: dict,
    artifact_sha256: str,
    coverage_sha256: str,
    pvo_artifact_path: Any,
    coverage_artifact_path: Any,
    artifact_vintage: Optional[str],
    capture_date: str,
    artifact_age_days: Optional[int],
    feature_source: Optional[Any] = None,
) -> tuple[dict, dict]:
    """Resolve the §4 provenance block READ-ONLY. Raises FileNotFoundError on a
    missing REQUIRED artifact (for the engines present among model-supported rows).

    ``feature_source`` may pin a ``ResolvedFeatureSource`` (hermeticity seam); resolved
    ONCE here so the audit block and the hashed subset agree on a single source."""
    engines = {
        r.get("valuation", {}).get("engine_path")
        for r in players
        if r.get("valuation", {}).get("engine_path") in MODEL_SUPPORTED_ENGINE_PATHS
    }
    needs_b = bool(engines & {"ENGINE_B", "BLEND_AB"})
    needs_a = bool(engines & {"ENGINE_A", "BLEND_AB"})

    resolved_feature_source = None
    if needs_b:
        resolved_feature_source = (
            feature_source
            if feature_source is not None
            else resolve_feature_source(
                seed_path=ENGINE_B_FEATURE_SEED_PATH,
                runtime_dir=ENGINE_B_FEATURES_RUNTIME_DIR,
            )
        )

    producer_hash = _sha(read_artifact(PRODUCER_PATH))

    block: dict[str, Any] = {
        "git_sha": git_sha_fn(),  # audit-only; NOT in provenance_hash
        "pvo_artifact_path": str(pvo_artifact_path),
        "artifact_sha256": artifact_sha256,
        "artifact_vintage": artifact_vintage,
        "source_snapshot_captured_at": pvo.get("source_snapshot_captured_at"),
        "pvo_schema_version": pvo.get("schema_version"),
        "coverage_artifact_path": str(coverage_artifact_path),
        "coverage_sha256": coverage_sha256,
        "capture_date": capture_date,
        "artifact_age_days": artifact_age_days,
        "pvo_producer": {"path": str(PRODUCER_PATH), "sha256": producer_hash},
    }

    if needs_b:
        manifest_bytes = read_artifact(ENGINE_B_MANIFEST_PATH)
        manifest = json.loads(manifest_bytes)
        per_position: dict[str, Any] = {}
        for position, pkl_path in manifest.items():
            per_position[position] = {
                "path": pkl_path,
                "sha256": _sha(read_artifact(Path(pkl_path))),
            }
        feature_bytes = read_artifact(resolved_feature_source.path)
        feature_hash = _sha(feature_bytes)
        seed_hash = _sha(read_artifact(ENGINE_B_FEATURE_SEED_PATH))
        cutoff = _derived_training_cutoff(feature_bytes)
        derived_cutoff = {"value": cutoff, "status": "derived"}
        block["engine_b_manifest"] = {
            "path": str(ENGINE_B_MANIFEST_PATH),
            "sha256": _sha(manifest_bytes),
        }
        block["engine_b_per_position"] = per_position
        block["engine_b_derived_training_cutoff"] = derived_cutoff
        # Audit-only (NOT in provenance_hash): which source served + the seed baseline, so
        # an analyst can see whether a vintage came from a published runtime or the seed.
        block["feature_csv"] = {
            "path": str(resolved_feature_source.path),
            "feature_source_kind": resolved_feature_source.source_kind,
            "sha256": feature_hash,
            "feature_csv_sha256": feature_hash,
            "published_seed_sha256": seed_hash,
            "max_training_season": cutoff,
        }

    if needs_a:
        latest_bytes = read_artifact(ENGINE_A_LATEST_PATH)
        latest = json.loads(latest_bytes)
        head_a_bytes = read_artifact(HEAD_A_V3_MANIFEST_PATH)
        head_a = json.loads(head_a_bytes)
        te_meta_path = Path(head_a["TE"]).parent / "te_v3_metadata.json"
        te_meta_bytes = read_artifact(te_meta_path)
        block["engine_a_v2_pointer"] = {
            "path": str(ENGINE_A_LATEST_PATH),
            "model_version": latest.get("model_version"),
            "run_dir": latest.get("run_dir"),
            "sha256": _sha(latest_bytes),
        }
        block["head_a_v3_manifest"] = {
            "path": str(HEAD_A_V3_MANIFEST_PATH),
            "sha256": _sha(head_a_bytes),
        }
        block["te_v3_metadata"] = {
            "path": str(te_meta_path),
            "sha256": _sha(te_meta_bytes),
        }
        block["engine_a_training_cutoff"] = {"value": None, "status": "unknown"}

    subset = resolve_provenance_subset(
        pvo, read_artifact=read_artifact, feature_source=resolved_feature_source
    )
    return block, subset


def _util_role(field: str, position: Optional[str]) -> str:
    """Position-AWARE role per the Engine B contract: a field is ``model_input`` only when
    it is in that position's model matrix, else ``diagnostic_only``. ``route_participation``,
    ``target_share_nfl`` and ``air_yards_share`` are in NO position set (excluded — collinear),
    so they are always ``diagnostic_only``; ``weighted_opportunity``/``yprr``/``tprr`` are
    ``model_input`` for WR/TE only; ``snap_share`` is ``model_input`` for all positions."""
    matrix = ENGINE_B_FEATURES_BY_POSITION.get(position or "", frozenset())
    return "model_input" if field in matrix else "diagnostic_only"


def _parse_util_value(raw: Any) -> Optional[float]:
    """Parse a feature-CSV cell to a finite float, else None (blank/unparseable/non-finite).
    Feature cells are strings; a non-finite or non-numeric cell is recorded as a null value
    rather than aborting the whole survivorship-complete capture."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "":
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _load_prediction_time_utilization(
    provenance: dict, read_artifact: Callable[[Any], bytes]
) -> tuple[dict[str, dict[str, str]], frozenset[str]]:
    """Read the RESOLVED Engine B feature source (the same CSV the producer scored — the
    ``training_eligible == False`` inference rows keyed by gsis ``player_id``) and return a
    ``{player_id: row}`` map plus the set of canonical util columns actually present in the
    header. When no Engine B feature source is in provenance (no model-supported B rows),
    returns empty — every companion row then reads ``missing_feature_row``."""
    feature_csv = provenance.get("feature_csv")
    if not feature_csv or not feature_csv.get("path"):
        return {}, frozenset()
    raw = read_artifact(Path(feature_csv["path"]))
    reader = csv.DictReader(io.StringIO(raw.decode()))
    header = reader.fieldnames or []
    present = frozenset(c for c in CANONICAL_UTIL_FIELDS if c in header)
    by_player_id: dict[str, dict[str, str]] = {}
    for record in reader:
        if str(record.get("training_eligible", "")).strip().lower() != "false":
            continue  # only inference rows carry the prediction-time utilization
        player_id = record.get("player_id")
        if player_id:
            by_player_id[str(player_id)] = record
    return by_player_id, present


def _build_utilization_snapshot(
    *,
    dg_player_id: Optional[str],
    position: Optional[str],
    feature_rows_by_player_id: dict[str, dict[str, str]],
    present_util_columns: frozenset[str],
) -> tuple[dict[str, dict[str, Any]], str]:
    """Build the role-tagged utilization snapshot for one captured row by joining its
    ``dg_player_id`` (== gsis ``player_id`` for Engine B, set in ``build_universe_pvo_batch``)
    onto the inference feature row. Fail-closed + survivorship-complete: an unmatched key →
    all-null values + ``missing_feature_row``; a matched row missing some canonical columns →
    those fields null + ``partial_missing_util_columns``. Roles are always position-aware,
    even when a value is null, because position is known independent of the value."""
    feature_row = (
        feature_rows_by_player_id.get(str(dg_player_id))
        if dg_player_id is not None
        else None
    )
    if feature_row is None:
        utilization = {
            field: {"value": None, "role": _util_role(field, position)}
            for field in CANONICAL_UTIL_FIELDS
        }
        return utilization, "missing_feature_row"

    utilization = {}
    for field in CANONICAL_UTIL_FIELDS:
        value = _parse_util_value(feature_row.get(field)) if field in present_util_columns else None
        utilization[field] = {"value": value, "role": _util_role(field, position)}
    all_columns_present = set(CANONICAL_UTIL_FIELDS) <= present_util_columns
    status = "complete" if all_columns_present else "partial_missing_util_columns"
    return utilization, status


def capture_model_pvo_snapshot(
    *,
    db_path: Path,
    report_path: Optional[Path],
    pvo_artifact_path: Any,
    coverage_artifact_path: Any,
    read_artifact: Callable[[Any], bytes],
    now_fn: Callable[[], datetime],
    git_sha_fn: Callable[[], str],
    feature_source: Optional[Any] = None,
) -> dict[str, Any]:
    """Capture one model-output PIT snapshot from the published PVO artifact.

    ``feature_source`` may pin a ``ResolvedFeatureSource`` for hermetic tests; when None the
    ambient resolver runs so a production capture picks up the published runtime."""
    now = now_fn()
    capture_date = now.date().isoformat()

    def _persist(report: dict) -> dict:
        if report_path is not None:
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True))
        return report

    def abort(reason: str) -> dict:
        return _persist(
            {
                "status": "aborted",
                "capture_date": capture_date,
                "aborted_reason": reason,
                "decision_supported": False,
            }
        )

    # ── read + validate the PVO artifact ──
    try:
        pvo_bytes = read_artifact(pvo_artifact_path)
    except FileNotFoundError:
        return abort("missing_artifact")
    artifact_sha256 = _sha(pvo_bytes)
    try:
        pvo = json.loads(pvo_bytes)
    except (json.JSONDecodeError, ValueError):
        return abort("malformed_artifact")
    players = pvo.get("players")
    if not isinstance(players, list) or not players:
        return abort("empty_artifact")
    artifact_vintage = pvo.get("captured_at")

    try:
        coverage_bytes = read_artifact(coverage_artifact_path)
    except FileNotFoundError:
        return abort("missing_coverage_artifact")
    coverage_sha256 = _sha(coverage_bytes)

    artifact_age_days: Optional[int] = None
    if isinstance(artifact_vintage, str):
        try:
            artifact_age_days = (now.date() - date.fromisoformat(artifact_vintage[:10])).days
        except ValueError:
            artifact_age_days = None

    # ── resolve provenance (required-missing → abort, no write) ──
    try:
        provenance, provenance_subset = _resolve_provenance(
            players,
            read_artifact=read_artifact,
            git_sha_fn=git_sha_fn,
            pvo=pvo,
            artifact_sha256=artifact_sha256,
            coverage_sha256=coverage_sha256,
            pvo_artifact_path=pvo_artifact_path,
            coverage_artifact_path=coverage_artifact_path,
            artifact_vintage=artifact_vintage,
            capture_date=capture_date,
            artifact_age_days=artifact_age_days,
            feature_source=feature_source,
        )
    except FileNotFoundError as exc:
        return abort(f"required_provenance_missing:{exc}")

    # ── 3-hash vintage model ──
    semantic_output_hash = _sha(_canon([_semantic_projection(r) for r in players]))
    provenance_hash = _sha(_canon(provenance_subset))

    # ── map rows → T1 entries (market excluded; survivorship-complete) ──
    entries: list[dict] = []
    counts_by_engine_path: dict[str, int] = {}
    row_lineage: list[dict] = []
    market_excluded = 0
    for index, row in enumerate(players):
        valuation = row.get("valuation") or {}
        identity_ids = row.get("identity_ids") or {}
        player = row.get("player") or {}
        lineage = row.get("lineage") or {}
        engine_path = valuation.get("engine_path")
        counts_by_engine_path[engine_path] = counts_by_engine_path.get(engine_path, 0) + 1
        if row.get("market_overlay") is not None or row.get("divergence") is not None:
            market_excluded += 1
        semantic_row_hash = _sha(_canon(_semantic_projection(row)))
        player_key = build_model_player_key(
            row,
            semantic_output_hash=semantic_output_hash,
            row_index=index,
            semantic_row_hash=semantic_row_hash,
        )
        # Model-supported rows REQUIRE per-row lineage (sleeper_snapshot_hash); missing
        # → abort the whole run before any write (spec §4). row_lineage carries the
        # volatile pipeline_run_id as audit metadata and is NOT in provenance_hash.
        if engine_path in MODEL_SUPPORTED_ENGINE_PATHS:
            ssh = lineage.get("sleeper_snapshot_hash")
            gov = lineage.get("governance_version")
            if not (isinstance(ssh, str) and ssh.strip()):
                return abort(
                    f"required_provenance_missing:row_lineage_sleeper_snapshot_hash:{player_key}"
                )
            if not (isinstance(gov, str) and gov.strip()):
                return abort(
                    f"required_provenance_missing:row_lineage_governance_version:{player_key}"
                )
            row_lineage.append(
                {
                    "player_key": player_key,
                    "lineage": {
                        "governance_version": gov,
                        "sleeper_snapshot_hash": ssh,
                    },
                    "pipeline_run_id": row.get("pipeline_run_id"),
                }
            )
        entries.append(
            {
                "capture_date": capture_date,
                "source": MODEL_PVO_SOURCE,
                "semantic_output_hash": semantic_output_hash,
                "provenance_hash": provenance_hash,
                "player_key": player_key,
                "sleeper_id": identity_ids.get("sleeper_id"),
                "dg_player_id": row.get("dg_player_id"),
                "player_name": player.get("full_name"),
                "position": player.get("position"),
                "engine_path": engine_path,
                "dynasty_value_score": valuation.get("dynasty_value_score"),
                "dvs_pct": row.get("dvs_pct"),
                "xvar": row.get("xvar"),
                "model_grade": valuation.get("model_grade"),
                "model_version": valuation.get("model_version"),
                "artifact_vintage": artifact_vintage,
                "row_index": index,
                "semantic_row_hash": semantic_row_hash,
                "payload_hash": semantic_row_hash,
            }
        )

    player_keys = [e["player_key"] for e in entries]
    duplicate_count = len(player_keys) - len(set(player_keys))
    missing_sleeper_count = sum(
        1 for k in player_keys if not k.startswith("sleeper:")
    )
    unresolved_count = sum(1 for k in player_keys if k.startswith("unresolved:"))
    provenance["row_lineage"] = row_lineage
    store_hash = _sha(
        _canon({"sigs": sorted(e["player_key"] + ":" + e["payload_hash"] for e in entries)})
    )

    # ── store + vintage_changed (was this vintage seen before this write?) ──
    store = ModelForwardCaptureStore(db_path)
    with sqlite3.connect(Path(db_path)) as conn:
        prior = conn.execute(
            "SELECT 1 FROM model_forward_capture_raw "
            "WHERE semantic_output_hash=? AND provenance_hash=? LIMIT 1",
            [semantic_output_hash, provenance_hash],
        ).fetchone()
    vintage_changed = prior is None

    # ── companion prediction snapshots (projection_2y + prediction-time util), 1:1 ──
    # Prediction-time utilization is pulled from the SAME resolved Engine B feature source
    # the producer scored (inference rows, joined on dg_player_id == gsis player_id), with
    # position-aware role tags from the Engine B contract. source_hash is the resolved
    # feature-CSV sha from provenance (NOT the injected feature_source, which is None on the
    # real CLI path). No T2 identity bridge is needed: for Engine B, dg_player_id IS the gsis.
    companion = PredictionSnapshotStore(db_path)
    feature_rows_by_player_id, present_util_columns = _load_prediction_time_utilization(
        provenance, read_artifact
    )
    source_hash = (provenance.get("feature_csv") or {}).get("sha256")
    companion_rows: list[dict] = []
    for entry, row in zip(entries, players):
        projection_2y = row.get("projection_2y")
        utilization, util_snapshot_status = _build_utilization_snapshot(
            dg_player_id=entry.get("dg_player_id"),
            position=entry.get("position"),
            feature_rows_by_player_id=feature_rows_by_player_id,
            present_util_columns=present_util_columns,
        )
        companion_rows.append(
            {
                "capture_date": entry["capture_date"],
                "source": entry["source"],
                "semantic_output_hash": entry["semantic_output_hash"],
                "provenance_hash": entry["provenance_hash"],
                "player_key": entry["player_key"],
                "projection_2y": projection_2y,
                "utilization": utilization,
                "prediction_ppg_status": (
                    "captured" if projection_2y is not None else "capture_incomplete"
                ),
                "util_snapshot_status": util_snapshot_status,
                "schema_version": 1,
                "source_hash": source_hash,
            }
        )

    # ── atomic core + companion write: a companion failure rolls the core write back ──
    try:
        with sqlite3.connect(Path(db_path)) as conn:
            result = store.append_entries(entries, conn=conn)
            for companion_row in companion_rows:
                companion.append_snapshot(companion_row, conn=conn)
    except (ModelForwardCaptureConflictError, ModelForwardCaptureValidationError):
        raise  # preserve core-store conflict/validation semantics (propagates, rolls back)
    except Exception as exc:  # companion failure → abort, core already rolled back
        return abort(f"companion_write_failed:{exc}")

    report = {
        "status": "ok",
        "capture_date": capture_date,
        "artifact_vintage": artifact_vintage,
        "artifact_age_days": artifact_age_days,
        "raw_rows": result["raw_rows_written"],
        "joinable_rows": result["joinable_rows_written"],
        "counts_by_engine_path": counts_by_engine_path,
        "missing_sleeper_count": missing_sleeper_count,
        "unresolved_count": unresolved_count,
        "duplicate_count": duplicate_count,
        "market_fields_excluded_count": market_excluded,
        "artifact_sha256": artifact_sha256,
        "coverage_sha256": coverage_sha256,
        "semantic_output_hash": semantic_output_hash,
        "provenance_hash": provenance_hash,
        "store_hash": store_hash,
        "vintage_changed": vintage_changed,
        "decision_supported": False,
        "aborted_reason": None,
        "provenance": provenance,
    }
    return _persist(report)
