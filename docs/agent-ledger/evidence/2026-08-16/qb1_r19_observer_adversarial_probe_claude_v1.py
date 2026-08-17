"""R19 self-probe (Claude, pre-routing): adversarial inputs to the observer
seam BEYOND the correction contracts. Read-only against product code; writes
only under a tempdir. Every case must keep the atomic six-key envelope and
never leak detail. Run:
    .venv/bin/python3.14 docs/agent-ledger/evidence/2026-08-16/qb1_r19_observer_adversarial_probe_claude_v1.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import src.dynasty_genius.eval.qb_validation as qb  # noqa: E402

SENTINEL = "R19-PROBE-SENTINEL--3.14159--NEVER-PERSISTED"
ENVELOPE = [
    "decision_supported",
    "failure_reason",
    "generated_at",
    "registration_hash",
    "run_status",
    "schema_version",
]


def refusing() -> dict:
    raise qb.QBValidationFailure("stat_value_invalid", SENTINEL)


def run_case(name: str, observer) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "app/data/backtest/qb_validation/report.json"
        report = qb.run_qb1_study(
            execute=refusing,
            output_path=dest,
            registration_hash=qb.REGISTRATION_PIN,
            generated_at="2026-08-16T23:59:00Z",
            repo_root=Path(tmp),
            failure_observer=observer,
        )
        artifact = json.loads(dest.read_text())
        assert sorted(artifact) == ENVELOPE, (name, sorted(artifact))
        assert artifact["run_status"] == "failed", name
        assert artifact["failure_reason"] == "stat_value_invalid", name
        assert SENTINEL not in dest.read_text(), name
        assert report["run_status"] == "failed", name
    print(f"PASS {name}")


def main() -> None:
    # 1. Non-callable observer: calling it raises TypeError inside the notify
    #    helper — swallowed; envelope already on disk.
    run_case("non_callable_observer", 42)

    # 2. Observer that mutates the diagnostic then raises: neither the
    #    mutation nor the raise reaches the artifact or the caller.
    def mutate_and_raise(diagnostic) -> None:
        diagnostic["sites"] = None
        diagnostic["phase"] = SENTINEL
        raise RuntimeError(SENTINEL)

    run_case("mutating_raising_observer", mutate_and_raise)

    # 3. Observer that recursively re-enters the runner (hostile reentrancy):
    #    the inner run writes its own tempdir artifact; the outer envelope
    #    stays intact; no recursion blowup because the inner observer is None.
    def reentrant(_diagnostic) -> None:
        with tempfile.TemporaryDirectory() as inner:
            inner_dest = Path(inner) / "app/data/backtest/qb_validation/r.json"
            qb.run_qb1_study(
                execute=refusing,
                output_path=inner_dest,
                registration_hash=qb.REGISTRATION_PIN,
                generated_at="2026-08-16T23:59:01Z",
                repo_root=Path(inner),
            )

    run_case("reentrant_observer", reentrant)

    # 4. Lambda raise site: code-object name is the identifier "<lambda>" —
    #    still no value leakage, envelope intact, diagnostic well-formed.
    captured: list = []
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "app/data/backtest/qb_validation/report.json"
        qb.run_qb1_study(
            execute=lambda: (_ for _ in ()).throw(
                qb.QBValidationFailure("stat_value_invalid", SENTINEL)
            ),
            output_path=dest,
            registration_hash=qb.REGISTRATION_PIN,
            generated_at="2026-08-16T23:59:02Z",
            repo_root=Path(tmp),
            failure_observer=captured.append,
        )
        assert captured, "lambda case must emit a diagnostic"
        blob = json.dumps(captured)
        assert SENTINEL not in blob
        for site in captured[0]["sites"]:
            assert not Path(site["path"]).is_absolute()
            assert ".." not in Path(site["path"]).parts
    print("PASS lambda_raise_site")

    # 5. Detail-free failure (empty detail): diagnostic still emitted; shape
    #    identical — the channel is content-independent by construction.
    captured2: list = []

    def bare() -> dict:
        raise qb.QBValidationFailure("stat_value_invalid")

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "app/data/backtest/qb_validation/report.json"
        qb.run_qb1_study(
            execute=bare,
            output_path=dest,
            registration_hash=qb.REGISTRATION_PIN,
            generated_at="2026-08-16T23:59:03Z",
            repo_root=Path(tmp),
            failure_observer=captured2.append,
        )
    assert captured2 and sorted(captured2[0]) == ["phase", "sites"]
    print("PASS detail_free_failure")

    print("ALL 5 PROBE CASES PASS")


if __name__ == "__main__":
    main()
