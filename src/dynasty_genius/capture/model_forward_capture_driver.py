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

import hashlib
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Optional

from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    MODEL_SUPPORTED_ENGINE_PATHS,
    ModelForwardCaptureStore,
    build_model_player_key,
)

PRODUCER_PATH = Path("scripts/build_universe_pvo_batch.py")
ENGINE_B_MANIFEST_PATH = Path("app/data/models/engine_b/v2_manifest.json")
ENGINE_B_FEATURE_CSV_PATH = Path("app/data/training/engine_b_features_v2.csv")
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
) -> dict[str, Any]:
    """The vintage-defining lineage subset that feeds provenance_hash — SHARED by T2
    capture and T4 refresh so both compute the identical hash. Reads model artifacts
    READ-ONLY; raises FileNotFoundError on a missing REQUIRED artifact (per the engines
    present among model-supported rows). EXCLUDES git_sha / artifact_sha256 / dates /
    row_lineage (those are kept out of the vintage hash)."""
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
        feature_bytes = read_artifact(ENGINE_B_FEATURE_CSV_PATH)
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
) -> tuple[dict, dict]:
    """Resolve the §4 provenance block READ-ONLY. Raises FileNotFoundError on a
    missing REQUIRED artifact (for the engines present among model-supported rows)."""
    engines = {
        r.get("valuation", {}).get("engine_path")
        for r in players
        if r.get("valuation", {}).get("engine_path") in MODEL_SUPPORTED_ENGINE_PATHS
    }
    needs_b = bool(engines & {"ENGINE_B", "BLEND_AB"})
    needs_a = bool(engines & {"ENGINE_A", "BLEND_AB"})

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
        feature_bytes = read_artifact(ENGINE_B_FEATURE_CSV_PATH)
        feature_hash = _sha(feature_bytes)
        cutoff = _derived_training_cutoff(feature_bytes)
        derived_cutoff = {"value": cutoff, "status": "derived"}
        block["engine_b_manifest"] = {
            "path": str(ENGINE_B_MANIFEST_PATH),
            "sha256": _sha(manifest_bytes),
        }
        block["engine_b_per_position"] = per_position
        block["engine_b_derived_training_cutoff"] = derived_cutoff
        block["feature_csv"] = {
            "path": str(ENGINE_B_FEATURE_CSV_PATH),
            "sha256": feature_hash,
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

    subset = resolve_provenance_subset(pvo, read_artifact=read_artifact)
    return block, subset


def capture_model_pvo_snapshot(
    *,
    db_path: Path,
    report_path: Optional[Path],
    pvo_artifact_path: Any,
    coverage_artifact_path: Any,
    read_artifact: Callable[[Any], bytes],
    now_fn: Callable[[], datetime],
    git_sha_fn: Callable[[], str],
) -> dict[str, Any]:
    """Capture one model-output PIT snapshot from the published PVO artifact."""
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

    result = store.append_entries(entries)

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
