"""T3.1 RED: concrete CLI entrypoint for FC forward capture.

The production driver is dependency-injected. T3.1 adds the executable wrapper
that supplies real httpx / UTC clock / sleep / jitter and scheduler-friendly
paths without importing the retired legacy collector.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from src.dynasty_genius.capture.fc_forward_capture_driver import SETTINGS_HASH
from src.dynasty_genius.capture.fc_forward_capture_store import FCForwardCaptureStore


def _load_cli():
    return importlib.import_module("scripts.run_fc_forward_capture")


class _Response:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self._body = body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "status error",
                request=httpx.Request("GET", "https://example.test/fc"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> object:
        return self._body


def _payload() -> dict:
    return {
        "players": [
            {
                "player": {
                    "id": 1,
                    "name": "Bijan Robinson",
                    "sleeperId": "9509",
                    "position": "RB",
                },
                "value": 10500,
                "overallRank": 1,
                "positionRank": 1,
                "trend30Day": -50,
            },
            {
                "player": {
                    "id": 2,
                    "name": "No Sleeper ID",
                    "sleeperId": None,
                    "position": "WR",
                },
                "value": 5000,
                "overallRank": 50,
                "positionRank": 10,
                "trend30Day": 0,
            },
        ]
    }


def test_preflight_prints_resolved_config_without_network_or_write(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = _load_cli()

    def fail_network(*_args, **_kwargs):
        raise AssertionError("preflight must not call the FantasyCalc endpoint")

    monkeypatch.setattr(cli.httpx, "get", fail_network)
    db_path = tmp_path / "capture.db"
    report_path = tmp_path / "reports" / "preflight.json"

    result = cli.main([
        "--db-path",
        str(db_path),
        "--report-path",
        str(report_path),
        "--preflight",
    ])

    assert result == 0
    out = json.loads(capsys.readouterr().out)
    assert out["preflight"] is True
    assert out["db_path"] == str(db_path)
    assert out["report_path"] == str(report_path)
    assert out["source"] == "fc_native"
    assert out["settings_hash"] == SETTINGS_HASH
    assert not db_path.exists()
    assert not report_path.exists()


def test_live_success_uses_real_httpx_shape_and_writes_section4_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cli = _load_cli()
    seen_urls: list[str] = []

    def fake_get(url: str, timeout: float) -> _Response:
        seen_urls.append(url)
        assert timeout > 0
        return _Response(200, _payload())

    monkeypatch.setattr(cli.httpx, "get", fake_get)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(cli.random, "random", lambda: 0.0)
    db_path = tmp_path / "capture.db"
    report_path = tmp_path / "nested" / "reports" / "capture.json"

    result = cli.main(["--db-path", str(db_path), "--report-path", str(report_path)])

    assert result == 0
    assert len(seen_urls) == 1
    report = json.loads(report_path.read_text())
    assert report["status"] == "ok"
    assert report["raw_entries_written"] == 2
    assert report["joinable_rows_written"] == 1
    assert report["missing_sleeper_count"] == 1
    assert report["duplicate_count"] == 0
    assert report["source"] == "fc_native"
    assert report["settings_hash"] == SETTINGS_HASH
    assert report["endpoint"] == seen_urls[0]
    assert report["payload_hash"]
    assert report["store_hash"]
    assert report["aborted_reason"] is None
    assert report["decision_supported"] is False

    store = FCForwardCaptureStore(db_path)
    assert len(store.get_raw_entries(report["snapshot_date"], "fc_native", SETTINGS_HASH)) == 2
    assert len(store.get_joinable_entries(report["snapshot_date"], "fc_native", SETTINGS_HASH)) == 1


@pytest.mark.parametrize("status_code", [429, 500])
def test_transient_non_200_exhaustion_writes_aborted_report_without_store_rows(
    tmp_path: Path,
    monkeypatch,
    status_code: int,
) -> None:
    cli = _load_cli()
    attempts: list[str] = []

    def fake_get(url: str, timeout: float) -> _Response:
        attempts.append(url)
        return _Response(status_code, {"error": "transient"})

    monkeypatch.setattr(cli.httpx, "get", fake_get)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(cli.random, "random", lambda: 0.0)
    db_path = tmp_path / "capture.db"
    report_path = tmp_path / "reports" / "aborted.json"

    result = cli.main(["--db-path", str(db_path), "--report-path", str(report_path)])

    assert result == 1
    assert len(attempts) == 3
    report = json.loads(report_path.read_text())
    assert report["status"] == "aborted"
    assert report["aborted_reason"] == f"retry_exhausted_http_{status_code}"
    assert report["raw_entries_written"] == 0
    assert report["joinable_rows_written"] == 0
    assert report["decision_supported"] is False
    assert FCForwardCaptureStore(db_path).get_raw_entries(
        report["snapshot_date"],
        "fc_native",
        SETTINGS_HASH,
    ) == []


def test_cli_does_not_import_retired_legacy_collector_or_store() -> None:
    cli = _load_cli()

    imported_modules = {
        getattr(value, "__name__", "")
        for value in vars(cli).values()
        if getattr(value, "__name__", "")
    }
    assert "scripts.snapshot_fantasycalc" not in imported_modules
    assert "src.dynasty_genius.eval.market_snapshot_store" not in imported_modules


def test_cli_loads_standalone_from_outside_repo(tmp_path: Path) -> None:
    script_path = Path("scripts/run_fc_forward_capture.py").resolve()
    probe = "\n".join(
        [
            "import importlib.util",
            "import os",
            "import pathlib",
            f"script_path = pathlib.Path({str(script_path)!r})",
            f"os.chdir({str(tmp_path)!r})",
            "spec = importlib.util.spec_from_file_location(",
            "    'run_fc_forward_capture_standalone', script_path",
            ")",
            "module = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(module)",
            "assert callable(module.main)",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
