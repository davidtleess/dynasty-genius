"""Build the versioned provider-contract evidence bundle.

The bundle exists to stop source adapters from being implemented from memory. Public CFBD
contracts are committed in full. Paid PFF and PlayerProfiler exports remain private: their
committed manifests contain only hashes, counts, vintages, and value-*kind* profiles — never
row values, filenames, or complete paid headers.

This is an explicit/manual refresh command. It does not call a paid API and does not mutate
any ingestion store.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "provider-contracts"
DEFAULT_CFBD_RAW = (
    ROOT
    / "app"
    / "data"
    / "sources"
    / "cfbd_foundation"
    / "raw"
    / "20260802T024342156864Z"
)
DEFAULT_PFF_RAW = ROOT / "app" / "data" / "pff_exports" / "raw"
DEFAULT_PFF_CATALOG = ROOT / "app" / "data" / "pff_exports" / "pff_schema_catalog.json"
DEFAULT_PP_STATUS = ROOT / "app" / "data" / "playerprofiler"

BUNDLE_VERSION = "provider-contracts.v1"
CFBD_SWAGGER_INIT_URL = "https://api.collegefootballdata.com/swagger-ui-init.js"
VALUE_PROFILE_SAMPLE_ROWS = 200


class ProviderContractError(RuntimeError):
    """The evidence bundle refuses rather than pinning an ambiguous source shape."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, payload: Any) -> str:
    data = _canonical_json(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha256_bytes(data)


def _extract_swagger_doc(swagger_init: Path) -> dict[str, Any]:
    text = swagger_init.read_text(encoding="utf-8")
    marker = '"swaggerDoc":'
    start = text.find(marker)
    if start < 0:
        raise ProviderContractError("cfbd_swagger_doc_missing")
    start += len(marker)
    try:
        payload, _ = json.JSONDecoder().raw_decode(text[start:].lstrip())
    except json.JSONDecodeError as exc:
        raise ProviderContractError(f"cfbd_swagger_doc_invalid: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("paths"), dict):
        raise ProviderContractError("cfbd_swagger_doc_wrong_root")
    return payload


def _build_cfbd(
    *, swagger_init: Path, raw_dir: Path, output: Path, generated_at: str
) -> dict[str, Any]:
    openapi = _extract_swagger_doc(swagger_init)
    info = openapi.get("info") or {}
    version = str(info.get("version") or "").strip()
    if not version:
        raise ProviderContractError("cfbd_openapi_version_missing")

    openapi_path = output / "cfbd" / "openapi.json"
    openapi_sha = _write_json(openapi_path, openapi)

    raw_files = sorted(raw_dir.glob("qb_raw_*_team.json"))
    if not raw_files:
        raise ProviderContractError(f"cfbd_team_stat_evidence_missing: {raw_dir}")
    unique_payloads: dict[str, list[Mapping[str, Any]]] = {}
    for path in raw_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not all(
            isinstance(row, dict) for row in payload
        ):
            raise ProviderContractError(f"cfbd_team_stat_wrong_shape: {path.name}")
        digest = _sha256_bytes(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        unique_payloads.setdefault(digest, payload)

    observed: dict[str, dict[str, set[Any]]] = defaultdict(
        lambda: {"seasons": set(), "teams": set(), "payloads": set()}
    )
    for digest, payload in unique_payloads.items():
        for row in payload:
            name = str(row.get("statName") or "").strip()
            if not name:
                raise ProviderContractError("cfbd_team_stat_name_blank")
            observed[name]["seasons"].add(row.get("season"))
            observed[name]["teams"].add(str(row.get("team") or ""))
            observed[name]["payloads"].add(digest)

    stat_catalog = {
        "contract_version": BUNDLE_VERSION,
        "source": "collegefootballdata.com",
        "endpoint": "/stats/season",
        "evidence_run_id": raw_dir.name,
        "privacy": "public provider response names only; values and player rows omitted",
        "raw_files_examined": len(raw_files),
        "unique_payloads_examined": len(unique_payloads),
        "stats": [
            {
                "stat_name": name,
                "payload_count": len(meta["payloads"]),
                "seasons": sorted(x for x in meta["seasons"] if x is not None),
                "team_count": len(meta["teams"] - {""}),
            }
            for name, meta in sorted(observed.items())
        ],
    }
    stat_path = output / "cfbd" / "team-stat-catalog.json"
    stat_sha = _write_json(stat_path, stat_catalog)

    required_paths = (
        "/player/search",
        "/stats/player/season",
        "/ppa/players/season",
        "/wepa/players/passing",
        "/stats/season",
        "/games",
    )
    missing = sorted(set(required_paths) - set(openapi["paths"]))
    if missing:
        raise ProviderContractError(f"cfbd_required_paths_missing: {missing}")

    manifest = {
        "contract_version": BUNDLE_VERSION,
        "provider": "collegefootballdata.com",
        "retrieved_at": generated_at,
        "source_url": CFBD_SWAGGER_INIT_URL,
        "swagger_init_sha256": _sha256_file(swagger_init),
        "openapi_version": version,
        "openapi_sha256": openapi_sha,
        "team_stat_catalog_sha256": stat_sha,
        "required_paths": list(required_paths),
        "response_identity_fields": {
            "/player/search": "id",
            "/stats/player/season": "playerId",
            "/ppa/players/season": "id",
            "/wepa/players/passing": "athleteId",
            "/stats/season": "team+season",
            "/games": "id",
        },
        "known_invalid_paths": ["/stats/team/season"],
        "required_dynamic_stat_names": ["passAttempts", "sacksOpponent"],
        "known_invalid_dynamic_stat_names": ["sacksAllowed"],
    }
    _write_json(output / "cfbd" / "manifest.json", manifest)
    return manifest


_INT = re.compile(r"^[+-]?\d+$")
_DECIMAL = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?$")


def _value_kind(value: str | None) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"na", "n/a", "#n/a", "null", "none", "-"}:
        return "blank_or_null_token"
    if _INT.fullmatch(text):
        return "integer"
    if _DECIMAL.fullmatch(text):
        return "decimal"
    if text.lower() in {"true", "false"}:
        return "boolean"
    return "text"


def _read_csv_profile(
    path: Path,
    *,
    sample_limit: int = VALUE_PROFILE_SAMPLE_ROWS,
    block_fields: Sequence[str] = (),
) -> tuple[tuple[str, ...], list[set[str]], dict[str, set[str]]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        if not columns:
            raise ProviderContractError(f"provider_header_missing: {path.name}")
        kinds = [set() for _ in columns]
        blocks: dict[str, set[str]] = {field: set() for field in block_fields}
        row_count = 0
        for row in reader:
            row_count += 1
            for field in block_fields:
                value = str(row.get(field) or "").strip()
                if value:
                    blocks[field].add(value)
            if row_count <= sample_limit:
                for index, column in enumerate(columns):
                    kinds[index].add(_value_kind(row.get(column)))
            if row_count >= sample_limit and not block_fields:
                break
        if row_count == 0:
            raise ProviderContractError(f"provider_export_empty: {path.name}")
    return columns, kinds, blocks


def _merge_kinds(left: list[set[str]], right: list[set[str]]) -> None:
    if len(left) != len(right):
        raise ProviderContractError("provider_profile_width_mismatch")
    for target, source in zip(left, right):
        target.update(source)


def _profile_signature(kinds: Iterable[set[str]]) -> tuple[list[list[str]], str]:
    profile = [sorted(values) for values in kinds]
    digest = _sha256_bytes(
        json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return profile, digest


def _build_pff(
    *, raw_root: Path, private_catalog: Path, output: Path, generated_at: str
) -> dict[str, Any]:
    files = sorted(raw_root.rglob("*.csv"))
    if not files:
        raise ProviderContractError(f"pff_exports_missing: {raw_root}")

    groups: dict[str, dict[str, Any]] = {}
    for path in files:
        relative = path.relative_to(raw_root)
        if len(relative.parts) < 5:
            raise ProviderContractError(f"pff_canonical_path_invalid: {relative}")
        league, report, scope, season = relative.parts[:4]
        columns, kinds, _ = _read_csv_profile(path)
        header_sha = _sha256_bytes("\n".join(columns).encode("utf-8"))
        group = groups.setdefault(
            header_sha,
            {
                "header_sha256": header_sha,
                "column_count": len(columns),
                "reports": set(),
                "leagues": set(),
                "scopes": set(),
                "seasons": set(),
                "payload_count": 0,
                "kinds": [set() for _ in columns],
            },
        )
        if group["column_count"] != len(columns):
            raise ProviderContractError("pff_header_hash_collision")
        group["reports"].add(report)
        group["leagues"].add(league)
        group["scopes"].add(scope)
        group["seasons"].add(int(season))
        group["payload_count"] += 1
        _merge_kinds(group["kinds"], kinds)

    schemas = []
    for group in groups.values():
        profile, profile_sha = _profile_signature(group.pop("kinds"))
        kind_counts: dict[str, int] = defaultdict(int)
        for values in profile:
            for value in values:
                kind_counts[value] += 1
        schemas.append(
            {
                **group,
                "reports": sorted(group["reports"]),
                "leagues": sorted(group["leagues"]),
                "scopes": sorted(group["scopes"]),
                "seasons": sorted(group["seasons"]),
                "value_kind_profile_sha256": profile_sha,
                "value_kind_column_counts": dict(sorted(kind_counts.items())),
            }
        )

    private_schema_ids = {
        str(row.get("schema_sha256") or "")
        for row in json.loads(private_catalog.read_text(encoding="utf-8"))
    }
    generated_schema_ids = {schema["header_sha256"] for schema in schemas}
    if private_schema_ids != generated_schema_ids:
        raise ProviderContractError(
            "pff_private_catalog_drift: generated headers do not match the governed "
            f"private catalog (missing={sorted(private_schema_ids - generated_schema_ids)}, "
            f"extra={sorted(generated_schema_ids - private_schema_ids)})"
        )

    manifest = {
        "contract_version": BUNDLE_VERSION,
        "provider": "pff",
        "generated_at": generated_at,
        "delivery": "paid manual exports",
        "privacy": {
            "raw_values_committed": False,
            "complete_headers_committed": False,
            "source_filenames_committed": False,
            "note": (
                "Full paid headers and rows remain in the gitignored, backed-up private "
                "inventory. This manifest pins each header and redacted value-kind profile "
                "by SHA-256 without publishing proprietary contents."
            ),
        },
        "private_catalog_sha256": _sha256_file(private_catalog),
        "value_profile_sample_rows_per_payload": VALUE_PROFILE_SAMPLE_ROWS,
        "payload_count": len(files),
        "schema_count": len(schemas),
        "schemas": sorted(schemas, key=lambda item: item["header_sha256"]),
    }
    _write_json(output / "pff" / "header-manifest.json", manifest)
    return manifest


def _playerprofiler_sources(downloads: Path) -> list[tuple[str, Path, tuple[str, ...]]]:
    patterns = (
        ("player_season", "data_analysis_report*.csv", ("season", "position")),
        ("medical_history", "MedicalHistory_*.csv", ()),
        ("weekly_roster_key", "[0-9][0-9][0-9][0-9]-Weekly-Roster-Key.csv", ()),
        ("advanced_gamelog", "[0-9][0-9][0-9][0-9]-Advanced-Gamelog.csv", ()),
        ("advanced_pbp", "[0-9][0-9][0-9][0-9]-Advanced-PBP-Data.csv", ()),
    )
    out: list[tuple[str, Path, tuple[str, ...]]] = []
    for stream, pattern, block_fields in patterns:
        out.extend(
            (stream, path, block_fields) for path in sorted(downloads.glob(pattern))
        )
    return out


def _filename_season(path: Path) -> str | None:
    leading = re.match(r"(\d{4})", path.name)
    if leading:
        return leading.group(1)
    medical = re.search(r"MedicalHistory_(\d{4})", path.name)
    return medical.group(1) if medical else None


def _build_playerprofiler(
    *, downloads: Path, status_root: Path, output: Path, generated_at: str
) -> dict[str, Any]:
    sources = _playerprofiler_sources(downloads)
    if not sources:
        raise ProviderContractError(f"playerprofiler_exports_missing: {downloads}")

    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for stream, path, block_fields in sources:
        columns, kinds, blocks = _read_csv_profile(path, block_fields=block_fields)
        header_sha = _sha256_bytes("\n".join(columns).encode("utf-8"))
        key = (stream, header_sha)
        group = groups.setdefault(
            key,
            {
                "stream": stream,
                "header_sha256": header_sha,
                "column_count": len(columns),
                "source_file_count": 0,
                "seasons": set(),
                "positions": set(),
                "kinds": [set() for _ in columns],
            },
        )
        group["source_file_count"] += 1
        season = _filename_season(path)
        if season:
            group["seasons"].add(season)
        group["seasons"].update(blocks.get("season", set()))
        group["seasons"].update(blocks.get("Year", set()))
        group["positions"].update(blocks.get("position", set()))
        _merge_kinds(group["kinds"], kinds)

    status_files = sorted(status_root.glob("*status_latest.json"))
    versions = {}
    for path in status_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stream = str(
            (payload.get("provenance") or {}).get("stream") or "player_season_medical"
        )
        versions[stream] = {
            "schema_version": payload.get("schema_version"),
            "run_id": payload.get("run_id"),
            "status_sha256": _sha256_file(path),
        }

    schemas = []
    for group in groups.values():
        profile, profile_sha = _profile_signature(group.pop("kinds"))
        kind_counts: dict[str, int] = defaultdict(int)
        for values in profile:
            for value in values:
                kind_counts[value] += 1
        schemas.append(
            {
                **group,
                "seasons": sorted(group["seasons"]),
                "positions": sorted(group["positions"]),
                "value_kind_profile_sha256": profile_sha,
                "value_kind_column_counts": dict(sorted(kind_counts.items())),
            }
        )

    manifest = {
        "contract_version": BUNDLE_VERSION,
        "provider": "playerprofiler",
        "generated_at": generated_at,
        "delivery": "paid manual subscriber exports",
        "privacy": {
            "raw_values_committed": False,
            "complete_headers_committed": False,
            "source_filenames_committed": False,
            "note": (
                "Only header hashes, widths, vintages, and value-kind profile hashes are "
                "committed. No subscriber row, player identifier, filename, or complete "
                "paid header leaves the private source directory."
            ),
        },
        "source_file_count": len(sources),
        "value_profile_sample_rows_per_file": VALUE_PROFILE_SAMPLE_ROWS,
        "schema_count": len(schemas),
        "status_contracts": dict(sorted(versions.items())),
        "schemas": sorted(
            schemas, key=lambda item: (item["stream"], item["header_sha256"])
        ),
    }
    _write_json(output / "playerprofiler" / "header-manifest.json", manifest)
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cfbd-swagger-init", required=True, type=Path)
    parser.add_argument("--cfbd-raw-dir", type=Path, default=DEFAULT_CFBD_RAW)
    parser.add_argument("--pff-raw-root", type=Path, default=DEFAULT_PFF_RAW)
    parser.add_argument("--pff-private-catalog", type=Path, default=DEFAULT_PFF_CATALOG)
    parser.add_argument(
        "--playerprofiler-downloads", type=Path, default=Path.home() / "Downloads"
    )
    parser.add_argument(
        "--playerprofiler-status-root", type=Path, default=DEFAULT_PP_STATUS
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--generated-at")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    generated_at = args.generated_at or datetime.now(timezone.utc).isoformat()
    cfbd = _build_cfbd(
        swagger_init=args.cfbd_swagger_init,
        raw_dir=args.cfbd_raw_dir,
        output=args.output,
        generated_at=generated_at,
    )
    pff = _build_pff(
        raw_root=args.pff_raw_root,
        private_catalog=args.pff_private_catalog,
        output=args.output,
        generated_at=generated_at,
    )
    playerprofiler = _build_playerprofiler(
        downloads=args.playerprofiler_downloads,
        status_root=args.playerprofiler_status_root,
        output=args.output,
        generated_at=generated_at,
    )
    index = {
        "contract_version": BUNDLE_VERSION,
        "generated_at": generated_at,
        "providers": {
            "cfbd": {
                "manifest": "cfbd/manifest.json",
                "openapi_version": cfbd["openapi_version"],
            },
            "pff": {
                "manifest": "pff/header-manifest.json",
                "schemas": pff["schema_count"],
            },
            "playerprofiler": {
                "manifest": "playerprofiler/header-manifest.json",
                "schemas": playerprofiler["schema_count"],
            },
        },
    }
    _write_json(args.output / "index.json", index)
    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
