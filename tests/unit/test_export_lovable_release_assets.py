"""A hosted copy preserves the reading while excluding private delivery metadata."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import struct
import zlib
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/export_lovable_release_assets.py"
SPEC = importlib.util.spec_from_file_location("release_exporter", SCRIPT)
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)
COMMIT = "a" * 40


def png() -> bytes:
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\xff\0\0")) + chunk(b"IEND", b""))


@pytest.fixture
def inputs(tmp_path):
    source = {
        "report_run": "20260906T214512Z", "report_sha256": "1" * 64,
        "market_sha256": "2" * 64, "league_sha256": "3" * 64,
        "catalog_run": "20260907T013635Z", "catalog_content_sha256": "4" * 64,
    }
    dates = {"forecast_date": "2026-09-06", "market_as_of": "2026-09-06T13:00:00Z",
             "ownership_as_of": "2026-09-06T14:00:00Z"}
    board = {
        "kind": "dg.read-model.bundle", "bundle_version": 1,
        "snapshot": {**source, **dates}, "basis": {"years": [2026, 2027]},
        "payloads": {
            "market_ranks": {"source": {**source, **dates}, "rows": [
                {"name": "A", "model_value": 17.125, "market_value": None,
                 "our_rank": 1, "market_rank": None}]},
            "comparison": {"source": source.copy()},
            "available": {
                "source": {"report_run": source["report_run"], "provenance": {
                    "argv": ["producer.py", "--input", "/Users/private/raw.csv"],
                    "script": "scripts/build_football_report.py", "git_head": COMMIT}},
                "starting_estimates": {"source": {
                    "run_dir": "/private/tmp/run", "sha256": "5" * 64,
                    "coverage_run": {"run_dir": "runs/20260907T010020Z/dg165_cold_start_coverage"}}},
                "rows": [{"sleeper_id": "12", "forecast": {"value": -0.0,
                          "source_csv": "/Users/private/forecast.csv", "source": "nflverse / PPR",
                          "source_url": "https://github.com/nflverse/nflverse-data/releases"}},
                         {"sleeper_id": "34", "forecast": None, "now_points": None}],
            },
        },
        "identity": {"path_template": "/assets/headshots/{sleeper_id}.jpg", "ids": ["12", "34"]},
    }
    selected = {"snapshot_id": "f" * 64, "source": source, **dates,
                "years": [2026, 2027], "counts": {"available": 2},
                "evaluation_status": "ungraded"}
    view = {
        "schema_version": "track_record.view.v1", "status": "available", "reason": None,
        "selected": selected, "snapshots": [copy.deepcopy(selected)],
        "production": {"state": "not_ready", "result": None, "observations": [
            {"forecast": 17.125, "outcome": None, "error": None, "name": "A"}]},
        "market": {"state": "not_registered", "result": None},
        "save_capability": {"enabled": True, "reason": None, "expected": source.copy()},
    }
    board_file, view_file, images = tmp_path / "board.json", tmp_path / "view.json", tmp_path / "faces"
    board_file.write_text(json.dumps(board))
    view_file.write_text(json.dumps(view))
    images.mkdir()
    for name in ("12.jpg", "34.jpg"):
        (images / name).write_bytes(png())
    return board_file, view_file, images, board, view


def run_export(inputs, output):
    return exporter.export_release(board_path=inputs[0], track_record_path=inputs[1],
                                   headshots_dir=inputs[2], output_dir=output, source_commit=COMMIT)


def rewrite(path, document):
    path.write_text(json.dumps(document))


def test_export_preserves_values_and_sources_removes_only_known_metadata(inputs, tmp_path):
    original_bytes = [path.read_bytes() for path in inputs[:2]]
    expected = copy.deepcopy(inputs[3])
    del expected["payloads"]["available"]["source"]["provenance"]["argv"]
    del expected["payloads"]["available"]["starting_estimates"]["source"]["run_dir"]
    del expected["payloads"]["available"]["rows"][0]["forecast"]["source_csv"]
    output = tmp_path / "release"
    run_export(inputs, output)
    delivered = json.loads((output / "dg-bundle.json").read_bytes())
    assert delivered == expected
    assert b'-0.0' in (output / "dg-bundle.json").read_bytes()
    assert [path.read_bytes() for path in inputs[:2]] == original_bytes
    assert "argv" in inputs[3]["payloads"]["available"]["source"]["provenance"]


@pytest.mark.parametrize("extra", [
    {"new_source": "/Users/someone/unreviewed.csv"},
    {"new_source": "cache stored in /private/tmp/model.pkl"},
    {"new_source": "C:\\Users\\someone\\private.csv"},
    {"new_source": "http://localhost:8000/private"},
    {"new_source": "http://127.0.0.1:8080"},
    {"new_source": "file:///home/someone/archive.json"},
    {"new_source": "%2FUsers%2Fsomeone%2Fprivate.csv"},
    {"new_source": "app/data/private/archive.json"},
    {"new_source": "runs/../../unreviewed.csv"},
    {"api_key": "FAKE_TEST_CREDENTIAL_DO_NOT_PRINT"},
    {"comment": "Bearer FAKE_TEST_CREDENTIAL_DO_NOT_PRINT"},
])
def test_unreviewed_private_or_credential_content_refuses_without_output(inputs, tmp_path, extra):
    inputs[3]["payloads"]["comparison"].update(extra)
    rewrite(inputs[0], inputs[3])
    output = tmp_path / "refused"
    with pytest.raises(exporter.ExportError) as error:
        run_export(inputs, output)
    assert not output.exists()
    assert "FAKE_TEST_CREDENTIAL" not in str(error.value)
    assert "someone" not in str(error.value)


@pytest.mark.parametrize("change", ["source", "date", "years", "snapshot_list", "payload_source"])
def test_mismatched_reading_refuses(inputs, tmp_path, change):
    if change == "source":
        inputs[4]["selected"]["source"]["report_sha256"] = "0" * 64
    elif change == "date":
        inputs[4]["selected"]["forecast_date"] = "2025-09-06"
    elif change == "years":
        inputs[4]["selected"]["years"] = [2025, 2026]
    elif change == "snapshot_list":
        inputs[4]["snapshots"][0]["snapshot_id"] = "0" * 64
    else:
        inputs[3]["payloads"]["market_ranks"]["source"]["report_sha256"] = "0" * 64
    rewrite(inputs[0], inputs[3])
    rewrite(inputs[1], inputs[4])
    with pytest.raises(exporter.ExportError):
        run_export(inputs, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_track_record_changes_only_save_capability(inputs, tmp_path):
    expected = copy.deepcopy(inputs[4])
    expected["save_capability"] = {
        "enabled": False, "reason": "Saving new readings is available in the Mac preview.", "expected": None,
    }
    output = tmp_path / "release"
    run_export(inputs, output)
    assert json.loads((output / "track-record.json").read_bytes()) == expected
    assert inputs[4]["save_capability"]["enabled"] is True


def test_manifest_replays_exact_bytes_and_reports_magic_mime_and_extra_images(inputs, tmp_path):
    # A small valid lossless WebP container, deliberately stored as .jpg like the real cache.
    import base64
    webp = base64.b64decode("UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==")
    (inputs[2] / "34.jpg").write_bytes(webp)
    (inputs[2] / "56.jpg").write_bytes(png())
    output = tmp_path / "release"
    run_export(inputs, output)
    manifest = json.loads((output / "asset-manifest.json").read_bytes())
    assets = {asset["path"]: asset for asset in manifest["assets"]}
    assert manifest["schema_version"] == "dg.delivery-assets.v1"
    assert manifest["source_commit"] == COMMIT
    assert manifest["snapshot_id"] == inputs[4]["selected"]["snapshot_id"]
    assert manifest["snapshot"] == inputs[3]["snapshot"]
    assert manifest["asset_count"] == len(assets) == 5
    assert manifest["headshots"]["extra_ids"] == ["56"]
    assert assets["headshots/12.jpg"]["content_type"] == "image/png"
    assert assets["headshots/34.jpg"]["content_type"] == "image/webp"
    assert (output / "headshots/34.jpg").read_bytes() == webp
    for name, asset in assets.items():
        content = (output / name).read_bytes()
        assert asset["bytes"] == len(content)
        assert asset["sha256"] == hashlib.sha256(content).hexdigest()
    assert manifest["source"]["board_bundle_sha256"] == hashlib.sha256(inputs[0].read_bytes()).hexdigest()
    assert manifest["source"]["track_record_view_sha256"] == hashlib.sha256(inputs[1].read_bytes()).hexdigest()
    assert str(tmp_path) not in (output / "asset-manifest.json").read_text()
    second = tmp_path / "repeat"
    run_export(inputs, second)
    assert {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()} == {
        str(p.relative_to(second)): p.read_bytes() for p in second.rglob("*") if p.is_file()}


@pytest.mark.parametrize("bad_image", [
    b"<svg>unsafe</svg>", b"\x89PNG\r\n\x1a\n", b"RIFF\x04\0\0\0WEBP",
    b"\xff\xd8\xff" + b"invalid-header" * 2 + b"\xff\xda" + b"\xff\xd9",
])
def test_unknown_or_truncated_images_refuse(inputs, tmp_path, bad_image):
    (inputs[2] / "12.jpg").write_bytes(bad_image)
    with pytest.raises(exporter.ExportError):
        run_export(inputs, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("problem", ["missing", "unexpected_file", "symlink"])
def test_untrusted_image_directory_refuses(inputs, tmp_path, problem):
    if problem == "missing":
        (inputs[2] / "12.jpg").unlink()
    elif problem == "unexpected_file":
        (inputs[2] / "archive.json").write_text("{}")
    else:
        (inputs[2] / "56.jpg").symlink_to(inputs[2] / "12.jpg")
    with pytest.raises(exporter.ExportError):
        run_export(inputs, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_existing_output_is_preserved_even_when_empty(inputs, tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(exporter.ExportError):
        run_export(inputs, output)
    assert list(output.iterdir()) == []
    sentinel = output / "sentinel"
    sentinel.write_bytes(b"do not overwrite")
    with pytest.raises(exporter.ExportError):
        run_export(inputs, output)
    assert [(p.name, p.read_bytes()) for p in output.iterdir()] == [("sentinel", b"do not overwrite")]


def test_json_duplicate_keys_and_nonfinite_numbers_refuse(inputs, tmp_path):
    for number, document in enumerate((b'{"kind":1,"kind":2}', b'{"value":NaN}', b'{"value":1e400}')):
        inputs[0].write_bytes(document)
        output = tmp_path / str(number)
        with pytest.raises(exporter.ExportError):
            run_export(inputs, output)
        assert not output.exists()
