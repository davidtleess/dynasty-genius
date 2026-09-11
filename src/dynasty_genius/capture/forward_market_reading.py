"""New dated research readings from an unchanged, verified forecast archive."""

from __future__ import annotations

import base64
import copy
import hashlib
import re
from pathlib import Path

from src.dynasty_genius.capture.workspace_snapshot_store import (
    ARTIFACT_NAMES,
    SnapshotBundle,
    canonical_bytes,
    read_snapshot,
    strict_json,
)
from src.dynasty_genius.ranking.market_ranks import (
    build_forward_market_ranks,
    build_market_ranks,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_forward_template(archive_root: Path, snapshot_id: str) -> SnapshotBundle:
    """Read an original immutable snapshot; never instantiate a writable store."""
    from scripts.capture_track_record_inputs import read_archived_artifacts

    saved = read_snapshot(archive_root, snapshot_id)
    artifacts = read_archived_artifacts(archive_root, snapshot_id)
    return SnapshotBundle(
        artifacts={name: artifacts[name] for name in ARTIFACT_NAMES},
        ranks=saved["ranks"],
        comparison=saved["comparison"],
    )


def _validated_template(template: SnapshotBundle) -> tuple[dict, dict, dict]:
    raw = template.artifacts
    _require(set(raw) == set(ARTIFACT_NAMES), "Unexpected template artifacts")
    docs = {name: strict_json(data, f"template {name}") for name, data in raw.items()}
    report, market, league = (docs[name] for name in ("report.json", "market.json", "league.json"))
    manifest = docs["source-manifest.json"]
    for key in ("report", "market", "league"):
        _require(
            manifest["files"][key]["sha256"] == _sha(raw[f"{key}.json"]),
            f"Moved template {key} source",
        )
    _require(report["run"] == manifest["report_run"], "Changed template report run")
    _require(report["inputs"]["snapshot"]["sha256"] == _sha(raw["league.json"]), "Changed template league binding")
    catalog, companion = docs["catalog.json"], docs["catalog-companion.json"]
    _require(catalog["run"] == companion["run"], "Changed template catalog identity")
    _require(catalog["source_report_run"] == companion["source_report_run"] == report["run"], "Changed template catalog report")
    _require(companion["outputs_sha256"]["catalog.json"] == _sha(raw["catalog.json"]), "Moved template catalog bytes")

    # Recompute the original financial identities. Prose and later additive
    # explanation fields are not part of the saved forecast's identity.
    expected = build_market_ranks(report, market, league)
    actual = {row["sleeper_id"]: row for row in template.ranks["rows"]}
    _require(len(actual) == len(template.ranks["rows"]) == len(expected["rows"]), "Changed template rank population")
    fields = (
        "name", "position", "team", "model_zero_tie", "reference_player",
        "model_value", "market_value", "our_rank", "market_rank",
        "model_rank_all", "market_rank_published", "seasons", "on_roster",
        "league_ownership", "taxi_or_reserve", "comparison",
    )
    for row in expected["rows"]:
        saved = actual.get(row["sleeper_id"])
        _require(saved is not None and all(saved.get(key) == row.get(key) for key in fields), "Changed template rank values")
    _require(template.ranks["coverage"] == expected["coverage"], "Changed template coverage")
    for key, value in expected["source"].items():
        if key.endswith("_sha256"):
            value = _sha(raw[key.removesuffix("_sha256") + ".json"])
        _require(template.ranks["source"].get(key) == value, "Changed template source identity")
    _require(template.comparison["source"]["report_sha256"] == _sha(raw["report.json"]), "Changed template comparison source")
    return report, market, league


def build_forward_reading(
    template: SnapshotBundle, market_bytes: bytes, *, capture_artifacts: dict[str, bytes]
) -> SnapshotBundle:
    """Create a distinct reading while retaining every original football source.

    The fixed archive format has no extra artifact slots. Exact capture evidence
    is therefore embedded as base64 bytes plus hashes in the new source manifest,
    together with the original manifest. Nothing is written by this function.
    """
    try:
        report, _, league = _validated_template(template)
        _require(isinstance(market_bytes, bytes), "Market artifact must be bytes")
        market = strict_json(market_bytes, "new market capture")
        ranks = build_forward_market_ranks(report, market, league)
        evidence = {}
        _require(isinstance(capture_artifacts, dict) and bool(capture_artifacts), "Capture artifact evidence is required")
        for name, payload in capture_artifacts.items():
            _require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) is not None, "Invalid capture artifact name")
            _require(isinstance(payload, bytes) and bool(payload), "Capture artifact must contain bytes")
            evidence[name] = {"sha256": _sha(payload), "base64": base64.b64encode(payload).decode("ascii")}
        artifacts = dict(template.artifacts)
        artifacts["market.json"] = market_bytes
        manifest = {
            "schema_version": 2,
            "reading_kind": "frozen_forecast_new_market",
            "report_run": report["run"],
            "forecast_date": report["forecast_date"],
            "market_observed_at": market["retrieved_at"],
            "observation_clock": "collector retrieval time; source publication time unavailable",
            "files": {key: {"artifact": f"{key}.json", "sha256": _sha(artifacts[f"{key}.json"])} for key in ("report", "market", "league")},
            "template_source_manifest": {
                "sha256": _sha(template.artifacts["source-manifest.json"]),
                "base64": base64.b64encode(template.artifacts["source-manifest.json"]).decode("ascii"),
            },
            "capture_evidence": evidence,
        }
        artifacts["source-manifest.json"] = canonical_bytes(manifest, what="forward source manifest")
        ranks["source"].update({f"{key}_sha256": _sha(artifacts[f"{key}.json"]) for key in ("report", "market", "league")})
        return SnapshotBundle(artifacts=artifacts, ranks=ranks, comparison=copy.deepcopy(template.comparison))
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError("Incomplete forward reading or template") from exc
