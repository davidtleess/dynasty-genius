"""RED — competition-scoped game calendar events.

THE DEFECT, IN CODE ALREADY ON MAIN, reproduced three ways before writing this file.

`feed_cadence` reads ONE global game calendar for every weekly policy, so NFL facts govern the seven
NCAA PFF lanes. With an NFL calendar carrying `game_week_completions`:

    NFL week completion -> pff.ncaa_receiving_summary  cadence='due'  trigger='game_week_complete'
    NFL season_final    -> pff.ncaa_receiving_summary  cadence='current'
    NFL active window   -> pff.ncaa_receiving_summary  cadence='current'

Three separate leaks, not one:
    `_last_event`        reads one global `game_week_completions` for every weekly policy
    `season_final`       reads one global `final_game`
    `_in_active_window`  reads one global `week1_kickoff` / `final_game`

An FBS lane would be told its data is due because an NFL game finished, and told it is current
because the NFL season is underway. Both are false and neither is detectable from the output.

WHY THIS IS ITS OWN SLICE. It is latent TODAY only because the governed input is absent, so no
completions exist to leak. It goes live the moment that artifact lands, which is the next slice but
one. Compensating for it inside the future artifact generator would leave the engine wrong and paper
over it at one call site — so it is repaired here, in the engine, under its own RED.

TAGGING AN ARTIFACT DOES NOT FIX IT. My previous attempt asserted the derived anchors carried
`league=nfl` and that the string "ncaa" was absent from them. The shipped engine never consults such
a tag, so that check constrained nothing — a test aimed at the wrong artifact entirely.

DELIBERATELY OUT OF SCOPE: any GREEN, B21 capture, the governed input artifact, scheduler, provider
contact. This slice makes the engine capable of league isolation; it supplies no FBS evidence and
must not invent any.

CORRECTION TO MY OWN PREAMBLE (Codex, blocker 8). An earlier draft ended "the scoped module does
not exist." That was FALSE and copied from a template: `feed_cadence` is SHIPPED and green. What does
not exist is the COMPETITION SCOPE within it. These tests fail on missing attributes and wrong
behaviour in a live module — they do not skip, and nothing here is gated on a module import.
"""
from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone

import pytest

MODULE = "src.dynasty_genius.sources.feed_cadence"

#: Closed competition set. A third competition would need its own evidence source, so the set is
#: closed rather than open-ended.
NFL, FBS = "nfl", "fbs"
COMPETITIONS = frozenset({NFL, FBS})

#: The TOTAL policy-to-competition map, pinned HERE rather than read from the module. Reading the
#: module's own map would let a GREEN declare everything `nfl` and pass.
EXPECTED_COMPETITION = {
    # MEASURED TRIGGERS, not assumed ones. `roster` fires on league_year_open/draft_complete and
    # `medical` on operator_drop — NEITHER is a game event, so neither belongs in a map of
    # game-calendar scopes. An earlier draft listed `roster` here while the comprehension filtered
    # it out by trigger, making P2 unsatisfiable by construction: no implementation could produce a
    # map containing a key the same test excluded. P3b covers their right to stay unscoped.
    ("playerprofiler", "gamelog"): NFL,
    ("playerprofiler", "pbp"): NFL,
    ("playerprofiler", "player_season"): NFL,
    **{("pff", f"nfl_{fam}"): NFL for fam in (
        "passing_depth", "passing_pressure", "passing_summary",
        "receiving_depth", "receiving_scheme", "receiving_summary", "rushing_summary")},
    **{("pff", f"ncaa_{fam}"): FBS for fam in (
        "passing_depth", "passing_pressure", "passing_summary",
        "receiving_depth", "receiving_scheme", "receiving_summary", "rushing_summary")},
}


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover
        pytest.fail(f"{MODULE} does not exist yet (RED): {exc}")


def _at(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(timezone.utc)


def _held(ingested: str) -> dict:
    return {"newest_season": 2025, "covered_seasons": [2025], "ingested_at": ingested}


def _offer(observed: str) -> dict:
    return {"newest_season": 2025, "covered_seasons": [2025],
            "observed_at": observed, "provenance": "vendor_export_manifest"}


#: SCOPED calendar. The flat keys are GONE — a flat fallback would silently restore the leak, so the
#: contract requires the scoped shape and nothing else.
SCOPED_CAL = {
    "season": 2026,
    "competitions": {
        NFL: {
            "week1_kickoff": "2026-09-10T20:20:00-04:00",
            "final_game": "2027-01-04T20:20:00-05:00",
            "game_week_completions": ["2026-09-14T23:30:00-04:00"],
        },
        FBS: {
            "week1_kickoff": "2026-08-29T19:00:00-04:00",
            "final_game": "2027-01-11T19:30:00-05:00",
            "game_week_completions": [],          # no FBS evidence supplied
        },
    },
    "league_year_open": "2026-03-11T16:00:00-04:00",
    "draft_complete": "2026-04-25T19:00:00-04:00",
}


# ================== P1 — every game-triggered policy is scoped ====================


def test_p1_competition_vocabulary_is_closed():
    m = _mod()
    assert set(m.COMPETITIONS) == COMPETITIONS


def test_p2_the_scoped_map_is_EXACT_IN_BOTH_DIRECTIONS():
    """Pinned here, not read from the module: reading the module's own map would let a GREEN declare
    every lane `nfl` and pass while the leak persisted.

    BOTH DIRECTIONS (Codex, blocker 2). My earlier draft iterated only the EXPECTED keys, so a lane
    the module scoped but the test did not know about was invisible — a new game-triggered stream
    could be added, mis-scoped, and never caught. Set equality closes that: an extra scoped policy
    now fails as loudly as a missing one."""
    m = _mod()
    game_triggers = {"game_week_complete", "season_final"}
    actual = {
        (source, stream): m.policy_for(source, stream).competition
        for source in m.MANUAL_SOURCES
        for stream in m.streams_for(source)
        if game_triggers & set(m.policy_for(source, stream).triggers)
    }
    assert actual == EXPECTED_COMPETITION, (
        f"unexpected/extra: {sorted(set(actual) - set(EXPECTED_COMPETITION))}; "
        f"missing: {sorted(set(EXPECTED_COMPETITION) - set(actual))}; "
        f"mis-scoped: {sorted(k for k in set(actual) & set(EXPECTED_COMPETITION) if actual[k] != EXPECTED_COMPETITION[k])}"
    )


def test_p3_the_REGISTRY_CONSTRUCTOR_refuses_an_unscoped_game_policy():
    """CONSTRUCTOR, NOT ASSEMBLED POLICIES (Codex, blocker 3). My earlier draft inspected policies
    that `build_policy_registry` had already built, which only proves the shipped declarations
    happen to be scoped today — it does not prove an unscoped one is IMPOSSIBLE TO DECLARE. The
    rejection has to bite where the duplicate check already bites: at construction.

    STABLE CODES, not prose. A test that greps an error message re-breaks the moment someone
    rewords it, and passes for the wrong reason if a different guard fires with similar wording."""
    m = _mod()
    weekly = ("game_week_complete", "season_final")

    # OMITTED FIELD — the realistic migration failure. A declaration written against the OLD
    # 3-tuple shape must be refused outright, not silently accepted with an implicit scope. My
    # earlier draft only passed an explicit None, which a GREEN could satisfy while still accepting
    # a legacy 3-tuple and defaulting it to `nfl` — restoring the leak through the back door.
    with pytest.raises(m.CadenceError) as exc:
        m.build_policy_registry([("pff", "nfl_passing_summary", weekly)])
    assert exc.value.code == "competition_missing"

    # EXPLICIT None — the same refusal, stated rather than omitted.
    with pytest.raises(m.CadenceError) as exc:
        m.build_policy_registry([("pff", "nfl_passing_summary", weekly, None)])
    assert exc.value.code == "competition_missing"

    with pytest.raises(m.CadenceError) as exc:
        m.build_policy_registry([("pff", "nfl_passing_summary", weekly, "xfl")])
    assert exc.value.code == "competition_unknown"


def test_p3c_a_VALID_scoped_game_declaration_is_ACCEPTED():
    """Counter-case to P3 (Codex, blocker 2). Without it, a constructor that refused EVERY game
    declaration would satisfy all three rejection assertions and pass."""
    m = _mod()
    weekly = ("game_week_complete", "season_final")
    registry = m.build_policy_registry([("pff", "ncaa_passing_summary", weekly, FBS)])
    assert registry[("pff", "ncaa_passing_summary")].competition == FBS


def test_p3b_a_NON_game_policy_may_remain_unscoped():
    """Counter-test. `playerprofiler.medical` fires on `operator_drop` and `roster` on the league
    year — neither is a game event, so demanding a competition of them would be noise. The
    constructor must reject unscoped GAME policies specifically, not every unscoped policy."""
    m = _mod()
    registry = m.build_policy_registry([("playerprofiler", "medical", ("operator_drop",), None)])
    assert registry[("playerprofiler", "medical")].competition is None


def test_p4_pff_grades_is_REMOVED_because_it_names_no_feed():
    """SINGLE OUTCOME, per Codex's superseding ruling. My earlier draft accepted either removal or a
    per-league split; that was unsatisfiable — it contradicted a shipped contract
    (`test_manual_feed_cadence_red.py:98,115`) whichever branch a GREEN took.

    MEASURED TOPOLOGY, which is what decides it: the PFF store holds exactly 7 families x 2 leagues
    = 14 payload directories and NO grades directory in either league. Every occurrence of "grades"
    in the schema catalog is a COLUMN NAME inside those 14 lanes. `pff.grades` is a phantom stream —
    weekly triggers and no league identity because it was never an independently acquired feed.
    Splitting it would create two phantom obligations instead of one. Grade fields refresh exactly
    when the real lane carrying them refreshes.

    ASSERTED AGAINST THE DECLARED REGISTRY, NEVER THE STORE: the store is gitignored, so a committed
    test that read it would pass on this machine and be meaningless in CI."""
    m = _mod()
    declared = set(m.streams_for("pff"))
    assert declared == {f"{lg}_{fam}" for lg in ("nfl", "ncaa") for fam in (
        "passing_depth", "passing_pressure", "passing_summary",
        "receiving_depth", "receiving_scheme", "receiving_summary", "rushing_summary")}, (
        f"expected exactly the 14 real lanes; got {sorted(declared)}"
    )
    for phantom in ("grades", "nfl_grades", "ncaa_grades"):
        assert phantom not in declared, f"`{phantom}` names no payload lane"


def test_p5_every_real_lane_KEEPS_its_refresh_obligation():
    """Counter-test to P4. Removing the phantom must not be achieved by thinning the registry — the
    14 real lanes each retain their game-driven obligation."""
    m = _mod()
    for stream in m.streams_for("pff"):
        p = m.policy_for("pff", stream)
        assert {"game_week_complete", "season_final"} <= set(p.triggers), (
            f"pff.{stream} lost its refresh obligation"
        )


def test_p6_no_REAL_lane_is_marked_model_use_forbidden_at_STREAM_level():
    """The grades model-input prohibition is COLUMN-level and is enforced independently of the
    cadence registry (`head_b_contract.py` rejects prohibited grade columns by name; the PFF export
    adapters carry column blocklists). The stream-level `is_grades` advisory flag hung off a lane
    holding zero data.

    Removing that flag must NOT be over-corrected into flagging the 14 real lanes: those lanes carry
    legitimately retained non-grade data, and forbidding them wholesale would suppress real inputs
    to enforce a restriction that operates on columns. Layer 1 retains everything; column-level
    contracts decide what may reach a model.

    ASSERTED AGAINST `stream_disposition`, WHICH IS WHERE THE FLAG LIVES. My first draft read
    `policy_for(...)` with `getattr(p, "model_use_forbidden", False)`. `StreamPolicy` has no such
    attribute, so the default made it pass on every input — it would have passed with all 14 lanes
    flagged. Querying the wrong object and defaulting the answer is not a check.
    """
    m = _mod()
    for stream in m.streams_for("pff"):
        d = m.stream_disposition("pff", stream)
        assert d.model_use_forbidden is False, (
            f"pff.{stream} is a real retained lane; the grade restriction is column-level"
        )
        # ...and the lane is still ingested and retained, so the flag was not cleared by
        # demoting the lane itself.
        assert d.retained_raw is True and d.ingestion_authorized is True


# ================== I1 — behavioural isolation, both directions ===================


def test_i1_an_NFL_week_completion_does_NOT_make_an_FBS_lane_due():
    """The exact reproduction that opened this slice. SCOPED_CAL supplies an NFL completion and NO
    FBS completions."""
    m = _mod()
    r = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-09-16T00:00:00+00:00"), calendar=SCOPED_CAL,
        held=_held("2026-09-01T00:00:00+00:00"), offer=_offer("2026-09-16T00:00:00+00:00"),
    )
    # EXACT STATE, not merely "not due" (Codex, blocker 7). `!= "due"` is satisfied by `current`,
    # `not_due` AND `undetermined` — three materially different answers, two of which would be a
    # different bug. With no FBS completions the only honest state is `undetermined`.
    assert r.cadence == "undetermined", (
        f"an NFL game cannot make an FBS lane due; got {r.cadence!r} trigger={r.trigger!r}"
    )
    assert r.trigger is None


def test_i1b_the_SAME_instant_DOES_make_the_NFL_lane_due():
    """Counter-test, so I1 is not passing merely because nothing is ever due."""
    m = _mod()
    r = m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary",
        now=_at("2026-09-16T00:00:00+00:00"), calendar=SCOPED_CAL,
        held=_held("2026-09-01T00:00:00+00:00"), offer=_offer("2026-09-16T00:00:00+00:00"),
    )
    assert r.cadence == "due" and r.trigger == "game_week_complete"


def test_i2_isolation_holds_in_the_OTHER_direction_too():
    """An FBS completion must not make an NFL lane due. Testing only one direction would let an
    implementation hardcode `nfl` and pass."""
    m = _mod()
    cal = {**SCOPED_CAL, "competitions": {
        NFL: {**SCOPED_CAL["competitions"][NFL], "game_week_completions": []},
        FBS: {**SCOPED_CAL["competitions"][FBS],
              "game_week_completions": ["2026-09-13T23:30:00-04:00"]},
    }}
    nfl_lane = m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary",
        now=_at("2026-09-16T00:00:00+00:00"), calendar=cal,
        held=_held("2026-09-01T00:00:00+00:00"), offer=_offer("2026-09-16T00:00:00+00:00"))
    fbs_lane = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-09-16T00:00:00+00:00"), calendar=cal,
        held=_held("2026-09-01T00:00:00+00:00"), offer=_offer("2026-09-16T00:00:00+00:00"))
    # EXACT STATES. The NFL block now carries no completions while the NFL season IS underway, so
    # the NFL lane is `undetermined` for the same reason the FBS lane was in I1 — symmetry is the
    # point of running this direction at all.
    assert nfl_lane.cadence == "undetermined", (
        f"an FBS game cannot make an NFL lane due; got {nfl_lane.cadence!r}"
    )
    assert nfl_lane.trigger is None
    assert fbs_lane.cadence == "due" and fbs_lane.trigger == "game_week_complete"


def test_i3_SEASON_FINAL_is_scoped():
    """Second leak vector: one global `final_game` meant the NFL season ending made every FBS lane
    due for a season-final refresh.

    TEMPORALLY REPAIRED (Codex, blocker 7). My draft evaluated at 2027-01-05T00:00Z, which is
    80 MINUTES BEFORE the NFL final at 2027-01-04T20:20-05:00 == 2027-01-05T01:20Z. The season-final
    event had not occurred at all, so the test asserted the absence of a leak that could not have
    happened yet — it would have passed against the unrepaired engine. Verified by arithmetic, not
    by eye. Now evaluated a day AFTER the NFL final and a week BEFORE the FBS final (2027-01-11), so
    the NFL season really has ended and the FBS season really has not."""
    m = _mod()
    when = _at("2027-01-06T00:00:00+00:00")
    fbs = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary", now=when, calendar=SCOPED_CAL,
        held=_held("2026-12-01T00:00:00+00:00"), offer=_offer("2027-01-06T00:00:00+00:00"))
    assert fbs.trigger != "season_final", "the NFL season ending is not an FBS season-final event"
    assert fbs.cadence == "undetermined", f"no FBS evidence; got {fbs.cadence!r}"
    # Counter-test at the SAME instant: the NFL lane genuinely has crossed its season final, so the
    # event exists and I3 is not passing because nothing happened.
    nfl = m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary", now=when, calendar=SCOPED_CAL,
        held=_held("2026-12-01T00:00:00+00:00"), offer=_offer("2027-01-06T00:00:00+00:00"))
    assert nfl.trigger == "season_final" and nfl.cadence == "due"


def test_i4_the_ACTIVE_WINDOW_is_scoped():
    """Third leak vector: one global kickoff/final meant an FBS lane read `current` merely because
    the NFL season was underway. On 2026-08-30 the FBS season HAS started and the NFL has not, so a
    correct implementation must treat the two lanes differently at this instant."""
    m = _mod()
    when = _at("2026-08-30T00:00:00+00:00")
    fbs = m.evaluate_stream(source="pff", stream="ncaa_receiving_summary", now=when,
                            calendar=SCOPED_CAL, held=_held("2026-08-01T00:00:00+00:00"),
                            offer=_offer("2026-08-30T00:00:00+00:00"))
    nfl = m.evaluate_stream(source="pff", stream="nfl_receiving_summary", now=when,
                            calendar=SCOPED_CAL, held=_held("2026-08-01T00:00:00+00:00"),
                            offer=_offer("2026-08-30T00:00:00+00:00"))
    assert nfl.cadence == "not_due", "the NFL season has not started on 2026-08-30"
    # EXACT STATE. The FBS season has started but carries no completions, so `undetermined` —
    # `!= "not_due"` would also have accepted `current`, which is the very overclaim E1 forbids.
    assert fbs.cadence == "undetermined", (
        f"the FBS season HAS started and has no evidence; got {fbs.cadence!r}"
    )


# ================== E1 — missing FBS evidence leaves FBS undetermined =============


def test_e1_no_FBS_completions_leaves_FBS_lanes_UNDETERMINED_in_season():
    """This slice supplies no FBS evidence and must not invent any. In the FBS season with no
    declared completions the honest answer is `undetermined` — not `current`, and certainly not
    borrowed NFL weeks."""
    m = _mod()
    r = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-10-01T00:00:00+00:00"), calendar=SCOPED_CAL,
        held=_held("2026-09-20T00:00:00+00:00"), offer=_offer("2026-10-01T00:00:00+00:00"))
    assert r.cadence == "undetermined", (
        f"no FBS completions exist, so the obligation is uncomputable; got {r.cadence!r}"
    )


def test_e1b_supplying_FBS_evidence_resolves_it():
    """Counter-test: `undetermined` is a consequence of missing evidence, not a permanent state."""
    m = _mod()
    cal = {**SCOPED_CAL, "competitions": {
        **SCOPED_CAL["competitions"],
        FBS: {**SCOPED_CAL["competitions"][FBS],
              "game_week_completions": ["2026-09-27T23:30:00-04:00"]},
    }}
    r = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-10-01T00:00:00+00:00"), calendar=cal,
        held=_held("2026-09-20T00:00:00+00:00"), offer=_offer("2026-10-01T00:00:00+00:00"))
    assert r.cadence == "due" and r.trigger == "game_week_complete"


# ================== V1 — the validator rejects unscoped calendars =================
#
# STABLE MACHINE CODES, NOT PROSE (Codex, blocker 4). My earlier draft asserted
# `"competition" in detail.lower()`. That couples the contract to wording: a reword breaks it, and —
# worse — a DIFFERENT guard whose message happens to contain the word passes it. The validator must
# surface a stable code as the first colon-delimited token of `detail`.

SCOPE_CODES = frozenset({
    "calendar_scope_missing",           # flat calendar: no competitions block at all
    "calendar_scope_not_object",        # competitions present but not an object
    "calendar_competition_unknown",     # a competition outside the closed set
    "calendar_competition_not_object",  # a competition entry that is not an object
    "calendar_competition_partial",     # the three scoped facts not supplied together
})


def _code(detail: str) -> str:
    return (detail or "").split(":", 1)[0].strip()


def test_v1_a_FLAT_calendar_is_REJECTED_with_a_stable_code():
    """No flat fallback. Accepting the old shape would silently restore the leak for any artifact
    written before this change."""
    _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    flat = {"calendar": {"season": 2026,
                         "week1_kickoff": "2026-09-10T20:20:00-04:00",
                         "final_game": "2027-01-04T20:20:00-05:00"}}
    status, _loaded, detail = daily_control._validate_inputs(flat)
    assert status == "invalid", "a flat game calendar must be refused"
    assert _code(detail) == "calendar_scope_missing", detail


@pytest.mark.parametrize("label,competitions,expected_code", [
    ("unknown competition",
     {"xfl": {"week1_kickoff": "2026-09-10T20:20:00-04:00",
              "final_game": "2027-01-04T20:20:00-05:00",
              "game_week_completions": []}},
     "calendar_competition_unknown"),
    ("competitions not an object", "nfl", "calendar_scope_not_object"),
    ("competition entry not an object", {NFL: "2026-09-10T20:20:00-04:00"},
     "calendar_competition_not_object"),
    ("partial competition", {NFL: {"week1_kickoff": "2026-09-10T20:20:00-04:00"}},
     "calendar_competition_partial"),
])
def test_v2_malformed_scopes_are_rejected_by_path(label, competitions, expected_code):
    """`week1_kickoff`, `final_game` and `game_week_completions` are scoped TOGETHER — a half-scoped
    competition is how a partial migration would reintroduce a global read.

    Each path asserts its OWN code. A single shared code would let one guard catch all four while
    three remained unwritten."""
    _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    status, _loaded, detail = daily_control._validate_inputs(
        {"calendar": {"season": 2026, "competitions": competitions}})
    assert status == "invalid", f"{label}: accepted"
    assert _code(detail) in SCOPE_CODES, f"{label}: unrecognised code in {detail!r}"
    assert _code(detail) == expected_code, f"{label}: wrong guard fired — {detail!r}"


def test_v3_a_correctly_scoped_calendar_is_ACCEPTED():
    """Counter-test, so the validator is not simply refusing every calendar."""
    _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    status, loaded, detail = daily_control._validate_inputs({"calendar": SCOPED_CAL})
    assert status == "ok", f"a correctly scoped calendar was rejected: {detail}"
    assert loaded is not None


def test_v4_an_ABSENT_competition_block_is_HONEST_MISSING_EVIDENCE_not_an_error():
    """CODEX BLOCKER 5, and the distinction that matters most in this slice.

    ABSENT and PARTIAL are not the same failure. We hold no FBS schedule evidence at all, so an
    artifact that simply omits the FBS block is TRUE — it says "I have nothing for FBS", and the
    engine's answer is `undetermined`. Rejecting it would force an operator to fabricate FBS anchors
    to make the file load, which is precisely how invented evidence enters a store.

    A PARTIAL block is different: it CLAIMS to describe a competition and then supplies some of the
    facts, so anything reading it gets a half-answer it cannot detect. That stays invalid (V2)."""
    _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    nfl_only = {**SCOPED_CAL,
                "competitions": {NFL: SCOPED_CAL["competitions"][NFL]}}
    status, loaded, detail = daily_control._validate_inputs({"calendar": nfl_only})
    assert status == "ok", f"an omitted FBS block is honest, not malformed: {detail}"
    assert loaded is not None


def test_v4b_the_omitted_block_leaves_FBS_UNDETERMINED_and_NFL_working():
    """The other half of V4: accepting the artifact must not mean guessing. An omitted competition
    yields `undetermined` for its lanes while the supplied competition still computes."""
    m = _mod()
    nfl_only = {**SCOPED_CAL, "competitions": {NFL: SCOPED_CAL["competitions"][NFL]}}
    fbs = m.evaluate_stream(
        source="pff", stream="ncaa_receiving_summary",
        now=_at("2026-09-16T00:00:00+00:00"), calendar=nfl_only,
        held=_held("2026-09-01T00:00:00+00:00"), offer=_offer("2026-09-16T00:00:00+00:00"))
    nfl = m.evaluate_stream(
        source="pff", stream="nfl_receiving_summary",
        now=_at("2026-09-16T00:00:00+00:00"), calendar=nfl_only,
        held=_held("2026-09-01T00:00:00+00:00"), offer=_offer("2026-09-16T00:00:00+00:00"))
    assert fbs.cadence == "undetermined" and fbs.trigger is None
    assert nfl.cadence == "due" and nfl.trigger == "game_week_complete"


# ================== X1 — malformed scope through the REAL controller ==============


def test_x1_a_malformed_scope_drives_EXECUTE_to_a_disclosed_failure(tmp_path, monkeypatch):
    """CODEX BLOCKER 6. Unit-level validation is not the product surface. The controller is what
    runs daily, and a governed input that fails to load must produce a LOUD, disclosed result — not
    a quiet fallback to `undetermined` that looks like an ordinary uninitialised morning.

    Four properties, because a partial failure here is worse than a total one:
      1. nonzero exit — the scheduler must see the failure
      2. every manual source discloses `manual_inputs_invalid`, naming the cause
      3. every declared stream still serializes BOTH axes — a broken calendar must not erase the
         coverage answer, which does not depend on the calendar at all
      4. the automatic route is ISOLATED and still healthy — one bad manual artifact must not take
         down ingestion that never reads it
    """
    m = _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    bad = tmp_path / "manual_feed_cadence_inputs.json"
    bad.write_text(json.dumps({"calendar": {"season": 2026, "competitions": {
        NFL: {"week1_kickoff": "2026-09-10T20:20:00-04:00"}}}}), encoding="utf-8")
    monkeypatch.setattr(daily_control, "MANUAL_CADENCE_INPUTS", bad)

    # HERMETIC, DELIBERATELY ORDERED MANIFEST (Codex, blocker on v4). In the DEFAULT manifest the
    # automatic routes sit at indices 0-1 and the failing manual sources at 5-6 — MEASURED. So
    # `ran` was already populated BEFORE the manual failure occurred, and my assertion could not
    # distinguish "execution continued past the fault" from "execution halted at it". The test
    # would have passed against a controller that aborted on the first manual failure, which is
    # precisely the isolation property it claims to prove.
    #
    # Ordering the manual failure FIRST and a preflight-valid automatic route SECOND makes the
    # later runner call the evidence: it can only happen if the fault did not stop the run.
    full = {e.source: e for e in daily_control.build_manifest()}
    ordered = [full["playerprofiler"], full["nflverse_usage_capture"]]
    assert [e.source for e in ordered] == ["playerprofiler", "nflverse_usage_capture"], (
        "the malformed manual source must precede the automatic route or this proves nothing"
    )

    ran: list[str] = []

    def runner(entry):
        ran.append(entry.source)
        return daily_control.SourceResult(source=entry.source, state="ok", failed=False)

    result = daily_control.execute(manifest=ordered, report_root=tmp_path, runner=runner)

    assert result.exit_code != 0, "a malformed governed input must not exit 0"

    r = result.by_source["playerprofiler"]
    # `state` is the machine field and already carries `manual_inputs_invalid` on the shipped
    # controller; `detail` carries the REASON. My first draft asserted the state code against
    # `detail` and would have failed on correct code. The scope requirement is that the reason
    # names the scope fault with a stable code.
    assert r.state == "manual_inputs_invalid", f"playerprofiler state was {r.state!r}"
    assert _code(r.detail) in SCOPE_CODES, (
        f"playerprofiler did not name the scope fault with a stable code: {r.detail!r}"
    )
    assert r.streams, "playerprofiler serialized no streams"
    for stream, st in r.streams.items():
        assert st.get("cadence") in m.CADENCE_STATES, f"{stream} lost the cadence axis"
        assert st.get("coverage") in m.COVERAGE_STATES, (
            f"{stream} lost the COVERAGE axis, which does not depend on the calendar"
        )

    # THE EXACT LATER CALL. Not "something ran" — the automatic route that is SEQUENCED AFTER the
    # failure must have been invoked, and must have succeeded. This is the only formulation that
    # actually witnesses isolation.
    assert ran == ["nflverse_usage_capture"], (
        f"the automatic route sequenced after the manual fault did not run; ran={ran}"
    )
    after = result.by_source["nflverse_usage_capture"]
    assert after.state == "ok" and not after.failed, (
        f"the later automatic route was contaminated by the manual fault: {after.state!r}"
    )


def test_x1b_ROUTE_PRECEDENCE_survives_a_malformed_scope(tmp_path, monkeypatch):
    """Split out of X1 (Codex, earlier blocker). RotoViz and Campus2Canton hold nothing and
    correctly stop at `manual_route_incomplete` — the governed input never becomes relevant to them.
    Demanding `manual_inputs_invalid` of them would force a GREEN to BREAK a correct precedence rule
    to satisfy this test."""
    _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    bad = tmp_path / "manual_feed_cadence_inputs.json"
    bad.write_text(json.dumps({"calendar": {"season": 2026, "competitions": {
        NFL: {"week1_kickoff": "2026-09-10T20:20:00-04:00"}}}}), encoding="utf-8")
    monkeypatch.setattr(daily_control, "MANUAL_CADENCE_INPUTS", bad)

    full = {e.source: e for e in daily_control.build_manifest()}
    ordered = [full["rotoviz"], full["campus2canton"]]
    result = daily_control.execute(
        manifest=ordered, report_root=tmp_path,
        runner=lambda e: daily_control.SourceResult(source=e.source, state="ok", failed=False))

    for source in ("rotoviz", "campus2canton"):
        assert result.by_source[source].state == "manual_route_incomplete", (
            f"{source} holds nothing and must stop at route precedence, not at the calendar; "
            f"got {result.by_source[source].state!r}"
        )


# ================== E2 — a missing game clock silences ONLY the game clock ========


def test_e2_an_absent_competition_block_does_NOT_suppress_NON_GAME_events():
    """REGRESSION. Codex found this by direct reproduction against my first GREEN; nothing in this
    file caught it, which is why it now exists.

    `playerprofiler.player_season` responds to `game_week_complete` and `season_final` (game events,
    competition-scoped) AND to `combine_complete` and `draft_complete` (LEAGUE-YEAR events that live
    at the top level of the calendar and are observable with no game calendar whatsoever).

    My first version returned `undetermined` the instant a game-triggered policy had no competition
    facts. That let an ABSENT fact SUPPRESS AN EVENT WE COULD SEE PERFECTLY WELL: with no NFL block,
    a completed draft stopped registering and the stream read `undetermined` instead of `due`. The
    real-world shape of that is the offseason — exactly when draft and combine are the only things
    moving and the game calendar is legitimately empty."""
    m = _mod()
    cal = {
        "season": 2026,
        "competitions": {},                                    # no game facts at all
        "combine_complete": "2026-02-28T12:00:00-05:00",
        "draft_complete": "2026-04-25T19:00:00-04:00",
    }
    r = m.evaluate_stream(
        source="playerprofiler", stream="player_season",
        now=_at("2026-05-01T00:00:00+00:00"), calendar=cal,
        held=_held("2026-01-01T00:00:00+00:00"), offer=None)
    assert r.cadence == "due", (
        f"the draft completed on 2026-04-25 and we hold data from 2026-01-01; an absent game "
        f"calendar must not hide it. got {r.cadence!r}"
    )
    assert r.trigger == "draft_complete"


def test_e2b_with_NO_observable_event_the_missing_game_clock_IS_the_answer():
    """Counter-test to E2, and the reason E2 is not simply a licence to ignore missing facts. When
    no non-game event has overtaken what we hold, the unseeable game clock genuinely decides the
    question — and the honest answer is `undetermined`, never `current`."""
    m = _mod()
    cal = {
        "season": 2026,
        "competitions": {},
        "combine_complete": "2026-02-28T12:00:00-05:00",
        "draft_complete": "2026-04-25T19:00:00-04:00",
    }
    r = m.evaluate_stream(
        source="playerprofiler", stream="player_season",
        now=_at("2026-05-01T00:00:00+00:00"), calendar=cal,
        held=_held("2026-04-30T00:00:00+00:00"),          # held AFTER the draft
        offer=None)
    assert r.cadence == "undetermined", (
        f"no event outranks what we hold, and the game clock is invisible; got {r.cadence!r}"
    )
    assert r.trigger is None


def test_e2c_a_NON_game_stream_is_unaffected_by_a_missing_game_calendar():
    """`playerprofiler.roster` carries no game trigger at all, so a missing game calendar is simply
    irrelevant to it. Without this, a fix could route every stream through the game-clock branch and
    still satisfy E2/E2b."""
    m = _mod()
    cal = {"season": 2026, "competitions": {},
           "league_year_open": "2026-03-11T16:00:00-04:00",
           "draft_complete": "2026-04-25T19:00:00-04:00"}
    r = m.evaluate_stream(
        source="playerprofiler", stream="roster",
        now=_at("2026-05-01T00:00:00+00:00"), calendar=cal,
        held=_held("2026-01-01T00:00:00+00:00"), offer=None)
    assert r.cadence == "due" and r.trigger == "draft_complete"


# ================== P7 — a removed stream authorizes nothing ======================


def test_p7_an_UNDECLARED_stream_authorizes_nothing():
    """REGRESSION. `ingestion_authorized` was hardcoded True for every (source, stream) pair, so
    after `pff.grades` was removed the disposition still answered YES to "may we acquire this?" for
    a stream that names no feed. A removed phantom must not keep granting permissions.

    Authorization follows the DECLARATION: no policy, no route, nothing to authorize."""
    m = _mod()
    assert m.policy_for("pff", "grades") is None, "fixture precondition: the phantom is removed"
    d = m.stream_disposition("pff", "grades")
    assert d.ingestion_authorized is False, "an undeclared stream is not authorized for ingestion"
    assert d.creates_refresh_obligation is False, "and it cannot create a refresh obligation"
    assert d.retained_raw is False, "there is no payload to retain"


@pytest.mark.parametrize("source,stream", [
    ("pff", "totally_invented_lane"),      # unknown stream on a REAL source
    ("pff", "grades"),                     # the specific phantom that was removed
    ("playerprofiler", "nonexistent"),     # unknown stream on the other manual source
    ("no_such_vendor", "anything"),        # unknown source entirely
])
def test_p7c_the_rule_is_GENERAL_not_a_special_case_for_grades(source, stream):
    """Codex, residual 2. P7 pinned only `pff.grades`, so an implementation could satisfy it by
    special-casing that one key — leaving every OTHER unknown stream still answering YES to "may we
    acquire this?". The property is about undeclared streams as a class, not about one removed
    phantom, and a rule that holds for exactly one input is not a rule."""
    m = _mod()
    assert m.policy_for(source, stream) is None, "fixture precondition: this stream is undeclared"
    d = m.stream_disposition(source, stream)
    assert d.ingestion_authorized is False
    assert d.creates_refresh_obligation is False
    assert d.retained_raw is False


def test_p7b_a_REAL_lane_is_still_fully_authorized():
    """Counter-test. Tightening authorization must not revoke it from the 14 real lanes — that would
    stop Layer 1 ingestion to fix a phantom."""
    m = _mod()
    for stream in m.streams_for("pff"):
        d = m.stream_disposition("pff", stream)
        assert d.ingestion_authorized is True, f"pff.{stream} is a real lane and must stay ingested"
        assert d.retained_raw is True
        assert d.creates_refresh_obligation is True
