"""Fourth independent GREEN-review RED amendment for CFBD DATA promotion.

The earlier RED blobs remain immutable. These cases cover incomplete application
of the G16 role gate and G18 under-lock revalidation. All mutations stay below
``tmp_path``.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

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


def test_confirmed_recovery_applies_role_gate_before_lock_can_delete_manifest(
    promotion_env,
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    _create_split_state(mod, spec)
    promoted = spec.active_path.read_bytes()
    preimage = spec.preimage_path.read_bytes()
    manifest = spec.manifest_path.read_bytes()
    aliased = replace(spec, lock_path=spec.manifest_path)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.recover_cfbd_promotion(aliased, confirm=True)
    _assert_reason(exc, "path_alias")
    assert spec.active_path.read_bytes() == promoted
    assert spec.preimage_path.read_bytes() == preimage
    assert spec.manifest_path.read_bytes() == manifest
    assert not spec.receipt_path.exists()


@pytest.mark.parametrize("provenance", ["latest_manifest", "raw_payload"])
def test_confirmed_promotion_revalidates_provenance_under_lock_before_first_write(
    promotion_env,
    monkeypatch: pytest.MonkeyPatch,
    provenance: str,
) -> None:
    mod, spec, manifest, _raw_manifest = promotion_env
    active = spec.active_path.read_bytes()
    raw_payload = json.loads(spec.manifest_path.read_text(encoding="utf-8"))
    raw_file = next(
        path
        for path in sorted(Path(raw_payload["raw_root"]).glob("*.json"))
        if path.name != "manifest.json"
    )

    @contextmanager
    def mutate_provenance_before_lock_body(_spec):
        if provenance == "latest_manifest":
            changed = {**manifest, "run_id": "concurrent-run"}
            _write_json(spec.manifest_path, changed)
        else:
            raw_file.write_text('{"concurrent":true}\n', encoding="utf-8")
        yield

    monkeypatch.setattr(mod, "promotion_lock", mutate_provenance_before_lock_body)
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.promote_cfbd_data(spec, confirm=True)
    _assert_reason(
        exc,
        "raw_manifest_mismatch"
        if provenance == "latest_manifest"
        else "raw_content_mismatch",
    )
    assert spec.active_path.read_bytes() == active
    assert not spec.preimage_path.exists()
    assert not spec.receipt_path.exists()
