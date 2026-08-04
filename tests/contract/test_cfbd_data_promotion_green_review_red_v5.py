"""Fifth independent GREEN-review RED amendment for CFBD DATA promotion.

These cases bind the post-execution jurisdiction repair. Jurisdiction comes from
trusted caller configuration, never from the receipt being judged. All writes stay
below ``tmp_path``; no real promotion artifact is read or mutated.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tests.contract.test_cfbd_data_promotion_red import _write_json

pytest_plugins = ("tests.contract.test_cfbd_data_promotion_red",)


def _assert_reason(exc: pytest.ExceptionInfo[BaseException], reason: str) -> None:
    assert getattr(exc.value, "reason", None) == reason, str(exc.value)


def _promote(mod, spec) -> None:
    report = mod.promote_cfbd_data(spec, confirm=True)
    assert report["status"] == "promoted"


def test_receipt_active_path_cannot_self_exempt_governed_target(promotion_env) -> None:
    """Changing only receipt.active_path must not disable the real-file guard."""
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    payload = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
    payload["active_path"] = str(spec.active_path.with_name("decoy.csv"))
    _write_json(spec.receipt_path, payload)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            governed_active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "promotion_receipt_invalid")


def test_valid_receipt_has_no_jurisdiction_over_unrelated_target(
    promotion_env, tmp_path: Path
) -> None:
    """A trusted target mismatch is silent even if the unrelated file is not a projection."""
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    unrelated = tmp_path / "fixture-world" / "unrelated.csv"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("not,a,governed,projection\n", encoding="utf-8")

    mod.guard_destructive_cfbd_write(
        active_path=unrelated,
        governed_active_path=spec.active_path,
        receipt_path=spec.receipt_path,
        writer_name="test_writer",
    )


def test_unreadable_receipt_has_no_jurisdiction_over_unrelated_target(
    promotion_env, tmp_path: Path
) -> None:
    """Jurisdiction is established before reading evidence from another world."""
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)
    spec.receipt_path.write_text("{not-json", encoding="utf-8")
    unrelated = tmp_path / "fixture-world" / "unrelated.csv"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("fixture\n", encoding="utf-8")

    mod.guard_destructive_cfbd_write(
        active_path=unrelated,
        governed_active_path=spec.active_path,
        receipt_path=spec.receipt_path,
        writer_name="test_writer",
    )


def test_canonical_target_still_refuses_destructive_write(promotion_env) -> None:
    """The trusted jurisdiction repair must not weaken the live protected path."""
    mod, spec, _manifest, _raw_manifest = promotion_env
    _promote(mod, spec)

    with pytest.raises(mod.CfbdPromotionError) as exc:
        mod.guard_destructive_cfbd_write(
            active_path=spec.active_path,
            governed_active_path=spec.active_path,
            receipt_path=spec.receipt_path,
            writer_name="test_writer",
        )
    _assert_reason(exc, "promoted_projection_write_refused")


@pytest.mark.parametrize(
    "relative_path",
    ["scripts/build_head_b_targets.py", "scripts/build_w2b_cfbd.py"],
)
def test_each_destructive_producer_declares_trusted_guard_jurisdiction(
    relative_path: str,
) -> None:
    """Neither live writer may fall back to receipt-defined jurisdiction."""
    root = Path(__file__).resolve().parents[2]
    tree = ast.parse((root / relative_path).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "guard_destructive_cfbd_write"
    ]
    assert len(calls) == 1
    keywords = {keyword.arg for keyword in calls[0].keywords}
    assert "governed_active_path" in keywords
