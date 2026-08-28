"""DG-083 RED (SR-10a step 3): the schedule-drift block on capture health.

Written before the drift field existed. A capture that lands hours after its
slot is present-but-degraded, and until now the surface reported it as simply
present: SR-09's chain report records target-vs-actual per step
(``daily_chain_latest_report.json`` — ``started_at`` + ``target``), and this
surfaces that number per store against the store's OWN ``scheduled_time_local``.
The market store keeps its 09:40 target while the chain runs the 09:00 slot
precisely so the difference stays visible (spec:993 — moving the target would
hide the drift).

Deliberately DESCRIPTIVE ONLY: ``store_status`` and the SR-11 alert lines do
not move on drift — the same no-warn-behavior-change-days-before-kickoff
reasoning as the landed season-window comment (SR-10a step 2). A store or
surface without the wiring says why in ``basis``; a number is never fabricated.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "app" / "config" / "capture_cadence.json"

TZ = "America/New_York"
REPORT_RELPATH = Path("app/data/ops/daily_chain_latest_report.json")


def _models():
    from app.api.routes import system_capture_health_models as models

    return models


def _route_module():
    from app.api.routes import system_capture_health

    return system_capture_health


def _run_daily_chain_module():
    """Load scripts/run_daily_chain.py as a module (scripts/ is no package)."""

    import sys

    name = "run_daily_chain_dg083"
    if name in sys.modules:
        return sys.modules[name]
    path = REPO_ROOT / "scripts" / "run_daily_chain.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _market_store(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    store: dict[str, Any] = {
        "store_id": "market_divergence_history",
        "db_path": "app/data/market_divergence_history.db",
        "table": "market_divergence_history",
        "date_column": "capture_date",
        "source_filter": None,
        "expected_settings_hash": None,
        "capture_start_date": "2026-08-25",
        "expected_cadence": "daily",
        "scheduled_time_local": "09:40",
        "grace_hours": 3,
        "density_floor_pct": 50,
        "density_baseline_window": 14,
        "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
        "window_risk_contiguous_days": 7,
        "companion_tables": [],
        "chain_step": "run_market_divergence_refresh",
    }
    if overrides:
        store.update(overrides)
    return store


def _config_body(stores: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "config_version": 1,
        "timezone": TZ,
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        "stores": stores,
    }


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _step(
    name: str = "run_market_divergence_refresh",
    status: str = "ok",
    started_at: str = "2026-08-27T09:41:00-04:00",
) -> dict[str, Any]:
    return {
        "name": name,
        "exit_code": 0 if status == "ok" else None,
        "status": status,
        "started_at": started_at,
        "duration_s": 8.0,
        "target": "09:40",
    }


def _report(steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": 1,
        "chain": {
            "target_start": "09:00",
            "started_at": "2026-08-27T09:00:04-04:00",
            "finished_at": "2026-08-27T09:05:00-04:00",
            "drift_minutes": 0,
            "exit_code": 0,
        },
        "steps": steps,
    }


def _store_config(overrides: dict[str, Any] | None = None):
    models = _models()
    return models.CadenceStoreConfig.model_validate(_market_store(overrides))


def _evaluate(
    steps: list[dict[str, Any]],
    *,
    store_overrides: dict[str, Any] | None = None,
    report: dict[str, Any] | None = None,
):
    models = _models()
    return models.evaluate_schedule_drift(
        store_config=_store_config(store_overrides),
        chain_report=report if report is not None else _report(steps),
        timezone=TZ,
    )


class TestChainStepConfigField:
    """``chain_step`` is optional, additive, and fail-closed on garbage."""

    def _load(self, tmp_path: Path, stores: list[dict[str, Any]]):
        models = _models()
        config_path = _write_json(tmp_path / "cadence.json", _config_body(stores))
        return models.load_capture_cadence(config_path=config_path)

    def test_chain_step_is_optional_and_defaults_to_none(self, tmp_path: Path) -> None:
        store = _market_store()
        del store["chain_step"]
        config = self._load(tmp_path, [store])
        assert config.stores[0].chain_step is None

    def test_chain_step_round_trips_through_the_loader(self, tmp_path: Path) -> None:
        config = self._load(tmp_path, [_market_store()])
        assert config.stores[0].chain_step == "run_market_divergence_refresh"

    @pytest.mark.parametrize(
        "bad", ["", "rm -rf /", "Run-Chain", "run chain", "run;chain", "9lives"]
    )
    def test_malformed_chain_step_fails_closed(self, tmp_path: Path, bad: str) -> None:
        models = _models()
        with pytest.raises(models.CaptureHealthConfigError):
            self._load(tmp_path, [_market_store({"chain_step": bad})])


class TestEvaluateScheduleDrift:
    """Pure evaluation of one store's drift from a parsed chain report."""

    def test_on_time_run_reports_small_drift(self) -> None:
        drift = _evaluate([_step(started_at="2026-08-27T09:41:00-04:00")])
        assert drift.basis == "chain_report"
        assert drift.chain_step == "run_market_divergence_refresh"
        assert drift.target_local == "09:40"
        assert drift.recorded_start == "2026-08-27T09:41:00-04:00"
        assert drift.drift_minutes == 1
        assert drift.exceeds_grace is False

    def test_spec_1142_case_surfaces_the_number(self) -> None:
        # The spec's own example: a capture that landed 11:42 for a 09:40 slot.
        # The NUMBER reaches the surface; the boolean stays the config's own
        # grace judgment (122 min is inside this store's 3h grace window).
        drift = _evaluate([_step(started_at="2026-08-27T11:42:00-04:00")])
        assert drift.drift_minutes == 122
        assert drift.exceeds_grace is False

    def test_late_past_grace_sets_exceeds_grace(self) -> None:
        drift = _evaluate([_step(started_at="2026-08-27T13:05:00-04:00")])
        assert drift.drift_minutes == 205
        assert drift.exceeds_grace is True

    def test_early_chain_slot_is_negative_never_degraded(self) -> None:
        # SR-09 runs the whole chain at 09:00 while the store's target stays
        # 09:40 — routine negative drift, visible and never judged late.
        drift = _evaluate([_step(started_at="2026-08-27T09:05:00-04:00")])
        assert drift.drift_minutes == -35
        assert drift.exceeds_grace is False

    def test_past_midnight_catchup_mirrors_the_chain_runners_rule(self) -> None:
        # run_daily_chain.py:198 — a start hours "early" is a catch-up chasing
        # YESTERDAY's target. Same floor (-120), same re-anchoring, so SR-09's
        # recorded number and this surface can never disagree about one run.
        drift = _evaluate([_step(started_at="2026-08-28T00:10:00-04:00")])
        assert drift.drift_minutes == 870
        assert drift.exceeds_grace is True

    def test_failed_step_yields_no_number(self) -> None:
        drift = _evaluate([_step(status="failed")])
        assert drift.basis == "chain_step_not_ok:failed"
        assert drift.drift_minutes is None
        assert drift.recorded_start is None
        assert drift.exceeds_grace is None

    def test_skipped_step_yields_no_number(self) -> None:
        drift = _evaluate([_step(status="skipped_upstream_failed")])
        assert drift.basis == "chain_step_not_ok:skipped_upstream_failed"
        assert drift.drift_minutes is None

    def test_step_absent_from_report_names_itself(self) -> None:
        drift = _evaluate([_step(name="run_fc_forward_capture")])
        assert drift.basis == "chain_step_not_in_report"
        assert drift.drift_minutes is None

    def test_report_without_steps_list_is_unreadable(self) -> None:
        drift = _evaluate([], report={"schema": 1})
        assert drift.basis == "chain_report_unreadable"
        assert drift.drift_minutes is None

    def test_naive_started_at_refuses_to_guess_a_zone(self) -> None:
        # The chain runner always stamps an offset (datetime.now().astimezone());
        # a naive stamp is outside the report's contract — no guessed zones.
        drift = _evaluate([_step(started_at="2026-08-27T09:41:00")])
        assert drift.basis == "chain_report_unreadable"
        assert drift.drift_minutes is None


class TestInspectWiring:
    """inspect_capture_store attaches the drift block on EVERY path."""

    NOW = datetime(2026, 8, 27, 13, 30, tzinfo=ZoneInfo(TZ))

    def _inspect(
        self,
        tmp_path: Path,
        *,
        store_overrides: dict[str, Any] | None = None,
        report_text: str | None = None,
        report_body: dict[str, Any] | None = None,
        pass_report_path: bool = True,
        create_db: bool = False,
    ):
        models = _models()
        repo_root = tmp_path
        report_path = repo_root / REPORT_RELPATH
        if report_body is not None:
            _write_json(report_path, report_body)
        elif report_text is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text, encoding="utf-8")
        if create_db:
            _create_market_db(repo_root, ["2026-08-25", "2026-08-26", "2026-08-27"])
        kwargs: dict[str, Any] = {}
        if pass_report_path:
            kwargs["chain_report_path"] = report_path
        return models.inspect_capture_store(
            store_config=_store_config(store_overrides),
            repo_root=repo_root,
            now=self.NOW,
            timezone=TZ,
            season_windows=_models().SeasonWindows(in_season_months=[9, 10, 11, 12, 1]),
            **kwargs,
        )

    def test_absent_report_names_itself(self, tmp_path: Path) -> None:
        health = self._inspect(tmp_path)
        assert health.schedule_drift.basis == "chain_report_absent"
        assert health.schedule_drift.drift_minutes is None

    def test_malformed_report_json_names_itself(self, tmp_path: Path) -> None:
        health = self._inspect(tmp_path, report_text="{not json")
        assert health.schedule_drift.basis == "chain_report_unreadable"

    def test_store_without_chain_step_says_so(self, tmp_path: Path) -> None:
        health = self._inspect(
            tmp_path,
            store_overrides={"chain_step": None},
            report_body=_report([_step()]),
        )
        assert health.schedule_drift.basis == "no_chain_step_configured"
        assert health.schedule_drift.drift_minutes is None

    def test_drift_rides_the_absent_store_path(self, tmp_path: Path) -> None:
        # An absent db must not blank the drift block: the report still knows
        # when (and whether) the producing step ran.
        health = self._inspect(tmp_path, report_body=_report([_step()]))
        assert health.store_presence == "absent"
        assert health.schedule_drift.basis == "chain_report"
        assert health.schedule_drift.drift_minutes == 1

    def test_default_callers_get_not_evaluated(self, tmp_path: Path) -> None:
        # The gap alert / system_health / tier_readiness call sites pass no
        # report path and must keep working, honestly labeled.
        health = self._inspect(tmp_path, pass_report_path=False)
        assert health.schedule_drift.basis == "not_evaluated"
        assert health.schedule_drift.drift_minutes is None

    def test_drift_never_flips_store_status(self, tmp_path: Path) -> None:
        # DESCRIPTIVE ONLY, pinned: a healthy store whose capture ran late
        # past grace stays ok — no new caveat, no status flip, no new SR-11
        # alert line (the no-behavior-change-before-kickoff ruling).
        health = self._inspect(
            tmp_path,
            create_db=True,
            report_body=_report([_step(started_at="2026-08-27T13:05:00-04:00")]),
        )
        assert health.schedule_drift.exceeds_grace is True
        assert health.store_status == "ok"
        assert health.caveats == []


def _create_market_db(repo_root: Path, dates: list[str]) -> Path:
    db_path = repo_root / "app/data/market_divergence_history.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE market_divergence_history (
                player_id TEXT,
                capture_date TEXT,
                decision_supported INTEGER,
                payload_json TEXT,
                PRIMARY KEY (player_id, capture_date)
            )
            """
        )
        for day in dates:
            conn.executemany(
                "INSERT INTO market_divergence_history VALUES (?, ?, 0, '{}')",
                [(f"p{i}", day) for i in range(3)],
            )
    return db_path


class TestRouteWiring:
    """The T4 route reads the chain report and serves the block per store."""

    def _client(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, now: datetime
    ) -> TestClient:
        route = _route_module()
        config_path = _write_json(
            tmp_path / "cadence.json", _config_body([_market_store()])
        )
        monkeypatch.setattr(route, "_CONFIG_PATH", config_path)
        monkeypatch.setattr(route, "_REPO_ROOT", tmp_path)
        monkeypatch.setattr(route, "_CLOCK", lambda: now)
        from app.main import app

        return TestClient(app)

    def test_route_serves_the_drift_block(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _write_json(
            tmp_path / REPORT_RELPATH,
            _report([_step(started_at="2026-08-27T11:42:00-04:00")]),
        )
        client = self._client(
            monkeypatch, tmp_path, datetime(2026, 8, 27, 13, 30, tzinfo=ZoneInfo(TZ))
        )
        body = client.get("/api/system/capture-health").json()
        (store,) = body["stores"]
        assert store["schedule_drift"] == {
            "target_local": "09:40",
            "chain_step": "run_market_divergence_refresh",
            "recorded_start": "2026-08-27T11:42:00-04:00",
            "drift_minutes": 122,
            "exceeds_grace": False,
            "basis": "chain_report",
        }

    def test_route_report_path_matches_the_chain_writers_contract(self) -> None:
        # The same cross-contract that holds the gap alert to the chain writer:
        # the route must read exactly where run_daily_chain.py writes.
        route = _route_module()
        chain = _run_daily_chain_module()
        assert (
            route._REPO_ROOT / route._CHAIN_REPORT_RELPATH
            == chain.default_report_path(route._REPO_ROOT)
        )


class TestRealConfigWiring:
    """The repo's own config carries the wiring this ticket registers."""

    def _real_config(self) -> dict[str, Any]:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_all_three_stores_are_wired_to_their_chain_steps(self) -> None:
        stores = {s["store_id"]: s.get("chain_step") for s in self._real_config()["stores"]}
        assert stores == {
            "fc_forward_capture": "run_fc_forward_capture",
            # run_pvo_refresh carries --capture-db-path model_forward_capture.db:
            # the pvo step IS the model capture's producer in the chain.
            "model_forward_capture": "run_pvo_refresh",
            "market_divergence_history": "run_market_divergence_refresh",
        }

    def test_config_version_is_bumped(self) -> None:
        assert self._real_config()["config_version"] >= 3

    def test_chain_steps_name_real_steps_in_the_chain_table(self) -> None:
        # A renamed chain step must not silently orphan the drift wiring.
        chain = _run_daily_chain_module()
        step_names = {step.name for step in chain.build_steps(REPO_ROOT)}
        configured = {
            s["chain_step"]
            for s in self._real_config()["stores"]
            if s.get("chain_step")
        }
        assert configured <= step_names

    def test_fail_closed_loader_accepts_the_real_config(self) -> None:
        models = _models()
        config = models.load_capture_cadence(config_path=CONFIG_PATH)
        assert all(s.chain_step for s in config.stores)
