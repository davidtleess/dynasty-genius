"""Seventh independent GREEN-review RED: unknown path identity fails closed.

The shared identity primitive must not collapse an OS/stat failure into "different
files", because the guard interprets "different" as permission. This synthetic
failure case stays wholly below ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ("tests.contract.test_cfbd_data_promotion_red",)


def _assert_reason(exc: pytest.ExceptionInfo[BaseException], reason: str) -> None:
    assert getattr(exc.value, "reason", None) == reason, str(exc.value)


def test_unknown_alias_identity_cannot_become_out_of_jurisdiction_permission(
    promotion_env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    report = mod.promote_cfbd_data(spec, confirm=True)
    assert report["status"] == "promoted"
    alias = tmp_path / "active-alias.csv"
    alias.symlink_to(spec.active_path)

    original_resolve = Path.resolve
    original_samefile = Path.samefile

    def unreadable_resolve(self: Path, *args, **kwargs):
        if self in {alias, spec.active_path}:
            raise OSError("synthetic path-identity failure")
        return original_resolve(self, *args, **kwargs)

    def unreadable_samefile(self: Path, other: Path):
        if self in {alias, spec.active_path}:
            raise OSError("synthetic inode-identity failure")
        return original_samefile(self, other)

    monkeypatch.setattr(Path, "resolve", unreadable_resolve)
    monkeypatch.setattr(Path, "samefile", unreadable_samefile)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=alias,
            governed_active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "path_identity_unreadable")
