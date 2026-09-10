"""Export a reviewed Lovable reading into a new, deterministic public asset directory.

Every input is explicit. This stdlib-only helper runs no producer, model, URL or
subprocess. It removes three reviewed metadata fields from the board copy and
disables saving in the track-record copy; all other parsed content is retained.
Unknown private paths or credential markers cause refusal, never extra redaction.
The manifest records original source hashes separately from delivery file hashes.
It is written last, after all assets, and never includes local input paths.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import unquote


class ExportError(ValueError):
    """A source or destination is unsuitable for a public immutable export."""


SOURCE_FIELDS = (
    "report_run", "report_sha256", "market_sha256", "league_sha256",
    "catalog_run", "catalog_content_sha256",
)
DATE_FIELDS = ("forecast_date", "market_as_of", "ownership_as_of")
REMOVED_METADATA = (
    "payloads.available.source.provenance.argv",
    "payloads.available.starting_estimates.source.run_dir",
    "payloads.available.rows[*].forecast.source_csv",
)
SAVE_CAPABILITY = {
    "enabled": False,
    "reason": "Saving new readings is available in the Mac preview.",
    "expected": None,
}
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
NUMERIC_ID = re.compile(r"(?:0|[1-9][0-9]*)\Z")
PRIVATE_MARKER = re.compile(
    r"file:/{1,3}|(?:^|[\s='\"(])(?:~/|\.{1,2}/|[a-z]:[\\/])"
    r"|\\\\[a-z0-9_.-]+\\"
    r"|/(?:Users|home|private|tmp|var|etc|opt|Volumes|root|mnt|proc|sys|dev)(?:/|\b)"
    r"|(?:^|[\s'\"/])(?:app/data|\.env|\.ssh|\.aws|\.codex|\.venv)(?:[/\s'\"]|$)"
    r"|(?:^|[\\/])\.\.(?:[\\/]|$)"
    r"|\blocalhost\b|\bhost\.docker\.internal\b|\b127(?:\.\d{1,3}){3}\b"
    r"|\b0\.0\.0\.0\b|\[?::1\]?(?=[:/\s]|$)",
    re.IGNORECASE,
)
ABSOLUTE_PATH = re.compile(r"(?:^|[\s='\"(])/[a-z0-9_.~-]+(?:/[^\s'\"<>]*)?", re.I)
PUBLIC_FACE_PATH = re.compile(r"/assets/headshots/(?:\{sleeper_id\}|[0-9]+)\.jpg\Z")
SECRET_FIELD = re.compile(
    r"(?:^|_)(?:api_?key|access_?token|refresh_?token|id_?token|auth_?token|"
    r"password|passwd|secret|client_?secret|secret_?key|private_?key|"
    r"service_?role|credential|credentials|authorization|cookie|set_cookie)(?:$|_)", re.I,
)
SECRET_VALUE = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"
    r"|\bBearer\s+\S+|\bBasic\s+[A-Za-z0-9+/]{12,}={0,2}"
    r"|\b(?:sk-|sb_secret_|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{12,}"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    r"|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    r"|[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@", re.I,
)


def _need(condition: Any, message: str) -> None:
    if not condition:
        raise ExportError(message)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_json(path: Path, label: str) -> tuple[dict, bytes]:
    _need(path.is_file() and not path.is_symlink(), f"{label} must be a regular file")
    raw = path.read_bytes()

    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, f"{label} contains duplicate JSON keys")
            result[key] = value
        return result

    def reject_constant(_value):
        raise ExportError(f"{label} contains a nonfinite JSON number")

    def finite_float(value):
        parsed = float(value)
        _need(math.isfinite(parsed), f"{label} contains a nonfinite JSON number")
        return parsed

    try:
        document = json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant,
                              parse_float=finite_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ExportError(f"{label} is not valid UTF-8 JSON") from exc
    _need(isinstance(document, dict), f"{label} must be a JSON object")
    return document, raw


def _assert_public(value: Any, label: str) -> None:
    """Fail closed on recognizable hazards, without logging their values or keys."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"([a-z])([A-Z])", r"\1_\2", key)
            normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized)
            _need(not SECRET_FIELD.search(normalized), f"{label} contains a credential-like field")
            _assert_public(key, label)
            _assert_public(child, label)
    elif isinstance(value, list):
        for child in value:
            _assert_public(child, label)
    elif isinstance(value, str):
        decoded = value
        for _ in range(3):
            decoded = unquote(decoded)
        public_path = PUBLIC_FACE_PATH.fullmatch(decoded) is not None
        _need(not PRIVATE_MARKER.search(decoded), f"{label} contains a private path or local host marker")
        _need(public_path or not ABSOLUTE_PATH.search(decoded), f"{label} contains an unreviewed absolute path")
        _need(not SECRET_VALUE.search(decoded), f"{label} contains a credential-like value")


def _board_copy(board: dict) -> tuple[dict, dict[str, int]]:
    result = copy.deepcopy(board)
    _need(result.get("kind") == "dg.read-model.bundle" and result.get("bundle_version") == 1,
          "board has an unsupported schema")
    try:
        available = result["payloads"]["available"]
        counts = dict.fromkeys(REMOVED_METADATA, 0)
        provenance = available["source"].get("provenance", {})
        if "argv" in provenance:
            del provenance["argv"]
            counts[REMOVED_METADATA[0]] = 1
        estimates_source = available.get("starting_estimates", {}).get("source", {})
        if "run_dir" in estimates_source:
            del estimates_source["run_dir"]
            counts[REMOVED_METADATA[1]] = 1
        for row in available["rows"]:
            forecast = row.get("forecast")
            if isinstance(forecast, dict) and "source_csv" in forecast:
                del forecast["source_csv"]
                counts[REMOVED_METADATA[2]] += 1
    except (KeyError, TypeError, AttributeError) as exc:
        raise ExportError("board is missing its expected payload structure") from exc
    _assert_public(result, "board")
    return result, counts


def _validate_reading(board: dict, view: dict) -> dict:
    _need(view.get("schema_version") == "track_record.view.v1" and view.get("status") == "available",
          "track record must be an available reading")
    selected = view.get("selected")
    snapshot = board.get("snapshot")
    _need(isinstance(selected, dict) and isinstance(snapshot, dict), "reading identity is missing")
    _need(isinstance(selected.get("snapshot_id"), str) and HEX64.fullmatch(selected["snapshot_id"]),
          "selected snapshot has no valid identity")
    _need(view.get("snapshots") == [selected], "snapshot index must describe exactly the selected reading")
    source = selected.get("source")
    _need(isinstance(source, dict) and set(source) == set(SOURCE_FIELDS), "selected source identity is incomplete")
    for key in SOURCE_FIELDS:
        _need(isinstance(source[key], str) and source[key] and source[key] == snapshot.get(key),
              "selected source identity does not match the board")
        if key.endswith("sha256"):
            _need(HEX64.fullmatch(source[key]), "source identity contains an invalid hash")
    for key in DATE_FIELDS:
        _need(isinstance(selected.get(key), str) and selected[key] and selected[key] == snapshot.get(key),
              "selected source dates do not match the board")
    _need(isinstance(selected.get("years"), list) and selected["years"]
          and selected["years"] == board.get("basis", {}).get("years"),
          "selected forecast years do not match the board")
    for payload in board["payloads"].values():
        _need(isinstance(payload, dict) and isinstance(payload.get("source"), dict),
              "board payload has no source identity")
        for key, value in payload["source"].items():
            if key in snapshot:
                _need(value == snapshot[key], "board payload source identity does not match its snapshot")
    return source


def _image_mime(content: bytes) -> str:
    """Recognize raster containers from bytes and reject missing/truncated chunks.

    This is container validation, not pixel decoding or image transformation.
    """
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        position, kinds = 8, []
        while position + 12 <= len(content):
            size = struct.unpack_from(">I", content, position)[0]
            end = position + 12 + size
            _need(end <= len(content), "headshot has a truncated PNG chunk")
            kind = content[position + 4:position + 8]
            data = content[position + 8:end - 4]
            crc = struct.unpack_from(">I", content, end - 4)[0]
            _need(zlib.crc32(kind + data) == crc, "headshot has an invalid PNG checksum")
            if not kinds:
                _need(kind == b"IHDR" and size == 13 and all(struct.unpack_from(">II", data)),
                      "headshot has an invalid PNG header")
            kinds.append(kind)
            position = end
            if kind == b"IEND":
                _need(size == 0 and end == len(content) and b"IDAT" in kinds,
                      "headshot has an invalid PNG ending")
                return "image/png"
        raise ExportError("headshot has no complete PNG ending")
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        _need(len(content) >= 20 and struct.unpack_from("<I", content, 4)[0] + 8 == len(content),
              "headshot has an invalid WebP container length")
        position, has_frame = 12, False
        while position + 8 <= len(content):
            kind = content[position:position + 4]
            size = struct.unpack_from("<I", content, position + 4)[0]
            end = position + 8 + size
            _need(end + (size % 2) <= len(content), "headshot has a truncated WebP chunk")
            data = content[position + 8:end]
            if kind == b"VP8 ":
                _need(size >= 10 and data[3:6] == b"\x9d\x01\x2a", "headshot has an invalid WebP frame")
                has_frame = True
            elif kind == b"VP8L":
                _need(size >= 5 and data[0] == 0x2f, "headshot has an invalid lossless WebP frame")
                has_frame = True
            position = end + (size % 2)
        _need(position == len(content) and has_frame, "headshot has no complete WebP frame")
        return "image/webp"
    if content.startswith(b"\xff\xd8\xff"):
        _need(content.endswith(b"\xff\xd9"), "headshot has an incomplete JPEG container")
        position, has_frame = 2, False
        while position + 4 <= len(content):
            _need(content[position] == 0xff, "headshot has an invalid JPEG marker")
            while position < len(content) and content[position] == 0xff:
                position += 1
            _need(position + 3 <= len(content), "headshot has a truncated JPEG marker")
            marker = content[position]
            size = struct.unpack_from(">H", content, position + 1)[0]
            end = position + 1 + size
            _need(size >= 2 and end <= len(content), "headshot has a truncated JPEG segment")
            data = content[position + 3:end]
            if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                _need(size >= 11 and all(struct.unpack_from(">HH", data, 1))
                      and data[5] > 0 and size == 8 + 3 * data[5],
                      "headshot has an invalid JPEG frame")
                has_frame = True
            if marker == 0xda:
                _need(has_frame and size >= 8 and data[0] > 0 and size == 6 + 2 * data[0]
                      and end < len(content) - 2, "headshot has an invalid JPEG scan")
                return "image/jpeg"
            position = end
        raise ExportError("headshot has no complete JPEG frame and scan")
    raise ExportError("headshot has an unsupported raster signature")


def export_release(*, board_path: Path, track_record_path: Path, headshots_dir: Path,
                   output_dir: Path, source_commit: str) -> dict:
    """Validate every input before reserving a never-overwritten output directory."""
    board_path, track_record_path = Path(board_path), Path(track_record_path)
    headshots_dir, output_dir = Path(headshots_dir), Path(output_dir)
    _need(not output_dir.exists() and not output_dir.is_symlink(), "output directory already exists")
    _need(output_dir.parent.is_dir(), "output parent directory must already exist")
    _need(not output_dir.resolve().is_relative_to(headshots_dir.resolve()),
          "output cannot be inside the source headshots directory")
    _need(re.fullmatch(r"[a-f0-9]{40}", source_commit), "source commit must be an explicit full Git SHA")
    original_board, board_bytes = _read_json(board_path, "board")
    original_view, view_bytes = _read_json(track_record_path, "track record")
    board, removed = _board_copy(original_board)
    source = _validate_reading(board, original_view)
    # Check before replacing Save as well, so an unfamiliar private field is never
    # silently removed by the read-only capability transformation.
    _assert_public(original_view, "track record")
    view = copy.deepcopy(original_view)
    view["save_capability"] = copy.deepcopy(SAVE_CAPABILITY)
    assets = [("dg-bundle.json", _json_bytes(board), "application/json"),
              ("track-record.json", _json_bytes(view), "application/json")]
    _need(headshots_dir.is_dir() and not headshots_dir.is_symlink(), "headshots must be an explicit regular directory")
    referenced = board.get("identity", {}).get("ids")
    _need(isinstance(referenced, list) and referenced
          and all(isinstance(value, str) and NUMERIC_ID.fullmatch(value) for value in referenced),
          "board headshot identities must be numeric strings")
    _need(len(referenced) == len(set(referenced)), "board headshot identities contain duplicates")
    image_ids = set()
    for path in sorted(headshots_dir.iterdir()):
        _need(path.is_file() and not path.is_symlink() and path.suffix == ".jpg"
              and NUMERIC_ID.fullmatch(path.stem), "headshots contain a nonnumeric, nonregular or unsupported file")
        _need(path.stem not in image_ids, "headshot directory contains duplicate identities")
        image_ids.add(path.stem)
        raw = path.read_bytes()
        assets.append((f"headshots/{path.name}", raw, _image_mime(raw)))
    _need(set(referenced) <= image_ids, "one or more referenced headshots are missing")
    manifest = {
        "schema_version": "dg.delivery-assets.v1", "source_commit": source_commit,
        "snapshot_id": view["selected"]["snapshot_id"], "snapshot": board["snapshot"],
        "source": {"board_bundle_sha256": _sha(board_bytes),
                   "track_record_view_sha256": _sha(view_bytes), "identity": source},
        "transformations": {"removed_board_metadata_counts": removed, "save_capability": SAVE_CAPABILITY},
        "headshots": {"count": len(image_ids), "referenced_count": len(referenced),
                      "extra_ids": sorted(image_ids - set(referenced))},
        "asset_count": len(assets),
        "assets": [{"path": name, "bytes": len(raw), "sha256": _sha(raw), "content_type": mime}
                   for name, raw, mime in assets],
    }
    _assert_public(manifest, "manifest")
    try:
        output_dir.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise ExportError("output directory already exists") from exc
    (output_dir / "headshots").mkdir()
    for name, raw, _mime in assets:
        with (output_dir / name).open("xb") as destination:
            destination.write(raw)
    with (output_dir / "asset-manifest.json").open("xb") as destination:
        destination.write(_json_bytes(manifest))
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--track-record", type=Path, required=True)
    parser.add_argument("--headshots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True,
                        help="reviewed integration source commit, not the later hosted consumer commit")
    args = parser.parse_args(argv)
    try:
        manifest = export_release(board_path=args.board, track_record_path=args.track_record,
                                  headshots_dir=args.headshots, output_dir=args.output,
                                  source_commit=args.source_commit)
    except (ValueError, OSError, RecursionError, OverflowError) as exc:
        # OSError paths and parser context may themselves contain private values.
        message = str(exc) if isinstance(exc, ExportError) else "input/output or JSON processing failed"
        print(f"Export refused: {message}", file=sys.stderr)
        return 1
    print(json.dumps({"asset_count": manifest["asset_count"], "headshot_count": manifest["headshots"]["count"],
                      "snapshot_id": manifest["snapshot_id"],
                      "manifest_sha256": _sha((args.output / "asset-manifest.json").read_bytes())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
