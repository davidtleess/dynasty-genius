"""Third independent GREEN-review RED amendment for CFBD DATA promotion.

The earlier RED blobs remain immutable. These tests cover residual evidence races
and path/receipt semantics visible only after reading the 100/100 GREEN. All
mutations stay below ``tmp_path``.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import replace

import pytest

from tests.contract.test_cfbd_data_promotion_red import _write_json

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


def test_manifest_is_a_distinct_governed_role_not_a_permitted_lock_alias(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    active_before = spec.active_path.read_bytes()
    candidate_before = spec.candidate_path.read_bytes()
    manifest_before = spec.manifest_path.read_bytes()
    aliased = replace(spec, lock_path=spec.manifest_path)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(aliased, confirm=True)
    _assert_reason(exc, "path_alias")
    assert spec.active_path.read_bytes() == active_before
    assert spec.candidate_path.read_bytes() == candidate_before
    assert spec.manifest_path.read_bytes() == manifest_before
    assert not spec.preimage_path.exists()
    assert not spec.receipt_path.exists()


@pytest.mark.parametrize(
    "field",
    [
        "model_changed",
        "bakeoff_run",
        "predictive_validation_run",
        "promotion_decision",
    ],
)
def test_idempotence_requires_the_complete_honesty_block(
    promotion_env, field: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"
    receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    receipt.pop(field)
    _write_json(spec.receipt_path, receipt)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "receipt_invalid")


@pytest.mark.parametrize("field", ["active_path", "candidate_path"])
def test_idempotence_requires_receipt_paths_to_match_this_transaction(
    promotion_env, field: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"
    receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    receipt[field] = str(spec.receipt_path.parent / f"foreign-{field}")
    _write_json(spec.receipt_path, receipt)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "receipt_invalid")


@pytest.mark.parametrize("artifact", ["preimage", "receipt"])
def test_promotion_rechecks_evidence_occupancy_under_lock_before_first_write(
    promotion_env, monkeypatch: pytest.MonkeyPatch, artifact: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    active_before = spec.active_path.read_bytes()
    evidence_path = spec.preimage_path if artifact == "preimage" else spec.receipt_path
    unrelated = f"concurrent {artifact} evidence\n".encode()

    @contextmanager
    def occupy_before_lock_body(_spec):
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(unrelated)
        yield

    monkeypatch.setattr(mod, "promotion_lock", occupy_before_lock_body)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(exc, "evidence_collision")
    assert spec.active_path.read_bytes() == active_before
    assert evidence_path.read_bytes() == unrelated


@pytest.mark.parametrize(
    ("artifact", "reason"),
    [("preimage", "evidence_incomplete"), ("receipt", "evidence_collision")],
)
def test_recovery_rechecks_evidence_under_lock_before_receipting(
    promotion_env,
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
    reason: str,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _create_split_state(mod, spec)
    promoted = spec.active_path.read_bytes()
    evidence_path = spec.preimage_path if artifact == "preimage" else spec.receipt_path
    unrelated = f"concurrent {artifact} evidence\n".encode()

    @contextmanager
    def mutate_before_lock_body(_spec):
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(unrelated)
        yield

    monkeypatch.setattr(mod, "promotion_lock", mutate_before_lock_body)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.recover_cfbd_promotion(spec, confirm=True)
    _assert_reason(exc, reason)
    assert spec.active_path.read_bytes() == promoted
    assert evidence_path.read_bytes() == unrelated


def test_rollback_rechecks_preimage_under_lock_before_replacing_active(
    promotion_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    assert mod.promote_cfbd_data(spec, confirm=True)["status"] == "promoted"
    promoted = spec.active_path.read_bytes()
    unrelated = b"concurrent preimage replacement\n"

    @contextmanager
    def mutate_before_lock_body(_spec):
        spec.preimage_path.write_bytes(unrelated)
        yield

    monkeypatch.setattr(mod, "promotion_lock", mutate_before_lock_body)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.rollback_cfbd_promotion(spec, confirm=True)
    _assert_reason(exc, "evidence_incomplete")
    assert spec.active_path.read_bytes() == promoted
    assert spec.preimage_path.read_bytes() == unrelated
    assert not spec.rollback_receipt_path.exists()
