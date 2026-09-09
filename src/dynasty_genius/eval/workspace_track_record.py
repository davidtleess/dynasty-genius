"""DG-207 — the two track-record graders.

Two questions that are not the same question, kept apart on purpose:

* **Production** grades an archived football forecast against realized points, under the
  ORIGINAL frozen declaration ``workspace-production-2026-v1``. Nothing here amends it.
* **Market** tests one ORDINAL hypothesis under the separate registration
  ``workspace-market-movement-90d-v1``: do players we rank above FantasyCalc subsequently
  rise more in relative price? We never forecast a price, so ``error`` is null on every
  market row and no result here is a price forecast, a trade return or a decision edge.

Four rules are load-bearing:

1. **A missing value is missing.** A verified nonparticipation zero and an unknown are
   different facts and never merge. An absent end price is not a loss.
2. **A degenerate statistic is undefined, not zero.** If every adjusted movement is equal,
   the outcome has no variance and the correlation does not exist. Printing 0.0 there would
   claim we measured no relationship when nothing was measurable.
3. **The denominator ships with the number.** Every comparison carries its own eligible and
   scored counts, and producers are never pooled into one flattering average.
4. **Refuse before computing.** A target or configuration mismatch, a duplicate id or an
   incomplete window stops the run; it never degrades into a partial grade.

Pure functions: every input is injected, there is no I/O, no store read and no wall clock.
``decision_supported`` is False on every document this module produces.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional

import numpy as np

GRADE_SCHEMA = "track_record.grade.v1"
OUTCOME_SCHEMA = "track_record.outcome_source.v1"
ENDPOINT_SCHEMA = "track_record.endpoint_source.v1"

PRODUCTION_SEED = 189
MARKET_SEED = 205
RESAMPLES = 10_000
MIN_VALID_RESAMPLES = 9_500
MIN_POSITION_COHORT = 10
ALLOWED_HORIZONS = (30, 90)
CAPTURE_WINDOW_DAYS = 3
BASELINES = ("prior_season", "position_median")
# States in which the enrolled market stream was never a live prospective registration.
MARKET_INELIGIBLE_STATES = ("not_registered", "input_unavailable", "cutoff_ineligible",
                            "ineligible")


class TrackRecordError(ValueError):
    """A refusal. Raised before any metric is computed, never after seeing a result."""


# --------------------------------------------------------------------------- small helpers
def _finite(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _instant(value: Any, what: str) -> float:
    """ISO-8601 Zulu to epoch seconds. No wall clock is ever read."""
    if not isinstance(value, str) or not value:
        raise TrackRecordError(f"{what} must be an ISO-8601 instant")
    text = value.replace("Z", "+00:00")
    try:
        from datetime import datetime

        moment = datetime.fromisoformat(text)
    except ValueError as error:
        raise TrackRecordError(f"{what} is not a valid instant: {value}") from error
    # A naive stamp is REFUSED, never assumed to be UTC. `.timestamp()` on a naive datetime
    # silently reads the machine's local zone, so identical bytes would grade differently on two
    # machines while the CLI's own normaliser assumed UTC -- two readings of one field.
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise TrackRecordError(
            f"{what} carries no timezone offset; an instant without a zone is not an instant"
        )
    return moment.timestamp()


def _count(value: Any, what: str) -> int:
    """A strict non-negative count. Bools and floats are refused rather than coerced.

    ``int(True)`` is 1 and ``int(2.9)`` is 2, so a malformed count used to pass a coverage gate
    by silently becoming a plausible number.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TrackRecordError(f"{what} must be a non-negative integer, not {value!r}")
    return value


# A serialization of the prepared numbers is a restatement of the answer, not an observation of
# the world. It carries no capture time and can never witness completeness or chronology.
PREPARED_ROLE = "prepared_serialization"


def _actual_captures(source: dict) -> list[dict]:
    return [entry for entry in (source.get("sources") or [])
            if isinstance(entry, dict) and entry.get("role") != PREPARED_ROLE]


def _capture_chronology(source: dict, *, evaluated_at: str, closed_at: Optional[str],
                        what: str) -> Optional[str]:
    """None when the ACTUAL capture times are coherent, otherwise the reason they are not.

    Only real captures are considered. Letting a helper timestamp stand in for an observation is
    how a source captured mid-season graded a full season: the runner's own prepared entry was
    stamped at the window end and satisfied the check the raw bytes failed.
    """
    captures = _actual_captures(source)
    if not captures:
        return f"the {what} names no actual capture, so chronology is unprovable"
    stamps: list[float] = []
    for entry in captures:
        value = entry.get("captured_at")
        if not value:
            return f"an actual {what} capture declares no capture time"
        stamps.append(_instant(value, "source captured_at"))
    if max(stamps) > _instant(evaluated_at, "evaluated_at"):
        return (f"an actual {what} capture is stamped after the evaluation instant, so it was not "
                "knowable when this run was made")
    if closed_at is not None and max(stamps) < _instant(closed_at, "window close"):
        return f"every actual {what} capture predates the close of the window it describes"
    return None


def _measurement_identity(target: Any) -> Any:
    """The measurement, without the vintage. `labels_through` is a revision marker, not identity."""
    if not isinstance(target, dict):
        return target
    return {k: v for k, v in target.items() if k != "labels_through"}


def _unique(rows: Iterable[dict], what: str) -> list[dict]:
    listed = list(rows)
    seen: set[str] = set()
    for row in listed:
        player = row.get("sleeper_id")
        if not isinstance(player, str) or not player:
            raise TrackRecordError(f"{what} row is missing a player identity")
        if player in seen:
            raise TrackRecordError(f"{what} duplicate player identity: {player}")
        seen.add(player)
    return listed


def _midpoint(interval: Any) -> Optional[float]:
    """A tie is a span, and its position is its middle. Order inside it is never a prediction."""
    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
        return None
    low, high = _finite(interval[0]), _finite(interval[1])
    if low is None or high is None or high < low:
        return None
    return (low + high) / 2.0


def _ranks(values: np.ndarray) -> np.ndarray:
    """Midranks, so tied values share a rank rather than being ordered arbitrarily."""
    order = np.argsort(values, kind="mergesort")
    ranked = np.empty(len(values), dtype=float)
    ranked[order] = np.arange(1, len(values) + 1, dtype=float)
    sorted_values = values[order]
    start = 0
    for index in range(1, len(values) + 1):
        if index == len(values) or sorted_values[index] != sorted_values[start]:
            if index - start > 1:
                ranked[order[start:index]] = ranked[order[start:index]].mean()
            start = index
    return ranked


def _spearman(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    """None when either side is constant: the correlation does not exist, it is not zero."""
    if len(x) < 2:
        return None
    rx, ry = _ranks(x), _ranks(y)
    if rx.std() == 0.0 or ry.std() == 0.0:
        return None
    value = float(np.corrcoef(rx, ry)[0, 1])
    return value if np.isfinite(value) else None


def _percentile_interval(samples: list[float]) -> Optional[list[float]]:
    if len(samples) < MIN_VALID_RESAMPLES:
        return None
    array = np.asarray(samples, dtype=float)
    return [float(np.percentile(array, 2.5)), float(np.percentile(array, 97.5))]


def _state_for(estimate: Optional[float], interval: Optional[list[float]],
               favorable_when: str) -> str:
    """The two claims point opposite ways and must not share a rule.

    Production's metric is forecast MAE minus baseline MAE, so **lower is better** and the
    declaration says the forecast beat a baseline only when the interval lies entirely BELOW
    zero. The market metric is a correlation, where **higher is better** and a favorable
    association needs the interval entirely ABOVE zero. Collapsing these into one direction
    would report a three-point error reduction as a loss.
    """
    if estimate is None or interval is None:
        return "insufficient"
    if favorable_when == "below_zero":
        if interval[1] < 0.0:
            return "favorable"
        if interval[0] > 0.0:
            return "unfavorable"
        return "inconclusive"
    if interval[0] > 0.0:
        return "favorable"
    if interval[1] < 0.0:
        return "unfavorable"
    return "inconclusive"


def _comparison(*, identity: str, label: str, units: str, estimate: Optional[float],
                interval: Optional[list[float]], note: str, eligible: int, scored: int,
                state: Optional[str] = None,
                favorable_when: str = "above_zero") -> dict[str, Any]:
    return {
        "id": identity,
        "label": label,
        "units": units,
        "estimate": estimate,
        "interval95": interval,
        "state": state if state is not None else _state_for(estimate, interval, favorable_when),
        "note": note,
        "eligible": int(eligible),
        "scored": int(scored),
    }


def _envelope(*, enrollment: dict, claim: str, state: str, reason: Optional[str],
              window: Any, provenance_class: Any, policy_sha256: Any,
              input_hashes: dict[str, str], evaluated_at: str,
              counts: dict[str, int], result: Optional[dict],
              horizon_days: Optional[int], outcome_source_hashes: dict[str, str]) -> dict[str, Any]:
    # A graded state must be able to name the exact outcome bytes it consumed. Keeping them in
    # their own field as well as in input_hashes means a later reader can tell which hashes came
    # from the enrollment and which came from the outcome feed, instead of guessing from a merge.
    if state == "graded" and not outcome_source_hashes:
        raise TrackRecordError("a graded result must carry its outcome source hashes")
    return {
        "schema_version": GRADE_SCHEMA,
        "snapshot_id": enrollment.get("snapshot_id"),
        "enrollment_id": enrollment.get("record_id"),
        "claim": claim,
        "evaluated_at": evaluated_at,
        "policy_sha256": policy_sha256,
        "input_hashes": input_hashes,
        "decision_supported": False,
        "horizon_days": horizon_days,
        "outcome_source_hashes": outcome_source_hashes,
        "state": state,
        "reason": reason,
        "window": window,
        "provenance_class": provenance_class,
        "counts": {k: int(v) for k, v in counts.items()},
        "result": result,
    }


def _source_hashes(source: dict, existing: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Returns (all enrollment + outcome hashes, outcome-only hashes)."""
    outcome: dict[str, str] = {}
    for entry in source.get("sources") or []:
        name, digest = entry.get("name"), entry.get("sha256")
        if not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64:
            raise TrackRecordError("every outcome source entry needs a name and a sha256")
        outcome[name] = digest
    return {**existing, **outcome}, outcome


def _stream(enrollment: dict, key: str) -> dict:
    document = enrollment.get("document")
    if not isinstance(document, dict):
        raise TrackRecordError("enrollment record has no document")
    stream = document.get(key)
    if not isinstance(stream, dict):
        raise TrackRecordError(f"enrollment document has no {key} stream")
    return stream


# --------------------------------------------------------------------------- production
def grade_production(*, enrollment: dict, outcome_source: dict, evaluated_at: str) -> dict[str, Any]:
    """Grade the archived football forecast under the ORIGINAL declaration, unchanged."""
    stream = _stream(enrollment, "production")
    rows = _unique(stream.get("rows") or [], "production")
    claim = "football_production"
    window = stream.get("window")
    policy = stream.get("plan_sha256")
    hashes = dict(enrollment.get("artifact_hashes") or {})

    if outcome_source.get("schema_version") != OUTCOME_SCHEMA:
        raise TrackRecordError(f"outcome source must be {OUTCOME_SCHEMA}")
    # Measurement identity is what the number MEASURES; vintage is when the labels were cut.
    # `labels_through` moves every time the feed is re-pulled, so comparing it as part of the
    # target would refuse a correct source for having a newer revision. It is recorded and
    # reported separately instead, and an artifact hash is never treated as a measurement identity.
    if _measurement_identity(outcome_source.get("target")) != _measurement_identity(stream.get("target")):
        raise TrackRecordError("outcome source target does not match the enrolled measurement target")
    hashes, outcome_hashes = _source_hashes(outcome_source, hashes)

    def unavailable(state: str, reason: str) -> dict[str, Any]:
        return _envelope(
            enrollment=enrollment, claim=claim, state=state, reason=reason, window=window,
            provenance_class=stream.get("provenance_class"), policy_sha256=policy,
            input_hashes=hashes, evaluated_at=evaluated_at,
            counts={"eligible": len(rows), "scored": 0, "missing": len(rows)}, result=None,
            horizon_days=None, outcome_source_hashes=outcome_hashes,
        )

    # A game that began before the freeze was never a forecast for that game.
    cutoff, start = stream.get("cutoff_at"), stream.get("target_start_at")
    if cutoff is None or start is None:
        return unavailable("input_unavailable", "freeze cutoff or target start is unproven")
    if _instant(cutoff, "cutoff_at") > _instant(start, "target_start_at"):
        return unavailable(
            "cutoff_ineligible",
            "a declared target game began before the demonstrable forecast freeze",
        )

    # The window must be closed before it can be graded, and the source must be describing the
    # SAME window. A source that self-asserts complete: true for a window that has not ended, or
    # for a different window, would otherwise grade a full-season forecast on a part-season.
    # The number depends on the code that produced it. Without a named, hashed scoring identity
    # the outcome column is an unattributed table, and "the declared scoring preset" is a claim
    # nobody can check later.
    identity = outcome_source.get("scoring_code_identity")
    if not isinstance(identity, dict) or not identity.get("sha256") or not identity.get("name"):
        return unavailable(
            "input_unavailable",
            "the outcome source names no scoring-code identity, so the numbers are unattributed",
        )

    end = stream.get("target_end_at")
    if end is None:
        return unavailable("input_unavailable", "the declared target end is unproven")
    if _instant(evaluated_at, "evaluated_at") < _instant(end, "target_end_at"):
        return unavailable(
            "awaiting_horizon",
            "the declared target window has not closed, so no full-window grade exists yet",
        )
    if outcome_source.get("window") != stream.get("window"):
        return unavailable(
            "input_unavailable",
            "the outcome source describes a different window from the enrolled one",
        )

    # Bytes stamped after the evaluation instant, or before the window they claim to describe
    # closed, are not evidence about that window. A source captured in 2099 cannot support a
    # 2027 grade, and one captured mid-season cannot describe a finished season.
    problem = _capture_chronology(outcome_source, evaluated_at=evaluated_at, closed_at=end,
                                  what="outcome source")
    if problem:
        return unavailable("input_unavailable", problem)

    # The expected universe comes from the ENROLLMENT's frozen schedule, never from the outcome
    # table's own assertion. Comparing weeks_expected to weeks_present only ever compared the
    # source to itself -- a tautological check that any self-consistent source passes, which is
    # how weeks_expected=[1] with games_expected=1 graded as a complete season.
    enrolled_weeks = stream.get("weeks_expected")
    enrolled_games = stream.get("expected_game_ids")
    if not isinstance(enrolled_weeks, list) or not enrolled_weeks:
        return unavailable("input_unavailable",
                           "the enrollment declares no frozen week universe")
    if not isinstance(enrolled_games, list) or not enrolled_games:
        return unavailable("input_unavailable",
                           "the enrollment declares no frozen expected_game_ids")
    if len(set(enrolled_games)) != len(enrolled_games):
        raise TrackRecordError("enrolled expected_game_ids carries duplicate game ids")

    coverage = outcome_source.get("coverage") or {}
    source_games = coverage.get("expected_game_ids")
    observed_games = coverage.get("observed_game_ids")
    if not isinstance(source_games, list) or not isinstance(observed_games, list):
        return unavailable(
            "input_unavailable",
            "the outcome coverage carries no expected_game_ids and observed_game_ids",
        )
    if len(set(source_games)) != len(source_games):
        raise TrackRecordError("outcome expected_game_ids carries duplicate game ids")
    if len(set(observed_games)) != len(observed_games):
        raise TrackRecordError("outcome observed_game_ids carries duplicate game ids")
    if set(source_games) != set(enrolled_games):
        return unavailable(
            "input_unavailable",
            "the outcome source redefines the expected game universe frozen at enrollment",
        )
    source_weeks = coverage.get("weeks_expected")
    if source_weeks is not None and sorted(source_weeks) != sorted(enrolled_weeks):
        return unavailable(
            "input_unavailable",
            "the outcome source redefines the expected week universe frozen at enrollment",
        )
    present = list(coverage.get("weeks_present") or [])
    if outcome_source.get("complete") is not True or sorted(present) != sorted(enrolled_weeks):
        return unavailable("input_unavailable", "the declared outcome window is not complete")

    unobserved = set(enrolled_games) - set(observed_games)
    if unobserved:
        return unavailable(
            "input_unavailable",
            f"{len(unobserved)} of {len(enrolled_games)} frozen scheduled games are unobserved",
        )
    if set(observed_games) - set(enrolled_games):
        return unavailable(
            "input_unavailable",
            "the outcome observes games outside the frozen enrolled schedule",
        )
    # An ABSENT count is an unproven input (a declared state); a malformed one is a broken
    # source (a refusal). They are different failures and must not collapse into one.
    if coverage.get("games_expected") is None or coverage.get("games_present") is None:
        return unavailable("input_unavailable",
                           "schedule game coverage is unproven for the declared window")
    games_expected = _count(coverage.get("games_expected"), "games_expected")
    games_present = _count(coverage.get("games_present"), "games_present")
    if games_expected != len(enrolled_games):
        return unavailable(
            "input_unavailable",
            "declared games_expected disagrees with the frozen enrolled schedule",
        )
    if games_present != games_expected:
        return unavailable(
            "input_unavailable",
            f"only {games_present} of {games_expected} scheduled games are covered",
        )

    players = outcome_source.get("players") or {}
    display: list[dict[str, Any]] = []
    scored: list[dict[str, Any]] = []
    for row in rows:
        player = row["sleeper_id"]
        record = players.get(player) or {}
        outcome = _finite(record.get("value"))
        forecast = _finite(row.get("forecast"))
        reason = record.get("reason")
        if outcome is None and reason is None:
            reason = "no verified outcome for this player"
        baselines = row.get("baselines") or {}
        display.append({
            "sleeper_id": player, "name": row.get("name"), "position": row.get("position"),
            "producer": row.get("producer"), "provenance": row.get("provenance"),
            "forecast": forecast,
            "baseline": _finite(baselines.get("prior_season")),
            "baseline_position_median": _finite(baselines.get("position_median")),
            "outcome": outcome,
            "error": None if (outcome is None or forecast is None) else abs(forecast - outcome),
            "reason": reason,
        })
        if outcome is not None and forecast is not None:
            scored.append({
                "player": player, "position": row.get("position"),
                "producer": row.get("producer"), "provenance": row.get("provenance"),
                "forecast_error": abs(forecast - outcome),
                "baseline_error": {
                    name: (None if _finite(baselines.get(name)) is None
                           else abs(_finite(baselines.get(name)) - outcome))
                    for name in BASELINES
                },
            })

    comparisons = _production_comparisons(scored, rows)
    missing = sum(1 for row in display if row["outcome"] is None)
    result = {
        "summary": (
            f"{len(scored)} of {len(rows)} enrolled players carry a numeric forecast and a "
            "verified outcome. Forecast error is compared with each declared baseline separately "
            "on identical players; producers are never pooled."
        ),
        "comparisons": comparisons,
        "rows": display,
        "details": [
            {"label": "Declaration",
             "value": "workspace-production-2026-v1, unchanged. One season only; this is not "
                      "validation of the five-year value framework."},
            {"label": "Primary metric",
             "value": "Equal-position forecast MAE minus baseline MAE. Negative favours the forecast."},
            {"label": "Interval",
             "value": f"Paired player bootstrap within position, {RESAMPLES} resamples, seed "
                      f"{PRODUCTION_SEED}, percentile 95%."},
            {"label": "Provenance",
             "value": f"Baseline inputs are {stream.get('provenance_class')}; a reconstruction is "
                      "never equivalent to a contemporaneous frozen baseline."},
            {"label": "Excluded",
             "value": f"{missing} enrolled players have no verified outcome and are missing, not zero."},
            {"label": "Outcome vintage",
             "value": (f"labels_through {(outcome_source.get('target') or {}).get('labels_through')}; "
                       "recorded separately from the measurement target. An artifact hash is not a "
                       "measurement identity, and a file timestamp does not prove when we held the bytes.")},
        ],
    }
    return _envelope(
        enrollment=enrollment, claim=claim, state="graded", reason=None, window=window,
        provenance_class=stream.get("provenance_class"), policy_sha256=policy,
        input_hashes=hashes, evaluated_at=evaluated_at,
        counts={"eligible": len(rows), "scored": len(scored), "missing": missing}, result=result,
        horizon_days=None, outcome_source_hashes=outcome_hashes,
    )


def _equal_position_mae_difference(entries: list[dict], baseline: str) -> tuple[Optional[float], list[str]]:
    positions = sorted({e["position"] for e in entries})
    diffs: list[float] = []
    for position in positions:
        cohort = [e for e in entries
                  if e["position"] == position and e["baseline_error"].get(baseline) is not None]
        if not cohort:
            return None, positions
        forecast_mae = float(np.mean([e["forecast_error"] for e in cohort]))
        baseline_mae = float(np.mean([e["baseline_error"][baseline] for e in cohort]))
        diffs.append(forecast_mae - baseline_mae)
    return (float(np.mean(diffs)) if diffs else None), positions


def _production_comparisons(scored: list[dict], enrolled: list[dict]) -> list[dict[str, Any]]:
    """Separate every (producer, provenance) stratum. Never pool them into one flattering number.

    An earlier version grouped by producer alone and carried `provenance` through the rows
    without using it, so an original and a recovered forecast from the SAME producer landed in
    one aggregate. Recovered rows do not necessarily carry a different producer id, so producer
    grouping cannot stand in for provenance grouping.

    `eligible` counts the full enrolled stratum, not the subset that already survived to a
    numeric forecast and outcome, so the denominator shows what was excluded.
    """
    comparisons: list[dict[str, Any]] = []
    # Strata are enumerated from the ENROLLED rows. Deriving them from `scored` made a stratum
    # whose every outcome was missing vanish from the report entirely -- the reader saw the
    # producers that survived and had no way to see the one that produced nothing.
    strata = sorted({(r.get("producer") or "unnamed", r.get("provenance") or "unstated")
                     for r in enrolled})
    required = {"QB", "RB", "WR", "TE"}

    def stratum_rows(producer: str, provenance: str) -> list[dict]:
        return [r for r in enrolled
                if (r.get("producer") or "unnamed") == producer
                and (r.get("provenance") or "unstated") == provenance]

    def enrolled_in(producer: str, provenance: str) -> int:
        return len(stratum_rows(producer, provenance))

    for producer, provenance in strata:                              # aggregates first
        entries = [e for e in scored
                   if (e["producer"] or "unnamed") == producer
                   and (e["provenance"] or "unstated") == provenance]
        stratum_enrolled = enrolled_in(producer, provenance)
        for baseline in BASELINES:
            usable = [e for e in entries if e["baseline_error"].get(baseline) is not None]
            covered = {e["position"] for e in usable}
            identity = f"production:aggregate:{producer}:{provenance}:{baseline}"
            label = (f"{producer} ({provenance}) versus {baseline.replace('_', ' ')} "
                     "— all positions")
            if not required.issubset(covered):
                comparisons.append(_comparison(
                    identity=identity, label=label, units="points MAE difference",
                    estimate=None, interval=None, state="insufficient",
                    note="every position must be evaluable before an aggregate is reported; "
                         f"covered {sorted(covered)}",
                    eligible=stratum_enrolled, scored=len(usable)))
                continue
            estimate, _ = _equal_position_mae_difference(usable, baseline)
            interval = _bootstrap_production(usable, baseline)
            comparisons.append(_comparison(
                identity=identity, label=label, units="points MAE difference",
                estimate=estimate, interval=interval, favorable_when="below_zero",
                note="negative favours the forecast; one season only",
                eligible=stratum_enrolled, scored=len(usable)))

    for producer, provenance in strata:                              # then descriptive positions
        entries = [e for e in scored
                   if (e["producer"] or "unnamed") == producer
                   and (e["provenance"] or "unstated") == provenance]
        rows_here = stratum_rows(producer, provenance)
        # Positions are enumerated from the enrolled stratum, so a position whose every row was
        # excluded still shows a denominator instead of disappearing.
        for position in sorted({r.get("position") for r in rows_here if r.get("position")}):
            cohort_all = [e for e in entries if e["position"] == position]
            enrolled_here = sum(1 for r in rows_here if r.get("position") == position)
            if not cohort_all:
                comparisons.append(_comparison(
                    identity=f"position:{position}:{producer}:{provenance}:forecast_mae",
                    label=f"{position} — {producer} ({provenance}) forecast MAE",
                    units="points", estimate=None, interval=None, state="insufficient",
                    note="no enrolled row in this position reached a numeric forecast and outcome",
                    eligible=enrolled_here, scored=0))
                continue
            errors = np.array([e["forecast_error"] for e in cohort_all], dtype=float)
            # The declaration promises positional MAE and RMSE descriptively, not only a difference.
            comparisons.append(_comparison(
                identity=f"position:{position}:{producer}:{provenance}:forecast_mae",
                label=f"{position} — {producer} ({provenance}) forecast MAE",
                units="points", estimate=float(errors.mean()), interval=None,
                state="insufficient", note="descriptive positional error, not a decision rule",
                eligible=enrolled_here, scored=len(cohort_all)))
            comparisons.append(_comparison(
                identity=f"position:{position}:{producer}:{provenance}:forecast_rmse",
                label=f"{position} — {producer} ({provenance}) forecast RMSE",
                units="points", estimate=float(np.sqrt((errors ** 2).mean())), interval=None,
                state="insufficient", note="descriptive positional error, not a decision rule",
                eligible=enrolled_here, scored=len(cohort_all)))
            for baseline in BASELINES:
                cohort = [e for e in cohort_all if e["baseline_error"].get(baseline) is not None]
                if not cohort:
                    continue
                forecast_mae = float(np.mean([e["forecast_error"] for e in cohort]))
                baseline_mae = float(np.mean([e["baseline_error"][baseline] for e in cohort]))
                comparisons.append(_comparison(
                    identity=f"position:{position}:{producer}:{provenance}:{baseline}",
                    label=f"{position} — {producer} ({provenance}) versus "
                          f"{baseline.replace('_', ' ')}",
                    units="points MAE difference",
                    estimate=forecast_mae - baseline_mae, interval=None, state="insufficient",
                    note="descriptive; position intervals are not a decision rule",
                    eligible=enrolled_here, scored=len(cohort)))
    return comparisons


def _bootstrap_production(entries: list[dict], baseline: str) -> Optional[list[float]]:
    positions = sorted({e["position"] for e in entries})
    buckets = {p: [e for e in entries if e["position"] == p] for p in positions}
    rng = np.random.default_rng(PRODUCTION_SEED)
    samples: list[float] = []
    for _ in range(RESAMPLES):
        diffs: list[float] = []
        for position in positions:
            cohort = buckets[position]
            picks = rng.integers(0, len(cohort), size=len(cohort))
            forecast = float(np.mean([cohort[i]["forecast_error"] for i in picks]))
            base = float(np.mean([cohort[i]["baseline_error"][baseline] for i in picks]))
            diffs.append(forecast - base)
        if diffs:
            samples.append(float(np.mean(diffs)))
    return _percentile_interval(samples)


def select_endpoint(*, inventory: list[dict], t0: str, horizon_days: int,
                    configuration: Any, evaluated_at: str) -> dict[str, Any]:
    """The FIRST complete COMPATIBLE capture in the registered window, chosen before results.

    Deterministic by (as_of, content hash) so a reversed inventory cannot change the answer, and
    so a caller cannot reach past a day-90 capture to a more flattering day-92 one.

    "Compatible" is enforced, not asserted. An earlier capture taken under different league
    settings is not a cheaper version of the right capture -- it is a different measurement, and
    letting it win on timestamp alone graded a 1QB board against a superflex enrollment. A
    capture stamped after the evaluation instant did not exist when the run was made and cannot
    be selected by it.
    """
    if horizon_days not in ALLOWED_HORIZONS:
        raise TrackRecordError(f"horizon_days must be one of {ALLOWED_HORIZONS}")
    start = _instant(t0, "market t0") + horizon_days * 86400.0
    end = start + CAPTURE_WINDOW_DAYS * 86400.0
    limit = _instant(evaluated_at, "evaluated_at")
    eligible, rejected = [], []
    for entry in inventory:
        as_of = entry.get("as_of")
        digest = entry.get("sha256")
        if not isinstance(as_of, str) or not isinstance(digest, str) or len(digest) != 64:
            raise TrackRecordError("every inventory capture needs an as_of and a sha256")
        moment = _instant(as_of, "capture as_of")
        if entry.get("complete") is not True:
            rejected.append((as_of, "incomplete"))
            continue
        if configuration is not None and entry.get("configuration") != configuration:
            rejected.append((as_of, "configuration differs from the enrolled one"))
            continue
        if moment > limit:
            rejected.append((as_of, "stamped after the evaluation instant"))
            continue
        if not (start <= moment <= end):
            rejected.append((as_of, "outside the registered window"))
            continue
        eligible.append((moment, digest, entry))
    if not eligible:
        return {"chosen": None,
                "reason": "no complete compatible capture falls inside the registered window",
                "considered": len(inventory), "rejected": rejected}
    eligible.sort(key=lambda item: (item[0], item[1]))
    return {"chosen": eligible[0][2], "reason": None,
            "considered": len(inventory), "rejected": rejected}


# --------------------------------------------------------------------------- market
def grade_market(*, enrollment: dict, endpoint_source: Optional[dict], evaluated_at: str,
                 horizon_days: int = 90) -> dict[str, Any]:
    """Test the ordinal hypothesis. Never a price forecast: every row's ``error`` is null."""
    if horizon_days not in ALLOWED_HORIZONS:
        raise TrackRecordError(f"horizon_days must be one of {ALLOWED_HORIZONS}")
    stream = _stream(enrollment, "market")
    rows = _unique(stream.get("rows") or [], "market")
    # The claim names WHAT is being tested; the horizon is a separate field. Folding the horizon
    # into the claim string made "market_movement_30d" and "market_movement_90d" look like two
    # different claims to a consumer keyed on claim alone, which is how a descriptive 30-day
    # result could stand in for an absent 90-day one.
    claim = "market_movement"
    policy = stream.get("plan_sha256")
    hashes = dict(enrollment.get("artifact_hashes") or {})

    # Whether this was ever a live prospective registration was settled at enrollment, so it is
    # decided BEFORE the capture window is consulted. Asking "has a capture arrived yet?" first
    # reported an ineligible stream as awaiting_capture, which reads as merely early.
    registered = stream.get("state")
    if registered in MARKET_INELIGIBLE_STATES:
        return _envelope(
            enrollment=enrollment, claim=claim, state="input_unavailable",
            reason=(f"the enrolled market stream is {registered}"
                    f"{'' if not stream.get('reason') else ': ' + str(stream.get('reason'))}; "
                    "a later endpoint cannot make an ineligible registration prospective"),
            window={"label": f"{horizon_days}-day", "start_at": stream.get("t0"), "end_at": None},
            provenance_class=stream.get("provenance_class"), policy_sha256=policy,
            input_hashes=hashes, evaluated_at=evaluated_at,
            counts={"eligible": len(rows), "scored": 0, "missing": len(rows)}, result=None,
            horizon_days=horizon_days, outcome_source_hashes={},
        )

    if endpoint_source is None:
        # No compatible capture was selected. Whether that is "not yet" or "never" depends on
        # where the evaluation instant sits relative to the registered window, not on hope.
        opens_at = _instant(stream.get("t0"), "market t0") + horizon_days * 86400.0
        closes_at = opens_at + CAPTURE_WINDOW_DAYS * 86400.0
        # The window is day 90 THROUGH day 93. On day 91 a compatible capture can still arrive,
        # so the absence of one is "not yet", not "never" -- calling it input_unavailable closed
        # a window that was still open and made a recoverable state look terminal.
        moment = _instant(evaluated_at, "evaluated_at")
        pending = moment <= closes_at
        return _envelope(
            enrollment=enrollment, claim=claim,
            state="awaiting_capture" if pending else "input_unavailable",
            reason=("the registered capture window has not opened" if moment < opens_at else
                    "the registered capture window is still open" if pending else
                    "no complete compatible capture fell inside the registered window"),
            window={"label": f"{horizon_days}-day", "start_at": stream.get("t0"), "end_at": None},
            provenance_class=stream.get("provenance_class"), policy_sha256=policy,
            input_hashes=hashes, evaluated_at=evaluated_at,
            counts={"eligible": len(rows), "scored": 0, "missing": len(rows)}, result=None,
            horizon_days=horizon_days, outcome_source_hashes={},
        )
    if endpoint_source.get("schema_version") != ENDPOINT_SCHEMA:
        raise TrackRecordError(f"endpoint source must be {ENDPOINT_SCHEMA}")
    if endpoint_source.get("configuration") != stream.get("configuration"):
        raise TrackRecordError("endpoint capture configuration does not match the enrolled one")
    hashes, outcome_hashes = _source_hashes(endpoint_source, hashes)

    t0 = _instant(stream.get("t0"), "market t0")
    opens = t0 + horizon_days * 86400.0
    closes = opens + CAPTURE_WINDOW_DAYS * 86400.0
    as_of = _instant(endpoint_source.get("as_of"), "endpoint as_of")
    observed_window = {
        "label": f"{horizon_days}-day",
        "start_at": stream.get("t0"),
        "end_at": endpoint_source.get("as_of"),
    }

    def unavailable(state: str, reason: str) -> dict[str, Any]:
        return _envelope(
            enrollment=enrollment, claim=claim, state=state, reason=reason, window=observed_window,
            provenance_class=stream.get("provenance_class"), policy_sha256=policy,
            input_hashes=hashes, evaluated_at=evaluated_at,
            counts={"eligible": len(rows), "scored": 0, "missing": len(rows)}, result=None,
            horizon_days=horizon_days, outcome_source_hashes=outcome_hashes,
        )

    if as_of > _instant(evaluated_at, "evaluated_at"):
        return unavailable(
            "input_unavailable",
            "the endpoint capture is stamped after the evaluation instant, so it did not exist "
            "when this run was made",
        )
    if as_of < opens:
        return unavailable("awaiting_capture", "the registered capture window has not opened")
    if as_of > closes:
        return unavailable(
            "input_unavailable",
            "no complete capture fell inside the registered window; no outside-window fallback",
        )
    if endpoint_source.get("complete") is not True:
        return unavailable("input_unavailable",
                           "capture-wide coverage is incomplete, so no primary grade is produced")
    # The endpoint's own as_of is a label on the envelope. The raw captures behind it carry their
    # own stamps, and a capture declared in 2099 was not knowable by a 2026 run whatever the
    # envelope says. Matching an inventory digest proves identity, never knowledge.
    problem = _capture_chronology(endpoint_source, evaluated_at=evaluated_at, closed_at=None,
                                  what="endpoint source")
    if problem:
        return unavailable("input_unavailable", problem)

    prices = endpoint_source.get("prices") or {}
    entries: list[dict[str, Any]] = []
    display: list[dict[str, Any]] = []
    start_zero = 0
    for row in rows:
        player = row["sleeper_id"]
        record = prices.get(player) or {}
        end = _finite(record.get("price"))
        start = _finite(row.get("start_price"))
        gap_low, gap_high = _midpoint(row.get("market_rank")), _midpoint(row.get("our_rank"))
        gap = None if (gap_low is None or gap_high is None) else gap_low - gap_high
        reason = record.get("reason")
        raw: Optional[float] = None
        if start is not None and start == 0.0:
            start_zero += 1
            reason = reason or "start price zero, excluded from percentage return"
        elif start is not None and start > 0.0 and end is not None and end >= 0.0:
            raw = (end / start) - 1.0
        elif end is None:
            reason = reason or "absent from the complete capture"
        display.append({
            "sleeper_id": player, "name": row.get("name"), "position": row.get("position"),
            "producer": None, "provenance": "market",
            "forecast": gap, "baseline": _finite(row.get("momentum")),
            "baseline_position_median": None,
            "outcome": None, "error": None, "reason": reason,
        })
        entries.append({
            "player": player, "position": row.get("position"), "gap": gap, "raw": raw,
            "momentum": _finite(row.get("momentum")), "index": len(display) - 1,
            # a zero START price is excluded from percentage returns; it is NOT a missing endpoint
            "start_zero": start is not None and start == 0.0,
            # a percentage return needs a POSITIVE start; unknown and zero are both ineligible
            "start_positive": start is not None and start > 0.0,
            "endpoint_missing": end is None,
        })

    valid = [e for e in entries if e["raw"] is not None]
    adjustment = float(np.median([e["raw"] for e in valid])) if valid else None
    for entry in valid:
        entry["adjusted"] = entry["raw"] - adjustment
        display[entry["index"]]["outcome"] = entry["adjusted"]

    usable = [e for e in valid if e["gap"] is not None]
    comparisons = _market_comparisons(usable)
    missing = sum(1 for row in display if row["outcome"] is None)
    # Only the PRIMARY aggregate decides the state. Descriptive position readings must never
    # promote a grade to "graded" when the declared four-position aggregate does not exist.
    primary = next(c for c in comparisons if c["id"] == "market:gap_correlation")
    degenerate = primary["estimate"] is None
    state = "insufficient_evidence" if degenerate else "graded"

    sensitivity = _missing_endpoint_sensitivity(entries)
    result = {
        "summary": (
            f"{len(usable)} of {len(rows)} enrolled players carry a rank gap and a valid "
            f"{horizon_days}-day relative movement. Ordinal association only: no price was forecast, "
            "so no row carries an error."
        ),
        "comparisons": comparisons,
        "rows": display,
        "details": [
            {"label": "Declaration",
             "value": "workspace-market-movement-90d-v1. The archived declaration's "
                      "market_movement block remains not_registered_for_grading and is unchanged."},
            {"label": "Claim limit",
             "value": "Ordinal association only — not a FantasyCalc value forecast, not a trade "
                      "return, not a demonstrated edge."},
            {"label": "Market adjustment",
             "value": ("no valid pair, so no adjustment" if adjustment is None else
                       f"median raw movement {adjustment:+.4f} subtracted; available-case "
                       f"denominator of {len(valid)} players, not a survivor-free index")},
            {"label": "Observed window",
             "value": f"t0 {stream.get('t0')} to capture {endpoint_source.get('as_of')} "
                      f"(nominal {horizon_days} days)"},
            {"label": "Excluded",
             "value": f"{missing} without a usable endpoint; {start_zero} with a zero start price "
                      "retained but outside the percentage return"},
            {"label": "Missing-endpoint sensitivity",
             "value": (f"{sensitivity['state']}: {sensitivity['note']}"
                       + ("" if sensitivity.get("estimate") is None else
                          f" Scenario correlation {sensitivity['estimate']:+.4f} on "
                          f"{sensitivity.get('scored_n')} players, including "
                          f"{sensitivity['missing_n']} set to -100%."))},
            {"label": "Limitation",
             "value": "Player bootstrap intervals do not fully account for team-wide shocks, and "
                      "one enrolled cohort is not a repeatable edge."},
        ],
    }
    return _envelope(
        enrollment=enrollment, claim=claim, state=state,
        reason=("the declared four-position aggregate is not evaluable; any position "
                "readings below are descriptive only") if degenerate else None,
        window=observed_window, provenance_class=stream.get("provenance_class"),
        policy_sha256=policy, input_hashes=hashes, evaluated_at=evaluated_at,
        counts={"eligible": len(rows), "scored": len(usable), "missing": missing}, result=result,
        horizon_days=horizon_days, outcome_source_hashes=outcome_hashes,
    )


REQUIRED_POSITIONS = ("QB", "RB", "WR", "TE")


def _equal_position_mean(entries: list[dict], predictor: str) -> tuple[Optional[float], list[str]]:
    """All four positions, each with a real non-degenerate cohort, or no aggregate at all.

    Averaging whatever positions happen to qualify would let a two-position result stand where
    the declaration asks for four, and the reader would have no way to see the difference.
    """
    values: list[float] = []
    for position in REQUIRED_POSITIONS:
        cohort = [e for e in entries if e["position"] == position and e.get(predictor) is not None]
        if len(cohort) < MIN_POSITION_COHORT:
            return None, list(REQUIRED_POSITIONS)
        rho = _spearman(np.array([e[predictor] for e in cohort], dtype=float),
                        np.array([e["adjusted"] for e in cohort], dtype=float))
        if rho is None:
            return None, list(REQUIRED_POSITIONS)
        values.append(rho)
    return float(np.mean(values)), list(REQUIRED_POSITIONS)


def _market_comparisons(entries: list[dict]) -> list[dict[str, Any]]:
    """Three readings, and the paired one is computed on complete cases only.

    An earlier version subtracted the momentum correlation, measured on the players that HAVE
    momentum, from the gap correlation measured on EVERY player, and then bootstrapped the
    difference on the paired subset alone. That is two different populations inside one
    subtraction: the point estimate and its interval did not describe the same players, and the
    difference would move when momentum coverage changed even if nothing about the market did.
    The paired difference now uses one complete-case population per position, and both of its
    component correlations are recomputed on exactly that population.
    """
    paired = [e for e in entries if e.get("gap") is not None and e.get("momentum") is not None]

    gap_all, _ = _equal_position_mean(entries, "gap")
    gap_all_interval = _bootstrap_market(entries, "gap") if gap_all is not None else None

    gap_paired, _ = _equal_position_mean(paired, "gap")
    momentum_paired, _ = _equal_position_mean(paired, "momentum")
    difference = (None if (gap_paired is None or momentum_paired is None)
                  else gap_paired - momentum_paired)
    difference_interval = _bootstrap_market_difference(paired) if difference is not None else None

    undefined_note = (
        "undefined, not zero: the predictor or the adjusted outcome is constant, or one of the "
        f"four positions has fewer than {MIN_POSITION_COHORT} eligible players"
    )
    return [
        _comparison(
            identity="market:gap_correlation",
            label="Rank-gap association with relative movement (all eligible players)",
            units="Spearman correlation", estimate=gap_all, interval=gap_all_interval,
            note="ordinal association only" if gap_all is not None else undefined_note,
            eligible=len(entries), scored=len(entries) if gap_all is not None else 0),
        _comparison(
            identity="market:gap_correlation_paired",
            label="Rank-gap association on the players that also carry frozen momentum",
            units="Spearman correlation", estimate=gap_paired, interval=None, state="insufficient",
            note=("the gap side of the paired difference, on the complete-case population"
                  if gap_paired is not None else undefined_note),
            eligible=len(paired), scored=len(paired) if gap_paired is not None else 0),
        _comparison(
            identity="market:momentum_correlation",
            label="Trailing 30-day momentum association, on the same complete-case players",
            units="Spearman correlation", estimate=momentum_paired, interval=None,
            state="insufficient",
            note=("the declared comparator, shown descriptively"
                  if momentum_paired is not None
                  else "frozen momentum is unavailable, so no comparator claim is made"),
            eligible=len(paired), scored=len(paired) if momentum_paired is not None else 0),
        _comparison(
            identity="market:paired_difference",
            label="Rank gap minus momentum, both on the same complete-case players",
            units="Spearman correlation difference", estimate=difference,
            interval=difference_interval,
            note=("outperforming the comparator requires this interval wholly above zero; "
                  f"computed on {len(paired)} complete cases of {len(entries)} eligible"
                  if difference is not None
                  else "no comparator claim without frozen momentum on the same players"),
            eligible=len(entries), scored=len(paired) if difference is not None else 0),
        # A valid position reading survives even when one other position fails the aggregate gate.
        # Suppressing the whole table because TE is thin would hide readings that are fine.
        *_market_position_descriptions(entries),
    ]


def _market_position_descriptions(entries: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for position in REQUIRED_POSITIONS:
        cohort = [e for e in entries if e["position"] == position and e.get("gap") is not None]
        if not cohort:
            continue
        rho = (_spearman(np.array([e["gap"] for e in cohort], dtype=float),
                         np.array([e["adjusted"] for e in cohort], dtype=float))
               if len(cohort) >= MIN_POSITION_COHORT else None)
        out.append(_comparison(
            identity=f"position:{position}:market:gap_correlation",
            label=f"{position} — rank-gap association with relative movement",
            units="Spearman correlation", estimate=rho, interval=None, state="insufficient",
            note=("descriptive; position readings are not a decision rule" if rho is not None
                  else f"undefined: fewer than {MIN_POSITION_COHORT} eligible players, or a "
                       "constant predictor or outcome"),
            eligible=len(cohort), scored=len(cohort) if rho is not None else 0))
    return out


def _bootstrap_market(entries: list[dict], predictor: str) -> Optional[list[float]]:
    positions = list(REQUIRED_POSITIONS)
    buckets = {p: [e for e in entries if e["position"] == p] for p in positions}
    if any(len(buckets[p]) < MIN_POSITION_COHORT for p in positions):
        return None
    rng = np.random.default_rng(MARKET_SEED)
    samples: list[float] = []
    for _ in range(RESAMPLES):
        values: list[float] = []
        for position in positions:
            cohort = buckets[position]
            picks = rng.integers(0, len(cohort), size=len(cohort))
            rho = _spearman(np.array([cohort[i][predictor] for i in picks], dtype=float),
                            np.array([cohort[i]["adjusted"] for i in picks], dtype=float))
            if rho is None:
                values = []
                break
            values.append(rho)
        if values:
            samples.append(float(np.mean(values)))
    return _percentile_interval(samples)


def _bootstrap_market_difference(entries: list[dict]) -> Optional[list[float]]:
    positions = list(REQUIRED_POSITIONS)
    buckets = {p: [e for e in entries if e["position"] == p] for p in positions}
    if any(len(buckets[p]) < MIN_POSITION_COHORT for p in positions):
        return None
    rng = np.random.default_rng(MARKET_SEED)
    samples: list[float] = []
    for _ in range(RESAMPLES):
        gaps: list[float] = []
        moms: list[float] = []
        for position in positions:
            cohort = buckets[position]
            picks = rng.integers(0, len(cohort), size=len(cohort))
            adjusted = np.array([cohort[i]["adjusted"] for i in picks], dtype=float)
            gap = _spearman(np.array([cohort[i]["gap"] for i in picks], dtype=float), adjusted)
            mom = _spearman(np.array([cohort[i]["momentum"] for i in picks], dtype=float), adjusted)
            if gap is None or mom is None:
                gaps = []
                break
            gaps.append(gap)
            moms.append(mom)
        if gaps:
            samples.append(float(np.mean(gaps)) - float(np.mean(moms)))
    return _percentile_interval(samples)


def _missing_endpoint_sensitivity(entries: list[dict]) -> dict[str, Any]:
    """The declared scenario, actually RECOMPUTED on the declared cohort.

    The cohort is the INITIAL enrolled population whose frozen baseline was available and whose
    start price is positive -- not every row that happens to carry a gap. A player with no frozen
    momentum has no baseline to re-associate, and a zero or unknown start price has no percentage
    return at all. An earlier version rebuilt a gap-only correlation over every gap-bearing row
    and reported a strong association from a cohort in which nobody had frozen momentum, which
    answered a question the declaration never asked.

    Missing endpoints inside that cohort are assigned a hypothetical end price of zero (-100%)
    and the whole statistic is rebuilt: the market adjustment is re-derived from the enlarged
    valid population, never reused from the primary. Recorded statuses stay missing and the
    primary result is untouched. This is one declared scenario, not a bound on all outcomes.
    """
    cohort = [e for e in entries
              if e.get("start_positive") and e.get("gap") is not None
              and e.get("momentum") is not None]
    if not cohort:
        return {"state": "insufficient", "missing_n": 0, "estimate": None, "cohort_n": 0,
                "note": ("no enrolled player carries both a frozen baseline and a positive start "
                         "price, so the declared scenario has no cohort to evaluate")}

    missing = [e for e in cohort if e.get("endpoint_missing")]
    if not missing:
        return {"state": "not_exercised", "missing_n": 0, "estimate": None,
                "cohort_n": len(cohort),
                "note": (f"every one of the {len(cohort)} baseline-complete players has an "
                         "endpoint, so the scenario does not apply")}

    scenario = {id(e) for e in missing}
    rebuilt: list[dict[str, Any]] = []
    for entry in cohort:
        raw = entry["raw"] if entry["raw"] is not None else (
            -1.0 if id(entry) in scenario else None)
        if raw is None:
            continue
        rebuilt.append({**entry, "raw": raw})
    if not rebuilt:
        return {"state": "unavailable", "missing_n": len(missing), "estimate": None,
                "cohort_n": len(cohort),
                "note": "no player survives the scenario with both a gap and a movement"}

    adjustment = float(np.median([e["raw"] for e in rebuilt]))
    for entry in rebuilt:
        entry["adjusted"] = entry["raw"] - adjustment
    gap_estimate, _ = _equal_position_mean(rebuilt, "gap")
    momentum_estimate, _ = _equal_position_mean(rebuilt, "momentum")
    if gap_estimate is None or momentum_estimate is None:
        return {"state": "insufficient", "missing_n": len(missing), "estimate": None,
                "cohort_n": len(cohort), "scored_n": len(rebuilt),
                "note": ("the scenario cohort does not meet the four-position minimum on both "
                         "the rank gap and the frozen baseline, so no sensitivity is reported")}
    return {"state": "computed", "missing_n": len(missing), "estimate": gap_estimate,
            "momentum_estimate": momentum_estimate,
            "paired_difference": gap_estimate - momentum_estimate,
            "cohort_n": len(cohort), "scored_n": len(rebuilt), "adjustment": adjustment,
            "note": ("missing endpoints inside the baseline-complete cohort set to a hypothetical "
                     "-100%; the market adjustment is re-derived on the enlarged population; "
                     "primary data unchanged")}


def canonical_grade_bytes(document: dict) -> bytes:
    """Stable bytes for content addressing. Rejects NaN so a grade can never carry one."""
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")
