"""Independent Round-19 failure-observability falsification probe.

This does not run registered composition. Every artifact is written below a
temporary directory and challenged only for envelope ordering, non-disclosure,
traceback containment, and process-control behavior.
"""
from __future__ import annotations

import importlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

qb = importlib.import_module("src.dynasty_genius.eval.qb_validation")


SENTINEL = "R19-CODEX-PROBE-REGISTERED-VALUE-DO-NOT-SERIALIZE"
ENVELOPE_KEYS = {
    "schema_version",
    "generated_at",
    "registration_hash",
    "run_status",
    "failure_reason",
    "decision_supported",
}


def _destination(root: Path, name: str) -> Path:
    return root / "app/data/backtest/qb_validation" / f"{name}.json"


def _assert_envelope(path: Path, reason: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    assert set(report) == ENVELOPE_KEYS
    assert report["run_status"] == "failed"
    assert report["failure_reason"] == reason
    assert report["decision_supported"] is False
    assert SENTINEL not in path.read_text(encoding="utf-8")
    return report


def _run(
    root: Path,
    name: str,
    execute: Any,
    observer: Any,
) -> tuple[dict[str, Any], Path]:
    path = _destination(root, name)
    report = qb.run_qb1_study(
        execute=execute,
        output_path=path,
        registration_hash=qb.REGISTRATION_PIN,
        generated_at="2026-08-16T23:59:59Z",
        repo_root=root,
        failure_observer=observer,
    )
    return report, path


def _named_refusal() -> dict[str, Any]:
    raise qb.QBValidationFailure("stat_value_invalid", SENTINEL)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # The callback must observe the already-complete six-key artifact.
        ordering_seen: list[dict[str, Any]] = []
        ordering_path = _destination(root, "ordering")

        def ordering_observer(diagnostic: dict[str, Any]) -> None:
            _assert_envelope(ordering_path, "stat_value_invalid")
            ordering_seen.append(diagnostic)

        _run(root, "ordering", _named_refusal, ordering_observer)
        assert len(ordering_seen) == 1
        assert ordering_seen[0]["phase"] == "execute"
        assert SENTINEL not in json.dumps(ordering_seen)
        print("PASS artifact_before_observer_and_detail_absent")

        # A post-assembly schema refusal has the other closed phase value.
        gate_seen: list[dict[str, Any]] = []
        _run(
            root,
            "gate",
            lambda: {"run_status": SENTINEL},
            gate_seen.append,
        )
        _assert_envelope(_destination(root, "gate"), "report_schema_invalid")
        assert len(gate_seen) == 1
        assert gate_seen[0]["phase"] == "publication_gate"
        assert SENTINEL not in json.dumps(gate_seen)
        print("PASS publication_gate_phase_and_payload_absent")

        # An ordinary exception preserves the established no-diagnostic path.
        generic_seen: list[dict[str, Any]] = []

        def generic_failure() -> dict[str, Any]:
            raise ValueError(SENTINEL)

        _run(root, "generic", generic_failure, generic_seen.append)
        _assert_envelope(_destination(root, "generic"), "execution_error")
        assert generic_seen == []
        print("PASS generic_exception_has_no_diagnostic")

        # An out-of-repository compiled frame must never appear in the sites.
        namespace = {"QBValidationFailure": qb.QBValidationFailure, "SENTINEL": SENTINEL}
        exec(
            compile(
                "def external_raise():\n"
                "    raise QBValidationFailure('stat_value_invalid', SENTINEL)\n",
                "/tmp/R19-SENTINEL-EXTERNAL-FRAME.py",
                "exec",
            ),
            namespace,
        )
        contained_seen: list[dict[str, Any]] = []

        def in_repo_caller() -> dict[str, Any]:
            namespace["external_raise"]()
            raise AssertionError("unreachable")

        _run(root, "contained", in_repo_caller, contained_seen.append)
        sites = contained_seen[0]["sites"]
        assert sites
        assert all(not Path(site["path"]).is_absolute() for site in sites)
        assert all(".." not in Path(site["path"]).parts for site in sites)
        assert all("R19-SENTINEL-EXTERNAL-FRAME" not in site["path"] for site in sites)
        print("PASS external_frame_omitted_and_paths_contained")

        # BaseException process control still propagates, but only after the
        # atomic envelope exists; ordinary observer exceptions are covered by
        # the contract suite and Claude's separate adversarial probe.
        control_path = _destination(root, "control")

        def control_observer(_diagnostic: dict[str, Any]) -> None:
            raise SystemExit(73)

        try:
            _run(root, "control", _named_refusal, control_observer)
        except SystemExit as failure:
            assert failure.code == 73
        else:
            raise AssertionError("observer SystemExit did not propagate")
        _assert_envelope(control_path, "stat_value_invalid")
        print("PASS process_control_propagates_after_artifact")

    print("ALL 5 INDEPENDENT R19 PROBES PASS")


if __name__ == "__main__":
    main()
