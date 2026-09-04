"""DG-018 runner — grade the frozen model predictions against the market, weekly.

The realized-outcome loop answers "is the model any good against reality". This answers the
question DG-018 was actually filed for: **does the model beat free consensus pricing?** It
reuses that loop's governed pieces rather than inventing parallel ones — the SAME declared
frozen prediction set (David's own declaration, never inferred), the SAME week-finality law,
and the SAME realized outcomes — and adds only the market side and the paired comparison.

It writes one artifact and nothing else. No git, no producer, no network beyond the loaders.
Every terminal state is named: an unfinished week is a no-op that writes NO scorecard, and a
missing market snapshot is a LOUD failure, because grading the model against an empty market
would report a win by construction.

Run it after a week finalises:

    .venv/bin/python3.14 scripts/run_model_vs_market_scoring.py \
        --report-path app/data/model_capture/model_vs_market_latest.json

Outcomes are rebuilt from finalised weeks on every run, so a first run in week 6 grades
weeks 1 through 6. Nothing perishes by not running earlier.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.outcome_loop.model_vs_market_scorer import (  # noqa: E402
    score_model_vs_market,
)

MARKET_SNAPSHOT_DB = ROOT / "app" / "data" / "fc_snapshots.db"
DEFAULT_REPORT = ROOT / "app" / "data" / "model_capture" / "model_vs_market_latest.json"


def run(
    season: int,
    week: int,
    report_path: Path | str,
    *,
    prediction_loader: Callable[[int], dict[str, Any]],
    market_loader: Callable[[str], list[dict[str, Any]]],
    outcome_loader: Callable[[int, int, list[dict[str, Any]]], dict[str, Any]],
    week_finalized: Callable[[int, int], bool],
) -> dict[str, Any]:
    """Score one week. Pure control flow; every input is injected so this is testable."""
    report_path = Path(report_path)

    def _noop(reason: str) -> dict[str, Any]:
        # Deliberately writes NOTHING. A scorecard on disk means a grade happened.
        return {
            "status": "noop",
            "noop_reason": reason,
            "season": season,
            "week": week,
            "decision_supported": False,
        }

    def _failed(reason: str) -> dict[str, Any]:
        return {
            "status": "failed",
            "failure_reason": reason,
            "season": season,
            "week": week,
            "decision_supported": False,
        }

    if not week_finalized(season, week):
        return _noop("week_not_finalized")

    declaration = prediction_loader(season)
    predictions = list(declaration.get("rows") or [])
    if not predictions:
        return _failed("no_frozen_predictions")

    frozen_date = str(declaration.get("frozen_capture_date") or "")
    market = list(market_loader(frozen_date))
    if not market:
        # Grading against an empty market would hand back a win by construction.
        return _failed("no_market_snapshot_for_frozen_date")

    # The loader receives the predictions because outcomes are gsis-keyed and only the
    # predictions carry the sleeper ids that resolve to them: the identity bridge maps
    # sleeper -> gsis and has NO reverse lookup.
    outcome_payload = outcome_loader(season, week, predictions)
    outcomes = outcome_payload.get("outcomes") or {}
    finalized_weeks = list(outcome_payload.get("finalized_weeks") or [])
    if not finalized_weeks:
        return _noop("no_finalized_weeks")
    if not outcomes:
        # Weeks HAVE finalised and nothing resolved. That is breakage, not an off-season,
        # and reporting it as a quiet no-op would look healthy every week of the season.
        return _failed("no_outcomes_for_finalized_weeks")

    card = score_model_vs_market(
        model_predictions=predictions, market_snapshot=market, outcomes=outcomes
    )
    result = {
        "status": "ok",
        "season": season,
        "week": week,
        "finalized_weeks": finalized_weeks,
        "frozen_capture_date": frozen_date,
        "declared_by": declaration.get("declared_by"),
        "market_source": "fc_snapshots",
        "market_snapshot_date": frozen_date,
        "market_rows": len(market),
        "model_rows": len(predictions),
        **card,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


# ── production loaders ───────────────────────────────────────────────────────────────


def _default_prediction_loader(season: int) -> dict[str, Any]:
    """The DECLARED frozen set, read through the realized loop's own governed reader.

    Reusing that loader is deliberate: the frozen capture is David's declaration
    (2026-08-13, "the frozen set is 2026-08-05"), and a second hand-rolled reader here
    could silently disagree with the one the realized-outcome scorecard uses.
    """
    from scripts.run_realized_outcome_scoring import (
        _default_prediction_loader as governed_loader,
    )
    from scripts.run_realized_outcome_scoring import (
        _load_frozen_declaration,
    )

    entry = _load_frozen_declaration(season)
    envelope = governed_loader(season, 1)
    return {
        "rows": envelope["rows"],
        "coverage": envelope.get("coverage", {}),
        "frozen_capture_date": entry["frozen_capture_date"],
        "declared_by": entry["declared_by"],
    }


def _default_market_loader(snapshot_date: str) -> list[dict[str, Any]]:
    """The market's own prices on the frozen capture date, read-only.

    ``value`` is FantasyCalc's dynasty value, higher is better; the pull is
    numQbs=2 numTeams=12 ppr=1, which matches this league.
    """
    if not MARKET_SNAPSHOT_DB.exists():
        return []
    with sqlite3.connect(f"file:{MARKET_SNAPSHOT_DB}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT sleeper_id, position, value FROM fc_snapshots WHERE snapshot_date = ?",
            (snapshot_date,),
        ).fetchall()
    return [
        {
            "sleeper_id": str(row["sleeper_id"]),
            "position": row["position"],
            "value": row["value"],
        }
        for row in rows
        if row["sleeper_id"] is not None
    ]


def _default_outcome_loader(
    season: int, week: int, predictions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Realized points per game to date, rebuilt from every finalised week.

    Delegates to the realized-outcome loop's own builders so both scorecards grade against
    identical outcomes. The bridge resolves sleeper -> gsis FORWARD only, so the mapping is
    driven from the predictions rather than from the outcome keys.
    """
    from scripts.run_realized_outcome_scoring import (
        _build_outcomes,
        _default_identity_snapshot_loader,
        _default_schedule_loader,
        _default_stat_loader,
        _default_util_loader,
    )
    from src.dynasty_genius.identity.outcome_identity_bridge import (
        OutcomeIdentityBridge,
    )

    built = _build_outcomes(
        season,
        week,
        schedule_loader=_default_schedule_loader,
        stat_loader=_default_stat_loader,
        util_loader=_default_util_loader,
    )
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        _default_identity_snapshot_loader(season, week)
    )
    players = built.get("players") or {}
    by_sleeper: dict[str, dict[str, Any]] = {}
    unresolved = 0
    for prediction in predictions:
        sleeper = prediction.get("sleeper_id")
        resolution = bridge.resolve(sleeper, prediction.get("capture_date"))
        gsis = getattr(resolution, "gsis_id", None) or (
            resolution.get("gsis_id") if isinstance(resolution, dict) else None
        )
        status = getattr(resolution, "resolution_status", None) or (
            resolution.get("resolution_status") if isinstance(resolution, dict) else None
        )
        if status != "resolved" or not gsis:
            unresolved += 1
            continue
        entry = players.get(str(gsis))
        if entry is None:
            continue
        outcome = entry.get("outcome") or {}
        by_sleeper[str(sleeper)] = {
            "ppg": outcome.get("ppg_to_date"),
            "games_played": outcome.get("games_played"),
        }
    return {
        "outcomes": by_sleeper,
        "finalized_weeks": built_finalized_weeks(built, week),
        "identity_unresolved_n": unresolved,
    }


def built_finalized_weeks(built: dict[str, Any], week: int) -> list[int]:
    """Which weeks actually contributed outcomes. ``_build_outcomes`` skips unfinalised
    weeks silently, so this must not assume 1..week were all played."""
    weeks: set[int] = set()
    for entry in (built.get("players") or {}).values():
        for fact in entry.get("weekly_util") or []:
            value = fact.get("week")
            if isinstance(value, int):
                weeks.add(value)
    return sorted(weeks)


def _default_week_finalized(season: int, week: int) -> bool:
    from scripts.run_realized_outcome_scoring import _default_schedule_loader
    from src.dynasty_genius.eval.week_finality import week_status

    schedule = _default_schedule_loader(season, week)
    return week_status(season, week, schedule=schedule) == "finalized"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)

    result = run(
        args.season,
        args.week,
        args.report_path,
        prediction_loader=_default_prediction_loader,
        market_loader=_default_market_loader,
        outcome_loader=_default_outcome_loader,
        week_finalized=_default_week_finalized,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in ("ok", "noop") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
