"""Second independent GREEN-review RED amendment for CFBD DATA promotion.

The first 25-case review amendment remains byte-immutable. These tests cover
residuals visible only after reading GREEN v2. All mutations stay below
``tmp_path``.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from tests.contract.test_cfbd_data_promotion_red import _sha, _write_json

pytest_plugins = ("tests.contract.test_cfbd_data_promotion_red",)


def _assert_reason(exc: pytest.ExceptionInfo[BaseException], reason: str) -> None:
    assert getattr(exc.value, "reason", None) == reason, str(exc.value)


class _Crash(BaseException):
    pass


def _create_split_state(mod, spec) -> None:
    def crash(stage: str) -> None:
        if stage == "after_active_replace":
            raise _Crash

    with pytest.raises(_Crash):
        mod.promote_cfbd_data(spec, confirm=True, fault_hook=crash)
    spec.lock_path.unlink(missing_ok=True)


def test_confirm_revalidates_under_lock_before_writing_preimage(
    promotion_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    candidate = spec.candidate_path.read_bytes()

    @contextmanager
    def mutate_before_lock_body(_spec):
        spec.active_path.write_bytes(candidate)
        yield

    monkeypatch.setattr(mod, "promotion_lock", mutate_before_lock_body)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "active_changed_during_promotion")
    assert spec.active_path.read_bytes() == candidate
    assert not spec.preimage_path.exists()
    assert not spec.receipt_path.exists()


def test_recovery_revalidates_split_state_under_lock_before_receipting(
    promotion_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _create_split_state(mod, spec)
    intervening = b"concurrent writer after recovery classification\n"

    @contextmanager
    def mutate_before_lock_body(_spec):
        spec.active_path.write_bytes(intervening)
        yield

    monkeypatch.setattr(mod, "promotion_lock", mutate_before_lock_body)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.recover_cfbd_promotion(spec, confirm=True)
    _assert_reason(exc, "active_changed_during_recovery")
    assert spec.active_path.read_bytes() == intervening
    assert not spec.receipt_path.exists()


def test_rollback_rechecks_cas_under_lock_before_replacing_unknown_bytes(
    promotion_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"
    intervening = b"concurrent writer after rollback classification\n"

    @contextmanager
    def mutate_before_lock_body(_spec):
        spec.active_path.write_bytes(intervening)
        yield

    monkeypatch.setattr(mod, "promotion_lock", mutate_before_lock_body)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.rollback_cfbd_promotion(spec, confirm=True)
    _assert_reason(exc, "rollback_cas_mismatch")
    assert spec.active_path.read_bytes() == intervening
    assert not spec.rollback_receipt_path.exists()


def test_rollback_receipt_collision_is_refused_before_active_moves(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"
    promoted = spec.active_path.read_bytes()
    unrelated = b"unrelated durable rollback evidence\n"
    spec.rollback_receipt_path.write_bytes(unrelated)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.rollback_cfbd_promotion(spec, confirm=True)
    _assert_reason(exc, "evidence_collision")
    assert spec.active_path.read_bytes() == promoted
    assert spec.rollback_receipt_path.read_bytes() == unrelated


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "rolled_back"),
        ("decision_supported", True),
        ("after_projection_sha256", "not-the-pinned-projection"),
    ],
)
def test_idempotence_rejects_receipt_values_from_a_different_transaction(
    promotion_env, field: str, value: object
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"
    receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    receipt[field] = value
    _write_json(spec.receipt_path, receipt)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "receipt_invalid")


def test_idempotence_rejects_receipt_that_names_an_unrelated_matching_file(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"
    receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    receipt["preimage_path"] = str(spec.candidate_path)
    receipt["before_sha256"] = _sha(spec.candidate_path)
    _write_json(spec.receipt_path, receipt)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "receipt_invalid")


def test_guard_rejects_partial_receipt_even_if_projection_digest_is_present(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    spec.receipt_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        spec.receipt_path,
        {"after_projection_sha256": spec.expected_active_projection_sha256},
    )
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "promotion_receipt_invalid")


def test_raw_file_count_is_a_required_manifest_field(promotion_env) -> None:
    mod, spec, manifest, raw_manifest_path = promotion_env
    manifest.pop("raw_file_count", None)
    _write_json(spec.manifest_path, manifest)
    _write_json(raw_manifest_path, manifest)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.validate_promotion(spec)
    _assert_reason(exc, "raw_file_count_mismatch")


@pytest.mark.parametrize(
    ("artifact", "target"),
    [
        ("preimage_path", "candidate_path"),
        ("receipt_path", "preimage_path"),
        ("rollback_receipt_path", "active_path"),
        ("lock_path", "active_path"),
        ("lock_path", "candidate_path"),
    ],
)
def test_every_transaction_artifact_role_is_path_distinct(
    promotion_env, artifact: str, target: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    active_before = spec.active_path.read_bytes()
    candidate_before = spec.candidate_path.read_bytes()
    aliased = replace(spec, **{artifact: Path(getattr(spec, target))})

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(aliased, confirm=True)
    _assert_reason(exc, "path_alias")
    assert spec.active_path.read_bytes() == active_before
    assert spec.candidate_path.read_bytes() == candidate_before
