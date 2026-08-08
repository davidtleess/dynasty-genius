"""Per-stream manual-feed cadence: two independent axes.

WHY THIS EXISTS
    On 2026-08-08 PFF and PlayerProfiler both reported `due` at roughly seven days while holding
    season-complete data through 2025. No in-scope 2026 regular-season event had occurred, so no
    2026 regular-season gamelog, grade, or snap count could exist — our own importer had returned
    `unchanged` for all six gamelog and all six play-by-play seasons a week earlier. A flat daily
    clock on a seasonal source manufactures an obligation no vendor data can satisfy, and a status
    surface that cries wolf all summer gets ignored in September, which is exactly when it matters.

TWO AXES, NEVER COLLAPSED
    CADENCE  : current | due | not_due | undetermined   — is an acquisition owed right now?
    COVERAGE : adequate | unknown | inadequate          — is what we hold materially complete?

    These are independent and both always serialize. PlayerProfiler's medical archive in June is
    BOTH not-due (no observable event is pending) AND inadequate (it stops at 2023 while play runs
    to 2026). An earlier design made one "outrank" the other; that destroyed information and forced
    a false choice between "nothing to do" and "your data is incomplete". David needs both facts.

    `undetermined` is not a synonym for `not_due`. RotoViz and Campus2Canton hold no data and no
    marker, so no obligation can be COMPUTED for them at all — saying not_due would assert that
    nothing is owed, which we do not know.

PER STREAM, NOT PER SOURCE
    A source is not one thing. In a single PlayerProfiler import run, gamelog and pbp returned
    `unchanged` while roster returned `inserted`. One cadence per source is wrong in both directions
    simultaneously: it nags for frozen streams and under-serves the moving one.

EVENTS, NOT TIMERS
    Neither vendor exposes a governed push signal, so "refresh every time it changes" is achievable
    only at OBSERVABLE EVENT WINDOWS — a completed game week, the league year opening, the draft, a
    published correction. Time passing is never a trigger, and a settled season does not reopen
    because another week was played somewhere else.

EVIDENCE HAS TO PRE-DATE THE QUESTION
    What a vendor offers is an OBSERVATION carrying when and how it was made, never a bare oracle.
    An observation timestamped after the instant being evaluated is refused outright: evidence from
    the future is not evidence.

DELIBERATELY NOT HERE
    No scheduler, no automated acquisition, no provider contact, no paid action, no normalized or
    analytical store, no consumer rewiring, and no promotion of PFF grades to a model surface —
    grades are barred as MODEL INPUTS by shipped contracts, while raw retention, diagnostic review
    and ingestion at their cadence all remain allowed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence

__all__ = [
    "CadenceError",
    "CADENCE_STATES",
    "COVERAGE_STATES",
    "CURRENT",
    "DUE",
    "NOT_DUE",
    "UNDETERMINED",
    "ADEQUATE",
    "UNKNOWN",
    "INADEQUATE",
    "OBSERVABLE_TRIGGERS",
    "HISTORY_CORRECTION_TRIGGERS",
    "MANUAL_SOURCES",
    "StreamPolicy",
    "StreamState",
    "StreamDisposition",
    "build_policy_registry",
    "streams_for",
    "policy_for",
    "validate_triggers",
    "stream_disposition",
    "evaluate_stream",
    "evaluate_source",
    "build_report",
]

# --------------------------------------------------------------------------------------
# Vocabulary — two closed, DISJOINT sets. A shared token would invite recollapsing them.
# --------------------------------------------------------------------------------------

CURRENT, DUE, NOT_DUE, UNDETERMINED = "current", "due", "not_due", "undetermined"
CADENCE_STATES = frozenset({CURRENT, DUE, NOT_DUE, UNDETERMINED})

ADEQUATE, UNKNOWN, INADEQUATE = "adequate", "unknown", "inadequate"
COVERAGE_STATES = frozenset({ADEQUATE, UNKNOWN, INADEQUATE})

#: Every legal trigger. There is deliberately no `vendor_push`: no governed push signal exists, and
#: inventing one would let an implementation claim knowledge it cannot have.
OBSERVABLE_TRIGGERS = frozenset({
    "game_week_complete",
    "season_final",
    "league_year_open",
    "draft_complete",
    "combine_complete",
    "vendor_correction_notice",
    "schema_change",
    "methodology_change",
    "pre_analysis_hash_check",
    "operator_drop",
})

#: A COMPLETED season reopens only on one of these. Time passing is not among them, and neither is
#: another game week being played — that would drag settled history back into the queue forever.
HISTORY_CORRECTION_TRIGGERS = frozenset({
    "vendor_correction_notice",
    "schema_change",
    "methodology_change",
    "pre_analysis_hash_check",
})

#: How a stream's completeness is judged.
#:   VENDOR_OFFER  — adequate when we hold everything the vendor currently publishes. Holding MORE
#:                   than is offered is never a gap: we may retain seasons the vendor has retired,
#:                   and treating that as a defect would license pruning real data.
#:   CONTIGUOUS    — adequate only when every season through the current one is represented. Used
#:                   where a hole is a blind spot rather than a choice: injuries happen every year,
#:                   so a medical archive stopping at 2023 is incomplete even if that is all the
#:                   vendor ships.
VENDOR_OFFER, CONTIGUOUS = "vendor_offer", "contiguous_through_current_season"

MANUAL_SOURCES: tuple[str, ...] = ("playerprofiler", "pff", "rotoviz", "campus2canton")

#: Measured from app/data/pff_exports/pff_unique_payload_inventory.csv: seven report families across
#: two leagues. The league prefix stays in the key because NFL and FBS publish on different clocks.
_PFF_FAMILIES: tuple[str, ...] = (
    "passing_depth", "passing_pressure", "passing_summary",
    "receiving_depth", "receiving_scheme", "receiving_summary", "rushing_summary",
)

#: Which availability window a PFF lane follows.
_LEAGUE_WINDOW = {"nfl": "nfl", "ncaa": "fbs"}


class CadenceError(RuntimeError):
    """A cadence question could not be answered as posed."""


@dataclass(frozen=True)
class StreamPolicy:
    source: str
    stream: str
    triggers: tuple[str, ...]
    coverage_basis: str = VENDOR_OFFER
    #: Which availability clock gates this stream's events, when availability facts are supplied.
    window: Optional[str] = None


@dataclass
class StreamState:
    source: str
    stream: str
    cadence: str
    coverage: str
    age_days: Optional[float] = None
    missing_seasons: tuple[int, ...] = ()
    trigger: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "stream": self.stream,
            "cadence": self.cadence,
            "coverage": self.coverage,
            "age_days": self.age_days,
            "missing_seasons": list(self.missing_seasons),
            "trigger": self.trigger,
        }


@dataclass(frozen=True)
class StreamDisposition:
    source: str
    stream: str
    model_use_forbidden: bool
    retained_raw: bool
    ingestion_authorized: bool
    creates_refresh_obligation: bool
    consumer_authorized: bool = False


# --------------------------------------------------------------------------------------
# Policy registry
# --------------------------------------------------------------------------------------


def build_policy_registry(
    declarations: Iterable[tuple[str, str, Sequence[str]]],
) -> dict[tuple[str, str], StreamPolicy]:
    """Assemble policies from RAW declarations, refusing duplicates.

    The rejection has to happen here rather than over the assembled collection: iterating a set,
    dict or deduped list can never reveal a duplicate, because the collection has already collapsed
    it. A policy silently shadowing another would be invisible downstream.
    """
    registry: dict[tuple[str, str], StreamPolicy] = {}
    for source, stream, triggers in declarations:
        key = (source, stream)
        if key in registry:
            raise CadenceError(
                f"duplicate policy declaration for {source}.{stream}: a stream may be declared once"
            )
        validate_triggers(triggers)
        registry[key] = StreamPolicy(
            source=source,
            stream=stream,
            triggers=tuple(triggers),
            coverage_basis=_coverage_basis(source, stream),
            window=_window_for(source, stream),
        )
    return registry


def _coverage_basis(source: str, stream: str) -> str:
    if (source, stream) == ("playerprofiler", "medical"):
        return CONTIGUOUS
    return VENDOR_OFFER


def _window_for(source: str, stream: str) -> Optional[str]:
    if source != "pff":
        return None
    league = stream.split("_", 1)[0]
    return _LEAGUE_WINDOW.get(league)


def validate_triggers(triggers: Sequence[str]) -> None:
    unknown = set(triggers) - OBSERVABLE_TRIGGERS
    if unknown:
        raise CadenceError(
            f"triggers {sorted(unknown)} are not observable event windows; no governed push signal "
            "exists for these vendors"
        )


def _declarations() -> list[tuple[str, str, tuple[str, ...]]]:
    """The shipped declarations.

    `player_season` carries FOUR triggers, not one. Measured: 322 columns, of which 134 are per-game
    or cumulative and 38 are prospect/combine derivatives (breakout_age, agility_score, bench_press,
    college). It genuinely moves on the game week, at season end, at the combine, and through the
    draft cycle.
    """
    weekly = ("game_week_complete", "season_final")
    out: list[tuple[str, str, tuple[str, ...]]] = [
        ("playerprofiler", "gamelog", weekly),
        ("playerprofiler", "pbp", weekly),
        ("playerprofiler", "player_season",
         ("game_week_complete", "season_final", "combine_complete", "draft_complete")),
        ("playerprofiler", "roster", ("league_year_open", "draft_complete")),
        ("playerprofiler", "medical", ("operator_drop",)),
        ("pff", "grades", weekly),
        # RotoViz and Campus2Canton hold nothing and have no marker. No stream detail is invented:
        # a single `export` stream stands in until a first-drop inventory exists.
        ("rotoviz", "export", ("operator_drop",)),
        ("campus2canton", "export", ("operator_drop",)),
    ]
    for league in ("nfl", "ncaa"):
        for family in _PFF_FAMILIES:
            out.append(("pff", f"{league}_{family}", weekly))
    return out


_REGISTRY: dict[tuple[str, str], StreamPolicy] = build_policy_registry(_declarations())


def streams_for(source: str) -> tuple[str, ...]:
    return tuple(stream for (src, stream) in _REGISTRY if src == source)


def policy_for(source: str, stream: str) -> Optional[StreamPolicy]:
    return _REGISTRY.get((source, stream))


def stream_disposition(source: str, stream: str) -> StreamDisposition:
    """What we may do with a stream.

    PFF grades are barred as MODEL INPUTS by shipped contracts (source_registry, engine_a_contract,
    head_b_contract, with enforcing tests). That is a rule about USE. It says nothing about
    ACQUISITION: David's instruction is to refresh manual datapoints not covered by other sources
    every time they change, and grades are proprietary constructs with no counterpart in any
    automated source. So ingestion is authorized and the refresh obligation stands, while model use
    stays forbidden and the raw payload is retained.
    """
    is_grades = (source, stream) == ("pff", "grades")
    return StreamDisposition(
        source=source,
        stream=stream,
        model_use_forbidden=is_grades,
        retained_raw=True,
        ingestion_authorized=True,
        creates_refresh_obligation=policy_for(source, stream) is not None,
        consumer_authorized=False,
    )


# --------------------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------------------


def _ts(value: Any, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise CadenceError(f"{field_name} is not an ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise CadenceError(f"{field_name} must be timezone-aware; got naive {value!r}")
    return parsed.astimezone(timezone.utc)


def _game_week_completions(calendar: Mapping[str, Any]) -> list[datetime]:
    """Declared completion instants for each regular-season week.

    These are FACTS the calendar must supply. An earlier version manufactured them as
    `week1_kickoff + 4 days + 7n` — a timer approximation dressed as an observable event. That is
    exactly the failure this module exists to prevent: a computed clock is not evidence that a week
    finished, and a schedule with a flexed or postponed game makes the arithmetic simply wrong.

    When the calendar declares none, no game-week event can be derived and the streams that depend
    on one report `undetermined` rather than inventing a completion.
    """
    declared = calendar.get("game_week_completions")
    if not declared:
        return []
    return [_ts(v, field_name="game_week_completions[]") for v in declared]


def _last_event(
    policy: StreamPolicy,
    now: datetime,
    calendar: Mapping[str, Any],
    offer: Optional[Mapping[str, Any]],
    availability: Optional[Mapping[str, Any]],
) -> tuple[Optional[datetime], Optional[str]]:
    """The most recent observable event on or before `now` that this stream responds to."""
    candidates: list[tuple[datetime, str]] = []

    if "game_week_complete" in policy.triggers:
        if availability and policy.window and policy.window in availability:
            # An explicit availability fact overrides the derived completion: the export does not
            # exist until the vendor publishes it, and NFL and FBS publish on different clocks.
            published = _ts(availability[policy.window]["available_at"], field_name="available_at")
            if published <= now:
                candidates.append((published, "game_week_complete"))
        else:
            for moment in _game_week_completions(calendar):
                if moment <= now:
                    candidates.append((moment, "game_week_complete"))

    for trigger, key in (
        ("season_final", "final_game"),
        ("league_year_open", "league_year_open"),
        ("draft_complete", "draft_complete"),
        ("combine_complete", "combine_complete"),
    ):
        if trigger in policy.triggers and key in calendar:
            moment = _ts(calendar[key], field_name=key)
            if moment <= now:
                candidates.append((moment, trigger))

    # A vendor notice, and an OPERATOR DROP, are events in their own right — each carried on the
    # observation's provenance. `operator_drop` was previously declared as the only trigger for
    # medical, RotoViz and Campus2Canton while `_last_event` never handled it, so their sole trigger
    # was inert and a genuinely newer drop could never register as due.
    if offer:
        provenance = str(offer.get("provenance") or "")
        if provenance.endswith("_manifest"):
            provenance = provenance[: -len("_manifest")]
        # A CORRECTION-CLASS notice is universal: any stream can be told its settled history was
        # republished, and no stream needs to pre-declare that it might be. An OPERATOR DROP is
        # stream-specific — it only counts where the policy declares it. Gating BOTH on declared
        # triggers (my first attempt at this fix) silently disabled correction notices for every PFF
        # lane, because those lanes declare only game_week_complete and season_final.
        eventful = HISTORY_CORRECTION_TRIGGERS | ({"operator_drop"} & set(policy.triggers))
        if provenance in eventful and provenance in OBSERVABLE_TRIGGERS:
            observed = _ts(offer["observed_at"], field_name="observed_at")
            if observed <= now:
                candidates.append((observed, provenance))

    if not candidates:
        return None, None
    return max(candidates, key=lambda pair: pair[0])


def _in_active_window(
    policy: StreamPolicy,
    now: datetime,
    calendar: Mapping[str, Any],
    availability: Optional[Mapping[str, Any]] = None,
) -> bool:
    """Whether this stream is inside a period during which its triggers can fire at all.

    An explicit availability fact GATES this. Between a game finishing and the vendor publishing,
    the export does not exist yet, so nothing can change and nothing is owed — that is `not_due`,
    not `current`. Claiming `current` there would assert we hold the newest the source can offer
    while the source has not offered it.
    """
    if "game_week_complete" not in policy.triggers:
        return False
    if availability and policy.window and policy.window in availability:
        published = _ts(availability[policy.window]["available_at"], field_name="available_at")
        if published > now:
            return False
    kickoff = _ts(calendar["week1_kickoff"], field_name="week1_kickoff")
    final = _ts(calendar["final_game"], field_name="final_game")
    return kickoff <= now <= final


# --------------------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------------------


def _coverage(
    policy: StreamPolicy,
    held: Optional[Mapping[str, Any]],
    offer: Optional[Mapping[str, Any]],
    calendar: Mapping[str, Any],
) -> tuple[str, tuple[int, ...]]:
    if held is None or offer is None:
        return UNKNOWN, ()

    held_seasons = {int(s) for s in held.get("covered_seasons", [])}
    offered = {int(s) for s in offer.get("covered_seasons", [])}

    if policy.coverage_basis == CONTIGUOUS:
        season = int(calendar["season"])
        if not held_seasons:
            return UNKNOWN, ()
        expected = set(range(min(held_seasons), season + 1))
    else:
        expected = offered

    missing = tuple(sorted(expected - held_seasons))
    return (INADEQUATE if missing else ADEQUATE), missing


# --------------------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------------------


def evaluate_stream(
    *,
    source: str,
    stream: str,
    now: datetime,
    calendar: Mapping[str, Any],
    held: Optional[Mapping[str, Any]],
    offer: Optional[Mapping[str, Any]] = None,
    availability: Optional[Mapping[str, Any]] = None,
) -> StreamState:
    policy = policy_for(source, stream)
    if policy is None:
        raise CadenceError(f"no policy declared for {source}.{stream}")

    if offer is not None:
        for required in ("observed_at", "provenance"):
            if not str(offer.get(required) or "").strip():
                raise CadenceError(
                    f"{source}.{stream}: an offer must carry {required}. No governed push signal "
                    "exists, so a bare claim about what the vendor publishes is not evidence."
                )
        observed = _ts(offer["observed_at"], field_name="observed_at")
        if observed > now:
            raise CadenceError(
                f"{source}.{stream}: offer observed_at {observed.isoformat()} is AFTER the "
                f"evaluation instant {now.isoformat()}; evidence from the future is not evidence"
            )

    coverage, missing = _coverage(policy, held, offer, calendar)

    if held is None:
        # No inventory exists, so no obligation can be computed. `not_due` would assert that nothing
        # is owed, which is a claim we cannot support.
        return StreamState(source, stream, UNDETERMINED, coverage, None, missing, None)

    ingested = _ts(held["ingested_at"], field_name="ingested_at")
    age_days = round((now - ingested).total_seconds() / 86400.0, 3)
    event_at, trigger = _last_event(policy, now, calendar, offer, availability)

    if event_at is not None and event_at > ingested:
        return StreamState(source, stream, DUE, coverage, age_days, missing, trigger)

    # NO GOVERNED EVENT EVIDENCE means the obligation is UNCOMPUTABLE, not satisfied. A
    # game-week-driven stream evaluated mid-season with no declared completions previously reported
    # CURRENT — asserting we hold the newest the source can offer while having no way to know
    # whether a week had even finished. Absence of evidence is not evidence of currency.
    if (
        "game_week_complete" in policy.triggers
        and not calendar.get("game_week_completions")
        and not (availability and policy.window and policy.window in availability)
    ):
        kickoff = _ts(calendar["week1_kickoff"], field_name="week1_kickoff")
        final = _ts(calendar["final_game"], field_name="final_game")
        if kickoff <= now <= final:
            return StreamState(source, stream, UNDETERMINED, coverage, age_days, missing, None)

    if _in_active_window(policy, now, calendar, availability):
        return StreamState(source, stream, CURRENT, coverage, age_days, missing, None)
    return StreamState(source, stream, NOT_DUE, coverage, age_days, missing, None)


def evaluate_source(
    *,
    source: str,
    now: datetime,
    calendar: Mapping[str, Any],
    held: Optional[Mapping[str, Any]] = None,
    offer: Optional[Mapping[str, Any]] = None,
    availability: Optional[Mapping[str, Any]] = None,
) -> dict[str, StreamState]:
    """Per-stream states. There is deliberately no collapsed per-source verdict here: streams of one
    source genuinely disagree, and a single value cannot be honest for all of them."""
    held = held or {}
    offer = offer or {}
    return {
        stream: evaluate_stream(
            source=source, stream=stream, now=now, calendar=calendar,
            held=held.get(stream), offer=offer.get(stream), availability=availability,
        )
        for stream in streams_for(source)
    }


def _rollup_cadence(states: Iterable[StreamState]) -> str:
    """A source rollup may never be quieter than its least-known stream.

    `due` and `current` are POSITIVE facts and govern when present. But a mix of `not_due` and
    `undetermined` previously rolled up to `not_due` — turning "we do not know whether anything is
    owed for three streams" into "nothing is owed", which is exactly the false reassurance the four
    states exist to prevent. Absent a governing positive fact, unknown obligation stays UNDETERMINED.
    """
    values = [s.cadence for s in states]
    if not values:
        return UNDETERMINED
    if DUE in values:
        return DUE
    if CURRENT in values:
        return CURRENT
    if UNDETERMINED in values:
        return UNDETERMINED
    return NOT_DUE


def _rollup_coverage(states: Iterable[StreamState]) -> str:
    values = [s.coverage for s in states]
    if INADEQUATE in values:
        return INADEQUATE
    if UNKNOWN in values:
        return UNKNOWN
    return ADEQUATE


def build_report(
    *,
    now: datetime,
    calendar: Mapping[str, Any],
    held: Optional[Mapping[str, Mapping[str, Any]]] = None,
    offer: Optional[Mapping[str, Mapping[str, Any]]] = None,
    availability: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """One report over every declared stream of every manual source.

    Every DECLARED stream is serialized even when it holds nothing — omitting it is how a gap
    becomes invisible. A coverage problem is never a run failure: marking one would make a real
    transport failure indistinguishable from a vendor gap we cannot fix.
    """
    held = held or {}
    offer = offer or {}
    report: dict[str, Any] = {}
    for source in MANUAL_SOURCES:
        states = evaluate_source(
            source=source, now=now, calendar=calendar,
            held=held.get(source), offer=offer.get(source), availability=availability,
        )
        report[source] = {
            "streams": {name: state.as_dict() for name, state in states.items()},
            "cadence": _rollup_cadence(states.values()),
            "coverage": _rollup_coverage(states.values()),
            "failed": False,
        }
    return report
