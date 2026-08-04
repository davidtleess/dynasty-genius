"""RED contract for the CFBD DATA promotion state machine.

Authored by the independent Codex lane after framing CLEAR on 2026-08-03.
These tests are deliberately offline and write only below ``tmp_path``. They
specify promotion mechanics; they do not run a bakeoff, train/write a model,
refresh CFBD, or make a predictive claim.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import importlib
import json
import os
import stat
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERSION = "cfbd_qb_projection.v1"
PROJECTION_FIELDS = (
    "gsis_id",
    "qb_completion_pct_final",
    "qb_completion_pct_final_source",
    "qb_completion_pct_final_missing",
    "qb_yards_per_attempt_final",
    "qb_yards_per_attempt_final_source",
    "qb_yards_per_attempt_final_missing",
    "qb_td_int_ratio_final",
    "qb_td_int_ratio_final_source",
    "qb_td_int_ratio_final_missing",
    "qb_sack_rate_final",
    "qb_sack_rate_final_source",
    "qb_sack_rate_final_missing",
)
PROMOTED_COLUMNS = frozenset(PROJECTION_FIELDS[1:])
EXTRA_FIELDS = ("pfr_player_name", "position", "season")
CSV_FIELDS = (*PROJECTION_FIELDS, *EXTRA_FIELDS)

GOLDEN_ROWS = [
    dict(
        zip(
            PROJECTION_FIELDS,
            (
                "b",
                "0.600",
                "cfbd",
                "0",
                "7.5",
                "cfbd",
                "0",
                "2.0",
                "cfbd",
                "0",
                "",
                "",
                "1",
            ),
            strict=True,
        )
    ),
    dict(
        zip(
            PROJECTION_FIELDS,
            (
                "a",
                "0.650",
                "cfbd",
                "0",
                "8.0",
                "cfbd",
                "0",
                "3.0",
                "cfbd",
                "0",
                "0.04",
                "cfbd",
                "0",
            ),
            strict=True,
        )
    ),
]
GOLDEN_SHA256 = "fed6b75a7b9d038ea4e59807a594aae16ee1e3ab924c44f6b41600af484f2945"


def _mod():
    return importlib.import_module("src.dynasty_genius.capture.cfbd_data_promotion")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_digest(rows: list[dict[str, str]]) -> str:
    ordered = sorted(
        ([row[field] for field in PROJECTION_FIELDS] for row in rows),
        key=lambda values: values[0].encode("utf-8"),
    )
    payload = [VERSION, list(PROJECTION_FIELDS), ordered]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _base_rows() -> list[dict[str, str]]:
    defaults = {
        "qb_completion_pct_final": "",
        "qb_completion_pct_final_source": "",
        "qb_completion_pct_final_missing": "1",
        "qb_yards_per_attempt_final": "",
        "qb_yards_per_attempt_final_source": "",
        "qb_yards_per_attempt_final_missing": "1",
        "qb_td_int_ratio_final": "",
        "qb_td_int_ratio_final_source": "",
        "qb_td_int_ratio_final_missing": "1",
        "qb_sack_rate_final": "",
        "qb_sack_rate_final_source": "",
        "qb_sack_rate_final_missing": "1",
    }
    return [
        {
            "gsis_id": "00-a",
            **defaults,
            "pfr_player_name": "Alpha QB",
            "position": "QB",
            "season": "2020",
        },
        {
            "gsis_id": "00-b",
            **defaults,
            "pfr_player_name": "Beta QB",
            "position": "QB",
            "season": "2021",
        },
        {
            "gsis_id": "00-c",
            **defaults,
            "pfr_player_name": "Gamma WR",
            "position": "WR",
            "season": "2021",
        },
    ]


def _candidate_rows() -> list[dict[str, str]]:
    rows = _base_rows()
    rows[0] = {
        **rows[0],
        "qb_completion_pct_final": "0.650",
        "qb_completion_pct_final_source": "cfbd",
        "qb_completion_pct_final_missing": "0",
    }
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]], fields=CSV_FIELDS) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _raw_content_sha(raw_root: Path) -> str:
    combined = hashlib.sha256()
    for path in sorted(raw_root.glob("*.json")):
        combined.update(path.name.encode("utf-8"))
        combined.update(_sha(path).encode("ascii"))
    return combined.hexdigest()


def _assert_reason(exc: pytest.ExceptionInfo[BaseException], reason: str) -> None:
    assert getattr(exc.value, "reason", None) == reason, str(exc.value)


@dataclass(frozen=True)
class _PromotionEnv:
    spec_kwargs: dict
    manifest_payload: dict
    raw_manifest: Path

    def __iter__(self):
        """Defer the missing production import to the test body, not fixture setup."""
        mod = _mod()
        yield mod
        yield mod.PromotionSpec(**self.spec_kwargs)
        yield self.manifest_payload
        yield self.raw_manifest


@pytest.fixture
def promotion_env(tmp_path: Path):
    active = _write_csv(
        tmp_path / "training" / "prospects_with_outcomes_v3.csv", _base_rows()
    )
    candidate = _write_csv(
        tmp_path / "sources" / "cfbd_foundation" / "curated" / active.name,
        _candidate_rows(),
    )
    raw_root = tmp_path / "sources" / "cfbd_foundation" / "raw" / "run-1"
    raw_root.mkdir(parents=True)
    raw_payload = [{"provider": "cfbd", "row": 1}]
    _write_json(raw_root / "qb_raw.json", raw_payload)
    raw_content_sha = _raw_content_sha(raw_root)
    manifest_payload = {
        "schema_version": "cfbd_foundation.v1",
        "source": "cfbd",
        "run_id": "run-1",
        "input_sha256": _sha(active),
        "curated_sha256": _sha(candidate),
        "raw_content_sha256": raw_content_sha,
        "raw_root": str(raw_root),
        "raw_file_count": 1,
        "row_count": 3,
    }
    manifest = _write_json(
        tmp_path / "sources" / "cfbd_foundation" / "manifest_latest.json",
        manifest_payload,
    )
    raw_manifest = _write_json(raw_root / "manifest.json", manifest_payload)
    history = tmp_path / "training" / "cfbd_promotion_history"
    return _PromotionEnv(
        spec_kwargs={
            "active_path": active,
            "candidate_path": candidate,
            "manifest_path": manifest,
            "preimage_path": history / "preimages" / f"{_sha(active)}.csv",
            "receipt_path": history / "receipts" / f"{_sha(candidate)}.json",
            "rollback_receipt_path": history
            / "receipts"
            / f"rollback-{_sha(candidate)}.json",
            "lock_path": history / "promotion.lock",
            "expected_active_sha256": _sha(active),
            "expected_candidate_sha256": _sha(candidate),
            "expected_active_projection_sha256": _canonical_digest(_base_rows()),
            "expected_candidate_projection_sha256": _canonical_digest(
                _candidate_rows()
            ),
            "expected_row_count": 3,
            "expected_column_count": len(CSV_FIELDS),
            "expected_changed_row_count": 1,
            "expected_changed_cell_count": 3,
            "allowed_changed_columns": PROMOTED_COLUMNS,
            "identity_columns": ("gsis_id", "pfr_player_name"),
        },
        manifest_payload=manifest_payload,
        raw_manifest=raw_manifest,
    )


# ── Canonical projection digest ─────────────────────────────────────────────


def test_projection_digest_constants_are_the_cleared_contract() -> None:
    mod = _mod()
    assert mod.PROJECTION_DIGEST_VERSION == VERSION
    assert tuple(mod.PROJECTION_FIELDS) == PROJECTION_FIELDS


def test_projection_digest_matches_the_cross_lane_golden_vector(tmp_path: Path) -> None:
    mod = _mod()
    path = _write_csv(tmp_path / "golden.csv", GOLDEN_ROWS, PROJECTION_FIELDS)
    assert mod.projection_digest(path) == GOLDEN_SHA256


def test_projection_digest_is_keyed_not_file_ordered(tmp_path: Path) -> None:
    mod = _mod()
    first = _write_csv(tmp_path / "first.csv", GOLDEN_ROWS, PROJECTION_FIELDS)
    second = _write_csv(
        tmp_path / "second.csv", list(reversed(GOLDEN_ROWS)), PROJECTION_FIELDS
    )
    assert (
        mod.projection_digest(first) == mod.projection_digest(second) == GOLDEN_SHA256
    )


def test_projection_digest_preserves_exact_strings_and_empty_distinct_from_missing(
    tmp_path: Path,
) -> None:
    mod = _mod()
    exact = _write_csv(tmp_path / "exact.csv", GOLDEN_ROWS, PROJECTION_FIELDS)
    coerced_rows = [dict(row) for row in GOLDEN_ROWS]
    coerced_rows[0]["qb_completion_pct_final"] = "0.6"
    coerced = _write_csv(tmp_path / "coerced.csv", coerced_rows, PROJECTION_FIELDS)
    assert mod.projection_digest(exact) != mod.projection_digest(coerced)

    missing_fields = tuple(
        field for field in PROJECTION_FIELDS if field != "qb_sack_rate_final_source"
    )
    missing = _write_csv(tmp_path / "missing.csv", GOLDEN_ROWS, missing_fields)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.projection_digest(missing)
    _assert_reason(exc, "projection_missing_cell")


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda rows: rows[0].__setitem__("gsis_id", ""), "blank_identity"),
        (
            lambda rows: rows[1].__setitem__("gsis_id", rows[0]["gsis_id"]),
            "duplicate_identity",
        ),
    ],
)
def test_projection_digest_refuses_ambiguous_identity(
    tmp_path: Path, mutation, reason: str
) -> None:
    mod = _mod()
    rows = [dict(row) for row in GOLDEN_ROWS]
    mutation(rows)
    path = _write_csv(tmp_path / "bad.csv", rows, PROJECTION_FIELDS)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.projection_digest(path)
    _assert_reason(exc, reason)


# ── Pinned one-time specification and read-only validation ──────────────────


def test_default_spec_pins_the_authorized_real_promotion_without_reading_it(
    tmp_path: Path,
) -> None:
    mod = _mod()
    spec = mod.default_promotion_spec(root=tmp_path)
    assert (
        spec.expected_active_sha256
        == "b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38"
    )
    assert (
        spec.expected_candidate_sha256
        == "15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0"
    )
    assert (
        spec.expected_active_projection_sha256
        == "683384b89c860f67bf963d2e03022c9fc119572b52b3afc95c26b919d347f3b3"
    )
    assert (
        spec.expected_candidate_projection_sha256
        == "f2239463bf8da3a48d114b613cb75782d3bccc797cef059c071c1d08795c1dd0"
    )
    assert (spec.expected_row_count, spec.expected_column_count) == (874, 173)
    assert (spec.expected_changed_row_count, spec.expected_changed_cell_count) == (
        117,
        1123,
    )
    assert frozenset(spec.allowed_changed_columns) == PROMOTED_COLUMNS


def test_valid_promotion_recomputes_every_semantic_gate(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    report = mod.validate_promotion(spec)
    assert report["status"] == "valid"
    assert report["row_count"] == 3
    assert report["column_count"] == len(CSV_FIELDS)
    assert report["changed_row_count"] == 1
    assert report["changed_cell_count"] == 3
    assert report["changed_columns"] == sorted(
        {
            "qb_completion_pct_final",
            "qb_completion_pct_final_source",
            "qb_completion_pct_final_missing",
        }
    )
    assert report["changed_positions"] == {"QB": 1}
    assert report["decision_supported"] is False


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("expected_active_sha256", "active_sha_mismatch"),
        ("expected_candidate_sha256", "candidate_sha_mismatch"),
        ("expected_active_projection_sha256", "active_projection_mismatch"),
        ("expected_candidate_projection_sha256", "candidate_projection_mismatch"),
    ],
)
def test_hash_and_projection_pins_are_independently_fatal(
    promotion_env, field: str, reason: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(replace(spec, **{field: "0" * 64}))
    _assert_reason(exc, reason)


@pytest.mark.parametrize(
    ("manifest_field", "reason"),
    [
        ("schema_version", "manifest_schema_mismatch"),
        ("run_id", "raw_manifest_mismatch"),
        ("input_sha256", "manifest_input_mismatch"),
        ("curated_sha256", "manifest_candidate_mismatch"),
        ("raw_content_sha256", "raw_manifest_mismatch"),
    ],
)
def test_manifest_chain_mismatch_is_fatal(
    promotion_env, manifest_field: str, reason: str
) -> None:
    mod, spec, manifest_payload, _raw_manifest = promotion_env
    broken = dict(manifest_payload)
    broken[manifest_field] = "wrong"
    _write_json(spec.manifest_path, broken)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(spec)
    _assert_reason(exc, reason)


def test_raw_snapshot_bytes_are_recomputed_not_trusted_from_two_matching_manifests(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    raw_root = Path(json.loads(spec.manifest_path.read_text())["raw_root"])
    _write_json(raw_root / "qb_raw.json", [{"provider": "cfbd", "tampered": True}])
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(spec)
    _assert_reason(exc, "raw_content_mismatch")


def _mutate_candidate(spec, mutation) -> None:
    rows = _read_csv(spec.candidate_path)
    fields = list(rows[0])
    mutation(rows, fields)
    _write_csv(spec.candidate_path, rows, fields)


@pytest.mark.parametrize(
    ("mutation", "spec_changes", "reason"),
    [
        (lambda rows, fields: rows.pop(), {}, "row_count_mismatch"),
        (lambda rows, fields: fields.reverse(), {}, "header_mismatch"),
        (lambda rows, fields: rows.reverse(), {}, "row_order_mismatch"),
        (
            lambda rows, fields: rows[0].__setitem__(
                "pfr_player_name", "Moved Identity"
            ),
            {},
            "identity_mismatch",
        ),
        (
            lambda rows, fields: rows[2].__setitem__(
                "qb_completion_pct_final", "0.700"
            ),
            {"expected_changed_row_count": 2, "expected_changed_cell_count": 4},
            "non_qb_change",
        ),
        (
            lambda rows, fields: rows[0].__setitem__("season", "2099"),
            {"expected_changed_cell_count": 4},
            "changed_column_not_allowed",
        ),
        (
            lambda rows, fields: rows[1].__setitem__(
                "qb_completion_pct_final", "0.700"
            ),
            {"expected_changed_cell_count": 4},
            "changed_row_count_mismatch",
        ),
        (
            lambda rows, fields: rows[0].__setitem__("qb_sack_rate_final", "0.04"),
            {},
            "changed_cell_count_mismatch",
        ),
    ],
)
def test_each_semantic_delta_violation_fails_closed(
    promotion_env, mutation, spec_changes: dict, reason: str
) -> None:
    mod, spec, manifest_payload, raw_manifest = promotion_env
    _mutate_candidate(spec, mutation)
    # Re-pin byte/projection/manifest identities so this test reaches the named semantic gate.
    candidate_rows = _read_csv(spec.candidate_path)
    manifest_payload = dict(manifest_payload)
    manifest_payload["curated_sha256"] = _sha(spec.candidate_path)
    _write_json(spec.manifest_path, manifest_payload)
    _write_json(raw_manifest, manifest_payload)
    changes = {
        "expected_candidate_sha256": _sha(spec.candidate_path),
        "expected_candidate_projection_sha256": _canonical_digest(candidate_rows),
        **spec_changes,
    }
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(replace(spec, **changes))
    _assert_reason(exc, reason)


def test_duplicate_or_blank_secondary_identity_is_fatal(promotion_env) -> None:
    mod, spec, manifest_payload, raw_manifest = promotion_env
    for bad_name, reason in (("", "blank_identity"), ("Beta QB", "duplicate_identity")):
        rows = _candidate_rows()
        rows[0]["pfr_player_name"] = bad_name
        _write_csv(spec.candidate_path, rows)
        manifest_payload = {
            **manifest_payload,
            "curated_sha256": _sha(spec.candidate_path),
        }
        _write_json(spec.manifest_path, manifest_payload)
        _write_json(raw_manifest, manifest_payload)
        changed = replace(
            spec,
            expected_candidate_sha256=_sha(spec.candidate_path),
            expected_candidate_projection_sha256=_canonical_digest(rows),
        )
        with pytest.raises(mod.CfbdPromotionError) as exc:
            mod.validate_promotion(changed)
        _assert_reason(exc, reason)


# ── Promotion transaction, side effects, TOCTOU and durability ──────────────


def test_dry_run_is_read_only_and_reports_no_validation_verdict(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    before = {
        path: path.read_bytes() for path in (spec.active_path, spec.candidate_path)
    }
    report = mod.promote_cfbd_data(spec, confirm=False)
    assert report["status"] == "dry_run"
    assert report["would_promote"] is True
    assert report["decision_supported"] is False
    assert report["model_changed"] is False
    assert report["bakeoff_run"] is False
    assert not spec.preimage_path.exists()
    assert not spec.receipt_path.exists()
    assert {path: path.read_bytes() for path in before} == before


def test_confirm_writes_verified_preimage_then_atomically_replaces_and_receipts(
    promotion_env,
) -> None:
    mod, spec, manifest, _raw_manifest = promotion_env
    old = spec.active_path.read_bytes()
    candidate = spec.candidate_path.read_bytes()
    report = mod.promote_cfbd_data(spec, confirm=True)
    assert report["status"] == "promoted"
    assert spec.preimage_path.read_bytes() == old
    assert _sha(spec.preimage_path) == spec.expected_active_sha256
    assert spec.active_path.read_bytes() == candidate
    assert _sha(spec.active_path) == spec.expected_candidate_sha256
    assert (
        mod.projection_digest(spec.active_path)
        == spec.expected_candidate_projection_sha256
    )
    receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "promoted"
    assert receipt["decision_supported"] is False
    assert receipt["model_changed"] is False
    assert receipt["bakeoff_run"] is False
    assert receipt["predictive_validation_run"] is False
    assert receipt["promotion_decision"] == "not_applicable_data_movement"
    assert receipt["before_sha256"] == spec.expected_active_sha256
    assert receipt["after_sha256"] == spec.expected_candidate_sha256
    assert receipt["before_projection_sha256"] == spec.expected_active_projection_sha256
    assert (
        receipt["after_projection_sha256"] == spec.expected_candidate_projection_sha256
    )
    assert receipt["manifest_run_id"] == manifest["run_id"]
    assert receipt["changed_row_count"] == 1
    assert receipt["changed_cell_count"] == 3
    assert not ({"validated", "improved", "promotion_warranted"} & set(receipt))


def test_confirm_side_effects_are_exactly_active_preimage_and_receipt(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    root = spec.active_path.parents[1]
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    mod.promote_cfbd_data(spec, confirm=True)
    after = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    changed = {path for path in before | after if before.get(path) != after.get(path)}
    assert changed == {spec.active_path, spec.preimage_path, spec.receipt_path}
    assert not spec.lock_path.exists()
    assert not list(root.rglob("*.tmp"))


def test_every_atomic_replace_uses_a_sibling_temp_on_the_target_filesystem(
    promotion_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    real_replace = os.replace
    calls: list[tuple[Path, Path]] = []

    def sibling_only(source, target) -> None:
        source_path, target_path = Path(source), Path(target)
        calls.append((source_path, target_path))
        assert source_path.parent == target_path.parent
        real_replace(source_path, target_path)

    monkeypatch.setattr(mod.os, "replace", sibling_only)
    mod.promote_cfbd_data(spec, confirm=True)
    assert {target for _source, target in calls} >= {
        spec.preimage_path,
        spec.active_path,
        spec.receipt_path,
    }


def test_idempotent_rerun_does_not_overwrite_original_evidence(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    first = mod.promote_cfbd_data(spec, confirm=True)
    evidence = (spec.preimage_path.read_bytes(), spec.receipt_path.read_bytes())
    second = mod.promote_cfbd_data(spec, confirm=True)
    assert first["status"] == "promoted"
    assert second["status"] == "already_promoted"
    assert (spec.preimage_path.read_bytes(), spec.receipt_path.read_bytes()) == evidence


def test_candidate_toctou_refuses_without_mutating_active(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    old = spec.active_path.read_bytes()

    def mutate(stage: str) -> None:
        if stage == "before_active_replace":
            spec.candidate_path.write_bytes(b"changed after validation\n")

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True, fault_hook=mutate)
    _assert_reason(exc, "candidate_changed_during_promotion")
    assert spec.active_path.read_bytes() == old
    assert not spec.receipt_path.exists()


def test_active_toctou_refuses_and_preserves_intervening_writer(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    intervening = b"intervening writer bytes\n"

    def mutate(stage: str) -> None:
        if stage == "before_active_replace":
            spec.active_path.write_bytes(intervening)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True, fault_hook=mutate)
    _assert_reason(exc, "active_changed_during_promotion")
    assert spec.active_path.read_bytes() == intervening
    assert not spec.receipt_path.exists()


class SimulatedCrash(BaseException):
    pass


def test_crash_after_replace_is_a_named_recoverable_split_state(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env

    def crash(stage: str) -> None:
        if stage == "after_active_replace":
            raise SimulatedCrash

    with pytest.raises(SimulatedCrash):
        mod.promote_cfbd_data(spec, confirm=True, fault_hook=crash)
    assert _sha(spec.active_path) == spec.expected_candidate_sha256
    assert _sha(spec.preimage_path) == spec.expected_active_sha256
    assert not spec.receipt_path.exists()
    spec.lock_path.unlink(missing_ok=True)  # the crashed PID is gone in the real state
    preview = mod.recover_cfbd_promotion(spec)
    assert preview["status"] == "would_recover_post_replace"
    assert not spec.receipt_path.exists()
    report = mod.recover_cfbd_promotion(spec, confirm=True)
    assert report["status"] == "recovered_post_replace"
    assert spec.receipt_path.exists()


def test_post_replace_corruption_never_gets_a_success_receipt(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env

    def corrupt(stage: str) -> None:
        if stage == "after_active_replace":
            spec.active_path.write_bytes(b"corrupt after replace\n")

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True, fault_hook=corrupt)
    _assert_reason(exc, "post_replace_verification_failed")
    assert not spec.receipt_path.exists()


def test_preimage_fsync_failure_leaves_old_active_and_no_receipt(
    promotion_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    old = spec.active_path.read_bytes()

    def fail_fsync(_fd: int) -> None:
        raise OSError("simulated fsync failure")

    monkeypatch.setattr(mod.os, "fsync", fail_fsync)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "durability_failure")
    assert spec.active_path.read_bytes() == old
    assert not spec.receipt_path.exists()


def test_parent_directory_is_fsynced_for_durable_replace(
    promotion_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    directories: list[int] = []
    real_fsync = os.fsync

    def record_fsync(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directories.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(mod.os, "fsync", record_fsync)
    mod.promote_cfbd_data(spec, confirm=True)
    assert len(directories) >= 3, (
        "preimage, active and receipt parent dirs must be synced"
    )


@pytest.mark.parametrize(
    ("active_state", "receipt_state", "expected"),
    [
        ("old", "absent", "clean_pre_promotion"),
        ("old", "valid", "receipt_active_mismatch"),
        ("old", "corrupt", "receipt_corrupt"),
        ("new", "absent", "recovered_post_replace"),
        ("new", "valid", "complete"),
        ("new", "corrupt", "receipt_corrupt"),
        ("unknown", "absent", "unknown_active_state"),
        ("unknown", "valid", "unknown_active_state"),
        ("unknown", "corrupt", "receipt_corrupt"),
    ],
)
def test_recovery_matrix_is_exhaustive_and_fail_closed(
    promotion_env, active_state: str, receipt_state: str, expected: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    old = spec.active_path.read_bytes()
    mod.promote_cfbd_data(spec, confirm=True)
    new = spec.active_path.read_bytes()
    valid_receipt = spec.receipt_path.read_bytes()
    spec.active_path.write_bytes(
        {"old": old, "new": new, "unknown": b"unknown\n"}[active_state]
    )
    if receipt_state == "absent":
        spec.receipt_path.unlink()
    elif receipt_state == "corrupt":
        spec.receipt_path.write_text("{not-json", encoding="utf-8")
    else:
        spec.receipt_path.write_bytes(valid_receipt)

    if expected in {"clean_pre_promotion", "recovered_post_replace", "complete"}:
        assert (
            mod.recover_cfbd_promotion(
                spec, confirm=expected == "recovered_post_replace"
            )["status"]
            == expected
        )
    else:
        with pytest.raises(mod.CfbdPromotionError) as exc:
            mod.recover_cfbd_promotion(spec, confirm=False)
        _assert_reason(exc, expected)


def test_rollback_is_cas_guarded_and_preserves_the_original_receipt(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    old = spec.active_path.read_bytes()
    mod.promote_cfbd_data(spec, confirm=True)
    promotion_receipt = spec.receipt_path.read_bytes()
    preview = mod.rollback_cfbd_promotion(spec)
    assert preview["status"] == "would_roll_back"
    assert spec.active_path.read_bytes() != old
    assert not spec.rollback_receipt_path.exists()
    report = mod.rollback_cfbd_promotion(spec, confirm=True)
    assert report["status"] == "rolled_back"
    assert spec.active_path.read_bytes() == old
    assert spec.receipt_path.read_bytes() == promotion_receipt
    rollback = json.loads(spec.rollback_receipt_path.read_text(encoding="utf-8"))
    assert rollback["status"] == "rolled_back"
    assert rollback["decision_supported"] is False


def test_rollback_refuses_to_erase_intervening_bytes(promotion_env) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    mod.promote_cfbd_data(spec, confirm=True)
    intervening = b"later governed writer\n"
    spec.active_path.write_bytes(intervening)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.rollback_cfbd_promotion(spec, confirm=True)
    _assert_reason(exc, "rollback_cas_mismatch")
    assert spec.active_path.read_bytes() == intervening
    assert not spec.rollback_receipt_path.exists()


def test_lock_contention_refuses_but_a_stale_file_does_not_deadlock(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    with mod.promotion_lock(spec):
        with pytest.raises(mod.CfbdPromotionError) as exc:
            mod.promote_cfbd_data(spec, confirm=True)
        _assert_reason(exc, "promotion_locked")
    spec.lock_path.parent.mkdir(parents=True, exist_ok=True)
    spec.lock_path.write_text("stale owner pid=999999999\n", encoding="utf-8")
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"


@pytest.mark.parametrize("alias_kind", ["same_path", "hardlink", "symlink"])
def test_active_candidate_aliases_are_fatal(promotion_env, alias_kind: str) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    alias = spec.active_path
    if alias_kind != "same_path":
        alias = spec.active_path.with_name(f"alias-{alias_kind}.csv")
        if alias_kind == "hardlink":
            os.link(spec.active_path, alias)
        else:
            alias.symlink_to(spec.active_path)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(replace(spec, candidate_path=alias))
    _assert_reason(exc, "path_alias")


@pytest.mark.parametrize("artifact", ["preimage_path", "receipt_path"])
def test_evidence_collision_refuses_instead_of_overwriting(
    promotion_env, artifact: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    path = getattr(spec, artifact)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"unrelated existing evidence\n")
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "evidence_collision")
    assert path.read_bytes() == b"unrelated existing evidence\n"


# ── Destructive writers and offline entrypoint ──────────────────────────────


def test_destructive_writer_guard_refuses_an_active_promoted_projection(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    mod.promote_cfbd_data(spec, confirm=True)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="build_w2b_cfbd",
        )
    _assert_reason(exc, "promoted_projection_write_refused")


@pytest.mark.parametrize(
    "script_name", ["build_head_b_targets.py", "build_w2b_cfbd.py"]
)
def test_each_destructive_writer_calls_the_shared_guard_before_opening_for_write(
    script_name: str,
) -> None:
    source = (ROOT / "scripts" / script_name).read_text(encoding="utf-8")
    tree = ast.parse(source)
    guard_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id == "guard_destructive_cfbd_write"
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == "guard_destructive_cfbd_write"
        )
    ]
    write_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "w"
    ]
    assert guard_lines, (
        f"{script_name} does not call the shared destructive-write guard"
    )
    assert write_lines, f"{script_name} no longer has the expected write boundary"
    assert max(line for line in guard_lines if line < min(write_lines)) < min(
        write_lines
    )


def test_promotion_module_has_no_paid_network_subprocess_model_or_bakeoff_imports() -> (
    None
):
    module_path = ROOT / "src/dynasty_genius/capture/cfbd_data_promotion.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = {
        name
        for name in imported
        if name == "subprocess"
        or name.startswith(("httpx", "requests", "urllib", "socket"))
        or name.startswith("scripts")
        or "cfbd_foundation_refresh" in name
        or ".models" in name
        or ".eval" in name
    }
    assert forbidden == set()


def test_cli_is_read_only_without_confirm_and_exposes_only_governed_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = importlib.import_module("scripts.promote_cfbd_data")
    calls: list[tuple[str, bool | None]] = []

    class FakeSpec:
        pass

    monkeypatch.setattr(cli, "default_promotion_spec", lambda root=None: FakeSpec())
    monkeypatch.setattr(
        cli,
        "promote_cfbd_data",
        lambda _spec, confirm=False: (
            calls.append(("promote", confirm)) or {"status": "dry_run"}
        ),
    )
    monkeypatch.setattr(
        cli,
        "recover_cfbd_promotion",
        lambda _spec, confirm=False: (
            calls.append(("recover", confirm)) or {"status": "complete"}
        ),
    )
    monkeypatch.setattr(
        cli,
        "rollback_cfbd_promotion",
        lambda _spec, confirm=False: (
            calls.append(("rollback", confirm)) or {"status": "would_roll_back"}
        ),
    )
    assert cli.main([]) == 0
    assert calls == [("promote", False)]
    assert "dry_run" in capsys.readouterr().out
    assert cli.main(["--confirm"]) == 0
    assert cli.main(["--recover"]) == 0
    assert cli.main(["--rollback"]) == 0
    assert calls == [
        ("promote", False),
        ("promote", True),
        ("recover", False),
        ("rollback", False),
    ]
