"""RED — per-stream manual-feed cadence: TWO INDEPENDENT AXES.

David's question, 2026-08-08: "why are my manual ones due? look at the data - what could possibly
have changed?" Then: "identify what data in the manual feeds are not covered by other data sources
and how often those datapoints change - we need to refresh the manual datapoints that are not
covered by other data sources everytime they change."

THE MEASURED ANSWER THAT SHAPED THIS CONTRACT
  * PFF and PlayerProfiler read `due` at ~7 days while holding season-complete data through 2025.
    No IN-SCOPE 2026 REGULAR-SEASON event has occurred yet, so no 2026 regular-season gamelog,
    grade, or snap count can exist. (Preseason games ARE played in August; they are simply not an
    in-scope trigger for these streams. "The season has not kicked off" was imprecise.) Our own
    importer returned `unchanged` for all six gamelog and all six pbp seasons on 2026-08-01.
  * PlayerProfiler is NOT one thing. In the SAME import run, gamelog and pbp returned `unchanged`
    while roster returned `inserted`.
  * pp_medical_history stops at 2023 while gamelog runs to 2025 — a 2024-2026 blind window.
  * Neither vendor exposes a governed push signal, so "every time they change" is achievable only
    at OBSERVABLE EVENT WINDOWS.

TWO AXES, NOT ONE STATE. An earlier draft of this file used a single exclusive state and asserted
that INADEQUATE "outranks" NOT_DUE. That was wrong and it destroyed information: medical history is
BOTH not-due (no observable event is pending) AND inadequate (a three-season hole). Collapsing them
forces a false choice between "nothing to do" and "your data is incomplete", when David needs both
facts. Cadence and coverage are independent and BOTH serialize.

    CADENCE  : current | due | not_due | undetermined  — is an acquisition owed right now?
    COVERAGE : adequate | unknown | inadequate          — is what we hold materially complete?

ALIGNED ACROSS THREE LANES (Claude · Codex · Gemini), 2026-08-08. Claims of mine measured WRONG in
that debate and NOT encoded here: 92-of-149 PFF payloads as college (it is 76 NCAA / 73 NFL); medical
as event-driven year-round (it is coverage-inadequate); PFF as wholly unique (a column-NAME
comparison overstated it — a value-join found basic weekly totals 99.2-100% equal to nflverse); and
that no rule bars PFF grades from models (source_registry.py:170-174, engine_a_contract.py:59-64 and
head_b_contract.py:86-88 bar them as MODEL INPUTS, while raw retention and diagnostic review remain
allowed).

DELIBERATELY OUT OF SCOPE: any GREEN, scheduler install, automated acquisition, provider contact,
paid action, normalized/query store, consumer rewiring, or promotion of PFF grades to a model
surface. RotoViz and Campus2Canton hold no data and no marker, so NO stream detail is invented for
them here — cadence for those is unknowable until a first-drop inventory exists.

The module under test does not exist. Every test that exercises it FAILS — it does not skip.
"""
from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest

MODULE = "src.dynasty_genius.sources.feed_cadence"

#: AXIS 1 — cadence obligation. `undetermined` is NOT a synonym for not_due: it means we cannot yet
#: compute an obligation at all, because no inventory of the source exists. RotoViz and
#: Campus2Canton hold no data and no marker, so their cadence is genuinely uncomputable — saying
#: not_due would assert that nothing is owed, which we do not know.
CURRENT, DUE, NOT_DUE, UNDETERMINED = "current", "due", "not_due", "undetermined"
CADENCE_STATES = frozenset({CURRENT, DUE, NOT_DUE, UNDETERMINED})

#: AXIS 2 — coverage quality. Independent of cadence; both are always reported.
ADEQUATE, UNKNOWN, INADEQUATE = "adequate", "unknown", "inadequate"
COVERAGE_STATES = frozenset({ADEQUATE, UNKNOWN, INADEQUATE})

#: F5 — the trigger ontology is pinned HERE, in the test, as a literal. Asserting only that a
#: policy's triggers are members of the module's own allowed set is self-certifying: a GREEN could
#: add "vendor_push" to that set and pass while implementing exactly the fictional push signal the
#: contract exists to forbid. Neither vendor exposes a governed push.
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

#: R2/C1 — membership in the allowed set does NOT prove correct assignment: a GREEN could hand every
#: stream `operator_drop` and satisfy a membership check. Nor is a map "total" if it is total only
#: against the MODULE's own declarations — a GREEN could then simply declare fewer families. So the
#: EXPECTED KEY SET is enumerated HERE, independently, and equality with the declared set is
#: required.
#:
#: MEASURED from app/data/pff_exports/pff_unique_payload_inventory.csv: 7 report families across 2
#: leagues = 14 league-report lanes. An earlier draft named only 3 of them.
_PFF_FAMILIES = (
    "passing_depth", "passing_pressure", "passing_summary",
    "receiving_depth", "receiving_scheme", "receiving_summary", "rushing_summary",
)

#: NFL and FBS publish on different clocks, so the league prefix must survive into the stream key —
#: collapsing the 14 lanes to 7 families would erase the window distinction S7d pins.
EXPECTED_STREAM_KEYS: frozenset[tuple[str, str]] = frozenset(
    # `("pff", "grades")` WAS PINNED HERE AND NAMED NO FEED. Measured topology: the PFF store holds
    # exactly 7 families x 2 leagues = 14 payload directories and NO grades directory in either
    # league; every "grades" occurrence in the schema catalog is a COLUMN NAME inside those 14
    # lanes. It was a phantom stream — weekly triggers, no league identity — and it could not be
    # league-scoped because there was nothing to scope. Removed under Codex ruling
    # league_scoped_events_red_clear_codex_v1. Grade fields refresh when their containing lane does.
    {("pff", f"{league}_{fam}") for league in ("nfl", "ncaa") for fam in _PFF_FAMILIES}
    | {
        ("playerprofiler", "gamelog"),
        ("playerprofiler", "pbp"),
        ("playerprofiler", "player_season"),
        ("playerprofiler", "roster"),
        ("playerprofiler", "medical"),
    }
)

#: Per-stream REQUIRED triggers. Season-long PFF lanes accrue weekly and settle at season end.
#: `player_season` is NOT season-only: measured, it carries 134 per-game columns AND 38
#: prospect/combine columns (breakout_age, agility_score, bench_press, college...), so it moves on
#: the game week, at season end, at the combine, and through the draft cycle.
REQUIRED_TRIGGERS: dict[tuple[str, str], frozenset[str]] = {
    **{("pff", f"{league}_{fam}"): frozenset({"game_week_complete", "season_final"})
       for league in ("nfl", "ncaa") for fam in _PFF_FAMILIES},
    ("playerprofiler", "gamelog"): frozenset({"game_week_complete", "season_final"}),
    ("playerprofiler", "pbp"): frozenset({"game_week_complete", "season_final"}),
    ("playerprofiler", "player_season"): frozenset({
        "game_week_complete", "season_final", "combine_complete", "draft_complete",
    }),
    ("playerprofiler", "roster"): frozenset({"league_year_open", "draft_complete"}),
    ("playerprofiler", "medical"): frozenset({"operator_drop"}),
}

#: Completed history reopens ONLY on one of these. Time passing is never a trigger.
HISTORY_CORRECTION_TRIGGERS = frozenset({
    "vendor_correction_notice", "schema_change", "methodology_change", "pre_analysis_hash_check",
})


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - this IS the red state
        pytest.fail(f"{MODULE} does not exist yet (RED): {exc}")


def _at(iso: str) -> datetime:
    """An INJECTED evaluation instant. Nothing here reads the wall clock."""
    return datetime.fromisoformat(iso).astimezone(timezone.utc)


#: Injected calendar. `prior_final_game` exists because a standalone fixture check caught that
#: `final_game` (2027-01-04) is the END of the 2026 season and therefore in the FUTURE relative to an
#: August 2026 instant — with only that key the offseason window was unexpressible.
CAL_2026 = {
    "season": 2026,
    "prior_final_game": "2026-01-05T20:20:00-05:00",
    "league_year_open": "2026-03-11T16:00:00-04:00",
    "draft_complete": "2026-04-25T19:00:00-04:00",
    # COMPETITION-SCOPED GAME FACTS. These were flat, and the engine read them globally, so NFL
    # completions marked NCAA lanes due and the NFL season being underway marked them current. The
    # three facts are scoped together; there is no flat fallback.
    #
    # FBS carries its OWN dates rather than a copy of the NFL block. Copying would make every test
    # here pass identically whether the engine scoped correctly or leaked, which is the property
    # these fixtures should never have.
    "competitions": {
        "nfl": {
            "week1_kickoff": "2026-09-10T20:20:00-04:00",
            "final_game": "2027-01-04T20:20:00-05:00",
            # F4 — DECLARED completion facts, not a computed timer. An earlier implementation
            # manufactured these as kickoff + 4 days + 7n, which is arithmetic dressed as an
            # observable event and is simply wrong for a flexed or postponed game.
            "game_week_completions": [
                "2026-09-14T23:30:00-04:00",   # week 1
                "2026-09-21T23:30:00-04:00",   # week 2
                "2026-09-28T23:30:00-04:00",   # week 3
            ],
        },
        "fbs": {
            # The FBS season genuinely opens earlier and closes later than the NFL's.
            "week1_kickoff": "2026-08-29T19:00:00-04:00",
            "final_game": "2027-01-11T19:30:00-05:00",
            "game_week_completions": [
                "2026-09-13T23:30:00-04:00",
                "2026-09-20T23:30:00-04:00",
                "2026-09-27T23:30:00-04:00",
            ],
        },
    },
}

#: F3 — what the VENDOR offers is an observation with provenance, never a bare oracle. Since no
#: governed push signal exists, an offer claim must carry when and how it was observed.
def _offer(newest: int, covered: tuple[int, ...], *, observed_at: str, provenance: str) -> dict:
    return {
        "newest_season": newest,
        "covered_seasons": list(covered),
        "observed_at": observed_at,
        "provenance": provenance,
    }


def _held(newest: int, covered: tuple[int, ...], *, ingested_at: str) -> dict:
    return {"newest_season": newest, "covered_seasons": list(covered), "ingested_at": ingested_at}


SEASONS_20_25 = (2020, 2021, 2022, 2023, 2024, 2025)


# ================== S1 — two closed vocabularies, independently ===================


def test_s1_cadence_and_coverage_are_separate_closed_vocabularies():
    m = _mod()
    assert set(m.CADENCE_STATES) == CADENCE_STATES
    assert set(m.COVERAGE_STATES) == COVERAGE_STATES
    assert not (set(m.CADENCE_STATES) & set(m.COVERAGE_STATES)), (
        "the axes must not share a name; a shared token invites collapsing them again"
    )


def test_s1b_every_result_serializes_BOTH_axes():
    """F1 — neither axis may be omitted or inferred from the other."""
    m = _mod()
    r = m.evaluate_stream(
        source="playerprofiler", stream="medical",
        now=_at("2026-06-15T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023), ingested_at="2026-06-01T00:00:00+00:00"),
        offer=_offer(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023),
                     observed_at="2026-06-01T00:00:00+00:00", provenance="operator_drop_manifest"),
    )
    payload = r.as_dict()
    assert payload["cadence"] in CADENCE_STATES
    assert payload["coverage"] in COVERAGE_STATES


def test_s1c_medical_is_BOTH_not_due_AND_inadequate_at_the_same_instant():
    """F1, the case that proves the axes must be independent. In the deep offseason no acquisition
    is owed, AND the archive has a three-season hole. Reporting only one erases the other."""
    m = _mod()
    r = m.evaluate_stream(
        source="playerprofiler", stream="medical",
        now=_at("2026-06-15T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023), ingested_at="2026-06-01T00:00:00+00:00"),
        offer=_offer(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023),
                     observed_at="2026-06-01T00:00:00+00:00", provenance="operator_drop_manifest"),
    )
    assert r.cadence == NOT_DUE, "no observable event is pending in June"
    assert r.coverage == INADEQUATE, "2024-2026 is unrepresented and that must not be hidden"


# ================== S2 — per-stream disagreement, non-vacuously =====================


def test_s2_streams_of_one_source_GENUINELY_DISAGREE_at_one_instant():
    """F2. The previous version asserted `len({states}) >= 1`, which is TRUE for any non-empty
    input — it passed with all three streams identical and therefore asserted nothing. This pins the
    EXPECTED state of each stream and requires at least two DISTINCT cadence values, driven by an
    injected league-year-open event that post-dates the roster vintage.
    """
    m = _mod()
    now = _at("2026-03-20T09:00:00-04:00")   # after league_year_open, before the draft
    frozen = dict(ingested_at="2026-02-01T00:00:00+00:00")
    states = m.evaluate_source(
        source="playerprofiler", now=now, calendar=CAL_2026,
        held={
            "gamelog": _held(2025, SEASONS_20_25, **frozen),
            "pbp": _held(2025, SEASONS_20_25, **frozen),
            "roster": _held(2025, SEASONS_20_25, **frozen),
        },
        offer={
            "gamelog": _offer(2025, SEASONS_20_25, observed_at="2026-03-20T00:00:00+00:00",
                              provenance="vendor_export_manifest"),
            "pbp": _offer(2025, SEASONS_20_25, observed_at="2026-03-20T00:00:00+00:00",
                          provenance="vendor_export_manifest"),
            "roster": _offer(2026, SEASONS_20_25 + (2026,), observed_at="2026-03-20T00:00:00+00:00",
                             provenance="vendor_export_manifest"),
        },
    )
    assert states["gamelog"].cadence == NOT_DUE, "no games since January"
    assert states["pbp"].cadence == NOT_DUE
    assert states["roster"].cadence == DUE, "league year opened 2026-03-11; roster moved"
    distinct = {s.cadence for s in states.values()}
    assert len(distinct) >= 2, (
        f"the whole point of per-stream evaluation is that streams DISAGREE; got {distinct}"
    )


def test_s2b_every_stream_has_exactly_one_policy():
    """Partition, not a count."""
    m = _mod()
    for source in m.MANUAL_SOURCES:
        for stream in m.streams_for(source):
            assert m.policy_for(source, stream) is not None


def test_s2c_duplicate_declarations_are_rejected_at_CONSTRUCTION():
    """R5 — iterating `streams_for()` can never reveal a duplicate if that function returns a set,
    dict or deduped list: the collection has already collapsed them. The rejection has to happen
    where the RAW DECLARATIONS are assembled, so a policy silently shadowing another is impossible.
    """
    m = _mod()
    dupes = [
        ("playerprofiler", "roster", ("league_year_open",)),
        ("playerprofiler", "roster", ("draft_complete",)),
    ]
    with pytest.raises(m.CadenceError) as exc:
        m.build_policy_registry(dupes)
    assert "roster" in str(exc.value), f"the duplicated key must be named; got {exc.value}"


# ============ S3 — cadence: offseason quiet, in-season event-driven ===============


@pytest.mark.parametrize("stream", ["gamelog", "pbp", "player_season"])
def test_s3_frozen_stat_streams_are_not_due_in_the_offseason(stream):
    m = _mod()
    r = m.evaluate_stream(
        source="playerprofiler", stream=stream,
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2025, SEASONS_20_25, ingested_at="2026-08-01T13:36:41+00:00"),
        offer=_offer(2025, SEASONS_20_25, observed_at="2026-08-01T13:36:41+00:00",
                     provenance="vendor_export_manifest"),
    )
    assert r.cadence == NOT_DUE
    assert r.coverage == ADEQUATE, "holding everything the vendor offers is adequate"
    assert r.age_days is not None, "age is still reported; it is simply not an obligation"


def test_s3b_a_completed_game_week_makes_the_same_stream_due():
    """Counter-test so S3 cannot pass vacuously. NOTE: no universal weekday is encoded. The trigger
    is game_week_complete, derived from the calendar — an earlier draft called 2026-09-16 'Tuesday'
    when it is a WEDNESDAY, which is exactly why a weekday literal has no place in this contract."""
    m = _mod()
    r = m.evaluate_stream(
        source="playerprofiler", stream="gamelog",
        now=_at("2026-09-16T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2025, SEASONS_20_25, ingested_at="2026-09-01T00:00:00+00:00"),
        offer=_offer(2026, SEASONS_20_25 + (2026,), observed_at="2026-09-16T08:00:00+00:00",
                     provenance="vendor_export_manifest"),
    )
    assert r.cadence == DUE
    assert r.trigger == "game_week_complete", f"the reason must be named; got {r.trigger!r}"


# ============ S4 — coverage: completeness, not recency, not newest-only ===========


def test_s4_coverage_gap_is_named_and_survives_a_fresh_reingest():
    m = _mod()
    held = _held(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023), ingested_at="2026-08-08T08:59:00+00:00")
    r = m.evaluate_stream(
        source="playerprofiler", stream="medical",
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026, held=held,
        offer=_offer(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023),
                     observed_at="2026-08-08T08:00:00+00:00", provenance="operator_drop_manifest"),
    )
    assert r.coverage == INADEQUATE, "re-ingesting the same stale archive must not clear it"
    assert r.missing_seasons == (2024, 2025, 2026), f"the hole must be enumerated; got {r.missing_seasons}"


def test_s4b_INTERIOR_gaps_are_caught_which_newest_season_alone_cannot_see():
    """F4. Holding 2023 AND 2026 while missing 2024-2025 has newest_season == the vendor's newest,
    so a newest-only comparison reports adequate while two seasons are absent."""
    m = _mod()
    r = m.evaluate_stream(
        source="playerprofiler", stream="gamelog",
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2026, (2022, 2023, 2026), ingested_at="2026-08-01T00:00:00+00:00"),
        offer=_offer(2026, (2022, 2023, 2024, 2025, 2026), observed_at="2026-08-01T00:00:00+00:00",
                     provenance="vendor_export_manifest"),
    )
    assert r.coverage == INADEQUATE, "newest_season matches, but 2024 and 2025 are missing"
    assert r.missing_seasons == (2024, 2025)


def test_s4d_held_STRICT_SUPERSET_of_offered_remains_adequate():
    """R7. We may hold seasons the vendor no longer publishes. Requiring exact equality would
    license an implementation to read those as a defect and PRUNE them — a data-destroying reading
    of a completeness check. Retention is never a coverage failure."""
    m = _mod()
    r = m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary",
        now=_at("2026-06-15T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2025, (2015, 2016, 2017, 2024, 2025), ingested_at="2026-01-10T00:00:00+00:00"),
        offer=_offer(2025, (2017, 2024, 2025), observed_at="2026-06-01T00:00:00+00:00",
                     provenance="vendor_export_manifest"),
    )
    assert r.coverage == ADEQUATE, "holding MORE than the vendor offers is not a gap"
    assert r.missing_seasons == ()


def test_s4e_full_lifecycle_not_due_to_due_to_CURRENT_to_due():
    """R2. `current` was never behaviourally asserted — only adequate/not_due were. This walks the
    whole cadence lifecycle across an event, an ingest, and the NEXT event."""
    m = _mod()
    common = dict(source="playerprofiler", stream="gamelog", calendar=CAL_2026)
    frozen = _held(2025, SEASONS_20_25, ingested_at="2026-09-01T00:00:00+00:00")
    pre = m.evaluate_stream(now=_at("2026-09-09T09:00:00-04:00"), held=frozen,
                            offer=_offer(2025, SEASONS_20_25, observed_at="2026-09-09T00:00:00+00:00",
                                         provenance="vendor_export_manifest"), **common)
    assert pre.cadence == NOT_DUE, "before kickoff nothing has been played"

    after_wk1 = _offer(2026, SEASONS_20_25 + (2026,), observed_at="2026-09-16T08:00:00+00:00",
                       provenance="vendor_export_manifest")
    due = m.evaluate_stream(now=_at("2026-09-16T09:00:00-04:00"), held=frozen, offer=after_wk1, **common)
    assert due.cadence == DUE, "a completed game week is an observable event"

    ingested = _held(2026, SEASONS_20_25 + (2026,), ingested_at="2026-09-16T12:00:00+00:00")
    now_current = m.evaluate_stream(now=_at("2026-09-16T13:00:00-04:00"), held=ingested,
                                    offer=after_wk1, **common)
    assert now_current.cadence == CURRENT, (
        "after ingesting what the event produced, the stream is CURRENT — not merely not_due"
    )
    assert now_current.coverage == ADEQUATE

    after_wk2 = _offer(2026, SEASONS_20_25 + (2026,), observed_at="2026-09-23T08:00:00+00:00",
                       provenance="vendor_export_manifest")
    again = m.evaluate_stream(now=_at("2026-09-23T09:00:00-04:00"), held=ingested, offer=after_wk2, **common)
    assert again.cadence == DUE, "the NEXT game week reopens the obligation"


def test_s4c_coverage_is_adequate_when_the_held_set_matches_what_is_offered():
    m = _mod()
    r = m.evaluate_stream(
        source="playerprofiler", stream="medical",
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2026, (2024, 2025, 2026), ingested_at="2026-08-08T08:59:00+00:00"),
        offer=_offer(2026, (2024, 2025, 2026), observed_at="2026-08-08T08:00:00+00:00",
                     provenance="operator_drop_manifest"),
    )
    assert r.coverage == ADEQUATE
    assert r.missing_seasons == ()


# ============ S5 — the offer is an observation, never an oracle ===================


def test_s5_an_offer_without_provenance_is_refused():
    """F3. No governed push signal exists, so a bare claim about what the vendor offers cannot be
    trusted. It must carry when and how it was observed."""
    m = _mod()
    with pytest.raises(m.CadenceError):
        m.evaluate_stream(
            source="playerprofiler", stream="gamelog",
            now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026,
            held=_held(2025, SEASONS_20_25, ingested_at="2026-08-01T00:00:00+00:00"),
            offer={"newest_season": 2026, "covered_seasons": [2026]},   # no observed_at/provenance
        )


def test_s5b_no_offer_observation_yields_UNKNOWN_coverage_not_a_guess():
    m = _mod()
    r = m.evaluate_stream(
        source="playerprofiler", stream="gamelog",
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2025, SEASONS_20_25, ingested_at="2026-08-01T00:00:00+00:00"),
        offer=None,
    )
    assert r.coverage == UNKNOWN, "without an observation we cannot claim completeness"


@pytest.mark.parametrize("source", ["rotoviz", "campus2canton"])
def test_s5c_sources_with_no_held_data_are_unknown_on_both_axes(source):
    """No stream detail is invented for these; they hold nothing and have no marker."""
    m = _mod()
    r = m.evaluate_stream(
        source=source, stream="export",
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026, held=None, offer=None,
    )
    assert r.coverage == UNKNOWN, "we hold nothing, so completeness is unknowable"
    assert r.cadence == UNDETERMINED, (
        "cadence is UNCOMPUTABLE without an inventory — not_due would assert nothing is owed, "
        "which we do not know"
    )
    assert r.age_days is None, "absence must never carry an invented age"


# ============ S6 — trigger ontology pinned in the TEST, not self-certified ========


def test_s6_every_policy_trigger_is_in_the_TEST_PINNED_ontology():
    """F5. Asserting membership in the module's own set lets a GREEN add `vendor_push` and pass."""
    m = _mod()
    for source in m.MANUAL_SOURCES:
        for stream in m.streams_for(source):
            triggers = m.policy_for(source, stream).triggers
            assert triggers, f"{source}.{stream} must declare at least one trigger"
            assert set(triggers) <= OBSERVABLE_TRIGGERS, (
                f"{source}.{stream} declares {set(triggers) - OBSERVABLE_TRIGGERS} which are not "
                "observable event windows"
            )


def test_s6b_a_push_style_trigger_is_rejected_outright():
    m = _mod()
    assert "vendor_push" not in OBSERVABLE_TRIGGERS
    with pytest.raises(m.CadenceError):
        m.validate_triggers(("vendor_push",))


def test_s6c_declared_streams_EQUAL_the_independently_pinned_key_set():
    """C1. A map that is total only against the module's own declarations lets a GREEN declare
    FEWER families and still pass — my previous version checked `declared - mapped` and so was blind
    to omission. The expected keys are enumerated in this file from the MEASURED inventory (7 PFF
    families x 2 leagues = 14 lanes, plus grades, plus five PlayerProfiler streams) and equality is
    required in both directions.
    """
    m = _mod()
    declared = {(s, st) for s in m.MANUAL_SOURCES for st in m.streams_for(s)
                if s in {"pff", "playerprofiler"}}
    assert declared == EXPECTED_STREAM_KEYS, (
        f"missing from the implementation: {sorted(EXPECTED_STREAM_KEYS - declared)}; "
        f"unexpected extras: {sorted(declared - EXPECTED_STREAM_KEYS)}"
    )


def test_s6c2_every_stream_carries_its_REQUIRED_triggers_not_merely_allowed_ones():
    """R2. Membership in OBSERVABLE_TRIGGERS proves a trigger is LEGAL, not that it is the RIGHT
    one — a GREEN could assign `operator_drop` everywhere and pass a membership check."""
    m = _mod()
    assert set(REQUIRED_TRIGGERS) == EXPECTED_STREAM_KEYS, (
        "the trigger map must cover exactly the pinned key set, with no stream left unmapped"
    )
    for key, required in sorted(REQUIRED_TRIGGERS.items()):
        actual = set(m.policy_for(*key).triggers)
        assert required <= actual, f"{key}: missing required triggers {sorted(required - actual)}"


def test_s6c3_nfl_and_ncaa_lanes_remain_SEPARATE_keys():
    """C1. Collapsing the 14 lanes to 7 families would erase the NFL-noon vs FBS-08:00 window
    distinction that S7d pins."""
    m = _mod()
    declared = {st for st in m.streams_for("pff")}
    for fam in _PFF_FAMILIES:
        assert f"nfl_{fam}" in declared and f"ncaa_{fam}" in declared, (
            f"{fam} must exist as separate nfl_ and ncaa_ lanes; the publication clocks differ"
        )


def test_s6d_completed_history_reopens_only_on_a_correction_class_trigger():
    """R2. The aligned position was that settled history refreshes on correction, SCHEMA or
    METHODOLOGY notice, or a bounded pre-analysis comparison. Three of those four were missing from
    the ontology entirely."""
    m = _mod()
    assert HISTORY_CORRECTION_TRIGGERS <= OBSERVABLE_TRIGGERS
    assert HISTORY_CORRECTION_TRIGGERS <= set(m.HISTORY_CORRECTION_TRIGGERS)
    assert "game_week_complete" not in m.HISTORY_CORRECTION_TRIGGERS, (
        "a completed season does not reopen because another week was played"
    )


# ============ S7 — PFF cadence, and why grades create no obligation ==============


def test_s7_pff_nfl_family_is_due_after_a_completed_game_week():
    """F6. PFF had no cadence behaviour tested at all in the previous draft."""
    m = _mod()
    r = m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary",
        now=_at("2026-09-16T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2025, (2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025),
                   ingested_at="2026-08-01T00:00:00+00:00"),
        offer=_offer(2026, (2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026),
                     observed_at="2026-09-16T08:00:00+00:00", provenance="vendor_export_manifest"),
    )
    assert r.cadence == DUE
    assert r.trigger == "game_week_complete"


def test_s7b_completed_history_is_refreshed_only_on_a_correction_notice():
    """F6. A settled season does not become due again just because time passed."""
    m = _mod()
    quiet = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-06-15T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2025, (2024, 2025), ingested_at="2026-01-10T00:00:00+00:00"),
        offer=_offer(2025, (2024, 2025), observed_at="2026-06-01T00:00:00+00:00",
                     provenance="vendor_export_manifest"),
    )
    assert quiet.cadence == NOT_DUE
    corrected = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-06-15T09:00:00-04:00"), calendar=CAL_2026,
        held=_held(2025, (2024, 2025), ingested_at="2026-01-10T00:00:00+00:00"),
        offer=_offer(2025, (2024, 2025), observed_at="2026-06-14T00:00:00+00:00",
                     provenance="vendor_correction_notice"),
    )
    assert corrected.cadence == DUE
    assert corrected.trigger == "vendor_correction_notice"


def test_s7c_the_grades_PROHIBITION_is_COLUMN_level_and_survives_the_phantom_removal():
    """R1 — REWRITTEN. This test used to assert the model-input ban through a STREAM that named no
    feed: `stream_disposition("pff", "grades").model_use_forbidden is True`.

    That framing was wrong twice over. The store holds no grades payload, so the flag hung off an
    empty lane; and the grade COLUMNS it was meant to protect against live inside the 14 real
    family lanes, which carried no such flag. The prohibition it appeared to prove was therefore
    largely decorative at the stream level.

    The ENFORCING guards are column-level and independent of the cadence registry. This test now
    asserts those directly, so the ban is proven where it actually operates:
      - engine_a_contract.PROHIBITED_COLUMNS
      - head_b_contract rejects prohibited subjective grade columns by name

    THE BAN IS NOT WEAKENED BY THE REMOVAL — it never depended on the phantom. Removing a lane that
    holds nothing cannot loosen a restriction enforced on column names.
    """
    m = _mod()
    engine_a = importlib.import_module("src.dynasty_genius.models.engine_a_contract")
    head_b = importlib.import_module("src.dynasty_genius.models.head_b_contract")

    assert "pff_grade" in engine_a.PROHIBITED_COLUMNS, "the model-input ban must remain real"
    assert head_b.PFF_GRADE_PROHIBITED_COLUMNS, (
        "Head B must still bar subjective grade columns by name"
    )
    # ...and the ENFORCING function actually rejects one, not merely lists it. A constant nobody
    # consults is documentation, not a guard.
    # PIN THE TYPE AND THE DIAGNOSTIC. `pytest.raises(Exception)` would be satisfied by an
    # ImportError, a TypeError from a changed signature, or any unrelated breakage — it asserts
    # "something went wrong", not "the ban fired".
    sample = sorted(head_b.PFF_GRADE_PROHIBITED_COLUMNS)[0]
    with pytest.raises(ValueError) as exc:
        head_b.check_head_b_feature_leakage([sample])
    assert "prohibited subjective PFF grade column" in str(exc.value), (
        f"the ban must fire for the GRADE reason, not some other leakage rule: {exc.value}"
    )

    # The phantom is gone from the registry.
    assert ("pff", "grades") not in EXPECTED_STREAM_KEYS, "the pin must not resurrect it"
    assert m.policy_for("pff", "grades") is None, "`pff.grades` names no payload lane"
    assert "grades" not in m.streams_for("pff")

    # ...and the 14 REAL lanes remain ingested and retained. Over-correcting the removal into
    # flagging them would suppress legitimate Layer 1 inputs to enforce a column-level rule.
    for stream in m.streams_for("pff"):
        d = m.stream_disposition("pff", stream)
        assert d.model_use_forbidden is False, f"pff.{stream} is a real retained lane"
        assert d.retained_raw is True and d.ingestion_authorized is True
        assert d.creates_refresh_obligation is True


def test_s7d_pff_nfl_and_fbs_availability_windows_are_DISTINCT():
    """R4/R1 — the two leagues publish on different clocks, and NO evaluation may consult an
    observation made AFTER the instant being evaluated.

    An earlier draft supplied one offer observed 2026-09-15T13:00Z to BOTH the NFL checks and the
    FBS checks dated 2026-09-13 — evidence from two days in the future, which would let an
    implementation appear correct while time-travelling. Each evaluation below now carries an offer
    observed at or before its own instant, and the pre-window cases carry the PRE-EXISTING
    observation rather than the post-event one.
    """
    m = _mod()
    avail = {
        "nfl": {"game_end": "2026-09-14T23:30:00-04:00", "available_at": "2026-09-15T12:00:00-04:00"},
        "fbs": {"game_end": "2026-09-12T23:30:00-04:00", "available_at": "2026-09-13T08:00:00-04:00"},
    }
    held = _held(2025, (2024, 2025), ingested_at="2026-09-01T00:00:00+00:00")
    prior = _offer(2025, (2024, 2025), observed_at="2026-09-01T00:00:00+00:00",
                   provenance="vendor_export_manifest")

    # --- FBS: window opens 08:00 on 2026-09-13 ---
    fbs_before = m.evaluate_stream(source="pff", stream="ncaa_receiving_summary",
                                   now=_at("2026-09-13T07:00:00-04:00"), calendar=CAL_2026,
                                   held=held, offer=prior, availability=avail)
    assert fbs_before.cadence == NOT_DUE, "before 08:00 the FBS export does not exist yet"
    fbs_after = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-09-13T09:00:00-04:00"), calendar=CAL_2026, held=held,
        offer=_offer(2026, (2024, 2025, 2026), observed_at="2026-09-13T08:05:00-04:00",
                     provenance="vendor_export_manifest"),
        availability=avail)
    assert fbs_after.cadence == DUE

    # --- NFL: window opens noon on 2026-09-15, two days later ---
    nfl_before = m.evaluate_stream(source="pff", stream="nfl_receiving_summary",
                                   now=_at("2026-09-15T09:00:00-04:00"), calendar=CAL_2026,
                                   held=held, offer=prior, availability=avail)
    assert nfl_before.cadence == NOT_DUE, "before noon the NFL export does not exist yet"
    nfl_after = m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary",
        now=_at("2026-09-15T13:00:00-04:00"), calendar=CAL_2026, held=held,
        offer=_offer(2026, (2024, 2025, 2026), observed_at="2026-09-15T12:05:00-04:00",
                     provenance="vendor_export_manifest"),
        availability=avail)
    assert nfl_after.cadence == DUE
    assert avail["nfl"]["available_at"] != avail["fbs"]["available_at"], (
        "fixture precondition: the two windows genuinely differ"
    )


def test_s7e_an_offer_observed_AFTER_the_evaluation_instant_is_refused():
    """R1 — evidence from the future is not evidence. Without this, a contract can be satisfied by
    an implementation that consults observations it could not have had."""
    m = _mod()
    with pytest.raises(m.CadenceError) as exc:
        m.evaluate_stream(
            source="pff", stream="nfl_receiving_summary",
            now=_at("2026-09-13T09:00:00-04:00"), calendar=CAL_2026,
            held=_held(2025, (2024, 2025), ingested_at="2026-09-01T00:00:00+00:00"),
            offer=_offer(2026, (2024, 2025, 2026), observed_at="2026-09-15T13:00:00-04:00",
                         provenance="vendor_export_manifest"),
        )
    assert "observed_at" in str(exc.value), f"the offending field must be named; got {exc.value}"


# ============ S8 — controller integration, aggregated from real per-stream results ==


def test_s8_manual_entries_stop_carrying_a_flat_daily_refresh_target():
    """STANDING RED BY DESIGN — asserts on the SHIPPED manifest, so it stays red until GREEN."""
    _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    for e in daily_control.build_manifest():
        if e.mode == "manual_download":
            assert e.refresh_target != "daily", (
                f"{e.source}: a manual seasonal source must not carry a flat daily target"
            )


def test_s8b_the_source_report_is_AGGREGATED_from_per_stream_results_not_emptied():
    """F8. Setting refresh_target to None while reporting no streams would satisfy S8 and tell David
    nothing. The report must serialize both axes per stream AND derive the source rollup from them."""
    m = _mod()
    report = m.build_report(
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026,
        held={"playerprofiler": {
            "gamelog": _held(2025, SEASONS_20_25, ingested_at="2026-08-01T13:36:41+00:00"),
            "medical": _held(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023),
                             ingested_at="2026-08-01T13:36:41+00:00"),
        }},
        offer={"playerprofiler": {
            "gamelog": _offer(2025, SEASONS_20_25, observed_at="2026-08-01T13:36:41+00:00",
                              provenance="vendor_export_manifest"),
            "medical": _offer(2023, (2017, 2018, 2019, 2020, 2021, 2022, 2023),
                              observed_at="2026-08-01T13:36:41+00:00", provenance="operator_drop_manifest"),
        }},
    )
    pp = report["playerprofiler"]
    m_streams = set(m.streams_for("playerprofiler"))
    supplied = {"gamelog", "medical"}

    # RULING (Codex, w#4drz4720-1): S8e governs. Partial input must NEVER hide declared streams —
    # an earlier version of this test asserted equality with the SUPPLIED set, which encoded the
    # opposite rule and contradicted S8e's "a stream that is unknown must still APPEAR".
    assert supplied <= set(pp["streams"]), "the supplied streams must appear"
    assert set(pp["streams"]) == m_streams, (
        f"serialized keys must equal streams_for(); missing {sorted(m_streams - set(pp['streams']))}"
    )
    omitted = m_streams - supplied
    assert omitted, "fixture precondition: some declared stream must be unsupplied, or this is vacuous"
    for name in sorted(omitted):
        s = pp["streams"][name]
        assert s["cadence"] == UNDETERMINED, f"{name}: unsupplied must be undetermined, got {s['cadence']}"
        assert s["coverage"] == UNKNOWN, f"{name}: unsupplied must be unknown, got {s['coverage']}"
    for s in pp["streams"].values():
        assert s["cadence"] in CADENCE_STATES and s["coverage"] in COVERAGE_STATES
    assert pp["coverage"] == INADEQUATE, (
        "a source rollup must surface the WORST coverage among its streams, not hide it"
    )
    # F5 — three declared streams are unsupplied and therefore UNDETERMINED. A rollup of
    # not_due + undetermined must not collapse to not_due: that would turn "we cannot tell whether
    # anything is owed" into "nothing is owed", which is the false reassurance the axes prevent.
    assert pp["cadence"] == UNDETERMINED, (
        "unknown obligation must not become quiet certainty at the rollup"
    )


def test_s8c_source_rollup_surfaces_DUE_when_any_stream_is_due():
    """R6 — the coverage rollup was pinned but the cadence rollup was not. A source with one due
    stream must not read as quiet."""
    m = _mod()
    report = m.build_report(
        now=_at("2026-03-20T09:00:00-04:00"), calendar=CAL_2026,
        held={"playerprofiler": {
            "gamelog": _held(2025, SEASONS_20_25, ingested_at="2026-02-01T00:00:00+00:00"),
            "roster": _held(2025, SEASONS_20_25, ingested_at="2026-02-01T00:00:00+00:00"),
        }},
        offer={"playerprofiler": {
            "gamelog": _offer(2025, SEASONS_20_25, observed_at="2026-03-20T00:00:00+00:00",
                              provenance="vendor_export_manifest"),
            "roster": _offer(2026, SEASONS_20_25 + (2026,), observed_at="2026-03-20T00:00:00+00:00",
                             provenance="vendor_export_manifest"),
        }},
    )
    pp = report["playerprofiler"]
    assert pp["streams"]["gamelog"]["cadence"] == NOT_DUE
    assert pp["streams"]["roster"]["cadence"] == DUE
    assert pp["cadence"] == DUE, "one due stream makes the source due; quiet would hide it"


def test_s8d_unknown_and_inadequate_are_NOT_run_failures():
    """R6 — a coverage problem is information for David, not a job failure. Marking it failed would
    make a real transport failure indistinguishable from a vendor gap we cannot fix."""
    m = _mod()
    report = m.build_report(
        now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026,
        held={"playerprofiler": {"medical": _held(2023, (2022, 2023), ingested_at="2026-08-01T00:00:00+00:00")},
              "rotoviz": {"export": None}},
        offer={"playerprofiler": {"medical": _offer(2023, (2022, 2023),
                                                    observed_at="2026-08-01T00:00:00+00:00",
                                                    provenance="operator_drop_manifest")},
               "rotoviz": {"export": None}},
    )
    assert report["playerprofiler"]["streams"]["medical"]["coverage"] == INADEQUATE
    assert report["playerprofiler"]["failed"] is False, "a vendor coverage gap is not a run failure"
    assert report["rotoviz"]["streams"]["export"]["coverage"] == UNKNOWN
    assert report["rotoviz"]["streams"]["export"]["cadence"] == UNDETERMINED
    assert report["rotoviz"]["failed"] is False, "no inventory is not a failure either"


def test_s8e_every_declared_stream_is_serialized_even_when_it_holds_nothing():
    """R6 — a stream that is unknown must still APPEAR. Omitting it is how a gap becomes invisible."""
    m = _mod()
    report = m.build_report(now=_at("2026-08-08T09:00:00-04:00"), calendar=CAL_2026, held={}, offer={})
    for source in m.MANUAL_SOURCES:
        assert source in report, f"{source} missing from the report entirely"
        declared = set(m.streams_for(source))
        serialized = set(report[source]["streams"])
        assert declared == serialized, (
            f"{source}: declared {declared} but serialized {serialized}"
        )


# ============ LIFECYCLE — the four distinguishable phases ==========================


#: The lifecycle fixtures exercise NFL-scoped streams. Scoped, with no flat fallback: an absent
#: competition block is honest missing evidence and resolves to `undetermined`, so the "no
#: completions declared" phase must supply the block WITH an empty list rather than omit it — those
#: are two different facts and the engine answers them differently.
_LC_BASE = {"season": 2026, "competitions": {"nfl": {
    "week1_kickoff": "2026-09-10T20:20:00-04:00",
    "final_game": "2027-01-04T20:20:00-05:00",
    "game_week_completions": []}}}
_LC_WITH = {"season": 2026, "competitions": {"nfl": {
    "week1_kickoff": "2026-09-10T20:20:00-04:00",
    "final_game": "2027-01-04T20:20:00-05:00",
    "game_week_completions": ["2026-09-14T23:30:00-04:00", "2026-09-21T23:30:00-04:00"]}}}


def _lc(calendar, now, ingested, observed):
    m = _mod()
    return m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary",
        now=_at(now), calendar=calendar,
        held=_held(2025, (2025,), ingested_at=ingested),
        offer=_offer(2025, (2025,), observed_at=observed, provenance="vendor_export_manifest"),
    ).cadence


def test_lifecycle_preseason_is_not_due():
    """Before kickoff nothing has been played, so nothing can be owed."""
    assert _lc(_LC_BASE, "2026-08-08T00:00:00+00:00",
               "2026-08-01T00:00:00+00:00", "2026-08-01T00:00:00+00:00") == NOT_DUE


def test_lifecycle_IN_SEASON_WITHOUT_EVENT_EVIDENCE_is_undetermined():
    """The defect this pins: mid-season with NO declared completions, the stream previously reported
    CURRENT — asserting we hold the newest the source can offer while having no way to know whether
    a week had even finished. Absence of evidence is not evidence of currency."""
    assert _lc(_LC_BASE, "2026-10-01T00:00:00+00:00",
               "2026-09-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00") == UNDETERMINED


def test_lifecycle_in_season_before_a_completion_is_current():
    """With completion facts declared and none yet passed since ingest, `current` is a real claim
    backed by evidence — which is what distinguishes it from the case above."""
    assert _lc(_LC_WITH, "2026-09-12T00:00:00+00:00",
               "2026-09-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00") == CURRENT


def test_lifecycle_in_season_after_a_completion_is_due():
    assert _lc(_LC_WITH, "2026-09-16T00:00:00+00:00",
               "2026-09-01T00:00:00+00:00", "2026-09-16T00:00:00+00:00") == DUE


def test_lifecycle_ingesting_after_the_completion_returns_to_current():
    assert _lc(_LC_WITH, "2026-09-18T00:00:00+00:00",
               "2026-09-17T00:00:00+00:00", "2026-09-17T00:00:00+00:00") == CURRENT


def test_lifecycle_phases_are_genuinely_DISTINCT():
    """Guard against the whole lifecycle collapsing to one value — four phases, at least three
    distinct answers, or these tests would pass together while proving nothing."""
    phases = {
        _lc(_LC_BASE, "2026-08-08T00:00:00+00:00", "2026-08-01T00:00:00+00:00", "2026-08-01T00:00:00+00:00"),
        _lc(_LC_BASE, "2026-10-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00"),
        _lc(_LC_WITH, "2026-09-12T00:00:00+00:00", "2026-09-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00"),
        _lc(_LC_WITH, "2026-09-16T00:00:00+00:00", "2026-09-01T00:00:00+00:00", "2026-09-16T00:00:00+00:00"),
    }
    assert len(phases) >= 3, f"the lifecycle collapsed: {phases}"
