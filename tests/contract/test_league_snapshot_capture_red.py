"""F1 RED: scheduled, immutable, marker-pinned league capture.

No test in this module reads the live gitignored runtime store or calls Sleeper.
The production module is deliberately absent on main: each case is red until the
ratified capture contract is implemented.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = (
    "snapshot.json",
    "coverage.json",
    "team_posture.json",
    "team_value_matrix.json",
    "roster_cut_report.json",
    "provenance.json",
)
TRACKED_SEEDS = (
    "app/data/league_snapshots/sleeper_universe_snapshot_latest.json",
    "app/data/valuation/team_posture_latest.json",
    "app/data/valuation/team_value_matrix_latest.json",
    "app/data/valuation/roster_cut_report_latest.json",
)
FIXED_TIME = datetime(2026, 7, 15, 13, 20, tzinfo=timezone.utc)


def _module():
    return importlib.import_module("scripts.run_league_snapshot_capture")


def _snapshot(*, players: list[str] | None = None) -> dict:
    return {
        "rosters": [{"roster_id": 1, "players": players or ["101", "102"]}],
        "players": {player_id: {"player_id": player_id} for player_id in players or ["101", "102"]},
    }


def _derived(_: dict) -> dict:
    return {
        "coverage.json": {"decision_supported": False},
        "team_posture.json": {"decision_supported": False, "teams": []},
        "team_value_matrix.json": {"decision_supported": False, "teams": []},
        "roster_cut_report.json": {"decision_supported": False, "roster_cut_report": {}},
        "provenance.json": {"decision_supported": False},
    }


def _run(module, root: Path, *, run_id: str = "run-a", fetch=None, derive=None, **kwargs):
    return module.run_capture(
        fetch_league_state=fetch or _snapshot,
        derive_chain=derive or _derived,
        runtime_root=root,
        clock=lambda: FIXED_TIME,
        run_id=run_id,
        **kwargs,
    )


def _marker(root: Path) -> dict:
    return json.loads((root / "ready_latest.json").read_text(encoding="utf-8"))


def _seed_paths(tmp_path: Path) -> dict[str, Path]:
    seeds = {}
    for name in ARTIFACTS:
        path = tmp_path / "seeds" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"seed": True, "decision_supported": False}))
        seeds[name] = path
    return seeds


def test_f1_happy_path_writes_immutable_digest_verified_marker_last(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    _run(module, root)
    marker = _marker(root)
    assert marker["run_id"] == "run-a"
    assert marker["source_captured_at"] == FIXED_TIME.isoformat()
    assert tuple(marker["artifacts"]) == ARTIFACTS
    for name in ARTIFACTS:
        payload = root / "runs" / "run-a" / name
        assert payload.is_file()
        assert marker["sha256"][name] == hashlib.sha256(payload.read_bytes()).hexdigest()


def test_f2_derivation_failure_never_advances_marker_and_preserves_prior_run(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    _run(module, root, run_id="prior")
    with pytest.raises(Exception, match="derive"):
        _run(module, root, run_id="bad", derive=lambda _: (_ for _ in ()).throw(ValueError("derive")))
    assert _marker(root)["run_id"] == "prior"
    assert "failed:" in (root / "capture_status_latest.json").read_text(encoding="utf-8")


def test_f3_digest_mismatch_falls_to_seeds_without_mixing(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    seeds = _seed_paths(tmp_path)
    _run(module, root)
    (root / "runs" / "run-a" / "snapshot.json").write_text("tampered")
    loaded = module.load_league_set(root, seeds)
    assert loaded.caveat == "league_snapshot_seed_fallback"
    assert set(loaded.paths.values()) == set(seeds.values())


def test_f4_absent_marker_falls_to_seeds(tmp_path: Path) -> None:
    module = _module()
    seeds = _seed_paths(tmp_path)
    loaded = module.load_league_set(tmp_path / "runtime", seeds)
    assert loaded.caveat == "league_snapshot_seed_fallback"


@pytest.mark.parametrize("bad_marker", ["{", "[]", json.dumps({"run_id": 7})])
def test_f5_malformed_marker_fails_closed(tmp_path: Path, bad_marker: str) -> None:
    module = _module()
    root = tmp_path / "runtime"
    root.mkdir()
    seeds = _seed_paths(tmp_path)
    (root / "ready_latest.json").write_text(bad_marker)
    assert module.load_league_set(root, seeds).caveat == "league_snapshot_seed_fallback"


def test_f6_missing_marker_member_rejects_whole_run(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    seeds = _seed_paths(tmp_path)
    _run(module, root)
    (root / "runs" / "run-a" / "team_posture.json").unlink()
    assert module.load_league_set(root, seeds).caveat == "league_snapshot_seed_fallback"


def test_f7_duplicate_run_id_rejects_without_overwrite(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    _run(module, root)
    with pytest.raises(Exception, match="run_id_conflict"):
        _run(module, root)
    assert _marker(root)["run_id"] == "run-a"


@pytest.mark.parametrize(
    "payload",
    [
        {"rosters": []},
        {"rosters": "wrong"},
        {"rosters": [{"players": []}], "players": {}},
    ],
)
def test_f8_invalid_sleeper_payload_fails_before_derivation(tmp_path: Path, payload: dict) -> None:
    module = _module()
    called = False
    def deriver(_: dict) -> dict:
        nonlocal called
        called = True
        return _derived({})
    with pytest.raises(Exception, match="sleeper_payload_invalid"):
        _run(module, tmp_path / "runtime", fetch=lambda: payload, derive=deriver)
    assert called is False


def test_f9_capture_never_mutates_tracked_seed_paths_and_runtime_is_ignored(
    tmp_path: Path,
) -> None:
    module = _module()
    before = {p: (REPO_ROOT / p).read_bytes() for p in TRACKED_SEEDS}
    _run(module, tmp_path / "runtime")
    assert {p: (REPO_ROOT / p).read_bytes() for p in TRACKED_SEEDS} == before

    # Probe the real ignore grammar in an isolated git repository, never by
    # writing to the shared checkout or a live runtime artifact.
    repo = tmp_path / "ignore-fixture"
    repo.mkdir()
    (repo / ".gitignore").write_text((REPO_ROOT / ".gitignore").read_text())
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    candidate = "app/data/league_runtime/runs/example/snapshot.json"
    assert subprocess.run(
        ["git", "check-ignore", "-q", candidate], cwd=repo, check=False
    ).returncode == 0


def test_f10_loader_returns_one_marker_pinned_run_only(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    seeds = _seed_paths(tmp_path)
    _run(module, root)
    (root / "runs" / "other").mkdir(parents=True)
    loaded = module.load_league_set(root, seeds)
    assert set(loaded.run_ids.values()) == {"run-a"}


def test_f11_payload_invalid_reason_wins_over_deriver_error(tmp_path: Path) -> None:
    module = _module()
    with pytest.raises(Exception, match="sleeper_payload_invalid"):
        _run(module, tmp_path / "runtime", fetch=lambda: {"rosters": []}, derive=lambda _: (_ for _ in ()).throw(ValueError("derive")))


def test_f12_backup_manifest_covers_runtime_runs() -> None:
    manifest = json.loads((REPO_ROOT / "app/config/backup_manifest.json").read_text())
    paths = {item.get("path") for section in ("required", "optional") for item in manifest.get(section, [])}
    assert "app/data/league_runtime/runs" in paths


def test_f13_capture_never_introduces_decision_supported_true(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    _run(module, root)
    assert "true" not in "".join((root / "runs" / "run-a" / name).read_text().lower() for name in ARTIFACTS)


def test_f14_unresolved_identity_discloses_below_threshold_and_fails_at_threshold(tmp_path: Path) -> None:
    module = _module()
    config = tmp_path / "league_capture_config.json"
    config.write_text(json.dumps({"schema_version": "league_capture.v1", "unresolved_threshold_bp": 500, "rationale": "test"}))
    below = _snapshot(players=[str(i) for i in range(360)])
    for i in range(17):
        below["players"].pop(str(i))
    below_result = _run(module, tmp_path / "below", fetch=lambda: below, config_path=config)
    provenance = json.loads(below_result.paths["provenance.json"].read_text())
    assert provenance["identity"] == {
        "total_rostered": 360,
        "unresolved_count": 17,
        "unresolved_threshold_bp": 500,
    }
    assert _marker(tmp_path / "below")["unresolved_count"] == 17
    at = _snapshot(players=[str(i) for i in range(360)])
    for i in range(18):
        at["players"].pop(str(i))
    with pytest.raises(Exception, match="sleeper_identity_suspect"):
        _run(module, tmp_path / "at", fetch=lambda: at, config_path=config)


def test_f14_real_snapshot_player_rows_resolve_and_disclose_identity(tmp_path: Path) -> None:
    """The production Phase-17 snapshot has a list of identity rows, not an ID map."""
    module = _module()
    config = tmp_path / "league_capture_config.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": "league_capture.v1",
                "unresolved_threshold_bp": 500,
                "rationale": "test",
            }
        )
    )
    player_ids = [str(i) for i in range(360)]
    payload = {
        "rosters": [{"roster_id": 1, "players": player_ids}],
        "players": [
            {
                "sleeper_player_id": player_id,
                "identity_status": "unresolved" if int(player_id) < 17 else "sleeper_resolved",
            }
            for player_id in player_ids
        ],
    }
    result = _run(module, tmp_path / "runtime", fetch=lambda: payload, config_path=config)
    provenance = json.loads(result.paths["provenance.json"].read_text())
    assert provenance["identity"]["unresolved_count"] == 17


@pytest.mark.parametrize(
    "config_contents",
    [
        "{}",
        '{"schema_version":"league_capture.v1","unresolved_threshold_bp":true}',
        '{"schema_version":"league_capture.v1","unresolved_threshold_bp":-1}',
        "not-json",
    ],
)
def test_f14_invalid_config_fails_closed(tmp_path: Path, config_contents: str) -> None:
    module = _module()
    config = tmp_path / "league_capture_config.json"
    config.write_text(config_contents)
    with pytest.raises(Exception, match="league_capture_config_invalid"):
        _run(module, tmp_path / "runtime", config_path=config)


def test_f15_rename_failure_keeps_prior_marker(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "runtime"
    _run(module, root, run_id="prior")
    with pytest.raises(Exception, match="publish"):
        _run(module, root, run_id="next", rename=lambda *_: (_ for _ in ()).throw(OSError("publish")))
    assert _marker(root)["run_id"] == "prior"


@pytest.mark.parametrize("member", ["../snapshot.json", "/tmp/x", "extra.json"])
def test_f16_path_escape_or_noncanonical_set_rejects_marker(tmp_path: Path, member: str) -> None:
    module = _module()
    root = tmp_path / "runtime"
    seeds = _seed_paths(tmp_path)
    _run(module, root)
    marker = _marker(root)
    marker["artifacts"][0] = member
    (root / "ready_latest.json").write_text(json.dumps(marker))
    assert module.load_league_set(root, seeds).caveat == "league_snapshot_seed_fallback"


@pytest.mark.parametrize("run_id", ["../escaped", "/tmp/escaped", ".hidden", "a/b", "a\\b"])
def test_f16_run_id_escape_rejects_publish_and_marker_load(tmp_path: Path, run_id: str) -> None:
    module = _module()
    root = tmp_path / "runtime"
    seeds = _seed_paths(tmp_path)
    with pytest.raises(Exception, match="run_id_invalid"):
        _run(module, root, run_id=run_id)
    assert not (tmp_path / "escaped").exists()

    root.mkdir(exist_ok=True)
    (root / "ready_latest.json").write_text(
        json.dumps({"run_id": run_id, "artifacts": list(ARTIFACTS), "sha256": {}})
    )
    assert module.load_league_set(root, seeds).caveat == "league_snapshot_seed_fallback"


@pytest.mark.parametrize(
    "clock",
    [
        lambda: datetime(2026, 7, 15, 9, 20),
        lambda: datetime(2026, 7, 15, 9, 20, tzinfo=timezone(timedelta(hours=-4))),
    ],
)
def test_f1_source_clock_must_be_utc(tmp_path: Path, clock) -> None:
    module = _module()
    with pytest.raises(Exception, match="clock_.*rejected"):
        module.run_capture(
            fetch_league_state=_snapshot,
            derive_chain=_derived,
            runtime_root=tmp_path / "runtime",
            clock=clock,
            run_id="run-a",
        )


def test_f2_artifact_serialization_failure_records_named_status(tmp_path: Path) -> None:
    module = _module()
    bad = _derived({})
    bad["coverage.json"] = {"cannot_serialize": object()}
    with pytest.raises(TypeError):
        _run(module, tmp_path / "runtime", derive=lambda _: bad)
    status = json.loads((tmp_path / "runtime" / "capture_status_latest.json").read_text())
    assert status["status"] == "failed:artifact_write_error"
    assert not (tmp_path / "runtime" / "ready_latest.json").exists()


def test_f17_legacy_direct_readers_are_banned_outside_allowed_producers() -> None:
    module = _module()
    assert module.assert_no_legacy_direct_readers(repo_root=REPO_ROOT) is None
