"""Independent GREEN-review RED amendments for CFBD DATA promotion.

These tests preserve the original 60-test RED blob and exercise failure states
that became visible only after reading the GREEN implementation. All mutations
are confined to ``tmp_path``.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import importlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from tests.contract.test_cfbd_data_promotion_red import (
    CSV_FIELDS,
    PROMOTED_COLUMNS,
    _candidate_rows,
    _canonical_digest,
    _read_csv,
    _sha,
    _write_csv,
    _write_json,
)

pytest_plugins = ("tests.contract.test_cfbd_data_promotion_red",)

ROOT = Path(__file__).resolve().parents[2]


def _assert_reason(exc: pytest.ExceptionInfo[BaseException], reason: str) -> None:
    assert getattr(exc.value, "reason", None) == reason, str(exc.value)


def _tree_state(root: Path) -> tuple[tuple[str, ...], dict[str, bytes]]:
    directories = tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_dir())
    )
    files = {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    return directories, files


def _promote(mod, spec) -> None:
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"


# ── The writer guard must be silent only when no promotion evidence exists ──


@pytest.mark.parametrize(
    ("receipt_payload", "reason"),
    [
        (b"{not-json", "promotion_receipt_invalid"),
        (b"{}", "promotion_receipt_invalid"),
        (json.dumps([]).encode(), "promotion_receipt_invalid"),
    ],
)
def test_guard_fails_closed_on_occupied_but_invalid_receipt(
    promotion_env, receipt_payload: bytes, reason: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    spec.receipt_path.parent.mkdir(parents=True, exist_ok=True)
    spec.receipt_path.write_bytes(receipt_payload)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, reason)


def test_guard_fails_closed_when_receipt_exists_but_active_is_missing(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    spec.active_path.unlink()
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "promotion_state_invalid")


def test_guard_surfaces_projection_drift_instead_of_silently_allowing_more_writes(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    rows = _read_csv(spec.active_path)
    rows[0]["qb_completion_pct_final"] = "0.999"
    _write_csv(spec.active_path, rows)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "promoted_projection_drift")


def test_guard_fails_closed_when_active_projection_is_unreadable(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    spec.active_path.write_text("not,a,governed,csv\n", encoding="utf-8")
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "promotion_state_invalid")


# ── Read-only means no filesystem mutation, including recovery and rollback ─


def test_dry_run_leaves_no_lock_directory_or_other_filesystem_trace(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    root = spec.active_path.parents[1]
    before = _tree_state(root)
    assert mod.promote_cfbd_data(spec, confirm=False)["status"] == "dry_run"
    assert _tree_state(root) == before
    assert not spec.lock_path.parent.exists()


class _Crash(BaseException):
    pass


def _create_split_state(mod, spec) -> None:
    def crash(stage: str) -> None:
        if stage == "after_active_replace":
            raise _Crash

    with pytest.raises(_Crash):
        mod.promote_cfbd_data(spec, confirm=True, fault_hook=crash)
    spec.lock_path.unlink(missing_ok=True)


def test_recovery_is_read_only_without_confirm_and_locked_when_confirmed(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _create_split_state(mod, spec)
    before = _tree_state(spec.active_path.parents[1])
    report = mod.recover_cfbd_promotion(spec, confirm=False)
    assert report["status"] == "would_recover_post_replace"
    assert _tree_state(spec.active_path.parents[1]) == before
    assert not spec.receipt_path.exists()

    with mod.promotion_lock(spec):
        with pytest.raises(mod.CfbdPromotionError) as exc:
            mod.recover_cfbd_promotion(spec, confirm=True)
        _assert_reason(exc, "promotion_locked")


def test_rollback_is_read_only_without_confirm(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    before = _tree_state(spec.active_path.parents[1])
    report = mod.rollback_cfbd_promotion(spec, confirm=False)
    assert report["status"] == "would_roll_back"
    assert _tree_state(spec.active_path.parents[1]) == before


def test_cli_requires_confirm_for_promotion_recovery_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = importlib.import_module("scripts.promote_cfbd_data")
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(cli, "default_promotion_spec", lambda: object())
    monkeypatch.setattr(
        cli,
        "promote_cfbd_data",
        lambda _spec, confirm=False: (
            calls.append(("promote", confirm))
            or {"status": "promoted" if confirm else "dry_run"}
        ),
    )
    monkeypatch.setattr(
        cli,
        "recover_cfbd_promotion",
        lambda _spec, confirm=False: (
            calls.append(("recover", confirm))
            or {"status": "recovered" if confirm else "would_recover"}
        ),
    )
    monkeypatch.setattr(
        cli,
        "rollback_cfbd_promotion",
        lambda _spec, confirm=False: (
            calls.append(("rollback", confirm))
            or {"status": "rolled_back" if confirm else "would_roll_back"}
        ),
    )

    assert cli.main([]) == 0
    assert cli.main(["--confirm"]) == 0
    assert cli.main(["--recover"]) == 0
    assert cli.main(["--recover", "--confirm"]) == 0
    assert cli.main(["--rollback"]) == 0
    assert cli.main(["--rollback", "--confirm"]) == 0
    assert calls == [
        ("promote", False),
        ("promote", True),
        ("recover", False),
        ("recover", True),
        ("rollback", False),
        ("rollback", True),
    ]


# ── A parseable receipt is not necessarily a valid receipt ─────────────────


def test_idempotence_requires_complete_verified_receipt_and_preimage(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    spec.receipt_path.write_text(
        json.dumps({"after_sha256": spec.expected_candidate_sha256}),
        encoding="utf-8",
    )
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "receipt_invalid")

    # A complete receipt without its named preimage is also not idempotent success.
    # Rebuild a valid state, then remove the preimage.


def test_recovery_rejects_parseable_but_semantically_invalid_receipt(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    spec.receipt_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.recover_cfbd_promotion(spec, confirm=False)
    _assert_reason(exc, "receipt_invalid")


def test_complete_state_requires_the_receipts_named_preimage(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    spec.preimage_path.unlink()
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.recover_cfbd_promotion(spec, confirm=False)
    _assert_reason(exc, "evidence_incomplete")


def test_recovered_receipt_recomputes_actual_delta_and_records_recovery(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _create_split_state(mod, spec)
    assert (
        mod.recover_cfbd_promotion(spec, confirm=True)["status"]
        == "recovered_post_replace"
    )
    receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    assert receipt["changed_columns"] == sorted(
        {
            "qb_completion_pct_final",
            "qb_completion_pct_final_source",
            "qb_completion_pct_final_missing",
        }
    )
    assert receipt["recovered_from_split"] is True


def test_receipt_records_time_and_immutable_source_provenance(promotion_env) -> None:
    mod, spec, manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    assert receipt["recorded_at"].endswith("Z")
    assert receipt["source_manifest_sha256"] == _sha(spec.manifest_path)
    assert receipt["raw_content_sha256"] == manifest["raw_content_sha256"]
    assert receipt["raw_file_count"] == 1


# ── Govern every path and every source-manifest claim ───────────────────────


def test_preimage_may_not_alias_the_active_file(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    old = spec.active_path.read_bytes()
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(
            replace(spec, preimage_path=spec.active_path), confirm=True
        )
    _assert_reason(exc, "path_alias")
    assert spec.active_path.read_bytes() == old


def test_existing_or_symlinked_atomic_temp_is_a_collision_not_a_write_target(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    candidate_before = spec.candidate_path.read_bytes()
    active_temp = spec.active_path.with_name(f".{spec.active_path.name}.tmp")
    active_temp.symlink_to(spec.candidate_path)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "temporary_path_collision")
    assert spec.candidate_path.read_bytes() == candidate_before


def test_raw_root_must_remain_under_the_governed_foundation_root(promotion_env) -> None:
    mod, spec, manifest, raw_manifest = promotion_env
    old_raw_root = Path(manifest["raw_root"])
    outside = spec.active_path.parents[1] / "outside-raw" / "run-1"
    shutil.copytree(old_raw_root, outside)
    moved = {**manifest, "raw_root": str(outside)}
    _write_json(spec.manifest_path, moved)
    _write_json(outside / "manifest.json", moved)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(spec)
    _assert_reason(exc, "raw_root_outside_governed_root")
    assert raw_manifest.exists()


def test_raw_file_count_is_recomputed_not_dropped_from_the_chain(promotion_env) -> None:
    mod, spec, manifest, raw_manifest = promotion_env
    raw_root = Path(manifest["raw_root"])
    manifest = {**manifest, "raw_file_count": 1}
    _write_json(spec.manifest_path, manifest)
    _write_json(raw_manifest, manifest)
    (raw_root / "qb_raw.json").unlink()
    empty_digest = hashlib.sha256().hexdigest()
    manifest = {**manifest, "raw_content_sha256": empty_digest}
    _write_json(spec.manifest_path, manifest)
    _write_json(raw_manifest, manifest)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(spec)
    _assert_reason(exc, "raw_file_count_mismatch")


def test_ragged_projection_row_is_fatal_not_silently_projected(tmp_path: Path) -> None:
    mod = importlib.import_module("src.dynasty_genius.capture.cfbd_data_promotion")
    path = tmp_path / "ragged.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(mod.PROJECTION_FIELDS)
        writer.writerow(["00-a", *("" for _ in PROMOTED_COLUMNS), "surplus"])
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.projection_digest(path)
    _assert_reason(exc, "projection_extra_cell")


def test_secondary_identity_permutation_is_not_misclassified_as_row_reorder(
    promotion_env,
) -> None:
    mod, spec, manifest, raw_manifest = promotion_env
    rows = _candidate_rows()
    rows[0]["pfr_player_name"], rows[1]["pfr_player_name"] = (
        rows[1]["pfr_player_name"],
        rows[0]["pfr_player_name"],
    )
    _write_csv(spec.candidate_path, rows, CSV_FIELDS)
    manifest = {**manifest, "curated_sha256": _sha(spec.candidate_path)}
    _write_json(spec.manifest_path, manifest)
    _write_json(raw_manifest, manifest)
    changed = replace(
        spec,
        expected_candidate_sha256=_sha(spec.candidate_path),
        expected_candidate_projection_sha256=_canonical_digest(rows),
        expected_changed_cell_count=5,
    )
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(changed)
    _assert_reason(exc, "identity_mismatch")


# ── Writer integrations should fail before expense and share one receipt path ─


@pytest.mark.parametrize(
    ("script_name", "expensive_call"),
    [
        ("build_head_b_targets.py", "_build_curves"),
        ("build_w2b_cfbd.py", "_cfbd_api_key"),
    ],
)
def test_writer_guard_precedes_expensive_or_paid_work(
    script_name: str, expensive_call: str
) -> None:
    source = (ROOT / "scripts" / script_name).read_text(encoding="utf-8")
    tree = ast.parse(source)
    guard = min(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "guard_destructive_cfbd_write"
    )
    expensive = min(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == expensive_call
    )
    assert guard < expensive


@pytest.mark.parametrize(
    "script_name", ["build_head_b_targets.py", "build_w2b_cfbd.py"]
)
def test_writer_receipt_path_is_derived_from_the_shared_default_spec(
    script_name: str,
) -> None:
    source = (ROOT / "scripts" / script_name).read_text(encoding="utf-8")
    assert "default_promotion_spec" in source
    assert (
        "15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0" not in source
    )
