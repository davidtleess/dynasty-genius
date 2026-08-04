"""Sixth independent GREEN-review RED amendment for guard jurisdiction identity.

Trusted jurisdiction is file identity, not lexical Path spelling. These cases stay
below ``tmp_path`` and never read or mutate the live promotion.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ("tests.contract.test_cfbd_data_promotion_red",)


def _assert_reason(exc: pytest.ExceptionInfo[BaseException], reason: str) -> None:
    assert getattr(exc.value, "reason", None) == reason, str(exc.value)


@pytest.mark.parametrize("alias_kind", ["symlink", "dotdot"])
def test_path_alias_to_governed_active_cannot_escape_jurisdiction(
    promotion_env, tmp_path: Path, alias_kind: str
) -> None:
    mod, spec, _manifest, _raw_manifest = promotion_env
    report = mod.promote_cfbd_data(spec, confirm=True)
    assert report["status"] == "promoted"

    if alias_kind == "symlink":
        alias = tmp_path / "active-alias.csv"
        alias.symlink_to(spec.active_path)
    else:
        lexical_parent = spec.active_path.parent / "lexical-alias"
        lexical_parent.mkdir()
        alias = lexical_parent / ".." / spec.active_path.name

    assert alias != spec.active_path
    assert alias.resolve() == spec.active_path.resolve()
    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=alias,
            governed_active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "promoted_projection_write_refused")

