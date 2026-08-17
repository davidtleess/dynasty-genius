"""TW14-QB1-1 green-review round-2 correction contracts (Claude-authored).

Pins the seven green-review fixes (G1–G7, Codex verdict `740e3da1…`) and the
G4 end-to-end composition (`scripts/run_qb1_study.py`). Offered to Codex for
adoption alongside its frozen execution RED — these rows are ADDITIVE and
change no frozen contract.

Everything here is hermetic: synthetic receipts, synthetic pools, injected
frames. NO real substrate is consumed and NO study result is computed — the
one full-composition row drives the entire pipeline on fixture data whose
honest outcome is ``unsupported_power`` everywhere. H2 QB rushing remains a
registered hypothesis UNDER TEST with no result.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import src.dynasty_genius.eval.qb_validation as qb
import tests.contract.qb_validation_study_matrix_contract as matrix_fixtures

runner = importlib.import_module("scripts.run_qb1_study")

PIN = qb.REGISTRATION_PIN
DATASETS = (
    "weekly",
    "season_summary",
    "players",
    "rosters",
    "ff_playerids",
    "draft_picks",
    "pbp",
)


def _reason(exc_info: pytest.ExceptionInfo[BaseException]) -> str:
    reason = getattr(exc_info.value, "reason", None)
    assert isinstance(reason, str) and reason
    return reason


def _registration() -> dict[str, Any]:
    return json.loads(
        Path("docs/validation/2026-07-21-qb-1-study-registration.json").read_text()
    )


def _receipt(
    tmp_path: Path, *, registration_pin: Any = PIN, pbp_rows: int = 1
) -> Path:
    """A structurally valid seven-dataset completion receipt under tmp.
    ``pbp_rows`` lets seam fixtures declare a multi-row pbp frame (R15: the
    admission row cross-check compares the loaded frame to the receipt)."""
    raw = tmp_path / "app/data/backtest/qb_validation/raw"
    datasets: dict[str, Any] = {}
    for name in DATASETS:
        snapshot = raw / name / f"{name}.parquet"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(name.encode())
        datasets[name] = {
            "snapshots": [
                {
                    "file": str(snapshot.relative_to(tmp_path)),
                    "rows": pbp_rows if name == "pbp" else 1,
                    "columns": 1,
                    "bytes": snapshot.stat().st_size,
                    "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                }
            ]
        }
    receipt: dict[str, Any] = {
        "finished_at": "2026-08-14T16:00:00Z",
        "nflreadpy_version": "fixture",
        "datasets": datasets,
    }
    if registration_pin is not None:
        receipt["registration_pin"] = registration_pin
    (raw / "fetch_manifest.json").write_text(json.dumps(receipt))
    return raw


# ── G1: the admit→load composition seam ────────────────────────────────────────


def _pool_frame_loader(path: Path) -> pd.DataFrame:
    """Fixture loader for the admit→load seam: pbp gets its pinned parse
    source columns (R15 — the seam now APPLIES the registered pbp parse, so
    a shapeless pbp frame refuses by name); every other dataset stays the
    minimal one-column frame."""
    if Path(path).name == "pbp.parquet":
        return pd.DataFrame(
            {"season_type": ["REG", "POST"], "posteam": ["KC", "SF"]}
        )
    return pd.DataFrame({"x": [1]})


def test_g1_seam_admits_receipt_shape_end_to_end(tmp_path: Path) -> None:
    """The real defect: both stages individually green, jointly unusable. The
    seam must carry a receipt-admitted pool THROUGH the unchanged F1 gate."""
    pool = qb.admit_and_load_validation_pool(
        _receipt(tmp_path, pbp_rows=2),
        repo_root=tmp_path,
        frame_loader=_pool_frame_loader,
    )
    assert set(pool) == set(DATASETS)
    for state in pool.values():
        assert state["status"] == "ok"
        assert state["metadata"]["completeness"] == "ok"
        assert state["metadata"]["raw_snapshot_path"]
        assert state["metadata"]["parser_version"]
    # R15: the pool's pbp frame is the PARSED form the registration's §11
    # describes — renamed, REG-only.
    parsed = pool["pbp"]["frame"]
    assert "offense_team" in parsed.columns
    assert "posteam" not in parsed.columns
    assert list(parsed["season_type"].unique()) == ["REG"]


def test_g1_seam_tamper_still_refuses_before_any_parse(tmp_path: Path) -> None:
    raw = _receipt(tmp_path)
    (raw / "weekly" / "weekly.parquet").write_bytes(b"tampered")
    calls = 0

    def frame_loader(_path: Path) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return pd.DataFrame({"x": [1]})

    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.admit_and_load_validation_pool(
            raw, repo_root=tmp_path, frame_loader=frame_loader
        )
    assert _reason(exc_info) == "source_snapshot_drift"
    assert calls == 0


def test_g1_seam_never_launders_unverified_completeness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the receipt's verified ``"complete"`` translates to ``"ok"`` — any
    other completeness passes through and refuses at the F1 gate."""

    def fake_admit(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        snapshot = tmp_path / "weekly.parquet"
        snapshot.write_bytes(b"x")
        # R15: pbp must be PARSEABLE so this test keeps exercising the
        # completeness-laundering seam it exists for — the ruled ordering
        # parses pbp before the F1 gate, so a shapeless pbp fake would refuse
        # on the parse instead of the laundering.
        return {
            name: {
                "status": "ok",
                "frame": (
                    pd.DataFrame({"season_type": ["REG"], "posteam": ["KC"]})
                    if name == "pbp"
                    else pd.DataFrame({"x": [1]})
                ),
                "rows": 1,
                "metadata": {
                    "raw_snapshot_path": str(snapshot),
                    "source_timestamp": "2026-08-14T16:00:00Z",
                    "parser_version": "fixture",
                    "completeness": "partial",
                    "sha256": "0" * 64,
                },
            }
            for name in DATASETS
        }

    monkeypatch.setattr(qb.execution, "admit_fetch_manifest", fake_admit)
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.admit_and_load_validation_pool(
            tmp_path, repo_root=tmp_path, frame_loader=lambda _p: None
        )
    assert _reason(exc_info) == "source_unavailable"
    assert "partial" in str(exc_info.value)


# ── G2: the receipt's registration pin binds admission ─────────────────────────


def test_g2_wrong_pin_refuses_before_hashing(tmp_path: Path) -> None:
    """A wrong pin refuses as registration drift — and BEFORE pass-1 hashing:
    the snapshot is tampered so hashing WOULD refuse as snapshot drift; the
    observed reason proves the pin gate fired first."""
    raw = _receipt(tmp_path, registration_pin="0" * 64)
    (raw / "weekly" / "weekly.parquet").write_bytes(b"tampered")
    calls = 0

    def frame_loader(_path: Path) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return pd.DataFrame({"x": [1]})

    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.admit_fetch_manifest(raw, repo_root=tmp_path, frame_loader=frame_loader)
    assert _reason(exc_info) == "registration_drift"
    assert calls == 0


def test_g2_missing_pin_refuses_named(tmp_path: Path) -> None:
    raw = _receipt(tmp_path, registration_pin=None)
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.admit_fetch_manifest(
            raw, repo_root=tmp_path, frame_loader=lambda _p: pd.DataFrame({"x": [1]})
        )
    assert _reason(exc_info) == "preregistration_missing"


# ── G3: the runner gates every publication ─────────────────────────────────────


def _run(
    tmp_path: Path, execute: Any, *, registration: dict[str, Any] | None = None
) -> tuple[dict[str, Any], Path]:
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    report = qb.run_qb1_study(
        execute=execute,
        output_path=destination,
        registration_hash=PIN,
        generated_at="2026-08-14T19:00:00Z",
        repo_root=tmp_path,
        registration=registration,
    )
    return report, destination


def _fold_metric_entry() -> dict[str, Any]:
    """One produced per-contrast fold-metric entry (CIs are registered at the
    pooled level only, so the per-fold ci names that state).

    R10: producer-coherent by construction — the pool meets the registered
    fold_min_evaluable_n floor (20) and paired_delta is written as the literal
    ``spearman_left - spearman_right`` expression, so the gate's exact
    producer-shaped reconciliation holds down to the float bit pattern."""
    return {
        "paired_delta": 0.1 - 0.2,
        "spearman_left": 0.1,
        "spearman_right": 0.2,
        "common_pool_n": 24,
        "ci": {"state": "pooled_level_only", "decision_supported": False},
        "decision_supported": False,
    }


def _pooled_delta_entry() -> dict[str, Any]:
    return {"pooled_delta": -0.01, "evaluable_folds": 0, "decision_supported": False}


def _complete_ok_payload(registration: dict[str, Any]) -> dict[str, Any]:
    """A GENUINELY registration-complete ok payload (R5-G1 replaced the prior
    shell-tolerant oracle: the deep runner gate now refuses anything less than
    the produced ANALYTICAL CONTENT — per-fold contrast-bound typed metrics,
    exact ridge-lane manifest keys, full case rows with lane results, both
    qualifying slices' 14-contrast pooled readouts, the four-contrast H5
    margin readout, and the computed F13 structures)."""
    model_ids = [
        spec["id"] for spec in registration["contrasts"] if spec["lane"] != "h5"
    ]
    h5_ids = [
        spec["id"] for spec in registration["contrasts"] if spec["lane"] == "h5"
    ]
    h5_seasons = set(registration["h5"]["folds"])
    margins = registration["h5"]["margin_sensitivity"]
    cases = [
        {
            "id": case_id,
            "player_name": case_id.replace("_", " ").title(),
            "gsis_id": f"00-{index:07d}",
            "fold": 2025,
            "scope_note": "second-season"
            if case_id in {"daniels_2025", "nix_2025"}
            else "registered case",
            "state": "reported",
            "lanes": {
                "h1": {
                    "state": "reported",
                    "y_pred": 15.0,
                    "y_true": 14.0,
                    "decision_supported": False,
                },
                "naive": {"state": "not_in_lane_pool", "decision_supported": False},
            },
            "decision_supported": False,
        }
        for index, case_id in enumerate(sorted(qb.execution.CASE_PANEL_IDS))
    ]
    comparisons = []
    for spec in registration["contrasts"]:
        row: dict[str, Any] = {
            "id": spec["id"],
            "lane": spec["lane"],
            "registered_direction": spec["direction"],
            "pooled_delta": -0.01,
            "ci95": [None, None],
            "p_perm": None,
            "adjusted_p": None,
            "excluded_folds": None,
            "support_status": "unsupported_power",
            "evaluable_folds": 0,
            "decision_supported": False,
        }
        if spec["lane"] == "h5":
            # R7-G1/R7-G2: a fully-computed coherent H5 row — the shipped
            # status function emits exactly (inconclusive, ni_met=False, [])
            # for this evidence, and 4 evaluable + 0 excluded reconciles with
            # the 4 fold rows carrying the contrast's metrics.
            row.update(
                ci95=[-0.05, 0.03],
                one_sided_lower_95=-0.06,
                p_ni=0.5,
                adjusted_p_ni=0.6,
                ni_met=False,
                support_status="inconclusive",
                flags=[],
                evaluable_folds=4,
                excluded_folds=[],
            )
        comparisons.append(row)
    return {
        "run_status": "ok",
        "inputs": {
            "snapshot_ids": ["s1"],
            "settings_hash": registration["scoring"]["settings_hash"],
            "matrix_version": "qb_validation_matrix.v1",
        },
        "disclosures": [
            {**row, "decision_supported": False}
            for row in registration["disclosures"]
        ],
        "folds": [
            {
                "test_season": season,
                "n_evaluable": 1,
                "attrition": {
                    "no_target_season": 0,
                    "rookie_no_priors": 0,
                    "cohort_ineligible_prior": 0,
                    "cohort_ineligible_unobserved": 0,
                    "manifest_missing": {
                        lane: 0 for lane in qb.execution.RIDGE_LANE_NAMES
                    },
                },
                "metrics_with_CIs": {
                    contrast_id: _fold_metric_entry()
                    for contrast_id in (
                        model_ids + (h5_ids if season in h5_seasons else [])
                    )
                },
                "flags": [],
                "decision_supported": False,
            }
            for season in registration["folds"]["test_seasons"]
        ],
        "comparisons": comparisons,
        "case_panel": cases,
        "sensitivity_panels": [
            {
                "id": "archetype_threshold",
                "binary_dual_threat_gate": {
                    "rule": "season rushing yards > 400 in any of the three "
                    "trailing seasons (shipped is_dual_threat; fixture)",
                    "threshold_yards": 400,
                    "per_fold": [
                        {
                            "test_season": season,
                            "n_evaluable": 1,
                            "dual_threat_count": 0,
                            "pocket_count": 1,
                            # R11 full-evidence disclosure: one row per
                            # evaluable player. An empty window is honest
                            # evidence of absence — base False, pocket, no
                            # boundary membership.
                            "evaluable_players": [
                                {
                                    "player_id": "qb-pocket",
                                    "window_seasons": [],
                                    "decision_supported": False,
                                }
                            ],
                            "boundary_case_count": 0,
                            "boundary_cases": [],
                            "flips_at_minus_1_ypg": 0,
                            "flips_at_plus_1_ypg": 0,
                            "decision_supported": False,
                        }
                        for season in registration["folds"]["test_seasons"]
                    ],
                    "decision_supported": False,
                },
                "continuous_rushing_moderator": {
                    "basis": "registered manifest h2 continuous rushing fields "
                    "(t-1); boundary players reported per fold (fixture)",
                    "decision_supported": False,
                },
                "boundary_cases_yards_per_game": [-1, 1],
                "decision_supported": False,
            },
            {
                "id": "qualifying_games",
                "unfiltered_primary": {
                    "min_qualifying_games": None,
                    "pooled_deltas": {
                        spec["id"]: _pooled_delta_entry()
                        for spec in registration["contrasts"]
                    },
                    "decision_supported": False,
                },
                "min_four_games": {
                    "min_qualifying_games": 4,
                    "pooled_deltas": {
                        spec["id"]: _pooled_delta_entry()
                        for spec in registration["contrasts"]
                    },
                    "decision_supported": False,
                },
                "decision_supported": False,
            },
            {
                "id": "h5_margin",
                "margins": list(margins),
                "readout": {
                    contrast_id: {
                        str(margin): {
                            "p_ni": 0.5,
                            "adjusted_p_ni": 0.6,
                            "ni_met": False,
                            "decision_supported": False,
                        }
                        for margin in margins
                    }
                    for contrast_id in h5_ids
                },
                "decision_supported": False,
            },
        ],
    }


def test_g3_no_verdict_payload_publishes_as_named_failure(tmp_path: Path) -> None:
    report, destination = _run(
        tmp_path, lambda: {"run_status": "ok", "decision_supported": True}
    )
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
    assert report["decision_supported"] is False
    assert json.loads(destination.read_text()) == report
    assert "comparisons" not in report


def test_g3_ok_without_blocks_and_unknown_keys_refuse(tmp_path: Path) -> None:
    for payload in (
        {"run_status": "ok", "decision_supported": False},
        {"run_status": "ok", "decision_supported": False, "extra_block": 1},
        {"run_status": "ok", "decision_supported": False, "generated_at": "spoofed"},
    ):
        report, _destination = _run(tmp_path, lambda payload=payload: payload)
        assert report["run_status"] == "failed"
        assert report["failure_reason"] == "report_schema_invalid"


def test_g3_ordinary_exception_becomes_named_terminal_artifact(
    tmp_path: Path,
) -> None:
    def explode() -> dict[str, Any]:
        raise ValueError("unexpected parse failure")

    report, destination = _run(tmp_path, explode)
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "execution_error"
    assert json.loads(destination.read_text()) == report


def test_g3_process_control_exceptions_are_never_converted(tmp_path: Path) -> None:
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"

    def interrupt() -> dict[str, Any]:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        qb.run_qb1_study(
            execute=interrupt,
            output_path=destination,
            registration_hash=PIN,
            generated_at="2026-08-14T19:00:00Z",
            repo_root=tmp_path,
        )
    assert not destination.exists()


def test_g3_valid_success_payload_is_stamped_validated_published(
    tmp_path: Path,
) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    report, destination = _run(tmp_path, lambda: payload, registration=registration)
    assert report["run_status"] == "ok"
    assert report["generated_at"] == "2026-08-14T19:00:00Z"
    assert report["registration_hash"] == PIN
    assert report["decision_supported"] is False
    assert report["disclosures"] == payload["disclosures"]
    qb.validate_report_output(json.loads(destination.read_text()))


def test_r3g1_ok_publication_without_registration_refuses(tmp_path: Path) -> None:
    """R3-G1: the registered-schema gate is a RUNNER INVARIANT — an ok payload
    with no registration object publishes as a named failed artifact."""
    payload = _complete_ok_payload(_registration())
    report, destination = _run(tmp_path, lambda: payload, registration=None)
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
    assert json.loads(destination.read_text()) == report


def test_r3g1_incomplete_ok_payload_refuses_at_the_runner(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    del payload["disclosures"]
    report, _destination = _run(tmp_path, lambda: payload, registration=registration)
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"

    payload = _complete_ok_payload(registration)
    payload["folds"][0]["flags"] = ["not_a_registered_fold_flag"]
    report, _destination = _run(tmp_path, lambda: payload, registration=registration)
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"


# ── G5: the occurrence-specific F33 wall ───────────────────────────────────────


def _wall_repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "app").mkdir(exist_ok=True)
    return tmp_path


def test_g5_validation_loader_call_site_now_trips(tmp_path: Path) -> None:
    repo = _wall_repo(tmp_path)
    leak = repo / "app/services/leak.py"
    leak.parent.mkdir(parents=True)
    leak.write_text(
        "from src.dynasty_genius.adapters.nflreadpy_qb_adapter "
        "import load_validation_weekly_stats\n"
        "RESULT = load_validation_weekly_stats([2025])\n"
    )
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.enforce_consumer_boundary(repo_root=repo)
    assert _reason(exc_info) == "consumer_boundary_violation"
    assert "loaders" in str(exc_info.value)


def test_g5_private_helper_prefix_never_false_positives(tmp_path: Path) -> None:
    repo = _wall_repo(tmp_path)
    clean = repo / "app/services/rookie_like.py"
    clean.parent.mkdir(parents=True)
    clean.write_text(
        "def _load_validation_report(pointer):\n    return pointer\n"
    )
    qb.enforce_consumer_boundary(repo_root=repo)


def test_g5_allowlist_is_class_specific_not_whole_file(tmp_path: Path) -> None:
    """The adapter may hold loaders + the raw root; a package import inside
    the SAME file still violates — no whole-file escape hatch."""
    repo = _wall_repo(tmp_path)
    adapter = repo / "src/dynasty_genius/adapters/nflreadpy_qb_adapter.py"
    adapter.parent.mkdir(parents=True)
    adapter.write_text(
        "def load_validation_weekly_stats(seasons):\n"
        "    return 'app/data/backtest/qb_validation'\n"
    )
    qb.enforce_consumer_boundary(repo_root=repo)

    adapter.write_text(
        adapter.read_text()
        + "import src.dynasty_genius.eval.qb_validation as qb\n"
    )
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.enforce_consumer_boundary(repo_root=repo)
    assert "package" in str(exc_info.value)


def test_g5_registry_may_name_raw_root_but_not_call_loaders(tmp_path: Path) -> None:
    repo = _wall_repo(tmp_path)
    registry = repo / "src/dynasty_genius/sources/source_registry.py"
    registry.parent.mkdir(parents=True)
    registry.write_text('NOTE = "app/data/backtest/qb_validation/raw"\n')
    qb.enforce_consumer_boundary(repo_root=repo)

    registry.write_text(
        registry.read_text() + "RESULT = load_validation_pbp([2025])\n"
    )
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.enforce_consumer_boundary(repo_root=repo)
    assert "loaders" in str(exc_info.value)


def test_g5_real_repo_is_clean_under_the_tightened_wall() -> None:
    """The wall is a live repo gate: the actual tree must hold no unsanctioned
    marker. This row is the continuous enforcement, not a fixture check."""
    qb.enforce_consumer_boundary(repo_root=Path(".").resolve())


# ── G6: H5 impossible-evidence refusals ────────────────────────────────────────


def _h5_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "lane": "h5",
        "folds": 4,
        "pooled_delta": 0.01,
        "ci95": [-0.02, 0.04],
        "one_sided_lower_95": -0.04,
        "p_ni": 0.04,
        "adjusted_p_ni": 0.08,
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "overrides",
    [
        {"adjusted_p_ni": -1.0},
        {"p_ni": 2.0},
        {"folds": 5},
        {"pooled_delta": 0.08, "ci95": [-0.20, -0.10]},
        {"pooled_delta": -0.08, "ci95": [0.10, 0.20]},
        {"ci95": [0.20, 0.10]},
    ],
)
def test_g6_impossible_h5_evidence_refuses_named(overrides: dict[str, Any]) -> None:
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.evaluate_power_and_status(_h5_payload(**overrides))
    assert _reason(exc_info) == "status_payload_malformed"


def test_g6_coherent_boundary_evidence_still_labels() -> None:
    result = qb.evaluate_power_and_status(_h5_payload())
    assert result["support_status"] == "market_noninferior"
    assert result["decision_supported"] is False


# ── G7: exact-cardinality pins ─────────────────────────────────────────────────


def test_g7_duplicate_case_row_refuses() -> None:
    rows = [
        {
            "id": case_id,
            "scope_note": "second-season"
            if case_id in {"daniels_2025", "nix_2025"}
            else "case",
            "decision_supported": False,
        }
        for case_id in sorted(qb.execution.CASE_PANEL_IDS)
    ]
    rows.append(dict(rows[-1]))
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.require_case_panel(rows)
    assert _reason(exc_info) == "case_panel_incomplete"


@pytest.mark.parametrize("joined", [101, -1, True])
def test_g7_impossible_join_cardinality_refuses(joined: Any) -> None:
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.validate_join_coverage(joined, 100, registration=_registration())
    assert _reason(exc_info) == "join_coverage_invalid"


def test_g7_full_coverage_boundary_admits() -> None:
    result = qb.validate_join_coverage(100, 100, registration=_registration())
    assert result["coverage"] == pytest.approx(1.0)


# ── G4: the end-to-end composition (hermetic) ──────────────────────────────────


def _hermetic_pool(tmp_path: Path) -> dict[str, Any]:
    """The shared study-matrix synthetic pool, enriched so all four ridge
    lanes materialize and the F10 case names resolve."""
    pool = matrix_fixtures._sources(tmp_path / "pool")
    weekly = pool["weekly"]["frame"]
    weekly.loc[weekly["position"] == "QB", "rushing_tds"] = 1
    players = pool["players"]["frame"].copy()
    players["position"] = "QB"
    case_rows = [
        {
            "gsis_id": f"case-{index}",
            "display_name": name,
            "birth_date": "1996-01-01",
            "college_name": "Example U",
            "position": "QB",
        }
        for index, name in enumerate(
            (
                "Jayden Daniels",
                "Bo Nix",
                "Baker Mayfield",
                "Anthony Richardson",
                "Drake Maye",
                "Josh Allen",
            )
        )
    ]
    pool["players"]["frame"] = pd.concat(
        [players, pd.DataFrame(case_rows)], ignore_index=True
    )
    return pool


def _h5_inputs(tmp_path: Path) -> dict[str, Any]:
    """Synthetic H5 inputs with REAL on-disk snapshot files and REAL hashes —
    the R2-G4 frozen-input gate verifies bytes, so fixtures must be bytes."""
    snapshots = []
    for season in (2021, 2022, 2023, 2024):
        path = tmp_path / f"values_{season}.csv"
        path.write_text(f"player,pos,value_2qb,fp_id\nveteran,QB,5000,{season}\n")
        snapshots.append(
            {
                "season": season,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "path": path,
            }
        )
    return {
        "crosswalk_entries": [
            {"fantasypros_id": "fp-1", "gsis_id": "veteran", "name": "veteran"}
        ],
        "crosswalk_observed_at": "2026-05-16T03:28:22Z",
        "dp_snapshots": snapshots,
        "dp_rows_by_season": {
            season: [{"fp_id": "fp-1", "dp_name": "veteran", "value_2qb": 5000.0}]
            for season in (2021, 2022, 2023, 2024)
        },
    }


def test_g4_composition_runs_end_to_end_and_publishes(tmp_path: Path) -> None:
    """The whole registered pipeline on synthetic data: labels → matrix →
    8 folds → H1–H4 + naive + gated H5 → 14 contrasts → seeded inference →
    statuses → panels → runner-validated atomic publication. The honest
    outcome on a starved synthetic pool is ``unsupported_power`` everywhere —
    the row asserts STRUCTURE and honesty, never a study result."""
    report_blocks = runner.compose_study(
        registration=_registration(),
        pool=_hermetic_pool(tmp_path),
        repo_root=tmp_path,
        **_h5_inputs(tmp_path),
    )
    assert report_blocks["run_status"] == "ok"
    # R2-G3: the registered schema rides every ok report.
    assert report_blocks["disclosures"] == [
        {**row, "decision_supported": False}
        for row in _registration()["disclosures"]
    ]
    for fold in report_blocks["folds"]:
        assert set(fold["attrition"]) == {
            "no_target_season",
            "rookie_no_priors",
            "cohort_ineligible_prior",
            "cohort_ineligible_unobserved",
            "manifest_missing",
        }
        assert isinstance(fold["metrics_with_CIs"], dict)
        assert isinstance(fold["flags"], list)
    statuses = {row["id"]: row["support_status"] for row in report_blocks["comparisons"]}
    assert set(statuses) == {f"c{index:02d}" for index in range(1, 15)}
    allowed = {
        "supported",
        "not_separable",
        "contradicted",
        "unsupported_power",
        "market_noninferior",
        "market_superior",
        "model_superior",
        "inconclusive",
    }
    assert set(statuses.values()) <= allowed
    assert {row["id"] for row in report_blocks["case_panel"]} == set(
        qb.execution.CASE_PANEL_IDS
    )
    assert [panel["id"] for panel in report_blocks["sensitivity_panels"]] == [
        "archetype_threshold",
        "qualifying_games",
        "h5_margin",
    ]

    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    published = qb.run_qb1_study(
        execute=lambda: report_blocks,
        output_path=destination,
        registration_hash=PIN,
        generated_at="2026-08-14T19:00:00Z",
        repo_root=tmp_path,
        registration=_registration(),
    )
    assert published["run_status"] == "ok"
    assert destination.exists()
    qb.validate_report_output(json.loads(destination.read_text()))


def test_g4_registration_tamper_refuses_at_first_touch(tmp_path: Path) -> None:
    tampered = _registration()
    tampered["inference"]["fdr_q"] = 0.2
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.compose_study(
            registration=tampered,
            pool={},
            repo_root=tmp_path,
            **_h5_inputs(tmp_path),
        )
    # The shipped F7 gate (`require_registration_hash`) names a canonical-hash
    # mismatch `preregistration_missing` — a payload that does not hash to the
    # pin IS not the pre-registration. The refusal fires before any pool touch
    # (the empty pool would refuse differently, later).
    assert _reason(exc_info) == "preregistration_missing"


def test_g4_crosswalk_tamper_and_absence_refuse(tmp_path: Path) -> None:
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps({"metadata": {"pull_timestamp": "t"}, "entries": [{}]}))
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    entries, observed_at = runner.load_crosswalk(
        tmp_path, path=Path("crosswalk.json"), expected_sha256=actual
    )
    assert entries and observed_at == "t"

    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.load_crosswalk(
            tmp_path, path=Path("crosswalk.json"), expected_sha256="0" * 64
        )
    assert _reason(exc_info) == "source_snapshot_drift"

    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.load_crosswalk(
            tmp_path, path=Path("absent.json"), expected_sha256=actual
        )
    assert _reason(exc_info) == "source_unavailable"


def test_g4_dp_snapshot_rows_are_qb_only_and_numeric(tmp_path: Path) -> None:
    snapshot = tmp_path / "values.csv"
    snapshot.write_text(
        "player,pos,value_2qb,fp_id\n"
        "QB One,QB,5000,10\n"
        "RB One,RB,4000,11\n"
    )
    rows = runner.load_dp_snapshot_rows({"path": snapshot})
    assert [row["dp_name"] for row in rows] == ["QB One"]
    assert rows[0]["value_2qb"] == 5000.0

    snapshot.write_text("player,pos,value_2qb,fp_id\nQB One,QB,not-a-number,10\n")
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.load_dp_snapshot_rows({"path": snapshot})
    assert _reason(exc_info) == "source_snapshot_drift"

    snapshot.write_text("player,pos,value_2qb,fp_id\nRB One,RB,4000,11\n")
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.load_dp_snapshot_rows({"path": snapshot})
    assert _reason(exc_info) == "source_snapshot_drift"


def test_g4_h5_fold_excludes_on_registered_reconciliation_breach() -> None:
    """The registered exclusion mechanism: a >2% name-mismatch rate excludes
    the FOLD (empty lane + named audit), never fails the run and never joins
    by name."""
    fold = {
        "test_season": 2021,
        "test_rows": [
            {"player_id": f"g-{index}", "target": "target_evaluable"}
            for index in range(50)
        ],
    }
    crosswalk = [
        {"fantasypros_id": str(index), "gsis_id": f"g-{index}", "name": f"Name {index}"}
        for index in range(50)
    ]
    dp_rows = [
        # Two mismatched names out of 50 joined = 4% > the registered 2%.
        {
            "fp_id": str(index),
            "dp_name": f"Name {index}" if index >= 2 else f"Other {index}",
            "value_2qb": 1000.0 + index,
        }
        for index in range(50)
    ]
    labels = {(f"g-{index}", 2021): 10.0 for index in range(50)}
    lane, audit = runner.build_h5_lane(
        fold,
        dp_rows=dp_rows,
        crosswalk_entries=crosswalk,
        observed_at="2026-05-16T03:28:22Z",
        registration=_registration(),
        label_lookup=labels,
    )
    assert audit["excluded"] is True
    assert audit["exclusion_reason"] == "join_reconciliation_failed"
    assert lane["n_predicted"] == 0 and lane["predictions"] == []
    assert lane["lane"] == "h5" and lane["lane_source"] == "dynastyprocess_ecr_2qb"


def test_g4_h5_fold_admits_below_threshold_and_predicts() -> None:
    fold = {
        "test_season": 2021,
        "test_rows": [
            {"player_id": f"g-{index}", "target": "target_evaluable"}
            for index in range(50)
        ],
    }
    crosswalk = [
        {"fantasypros_id": str(index), "gsis_id": f"g-{index}", "name": f"Name {index}"}
        for index in range(50)
    ]
    dp_rows = [
        # One mismatch of 50 = 2% — exactly at threshold ADMITS (registered
        # strictly-greater-than rule).
        {
            "fp_id": str(index),
            "dp_name": f"Name {index}" if index >= 1 else "Other 0",
            "value_2qb": 1000.0 + index,
        }
        for index in range(50)
    ]
    labels = {(f"g-{index}", 2021): 10.0 for index in range(50)}
    lane, audit = runner.build_h5_lane(
        fold,
        dp_rows=dp_rows,
        crosswalk_entries=crosswalk,
        observed_at="2026-05-16T03:28:22Z",
        registration=_registration(),
        label_lookup=labels,
    )
    assert audit["excluded"] is False
    assert lane["n_predicted"] == 50
    first = lane["predictions"][0]
    assert first["source_provenance"] == "dynastyprocess_ecr_2qb"
    assert first["decision_supported"] is False


def test_g4_case_resolution_refuses_ambiguity_and_missing_columns() -> None:
    two_allens = pd.DataFrame(
        [
            {"display_name": name, "position": "QB", "gsis_id": f"g-{index}"}
            for index, name in enumerate(
                [case[1] for case in runner.CASE_TABLE] + ["Josh Allen"]
            )
        ]
    )
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.resolve_case_players(two_allens)
    assert _reason(exc_info) == "case_identity_unresolved"

    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.resolve_case_players(pd.DataFrame({"display_name": ["x"]}))
    assert _reason(exc_info) == "case_identity_unresolved"


def _inference_result(**overrides: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": "c11",
        "lane": "h5",
        "registered_direction": "market_noninferior_delta_gt_delta0",
        "pooled": {
            "pooled_delta": None,
            "evaluable_folds": 1,
            "excluded_folds": [],
        },
        "interval": {
            "ci95_low": None,
            "ci95_high": None,
            "one_sided_lower_95": None,
        },
        "permutation": {"p_two": None},
        "margin_sensitivity": {0.05: {"p_ni": None, "adjusted_p_ni": None}},
    }
    result.update(overrides)
    return result


def test_g4_status_below_floor_applies_registered_rule_only() -> None:
    row = runner.contrast_status(
        _inference_result(),
        fdr_adjusted={"c11": None},
        registration=_registration(),
    )
    assert row["support_status"] == "unsupported_power"
    assert row["flags"] == ["registered_below_floor_rule"]
    assert row["decision_supported"] is False


def test_g4_status_at_floor_with_missing_numerics_refuses() -> None:
    result = _inference_result()
    result["pooled"]["evaluable_folds"] = 3
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.contrast_status(
            result, fdr_adjusted={"c11": None}, registration=_registration()
        )
    assert _reason(exc_info) == "inference_evidence_incomplete"


def test_g4_model_status_payload_mapping_is_exact() -> None:
    result = _inference_result(
        id="c01",
        lane="model",
        registered_direction="h1_gt_naive",
        pooled={"pooled_delta": 0.08, "evaluable_folds": 8, "excluded_folds": []},
        interval={"ci95_low": 0.02, "ci95_high": 0.14, "one_sided_lower_95": 0.03},
        permutation={"p_two": 0.01},
    )
    row = runner.contrast_status(
        result, fdr_adjusted={"c01": 0.04}, registration=_registration()
    )
    assert row["support_status"] == "supported"

    # The same evidence in the WRONG registered direction is contradicted.
    result["pooled"]["pooled_delta"] = -0.08
    result["interval"] = {
        "ci95_low": -0.14,
        "ci95_high": -0.02,
        "one_sided_lower_95": -0.13,
    }
    row = runner.contrast_status(
        result, fdr_adjusted={"c01": 0.04}, registration=_registration()
    )
    assert row["support_status"] == "contradicted"


# ── Round-2 regression rows (R2-G1 … R2-G6, Codex verdict `02336cbb…`) ─────────


def test_r2g1_named_preflight_failure_publishes_terminal_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2-G1: a named failure BEFORE the composition (registration load) must
    publish the D5 failed artifact through the real ``main()`` path — never
    escape artifact-less."""
    monkeypatch.setattr(
        runner,
        "load_registration",
        lambda _repo: (_ for _ in ()).throw(
            qb.QBValidationFailure("registration_pin_mismatch", "fixture")
        ),
    )
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    exit_code = runner.main(repo_root=tmp_path, output_path=destination)
    assert exit_code == 1
    published = json.loads(destination.read_text())
    assert published["run_status"] == "failed"
    assert published["failure_reason"] == "registration_pin_mismatch"
    assert published["decision_supported"] is False


def test_r2g1_ordinary_preflight_exception_publishes_execution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "load_registration",
        lambda _repo: (_ for _ in ()).throw(ValueError("disk surprise")),
    )
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    assert runner.main(repo_root=tmp_path, output_path=destination) == 1
    published = json.loads(destination.read_text())
    assert published["run_status"] == "failed"
    assert published["failure_reason"] == "execution_error"


def test_r2g2_coverage_denominator_is_the_fold_evaluable_pool() -> None:
    """R2-G2: 1 joined of 100 fold-evaluable must EXCLUDE as
    ``join_coverage_low`` (registration §9.3: 'coverage <70% of the fold's
    evaluable pool'), with the denominators reported separately."""
    fold = {
        "test_season": 2021,
        "test_rows": [
            {"player_id": f"g-{index}", "target": "target_evaluable"}
            for index in range(100)
        ],
    }
    lane, audit = runner.build_h5_lane(
        fold,
        dp_rows=[{"fp_id": "fp-0", "dp_name": "Name 0", "value_2qb": 1000.0}],
        crosswalk_entries=[
            {"fantasypros_id": "fp-0", "gsis_id": "g-0", "name": "Name 0"}
        ],
        observed_at="2026-05-16T03:28:22Z",
        registration=_registration(),
        label_lookup={(f"g-{index}", 2021): 10.0 for index in range(100)},
    )
    assert audit["excluded"] is True
    assert audit["exclusion_reason"] == "join_coverage_low"
    assert audit["evaluable_pool"] == 100
    assert audit["in_evaluable_pool"] == 1
    assert lane["n_predicted"] == 0


def test_r2g3_registered_schema_gate_refuses_incomplete_success() -> None:
    registration = _registration()
    complete = _complete_ok_payload(registration)
    qb.validate_registered_report_blocks(complete, registration=registration)

    first_fold = complete["folds"][0]
    for mutation, expected_fragment in (
        ({"disclosures": complete["disclosures"][:-1]}, "disclosures"),
        (
            {
                "folds": [{**first_fold, "attrition": {"no_target_season": 0}}]
                + complete["folds"][1:]
            },
            "attrition",
        ),
        (
            {
                "folds": [
                    {k: v for k, v in first_fold.items() if k != "metrics_with_CIs"}
                ]
                + complete["folds"][1:]
            },
            "metrics_with_CIs",
        ),
        (
            {
                "comparisons": [{"id": "c01", "decision_supported": False}]
                + complete["comparisons"][1:]
            },
            "missing required fields",
        ),
    ):
        with pytest.raises(qb.QBValidationFailure) as exc_info:
            qb.validate_registered_report_blocks(
                {**complete, **mutation}, registration=registration
            )
        assert _reason(exc_info) == "report_schema_invalid"
        assert expected_fragment in str(exc_info.value)


def test_r4g1_deep_gate_refuses_every_codex_reproducer(tmp_path: Path) -> None:
    """R4-G1: each of Codex's round-4 survivors now publishes as a named
    metric-free ``report_schema_invalid`` failed artifact through the PUBLIC
    runner — never as ok."""
    registration = _registration()

    def mutate(**changes: Any) -> dict[str, Any]:
        payload = _complete_ok_payload(registration)
        payload.update(changes)
        return payload

    base = _complete_ok_payload(registration)
    one_fold = mutate(folds=base["folds"][:1])
    one_contrast = mutate(comparisons=base["comparisons"][:1])
    bad_inputs = mutate(inputs={"snapshot_ids": ["only-one"]})
    negative = _complete_ok_payload(registration)
    negative["folds"][0]["n_evaluable"] = -1
    negative["folds"][0]["attrition"]["no_target_season"] = -4
    wrong_lane_status = _complete_ok_payload(registration)
    wrong_lane_status["comparisons"][0]["support_status"] = "market_superior"
    h5_without_retention = _complete_ok_payload(registration)
    for row in h5_without_retention["comparisons"]:
        if row["lane"] == "h5":
            row.pop("p_ni")
            row.pop("ni_met")
    wrong_cases = mutate(
        case_panel=[{"id": "not_a_registered_case", "decision_supported": False}]
    )
    wrong_panels = mutate(
        sensitivity_panels=[
            {"id": "not_a_registered_panel", "decision_supported": False}
        ]
    )

    for payload in (
        one_fold,
        one_contrast,
        bad_inputs,
        negative,
        wrong_lane_status,
        h5_without_retention,
        wrong_cases,
        wrong_panels,
    ):
        report, _destination = _run(
            tmp_path, lambda payload=payload: payload, registration=registration
        )
        assert report["run_status"] == "failed", payload["inputs"]
        assert report["failure_reason"] in {
            "report_schema_invalid",
            "case_panel_incomplete",
            "sensitivity_panel_incomplete",
        }


def test_r2g4_frozen_gate_runs_before_and_after_composition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2-G4: ``qb.validate_frozen_hashes`` must be exercised by the PRODUCTION
    composition — once before the analytics and again before success blocks
    leave for publication."""
    calls = 0
    real_gate = qb.validate_frozen_hashes

    def counting_gate(expected: Any) -> None:
        nonlocal calls
        calls += 1
        real_gate(expected)

    monkeypatch.setattr(qb, "validate_frozen_hashes", counting_gate)
    report_blocks = runner.compose_study(
        registration=_registration(),
        pool=_hermetic_pool(tmp_path),
        repo_root=tmp_path,
        **_h5_inputs(tmp_path),
    )
    assert report_blocks["run_status"] == "ok"
    assert calls >= 2


def test_r2g4_frozen_drift_refuses_named(tmp_path: Path) -> None:
    inputs = _h5_inputs(tmp_path)
    Path(inputs["dp_snapshots"][0]["path"]).write_text("tampered-after-pinning\n")
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.compose_study(
            registration=_registration(),
            pool=_hermetic_pool(tmp_path),
            repo_root=tmp_path,
            **inputs,
        )
    assert _reason(exc_info) == "frozen_boundary_drift"


def test_r2g5_archetype_panel_computes_gate_flips_and_boundary_cases() -> None:
    """R2-G5: the F13 panel carries computed results — binary classification,
    boundary membership, and ±1 yd/game flip sensitivity — never a static
    declaration."""
    folds = [
        {
            "test_season": 2021,
            "test_rows": [
                {"player_id": p, "target": "target_evaluable", "rush_yds_per_game": v}
                for p, v in (("dual", 30.0), ("boundary", 39.5), ("pocket", 5.0))
            ],
        }
    ]
    rushing = {
        ("dual", 2020): {"rushing_yards": 500.0, "weeks": 16},
        ("boundary", 2020): {"rushing_yards": 395.0, "weeks": 10},
        ("pocket", 2020): {"rushing_yards": 100.0, "weeks": 16},
    }
    panel = runner.build_archetype_threshold_panel(folds, rushing)
    fold_row = panel["binary_dual_threat_gate"]["per_fold"][0]
    assert fold_row["dual_threat_count"] == 1
    assert fold_row["pocket_count"] == 2
    assert fold_row["boundary_case_count"] == 1
    boundary = fold_row["boundary_cases"][0]
    assert boundary["player_id"] == "boundary"
    # 395 yds over 10 weeks: threshold-10 = 390 < 395 → flips at −1 yd/game.
    assert boundary["flips_at_minus_1_ypg"] is True
    assert boundary["flips_at_plus_1_ypg"] is False
    # R10 (R9-G2): the case disclosed its FULL observed window evidence —
    # here the single observed 2020 row — as mechanically checkable rows.
    assert boundary["window_seasons"] == [
        {
            "season": 2020,
            "rushing_yards": 395.0,
            "qualifying_games": 10,
            "decision_supported": False,
        }
    ]
    assert "window_high_season_count" not in boundary
    # R11: EVERY evaluable player disclosed with their evidence — the dual
    # and pocket players too, not only the boundary case — and the boundary
    # case's rows are byte-for-byte its player's disclosed evidence.
    pool = {row["player_id"]: row["window_seasons"] for row in fold_row["evaluable_players"]}
    assert set(pool) == {"dual", "boundary", "pocket"}
    assert pool["dual"] == [
        {
            "season": 2020,
            "rushing_yards": 500.0,
            "qualifying_games": 16,
            "decision_supported": False,
        }
    ]
    assert pool["boundary"] == boundary["window_seasons"]
    assert pool["pocket"] == [
        {
            "season": 2020,
            "rushing_yards": 100.0,
            "qualifying_games": 16,
            "decision_supported": False,
        }
    ]
    assert fold_row["flips_at_minus_1_ypg"] == 1
    assert panel["boundary_cases_yards_per_game"] == [-1, 1]
    qb.require_threshold_sensitivity(panel)


def test_r2g6_every_admitted_snapshot_hash_reaches_metadata(tmp_path: Path) -> None:
    """R2-G6: a multi-snapshot dataset keeps ALL its hashes in the admitted
    envelope — never first-file-only."""
    raw = tmp_path / "app/data/backtest/qb_validation/raw"
    datasets: dict[str, Any] = {}
    for name in DATASETS:
        snapshots = []
        count = 3 if name == "pbp" else 1
        for index in range(count):
            snapshot = raw / name / f"{name}_{index}.parquet"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(f"{name}-{index}".encode())
            snapshots.append(
                {
                    "file": str(snapshot.relative_to(tmp_path)),
                    "rows": 1,
                    "columns": 1,
                    "bytes": snapshot.stat().st_size,
                    "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                }
            )
        datasets[name] = {"snapshots": snapshots}
    (raw / "fetch_manifest.json").write_text(
        json.dumps(
            {
                "registration_pin": PIN,
                "finished_at": "2026-08-14T16:00:00Z",
                "nflreadpy_version": "fixture",
                "datasets": datasets,
            }
        )
    )
    states = qb.admit_fetch_manifest(
        raw, repo_root=tmp_path, frame_loader=lambda _p: pd.DataFrame({"x": [1]})
    )
    pbp_hashes = [row["sha256"] for row in states["pbp"]["metadata"]["snapshots"]]
    assert len(pbp_hashes) == 3 and len(set(pbp_hashes)) == 3


# ── Round-3 regression rows (R3-G2 … R3-G5, Codex verdict `0b8dca62…`) ─────────


def test_r3g2_fold_flag_vocabulary_is_closed() -> None:
    registration = _registration()
    complete = _complete_ok_payload(registration)
    for flag in ("fold_starved", "join_coverage_low", "join_reconciliation_failed"):
        complete["folds"][0]["flags"] = [flag]
        qb.validate_registered_report_blocks(complete, registration=registration)
    complete["folds"][0]["flags"] = ["h5_fold_excluded:join_reconciliation_failed"]
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.validate_registered_report_blocks(complete, registration=registration)
    assert _reason(exc_info) == "report_schema_invalid"
    assert "unregistered flags" in str(exc_info.value)


def test_r3g3_manifest_missing_mapping_count_is_read_not_zeroed() -> None:
    """R3-G3: the real ridge shape {'count': n, 'keys': [...]} must surface n;
    an unreadable shape refuses, never silently zeroes."""
    lane = {"missingness": {"test_manifest_missing": {"count": 7, "keys": ["a"] * 7}}}
    assert runner.lane_manifest_missing(lane) == 7
    assert runner.lane_manifest_missing({"missingness": {"test_manifest_missing": 3}}) == 3
    assert (
        runner.lane_manifest_missing({"missingness": {"test_manifest_missing": [1, 2]}})
        == 2
    )
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner.lane_manifest_missing(
            {"missingness": {"test_manifest_missing": {"count": "seven"}}}
        )
    assert _reason(exc_info) == "report_schema_invalid"
    with pytest.raises(qb.QBValidationFailure):
        runner.lane_manifest_missing({"missingness": {"test_manifest_missing": None}})


def test_r3g4_f25_set_is_runner_owned_and_exactly_the_registered_five() -> None:
    """R3-G4: the F25 set is the registered product/model boundary, pinned at
    Codex's independently measured hashes, resolved against the script's OWN
    repo root — and the real repo passes it today (the standing tripwire)."""
    assert runner.F25_FROZEN_SET == {
        "app/config/model_registry.json": (
            "307200148e2c251e4b4de9ce3d03a02eab20839034dc3a8ba319a5a1298e1ac3"
        ),
        "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl": (
            "d7acb6808e4a6caf412ec05b41aa90324e04f90ef219bbf78f680f66ea7d304f"
        ),
        "app/data/models/engine_b/v2_manifest.json": (
            "86f199bd069823cc292f8d56553dadc91f07f78bd47ac26498a06f16440984bc"
        ),
        "src/dynasty_genius/eval/qb_v3_walk_forward.py": (
            "7f3e9283afac1928629b3c04ef2ec71e85c99f3e55278f2237fcf9bedab4a3b5"
        ),
        "docs/validation/2026-07-04-build4-qb-v3-promotion-decision-record.md": (
            "a963b671dc6a1ef88bb73283acac594201b7cee3bda59a84681a03b810f6bd63"
        ),
    }
    expected = runner.f25_frozen_expected()
    assert all(str(path).startswith(str(runner._REPO_ROOT)) for path in expected)
    qb.validate_frozen_hashes(expected)


def test_r3g5_nonqualifying_rows_never_count_as_games() -> None:
    """R3-G5 (Codex's own example): 398.5 yards on ONE qualifying row plus a
    zero-stat nonqualifying row → one registered qualifying game → shifted
    threshold 399 → no flip and no boundary membership."""
    rushing = runner.build_season_rushing(
        [
            {
                "player_id": "qb",
                "season": 2020,
                "rushing_yards": 398.5,
                "attempts": 20,
                "sacks_suffered": 1,
                "carries": 5,
            },
            {
                "player_id": "qb",
                "season": 2020,
                "rushing_yards": 0,
                "attempts": 0,
                "sacks_suffered": 0,
                "carries": 0,
            },
        ]
    )
    assert rushing[("qb", 2020)] == {"rushing_yards": 398.5, "weeks": 1}
    folds = [
        {
            "test_season": 2021,
            "test_rows": [
                {
                    "player_id": "qb",
                    "target": "target_evaluable",
                    "rush_yds_per_game": 23.4,
                }
            ],
        }
    ]
    fold_row = runner.build_archetype_threshold_panel(folds, rushing)[
        "binary_dual_threat_gate"
    ]["per_fold"][0]
    assert fold_row["flips_at_minus_1_ypg"] == 0
    assert fold_row["flips_at_plus_1_ypg"] == 0
    assert fold_row["boundary_case_count"] == 0


# ── R6 (R5-G1): the deep gate rejects CONTENT defects, one mutant per class ────
#
# Codex's round-5 verdict (review ead8cd4a…, probe 0bfa785b… 4/4) proved the
# prior gate presence-only below its top-level shells. Each test below mutates
# the genuinely complete oracle by exactly one rejected class and publishes
# through the PUBLIC runner boundary — the same path the probe exploited.


def _publish_mutant(
    tmp_path: Path, payload: dict[str, Any], registration: dict[str, Any]
) -> dict[str, Any]:
    report, destination = _run(tmp_path, lambda: payload, registration=registration)
    assert json.loads(destination.read_text()) == report
    return report


def _assert_schema_refusal(report: dict[str, Any]) -> None:
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
    assert report["decision_supported"] is False
    assert "comparisons" not in report


def test_r6_positive_control_complete_payload_publishes_ok(tmp_path: Path) -> None:
    registration = _registration()
    report = _publish_mutant(tmp_path, _complete_ok_payload(registration), registration)
    assert report["run_status"] == "ok"
    for fold in report["folds"]:
        assert fold["metrics_with_CIs"], "the oracle must never carry empty metrics"
    qb.validate_report_output(report)


def test_r6_metric_free_fold_refuses(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["folds"][0]["metrics_with_CIs"] = {}
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_unregistered_metric_contrast_id_refuses(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["folds"][0]["metrics_with_CIs"]["c99"] = _fold_metric_entry()
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_h5_metrics_outside_registered_h5_folds_refuse(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    non_h5_fold = next(
        fold
        for fold in payload["folds"]
        if fold["test_season"] not in set(registration["h5"]["folds"])
    )
    non_h5_fold["metrics_with_CIs"]["c11"] = _fold_metric_entry()
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_untyped_fold_metric_values_refuse(tmp_path: Path) -> None:
    registration = _registration()
    for field, bad in (
        ("paired_delta", "not-a-number"),
        ("paired_delta", float("nan")),
        ("spearman_left", 1.5),
        ("common_pool_n", -1),
        ("ci", "pooled"),
    ):
        payload = _complete_ok_payload(registration)
        payload["folds"][0]["metrics_with_CIs"]["c01"][field] = bad
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_unknown_manifest_lane_refuses(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["folds"][0]["attrition"]["manifest_missing"] = {"not_a_lane": 0}
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_missing_ridge_lane_refuses(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["folds"][0]["attrition"]["manifest_missing"] = {"h1": 0}
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_invalid_comparison_numerics_refuse(tmp_path: Path) -> None:
    """Codex probe row 2 verbatim: -9 folds, a string interval, a string
    probability, a string boolean — each alone must refuse."""
    registration = _registration()
    for mutate in (
        lambda row: row.__setitem__("evaluable_folds", -9),
        lambda row: row.__setitem__("ci95", "not-an-interval"),
        lambda row: row.__setitem__("ci95", [0.2, -0.2]),
        lambda row: row.__setitem__("pooled_delta", float("inf")),
        lambda row: row.__setitem__("p_perm", 1.5),
    ):
        payload = _complete_ok_payload(registration)
        mutate(payload["comparisons"][0])
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    for mutate in (
        lambda row: row.__setitem__("p_ni", "not-a-probability"),
        lambda row: row.__setitem__("ni_met", "not-a-boolean"),
    ):
        payload = _complete_ok_payload(registration)
        h5_row = next(row for row in payload["comparisons"] if row["lane"] == "h5")
        mutate(h5_row)
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_shell_case_rows_refuse(tmp_path: Path) -> None:
    """Codex probe row 1: id/scope_note/decision_supported shells are not
    case results."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["case_panel"] = [
        {
            "id": row["id"],
            "scope_note": row["scope_note"],
            "decision_supported": False,
        }
        for row in payload["case_panel"]
    ]
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_reported_case_lane_without_results_refuses(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["case_panel"][0]["lanes"]["h1"] = {
        "state": "reported",
        "decision_supported": False,
    }
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_qualifying_slice_without_pooled_deltas_refuses(tmp_path: Path) -> None:
    """Codex probe row 1: the qualifying slices must carry their pooled
    readouts — in BOTH slices."""
    registration = _registration()
    for slice_name in ("unfiltered_primary", "min_four_games"):
        payload = _complete_ok_payload(registration)
        del payload["sensitivity_panels"][1][slice_name]["pooled_deltas"]
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_qualifying_pooled_deltas_missing_a_contrast_refuses(
    tmp_path: Path,
) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    del payload["sensitivity_panels"][1]["unfiltered_primary"]["pooled_deltas"]["c07"]
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_h5_margin_without_readout_refuses(tmp_path: Path) -> None:
    """Codex probe row 1: a margins list with no per-contrast readout is a
    shell."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    del payload["sensitivity_panels"][2]["readout"]
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_h5_margin_readout_defects_refuse(tmp_path: Path) -> None:
    registration = _registration()
    # A missing H5 contrast.
    payload = _complete_ok_payload(registration)
    del payload["sensitivity_panels"][2]["readout"]["c11"]
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    # An unregistered margin key.
    payload = _complete_ok_payload(registration)
    payload["sensitivity_panels"][2]["readout"]["c11"]["0.5"] = {
        "p_ni": None,
        "adjusted_p_ni": None,
        "ni_met": None,
        "decision_supported": False,
    }
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    # An untyped leaf.
    payload = _complete_ok_payload(registration)
    payload["sensitivity_panels"][2]["readout"]["c11"]["0.05"]["p_ni"] = (
        "not-a-probability"
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_placeholder_archetype_panel_refuses(tmp_path: Path) -> None:
    """Codex probe row 3 verbatim: True / None / a 999 boundary are
    placeholders, not the computed F13 structures."""
    registration = _registration()
    for mutate in (
        lambda panel: panel.__setitem__("binary_dual_threat_gate", True),
        lambda panel: panel.__setitem__("continuous_rushing_moderator", None),
        lambda panel: panel.__setitem__(
            "boundary_cases_yards_per_game", [-1, 1, 999]
        ),
        lambda panel: panel["binary_dual_threat_gate"].__setitem__("per_fold", []),
        lambda panel: panel["binary_dual_threat_gate"]["per_fold"][0].__setitem__(
            "dual_threat_count", -1
        ),
    ):
        payload = _complete_ok_payload(registration)
        mutate(payload["sensitivity_panels"][0])
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r6_ridge_lane_single_source_of_truth() -> None:
    """The runner's manifest keys and the gate's required lane set are the
    same object — they cannot drift apart."""
    assert runner._RIDGE_LANES is qb.execution.RIDGE_LANE_NAMES


# ── R7 (the four R6 blockers): semantic coherence, one mutant per class ────────
#
# Codex's round-6 verdict (review 0afc2368…, probe b3b739a2… 6/6) proved the
# deep gate still content-blind in six classes. Each mutant below publishes
# through the PUBLIC runner boundary.


def test_r7_below_floor_substantive_statuses_refuse(tmp_path: Path) -> None:
    """R6-G1-STATUS / probe row 3: the registered fold floors (model 5, h5 3)
    make unsupported_power MANDATORY below floor."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["comparisons"][0].update(
        pooled_delta=0.10, ci95=[0.06, 0.14], p_perm=0.01,
        support_status="supported", evaluable_folds=0,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))

    payload = _complete_ok_payload(registration)
    h5_row = next(row for row in payload["comparisons"] if row["lane"] == "h5")
    h5_row.update(
        pooled_delta=0.10, ci95=[0.06, 0.14], p_ni=0.01, ni_met=True,
        support_status="market_noninferior", evaluable_folds=0,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_substantive_status_without_evidence_fields_refuses(
    tmp_path: Path,
) -> None:
    registration = _registration()
    # market_noninferior with ni_met False contradicts itself.
    payload = _complete_ok_payload(registration)
    h5_row = next(row for row in payload["comparisons"] if row["lane"] == "h5")
    h5_row.update(
        pooled_delta=0.10, ci95=[0.06, 0.14], p_ni=0.01, ni_met=False,
        support_status="market_noninferior", evaluable_folds=4,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    # A model "supported" without p_perm / a finite interval has no evidence.
    payload = _complete_ok_payload(registration)
    payload["comparisons"][0].update(
        support_status="supported", evaluable_folds=8,
        p_perm=None, ci95=[None, None],
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_h5_claimed_folds_exceeding_fold_evidence_refuse(
    tmp_path: Path,
) -> None:
    """R6-G1-H5-CONTENT / probe row 2: a positive H5 claim cannot outrun the
    per-fold evidence."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    for fold in payload["folds"]:
        fold["metrics_with_CIs"].pop("c11", None)
    c11 = next(row for row in payload["comparisons"] if row["id"] == "c11")
    c11.update(
        pooled_delta=0.10, ci95=[0.06, 0.14], p_ni=0.01, ni_met=True,
        support_status="market_noninferior", evaluable_folds=4,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_h5_fold_omission_needs_a_registered_exclusion_flag(
    tmp_path: Path,
) -> None:
    registration = _registration()
    h5_seasons = set(registration["h5"]["folds"])
    # Omission with NO flag refuses.
    payload = _complete_ok_payload(registration)
    target = next(
        fold for fold in payload["folds"] if fold["test_season"] in h5_seasons
    )
    for contrast_id in ("c11", "c12", "c13", "c14"):
        target["metrics_with_CIs"].pop(contrast_id, None)
    target["flags"] = []
    for row in payload["comparisons"]:
        if row["lane"] == "h5":
            row["evaluable_folds"] = 3
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    # The SAME omission with a registered exclusion flag publishes ok — the
    # honest-exclusion path Codex's ruling preserves. (R8-G2 tightened this
    # positive control: the honest claim now ALSO names the omitted season in
    # each row's excluded_folds — the registered complement of its evaluable
    # set — not only the fold-level flag.)
    payload = _complete_ok_payload(registration)
    target = next(
        fold for fold in payload["folds"] if fold["test_season"] in h5_seasons
    )
    for contrast_id in ("c11", "c12", "c13", "c14"):
        target["metrics_with_CIs"].pop(contrast_id, None)
    target["flags"] = ["join_coverage_low"]
    omitted = target["test_season"]
    for row in payload["comparisons"]:
        if row["lane"] == "h5":
            row["evaluable_folds"] = 3
            row["excluded_folds"] = [
                {
                    "test_season": omitted,
                    "reasons": ["join_coverage_low"],
                    "decision_supported": False,
                }
            ]
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r7_missing_or_extra_margin_cells_refuse(tmp_path: Path) -> None:
    """R6-G1-H5-CONTENT / probe row 1: all 12 contrast×margin cells are
    mandatory (§9.2) — empty maps and missing cells refuse."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["sensitivity_panels"][2]["readout"] = {
        contrast_id: {} for contrast_id in ("c11", "c12", "c13", "c14")
    }
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    payload = _complete_ok_payload(registration)
    del payload["sensitivity_panels"][2]["readout"]["c12"]["0.05"]
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_unavailable_margin_cell_with_honest_nulls_publishes(
    tmp_path: Path,
) -> None:
    """Codex's ruling verbatim: an uncomputable cell remains PRESENT with an
    honest unavailable state and null outputs."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["sensitivity_panels"][2]["readout"]["c12"]["0.05"] = {
        "state": "unavailable",
        "p_ni": None,
        "adjusted_p_ni": None,
        "ni_met": None,
        "decision_supported": False,
    }
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r7_fabricated_f13_content_refuses(tmp_path: Path) -> None:
    """R6-G1-F13 / probe row 4: typed-but-impossible content refuses on the
    shipped-computation invariants."""
    registration = _registration()
    for mutate in (
        lambda gate: gate.__setitem__("threshold_yards", -123.0),
        lambda gate: gate.__setitem__("rule", "an unrelated nonempty rule"),
        lambda gate: gate["per_fold"][0].update(
            dual_threat_count=999, pocket_count=999, boundary_case_count=999
        ),
        lambda gate: gate["per_fold"][0].__setitem__("boundary_case_count", 1),
        lambda gate: gate["per_fold"][0].__setitem__("flips_at_plus_1_ypg", 5),
    ):
        payload = _complete_ok_payload(registration)
        mutate(payload["sensitivity_panels"][0]["binary_dual_threat_gate"])
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    payload = _complete_ok_payload(registration)
    payload["sensitivity_panels"][0]["continuous_rushing_moderator"] = {
        "basis": "unrelated nonempty basis",
        "decision_supported": False,
    }
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_malformed_boundary_rows_refuse(tmp_path: Path) -> None:
    registration = _registration()
    payload = _complete_ok_payload(registration)
    gate = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]
    gate["per_fold"][0].update(
        boundary_case_count=1,
        boundary_cases=[{"player_id": "", "decision_supported": False}],
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_empty_or_reshaped_fold_ci_refuses(tmp_path: Path) -> None:
    """R6-G1-REPORT-CONTENT / probe row 6: the per-fold ci object is closed to
    its emitted pooled-level contract."""
    registration = _registration()
    for bad_ci in ({}, {"state": "computed", "decision_supported": False}):
        payload = _complete_ok_payload(registration)
        payload["folds"][0]["metrics_with_CIs"]["c01"]["ci"] = bad_ci
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_unproduced_case_identity_or_lane_refuses(tmp_path: Path) -> None:
    """R6-G1-REPORT-CONTENT / probe row 5: blank identities, invented lanes,
    and state/lane inconsistency all refuse."""
    registration = _registration()
    for mutate in (
        lambda case: case.__setitem__("player_name", ""),
        lambda case: case.__setitem__("gsis_id", "  "),
        lambda case: case.__setitem__(
            "lanes",
            {
                "fabricated_lane": {
                    "state": "reported",
                    "y_pred": 1.0,
                    "y_true": 2.0,
                    "decision_supported": False,
                }
            },
        ),
        lambda case: case.__setitem__("state", "not_in_evaluable_pool"),
    ):
        payload = _complete_ok_payload(registration)
        mutate(payload["case_panel"][0])
        _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r7_dual_threat_threshold_single_source_of_truth() -> None:
    assert runner.DUAL_THREAT_RUSHING_THRESHOLD is qb.execution.DUAL_THREAT_RUSHING_YARDS


# ── R8 (the four R7 blockers): the shipped functions are the authority ─────────
#
# Codex's round-7 verdict (review 25ac1c8f…, probe b939e781… 9/9) proved the
# gate still approximated instead of invoking the shipped machinery. Each
# mutant publishes through the PUBLIC runner boundary.


def _assert_refusal(report: dict[str, Any], *reasons: str) -> None:
    assert report["run_status"] == "failed"
    assert report["failure_reason"] in reasons
    assert report["decision_supported"] is False
    assert "comparisons" not in report


def test_r8_negative_delta_supported_must_be_contradicted(tmp_path: Path) -> None:
    """Codex G1 row 1: the shipped total function calls this contradicted."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["comparisons"][0].update(
        pooled_delta=-0.10, ci95=[-0.14, -0.06], p_perm=0.01, adjusted_p=0.01,
        support_status="supported", evaluable_folds=8,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_unsupported_power_with_full_folds_refuses(tmp_path: Path) -> None:
    """Codex G1 row 2: 8/8 folds cannot be unsupported_power under the shipped
    function's own evaluation of this evidence."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["comparisons"][0].update(
        support_status="unsupported_power", evaluable_folds=8,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_impossible_fold_total_refuses_named(tmp_path: Path) -> None:
    """Codex G1 row 3: 9 evaluable folds of a registered 8-fold lane is
    impossible evidence — the shipped function refuses it by name."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["comparisons"][0].update(evaluable_folds=9)
    report = _publish_mutant(tmp_path, payload, registration)
    _assert_refusal(report, "status_payload_malformed")


def test_r8_h5_noninferior_against_shipped_function_refuses(tmp_path: Path) -> None:
    """Codex G1 row 4: caller-typed ni_met=True with p_ni evidence the shipped
    H5 function rejects cannot publish as market_noninferior."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    h5_row = next(row for row in payload["comparisons"] if row["lane"] == "h5")
    h5_row.update(
        pooled_delta=0.01, ci95=[-0.02, 0.04], one_sided_lower_95=0.0,
        p_ni=0.99, adjusted_p_ni=0.99, ni_met=True,
        support_status="market_noninferior", evaluable_folds=4,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_h5_emitted_flags_must_match(tmp_path: Path) -> None:
    """A ci/p disagreement must surface the shipped ci_p_disagreement flag."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    h5_row = next(row for row in payload["comparisons"] if row["lane"] == "h5")
    # one_sided -0.04 > delta0 -0.05 (ci_pass True) while adjusted 0.6 > q
    # (p_pass False): the shipped function emits inconclusive + the flag.
    h5_row.update(one_sided_lower_95=-0.04, support_status="inconclusive", flags=[])
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))
    h5_row = None
    payload = _complete_ok_payload(registration)
    row = next(r for r in payload["comparisons"] if r["lane"] == "h5")
    row.update(
        one_sided_lower_95=-0.04, support_status="inconclusive",
        flags=["ci_p_disagreement"],
    )
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r8_all_empty_margin_leaves_refuse(tmp_path: Path) -> None:
    """Codex G2 row 1: 12 present keys with {} leaves are shells, refused."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    payload["sensitivity_panels"][2]["readout"] = {
        contrast_id: {str(margin): {} for margin in registration["h5"]["margin_sensitivity"]}
        for contrast_id in ("c11", "c12", "c13", "c14")
    }
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_single_contrast_omission_needs_flag(tmp_path: Path) -> None:
    """Codex G2 row 2: removing ONLY c11 from one H5 fold without a flag
    refuses — exclusion handling is per contrast, not all-or-nothing."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    h5_seasons = set(registration["h5"]["folds"])
    target = next(
        fold for fold in payload["folds"] if fold["test_season"] in h5_seasons
    )
    del target["metrics_with_CIs"]["c11"]
    target["flags"] = []
    c11 = next(row for row in payload["comparisons"] if row["id"] == "c11")
    c11.update(evaluable_folds=3)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_underreported_h5_folds_refuse(tmp_path: Path) -> None:
    """Codex G2 row 3: evaluable_folds=0 while four non-null per-fold rows
    remain — under-reporting refuses exactly like over-claiming."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    c11 = next(row for row in payload["comparisons"] if row["id"] == "c11")
    c11.update(evaluable_folds=0, support_status="unsupported_power", flags=[])
    # The below-floor label is coherent for the status function only when the
    # numerics are absent; keep them so the shipped function runs — and the
    # reconciliation (0 + 0 != 4) refuses regardless.
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_fabricated_boundary_row_refuses(tmp_path: Path) -> None:
    """Codex G3: a 1900 season, 10,000 yards, and -10.5 qualifying games can
    never be the shipped trailing-window boundary computation."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    gate = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]
    gate["per_fold"][0].update(
        boundary_case_count=1,
        boundary_cases=[
            {
                "player_id": "qb",
                "binary_dual_threat": False,
                "flips_at_minus_1_ypg": False,
                "flips_at_plus_1_ypg": False,
                "boundary_seasons": [
                    {
                        "season": 1900,
                        "rushing_yards": 10_000,
                        "qualifying_games": -10.5,
                        "decision_supported": False,
                    }
                ],
                "decision_supported": False,
            }
        ],
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_boundary_flip_must_recompute(tmp_path: Path) -> None:
    """A claimed flip that does not follow from the row's own boundary seasons
    refuses; the genuine computation publishes."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]

    def _boundary_case(*, flips_plus: bool) -> dict[str, Any]:
        # 401 yards, 5 games: base True (401>400); plus-shift threshold 405 →
        # 401 > 405 False → a GENUINE plus-flip; minus-shift 395 → True, no flip.
        row = {
            "season": first_season - 1,
            "rushing_yards": 401,
            "qualifying_games": 5,
            "decision_supported": False,
        }
        return {
            "player_id": "qb",
            "binary_dual_threat": True,
            "flips_at_minus_1_ypg": False,
            "flips_at_plus_1_ypg": flips_plus,
            "window_seasons": [dict(row)],
            "boundary_seasons": [dict(row)],
            "decision_supported": False,
        }

    def _disclosed_pool(case: dict[str, Any]) -> list[dict[str, Any]]:
        # R11: the case's player disclosed as the sole evaluable player.
        return [
            {
                "player_id": case["player_id"],
                "window_seasons": [dict(row) for row in case["window_seasons"]],
                "decision_supported": False,
            }
        ]

    payload = _complete_ok_payload(registration)
    gate = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]
    genuine = _boundary_case(flips_plus=True)
    gate["per_fold"][0].update(
        dual_threat_count=1,
        pocket_count=0,
        evaluable_players=_disclosed_pool(genuine),
        boundary_case_count=1,
        boundary_cases=[genuine],
        flips_at_plus_1_ypg=1,
    )
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"

    payload = _complete_ok_payload(registration)
    gate = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]
    bogus = _boundary_case(flips_plus=False)
    bogus["flips_at_minus_1_ypg"] = True  # 395-shift stays True: no real flip
    gate["per_fold"][0].update(
        dual_threat_count=1,
        pocket_count=0,
        evaluable_players=_disclosed_pool(bogus),
        boundary_case_count=1,
        boundary_cases=[bogus],
        flips_at_minus_1_ypg=1,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_h5_case_lane_outside_h5_folds_refuses(tmp_path: Path) -> None:
    """Codex G4: an H5 lane on a case whose fold is outside the registered H5
    folds cannot be produced by the composition."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    case = payload["case_panel"][0]
    assert case["fold"] not in set(registration["h5"]["folds"])
    case["lanes"]["h5"] = {
        "state": "reported",
        "y_pred": 1.0,
        "y_true": 2.0,
        "decision_supported": False,
    }
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r8_h5_case_lane_inside_h5_folds_publishes(tmp_path: Path) -> None:
    """The same H5 lane on a registered-H5-fold case is producible and passes."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    case = payload["case_panel"][0]
    case["fold"] = registration["h5"]["folds"][0]
    case["lanes"]["h5"] = {
        "state": "reported",
        "y_pred": 1.0,
        "y_true": 2.0,
        "decision_supported": False,
    }
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


# ── Round 9: the three Codex R8 smallest corrections — G1 below-floor
# exactness · G2 mechanical evaluable reconciliation · G3 F13 totality ────────


def _null_c11_entries(
    payload: dict[str, Any], registration: dict[str, Any], count: int
) -> list[int]:
    """Turn ``count`` of c11's keyed H5 fold entries into producer-shaped
    non-evaluable records (delta None, null Spearmans, empty pool); returns
    the affected seasons."""
    h5_seasons = set(registration["h5"]["folds"])
    seasons: list[int] = []
    for fold in payload["folds"]:
        if fold["test_season"] in h5_seasons and len(seasons) < count:
            fold["metrics_with_CIs"]["c11"].update(
                paired_delta=None,
                spearman_left=None,
                spearman_right=None,
                common_pool_n=0,
            )
            seasons.append(fold["test_season"])
    return seasons


def _excluded_rows(seasons: list[int]) -> list[dict[str, Any]]:
    return [
        {
            "test_season": season,
            "reasons": ["join_coverage_low"],
            "decision_supported": False,
        }
        for season in seasons
    ]


def test_r9_h5_keyed_shell_does_not_count_as_evaluable(tmp_path: Path) -> None:
    """Codex R8-G2 probe row: one keyed-but-non-evaluable c11 fold entry with
    an unchanged evaluable_folds=4 claim must refuse — key presence is not
    mechanically evaluable content."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    _null_c11_entries(payload, registration, 1)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_h5_keyed_shell_with_named_exclusion_publishes(tmp_path: Path) -> None:
    """Positive control: the same non-evaluable entry, honestly claimed —
    evaluable_folds=3 and the season named in excluded_folds — publishes."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    seasons = _null_c11_entries(payload, registration, 1)
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(evaluable_folds=3, excluded_folds=_excluded_rows(seasons))
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r9_h5_excluding_a_contributing_fold_refuses(tmp_path: Path) -> None:
    """The complement is exact in BOTH directions: excluding a fold whose
    emitted content is evaluable refuses even when the count is untouched."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(excluded_folds=_excluded_rows([registration["h5"]["folds"][0]]))
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_h5_delta_without_support_refuses(tmp_path: Path) -> None:
    """Producer coherence: a paired_delta floating on null Spearmans or an
    empty pool is not a producible record (inference refuses it as
    fold_record_inconsistent) and must refuse at the gate."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    h5_seasons = set(registration["h5"]["folds"])
    fold = next(
        fold for fold in payload["folds"] if fold["test_season"] in h5_seasons
    )
    fold["metrics_with_CIs"]["c11"].update(spearman_left=None)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_h5_below_floor_partial_evidence_refuses(tmp_path: Path) -> None:
    """Codex R8-G1 probe row verbatim: a below-floor c11 row with PARTIAL
    numerics and a caller-typed ni_met=True must refuse."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    h5_seasons = list(registration["h5"]["folds"])
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(
        evaluable_folds=2,
        pooled_delta=0.01,
        ci95=[-0.02, 0.04],
        p_ni=0.01,
        adjusted_p_ni=None,
        one_sided_lower_95=None,
        ni_met=True,
        support_status="unsupported_power",
        flags=["registered_below_floor_rule"],
        excluded_folds=_excluded_rows(h5_seasons[:2]),
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_h5_below_floor_partial_refuses_even_reconciled(tmp_path: Path) -> None:
    """G1 isolation: with the fold evidence and the complement PERFECTLY
    reconciled, partial numerics below the floor still refuse — neither
    computable nor honestly unavailable."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    seasons = _null_c11_entries(payload, registration, 2)
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(
        evaluable_folds=2,
        pooled_delta=0.01,
        ci95=[-0.02, 0.04],
        p_ni=0.01,
        adjusted_p_ni=None,
        one_sided_lower_95=None,
        ni_met=True,
        support_status="unsupported_power",
        flags=["registered_below_floor_rule"],
        excluded_folds=_excluded_rows(seasons),
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_h5_below_floor_wholly_unavailable_publishes(tmp_path: Path) -> None:
    """Positive control: the honestly-unavailable below-floor special case —
    all six inference numerics null, ni_met=False, the registered status and
    exactly the registered flag, reconciled to the fold evidence — publishes."""
    registration = _registration()
    below_floor_status = registration["fold_floors"]["below_floor_status"]
    payload = _complete_ok_payload(registration)
    seasons = _null_c11_entries(payload, registration, 2)
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(
        evaluable_folds=2,
        pooled_delta=None,
        ci95=[None, None],
        one_sided_lower_95=None,
        p_ni=None,
        adjusted_p_ni=None,
        ni_met=False,
        support_status=below_floor_status,
        flags=["registered_below_floor_rule"],
        excluded_folds=_excluded_rows(seasons),
    )
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r9_h5_below_floor_ni_met_true_refuses(tmp_path: Path) -> None:
    """The exact special-case schema rejects ni_met=True even when every
    numeric is honestly null."""
    registration = _registration()
    below_floor_status = registration["fold_floors"]["below_floor_status"]
    payload = _complete_ok_payload(registration)
    seasons = _null_c11_entries(payload, registration, 2)
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(
        evaluable_folds=2,
        pooled_delta=None,
        ci95=[None, None],
        one_sided_lower_95=None,
        p_ni=None,
        adjusted_p_ni=None,
        ni_met=True,
        support_status=below_floor_status,
        flags=["registered_below_floor_rule"],
        excluded_folds=_excluded_rows(seasons),
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def _r9_boundary_case(first_season: int, **overrides: Any) -> dict[str, Any]:
    """401 yards / 5 games: base True; minus-shift 395 → True (no flip);
    plus-shift 405 → False (a genuine plus flip when no high season exists).

    R10: the case discloses ``window_seasons`` — its full observed
    trailing-window evidence (here exactly the one boundary row) — replacing
    the R8-era trusted ``window_high_season_count``."""
    boundary_row = {
        "season": first_season - 1,
        "rushing_yards": 401.0,
        "qualifying_games": 5,
        "decision_supported": False,
    }
    case: dict[str, Any] = {
        "player_id": "qb-boundary",
        "binary_dual_threat": True,
        "flips_at_minus_1_ypg": False,
        "flips_at_plus_1_ypg": True,
        "window_seasons": [dict(boundary_row)],
        "boundary_seasons": [dict(boundary_row)],
        "decision_supported": False,
    }
    case.update(overrides)
    return case


def _r10_high_row(first_season: int) -> dict[str, Any]:
    """A strong out-of-boundary window season: 500 yards / 5 games sits
    strictly above every ±1-ypg-shifted threshold (405), forcing base, minus
    and plus all True while never qualifying as a boundary row."""
    return {
        "season": first_season - 2,
        "rushing_yards": 500.0,
        "qualifying_games": 5,
        "decision_supported": False,
    }


def _r9_f13_fold(
    payload: dict[str, Any], case: dict[str, Any], **fold_overrides: Any
) -> None:
    """Install one boundary case as the fold's whole story.

    R11: unless the caller overrides ``evaluable_players``, the case's player
    is disclosed as the sole evaluable player, with the case's own window rows
    as the evidence (falling back to its boundary rows when a mutant deletes
    the window disclosure) — so mutants exercise their intended guard rather
    than an accidental pool mismatch."""
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    evidence_rows = case.get("window_seasons", case.get("boundary_seasons", []))
    fold.update(
        n_evaluable=1,
        dual_threat_count=1,
        pocket_count=0,
        evaluable_players=[
            {
                "player_id": case["player_id"],
                "window_seasons": [dict(row) for row in evidence_rows],
                "decision_supported": False,
            }
        ],
        boundary_case_count=1,
        boundary_cases=[case],
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=0,
    )
    fold.update(fold_overrides)


def test_r9_f13_missing_window_disclosure_refuses(tmp_path: Path) -> None:
    """A boundary case without the window_seasons evidence disclosure is not
    the produced schema — the flip recomputation would not be evidence-bound.
    (R10 reshaped this from the R8-era missing-count test.)"""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    del case["window_seasons"]
    _r9_f13_fold(payload, case, flips_at_plus_1_ypg=1)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_f13_false_negative_flip_refuses(tmp_path: Path) -> None:
    """Codex R8-G3 probe row: 401/5 mechanically flips at +1 ypg, but the
    case asserts False — an impossible asserted False now refuses. (R11: the
    fold total is set to the evidence-honest 1 so this exercises the per-case
    recomputation, not the fold-total check.)"""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season, flips_at_plus_1_ypg=False)
    _r9_f13_fold(payload, case, flips_at_plus_1_ypg=1)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_f13_aggregate_mismatch_refuses(tmp_path: Path) -> None:
    """Codex R8-G3 probe row: an honest case flip with a zero fold aggregate
    refuses — aggregates must EQUAL the case-row sums."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    _r9_f13_fold(payload, case)  # aggregate stays 0; the case flips
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r9_f13_reconciled_flip_publishes(tmp_path: Path) -> None:
    """Positive control: the genuine plus flip with a matching aggregate."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    _r9_f13_fold(payload, case, flips_at_plus_1_ypg=1)
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r9_f13_high_season_masks_flip_publishes(tmp_path: Path) -> None:
    """Production-truth positive control: a near season PLUS a strong
    out-of-boundary season (401/5 and a 500-yard year). Production honestly
    reports no flips; boundary rows alone would predict a plus flip. R10: the
    strong season is now a DISCLOSED window row, so the gate derives the
    no-flip answer from evidence — the naive boundary-rows-only rule would
    falsely refuse it."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season, flips_at_plus_1_ypg=False)
    case["window_seasons"].append(_r10_high_row(first_season))
    _r9_f13_fold(payload, case)
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r9_f13_high_season_with_binary_false_refuses(tmp_path: Path) -> None:
    """The binary gate is recomputed in both directions too: a disclosed high
    window row forces binary_dual_threat True; asserting False refuses."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(
        first_season,
        binary_dual_threat=False,
        flips_at_plus_1_ypg=False,
    )
    case["window_seasons"].append(_r10_high_row(first_season))
    _r9_f13_fold(payload, case, dual_threat_count=0, pocket_count=1)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


# ── Round 10: the two Codex R9 smallest corrections — G1 H5 admission
# implements the producer invariant · G2 F13 evidence totality ────────────────


def _first_h5_fold_entry(
    payload: dict[str, Any], registration: dict[str, Any], contrast: str = "c11"
) -> tuple[int, dict[str, Any]]:
    h5_seasons = set(registration["h5"]["folds"])
    fold = next(
        fold for fold in payload["folds"] if fold["test_season"] in h5_seasons
    )
    return fold["test_season"], fold["metrics_with_CIs"][contrast]


def test_r10_h5_deleted_computable_delta_refuses(tmp_path: Path) -> None:
    """Codex R9 probe row 1: a fold with both Spearmans and common_pool_n=24
    deletes only its delta and is claimed excluded (evaluable_folds=3). The
    producer would have COMPUTED that delta, so the record is impossible —
    calling it an honest exclusion no longer publishes."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    season, entry = _first_h5_fold_entry(payload, registration)
    entry["paired_delta"] = None
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(evaluable_folds=3, excluded_folds=_excluded_rows([season]))
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_h5_starved_fold_with_statistics_refuses(tmp_path: Path) -> None:
    """Codex R9 probe row 2: a common_pool_n=1 fold retaining non-null
    Spearmans and a delta was counted as evaluable despite the registered
    20-row floor. The producer nulls every statistic on a starved fold, so
    the record is impossible and refuses."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    _season, entry = _first_h5_fold_entry(payload, registration)
    entry["common_pool_n"] = 1
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_h5_delta_spearman_inconsistency_refuses(tmp_path: Path) -> None:
    """Codex R9 probe row 3: paired_delta=1.75 while the two published
    Spearmans subtract to -0.1 — typed-valid, arithmetically impossible."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    _season, entry = _first_h5_fold_entry(payload, registration)
    entry["paired_delta"] = 1.75
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_h5_floor_boundary_pool_admits(tmp_path: Path) -> None:
    """Positive control at the exact floor: common_pool_n=20 (the registered
    fold_min_evaluable_n) with a producer-exact delta stays evaluable — the
    floor is >=, not >."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    _season, entry = _first_h5_fold_entry(payload, registration)
    entry["common_pool_n"] = registration["fold_floors"]["fold_min_evaluable_n"]
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r10_h5_starved_honest_nulls_excluded_publishes(tmp_path: Path) -> None:
    """Positive control one row below the floor: common_pool_n=19 with all
    three statistics honestly null and the fold named among the exclusions
    publishes — the floor, not an empty pool, is the admission boundary."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    season, entry = _first_h5_fold_entry(payload, registration)
    entry.update(
        paired_delta=None,
        spearman_left=None,
        spearman_right=None,
        common_pool_n=registration["fold_floors"]["fold_min_evaluable_n"] - 1,
    )
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(evaluable_folds=3, excluded_folds=_excluded_rows([season]))
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


def test_r10_h5_starved_nulls_claimed_evaluable_refuses(tmp_path: Path) -> None:
    """The same honest below-floor nulls WITHOUT the exclusion claim refuse:
    the evaluable-season set is derived from the reconciled deltas, and a
    non-contributing fold cannot stay inside evaluable_folds=4."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    _season, entry = _first_h5_fold_entry(payload, registration)
    entry.update(
        paired_delta=None,
        spearman_left=None,
        spearman_right=None,
        common_pool_n=registration["fold_floors"]["fold_min_evaluable_n"] - 1,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_missing_fold_min_evaluable_n_is_registration_drift() -> None:
    """The floor binds FROM the registration: a fold_floors block without
    fold_min_evaluable_n is registration drift, never a silent default.
    Exercised at the gate directly — through the runner a mutated
    registration already refuses on the pin, which would leave this binding
    untested."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    qb.validate_registered_report_blocks(payload, registration=registration)
    del registration["fold_floors"]["fold_min_evaluable_n"]
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.validate_registered_report_blocks(payload, registration=registration)
    assert _reason(exc_info) == "registration_drift"
    assert "fold_min_evaluable_n" in str(exc_info.value)


def test_r10_f13_count_claim_without_evidence_refuses(tmp_path: Path) -> None:
    """Codex R9 probe row 4 replay: a case asserting window_high_season_count
    (here the probe's impossible 999) with no window_seasons evidence refuses
    — a caller total is no longer a disclosure at all."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season, flips_at_plus_1_ypg=False)
    del case["window_seasons"]
    case["window_high_season_count"] = 999
    _r9_f13_fold(payload, case)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_f13_window_row_outside_window_refuses(tmp_path: Path) -> None:
    """A fabricated high row parked outside the registered three-season
    trailing window cannot silence the genuine +1-ypg flip."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season, flips_at_plus_1_ypg=False)
    outside = _r10_high_row(first_season)
    outside["season"] = first_season - 4
    case["window_seasons"].append(outside)
    _r9_f13_fold(payload, case)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_f13_duplicate_window_season_refuses(tmp_path: Path) -> None:
    """One observed row per season: a repeated window season row refuses
    rather than double-weighting the derived classifications."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season, flips_at_plus_1_ypg=False)
    case["window_seasons"].append(_r10_high_row(first_season))
    case["window_seasons"].append(_r10_high_row(first_season))
    _r9_f13_fold(payload, case)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_f13_duplicate_player_rows_refuse(tmp_path: Path) -> None:
    """Codex R9 probe row 5: the same player row twice — the shipped producer
    emits at most one case per evaluable player, so the duplicate refuses.
    (R11: the pool discloses two distinct players and the fold totals carry
    the evidence-honest values, so this exercises the duplicate-case guard
    itself rather than a pool-size or total mismatch.)"""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    twin = json.loads(json.dumps(case))
    _r9_f13_fold(
        payload,
        case,
        n_evaluable=2,
        dual_threat_count=2,
        pocket_count=0,
        evaluable_players=[
            {
                "player_id": case["player_id"],
                "window_seasons": [dict(row) for row in case["window_seasons"]],
                "decision_supported": False,
            },
            {
                "player_id": "qb-other-dual",
                "window_seasons": [_r10_high_row(first_season)],
                "decision_supported": False,
            },
        ],
        boundary_case_count=2,
        boundary_cases=[case, twin],
        flips_at_plus_1_ypg=1,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_f13_boundary_subset_mismatch_refuses(tmp_path: Path) -> None:
    """boundary_seasons must be EXACTLY the boundary-band subset of the
    disclosed window rows: a concealed band row and a disagreeing row both
    refuse."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]

    # Concealed: a second band row (399/5) in the window, absent from
    # boundary_seasons.
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season, flips_at_minus_1_ypg=False)
    case["window_seasons"].append(
        {
            "season": first_season - 2,
            "rushing_yards": 399.0,
            "qualifying_games": 5,
            "decision_supported": False,
        }
    )
    _r9_f13_fold(payload, case, flips_at_plus_1_ypg=1)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))

    # Disagreeing: the boundary row's yards differ from the window row's.
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    case["boundary_seasons"][0]["rushing_yards"] = 402.0
    _r9_f13_fold(payload, case, flips_at_plus_1_ypg=1)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r10_f13_low_and_zero_game_window_rows_publish(tmp_path: Path) -> None:
    """Positive control for honest window evidence the band never touches: a
    LOW row (100/5, False under every shifted threshold) and a zero-game row
    (350/0 — the producer's weeks counter can honestly be 0) change nothing
    and must not refuse."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    case["window_seasons"].append(
        {
            "season": first_season - 2,
            "rushing_yards": 100.0,
            "qualifying_games": 5,
            "decision_supported": False,
        }
    )
    case["window_seasons"].append(
        {
            "season": first_season - 3,
            "rushing_yards": 350.0,
            "qualifying_games": 0,
            "decision_supported": False,
        }
    )
    _r9_f13_fold(payload, case, flips_at_plus_1_ypg=1)
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


# ── Round 11: the David-sanctioned F13 full-evidence redesign — the pool
# disclosure is total and every fold total derives from evidence ──────────────


def _r11_player(player_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "window_seasons": [dict(row) for row in rows],
        "decision_supported": False,
    }


def test_r11_f13_true_player_counted_as_pocket_refuses(tmp_path: Path) -> None:
    """Codex R10 probe row 1: the sole evaluable player's evidence (401/5)
    classifies dual, but the fold counts dual=0/pocket=1 — an impossible
    partition under the shipped producer now refuses."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    _r9_f13_fold(
        payload,
        case,
        dual_threat_count=0,
        pocket_count=1,
        flips_at_plus_1_ypg=1,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_false_player_counted_as_dual_refuses(tmp_path: Path) -> None:
    """Codex R10 probe row 2: at 399/5 the sole player is base-False with a
    genuine minus flip; counting them dual=1/pocket=0 refuses."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    row = {
        "season": first_season - 1,
        "rushing_yards": 399.0,
        "qualifying_games": 5,
        "decision_supported": False,
    }
    case = _r9_boundary_case(
        first_season,
        binary_dual_threat=False,
        flips_at_minus_1_ypg=True,
        flips_at_plus_1_ypg=False,
        window_seasons=[dict(row)],
        boundary_seasons=[dict(row)],
    )
    _r9_f13_fold(
        payload,
        case,
        dual_threat_count=1,
        pocket_count=0,
        flips_at_minus_1_ypg=1,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_missing_pool_disclosure_refuses(tmp_path: Path) -> None:
    """A fold without evaluable_players is not the produced schema — no fold
    total is verifiable without the pool evidence."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    del fold["evaluable_players"]
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_pool_disclosure_short_of_n_evaluable_refuses(
    tmp_path: Path,
) -> None:
    """One row per evaluable player, exactly: a two-player pool disclosing a
    single evidence row refuses."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold.update(n_evaluable=2, pocket_count=2)
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_duplicate_pool_player_refuses(tmp_path: Path) -> None:
    """The pool disclosure is one row per player — a repeated player_id
    refuses rather than double-counting a classification."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold.update(
        n_evaluable=2,
        pocket_count=2,
        evaluable_players=[
            _r11_player("qb-pocket", []),
            _r11_player("qb-pocket", []),
        ],
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_concealed_boundary_player_refuses(tmp_path: Path) -> None:
    """Membership totality: a disclosed player whose evidence carries a band
    season (401/5) with NO corresponding boundary case refuses — boundary
    membership can no longer be under-reported."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    band_row = {
        "season": first_season - 1,
        "rushing_yards": 401.0,
        "qualifying_games": 5,
        "decision_supported": False,
    }
    fold.update(
        dual_threat_count=1,
        pocket_count=0,
        evaluable_players=[_r11_player("qb-hidden", [band_row])],
        flips_at_plus_1_ypg=1,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_case_evidence_forked_from_pool_refuses(tmp_path: Path) -> None:
    """One evidence source: a boundary case whose window rows disagree with
    its player's disclosed pool evidence refuses — no forked story."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    _r9_f13_fold(payload, case, flips_at_plus_1_ypg=1)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold["evaluable_players"][0]["window_seasons"][0]["rushing_yards"] = 403.0
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_case_player_absent_from_pool_refuses(tmp_path: Path) -> None:
    """A boundary case citing a player the pool disclosure does not carry is
    fabricated evidence and refuses."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    _r9_f13_fold(
        payload,
        case,
        evaluable_players=[_r11_player("qb-somebody-else", [])],
        flips_at_plus_1_ypg=1,
    )
    _assert_schema_refusal(_publish_mutant(tmp_path, payload, registration))


def test_r11_f13_multi_player_pool_publishes(tmp_path: Path) -> None:
    """Positive control: a three-player pool — a clear dual (500-yard year),
    an empty-window pocket, and the 401/5 boundary flip — with every fold
    total carried at its evidence-derived value publishes."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]
    payload = _complete_ok_payload(registration)
    case = _r9_boundary_case(first_season)
    _r9_f13_fold(
        payload,
        case,
        n_evaluable=3,
        dual_threat_count=2,
        pocket_count=1,
        evaluable_players=[
            _r11_player(case["player_id"], case["window_seasons"]),
            _r11_player("qb-clear-dual", [_r10_high_row(first_season)]),
            _r11_player("qb-empty-pocket", []),
        ],
        flips_at_plus_1_ypg=1,
    )
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


# ── Round 12: the publication-gate boundary, ruled and pinned (David,
# 2026-08-16 — "accept the boundary"). The gate's registered guarantee is
# internal coherence + conformance to the frozen registration; provenance
# grounding is OUT of scope and owned by pinned inputs, the shipped
# composition, and the end-to-end contracts. These contracts prevent silent
# scope creep in BOTH directions: the documentation may not quietly vanish,
# the gate may not quietly grow a source-binding input, and the ruled
# disposition of the R11 probe shapes may not quietly change. ──────────────


def test_r12_gate_boundary_documentation_pinned() -> None:
    """The ruling lives in the gate itself; deleting it fails a contract.
    (Docstrings wrap, so phrases are matched whitespace-normalized.)"""
    for owner in (qb.validate_registered_report_blocks, qb.run_qb1_study):
        doc = " ".join((owner.__doc__ or "").split())
        assert "REGISTERED GUARANTEE AND ITS BOUNDARY" in doc
        assert "David's ruling, 2026-08-16" in doc
        assert "R11-G1-F13-SOURCE-TOTALITY" in doc
        assert "is OUTSIDE this gate's scope" in doc
        assert (
            "INTERNAL COHERENCE plus CONFORMANCE TO THE FROZEN REGISTRATION"
            in doc
        )


def test_r12_gate_signature_admits_no_source_binding() -> None:
    """The gate's only inputs are the report and the registration, and the
    runner's are its six registered parameters — widening either with a
    source-binding input requires a new David ruling, so the signatures are
    pinned as contracts."""
    import inspect

    gate_params = inspect.signature(qb.validate_registered_report_blocks).parameters
    assert list(gate_params) == ["blocks", "registration"]
    assert gate_params["registration"].kind is inspect.Parameter.KEYWORD_ONLY
    runner_params = inspect.signature(qb.run_qb1_study).parameters
    # R19 (registration read 86bace11…) sanctioned exactly ONE widening: the
    # optional OUTPUT-ONLY failure_observer sink. It binds no source — it
    # receives the closed diagnostic and returns nothing — so the pin's
    # purpose (no source-binding input without a David ruling) is unchanged.
    assert list(runner_params) == [
        "execute",
        "output_path",
        "registration_hash",
        "generated_at",
        "repo_root",
        "registration",
        "failure_observer",
    ]
    assert runner_params["failure_observer"].default is None
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in runner_params.values()
    )


def _r12_truthful_producer_fold(first_season: int) -> dict[str, Any]:
    """A truthful F13 fold from the SHIPPED producer: 401/5 → dual, boundary,
    +1-flip."""
    folds = [
        {
            "test_season": first_season,
            "test_rows": [
                {
                    "player_id": "qb-real",
                    "target": "target_evaluable",
                    "rush_yds_per_game": 80.2,
                    "rush_att_per_game": 8.0,
                }
            ],
        }
    ]
    rushing = {
        ("qb-real", first_season - 1): {"rushing_yards": 401.0, "weeks": 5}
    }
    return runner.build_archetype_threshold_panel(folds, rushing)[
        "binary_dual_threat_gate"
    ]["per_fold"][0]


def test_r12_source_totality_disposition_of_record(tmp_path: Path) -> None:
    """THE RULED DISPOSITION, EXECUTABLE (David, 2026-08-16): the two Codex
    R11 probe shapes — an internally consistent concealment story and an
    identity substitution — PUBLISH ok, because provenance grounding is out
    of the gate's registered scope. These publishes are the documented
    boundary, NOT defects. If a future change makes either refuse, the gate
    has grown provenance behavior without a ruling — that change must go
    back to David, and this contract exists to force that conversation."""
    registration = _registration()
    first_season = registration["folds"]["test_seasons"][0]

    # Codex R11 probe shape 1: complete observed window concealed as absence,
    # every derived field rewritten to the consistent pocket story.
    truthful = _r12_truthful_producer_fold(first_season)
    concealed = json.loads(json.dumps(truthful))
    concealed.update(
        dual_threat_count=0,
        pocket_count=1,
        evaluable_players=[_r11_player("qb-real", [])],
        boundary_case_count=0,
        boundary_cases=[],
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=0,
    )
    payload = _complete_ok_payload(registration)
    fold_slot = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]
    fold_slot["per_fold"][0] = concealed
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"

    # Codex R11 probe shape 2: the producer's player identity substituted,
    # evidence values kept exact.
    substituted = json.loads(json.dumps(truthful))
    substituted["evaluable_players"][0]["player_id"] = "qb-substitute"
    substituted["boundary_cases"][0]["player_id"] = "qb-substitute"
    payload = _complete_ok_payload(registration)
    fold_slot = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]
    fold_slot["per_fold"][0] = substituted
    report = _publish_mutant(tmp_path, payload, registration)
    assert report["run_status"] == "ok"


# ── Round 14: the provider PLACEHOLDER row — a registered-cohort
# IMPLEMENTATION per Codex's corrected registration read v2 (§3 player target
# + exact qualifying predicate; §2.1 complete scoring inputs; §4
# QB_at_matrix_build; §5 full-pool team aggregation) under David's fresh
# bounded word. The revised exact predicate: missing player_id AND missing
# position AND exact VALIDATED zero across all 17 D2 inputs (3 qualifying +
# 14 scoring), where "validated" is the label builder's own _stat_decimal
# semantics. Names are audit evidence, never predicate inputs. Applied only
# to the copied records passed to build_label_table; every nonmatching,
# unproven, malformed, nonzero, identified, or position-bearing row stays
# fail-closed. (This supersedes the Round-13 name-based tests — that
# predicate was refuted on the real store: 10/192 coverage.) ───────────────


_R13_SETTINGS = {
    "pass_yd": 0.04,
    "pass_td": 4.0,
    "pass_int": -2.0,
    "pass_2pt": 2.0,
    "rush_yd": 0.1,
    "rush_td": 6.0,
    "rush_2pt": 2.0,
    "rec": 1.0,
    "rec_yd": 0.1,
    "rec_td": 6.0,
    "rec_2pt": 2.0,
    "fum_lost": -2.0,
}


def _r13_weekly_row(
    player_id: Any = "00-0000001",
    player_name: Any = "Real Player",
    position: Any = "QB",
    season: int = 2024,
    week: int = 1,
    **stats: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "player_id": player_id,
        "player_name": player_name,
        "position": position,
        "season": season,
        "week": week,
        "season_type": "REG",
        "attempts": 10,
        "carries": 2,
        "sacks_suffered": 1,
        "passing_yards": 100,
        "passing_tds": 1,
        "passing_interceptions": 0,
        "rushing_yards": 10,
        "rushing_tds": 0,
        "receptions": 0,
        "receiving_yards": 0,
        "receiving_tds": 0,
        "sack_fumbles_lost": 0,
        "rushing_fumbles_lost": 0,
        "receiving_fumbles_lost": 0,
        "passing_2pt_conversions": 0,
        "rushing_2pt_conversions": 0,
        "receiving_2pt_conversions": 0,
    }
    row.update(stats)
    return row


_R14_D2_COLUMNS = (
    "attempts",
    "sacks_suffered",
    "carries",
    *[column for column, _key in qb.SCORING_COMPONENTS],
)


def _r14_placeholder(
    season: int = 2024,
    week: int = 1,
    *,
    pid: Any,
    position: Any = None,
    player_name: Any = None,
    zero: Any = 0,
    **overrides: Any,
) -> dict[str, Any]:
    """The MEASURED provider placeholder: missing id, missing position, exact
    zero across all 17 D2 inputs. ``zero`` lets fixtures cover both int 0 and
    float 0.0 typings; names are audit evidence, never predicate inputs."""
    row = _r13_weekly_row(
        player_id=pid,
        player_name=player_name,
        position=position,
        season=season,
        week=week,
        **{column: zero for column in _R14_D2_COLUMNS},
    )
    row.update(overrides)
    return row


def test_r14_seventeen_d2_inputs_are_exactly_the_builders() -> None:
    """The predicate's 17-column set is the label builder's OWN pinned set —
    3 qualifying inputs + the 14 SCORING_COMPONENTS columns — so the two can
    never drift apart silently."""
    assert len(_R14_D2_COLUMNS) == 17
    assert set(runner.PLACEHOLDER_D2_COLUMNS) == set(_R14_D2_COLUMNS)


def test_r14_placeholder_classifier_predicate_exact() -> None:
    """Excluded: the three MEASURED shapes (anonymous, "Team"-named,
    "R.Rodgers"-named — names never matter), both missing-id forms, both
    zero typings. Kept: near misses violating exactly ONE conjunct each —
    the mutant-per-guard rows. The input records are not mutated."""
    nan = float("nan")
    excluded_rows = [
        _r14_placeholder(week=1, pid=nan, zero=0.0),
        _r14_placeholder(week=2, pid=None, zero=0),
        _r14_placeholder(week=3, pid=nan, player_name="Team", zero=0.0),
        _r14_placeholder(week=4, pid=nan, player_name="R.Rodgers", zero=0),
        # "0" IS a validated zero: the builder's own _lossless_int parses
        # strings, so the predicate — the builder's exact semantics, never a
        # second authority — excludes it too (documented, not accidental).
        _r14_placeholder(week=13, pid=None, attempts="0"),
    ]
    kept_rows = [
        _r13_weekly_row(),
        # identified row, otherwise placeholder-shaped
        _r14_placeholder(week=5, pid="00-0000009"),
        # position present, otherwise placeholder-shaped
        _r14_placeholder(week=6, pid=None, position="QB"),
        # exactly one nonzero D2 cell
        _r14_placeholder(week=7, pid=None, rushing_yards=1.0),
        # unproven zeros: absent value, NaN, boolean False (bool-kind is
        # refused by the builder), a malformed string, a negative count, and
        # a MISSING D2 column — none is a VALIDATED zero
        _r14_placeholder(week=8, pid=None, receptions=None),
        _r14_placeholder(week=9, pid=None, passing_yards=nan),
        _r14_placeholder(week=10, pid=None, carries=False),
        _r14_placeholder(week=11, pid=None, attempts="zero"),
        _r14_placeholder(week=12, pid=None, receiving_tds=-1),
    ]
    missing_column = _r14_placeholder(week=13, pid=None)
    del missing_column["sacks_suffered"]
    kept_rows.append(missing_column)
    records = excluded_rows + kept_rows
    snapshot = [dict(row) for row in records]
    result = runner.exclude_provider_placeholder_rows(records)
    assert result == kept_rows
    assert records == snapshot, "the classifier must not mutate its input"
    assert result is not records, "the classifier returns a copy, not the input"


def test_r14_near_misses_remain_fail_closed_at_label_builder() -> None:
    """A kept near miss still refuses the WHOLE build at the label builder —
    the exclusion never widens the fail-closed guard."""
    for near_miss, reason in (
        (_r14_placeholder(pid=None, rushing_yards=7.0), "label_row_invalid"),
        (_r14_placeholder(pid=float("nan"), attempts="zero"), "label_row_invalid"),
        (_r14_placeholder(pid=None, position="QB"), "label_row_invalid"),
    ):
        records = runner.exclude_provider_placeholder_rows(
            [_r13_weekly_row(), near_miss]
        )
        assert len(records) == 2, "the near miss must be KEPT by the classifier"
        with pytest.raises(qb.QBValidationFailure) as exc_info:
            qb.build_label_table(
                records,
                _R13_SETTINGS,
                expected_settings_hash=qb.settings_hash(_R13_SETTINGS),
            )
        assert _reason(exc_info) == reason


def test_r14_label_seam_excludes_placeholders_and_labels_build() -> None:
    """The composition seam, positive control: a REG frame carrying all three
    measured placeholder shapes among real player rows — the placeholders
    (and ONLY the placeholders) leave the label input, the frame itself is
    untouched, and build_label_table then SUCCEEDS over the kept records
    (the exact stage both 2026-08-16 executions failed closed on)."""
    nan = float("nan")
    player_rows = [
        _r13_weekly_row(week=week, season=2024) for week in (1, 2, 3, 4)
    ]
    placeholder_rows = [
        _r14_placeholder(season=2024, week=1, pid=nan, zero=0.0),
        _r14_placeholder(season=2024, week=2, pid=None, player_name="Team"),
        _r14_placeholder(
            season=2024, week=3, pid=nan, player_name="R.Rodgers", zero=0.0
        ),
    ]
    post_row = _r13_weekly_row(week=5, season=2024, season_type="POST")
    frame = pd.DataFrame(player_rows + placeholder_rows + [post_row])
    before = frame.copy(deep=True)
    reg_records = runner.filter_reg_weekly_records(frame)
    label_records = runner.exclude_provider_placeholder_rows(reg_records)
    assert len(reg_records) == len(player_rows) + len(placeholder_rows)
    assert len(label_records) == len(player_rows)
    assert all(row["player_id"] == "00-0000001" for row in label_records)
    assert frame.equals(before), "the admitted frame must not be mutated"
    out = qb.build_label_table(
        label_records,
        _R13_SETTINGS,
        expected_settings_hash=qb.settings_hash(_R13_SETTINGS),
    )
    assert [row["player_id"] for row in out["labels"]] == ["00-0000001"]

    # Negative control: a stat-bearing missing-id row among the same frame
    # STAYS and refuses the build — unattributed production is never excused.
    poisoned = pd.DataFrame(
        player_rows + [_r14_placeholder(season=2024, week=4, pid=None, passing_yards=250.0)]
    )
    kept = runner.exclude_provider_placeholder_rows(
        runner.filter_reg_weekly_records(poisoned)
    )
    assert len(kept) == len(player_rows) + 1
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.build_label_table(
            kept,
            _R13_SETTINGS,
            expected_settings_hash=qb.settings_hash(_R13_SETTINGS),
        )
    assert _reason(exc_info) == "label_row_invalid"


# ── Round 15: the PBP parse seam — the registered `posteam → offense_team at
# parse` transformation (registration §5; §11's parsed admitted frame)
# applied at the admitted-snapshot read-back, per Codex's registration read
# (`qb1_pbp_parse_seam_registration_read_codex_v1.md`) and David's bounded
# word. One parser, one rename table; hash-before-parse and raw bytes
# preserved; named refusals everywhere. ────────────────────────────────────


def _r15_raw_pbp(rows: dict[str, list[Any]] | None = None) -> pd.DataFrame:
    base = {
        "season_type": ["REG", "POST", "REG"],
        "posteam": ["KC", "KC", "SF"],
        "pass": [1, 1, 0],
        "pass_oe": [0.1, 0.2, 0.3],
        "season": [2024, 2024, 2024],
        "week": [1, 19, 2],
    }
    if rows:
        base.update(rows)
    return pd.DataFrame(base)


def test_r15_seam_parses_pbp_readback_and_touches_nothing_else(
    tmp_path: Path,
) -> None:
    """Through the real seam: the pool's pbp frame comes back parsed
    (renamed, REG-only), every OTHER dataset's frame is untouched, the pbp
    provenance metadata is preserved, and the raw snapshot file's bytes are
    byte-identical after the call (hash-before-parse preserved)."""
    raw = _receipt(tmp_path, pbp_rows=2)
    pbp_file = raw / "pbp" / "pbp.parquet"
    raw_bytes_before = pbp_file.read_bytes()
    pool = qb.admit_and_load_validation_pool(
        raw, repo_root=tmp_path, frame_loader=_pool_frame_loader
    )
    parsed = pool["pbp"]["frame"]
    assert list(parsed.columns).count("offense_team") == 1
    assert "posteam" not in parsed.columns
    assert set(parsed["season_type"]) == {"REG"}
    assert pool["pbp"]["metadata"]["raw_snapshot_path"]
    assert pool["pbp"]["metadata"]["completeness"] == "ok"
    for name in DATASETS:
        if name == "pbp":
            continue
        assert list(pool[name]["frame"].columns) == ["x"]
    assert pbp_file.read_bytes() == raw_bytes_before


def test_r15_parse_is_the_ingestion_parser_itself() -> None:
    """No second parser, no competing rename table: the ingestion path passes
    the SAME public function the read-back seam calls, and the rename comes
    from the adapter's own pinned table."""
    import inspect

    from src.dynasty_genius.adapters import nflreadpy_qb_adapter as adapter

    ingestion_source = inspect.getsource(adapter.load_validation_pbp)
    assert "parse=parse_validation_pbp" in ingestion_source
    parse_source = inspect.getsource(adapter.parse_validation_pbp)
    assert 'VALIDATION_PARSED_RENAMES["pbp"]' in parse_source


def test_r15_parse_output_shape_and_non_reg_exclusion() -> None:
    """The registered semantics, directly: rename applied, POST rows never
    enter the parsed frame, input frame unmutated."""
    from src.dynasty_genius.adapters import nflreadpy_qb_adapter as adapter

    raw = _r15_raw_pbp()
    before = raw.copy(deep=True)
    parsed = adapter.parse_validation_pbp(raw)
    assert "offense_team" in parsed.columns
    assert "posteam" not in parsed.columns
    assert len(parsed) == 2
    assert set(parsed["week"]) == {1, 2}
    assert raw.equals(before), "the input frame must not be mutated"


def test_r15_reparse_refuses_named_normalize_once() -> None:
    """Normalize-once, enforced by refusal: an already-parsed frame lacks the
    parse's pinned source column, so a second parse REFUSES by the registered
    name rather than silently double-transforming."""
    from src.dynasty_genius.adapters import nflreadpy_qb_adapter as adapter

    parsed = adapter.parse_validation_pbp(_r15_raw_pbp())
    with pytest.raises(adapter.ValidationIngestError) as exc_info:
        adapter.parse_validation_pbp(parsed)
    assert exc_info.value.reason == "manifest_column_missing"
    assert "posteam" in exc_info.value.detail


def test_r15_missing_source_columns_refuse_named_through_the_seam(
    tmp_path: Path,
) -> None:
    """A read-back pbp frame missing the parse's pinned source columns
    refuses by the registered name AT THE SEAM (as a study failure), never a
    generic error and never a silently skipped transformation."""

    def shapeless(path: Path) -> pd.DataFrame:
        return pd.DataFrame({"x": [1]})

    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.admit_and_load_validation_pool(
            _receipt(tmp_path), repo_root=tmp_path, frame_loader=shapeless
        )
    assert _reason(exc_info) == "manifest_column_missing"
    assert "pbp" in str(exc_info.value)


def test_r15_zero_reg_rows_refuse_named() -> None:
    """An all-POST pbp frame refuses source_unavailable — the REG filter's
    own named guard, preserved through the shared parser."""
    from src.dynasty_genius.adapters import nflreadpy_qb_adapter as adapter

    all_post = _r15_raw_pbp({"season_type": ["POST", "POST", "POST"]})
    with pytest.raises(adapter.ValidationIngestError) as exc_info:
        adapter.parse_validation_pbp(all_post)
    assert exc_info.value.reason == "source_unavailable"


def test_r15_source_gate_receives_parsed_pbp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE RULED ORDERING, contract-pinned (Codex R15 provisional finding):
    the shared parse runs after receipt admission and BEFORE the F1 source
    gate, so the gate receives the PARSED pbp frame its own contract
    describes — offense_team present, posteam gone, REG-only — never the raw
    read-back."""
    seen: dict[str, list[str]] = {}
    real_gate = qb.execution.load_validation_sources

    def gate_spy(sources: Any) -> Any:
        seen["pbp_columns"] = list(sources["pbp"]["frame"].columns)
        seen["season_types"] = sorted(set(sources["pbp"]["frame"]["season_type"]))
        return real_gate(sources)

    monkeypatch.setattr(qb.execution, "load_validation_sources", gate_spy)
    qb.admit_and_load_validation_pool(
        _receipt(tmp_path, pbp_rows=2),
        repo_root=tmp_path,
        frame_loader=_pool_frame_loader,
    )
    assert "offense_team" in seen["pbp_columns"]
    assert "posteam" not in seen["pbp_columns"]
    assert seen["season_types"] == ["REG"]


# ── Round 16: ONE shared placeholder classifier for BOTH consumers (David's
# bounded word; Codex R15 registration read). The classifier moves to
# qb_ppg_labels beside its single-source _stat_decimal; the runner
# re-exports it for the label seam; the matrix applies it on defensive
# weekly records immediately before _validated_weekly_row. The pool and
# frame stay untouched through matrix entry/gates; near misses stay
# fail-closed; and the zero-content proof is WHOLE-REPORT EQUALITY: the
# hermetic composition with and without injected placeholders must produce
# IDENTICAL reports — team rushing totals included, by construction. ───────


def _r16_matrix_placeholder(season: int, week: int, pid: Any) -> dict[str, Any]:
    """A provider placeholder in the MATRIX fixture's weekly shape: missing
    id, missing position, every D2 input exactly zero (the extra
    matrix-fixture columns stay harmless nonzero-irrelevant)."""
    row = matrix_fixtures._weekly_row("ignored", season, week=week)
    row["player_id"] = pid
    row["player_name"] = None
    row["position"] = None
    for column in runner.PLACEHOLDER_D2_COLUMNS:
        row[column] = 0
    return row


def test_r16_shared_classifier_is_one_object() -> None:
    """Single source: the label consumer (runner) and the matrix consumer
    reference the SAME function object, living in qb_ppg_labels beside the
    _stat_decimal semantics it mirrors — and the matrix applies it to its
    weekly records before row validation."""
    import inspect

    from src.dynasty_genius.eval.qb_validation import qb_ppg_labels, study_matrix

    assert (
        runner.exclude_provider_placeholder_rows
        is qb_ppg_labels.exclude_provider_placeholder_rows
    )
    assert (
        study_matrix.exclude_provider_placeholder_rows
        is qb_ppg_labels.exclude_provider_placeholder_rows
    )
    assert runner.PLACEHOLDER_D2_COLUMNS is qb_ppg_labels.PLACEHOLDER_D2_COLUMNS
    matrix_source = inspect.getsource(study_matrix.build_study_matrix)
    assert "exclude_provider_placeholder_rows(" in matrix_source


def test_r16_composition_identical_with_and_without_placeholders(
    tmp_path: Path,
) -> None:
    """THE ZERO-CONTENT PROOF, whole-report form: injecting the ruled
    placeholder shapes (both missing-id forms) into the hermetic pool's
    weekly frame changes NOTHING — the composed report is IDENTICAL to the
    placeholder-free run, so the all-position team rushing totals, folds,
    contrasts, and panels are unchanged by construction."""
    baseline = runner.compose_study(
        registration=_registration(),
        pool=_hermetic_pool(tmp_path / "clean"),
        repo_root=tmp_path / "clean",
        **_h5_inputs(tmp_path / "clean"),
    )
    pool = _hermetic_pool(tmp_path / "salted")
    weekly = pool["weekly"]["frame"]
    placeholders = pd.DataFrame(
        [
            _r16_matrix_placeholder(2021, 1, None),
            _r16_matrix_placeholder(2022, 2, float("nan")),
        ]
    )
    pool["weekly"]["frame"] = pd.concat([weekly, placeholders], ignore_index=True)
    salted = runner.compose_study(
        registration=_registration(),
        pool=pool,
        repo_root=tmp_path / "salted",
        **_h5_inputs(tmp_path / "salted"),
    )
    # The inputs block's raw dataset_rows disclosure HONESTLY differs by the
    # two injected raw rows; every analytical block must be IDENTICAL.
    assert salted["inputs"]["dataset_rows"]["weekly"] == (
        baseline["inputs"]["dataset_rows"]["weekly"] + 2
    )
    salted_analytic = {k: v for k, v in salted.items() if k != "inputs"}
    baseline_analytic = {k: v for k, v in baseline.items() if k != "inputs"}
    assert salted_analytic == baseline_analytic
    salted_inputs = {
        k: v for k, v in salted["inputs"].items() if k != "dataset_rows"
    }
    baseline_inputs = {
        k: v for k, v in baseline["inputs"].items() if k != "dataset_rows"
    }
    assert salted_inputs == baseline_inputs


def test_r16_matrix_near_misses_remain_fail_closed(tmp_path: Path) -> None:
    """A stat-bearing or position-bearing missing-id weekly row still refuses
    the WHOLE matrix build by the registered name — the shared exclusion
    never widens the matrix's fail-closed identity law."""
    for mutate in (
        lambda row: row.__setitem__("rushing_yards", 7),
        lambda row: row.__setitem__("position", "QB"),
    ):
        pool = _hermetic_pool(tmp_path / "near")
        near_miss = _r16_matrix_placeholder(2021, 3, None)
        mutate(near_miss)
        pool["weekly"]["frame"] = pd.concat(
            [pool["weekly"]["frame"], pd.DataFrame([near_miss])],
            ignore_index=True,
        )
        with pytest.raises(qb.QBValidationFailure) as exc_info:
            runner.compose_study(
                registration=_registration(),
                pool=pool,
                repo_root=tmp_path / "near",
                **_h5_inputs(tmp_path / "near"),
            )
        # The near miss is refused by the FIRST consumer it reaches: the
        # label builder (label_row_invalid) refuses missing-id near misses
        # before the matrix runs; a matrix-only shape would refuse
        # stat_value_invalid. Either registered name proves fail-closed.
        assert _reason(exc_info) in {"label_row_invalid", "stat_value_invalid"}


# ── R17 (revision 104, David's bounded word; Codex registration read
# `qb1_season_summary_aggregate_registration_read_codex_v1.md`): a PRIVATE
# season_summary non-player aggregate classifier at matrix stage 1b. Exact
# conjunction: missing player_id AND valid registered study season AND missing
# position AND null passing_cpoe AND games an exact validated integer >= 256.
# Names audit-only; near misses fall through to the stage-1b fail-closed law;
# whole-report equality with/without injected exact aggregates. ─────────────


def _r17_summary_aggregate(season: int, *, name: Any = None) -> dict[str, Any]:
    """The exact measured provider LEAGUE-AGGREGATE season_summary shape:
    missing id + missing position + null passing_cpoe + full-league games."""
    return {
        "player_id": None,
        "player_name": name,
        "season": season,
        "position": None,
        "passing_cpoe": None,
        "games": 272,
    }


def test_r17_summary_classifier_is_private_and_applied() -> None:
    """The classifier is study_matrix-PRIVATE (not shared, not exported, not
    in qb_ppg_labels or the runner) and build_study_matrix applies it to its
    season_summary records before the stage-1b loop."""
    import inspect

    from src.dynasty_genius.eval.qb_validation import qb_ppg_labels, study_matrix

    assert hasattr(study_matrix, "_exclude_provider_season_aggregate_rows")
    assert not hasattr(qb_ppg_labels, "_exclude_provider_season_aggregate_rows")
    assert not hasattr(runner, "_exclude_provider_season_aggregate_rows")
    assert not hasattr(qb, "_exclude_provider_season_aggregate_rows")
    matrix_source = inspect.getsource(study_matrix.build_study_matrix)
    assert "_exclude_provider_season_aggregate_rows(" in matrix_source


def test_r17_exact_aggregate_classifies_and_int_law_holds() -> None:
    """Positive control: the exact five-clause shape classifies — including
    the documented `_lossless_int` fact that a numeric STRING games count is
    a validated integer (the R14 precedent, disclosed not smoothed) — and a
    plain kept row passes through untouched."""
    from src.dynasty_genius.eval.qb_validation import study_matrix

    exclude = study_matrix._exclude_provider_season_aggregate_rows
    kept_row = {
        "player_id": "00-0000001",
        "season": 2021,
        "position": "QB",
        "passing_cpoe": 1.5,
        "games": 16,
    }
    rows = [
        _r17_summary_aggregate(2021),
        _r17_summary_aggregate(2015, name="Team"),
        _r17_summary_aggregate(2018, name="R.Rodgers"),
        {**_r17_summary_aggregate(2022), "games": 256},
        {**_r17_summary_aggregate(2023), "games": "272"},
        {**_r17_summary_aggregate(2024), "player_id": float("nan")},
        kept_row,
    ]
    survivors = exclude(rows)
    assert survivors == [kept_row]
    assert rows[-1] is survivors[0]


def test_r17_one_field_mutants_never_classify() -> None:
    """Each single-field deviation from the exact conjunction is KEPT (near
    misses fall through to the stage-1b fail-closed law): usable player_id ·
    present position · non-null passing_cpoe · missing/invalid/out-of-window
    season · missing / non-integral / bool-kind / <256 games."""
    from src.dynasty_genius.eval.qb_validation import study_matrix

    exclude = study_matrix._exclude_provider_season_aggregate_rows
    mutants = [
        {**_r17_summary_aggregate(2021), "player_id": "00-0034857"},
        {**_r17_summary_aggregate(2021), "position": "QB"},
        {**_r17_summary_aggregate(2021), "position": " K "},
        {**_r17_summary_aggregate(2021), "passing_cpoe": 0.0},
        {**_r17_summary_aggregate(2021), "passing_cpoe": -2.25},
        {**_r17_summary_aggregate(2021), "season": None},
        {**_r17_summary_aggregate(2021), "season": float("nan")},
        {**_r17_summary_aggregate(2021), "season": 1990},
        {**_r17_summary_aggregate(2021), "season": 2026},
        {**_r17_summary_aggregate(2021), "games": None},
        {**_r17_summary_aggregate(2021), "games": float("nan")},
        {**_r17_summary_aggregate(2021), "games": 255},
        {**_r17_summary_aggregate(2021), "games": 271.5},
        {**_r17_summary_aggregate(2021), "games": True},
        {**_r17_summary_aggregate(2021), "games": "gales"},
    ]
    missing_games = dict(_r17_summary_aggregate(2021))
    del missing_games["games"]
    mutants.append(missing_games)
    assert exclude(mutants) == mutants


def test_r17_composition_identical_with_and_without_aggregates(
    tmp_path: Path,
) -> None:
    """Whole-report equality: injecting the exact aggregate shapes (both
    missing-id forms, one name-bearing) into the hermetic pool's
    season_summary frame changes NOTHING analytical — only the raw
    dataset_rows disclosure honestly grows by the injected rows."""
    baseline = runner.compose_study(
        registration=_registration(),
        pool=_hermetic_pool(tmp_path / "clean"),
        repo_root=tmp_path / "clean",
        **_h5_inputs(tmp_path / "clean"),
    )
    pool = _hermetic_pool(tmp_path / "salted")
    summary = pool["season_summary"]["frame"]
    aggregates = pd.DataFrame(
        [
            _r17_summary_aggregate(2021),
            {**_r17_summary_aggregate(2022, name="Team"), "player_id": float("nan")},
        ]
    )
    pool["season_summary"]["frame"] = pd.concat(
        [summary, aggregates], ignore_index=True
    )
    salted = runner.compose_study(
        registration=_registration(),
        pool=pool,
        repo_root=tmp_path / "salted",
        **_h5_inputs(tmp_path / "salted"),
    )
    assert salted["inputs"]["dataset_rows"]["season_summary"] == (
        baseline["inputs"]["dataset_rows"]["season_summary"] + 2
    )
    salted_analytic = {k: v for k, v in salted.items() if k != "inputs"}
    baseline_analytic = {k: v for k, v in baseline.items() if k != "inputs"}
    assert salted_analytic == baseline_analytic
    salted_inputs = {
        k: v for k, v in salted["inputs"].items() if k != "dataset_rows"
    }
    baseline_inputs = {
        k: v for k, v in baseline["inputs"].items() if k != "dataset_rows"
    }
    assert salted_inputs == baseline_inputs


def test_r17_summary_near_misses_still_refuse_composition(
    tmp_path: Path,
) -> None:
    """A missing-id season_summary near miss (content-bearing CPOE, or a
    sub-league games count) still refuses the WHOLE composition by the
    registered stage-1b name — exclusion never widens into forgiveness."""
    for mutate in (
        lambda row: row.__setitem__("passing_cpoe", 3.5),
        lambda row: row.__setitem__("games", 12),
    ):
        pool = _hermetic_pool(tmp_path / "near")
        near_miss = _r17_summary_aggregate(2021)
        mutate(near_miss)
        pool["season_summary"]["frame"] = pd.concat(
            [pool["season_summary"]["frame"], pd.DataFrame([near_miss])],
            ignore_index=True,
        )
        with pytest.raises(qb.QBValidationFailure) as exc_info:
            runner.compose_study(
                registration=_registration(),
                pool=pool,
                repo_root=tmp_path / "near",
                **_h5_inputs(tmp_path / "near"),
            )
        assert _reason(exc_info) == "stat_value_invalid"


# ── R18 (revision 111, David's bounded word; Codex registration read
# `qb1_f34_college_normalization_registration_read_codex_v1.md`): the exact
# registered F34 college normalization — study `college_name` split on literal
# `;` into independently normalized institution tokens; draft college
# normalized under the same law; terminal-token-boundary expansions ONLY
# (`st`→`state`, `col`→`college`); the CLOSED exact alias set ONLY; pass iff
# the canonical draft institution is an EXACT member of the canonical study
# set; disjoint stays conflict; missing stays missing. No substring/fuzzy
# matching, no open-ended heuristics, no allowlists, no bypass. ─────────────

from src.dynasty_genius.eval.qb_validation.identity import (  # noqa: E402
    _college_check as _r18_college_check,
)
from src.dynasty_genius.eval.qb_validation.identity import (  # noqa: E402
    resolve_draft_join as _r18_resolve,
)


def _r18_study(college: Any, **over: Any) -> dict[str, Any]:
    row = {
        "gsis_id": "00-0034857",
        "display_name": "Josh Allen",
        "birth_date": "1996-05-21",
        "college_name": college,
    }
    row.update(over)
    return row


def _r18_draft(college: Any, **over: Any) -> dict[str, Any]:
    row = {
        "gsis_id": "00-0034857",
        "pfr_player_name": "Josh Allen",
        "season": 2018,
        "round": 1,
        "pick": 7,
        "age": 22,
        "college": college,
    }
    row.update(over)
    return row


def _r18_join(study_college: Any, draft_college: Any) -> dict[str, Any]:
    return _r18_resolve(
        _r18_study(study_college), [_r18_draft(draft_college)]
    )


def test_r18_canonicalizer_is_private_to_the_college_check() -> None:
    """The canonicalization path is identity-PRIVATE, referenced by
    _college_check, and the name-matching route still uses plain
    normalize_name (no college law leaks into player-name joining)."""
    import inspect

    from src.dynasty_genius.eval.qb_validation import identity

    assert hasattr(identity, "_canonical_college_institution")
    assert not hasattr(qb, "_canonical_college_institution")
    check_source = inspect.getsource(identity._college_check)
    assert "_canonical_college_institution" in check_source
    resolver_source = inspect.getsource(identity.resolve_draft_join)
    assert "_canonical_college_institution" not in resolver_source


def test_r18_multi_school_member_resolves_drafted() -> None:
    """The 23-player class: a semicolon history CONTAINING the draft school
    joins DRAFTED with the original capital."""
    record = _r18_join("Wyoming; Reedley", "Wyoming")
    assert record["resolution"] == "DRAFTED"
    assert record["draft_round"] == 1
    assert record["draft_overall"] == 7
    assert record["is_udfa"] == 0
    record = _r18_join("Sam Houston State; SMU; Wyoming", "Wyoming")
    assert record["resolution"] == "DRAFTED"


def test_r18_compound_multi_school_alias_resolves_drafted() -> None:
    """The 4-player COMPOUND class: multi-school history AND draft-side
    terminal-token abbreviation."""
    for study_college, draft_college in (
        ("Sam Houston State; SMU", "Sam Houston St."),
        ("San Jose State; Monterey Peninsula; Nevada", "San Jose St."),
        ("N.C. State; Florida", "North Carolina St."),
        ("N.C. State; Boise State", "North Carolina St."),
    ):
        record = _r18_join(study_college, draft_college)
        assert record["resolution"] == "DRAFTED", (study_college, draft_college)


def test_r18_single_school_alias_and_terminal_classes_resolve_drafted() -> None:
    """The 22-player class: every closed alias rule and both terminal-token
    expansions, in BOTH directions (the law is side-symmetric)."""
    for study_college, draft_college in (
        ("Boston College", "Boston Col."),
        ("Boston Col.", "Boston College"),
        ("N.C. State", "North Carolina St."),
        ("North Carolina State", "N.C. State"),
        ("UCF", "Central Florida"),
        ("Central Florida", "UCF"),
        ("Miami (Ohio)", "Miami (OH)"),
        ("Miami (OH)", "Miami (Ohio)"),
        ("UAB", "Ala-Birmingham"),
        ("Ala-Birmingham", "UAB"),
        ("Sam Houston State", "Sam Houston St."),
    ):
        record = _r18_join(study_college, draft_college)
        assert record["resolution"] == "DRAFTED", (study_college, draft_college)


def test_r18_negative_controls_remain_triage() -> None:
    """The two pinned real negative controls — true wrong-college joins the
    cross-check EXISTS to catch — remain TRIAGE, never DRAFTED/UDFA."""
    griffin = _r18_resolve(
        _r18_study(
            "Tulane",
            gsis_id="00-0029857",
            display_name="Ryan Griffin",
            birth_date="1989-11-15",
        ),
        [
            _r18_draft(
                "Connecticut",
                gsis_id="00-0029857",
                pfr_player_name="Ryan Griffin",
                season=2013,
                round=6,
                pick=201,
                age=23,
            )
        ],
    )
    assert griffin["resolution"] == "TRIAGE"
    assert griffin["reason"] == "cross_check_conflict"
    brown = _r18_resolve(
        _r18_study(
            "Oregon; Boston College",
            gsis_id="00-0037175",
            display_name="Anthony Brown",
            birth_date="1998-05-15",
        ),
        [
            _r18_draft(
                "Purdue",
                gsis_id="00-0037175",
                pfr_player_name="Anthony Brown",
                season=2022,
                round=6,
                pick=200,
                age=24,
            )
        ],
    )
    assert brown["resolution"] == "TRIAGE"
    assert brown["reason"] == "cross_check_conflict"


def test_r18_near_misses_remain_fail_closed() -> None:
    """One-field near misses: everything outside the exact closed law keeps
    the shipped conflict/missing behavior."""
    # True non-member colleges — disjoint stays conflict.
    for study_college, draft_college in (
        ("Tulane", "Connecticut"),
        ("Oregon; Boston College", "Purdue"),
        # Substring/prefix matching is FORBIDDEN — near-matches stay conflict.
        ("North Carolina", "North Carolina State"),
        ("Wyoming; Reedley", "Wyo"),
        # Non-TERMINAL 'st' token is never expanded.
        ("St. Johns", "State Johns"),
        # Aliases are a CLOSED set — no open-ended equivalence.
        ("Miami (Fla.)", "Miami (Ohio)"),
        ("USC", "Southern California"),
    ):
        assert _r18_college_check(
            _r18_study(study_college), _r18_draft(draft_college)
        ) == {"result": "conflict"}, (study_college, draft_college)
    # Missing/empty college on either side stays the registered missing law.
    for study_college, draft_college in (
        (None, "Wyoming"),
        (float("nan"), "Wyoming"),
        ("", "Wyoming"),
        ("; ;", "Wyoming"),
        ("Wyoming", None),
        ("Wyoming", ""),
    ):
        assert _r18_college_check(
            _r18_study(study_college), _r18_draft(draft_college)
        ) == {"result": "missing"}, (study_college, draft_college)


# ── R19: metric-free failure-origin observability (two-catch law) ──────────────
# Registration read 86bace11…: on a FAILED run the publication function may
# expose ONE closed diagnostic — {"phase": "execute"|"publication_gate",
# "sites": [{"path", "function", "line"}, …]} — to an optional in-memory
# observer; only the CLI stdout summary persists it. Raw failure.detail,
# rejected payloads, and exception text are NEVER serialized anywhere. The
# failed terminal artifact stays the exact six-key metric-free envelope.


_R19_SENTINEL_DETAIL = "R19-SENTINEL-DELTA--0.987654321--NEVER-PERSISTED"
_R19_SENTINEL_MESSAGE = "R19-SENTINEL-SECRET-MESSAGE--424242--NEVER-PERSISTED"
_R19_CONTRACTS_PATH = "tests/contract/test_qb1_green_correction_contracts.py"
_R19_EXECUTION_PATH = "src/dynasty_genius/eval/qb_validation/execution.py"
_R19_ENVELOPE_KEYS = [
    "decision_supported",
    "failure_reason",
    "generated_at",
    "registration_hash",
    "run_status",
    "schema_version",
]


def _r19_refusing_helper() -> None:
    raise qb.QBValidationFailure("stat_value_invalid", _R19_SENTINEL_DETAIL)


def _r19_execute_raises() -> dict[str, Any]:
    _r19_refusing_helper()
    raise AssertionError("unreachable")


def _r19_run(
    tmp_path: Path,
    execute: Any,
    *,
    registration: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
    sink: list[dict[str, Any]] = []
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    report = qb.run_qb1_study(
        execute=execute,
        output_path=destination,
        registration_hash=PIN,
        generated_at="2026-08-16T23:30:00Z",
        repo_root=tmp_path,
        registration=registration,
        failure_observer=sink.append,
    )
    return report, destination, sink


def _r19_failed_envelope(destination: Path, reason: str) -> dict[str, Any]:
    artifact = json.loads(destination.read_text())
    assert sorted(artifact) == _R19_ENVELOPE_KEYS
    assert artifact["run_status"] == "failed"
    assert artifact["failure_reason"] == reason
    assert artifact["decision_supported"] is False
    return artifact


def test_r19_execute_path_diagnostic_phase_and_exact_tail(tmp_path: Path) -> None:
    """Matrix rows 1+3: execute-path QBValidationFailure → phase=execute with
    the exact repository-relative tail; the helper-mediated refusal keeps the
    caller AND raise-origin frames distinguishable."""
    _report, destination, sink = _r19_run(tmp_path, _r19_execute_raises)
    _r19_failed_envelope(destination, "stat_value_invalid")
    assert len(sink) == 1
    diagnostic = sink[0]
    assert sorted(diagnostic) == ["phase", "sites"]
    assert diagnostic["phase"] == "execute"
    sites = diagnostic["sites"]
    assert isinstance(sites, list) and sites
    for site in sites:
        assert sorted(site) == ["function", "line", "path"]
        assert isinstance(site["line"], int) and not isinstance(site["line"], bool)
        assert site["line"] > 0
    assert [site["function"] for site in sites[-2:]] == [
        "_r19_execute_raises",
        "_r19_refusing_helper",
    ]
    assert sites[-1]["path"] == _R19_CONTRACTS_PATH
    assert sites[-2]["path"] == _R19_CONTRACTS_PATH
    # The raise origin is exact: the helper's sole body line.
    assert sites[-1]["line"] == _r19_refusing_helper.__code__.co_firstlineno + 1


def test_r19_publication_gate_diagnostic_phase_and_origin(tmp_path: Path) -> None:
    """Matrix row 2: a post-result report_schema_invalid → phase=
    publication_gate with the in-repository raise origin inside the runner."""
    _report, destination, sink = _r19_run(
        tmp_path, lambda: {"run_status": "ok", "r19_bogus_key": 1}
    )
    _r19_failed_envelope(destination, "report_schema_invalid")
    assert len(sink) == 1
    diagnostic = sink[0]
    assert diagnostic["phase"] == "publication_gate"
    sites = diagnostic["sites"]
    assert isinstance(sites, list) and sites
    assert sites[-1]["path"] == _R19_EXECUTION_PATH
    assert sites[-1]["function"] == "run_qb1_study"


def test_r19_sentinels_never_reach_artifact_or_diagnostic(tmp_path: Path) -> None:
    """Matrix row 4: sentinel values planted in failure.detail AND in a
    rejected payload value (interpolated into the gate's detail) must occur
    nowhere in the terminal artifact or the emitted diagnostic."""
    _report, destination, sink = _r19_run(tmp_path, _r19_execute_raises)
    for blob in (destination.read_text(), json.dumps(sink)):
        assert _R19_SENTINEL_DETAIL not in blob
    gate_dir = tmp_path / "gate"
    _report2, destination2, sink2 = _r19_run(
        gate_dir, lambda: {"run_status": _R19_SENTINEL_DETAIL}
    )
    _r19_failed_envelope(destination2, "report_schema_invalid")
    for blob in (destination2.read_text(), json.dumps(sink2)):
        assert _R19_SENTINEL_DETAIL not in blob


def test_r19_execution_error_emits_no_diagnostic_and_no_message(
    tmp_path: Path,
) -> None:
    """Matrix row 5: the ordinary-Exception path keeps the established
    execution_error reason, emits NO diagnostic, and serializes neither the
    message nor local state."""

    def boom() -> dict[str, Any]:
        local_state_that_must_not_persist = _R19_SENTINEL_MESSAGE
        raise ValueError(local_state_that_must_not_persist)

    _report, destination, sink = _r19_run(tmp_path, boom)
    _r19_failed_envelope(destination, "execution_error")
    assert sink == []
    assert _R19_SENTINEL_MESSAGE not in destination.read_text()


def test_r19_observer_absent_keeps_established_behavior(tmp_path: Path) -> None:
    """Matrix row 6a (regression guard, green pre-implementation): the
    observer-less runner surface is untouched."""
    _report, destination = _run(tmp_path, _r19_execute_raises)
    _r19_failed_envelope(destination, "stat_value_invalid")


def test_r19_throwing_observer_never_blocks_the_artifact(tmp_path: Path) -> None:
    """Matrix row 6b: a deliberately throwing observer neither suppresses nor
    corrupts the atomic failed artifact."""
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"

    def exploding(_diagnostic: Any) -> None:
        raise RuntimeError("observer failure must be swallowed")

    report = qb.run_qb1_study(
        execute=_r19_execute_raises,
        output_path=destination,
        registration_hash=PIN,
        generated_at="2026-08-16T23:30:00Z",
        repo_root=tmp_path,
        failure_observer=exploding,
    )
    assert report["run_status"] == "failed"
    _r19_failed_envelope(destination, "stat_value_invalid")


def test_r19_success_emits_no_diagnostic(tmp_path: Path) -> None:
    """Matrix row 7: a successful publication emits no failure diagnostic."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    report, _destination, sink = _r19_run(
        tmp_path, lambda: payload, registration=registration
    )
    assert report["run_status"] == "ok"
    assert sink == []


def test_r19_site_paths_are_repo_relative_without_traversal(
    tmp_path: Path,
) -> None:
    """Matrix row 8: every site path is repository-relative — never absolute,
    never traversing — and out-of-repository frames are omitted."""
    _report, _destination, sink = _r19_run(tmp_path, _r19_execute_raises)
    assert sink
    for site in sink[0]["sites"]:
        path = Path(site["path"])
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert path.parts[0] in {"src", "scripts", "tests"}


def _r19_cli_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cheap in-repo stubs for the CLI probes: every pre-composition step is
    inert so the probe exercises ONLY the runner's catch/publication seam."""
    monkeypatch.setattr(runner, "load_registration", lambda _root: _registration())
    monkeypatch.setattr(qb, "enforce_consumer_boundary", lambda *, repo_root: None)
    monkeypatch.setattr(
        runner, "load_crosswalk", lambda _root: ([], "2026-08-16T00:00:00Z")
    )
    monkeypatch.setattr(qb, "admit_and_load_validation_pool", lambda *_a, **_k: {})
    monkeypatch.setattr(qb, "load_h5_snapshots", lambda *_a, **_k: [])


def test_r19_cli_execute_phase_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI-level synthetic probe, execute phase: the stdout summary of a failed
    run carries the closed diagnostic; sentinels never reach stdout or disk."""
    _r19_cli_stubs(monkeypatch)

    def refusing_boundary(*, repo_root: Path) -> None:
        _r19_refusing_helper()

    monkeypatch.setattr(qb, "enforce_consumer_boundary", refusing_boundary)
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    code = runner.main(repo_root=tmp_path, output_path=destination)
    out = capsys.readouterr().out
    assert code == 1
    payload = json.loads(out)
    assert payload["run_status"] == "failed"
    assert payload["failure_reason"] == "stat_value_invalid"
    assert payload["decision_supported"] is False
    origin = payload["failure_origin"]
    assert sorted(origin) == ["phase", "sites"]
    assert origin["phase"] == "execute"
    assert origin["sites"][-1]["function"] == "_r19_refusing_helper"
    assert origin["sites"][-1]["path"] == _R19_CONTRACTS_PATH
    assert _R19_SENTINEL_DETAIL not in out
    assert _R19_SENTINEL_DETAIL not in destination.read_text()


def test_r19_cli_publication_gate_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI-level synthetic probe, publication-gate phase: the sentinel planted
    as a rejected payload value (interpolated into the refusing clause's
    detail) reaches neither stdout nor the terminal artifact."""
    _r19_cli_stubs(monkeypatch)
    monkeypatch.setattr(
        runner, "compose_study", lambda **_k: {"run_status": _R19_SENTINEL_DETAIL}
    )
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    code = runner.main(repo_root=tmp_path, output_path=destination)
    out = capsys.readouterr().out
    assert code == 1
    payload = json.loads(out)
    assert payload["failure_reason"] == "report_schema_invalid"
    origin = payload["failure_origin"]
    assert origin["phase"] == "publication_gate"
    # The refusal is helper-mediated (matrix row 3 at CLI level): the payload
    # passes the runner's own checks and is refused one frame deeper, inside
    # assemble_terminal_report — the tail keeps caller AND origin distinct.
    assert origin["sites"][-1]["path"] == _R19_EXECUTION_PATH
    assert origin["sites"][-1]["function"] == "assemble_terminal_report"
    assert "run_qb1_study" in [site["function"] for site in origin["sites"]]
    assert _R19_SENTINEL_DETAIL not in out
    assert _R19_SENTINEL_DETAIL not in destination.read_text()


def test_r19_cli_success_stdout_surface_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Matrix row 7, CLI surface: a successful run's stdout summary keeps the
    established four keys exactly — no diagnostic key appears."""
    _r19_cli_stubs(monkeypatch)
    registration = _registration()
    monkeypatch.setattr(runner, "load_registration", lambda _root: registration)
    monkeypatch.setattr(
        runner, "compose_study", lambda **_k: _complete_ok_payload(registration)
    )
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    code = runner.main(repo_root=tmp_path, output_path=destination)
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert sorted(payload) == [
        "decision_supported",
        "failure_reason",
        "run_status",
        "terminal_artifact",
    ]
    assert payload["run_status"] == "ok"
    assert payload["failure_reason"] is None


# ── R20: terminal-adapter exclusion-reason canonicalization ────────────────────
# Registration read 0453ca80…: the internal inference layer LOSSLESSLY carries
# `empty_common_pool`; the frozen terminal vocabulary does not register it.
# The registered implication (common_pool_n == 0 → below the registered
# fold_min_evaluable_n floor of 20 → the registered below_min_n_flag
# `fold_starved`) authorizes the terminal-report adapter — and ONLY it — to
# drop the internal word where `fold_starved` co-occurs. Everything outside
# that exact implication refuses `report_schema_invalid` by name. The gate,
# vocabulary, registration, comparisons.py, and inference.py are untouched.


_R20_MEASURED_REASONS = ["empty_common_pool", "fold_starved", "degenerate_input"]
_R20_H5_IDS = ["c11", "c12", "c13", "c14"]
_R20_MEASURED_SEASONS = [2021, 2022, 2023]


def _r20_entry(
    season: int = 2021, reasons: Any = None, **extra: Any
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "test_season": season,
        "reasons": list(_R20_MEASURED_REASONS) if reasons is None else reasons,
        "decision_supported": False,
    }
    entry.update(extra)
    return entry


def test_r20_measured_shape_canonicalizes_exactly() -> None:
    """Matrix rows 1+6+8(lossless): the measured triple maps to
    [fold_starved, degenerate_input] with order preserved, every output word
    in the UNCHANGED vocabulary, and the internal input record unmutated."""
    source = [_r20_entry()]
    source_snapshot = json.loads(json.dumps(source))
    out = runner._canonical_excluded_folds(source)
    assert out[0]["reasons"] == ["fold_starved", "degenerate_input"]
    assert list(out[0]) == ["test_season", "reasons", "decision_supported"]
    assert out[0]["test_season"] == 2021
    assert out[0]["decision_supported"] is False
    for word in out[0]["reasons"]:
        assert word in qb.execution._FOLD_FLAG_VOCABULARY
    # The adapter canonicalizes a COPY — the lossless internal record
    # (pool_paired_deltas' exclusion detail) is never mutated.
    assert source == source_snapshot
    # Tuple-shaped reasons keep their container type.
    tupled = runner._canonical_excluded_folds(
        [_r20_entry(reasons=tuple(_R20_MEASURED_REASONS))]
    )
    assert tupled[0]["reasons"] == ("fold_starved", "degenerate_input")


def test_r20_all_twelve_measured_positions_canonicalize() -> None:
    """Matrix row 2: every measured entry position (c11–c14 × 2021–2023)
    canonicalizes with season and metadata preserved."""
    for _contrast in _R20_H5_IDS:
        entries = [_r20_entry(season) for season in _R20_MEASURED_SEASONS]
        out = runner._canonical_excluded_folds(entries)
        assert [e["test_season"] for e in out] == _R20_MEASURED_SEASONS
        for entry in out:
            assert entry["reasons"] == ["fold_starved", "degenerate_input"]
            assert entry["decision_supported"] is False


def test_r20_contrast_status_row_identical_to_precanonical_input() -> None:
    """Matrix row 9: contrast_status output for a result carrying the internal
    word equals the output for the same result pre-canonicalized — ONLY the
    reasons projection differs from the raw internal record; every metric,
    uncertainty field, status, flag, and decision_supported is unchanged."""
    raw = _inference_result()
    raw["pooled"]["excluded_folds"] = [
        _r20_entry(season) for season in _R20_MEASURED_SEASONS
    ]
    pre = _inference_result()
    pre["pooled"]["excluded_folds"] = [
        _r20_entry(season, reasons=["fold_starved", "degenerate_input"])
        for season in _R20_MEASURED_SEASONS
    ]
    registration = _registration()
    row_raw = runner.contrast_status(
        raw, fdr_adjusted={"c11": None}, registration=registration
    )
    row_pre = runner.contrast_status(
        pre, fdr_adjusted={"c11": None}, registration=registration
    )
    assert row_raw == row_pre
    assert [e["reasons"] for e in row_raw["excluded_folds"]] == [
        ["fold_starved", "degenerate_input"]
    ] * 3


def test_r20_missing_fold_starved_refuses_by_name() -> None:
    """Matrix row 3: the internal word WITHOUT its registered implication
    refuses — never silently generalized."""
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner._canonical_excluded_folds(
            [_r20_entry(reasons=["empty_common_pool", "degenerate_input"])]
        )
    assert _reason(exc_info) == "report_schema_invalid"


def test_r20_duplicate_empty_common_pool_refuses_by_name() -> None:
    """Matrix row 4: duplicated internal word refuses."""
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        runner._canonical_excluded_folds(
            [
                _r20_entry(
                    reasons=[
                        "empty_common_pool",
                        "empty_common_pool",
                        "fold_starved",
                    ]
                )
            ]
        )
    assert _reason(exc_info) == "report_schema_invalid"


def test_r20_unreadable_shapes_pass_through_untouched() -> None:
    """R21 re-specification of the repr-era row (R20-G1): the adapter inspects
    the exact token ONLY in structurally readable shapes (Mapping entry +
    list/tuple reasons). EVERY unreadable shape — token-bearing or not —
    passes through untouched; the UNCHANGED registered validator keeps sole
    authority over malformed shapes. No repr/stringification inspection
    exists on any path."""
    for unreadable in (
        ["empty_common_pool"],
        [_r20_entry(reasons="empty_common_pool,fold_starved")],
        [42],
        [_r20_entry(reasons="not_a_list_but_no_target_word")],
    ):
        assert runner._canonical_excluded_folds(unreadable) == unreadable


def test_r20_unreadable_token_shapes_refuse_at_the_gate_e2e(
    tmp_path: Path,
) -> None:
    """The gate — not the adapter — refuses unreadable token-bearing shapes,
    by the required name, end-to-end through the public runner."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    for row in payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = ["empty_common_pool"]
    report, _destination = _run(
        tmp_path, lambda: payload, registration=registration
    )
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"


class _R21HostileRepr:
    """R21 (finding R20-G1): a reasons value whose __repr__ raises. The
    adapter must never stringify it; the run must still end in the NAMED
    report_schema_invalid refusal, never execution_error."""

    def __repr__(self) -> str:  # pragma: no cover - the raise IS the probe
        raise RuntimeError("r21-hostile-repr-sentinel")


def test_r21_hostile_repr_passes_the_adapter_untouched() -> None:
    """The adapter performs zero repr/str inspection: a hostile-__repr__
    reasons value flows through identity-unchanged with no exception."""
    entry = {
        "test_season": 2021,
        "reasons": _R21HostileRepr(),
        "decision_supported": False,
    }
    out = runner._canonical_excluded_folds([entry])
    assert out == [entry]
    assert out[0] is entry


def test_r21_hostile_repr_end_to_end_named_failure(tmp_path: Path) -> None:
    """R21 required regression: a hostile-__repr__ exclusion entry through
    the PUBLIC runner terminates in failure_reason=report_schema_invalid —
    never execution_error — with the atomic artifact written."""
    registration = _registration()
    payload = _complete_ok_payload(registration)
    for row in payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = [
                {
                    "test_season": 2021,
                    "reasons": _R21HostileRepr(),
                    "decision_supported": False,
                }
            ]
    report, destination = _run(
        tmp_path, lambda: payload, registration=registration
    )
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
    artifact = json.loads(destination.read_text())
    assert artifact["failure_reason"] == "report_schema_invalid"


def test_r22_hostile_container_repr_named_failure_e2e(tmp_path: Path) -> None:
    """R22: an excluded_folds CONTAINER whose __repr__ raises must still end
    in the named report_schema_invalid — the hardened container refusal
    carries only stable structural detail, never a payload representation."""
    hostile = _R21HostileRepr()
    assert runner._canonical_excluded_folds(hostile) is hostile
    registration = _registration()
    payload = _complete_ok_payload(registration)
    for row in payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = hostile
    report, destination = _run(
        tmp_path, lambda: payload, registration=registration
    )
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
    artifact = json.loads(destination.read_text())
    assert sorted(artifact) == _R19_ENVELOPE_KEYS


def test_r22_cli_execute_phase_hostile_entry_named_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R22 (both catch phases): a hostile-__repr__ entry refused at the
    composition's defense-in-depth gate call lands in the EXECUTE-phase
    catch — atomic six-key report_schema_invalid artifact, R19 diagnostic
    with phase=execute, never execution_error, never artifact-less."""
    _r19_cli_stubs(monkeypatch)
    registration = _registration()
    monkeypatch.setattr(runner, "load_registration", lambda _root: registration)
    sentinel = "R22-CLI-SENTINEL-PAYLOAD-VALUE--NEVER-PERSISTED"
    hostile_payload = _complete_ok_payload(registration)
    for row in hostile_payload["comparisons"]:
        if row["id"] == "c01":
            # The REFUSED entry itself carries a sentinel value: the fixed
            # structural refusal wording and the metric-free surfaces must
            # leak none of the refused entry's content.
            row["excluded_folds"] = [
                {
                    "test_season": 2021,
                    "reasons": _R21HostileRepr(),
                    "note": sentinel,
                    "decision_supported": False,
                }
            ]

    def compose_with_gate(**_kwargs: Any) -> dict[str, Any]:
        qb.validate_registered_report_blocks(
            hostile_payload, registration=registration
        )
        return hostile_payload

    monkeypatch.setattr(runner, "compose_study", compose_with_gate)
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    code = runner.main(repo_root=tmp_path, output_path=destination)
    out = capsys.readouterr().out
    assert code == 1
    payload = json.loads(out)
    assert payload["failure_reason"] == "report_schema_invalid"
    assert payload["failure_origin"]["phase"] == "execute"
    artifact = json.loads(destination.read_text())
    assert sorted(artifact) == _R19_ENVELOPE_KEYS
    assert artifact["failure_reason"] == "report_schema_invalid"
    # Zero-leakage on BOTH surfaces: captured stdout (summary + failure_origin
    # diagnostic) and the persisted terminal artifact.
    assert sentinel not in out
    assert sentinel not in destination.read_text()


# Armable hostility: __name__ access raises ONLY inside the product-call
# window, so pytest's own failure formatter (which type-names objects) can
# still report a clean RED instead of an INTERNALERROR.
_R22_HOSTILE_NAME_ARMED = {"armed": False}


class _R22HostileMeta(type):
    """R22 correction [w#5hbt8yxh-1]: even class-NAME access is payload-
    derived — this metaclass raises on __name__ (while armed) so any
    type-naming in a refusal detail recreates the pre-refusal escape."""

    def __getattribute__(cls, name: str) -> Any:
        if name == "__name__" and _R22_HOSTILE_NAME_ARMED["armed"]:
            raise RuntimeError("r22-hostile-metaclass-sentinel")
        return super().__getattribute__(name)


class _R22HostileNamed(metaclass=_R22HostileMeta):
    def __repr__(self) -> str:  # pragma: no cover - the raise IS the probe
        raise RuntimeError("r22-hostile-instance-repr-sentinel")


def test_r22_hostile_metaclass_name_container_named_failure_e2e(
    tmp_path: Path,
) -> None:
    """R22 correction: the container refusal detail performs ZERO derivation
    from the refused value — hostile __repr__ AND hostile metaclass __name__
    together still end in the named report_schema_invalid."""
    hostile = _R22HostileNamed()
    registration = _registration()
    payload = _complete_ok_payload(registration)
    for row in payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = hostile
    _R22_HOSTILE_NAME_ARMED["armed"] = True
    try:
        adapter_out = runner._canonical_excluded_folds(hostile)
        report, destination = _run(
            tmp_path, lambda: payload, registration=registration
        )
    finally:
        _R22_HOSTILE_NAME_ARMED["armed"] = False
    assert adapter_out is hostile
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
    assert sorted(json.loads(destination.read_text())) == _R19_ENVELOPE_KEYS


def test_r22_sentinel_reason_never_reaches_the_terminal_artifact(
    tmp_path: Path,
) -> None:
    """R22 zero-leakage row, ARTIFACT surface: a sentinel string planted as
    an unregistered reason word (refused at the hardened entry clause)
    appears nowhere in the terminal artifact. The stdout/diagnostic surface
    is proven by the CLI execute-phase test's sentinel-negative
    assertions."""
    sentinel = "R22-SENTINEL-REASON-WORD--NEVER-PERSISTED"
    registration = _registration()
    payload = _complete_ok_payload(registration)
    for row in payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = [_r20_entry(reasons=[sentinel, "fold_starved"])]
    report, destination = _run(
        tmp_path, lambda: payload, registration=registration
    )
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
    assert sentinel not in destination.read_text()


def test_r22_hostile_sequence_subclass_constructor_never_invoked() -> None:
    """R22 correction [w#6wxdinst-1]: the canonical projection never invokes
    a payload-supplied list/tuple-subclass constructor — built-in
    construction only, preserving reason order and the ordinary
    tuple-vs-list form."""
    constructor_calls = {"count": 0}

    class _HostileList(list):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            constructor_calls["count"] += 1
            raise RuntimeError("r22-hostile-list-subclass-constructor")

    hostile_list = list.__new__(_HostileList)
    list.extend(hostile_list, ["empty_common_pool", "fold_starved"])
    out = runner._canonical_excluded_folds(
        [
            {
                "test_season": 2021,
                "reasons": hostile_list,
                "decision_supported": False,
            }
        ]
    )
    assert constructor_calls["count"] == 0
    assert type(out[0]["reasons"]) is list
    assert out[0]["reasons"] == ["fold_starved"]

    class _HostileTuple(tuple):
        def __new__(cls, *args: Any, **kwargs: Any) -> "_HostileTuple":
            raise RuntimeError("r22-hostile-tuple-subclass-new")

    hostile_tuple = tuple.__new__(
        _HostileTuple, ("empty_common_pool", "fold_starved", "degenerate_input")
    )
    out = runner._canonical_excluded_folds(
        [
            {
                "test_season": 2021,
                "reasons": hostile_tuple,
                "decision_supported": False,
            }
        ]
    )
    assert type(out[0]["reasons"]) is tuple
    assert out[0]["reasons"] == ("fold_starved", "degenerate_input")


def test_r21_unrelated_metadata_token_never_triggers_canonicalization() -> None:
    """R21: the exact token sitting in unrelated entry metadata (a non-reasons
    value) triggers neither canonicalization nor refusal — the adapter reads
    ONLY the reasons elements."""
    entry = _r20_entry(
        reasons=["fold_starved", "degenerate_input"],
        note="empty_common_pool",
    )
    out = runner._canonical_excluded_folds([entry])
    assert out == [entry]
    assert out[0]["note"] == "empty_common_pool"
    assert out[0]["reasons"] == ["fold_starved", "degenerate_input"]


def test_r20_unknown_word_preserved_and_gate_rejects_e2e(tmp_path: Path) -> None:
    """Matrix row 5: an unrelated unknown reason survives the adapter
    unchanged, and the UNCHANGED publication gate rejects it end-to-end."""
    kept = runner._canonical_excluded_folds(
        [_r20_entry(reasons=["r20_bogus_reason", "fold_starved"])]
    )
    assert kept[0]["reasons"] == ["r20_bogus_reason", "fold_starved"]
    registration = _registration()
    payload = _complete_ok_payload(registration)
    for row in payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = kept
    report, _destination = _run(
        tmp_path, lambda: payload, registration=registration
    )
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"


def test_r20_none_and_empty_exclusions_unchanged() -> None:
    """Matrix row 7: None and empty collections are preserved exactly."""
    assert runner._canonical_excluded_folds(None) is None
    assert runner._canonical_excluded_folds([]) == []


def test_r20_e2e_canonical_publishes_ok_and_raw_still_refuses(
    tmp_path: Path,
) -> None:
    """Synthetic terminal publication probe: the canonicalized measured shape
    publishes ok through the public runner against the UNCHANGED gate, while
    the raw internal shape still refuses — the wall exists exactly until the
    adapter projects it."""
    registration = _registration()
    canonical = runner._canonical_excluded_folds([_r20_entry(2021)])
    ok_payload = _complete_ok_payload(registration)
    for row in ok_payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = canonical
    report, _destination = _run(
        tmp_path, lambda: ok_payload, registration=registration
    )
    assert report["run_status"] == "ok"

    raw_payload = _complete_ok_payload(registration)
    for row in raw_payload["comparisons"]:
        if row["id"] == "c01":
            row["excluded_folds"] = [_r20_entry(2021)]
    report, _destination = _run(
        tmp_path / "raw", lambda: raw_payload, registration=registration
    )
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == "report_schema_invalid"
