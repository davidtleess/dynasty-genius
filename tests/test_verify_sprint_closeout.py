import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "vsc",
    Path(__file__).resolve().parents[1] / "scripts" / "verify_sprint_closeout.py",
)
vsc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = vsc
_SPEC.loader.exec_module(vsc)


def test_checkresult_and_tiers():
    assert vsc.ENFORCE == "ENFORCE"
    assert vsc.REPORT == "REPORT"
    assert vsc.REMIND == "REMIND"

    result = vsc.CheckResult(
        name="x",
        tier=vsc.ENFORCE,
        passed=True,
        detail="ok",
    )
    assert (result.name, result.tier, result.passed, result.detail) == (
        "x",
        "ENFORCE",
        True,
        "ok",
    )

    report = vsc.CheckResult(
        name="y",
        tier=vsc.REPORT,
        passed=None,
        detail="d",
    )
    assert report.passed is None
