"""DG-045 / SR-09 RED — the dependency-ordered, fail-soft daily chain (steps 1-5).

Written test-first 2026-08-26 (D4 afternoon, pulled forward on David's go),
before ``scripts/run_daily_chain.py`` existed. Spec:
docs/strategies/2026-08-20-dg-SEASON-BUILD-SPEC.md SR-09 (:795-900) and the
PT-4b amendment (``--runtime-override``, :41-42 + SR-19 :1131-1170). Ticket:
~/dg-build/tickets/DG-045-sr09-dependency-ordered-fail-soft-chain.md.

Everything here is hermetic: injected step tables run ``python3 -c`` stubs,
reports land in tmp_path, and the live producers are never executed. The only
reads of real repo state are the tracked plists' argument vectors, mirrored as
constants (re-dumped live 2026-08-26 12:47 and verified identical to spec:814-836).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _chain():
    """Load scripts/run_daily_chain.py as a module (scripts/ is no package).

    The module must sit in ``sys.modules`` before exec: dataclass annotation
    resolution on 3.14 looks the defining module up by name.
    """
    name = "run_daily_chain"
    if name in sys.modules:
        return sys.modules[name]
    path = REPO_ROOT / "scripts" / "run_daily_chain.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


PY = ".venv/bin/python3.14"

EXPECTED_ORDER = (
    "run_fc_forward_capture",
    "run_feature_refresh",
    "run_league_snapshot_capture",
    "run_pvo_refresh",
    "run_market_divergence_refresh",
    "run_what_changed_report",
)

EXPECTED_TARGETS = ((9, 0), (9, 15), (9, 20), (9, 30), (9, 40), (9, 45))


class TestStepTable:
    """Spec step 1 (exact live argument vectors) + step 2 (edges as data)."""

    def test_six_steps_in_slot_order(self):
        steps = _chain().build_steps(REPO_ROOT)
        assert tuple(s.name for s in steps) == EXPECTED_ORDER

    def test_single_hard_edge_market_needs_fc(self):
        steps = _chain().build_steps(REPO_ROOT)
        by_name = {s.name: s for s in steps}
        assert by_name["run_market_divergence_refresh"].hard_upstreams == (
            "run_fc_forward_capture",
        )
        for name in EXPECTED_ORDER:
            if name != "run_market_divergence_refresh":
                assert by_name[name].hard_upstreams == ()

    def test_targets_match_the_retired_wall_clock_slots(self):
        steps = _chain().build_steps(REPO_ROOT)
        assert tuple(s.target for s in steps) == EXPECTED_TARGETS

    def test_fc_argv_matches_live_plist_verbatim(self):
        root = Path("/scratch/rooted")
        steps = _chain().build_steps(root)
        fc = next(s for s in steps if s.name == "run_fc_forward_capture")
        assert fc.argv == (
            str(root / PY),
            str(root / "scripts" / "run_fc_forward_capture.py"),
            "--db-path",
            str(root / "app" / "data" / "fc_forward_capture.db"),
            "--report-path",
            str(root / "app" / "data" / "capture" / "fc_forward_capture_latest_report.json"),
        )

    def test_market_argv_matches_live_plist_verbatim(self):
        root = Path("/scratch/rooted")
        steps = _chain().build_steps(root)
        market = next(s for s in steps if s.name == "run_market_divergence_refresh")
        assert market.argv == (
            str(root / PY),
            str(root / "scripts" / "run_market_divergence_refresh.py"),
            "--latest-path",
            str(root / "app" / "data" / "valuation" / "universe_market_divergence_latest.json"),
            "--coverage-latest-path",
            str(
                root
                / "app"
                / "data"
                / "valuation"
                / "universe_market_divergence_coverage_latest.json"
            ),
            "--history-db-path",
            str(root / "app" / "data" / "market_divergence_history.db"),
            "--fc-forward-capture-db-path",
            str(root / "app" / "data" / "fc_forward_capture.db"),
            "--fc-source",
            "fc_native",
            "--fc-settings-hash",
            "e27351d720e9fcf0",
            "--marker-path",
            str(
                root
                / "app"
                / "data"
                / "valuation_runtime"
                / "market_divergence_refresh_status_latest.json"
            ),
            "--report-path",
            str(
                root
                / "app"
                / "data"
                / "valuation_runtime"
                / "market_divergence_refresh_latest_report.json"
            ),
        )

    def test_bare_vector_steps_carry_no_arguments(self):
        root = Path("/scratch/rooted")
        steps = _chain().build_steps(root)
        by_name = {s.name: s for s in steps}
        assert by_name["run_feature_refresh"].argv == (
            str(root / PY),
            str(root / "scripts" / "run_feature_refresh.py"),
        )
        assert by_name["run_what_changed_report"].argv == (
            str(root / PY),
            str(root / "scripts" / "run_what_changed_report.py"),
        )


def _stub(name, code=0, upstreams=()):
    """A ChainStep whose subprocess exits with ``code`` and touches nothing."""
    chain = _chain()
    return chain.ChainStep(
        name=name,
        argv=(sys.executable, "-c", f"raise SystemExit({code})"),
        hard_upstreams=tuple(upstreams),
        target=(9, 0),
    )


def _report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestExecution:
    """Spec steps 3-4: three statuses, fail-soft, report, chain exit code."""

    def test_all_ok_chain_exits_zero_and_reports_ok(self, tmp_path):
        chain = _chain()
        steps = (_stub("a"), _stub("b"), _stub("c"))
        report_path = tmp_path / "chain.json"
        exit_code = chain.execute_chain(steps, report_path=report_path)
        assert exit_code == 0
        report = _report(report_path)
        assert [s["status"] for s in report["steps"]] == ["ok", "ok", "ok"]
        assert [s["exit_code"] for s in report["steps"]] == [0, 0, 0]

    def test_fail_soft_a_mid_chain_failure_does_not_stop_later_steps(self, tmp_path):
        chain = _chain()
        steps = (
            _stub("s1"),
            _stub("s2", code=1),
            _stub("s3"),
            _stub("s4"),
            _stub("s5"),
            _stub("s6"),
        )
        report_path = tmp_path / "chain.json"
        exit_code = chain.execute_chain(steps, report_path=report_path)
        assert exit_code != 0
        by_name = {s["name"]: s for s in _report(report_path)["steps"]}
        assert by_name["s2"]["status"] == "failed"
        assert by_name["s2"]["exit_code"] == 1
        for name in ("s1", "s3", "s4", "s5", "s6"):
            assert by_name[name]["status"] == "ok"

    def test_hard_edge_failed_upstream_skips_only_its_dependent(self, tmp_path):
        chain = _chain()
        steps = (
            _stub("s1", code=1),
            _stub("s2"),
            _stub("s3"),
            _stub("s4"),
            _stub("s5", upstreams=("s1",)),
            _stub("s6"),
        )
        report_path = tmp_path / "chain.json"
        exit_code = chain.execute_chain(steps, report_path=report_path)
        assert exit_code != 0
        by_name = {s["name"]: s for s in _report(report_path)["steps"]}
        assert by_name["s1"]["status"] == "failed"
        assert by_name["s5"]["status"] == "skipped_upstream_failed"
        assert by_name["s5"]["exit_code"] is None
        for name in ("s2", "s3", "s4", "s6"):
            assert by_name[name]["status"] == "ok"

    def test_report_written_even_when_every_step_fails(self, tmp_path):
        chain = _chain()
        steps = (_stub("a", code=1), _stub("b", code=2))
        report_path = tmp_path / "chain.json"
        assert chain.execute_chain(steps, report_path=report_path) != 0
        report = _report(report_path)
        assert [s["exit_code"] for s in report["steps"]] == [1, 2]

    def test_steps_record_started_at_and_duration(self, tmp_path):
        chain = _chain()
        report_path = tmp_path / "chain.json"
        chain.execute_chain((_stub("a"),), report_path=report_path)
        step = _report(report_path)["steps"][0]
        assert isinstance(step["started_at"], str) and "T" in step["started_at"]
        assert isinstance(step["duration_s"], float)


class TestAlertCrossContract:
    """The report this chain writes IS what DG-044's alert reads. Feed one to
    the other — the two tickets must never drift apart silently."""

    def _alert_module(self):
        name = "run_capture_gap_alert"
        if name in sys.modules:
            return sys.modules[name]
        path = REPO_ROOT / "scripts" / "run_capture_gap_alert.py"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[name]
            raise
        return module

    def test_healthy_chain_report_is_silent_in_the_alert(self, tmp_path):
        chain = _chain()
        report_path = tmp_path / "chain.json"
        chain.execute_chain((_stub("a"), _stub("b")), report_path=report_path)
        assert self._alert_module().chain_report_lines(report_path) == []

    def test_failed_and_skipped_steps_each_get_one_alert_line(self, tmp_path):
        chain = _chain()
        report_path = tmp_path / "chain.json"
        chain.execute_chain(
            (_stub("s1", code=1), _stub("s5", upstreams=("s1",))),
            report_path=report_path,
        )
        lines = self._alert_module().chain_report_lines(report_path)
        assert len(lines) == 2
        assert any("s1" in ln and "exit_code 1" in ln for ln in lines)
        assert any("s5" in ln and "skipped_upstream_failed" in ln for ln in lines)


class TestDrift:
    """Spec step 5: preserve the point-in-time truth the wall clock hides."""

    def test_report_records_target_actual_and_drift(self, tmp_path):
        import datetime as dt

        chain = _chain()
        late = dt.datetime(2026, 8, 26, 11, 42, 0).astimezone()
        report_path = tmp_path / "chain.json"
        chain.execute_chain(
            (_stub("a"),), report_path=report_path, now_fn=lambda: late
        )
        top = _report(report_path)["chain"]
        assert top["target_start"] == "09:00"
        assert top["started_at"].startswith("2026-08-26T11:42")
        assert top["drift_minutes"] == 162


class TestDefaultReportPath:
    """The alert reads app/data/ops/daily_chain_latest_report.json (its
    Runtime wiring, run_capture_gap_alert.py:970). The chain must write
    exactly there by default, resolved from the repo root — never hardcoded."""

    def test_default_path_is_what_the_alert_reads(self, tmp_path):
        chain = _chain()
        assert chain.default_report_path(tmp_path) == (
            tmp_path / "app" / "data" / "ops" / "daily_chain_latest_report.json"
        )


class TestRuntimeOverride:
    """PT-4b amendment: SR-19 runs the chain with --runtime-override $SCRATCH
    and the live runtime must be untouched. Data-driven per-step redirect."""

    def test_app_data_paths_are_rerooted_under_the_override(self, tmp_path):
        chain = _chain()
        root = Path("/scratch/rooted")
        override = tmp_path / "rehearsal"
        steps = chain.apply_runtime_override(
            chain.build_steps(root), repo_root=root, override_dir=override
        )
        fc = next(s for s in steps if s.name == "run_fc_forward_capture")
        assert str(override / "fc_forward_capture.db") in fc.argv
        assert str(root / "app" / "data" / "fc_forward_capture.db") not in fc.argv
        # Interpreter + script paths stay where the code lives.
        assert fc.argv[0] == str(root / PY)
        assert fc.argv[1] == str(root / "scripts" / "run_fc_forward_capture.py")

    def test_no_live_app_data_path_survives_in_any_step(self, tmp_path):
        chain = _chain()
        root = Path("/scratch/rooted")
        override = tmp_path / "rehearsal"
        steps = chain.apply_runtime_override(
            chain.build_steps(root), repo_root=root, override_dir=override
        )
        live_data = str(root / "app" / "data")
        for step in steps:
            for arg in step.argv[2:]:
                assert not arg.startswith(live_data), (step.name, arg)

    def test_feature_refresh_gains_runtime_dir_pointing_at_the_override(self, tmp_path):
        chain = _chain()
        root = Path("/scratch/rooted")
        override = tmp_path / "rehearsal"
        steps = chain.apply_runtime_override(
            chain.build_steps(root), repo_root=root, override_dir=override
        )
        fr = next(s for s in steps if s.name == "run_feature_refresh")
        assert fr.argv[-2:] == ("--runtime-dir", str(override))

    def test_what_changed_runs_preflight_because_it_cannot_be_redirected(self, tmp_path):
        chain = _chain()
        root = Path("/scratch/rooted")
        override = tmp_path / "rehearsal"
        steps = chain.apply_runtime_override(
            chain.build_steps(root), repo_root=root, override_dir=override
        )
        wc = next(s for s in steps if s.name == "run_what_changed_report")
        assert wc.argv[-1] == "--preflight"


class TestCli:
    """Spec verification block: bare --dry-run prints the plan and touches
    nothing; --dry-run=false executes; --steps-from loads a scratch table."""

    def _write_stub_table(self, tmp_path, fail=()):
        rows = []
        for name in ("s1", "s2", "s3"):
            code = 1 if name in fail else 0
            rows.append(
                {
                    "name": name,
                    "argv": [sys.executable, "-c", f"raise SystemExit({code})"],
                    "hard_upstreams": ["s1"] if name == "s3" else [],
                    "target": [9, 0],
                }
            )
        table = tmp_path / "steps.json"
        table.write_text(json.dumps(rows), encoding="utf-8")
        return table

    def test_dry_run_is_the_default_and_touches_nothing(self, tmp_path, capsys):
        chain = _chain()
        rc = chain.main(["--repo-root", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        for name in EXPECTED_ORDER:
            assert name in out
        assert "run_fc_forward_capture" in out
        # The market line names its hard upstream so the graph is readable.
        assert "run_market_divergence_refresh" in out
        assert not (tmp_path / "app" / "data" / "ops").exists()

    def test_dry_run_false_executes_the_scratch_table(self, tmp_path):
        chain = _chain()
        table = self._write_stub_table(tmp_path)
        report_path = tmp_path / "report.json"
        rc = chain.main(
            [
                "--dry-run=false",
                "--steps-from",
                str(table),
                "--report-path",
                str(report_path),
                "--repo-root",
                str(tmp_path),
            ]
        )
        assert rc == 0
        report = _report(report_path)
        assert [s["status"] for s in report["steps"]] == ["ok", "ok", "ok"]

    def test_spec_fail_soft_proof_through_the_cli(self, tmp_path):
        chain = _chain()
        table = self._write_stub_table(tmp_path, fail=("s2",))
        report_path = tmp_path / "report.json"
        rc = chain.main(
            [
                "--dry-run=false",
                "--steps-from",
                str(table),
                "--report-path",
                str(report_path),
                "--repo-root",
                str(tmp_path),
            ]
        )
        assert rc != 0
        by_name = {s["name"]: s for s in _report(report_path)["steps"]}
        assert by_name["s2"]["status"] == "failed"
        assert by_name["s1"]["status"] == "ok"
        assert by_name["s3"]["status"] == "ok"

    def test_spec_hard_edge_proof_through_the_cli(self, tmp_path):
        chain = _chain()
        table = self._write_stub_table(tmp_path, fail=("s1",))
        report_path = tmp_path / "report.json"
        rc = chain.main(
            [
                "--dry-run=false",
                "--steps-from",
                str(table),
                "--report-path",
                str(report_path),
                "--repo-root",
                str(tmp_path),
            ]
        )
        assert rc != 0
        by_name = {s["name"]: s for s in _report(report_path)["steps"]}
        assert by_name["s1"]["status"] == "failed"
        assert by_name["s3"]["status"] == "skipped_upstream_failed"
        assert by_name["s3"]["exit_code"] is None
        assert by_name["s2"]["status"] == "ok"

    def test_runtime_override_redirects_the_default_report_too(self, tmp_path):
        chain = _chain()
        table = self._write_stub_table(tmp_path)
        override = tmp_path / "rehearsal"
        rc = chain.main(
            [
                "--dry-run=false",
                "--steps-from",
                str(table),
                "--runtime-override",
                str(override),
                "--repo-root",
                str(tmp_path),
            ]
        )
        assert rc == 0
        assert (override / "daily_chain_latest_report.json").is_file()
        assert not (tmp_path / "app" / "data" / "ops").exists()


class TestSpawnFailure:
    """Fail-soft must survive the failure BEFORE the exit code: a step whose
    binary cannot spawn (OSError, not a return code) is 'failed', and the
    steps after it still run. Without this, one bad path aborts the morning."""

    def test_unspawnable_step_is_failed_and_later_steps_still_run(self, tmp_path):
        chain = _chain()
        broken = chain.ChainStep(
            name="s2",
            argv=(str(tmp_path / "no" / "such" / "binary"),),
            hard_upstreams=(),
            target=(9, 0),
        )
        steps = (_stub("s1"), broken, _stub("s3"))
        report_path = tmp_path / "chain.json"
        exit_code = chain.execute_chain(steps, report_path=report_path)
        assert exit_code != 0
        by_name = {s["name"]: s for s in _report(report_path)["steps"]}
        assert by_name["s2"]["status"] == "failed"
        assert by_name["s1"]["status"] == "ok"
        assert by_name["s3"]["status"] == "ok"

    def test_unspawnable_step_is_loud_in_the_alert(self, tmp_path):
        chain = _chain()
        broken = chain.ChainStep(
            name="s2",
            argv=(str(tmp_path / "no" / "such" / "binary"),),
            hard_upstreams=(),
            target=(9, 0),
        )
        report_path = tmp_path / "chain.json"
        chain.execute_chain((broken,), report_path=report_path)
        name = "run_capture_gap_alert"
        if name in sys.modules:
            alert = sys.modules[name]
        else:
            path = REPO_ROOT / "scripts" / "run_capture_gap_alert.py"
            spec = importlib.util.spec_from_file_location(name, path)
            alert = importlib.util.module_from_spec(spec)
            sys.modules[name] = alert
            spec.loader.exec_module(alert)
        lines = alert.chain_report_lines(report_path)
        assert len(lines) == 1 and "s2" in lines[0]
