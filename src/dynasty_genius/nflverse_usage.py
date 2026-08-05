"""nflverse usage ingestion — Next Gen Stats, snap counts, and the injury report.

Layer 1. Originally two streams David named that we already had installed and had **never once
called**: ``nflreadpy.load_nextgen_stats`` and ``nflreadpy.load_snap_counts``. A fifth spec,
``INJURIES`` (``nflreadpy.load_injuries``), joined them on 2026-08-01 — hence
``SCHEMA_VERSION`` ``v4``. v3 added the fifth stream; v4 marks the post-live contract change —
``source_era`` and ``season_type`` in the store and exports, era-dependent row-key semantics, and an
idempotence identity that includes the persisted projection. An artifact from before and after that
change must never carry the same label. Free, no credential, already
a daily dependency. Fetch, snapshot, resolve identity, store durably.

**Downstream, stated precisely (corrected 2026-08-03 — this paragraph previously read "Nothing
downstream reads it yet — no model input, no surface, no scoring", which was false on the first
clause).** Two production consumers read the export via ``load_nextgen_from_export``:
``scripts/run_feature_refresh.py`` and ``scripts/assemble_engine_b_dataset.py``. Six ``ngs_*``
columns therefore reach the assembled Engine B **dataset**.

**No shipped model trains on them, and that is deliberate.** ``scripts/train_engine_b.py`` excludes
``ngs_*`` from the unified matrix by name (position-exclusive features would be a wrong constant
behind a median imputer, not a sparse one), and the per-position opt-in helpers over
``ENGINE_B_OPTIONAL_FEATURES_BY_POSITION`` have **zero production callers**.

The registry role is ``context_signal``. What is unauthorized is **predictive-model training use and
model-feature promotion** — not the dataset assembly above, which exists and is stated plainly here
rather than denied. Reaching a dataset is not being a model input, but the gap between those two is
**one caller wide**: treat any new consumer of those per-position helpers as a governance change
requiring a separately authorized validation, never as a wiring change.

*(Open and escalated, not resolved here: this registry role and
``engine_b_contract.ENGINE_B_OPTIONAL_FEATURES_BY_POSITION`` — which declares these same six fields
as optional per-position model features — are in tension. Inert while nothing calls the helpers.)*

Callable, never self-scheduling. A scheduler is a separate decision and a separate word.

**This module is deliberately the same shape as ``league_transactions.py``**, which was proven
against live data the same night: raw snapshot before parsing, canonical identity with a
never-rounded outcome, a content-addressed store whose idempotence is provable by bytes, a status
marker written before any fetch, and failures that name themselves. It is a repetition of a working
pattern, not a new framework — five stream specs and one capture function.

Shape facts measured from the live source (2026-07-30), each of which the code must survive:

- NGS keys on ``player_gsis_id``, which **is** our canonical id — so NGS needs no bridge.
- Snap counts key on ``pfr_player_id``, which does not, and needs the governed crosswalk's
  ``pfr_id -> gsis_id`` bridge (7,774 of 7,952 entries carry both).
- **That bridge is not clean.** Three PFR ids each map to two different players in the governed
  crosswalk (``CartKy01`` -> Kyle Carter *and* David Morgan; ``HarrAl00``; ``MillSt00``). A bridge
  that silently picks one would attach real snap counts to the wrong player. Those resolve to
  ``conflict`` and are counted separately — see ``IdentityIndex``.
- NGS ``week`` includes ``0``, which is the season aggregate rather than a real week. It is stored
  as-is and labelled, never mistaken for week one.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA_VERSION = "nflverse_usage.v4"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = _REPO_ROOT / "app" / "data" / "nflverse_usage.db"
DEFAULT_RAW_ROOT = _REPO_ROOT / "app" / "data" / "nflverse_usage"
#: Consumer-facing DERIVED export. Not a second source of truth — a projection of
#: the store, published as one last-good unit (§publish_export).
DEFAULT_EXPORT_ROOT = DEFAULT_RAW_ROOT / "export"
GOVERNED_CROSSWALK = (
    _REPO_ROOT / "app" / "data" / "identity" / "_runs" / "ff_playerids_20260516.json"
)

#: Identity outcomes. Four-valued, and the extra value is the point: a source id that maps to two
#: different players is NOT the same thing as one that maps to none, and neither is "resolved".
CANONICAL_RESOLVED = "canonical_resolved"
SOURCE_ONLY = "source_only"
CONFLICT = "conflict"
UNKNOWN = "unknown"

#: A row for which player identity is NOT A QUESTION — the stream has no player column at all.
#:
#: This is categorically different from `UNKNOWN`, which means "we looked for a player and did
#: not find one". FTN charting is play-grain: 143,572 plays with no player field anywhere. Left
#: as `UNKNOWN`, every one of those plays would be reported as an unresolved PLAYER and would
#: land in `unresolved_identity.parquet` — a review artifact that exists so a human can chase
#: missing players would fill with rows that never had one. Distinguishing the two is Codex's
#: C7 requirement and the reason this constant exists rather than a nullable column.
NOT_APPLICABLE = "not_applicable"


class UsageCaptureError(RuntimeError):
    """The capture refuses rather than publishing something untrustworthy."""


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityIndex:
    """Resolves a source player id to the Dynasty Genius canonical id.

    Our canonical id is the GSIS id, so a GSIS-keyed stream resolves by membership and a
    PFR-keyed stream resolves through the governed crosswalk's bridge.

    **Conflicts are held, not resolved.** ``pfr_conflicts`` carries every PFR id the crosswalk
    maps to more than one GSIS id. Resolving one by picking the first row would silently attach a
    real player's snaps to a different player, which is worse than not having the row at all.
    """

    gsis_ids: frozenset[str]
    pfr_to_gsis: Mapping[str, str]
    pfr_conflicts: Mapping[str, tuple[str, ...]]
    names_by_gsis: Mapping[str, str]

    @classmethod
    def from_governed_crosswalk(cls, path: Path = GOVERNED_CROSSWALK) -> "IdentityIndex":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = payload.get("entries") or []
        if not entries:
            raise UsageCaptureError(
                f"governed_crosswalk_empty: {path} carries no entries — refusing to resolve "
                "identity against an empty universe"
            )

        gsis: set[str] = set()
        names: dict[str, str] = {}
        by_pfr: dict[str, set[str]] = {}
        for row in entries:
            gsis_id = str(row.get("gsis_id") or "").strip()
            if not gsis_id:
                continue
            gsis.add(gsis_id)
            if row.get("name"):
                names[gsis_id] = str(row["name"])
            pfr_id = str(row.get("pfr_id") or "").strip()
            if pfr_id:
                by_pfr.setdefault(pfr_id, set()).add(gsis_id)

        bridge = {k: next(iter(v)) for k, v in by_pfr.items() if len(v) == 1}
        conflicts = {k: tuple(sorted(v)) for k, v in by_pfr.items() if len(v) > 1}
        return cls(
            gsis_ids=frozenset(gsis),
            pfr_to_gsis=bridge,
            pfr_conflicts=conflicts,
            names_by_gsis=names,
        )

    def resolve(self, source_id: Any, *, kind: str) -> tuple[str | None, str]:
        """Returns ``(dg_player_id, identity_status)``. Never raises, never guesses."""
        key = str(source_id or "").strip()
        if not key:
            return None, UNKNOWN

        if kind == "gsis":
            if key in self.gsis_ids:
                return key, CANONICAL_RESOLVED
            # A real GSIS id the governed universe does not carry: attributable, not canonical.
            return None, SOURCE_ONLY

        if kind == "pfr":
            if key in self.pfr_conflicts:
                return None, CONFLICT
            resolved = self.pfr_to_gsis.get(key)
            if resolved is not None:
                return resolved, CANONICAL_RESOLVED
            return None, SOURCE_ONLY

        raise UsageCaptureError(f"unknown identity kind: {kind!r}")


# ---------------------------------------------------------------------------
# Stream specifications
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StreamEra:
    """One shape a stream has had, identified by its COLUMN SET, never by year.

    nflverse swapped `date_modified` for `season_type` at 2025 — same 16 columns,
    one traded for the other — and the 2025 era carries ZERO duplicate groups on
    the five-column key, so it cannot express a revision at all. Mapping one era
    onto the other would either lose the revision semantics or invent them.

    Detection is by content because a season label is not evidence of a shape:
    the same PlayerProfiler discipline where an unrecognised era REFUSES rather
    than being mapped onto whichever known era looks closest.
    """

    name: str
    requires: tuple[str, ...]
    forbids: tuple[str, ...]
    columns: tuple[str, ...]
    grain: tuple[str, ...]

    def matches(self, available: set[str]) -> bool:
        """EXACT column-set equality, not a marker check.

        `requires`/`forbids` alone accept an otherwise-valid row carrying an
        UNEXPECTED extra provider field and then silently discard it — which is
        precisely how 2025's `season_type` was lost the first time. An additive
        provider column must REFUSE, because the class and its error text promise
        that an unrecognised column set refuses (Codex B1).
        """
        return available == set(self.columns)


@dataclass(frozen=True)
class StreamSpec:
    """One nflverse stream: how to load it, how to key it, what to keep."""

    name: str
    table: str
    identity_column: str
    identity_kind: str
    grain: tuple[str, ...]
    columns: tuple[str, ...]
    loader: Callable[..., Any]
    loader_kwargs: Mapping[str, Any]

    #: Columns the EXPORT must publish as real numbers, not strings. SQLite holds
    #: every column as TEXT, so an untyped projection ships `week`/`season` as
    #: Utf8 — and E1 (Codex, reproduced) showed the exact existing feature filter
    #: `(week == 0) & (season_type == "REG")` then fails outright against it. An
    #: all-string Parquet is not an analyst-ready projection; calling it one is
    #: how a local-reader swap silently erases every NGS feature.
    integer_columns: tuple[str, ...] = ()
    float_columns: tuple[str, ...] = ()

    #: Columns where the provider ships MORE THAN ONE token for "absent". The
    #: nflverse injury report carries 45 true nulls and 69 whitespace strings
    #: ('\n    ', a scrape artifact) in `practice_status` alone. Stored as-is
    #: they are two different values meaning the same nothing — the same defect
    #: PlayerProfiler's `NA` token produced. Opt-in per stream so existing
    #: reviewed streams keep their exact behaviour.
    blank_as_null_columns: tuple[str, ...] = ()

    #: Refuse when any grain coordinate is absent. `date_modified` is the whole
    #: reason injury revisions are a time series rather than a conflict; a null
    #: there would still key successfully and quietly collapse two observations
    #: into an indistinguishable pair. Opt-in so existing streams are untouched.
    require_populated_grain: bool = False

    #: Refuse a non-finite value (NaN/inf) in a declared numeric column. Opt-in per stream so
    #: existing reviewed streams keep their exact behaviour. Refusal — not silent nulling — is
    #: the consistent choice: `publish_export` already refuses a cast that loses non-null
    #: values, so quietly turning an inf into a null here would contradict that contract and
    #: make corruption indistinguishable from missingness.
    refuse_non_finite: bool = False

    #: Exclude rows whose identity column is null, and RECONCILE the count in coverage.
    #:
    #: `ff_opportunity` ships exactly one residual row per (game_id, posteam) — 1,280 across
    #: 2023-2025 — carrying unattributed targets and air yards. Measured: 1,274 of them have a
    #: nonzero `rec_attempt` but ZERO realized production, and their total contribution to
    #: `total_fantasy_points` is exactly 0.0 (0.000% of the 143,269.2 attributed). They are an
    #: expected-value residual, not lost player production.
    #:
    #: They cannot simply flow through: the grain is (game_id, player_id) and a null player
    #: would key every team-game residual identically. Refusing the whole batch is also wrong —
    #: the residual is a normal property of the source, not corruption. So they are excluded
    #: and COUNTED, never dropped silently. Opt-in, so no existing stream changes.
    exclude_unidentified_rows: bool = False

    #: Whether player identity is a MEANINGFUL question for this stream.
    #:
    #: False for play-grain streams that carry no player column (FTN charting). Such rows get
    #: `identity_status = NOT_APPLICABLE`, are excluded from `unresolved_identity.parquet`, and
    #: do NOT inflate `rows_not_canonically_identified`. Coverage reports
    #: `identity_applicable_rows = 0` so the absence is stated rather than implied by four zeros.
    identity_applicable: bool = True

    #: Columns the export must publish as real Booleans. FTN is 15/29 Boolean and the export
    #: declares only integer and float casts, so without this they publish as TEXT out of SQLite
    #: — `"false"` is a truthy string, which is how a charting flag silently inverts.
    boolean_columns: tuple[str, ...] = ()

    #: Earliest season this source exists at all. Not a preference — a property of the provider.
    #:
    #: FTN charting begins in 2022 and `nflreadpy.load_ftn_charting` RAISES for anything earlier.
    #: The capture applies ONE season list to EVERY spec, so a 2018-2025 run over a 2022+ source
    #: aborted the whole run (observed live: `failed_stream=ftn_charting, season=2018`). The
    #: fail-closed machinery behaved correctly — last-good stood, the marker named the failure —
    #: but a source's own start date is a declarable fact, not something to discover by crashing.
    #: This is the per-stream cousin of the seasonless-source capture-axis gap (Codex C5).
    #: Out-of-range seasons are RECORDED as skipped, never silently omitted.
    min_season: int | None = None

    #: Collapse rows that are EXACT content duplicates across every declared column, and
    #: reconcile the count. Opt-in, so no existing stream changes.
    #:
    #: Codex C8's rule: exact repeated payloads and distinct observations colliding on a
    #: candidate key are DIFFERENT failure classes and must not be treated as one. Measured on
    #: depth charts 2020-2024: 790 of 186,074 rows are exact full-row repeats, and after
    #: collapsing them there are ZERO semantic collisions on the declared grain. So the repeats
    #: are provider noise, not lost observations — but collapsing silently would hide a real
    #: upstream change, so the count is reported as `rows_collapsed_exact_duplicates`.
    #:
    #: This ONLY collapses byte-identical content. Two rows differing in any declared column
    #: still hit the grain check and still refuse.
    collapse_exact_duplicates: bool = False

    #: Columns that MUST be zero/absent on a row excluded by `exclude_unidentified_rows`.
    #: This is the exclusion's premise made executable rather than left in a docstring.
    exclude_requires_zero_columns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Fail closed on contradictory identity declarations (Codex C7).

        A nullable identity column alone would let a stream be half-declared — an identity kind
        with no column, or an exclusion policy for rows that were never identified — and each of
        those reads as working until the census is wrong.
        """
        if self.identity_applicable:
            if not self.identity_column or not self.identity_kind:
                raise UsageCaptureError(
                    f"stream {self.name}: identity_applicable is True but "
                    f"identity_column={self.identity_column!r} / "
                    f"identity_kind={self.identity_kind!r} — declare both or set "
                    "identity_applicable=False"
                )
        else:
            if self.identity_column or self.identity_kind:
                raise UsageCaptureError(
                    f"stream {self.name}: identity_applicable is False but still declares "
                    f"identity_column={self.identity_column!r} / "
                    f"identity_kind={self.identity_kind!r} — a stream with no player column "
                    "must not name one"
                )
            if self.exclude_unidentified_rows:
                raise UsageCaptureError(
                    f"stream {self.name}: exclude_unidentified_rows has no meaning when "
                    "identity_applicable is False — every row would be excluded"
                )

    #: Shapes this stream has had over time, resolved per batch from the observed
    #: column set. Empty means the stream has exactly one shape.
    eras: tuple[StreamEra, ...] = ()

    @property
    def stored_columns(self) -> tuple[str, ...]:
        """The table must hold the UNION of every era's columns.

        Otherwise an era-specific field has nowhere to go and is dropped SILENTLY
        at insert time — measured: the 2025 `season_type` value was declared by
        its era, produced by normalization, and then discarded because the table
        had been created from the default era's column list. Silent loss, no
        error, and only visible by querying for a column that was not there.
        """
        columns = list(self.columns)
        for era in self.eras:
            for column in era.columns:
                if column not in columns:
                    columns.append(column)
        base = (*columns, "dg_player_id", "identity_status", "row_key", "season_ingested")
        return (*base, "source_era") if self.eras else base

    @property
    def export_dtypes(self) -> dict[str, Any]:
        """Explicit per-column export types. Declared, never inferred — inference
        would silently retype a column the day its data happens to look numeric."""
        import polars as pl

        types: dict[str, Any] = {c: pl.Int64 for c in self.integer_columns}
        types.update({c: pl.Float64 for c in self.float_columns})
        types.update({c: pl.Boolean for c in self.boolean_columns})
        return types


_NGS_SHARED = (
    "season",
    "season_type",
    "week",
    "player_gsis_id",
    "player_display_name",
    "player_position",
    "team_abbr",
)

NGS_PASSING = StreamSpec(
    name="ngs_passing",
    table="ngs_passing",
    identity_column="player_gsis_id",
    identity_kind="gsis",
    grain=("season", "season_type", "week", "player_gsis_id"),
    columns=(
        *_NGS_SHARED,
        "avg_time_to_throw",
        "avg_completed_air_yards",
        "avg_intended_air_yards",
        "avg_air_yards_differential",
        "aggressiveness",
        "max_completed_air_distance",
        "avg_air_yards_to_sticks",
        "attempts",
        "pass_yards",
        "pass_touchdowns",
        "interceptions",
        "passer_rating",
        "completions",
        "completion_percentage",
        "expected_completion_percentage",
        "completion_percentage_above_expectation",
        "avg_air_distance",
        "max_air_distance",
    ),
    loader=None,  # bound at runtime; see build_streams
    loader_kwargs={"stat_type": "passing"},
    integer_columns=("season", "week", "attempts", "pass_yards", "pass_touchdowns",
                     "interceptions", "completions"),
    float_columns=("avg_time_to_throw", "avg_completed_air_yards", "avg_intended_air_yards",
                   "avg_air_yards_differential", "aggressiveness",
                   "max_completed_air_distance", "avg_air_yards_to_sticks", "passer_rating",
                   "completion_percentage", "expected_completion_percentage",
                   "completion_percentage_above_expectation", "avg_air_distance",
                   "max_air_distance"),
)

NGS_RUSHING = StreamSpec(
    name="ngs_rushing",
    table="ngs_rushing",
    identity_column="player_gsis_id",
    identity_kind="gsis",
    grain=("season", "season_type", "week", "player_gsis_id"),
    columns=(
        *_NGS_SHARED,
        "efficiency",
        "percent_attempts_gte_eight_defenders",
        "avg_time_to_los",
        "rush_attempts",
        "rush_yards",
        "avg_rush_yards",
        "rush_touchdowns",
        "expected_rush_yards",
        "rush_yards_over_expected",
        "rush_yards_over_expected_per_att",
        "rush_pct_over_expected",
    ),
    loader=None,
    loader_kwargs={"stat_type": "rushing"},
    integer_columns=("season", "week", "rush_attempts", "rush_yards", "rush_touchdowns"),
    float_columns=("efficiency", "percent_attempts_gte_eight_defenders", "avg_time_to_los",
                   "avg_rush_yards", "expected_rush_yards", "rush_yards_over_expected",
                   "rush_yards_over_expected_per_att", "rush_pct_over_expected"),
)

NGS_RECEIVING = StreamSpec(
    name="ngs_receiving",
    table="ngs_receiving",
    identity_column="player_gsis_id",
    identity_kind="gsis",
    grain=("season", "season_type", "week", "player_gsis_id"),
    columns=(
        *_NGS_SHARED,
        "avg_cushion",
        "avg_separation",
        "avg_intended_air_yards",
        "percent_share_of_intended_air_yards",
        "receptions",
        "targets",
        "catch_percentage",
        "yards",
        "rec_touchdowns",
        "avg_yac",
        "avg_expected_yac",
        "avg_yac_above_expectation",
    ),
    loader=None,
    # Explicit, not defaulted: nflreadpy's `stat_type` defaults to "passing", so an omitted
    # kwarg here silently loaded passing rows under a receiving label. The schema guard caught
    # it on the first live run — which is the guard doing exactly its job.
    loader_kwargs={"stat_type": "receiving"},
    integer_columns=("season", "week", "receptions", "targets", "rec_touchdowns"),
    float_columns=("avg_cushion", "avg_separation", "avg_intended_air_yards",
                   "percent_share_of_intended_air_yards", "catch_percentage", "yards",
                   "avg_yac", "avg_expected_yac", "avg_yac_above_expectation"),
)

SNAP_COUNTS = StreamSpec(
    name="snap_counts",
    table="player_snap_count",
    identity_column="pfr_player_id",
    identity_kind="pfr",
    grain=("game_id", "pfr_player_id"),
    columns=(
        "game_id",
        "pfr_game_id",
        "season",
        "game_type",
        "week",
        "player",
        "pfr_player_id",
        "position",
        "team",
        "opponent",
        "offense_snaps",
        "offense_pct",
        "defense_snaps",
        "defense_pct",
        "st_snaps",
        "st_pct",
    ),
    loader=None,
    loader_kwargs={},
    integer_columns=("season", "week"),
    float_columns=("offense_snaps", "offense_pct", "defense_snaps", "defense_pct",
                   "st_snaps", "st_pct"),
)


#: Weekly NFL injury report. Measured against the live source 2026-08-01
#: (17,882 rows 2023-2025; history reaches at least 2009).
#:
#: `date_modified` is IN THE GRAIN on purpose. The report is revised through the
#: week — Cade Stover 2024 wk15 HOU went Questionable (03:34 UTC) to Out (14:17
#: UTC) — and those are two real observations, not a conflict. Without it the
#: grain check would reject the revision as a duplicate and a last-wins store
#: would silently discard what we knew on Friday.
#:
#: `game_type` scopes the row, and `season_type` is DELIBERATELY ABSENT from the
#: contract. Measured 2026-08-01: the column exists ONLY in 2025 (16 columns for
#: 2015-2024, 17 for 2025). An earlier reading called it "66% null" — that was an
#: artifact of polars unioning schemas across a multi-season load, not a property
#: of the data. Declaring it would make every pre-2025 single-season load refuse
#: on schema drift, and it carries nothing `game_type` does not already give.
_INJURY_BASE_COLUMNS = (
    "season",
    "game_type",
    "team",
    "week",
    "gsis_id",
    "position",
    "full_name",
    "first_name",
    "last_name",
    "report_primary_injury",
    "report_secondary_injury",
    "report_status",
    "practice_primary_injury",
    "practice_secondary_injury",
    "practice_status",
)
_INJURY_BASE_GRAIN = ("season", "game_type", "week", "team", "gsis_id")

#: 2020-2024. `date_modified` is present and revisions DO occur — Cade Stover
#: 2024 wk15 went Questionable 03:34Z then Out 14:17Z — so the timestamp is part
#: of the grain and both observations survive.
INJURY_ERA_REVISIONED = StreamEra(
    name="revisioned",
    requires=("date_modified",),
    forbids=("season_type",),
    columns=(*_INJURY_BASE_COLUMNS, "date_modified"),
    grain=(*_INJURY_BASE_GRAIN, "date_modified"),
)

#: 2025 onward. nflverse traded `date_modified` for `season_type`. Measured:
#: ZERO duplicate groups on the five-column key, so this era cannot express a
#: revision at all. Its grain is therefore the five-column key, and a duplicate
#: there is still a refusal.
INJURY_ERA_SINGLE_OBSERVATION = StreamEra(
    name="single_observation",
    requires=("season_type",),
    forbids=("date_modified",),
    columns=(*_INJURY_BASE_COLUMNS, "season_type"),
    grain=_INJURY_BASE_GRAIN,
)


INJURIES = StreamSpec(
    name="injuries",
    table="nflverse_injury_report",
    identity_column="gsis_id",
    identity_kind="gsis",
    grain=INJURY_ERA_REVISIONED.grain,
    columns=INJURY_ERA_REVISIONED.columns,
    eras=(INJURY_ERA_REVISIONED, INJURY_ERA_SINGLE_OBSERVATION),
    loader=None,
    loader_kwargs={},
    integer_columns=("season", "week"),
    require_populated_grain=True,
    blank_as_null_columns=(
        "report_status",
        "report_primary_injury",
        "report_secondary_injury",
        "practice_status",
        "practice_primary_injury",
        "practice_secondary_injury",
        "position",
    ),
)


# ---------------------------------------------------------------------------
# PFR advanced stats (board block C, stream 1 of 6)
# ---------------------------------------------------------------------------
#
# Measured live 2026-08-04 (`nflreadpy 0.1.5`): 2018-2025, four stat types, 121,954
# rows. Column counts are IDENTICAL in every season — pass 24 · rush 16 · rec 17 ·
# def 29 — so this stream has no historical shape drift. Grain
# `(game_id, pfr_player_id)` measured zero-null and zero-duplicate in all four types.
# Identity: 121,688 canonical_resolved · 266 source_only · 0 conflict · 0 unknown.
#
# Each spec declares ONE explicit era even though the shape never changed. That is
# deliberate: `normalize_rows` enforces exact column-set equality only when
# `spec.eras` is non-empty (see the `if spec.eras:` branch). Without an era a NEW
# upstream column would be accepted and silently projected away — the same silent
# loss the era mechanism was built to stop. Declaring the era buys the refusal
# without changing behaviour for any existing stream.

_PFR_SHARED = (
    "game_id",
    "pfr_game_id",
    "season",
    "week",
    "game_type",
    "team",
    "opponent",
    "pfr_player_name",
    "pfr_player_id",
)
_PFR_GRAIN = ("game_id", "pfr_player_id")

_PFR_PASS_METRICS = (
    "passing_drops", "passing_drop_pct", "receiving_drop", "receiving_drop_pct",
    "passing_bad_throws", "passing_bad_throw_pct", "times_sacked", "times_blitzed",
    "times_hurried", "times_hit", "times_pressured", "times_pressured_pct",
    "def_times_blitzed", "def_times_hurried", "def_times_hitqb",
)
_PFR_RUSH_METRICS = (
    "carries", "rushing_yards_before_contact", "rushing_yards_before_contact_avg",
    "rushing_yards_after_contact", "rushing_yards_after_contact_avg",
    "rushing_broken_tackles", "receiving_broken_tackles",
)
_PFR_REC_METRICS = (
    "rushing_broken_tackles", "receiving_broken_tackles", "passing_drops",
    "passing_drop_pct", "receiving_drop", "receiving_drop_pct", "receiving_int",
    "receiving_rat",
)
_PFR_DEF_METRICS = (
    "def_ints", "def_targets", "def_completions_allowed", "def_completion_pct",
    "def_yards_allowed", "def_yards_allowed_per_cmp", "def_yards_allowed_per_tgt",
    "def_receiving_td_allowed", "def_passer_rating_allowed", "def_adot",
    "def_air_yards_completed", "def_yards_after_catch", "def_times_blitzed",
    "def_times_hurried", "def_times_hitqb", "def_sacks", "def_pressures",
    "def_tackles_combined", "def_missed_tackles", "def_missed_tackle_pct",
)


def _pfr_spec(name: str, stat_type: str, metrics: tuple[str, ...]) -> StreamSpec:
    columns = (*_PFR_SHARED, *metrics)
    return StreamSpec(
        name=name,
        table=name,
        identity_column="pfr_player_id",
        identity_kind="pfr",
        grain=_PFR_GRAIN,
        columns=columns,
        loader=None,  # bound in build_streams
        # Explicit, never defaulted: `load_pfr_advstats` DEFAULTS its stat_type, and an
        # omitted kwarg is exactly how NGS receiving once shipped passing rows.
        loader_kwargs={"stat_type": stat_type},
        integer_columns=("season", "week"),
        float_columns=metrics,
        refuse_non_finite=True,
        eras=(
            StreamEra(
                name=f"{stat_type}_v1",
                requires=(),
                forbids=(),
                columns=columns,
                grain=_PFR_GRAIN,
            ),
        ),
    )


PFR_PASS = _pfr_spec("pfr_pass", "pass", _PFR_PASS_METRICS)
PFR_RUSH = _pfr_spec("pfr_rush", "rush", _PFR_RUSH_METRICS)
PFR_REC = _pfr_spec("pfr_rec", "rec", _PFR_REC_METRICS)
PFR_DEF = _pfr_spec("pfr_def", "def", _PFR_DEF_METRICS)


# ---------------------------------------------------------------------------
# ff_opportunity — expected fantasy points (board block C, stream 2 of 6)
# ---------------------------------------------------------------------------
#
# Measured live 2026-08-04 (`nflreadpy 0.1.5`), seasons 2023-2025: 18,140 rows,
# 159 columns. TWO ROW CLASSES, not a broken grain:
#
#   * 16,860 PLAYER rows — grain `(game_id, player_id)` and `(season, week,
#     player_id)` both ZERO-duplicate. `player_id` is a GSIS id, so identity
#     resolves on our canonical key: 16,834 canonical_resolved / 26 source_only.
#   * 1,280 RESIDUAL rows — exactly ONE per `(game_id, posteam)`, `player_id`
#     null, no name, no position. 1,274 carry a nonzero `rec_attempt` but ZERO
#     realized production; their total `total_fantasy_points` is exactly 0.0
#     against 143,269.2 attributed (0.000%). An expected-value residual for
#     unattributed targets — NOT lost player production.
#
# An earlier reading called the 65 apparent duplicate groups a broken player
# grain. They were an artifact of grouping on a null `player_id`: the 65 buckets
# are season-week groupings of residual rows. Filtered to populated ids the
# player grain is perfectly unique.
#
# The residual rows are KEPT. An earlier design excluded them on the premise that they
# carry zero realized production — measured true for 2023-2025 and then applied to
# 2018-2025 WITHOUT being re-measured. It is FALSE: one row in 2022 carries 21.4
# fantasy points, 84 yards and 2 touchdowns, and the committed landing discarded it.
# Widening the grain to include `posteam` (unique in every season, measured) removes
# the need to exclude anything, so there is no longer a premise that can be wrong.
#
# `season` ships as String and `week` as Float64 in this source; both are
# declared integers and the existing normalization refuses a non-integral value
# rather than coercing one.

_FF_OPP_KEY = (
    'season', 'week', 'game_id', 'posteam', 'player_id', 'full_name', 'position',
)

_FF_OPP_METRICS = (
    'pass_attempt', 'rec_attempt', 'rush_attempt', 'pass_air_yards',
    'rec_air_yards', 'pass_completions', 'receptions', 'pass_completions_exp',
    'receptions_exp', 'pass_yards_gained', 'rec_yards_gained', 'rush_yards_gained',
    'pass_yards_gained_exp', 'rec_yards_gained_exp', 'rush_yards_gained_exp',
    'pass_touchdown', 'rec_touchdown', 'rush_touchdown', 'pass_touchdown_exp',
    'rec_touchdown_exp', 'rush_touchdown_exp', 'pass_two_point_conv',
    'rec_two_point_conv', 'rush_two_point_conv', 'pass_two_point_conv_exp',
    'rec_two_point_conv_exp', 'rush_two_point_conv_exp', 'pass_first_down',
    'rec_first_down', 'rush_first_down', 'pass_first_down_exp',
    'rec_first_down_exp', 'rush_first_down_exp', 'pass_interception',
    'rec_interception', 'pass_interception_exp', 'rec_interception_exp',
    'rec_fumble_lost', 'rush_fumble_lost', 'pass_fantasy_points_exp',
    'rec_fantasy_points_exp', 'rush_fantasy_points_exp', 'pass_fantasy_points',
    'rec_fantasy_points', 'rush_fantasy_points', 'total_yards_gained',
    'total_yards_gained_exp', 'total_touchdown', 'total_touchdown_exp',
    'total_first_down', 'total_first_down_exp', 'total_fantasy_points',
    'total_fantasy_points_exp', 'pass_completions_diff', 'receptions_diff',
    'pass_yards_gained_diff', 'rec_yards_gained_diff', 'rush_yards_gained_diff',
    'pass_touchdown_diff', 'rec_touchdown_diff', 'rush_touchdown_diff',
    'pass_two_point_conv_diff', 'rec_two_point_conv_diff',
    'rush_two_point_conv_diff', 'pass_first_down_diff', 'rec_first_down_diff',
    'rush_first_down_diff', 'pass_interception_diff', 'rec_interception_diff',
    'pass_fantasy_points_diff', 'rec_fantasy_points_diff',
    'rush_fantasy_points_diff', 'total_yards_gained_diff', 'total_touchdown_diff',
    'total_first_down_diff', 'total_fantasy_points_diff', 'pass_attempt_team',
    'rec_attempt_team', 'rush_attempt_team', 'pass_air_yards_team',
    'rec_air_yards_team', 'pass_completions_team', 'receptions_team',
    'pass_completions_exp_team', 'receptions_exp_team', 'pass_yards_gained_team',
    'rec_yards_gained_team', 'rush_yards_gained_team', 'pass_yards_gained_exp_team',
    'rec_yards_gained_exp_team', 'rush_yards_gained_exp_team',
    'pass_touchdown_team', 'rec_touchdown_team', 'rush_touchdown_team',
    'pass_touchdown_exp_team', 'rec_touchdown_exp_team', 'rush_touchdown_exp_team',
    'pass_two_point_conv_team', 'rec_two_point_conv_team',
    'rush_two_point_conv_team', 'pass_two_point_conv_exp_team',
    'rec_two_point_conv_exp_team', 'rush_two_point_conv_exp_team',
    'pass_first_down_team', 'rec_first_down_team', 'rush_first_down_team',
    'pass_first_down_exp_team', 'rec_first_down_exp_team',
    'rush_first_down_exp_team', 'pass_interception_team', 'rec_interception_team',
    'pass_interception_exp_team', 'rec_interception_exp_team',
    'rec_fumble_lost_team', 'rush_fumble_lost_team', 'pass_fantasy_points_exp_team',
    'rec_fantasy_points_exp_team', 'rush_fantasy_points_exp_team',
    'pass_fantasy_points_team', 'rec_fantasy_points_team',
    'rush_fantasy_points_team', 'pass_completions_diff_team',
    'receptions_diff_team', 'pass_yards_gained_diff_team',
    'rec_yards_gained_diff_team', 'rush_yards_gained_diff_team',
    'pass_touchdown_diff_team', 'rec_touchdown_diff_team',
    'rush_touchdown_diff_team', 'pass_two_point_conv_diff_team',
    'rec_two_point_conv_diff_team', 'rush_two_point_conv_diff_team',
    'pass_first_down_diff_team', 'rec_first_down_diff_team',
    'rush_first_down_diff_team', 'pass_interception_diff_team',
    'rec_interception_diff_team', 'pass_fantasy_points_diff_team',
    'rec_fantasy_points_diff_team', 'rush_fantasy_points_diff_team',
    'total_yards_gained_team', 'total_yards_gained_exp_team',
    'total_yards_gained_diff_team', 'total_touchdown_team',
    'total_touchdown_exp_team', 'total_touchdown_diff_team',
    'total_first_down_team', 'total_first_down_exp_team',
    'total_first_down_diff_team', 'total_fantasy_points_team',
    'total_fantasy_points_exp_team', 'total_fantasy_points_diff_team',
)

FF_OPPORTUNITY = StreamSpec(
    name="ff_opportunity",
    table="ff_opportunity",
    identity_column="player_id",
    identity_kind="gsis",
    # WIDENED from (game_id, player_id) after the exclusion premise FAILED on real data.
    # Measured 2018-2025: (game_id, posteam, player_id) is unique in EVERY season including the
    # residual rows, with game_id and posteam never null. So nothing needs excluding at all —
    # the residual rows store alongside the player rows and resolve to `unknown` identity,
    # which is honest and loses nothing.
    grain=("game_id", "posteam", "player_id"),
    columns=(*_FF_OPP_KEY, *_FF_OPP_METRICS),
    loader=None,  # bound in build_streams
    loader_kwargs={},
    integer_columns=("season", "week"),
    float_columns=_FF_OPP_METRICS,
    refuse_non_finite=True,
    # `player_id` is null on the residual rows by design; game_id and posteam never are.
    require_populated_grain=False,
    eras=(
        StreamEra(
            name="ffopportunity_v1",
            requires=(),
            forbids=(),
            columns=(*_FF_OPP_KEY, *_FF_OPP_METRICS),
            # The ERA owns the grain and REPLACES the spec's during normalization
            # (nflverse_usage.py, era resolution). Widening only the spec-level grain left this
            # one stale and the old key silently still in force — the same StreamEra property
            # Codex explained in C3, missed a second time.
            grain=("game_id", "posteam", "player_id"),
        ),
    ),
)


# ---------------------------------------------------------------------------
# FTN charting (board block C, stream 3 of 6) — PLAY-GRAIN, NO PLAYER IDENTITY
# ---------------------------------------------------------------------------
#
# Measured live 2026-08-04 (`nflreadpy 0.1.5`): 2022-2025, 185,215 rows, 29 columns
# in every season — charting begins 2022, so 2022 is the true start, not a gap.
# Grain `(nflverse_game_id, nflverse_play_id)`: 143,572/143,572 unique with ZERO
# nulls over 2023-2025 — the cleanest grain of the six loaders.
#
# THIS STREAM HAS NO PLAYER COLUMN. Not a sparse one — none. It is charting ABOUT
# PLAYS: was there motion, play action, a blitz, a drop. Declaring a nullable
# identity column would report all 143,572 plays as unresolved PLAYERS and bury the
# real unresolved-player artifact, so `identity_applicable=False` and the rows carry
# `NOT_APPLICABLE`, which the export excludes from `unresolved_identity.parquet`.
#
# 15 of the 29 columns are Boolean. SQLite has no Boolean type, so without an
# explicit Boolean cast the export publishes them as TEXT — and `"false"` is a
# truthy string, which is how a charting flag silently inverts.
#
# `date_pulled` is a provider timestamp, declared as an ordinary string column: it
# is scrape metadata, not an observation coordinate, and it is NOT in the grain.

_FTN_KEY = (
    "ftn_game_id",
    "nflverse_game_id",
    "season",
    "week",
    "ftn_play_id",
    "nflverse_play_id",
)
_FTN_STRING = ("starting_hash", "qb_location", "read_thrown", "date_pulled")
_FTN_INT = ("season", "week", "ftn_game_id", "ftn_play_id", "nflverse_play_id",
            "n_offense_backfield", "n_defense_box", "n_blitzers", "n_pass_rushers")
_FTN_BOOL = (
    "is_no_huddle", "is_motion", "is_play_action", "is_screen_pass", "is_rpo",
    "is_trick_play", "is_qb_out_of_pocket", "is_interception_worthy", "is_throw_away",
    "is_catchable_ball", "is_contested_ball", "is_created_reception", "is_drop",
    "is_qb_sneak", "is_qb_fault_sack",
)
_FTN_COLUMNS = (
    *_FTN_KEY,
    "starting_hash",
    "qb_location",
    "n_offense_backfield",
    "n_defense_box",
    *_FTN_BOOL[:9],
    "read_thrown",
    *_FTN_BOOL[9:14],
    "n_blitzers",
    "n_pass_rushers",
    _FTN_BOOL[14],
    "date_pulled",
)
_FTN_GRAIN = ("nflverse_game_id", "nflverse_play_id")

FTN_CHARTING = StreamSpec(
    name="ftn_charting",
    table="ftn_charting",
    identity_column="",
    identity_kind="",
    identity_applicable=False,
    grain=_FTN_GRAIN,
    columns=_FTN_COLUMNS,
    loader=None,  # bound in build_streams
    loader_kwargs={},
    integer_columns=_FTN_INT,
    boolean_columns=_FTN_BOOL,
    require_populated_grain=True,
    min_season=2022,  # charting begins 2022; the loader RAISES below it
    eras=(
        StreamEra(
            name="ftn_v1",
            requires=(),
            forbids=(),
            columns=_FTN_COLUMNS,
            grain=_FTN_GRAIN,
        ),
    ),
)


# ---------------------------------------------------------------------------
# Depth charts (board block C, stream 4 of 6) — TWO ERAS, DIFFERENT GRAINS
# ---------------------------------------------------------------------------
#
# Measured live 2026-08-04 (`nflreadpy 0.1.5`). The era boundary is PER SEASON and
# clean — an earlier reading called the eras "disjoint with nulls", which was an
# artifact of unioning schemas across a multi-season load, not a property of the data:
#
#   * 2020-2024 WEEKLY era — 15 columns, ~37k rows/season, keyed on the game week.
#   * 2025+ DAILY era      — 12 columns, 554,215 rows in 2025 alone. nflverse swapped
#     to a daily snapshot (`dt`) with ESPN position slots. It shares only `gsis_id`
#     and `team`/`club_code` semantics with the weekly era.
#
# `StreamEra` already carries a per-era grain (it is how the two injury eras work), so
# this needs no new era machinery — only the two shapes declared honestly.
#
# WEEKLY GRAIN, and why each coordinate is there:
#   `game_type` is load-bearing — week 19 exists as BOTH `REG` and `WC`, and without
#   it a player's wildcard row collides with his week-19 regular-season row.
#   `week` is NULL for exactly the `SBBYE` (Super Bowl bye) rows — 214-257 per season,
#   a real category, not corruption. `require_populated_grain` is therefore False for
#   this stream; `game_type` keeps those rows distinguishable.
#
# EXACT DUPLICATES: 790 of 186,074 weekly rows (2020-2024) are exact full-row repeats,
# and after collapsing them there are ZERO semantic collisions on the declared grain.
# Provider noise, not lost observations — collapsed deterministically and COUNTED.
#
# DAILY GRAIN uses `espn_id`, not `gsis_id`: measured, `(dt, team, espn_id, pos_grp,
# pos_slot, pos_rank)` is 554,215/554,215 unique with ZERO nulls, while `gsis_id` is
# null on 5,577 rows. Identity still resolves on `gsis_id` (those 5,577 become
# `unknown`, which is honest) — the grain and the identity key are different questions.

_DEPTH_WEEKLY_COLUMNS = (
        'club_code', 'depth_position', 'depth_team', 'elias_id', 'first_name',
        'football_name', 'formation', 'full_name', 'game_type', 'gsis_id',
        'jersey_number', 'last_name', 'position', 'season', 'week',
)
_DEPTH_WEEKLY_GRAIN = (
    "season", "game_type", "week", "club_code", "gsis_id", "depth_position",
    "formation", "depth_team",
)
_DEPTH_DAILY_COLUMNS = (
        'dt', 'espn_id', 'gsis_id', 'player_name', 'pos_abb', 'pos_grp',
        'pos_grp_id', 'pos_id', 'pos_name', 'pos_rank', 'pos_slot', 'team',
)
_DEPTH_DAILY_GRAIN = ("dt", "team", "espn_id", "pos_grp", "pos_slot", "pos_rank")

DEPTH_WEEKLY_ERA = StreamEra(
    name="weekly",
    requires=("week",),
    forbids=("dt",),
    columns=_DEPTH_WEEKLY_COLUMNS,
    grain=_DEPTH_WEEKLY_GRAIN,
)
DEPTH_DAILY_ERA = StreamEra(
    name="daily",
    requires=("dt",),
    forbids=("week",),
    columns=_DEPTH_DAILY_COLUMNS,
    grain=_DEPTH_DAILY_GRAIN,
)

DEPTH_CHARTS = StreamSpec(
    name="depth_charts",
    table="depth_charts",
    identity_column="gsis_id",
    identity_kind="gsis",
    grain=_DEPTH_WEEKLY_GRAIN,
    columns=_DEPTH_WEEKLY_COLUMNS,
    loader=None,  # bound in build_streams
    loader_kwargs={},
    integer_columns=("season",),
    collapse_exact_duplicates=True,
    require_populated_grain=False,  # SBBYE rows legitimately carry a null week
    eras=(DEPTH_WEEKLY_ERA, DEPTH_DAILY_ERA),
)


def build_streams() -> tuple[StreamSpec, ...]:
    """Bind the nflreadpy loaders. Imported lazily so the module stays importable offline."""
    import nflreadpy

    def _bind(spec: StreamSpec, loader: Callable[..., Any]) -> StreamSpec:
        return StreamSpec(
            name=spec.name,
            table=spec.table,
            identity_column=spec.identity_column,
            identity_kind=spec.identity_kind,
            grain=spec.grain,
            columns=spec.columns,
            loader=loader,
            loader_kwargs=spec.loader_kwargs,
            integer_columns=spec.integer_columns,
            float_columns=spec.float_columns,
            blank_as_null_columns=spec.blank_as_null_columns,
            require_populated_grain=spec.require_populated_grain,
            refuse_non_finite=spec.refuse_non_finite,
            exclude_unidentified_rows=spec.exclude_unidentified_rows,
            identity_applicable=spec.identity_applicable,
            boolean_columns=spec.boolean_columns,
            min_season=spec.min_season,
            collapse_exact_duplicates=spec.collapse_exact_duplicates,
            exclude_requires_zero_columns=spec.exclude_requires_zero_columns,
            eras=spec.eras,
        )

    return (
        _bind(NGS_PASSING, nflreadpy.load_nextgen_stats),
        _bind(NGS_RUSHING, nflreadpy.load_nextgen_stats),
        _bind(NGS_RECEIVING, nflreadpy.load_nextgen_stats),
        _bind(SNAP_COUNTS, nflreadpy.load_snap_counts),
        _bind(INJURIES, nflreadpy.load_injuries),
        _bind(PFR_PASS, nflreadpy.load_pfr_advstats),
        _bind(PFR_RUSH, nflreadpy.load_pfr_advstats),
        _bind(PFR_REC, nflreadpy.load_pfr_advstats),
        _bind(PFR_DEF, nflreadpy.load_pfr_advstats),
        _bind(FF_OPPORTUNITY, nflreadpy.load_ff_opportunity),
        _bind(FTN_CHARTING, nflreadpy.load_ftn_charting),
        _bind(DEPTH_CHARTS, nflreadpy.load_depth_charts),
    )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _row_key(spec: StreamSpec, row: Mapping[str, Any]) -> str:
    return "|".join(f"{col}={row.get(col)}" for col in spec.grain)


def normalize_rows(
    records: Sequence[Mapping[str, Any]],
    *,
    spec: StreamSpec,
    season: int,
    identity: IdentityIndex,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attach canonical identity and key each row. Returns ``(rows, coverage)``.

    Missing source columns are a **hard** failure, not a silent null: nflverse adding or renaming a
    field must surface as a named refusal rather than a column of empties that looks like real
    absence of data.
    """
    if not records:
        return [], _coverage(spec, season, [], missing_columns=[])

    # A non-mapping record is API MISUSE, not data corruption: fail loud and name the offending
    # index and type rather than letting `.keys()` raise an unattributed AttributeError deeper in.
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise UsageCaptureError(
                f"nflverse_bad_record_type: stream {spec.name} season {season} record "
                f"{index} is {type(record).__name__}, expected a mapping"
            )

    excluded_unidentified = 0

    available = set(records[0].keys())

    # Resolve the era from the column set before anything else — the declared
    # columns and grain depend on it.
    era_name = None
    columns, grain = spec.columns, spec.grain
    if spec.eras:
        matched = [era for era in spec.eras if era.matches(available)]
        if not matched:
            declared = {era.name: sorted(era.columns) for era in spec.eras}
            extra = {
                era.name: sorted(available - set(era.columns)) for era in spec.eras
            }
            absent = {
                era.name: sorted(set(era.columns) - available) for era in spec.eras
            }
            raise UsageCaptureError(
                f"nflverse_unknown_era: stream {spec.name} season {season} matches no "
                f"declared era exactly. Observed {sorted(available)}; declared "
                f"{declared}; unexpected-per-era {extra}; missing-per-era {absent}. "
                "Refusing rather than mapping an unrecognised shape onto whichever era "
                "looks closest — an accepted-and-dropped column is silent data loss"
            )
        if len(matched) > 1:
            raise UsageCaptureError(
                f"nflverse_ambiguous_era: stream {spec.name} season {season} matches "
                f"{[era.name for era in matched]} simultaneously; declared eras must be "
                "mutually exclusive. Taking the first match would make the contract "
                "depend on declaration order"
            )
        match = matched[0]
        era_name, columns, grain = match.name, match.columns, match.grain

        # Validate EVERY record, not only records[0]. Choosing the era from the
        # first mapping and never re-checking meant a heterogeneous batch — a
        # later row with an extra provider field, or missing a declared one —
        # was accepted and silently mangled, which is the exact defect the exact-
        # match rule was added to prevent (Codex R2-B1). The one-row positive
        # control could not see it.
        expected_keys = set(match.columns)
        for index, record in enumerate(records):
            observed = set(record.keys())
            if observed != expected_keys:
                raise UsageCaptureError(
                    f"nflverse_heterogeneous_batch: stream {spec.name} season "
                    f"{season} record {index} does not match era {match.name!r} "
                    f"exactly — unexpected {sorted(observed - expected_keys)}, "
                    f"missing {sorted(expected_keys - observed)}. Every record in a "
                    "batch must carry the same declared shape; validating only the "
                    "first row lets a later one be silently dropped or nulled"
                )
    spec = replace(spec, columns=columns, grain=grain)

    missing = [col for col in spec.columns if col not in available]
    if missing:
        raise UsageCaptureError(
            f"nflverse_schema_drift: stream {spec.name} season {season} is missing "
            f"{missing} — the upstream shape changed; storing nulls would look like missing "
            "data rather than a changed contract"
        )

    if spec.exclude_unidentified_rows:
        # MOVED here from before schema validation (Codex da00235-1). Filtering first meant
        # upstream drift confined to a row we were about to exclude was accepted and dropped —
        # a contract breach is a contract breach wherever it appears.
        kept, dropped = [], []
        for record in records:
            (kept if str(record.get(spec.identity_column) or "").strip() else dropped).append(
                record
            )

        # ENFORCE the premise the exclusion rests on (Codex da00235-2). Excluding these rows is
        # justified ONLY by the measurement that they carry zero realized production. The code
        # never checked it, so a blank-id row with 10 real fantasy points was silently
        # discarded. If the premise stops holding, REFUSE — do not quietly drop real production.
        for record in dropped:
            offending = {
                column: record.get(column)
                for column in spec.exclude_requires_zero_columns
                if record.get(column) not in (None, 0, 0.0, "", "0", "0.0")
            }
            if offending:
                raise UsageCaptureError(
                    f"nflverse_excluded_row_carries_production: stream {spec.name} season "
                    f"{season} would exclude a row with no {spec.identity_column}, but it "
                    f"carries {offending}. The exclusion premise is that unidentified rows "
                    "hold no realized production; refusing rather than discarding it."
                )

        excluded_unidentified = len(dropped)
        records = kept
        if not records:
            coverage = _coverage(spec, season, [], missing_columns=[])
            coverage["rows_excluded_unidentified"] = excluded_unidentified
            return [], coverage

    collapsed_exact = 0
    if spec.collapse_exact_duplicates:
        # Deterministic: first occurrence wins and input order is preserved, so a replay
        # produces byte-identical output. Keyed on the DECLARED columns only — an undeclared
        # provider field cannot make two otherwise-identical rows look distinct.
        seen_content: set[tuple] = set()
        deduped: list[Mapping[str, Any]] = []
        for record in records:
            fingerprint = tuple(
                # repr, not str: `None` and the string "None" must not collide.
                (column, repr(record.get(column)))
                for column in columns
            )
            if fingerprint in seen_content:
                collapsed_exact += 1
                continue
            seen_content.add(fingerprint)
            deduped.append(record)
        records = deduped

    rows: list[dict[str, Any]] = []
    for record in records:
        if spec.identity_applicable:
            dg_player_id, status = identity.resolve(
                record.get(spec.identity_column), kind=spec.identity_kind
            )
        else:
            # Not "we looked and failed" — there is nothing to look at. See NOT_APPLICABLE.
            dg_player_id, status = None, NOT_APPLICABLE
        row = {col: record.get(col) for col in spec.columns}
        if era_name is not None:
            row["source_era"] = era_name
        # The 2020 source types season/week as Float64 while 2021+ types them
        # Int32, so the store held '2020.0' and '1.0' — and `season == 2020`
        # then misses the whole season. Normalize integral values; refuse a
        # genuinely fractional one rather than inventing a coercion.
        for col in spec.integer_columns:
            value = row.get(col)
            if value is None:
                continue
            if isinstance(value, bool):
                # `True` is not week 1. Falling through left a bool in the key
                # and deferred the failure to a later export cast (Codex M1).
                raise UsageCaptureError(
                    f"nflverse_non_integer: stream {spec.name} season {season} has "
                    f"{col}={value!r}, a bool where an integer is declared"
                )
            try:
                as_float = float(value)
            except (TypeError, ValueError) as exc:
                raise UsageCaptureError(
                    f"nflverse_non_integer: stream {spec.name} season {season} has "
                    f"{col}={value!r}, which is not numeric; the normalization "
                    "contract must distinguish an integer from a non-integer rather "
                    "than deferring to an export cast after the season is stored"
                ) from exc
            if as_float != as_float or as_float in (float("inf"), float("-inf")):
                raise UsageCaptureError(
                    f"nflverse_non_integer: stream {spec.name} season {season} has "
                    f"{col}={value!r}, which is not finite"
                )
            if not as_float.is_integer():
                raise UsageCaptureError(
                    f"nflverse_non_integer: stream {spec.name} season {season} has "
                    f"{col}={value!r}, which is not a whole number; coercing it would "
                    "invent a fact"
                )
            row[col] = int(as_float)
        if spec.refuse_non_finite:
            # A NaN or inf reaching a float column silently poisons every downstream
            # aggregate. Refuse rather than null: the export already refuses a cast that
            # loses non-null values, so nulling here would contradict it.
            for col in spec.float_columns:
                value = row.get(col)
                if value is None or isinstance(value, str):
                    continue
                try:
                    as_float = float(value)
                except (TypeError, ValueError):
                    continue  # non-numeric text is the export cast's contract, not this one
                if as_float != as_float or as_float in (float("inf"), float("-inf")):
                    raise UsageCaptureError(
                        f"nflverse_non_finite: stream {spec.name} season {season} has "
                        f"{col}={value!r}, which is not finite; refusing rather than "
                        "nulling, which would make corruption indistinguishable from "
                        "missingness"
                    )
        for col in spec.blank_as_null_columns:
            value = row.get(col)
            if isinstance(value, str) and not value.strip():
                row[col] = None
        row["dg_player_id"] = dg_player_id
        row["identity_status"] = status
        if spec.require_populated_grain:
            # Read the NORMALIZED row, not the raw record. Reading `record` meant
            # 2020.0/1.0 and 2020/1 normalized to identical stored coordinates yet
            # produced DIFFERENT row keys, so one observation was stored twice and
            # the duplicate gate was satisfied by the divergence it should have
            # caught (Codex B2).
            blank_grain = [
                col
                for col in spec.grain
                if row.get(col) is None
                or (isinstance(row.get(col), str) and not str(row[col]).strip())
            ]
            if blank_grain:
                raise UsageCaptureError(
                    f"nflverse_blank_grain: stream {spec.name} season {season} has a row "
                    f"with absent grain coordinate(s) {blank_grain} — the grain is what "
                    "makes two observations distinguishable; keying on a blank silently "
                    "collapses them"
                )
        row["row_key"] = _row_key(spec, row)
        row["season_ingested"] = str(season)
        rows.append(row)

    keys = [r["row_key"] for r in rows]
    if len(keys) != len(set(keys)):
        duplicates = sorted({k for k in keys if keys.count(k) > 1})[:5]
        raise UsageCaptureError(
            f"nflverse_grain_violation: stream {spec.name} season {season} has duplicate rows at "
            f"its declared grain {spec.grain}; examples {duplicates} — refusing to store a grain "
            "that silently drops rows"
        )

    coverage = _coverage(spec, season, rows, missing_columns=[])
    if spec.collapse_exact_duplicates:
        # Reported even when zero: a silently absent key cannot be distinguished from a run
        # where nothing was collapsed, and the whole point is that the collapse is visible.
        coverage["rows_collapsed_exact_duplicates"] = collapsed_exact
    if spec.exclude_unidentified_rows:
        # Additive, and ONLY for opted-in specs, so every existing stream's coverage dict is
        # byte-identical to before. Reconciliation, not a silent drop.
        coverage["rows_excluded_unidentified"] = excluded_unidentified
    return rows, coverage


def _coverage(
    spec: StreamSpec,
    season: int,
    rows: Sequence[Mapping[str, Any]],
    *,
    missing_columns: Sequence[str],
) -> dict[str, Any]:
    by_status = {
        status: [r for r in rows if r["identity_status"] == status]
        for status in (CANONICAL_RESOLVED, SOURCE_ONLY, CONFLICT, UNKNOWN)
    }
    # Rows for which identity is a meaningful question. For a play-grain stream this is 0, and
    # the four buckets below are all 0 too — so the reconciliation invariant is
    # `identity_applicable_rows == sum(the four buckets)`, which holds for BOTH kinds of stream
    # (for an identity-bearing stream it also equals rows_total). Stating the zero explicitly is
    # the point: four zeros alone cannot distinguish "no players here" from "nothing resolved".
    identity_applicable_rows = len(rows) if spec.identity_applicable else 0

    return {
        "schema_version": SCHEMA_VERSION,
        "stream": spec.name,
        "season": season,
        "rows_total": len(rows),
        "identity_applicable_rows": identity_applicable_rows,
        # Four counts, never one. "Not canonically identified" is the sum of the last three and is
        # reported explicitly so no single zero can stand in for identity.
        "rows_canonical_resolved": len(by_status[CANONICAL_RESOLVED]),
        "rows_source_only": len(by_status[SOURCE_ONLY]),
        "rows_conflict": len(by_status[CONFLICT]),
        "rows_unknown": len(by_status[UNKNOWN]),
        "rows_not_canonically_identified": sum(
            len(by_status[s]) for s in (SOURCE_ONLY, CONFLICT, UNKNOWN)
        ),
        "source_only_ids": sorted(
            {str(r[spec.identity_column]) for r in by_status[SOURCE_ONLY]}
        )[:50],
        "conflict_ids": sorted({str(r[spec.identity_column]) for r in by_status[CONFLICT]}),
        "missing_columns": list(missing_columns),
    }


# ---------------------------------------------------------------------------
# Durable store
# ---------------------------------------------------------------------------

#: **A row here means a real successful capture.** That single invariant is the design, and it is
#: Codex's (TW30N integration review), taken over my own richer version because it needs no schema
#: change and cannot lie: a failed retry leaves the last-good row untouched and reports itself in
#: the run marker, and a ``failed`` row is written only when there is no prior success to preserve.
#: ``ingested_at`` on an ``ok`` row is therefore the last-good timestamp — staleness is readable
#: from the store alone without overloading ``status`` with attempt state.
_CAPTURE_COLUMNS = (
    "stream_season",
    "stream",
    "season",
    "status",
    "rows_total",
    "coverage_json",
    "failure_reason",
    "content_hash",
    "ingested_at",
)


def _projection_fingerprint(spec: StreamSpec) -> str:
    """The persisted projection contract, as part of the idempotence identity.

    Hashing rows ALONE meant a schema widening returned `unchanged`: the same
    normalized rows had already been stored through a narrower projection, so the
    new columns stayed NULL and only a manual DELETE recovered it (Codex B3).
    Same rows + different persisted projection must NOT be `unchanged`.
    """
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stored_columns": list(spec.stored_columns),
        "grain": list(spec.grain),
        "integer_columns": list(spec.integer_columns),
        "blank_as_null_columns": list(spec.blank_as_null_columns),
        "eras": [era.name for era in spec.eras],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _coverage_fingerprint(coverage: Mapping[str, Any]) -> str:
    """The reconciliation counters that make two same-rows captures genuinely different."""
    keys = (
        "rows_total",
        "rows_canonical_resolved",
        "rows_source_only",
        "rows_conflict",
        "rows_unknown",
        "rows_not_canonically_identified",
        "rows_excluded_unidentified",
        "rows_collapsed_exact_duplicates",
        "identity_applicable_rows",
    )
    return "|".join(f"{k}={coverage.get(k)}" for k in keys)


def _rows_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = sorted(
        (json.dumps(row, sort_keys=True, default=str) for row in rows),
    )
    return hashlib.sha256("\n".join(payload).encode("utf-8")).hexdigest()


def read_only_summary(db_path: Path) -> dict[str, Any]:
    """Inspect the store without the power to change it.

    `--summary` promised "read-only, full stop", but it built a UsageStore, whose
    constructor runs CREATE TABLE IF NOT EXISTS for every spec in build_streams().
    Adding a fifth stream therefore made a read-only command create a table in an
    existing four-stream database (Codex reproduced it by hashing the file before
    and after). Intent is not a guarantee: this opens SQLite with `mode=ro`, which
    physically cannot write, and reads only tables that already exist.
    """
    if not Path(db_path).exists():
        return {"captures": [], "tables": {}}

    conn = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        present = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        captures: list[dict[str, Any]] = []
        if "nflverse_capture" in present:
            cursor = conn.execute(
                "SELECT stream, season, status, rows_total, coverage_json "
                "FROM nflverse_capture ORDER BY stream, season"
            )
            for stream, season, status, rows_total, coverage_json in cursor:
                captures.append(
                    {
                        "stream": stream,
                        "season": season,
                        "status": status,
                        "rows_total": rows_total,
                        "coverage": json.loads(coverage_json) if coverage_json else {},
                    }
                )
        tables = {
            spec.table: (
                conn.execute(f"SELECT COUNT(*) FROM {spec.table}").fetchone()[0]
                if spec.table in present
                else None
            )
            for spec in build_streams()
        }
        return {"captures": captures, "tables": tables}
    finally:
        conn.close()


class UsageStore:
    """Content-addressed, reconciling store, one table per stream.

    Idempotence is per ``(stream, season)`` and proven by content: if the season's rows hash to
    what is already stored, **nothing is written** — not a row, not a timestamp. If they differ,
    that season's rows are replaced wholesale, so a row withdrawn upstream cannot survive as a
    phantom.
    """

    def __init__(self, db_path: Path | str, specs: Sequence[StreamSpec]) -> None:
        self.db_path = Path(db_path)
        self.specs = {spec.name: spec for spec in specs}
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS nflverse_capture ("
                + ", ".join(f"{c} TEXT" for c in _CAPTURE_COLUMNS)
                + ", PRIMARY KEY (stream_season))"
            )
            self._assert_schema(conn, "nflverse_capture", _CAPTURE_COLUMNS)
            for spec in specs:
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {spec.table} ("
                    + ", ".join(f"{c} TEXT" for c in spec.stored_columns)
                    + ", PRIMARY KEY (row_key))"
                )
                self._assert_schema(conn, spec.table, spec.stored_columns)

    @staticmethod
    def migrate_additive_columns(
        db_path: Path, specs: Sequence[StreamSpec]
    ) -> dict[str, list[str]]:
        """EXPLICIT, reproducible additive migration. Never runs implicitly.

        `UsageStore.__init__` still FAILS CLOSED on a schema mismatch — that
        contract is deliberate and predates this work, and silently widening a
        store on every open would be the same silent-change class this module
        exists to refuse. This is the operator's reproducible replacement for the
        two hand-run `ALTER TABLE` statements that got production to its current
        shape (Codex B5), and it is additive only: it never renames, drops,
        retypes, or backfills. The widened columns repopulate on the next capture
        because the projection fingerprint makes the season read as changed (B3).
        """
        added: dict[str, list[str]] = {}
        conn = sqlite3.connect(db_path)
        try:
            for spec in specs:
                new_columns = UsageStore._additive_gap(
                    conn, spec.table, spec.stored_columns
                )
                for column in new_columns:
                    conn.execute(
                        f"ALTER TABLE {spec.table} ADD COLUMN {column} TEXT"
                    )
                if new_columns:
                    added[spec.table] = new_columns
            conn.commit()
        finally:
            conn.close()
        return added

    @staticmethod
    def _additive_gap(
        conn: sqlite3.Connection, table: str, expected: Sequence[str]
    ) -> list[str]:
        """Declared-but-absent columns for an EXISTING table. Never mutates.

        Production reached its current shape through two hand-run `ALTER TABLE`
        statements and a manual delete, which meant the schema transition existed
        nowhere in code and could not be reproduced on another machine or from a
        fresh clone (Codex B5). This makes the narrow, safe half of that
        reproducible. It deliberately does NOT rename, drop, retype, or backfill:
        any of those is a real migration needing its own decision, and the
        widened columns are repopulated because the projection fingerprint now
        makes the next capture see the season as changed (B3).
        """
        actual = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if not actual:
            return []
        return [column for column in expected if column not in actual]

    @staticmethod
    def _assert_schema(
        conn: sqlite3.Connection, table: str, expected: Sequence[str]
    ) -> None:
        actual = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        missing = [column for column in expected if column not in actual]
        if missing:
            raise UsageCaptureError(
                f"nflverse_usage_schema_mismatch: {table} is missing {missing} for "
                f"{SCHEMA_VERSION}. Additive widening is NOT automatic — the store fails "
                "closed on purpose. Run the explicit, reproducible migration "
                "`UsageStore.migrate_additive_columns(db_path, specs)`, which adds "
                "declared-but-absent columns and nothing else. A column still absent "
                "afterwards means a NON-ADDITIVE change (rename, retype, drop) that needs "
                "its own decision — refusing rather than writing mixed-schema rows"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def apply_season(
        self,
        spec: StreamSpec,
        *,
        season: int,
        rows: Sequence[Mapping[str, Any]],
        coverage: Mapping[str, Any],
        ingested_at: str,
    ) -> str:
        key = f"{spec.name}:{season}"
        # Identity = rows AND the projection they are persisted through.
        digest = hashlib.sha256(
            # Coverage is part of the OBSERVATION, not decoration: two captures with
            # identical stored rows but a different excluded/collapsed count are different
            # facts. Hashing only the stored rows returned `unchanged` and left durable
            # SQLite coverage stale against the run marker — two truth surfaces disagreeing
            # (Codex da00235-3). Only the reconciliation counters are included; volatile
            # fields like ids/timestamps would defeat idempotence.
            f"{_rows_hash(rows)}|{_projection_fingerprint(spec)}"
            f"|{_coverage_fingerprint(coverage)}".encode("utf-8")
        ).hexdigest()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT content_hash, status FROM nflverse_capture WHERE stream_season = ?",
                (key,),
            ).fetchone()
            # A `failed` row always carries content_hash NULL, so this branch can only be
            # reached from a real prior success — no recovery special-case is needed.
            if existing is not None and existing["content_hash"] == digest:
                return "unchanged"

            # Reconcile: this season's stored rows become exactly the rows we just fetched.
            conn.execute(
                f"DELETE FROM {spec.table} WHERE season_ingested = ?", (str(season),)
            )
            for row in rows:
                conn.execute(
                    f"INSERT OR REPLACE INTO {spec.table} "
                    f"({', '.join(spec.stored_columns)}) "
                    f"VALUES ({', '.join('?' for _ in spec.stored_columns)})",
                    [row.get(c) for c in spec.stored_columns],
                )
            conn.execute(
                f"INSERT OR REPLACE INTO nflverse_capture ({', '.join(_CAPTURE_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _CAPTURE_COLUMNS)})",
                [
                    key,
                    spec.name,
                    str(season),
                    "ok",
                    len(rows),
                    json.dumps(coverage, sort_keys=True, default=str),
                    None,  # failure_reason — an ok row never carries one
                    digest,
                    ingested_at,
                ],
            )
            return "inserted" if existing is None else "updated"

    def record_failure(
        self, stream: str, season: int, reason: str, ingested_at: str
    ) -> None:
        """Record a failed attempt **without ever disturbing a prior success.**

        My first version overwrote the whole row, wiping ``content_hash`` — so the next good run
        could no longer recognise unchanged content and would rewrite every row, forfeiting the
        idempotence this store exists to prove. Codex's fix, adopted here, is stronger than my
        replacement: rather than teaching the row to hold both states, a successful row is simply
        left alone and the failing attempt is reported by the run marker, which already names the
        stream, the season and the reason. A ``failed`` row is written **only** when there is no
        prior success — so the season is never silently absent, and a row is never a lie.
        """
        try:
            with self._connect() as conn:
                key = f"{stream}:{season}"
                prior = conn.execute(
                    "SELECT status FROM nflverse_capture WHERE stream_season = ?", (key,)
                ).fetchone()
                if prior is not None and prior["status"] == "ok":
                    # Last-good evidence stands. The marker carries this failure.
                    return
                conn.execute(
                    f"INSERT OR REPLACE INTO nflverse_capture ({', '.join(_CAPTURE_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in _CAPTURE_COLUMNS)})",
                    [key, stream, str(season), "failed", None, "{}", reason, None, ingested_at],
                )
        except Exception:  # never mask the originating failure
            pass

    def row_count(self, table: str) -> int:
        with self._connect() as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def captures(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM nflverse_capture ORDER BY stream, season DESC"
            ).fetchall()
        out = []
        for row in rows:
            record = dict(row)
            record["coverage"] = json.loads(record.pop("coverage_json") or "{}")
            out.append(record)
        return out

    def content_fingerprint(self) -> str:
        """Hash of every stored DATA row. Identical content, identical bytes.

        Deliberately excludes ``nflverse_capture``: that table is operational history — a
        failure and a later recovery genuinely happened and must move it. Folding it in would
        mean the data-idempotence proof could be broken by a run that changed no data at all.
        """
        chunks: list[str] = []
        with self._connect() as conn:
            for table in sorted(s.table for s in self.specs.values()):
                for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1"):
                    chunks.append(json.dumps(tuple(row), default=str))
        return hashlib.sha256("\n".join(chunks).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Capture orchestration (callable; never self-scheduling)
# ---------------------------------------------------------------------------


def status_marker_path(raw_root: Path = DEFAULT_RAW_ROOT) -> Path:
    return Path(raw_root) / "nflverse_usage_status_latest.json"


def write_raw_snapshot(
    records: Sequence[Mapping[str, Any]],
    *,
    stream: str,
    season: int,
    captured_at: str,
    raw_root: Path = DEFAULT_RAW_ROOT,
) -> Path:
    """Write the raw payload BEFORE parsing (`01` §Source Adapter Rules)."""
    raw_dir = Path(raw_root) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = "".join(ch for ch in captured_at if ch.isalnum())
    path = raw_dir / f"{stream}_{season}_{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "stream": stream,
                "season": season,
                "captured_at": captured_at,
                "rows": len(records),
                "records": list(records),
            },
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _to_records(frame: Any) -> list[dict[str, Any]]:
    """polars or pandas -> list of dicts, without importing either at module scope."""
    if hasattr(frame, "to_dicts"):
        return frame.to_dicts()
    if hasattr(frame, "to_dict"):
        return frame.to_dict(orient="records")
    raise UsageCaptureError(f"unsupported frame type from loader: {type(frame)!r}")


@contextmanager
def _exclusive_capture_lock(db_path: Path):
    """One writer per STORE. E4 (Codex, reproduced): `run_usage_capture` had no
    lock at all, so two captures could interleave their per-season commits and one
    could export rows partly written by the other under its own run_id.

    R2-E4 (Codex, reproduced): the first fix keyed the lock to `raw_root`, but
    `db_path` and `raw_root` are INDEPENDENT arguments — two calls against the same
    SQLite store with different raw roots took two different locks and could still
    interleave that one store, contradicting the "one writer per store" claim this
    docstring makes. The lock is therefore keyed to the canonical DB path, which is
    the thing actually being protected.

    The lock spans the whole transaction: start marker, every DB write, the export,
    and the terminal marker. A second capture REFUSES by name and touches neither
    the first run's store nor its ready marker.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = db_path.with_name(f".{db_path.name}.capture.lock")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise UsageCaptureError(
            f"nflverse_capture_lock_held: {lock_path} exists; another capture may be "
            "running. A concurrent capture is refused rather than allowed to "
            "interleave stream-season commits."
        ) from exc
    try:
        os.write(descriptor, b"nflverse_usage_capture\n")
        os.close(descriptor)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def export_ready_marker_path(export_root: Path = DEFAULT_EXPORT_ROOT) -> Path:
    """The consumer's entry point. Reading this FIRST is the whole contract."""
    return Path(export_root) / "nflverse_usage.ready.json"


def publish_export(
    store: "UsageStore",
    specs: Sequence[StreamSpec],
    *,
    run_id: str,
    captured_at: str,
    export_root: Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    """Publish the DERIVED last-good export: Parquet projections + identity artifact.

    **Why this exists (Codex, TW31 — reproduced before accepting).** The SQLite store
    commits ONE stream-season at a time, each in its own transaction. Every commit is
    valid, but a consumer pointed at the store mid-capture observes a MIXED-VINTAGE
    read. That is not hypothetical: after the ten-season backfill the live store held
    two ``ingested_at`` stamps at once — 12 stream-seasons from one run and 28 from
    the next. A feature build reading between them would have mixed 2016-2022 fresh
    rows with 2023-2025 stale ones and reported neither.

    So consumers never read the store directly. They read the READY MARKER, which
    names one ``run_id``, and that marker is written LAST — after every Parquet file
    for the run has landed. The marker is the commit point:

      - Success -> a new immutable run directory, then the marker flips atomically.
      - Failure -> this function is never called, so the PRIOR run and PRIOR marker
        stand untouched and the consumer keeps reading the last good vintage. The run
        marker separately says ``failed``. Silence is never success.

    Parquet because columnar is the right shape to hand the analysis layer; SQLite is
    not. It is a projection, never a second adapter and never a second source of truth.
    """
    import polars as pl

    export_root = Path(export_root)
    run_dir = export_root / "runs" / run_id
    if run_dir.exists():
        raise UsageCaptureError(
            f"nflverse_export_run_exists: {run_dir} — refusing to overwrite an "
            "immutable export run"
        )
    run_dir.mkdir(parents=True)

    files: dict[str, dict[str, Any]] = {}
    unresolved_frames: list[Any] = []

    with store._connect() as conn:
        for spec in specs:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {spec.table}")]
            # Construct with an EXPLICIT all-Utf8 schema rather than letting polars
            # infer from a 100-row window. SQLite holds every column as TEXT, so
            # Utf8 is what the data actually is — and inference here was a live
            # failure, not a hypothetical: the injury stream's first rows carry a
            # null `report_primary_injury`, polars inferred Null, and the first
            # real value ("Ankle") raised ComputeError mid-export. The declared
            # casts below then apply the real types. "Declared, never inferred"
            # has to hold at CONSTRUCTION too, not only at cast time.
            # Both branches construct from the DECLARED columns. The empty branch
            # used to be a bare pl.DataFrame(), so a consumer's schema depended on
            # whether the table happened to be empty that run — a zero-column
            # Parquet where the contract promises typed columns (Codex B6).
            frame = pl.DataFrame(
                rows,
                schema={
                    column: pl.Utf8
                    for column in (rows[0] if rows else spec.stored_columns)
                },
            )
            # E1 (Codex, reproduced): SQLite stores every column TEXT, so an
            # untyped projection ships `week` and `season` as Utf8 and the exact
            # existing feature filter `(week == 0) & (season_type == "REG")` fails
            # against it outright. Types are DECLARED per stream, never inferred —
            # inference would silently retype a column the day its data happened to
            # look numeric.
            if frame.height:
                # R2-E1 (Codex, reproduced): `strict=False` alone turns malformed
                # non-null source text into NULL, so a typed Parquet can look
                # perfectly valid while having silently eaten bad values —
                # corruption made indistinguishable from missingness, which is the
                # exact disease this product keeps getting burned by. Every cast is
                # therefore RECONCILED: non-null count before vs after, and any
                # column that lost a value fails the publish BY NAME.
                lost: list[str] = []
                for name, dtype in spec.export_dtypes.items():
                    if name not in frame.columns:
                        continue
                    before = frame.height - frame[name].null_count()
                    if dtype == pl.Boolean:
                        # FAIL CLOSED (Codex edf05e9-1). The Int64 intermediate accepts ANY
                        # integer and polars maps nonzero -> true, so `is_motion='2'` published
                        # as True and the non-null reconciliation could not see it: it only
                        # counts nulls. The commit message claimed such a value "becomes null
                        # and is caught by the reconciliation" — that was simply false. Check
                        # the domain explicitly instead of trusting the cast.
                        as_int = frame[name].cast(pl.Int64, strict=False)
                        out_of_domain = (
                            frame.select(
                                bad=(
                                    as_int.is_not_null() & ~as_int.is_in([0, 1])
                                ).sum()
                            )["bad"][0]
                        )
                        if out_of_domain:
                            observed = sorted(
                                {
                                    v
                                    for v in frame[name].to_list()
                                    if str(v) not in ("0", "1", "None", "True", "False")
                                }
                            )[:5]
                            raise UsageCaptureError(
                                f"nflverse_export_boolean_out_of_domain: {spec.name}.{name} "
                                f"carries {out_of_domain} value(s) that are neither 0 nor 1 "
                                f"(e.g. {observed}). Casting them would silently publish True. "
                                "Refusing rather than inventing a boolean."
                            )
                        # SQLite has no Boolean type and holds these as TEXT '0'/'1'
                        # (measured), and polars refuses Utf8 -> Boolean outright. Go through
                        # Int64. Anything that is neither '0' nor '1' becomes null under
                        # strict=False and is then caught by the reconciliation below — which
                        # is the fail-closed behaviour we want, not a silent coercion.
                        casted = (
                            pl.col(name).cast(pl.Int64, strict=False).cast(pl.Boolean, strict=False)
                        )
                    else:
                        casted = pl.col(name).cast(dtype, strict=False)
                    frame = frame.with_columns(casted.alias(name))
                    after = frame.height - frame[name].null_count()
                    if after < before:
                        lost.append(f"{name} ({before - after} value(s))")
                if lost:
                    raise UsageCaptureError(
                        f"nflverse_export_cast_lost_values: {spec.name} lost non-null "
                        f"values casting {lost} — the source carries text that is not "
                        "the declared numeric type. Refusing to publish a typed export "
                        "in which corruption is indistinguishable from missingness."
                    )
            path = run_dir / f"{spec.name}.parquet"
            frame.write_parquet(path)
            files[spec.name] = {
                "path": str(path),
                "rows": len(rows),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            # The identity artifact covers EVERY non-canonical row across EVERY
            # stream — not one stream's empty file presented as identity being
            # complete. The 45,363 source-only snap rows and the 3 held conflicts
            # are the substance of it.
            for row in rows:
                # NOT_APPLICABLE is deliberately excluded: this artifact exists so a human can
                # chase players we failed to resolve. A play-grain stream has no player to
                # chase, and 143,572 FTN plays would otherwise drown the real 53,994 (Codex C7).
                if row.get("identity_status") not in (CANONICAL_RESOLVED, NOT_APPLICABLE):
                    unresolved_frames.append(
                        {
                            "stream": spec.name,
                            "source_id": str(row.get(spec.identity_column) or ""),
                            "identity_kind": spec.identity_kind,
                            "identity_status": row.get("identity_status"),
                            "season": row.get("season_ingested"),
                            "player": (
                                row.get("player")
                                or row.get("player_display_name")
                                # Injuries carry `full_name`. Without this the
                                # review artifact for every source_only row — 1,140
                                # in the 2024 cohort alone — loses the human name,
                                # which is the one field that makes it reviewable.
                                or row.get("full_name")
                            ),
                            "position": row.get("position") or row.get("player_position"),
                        }
                    )

    unresolved_path = run_dir / "unresolved_identity.parquet"
    (pl.DataFrame(unresolved_frames) if unresolved_frames else pl.DataFrame()).write_parquet(
        unresolved_path
    )
    files["unresolved_identity"] = {
        "path": str(unresolved_path),
        "rows": len(unresolved_frames),
        "sha256": hashlib.sha256(unresolved_path.read_bytes()).hexdigest(),
    }

    by_status: dict[str, int] = {}
    for row in unresolved_frames:
        status = str(row["identity_status"])
        by_status[status] = by_status.get(status, 0) + 1

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "captured_at": captured_at,
        "db_path": str(store.db_path),
        "files": files,
        "rows_total": sum(f["rows"] for name, f in files.items() if name != "unresolved_identity"),
        "unresolved_rows": len(unresolved_frames),
        "unresolved_by_status": by_status,
        "seasons": sorted({str(c["season"]) for c in store.captures()}),
    }
    _atomic_write_json(run_dir / "manifest.json", manifest)

    # THE COMMIT POINT — written last, atomically. Until this lands, the previous
    # run remains the last good vintage for every consumer.
    _atomic_write_json(export_ready_marker_path(export_root), manifest)
    return manifest


def read_last_good_export(
    export_root: Path = DEFAULT_EXPORT_ROOT, *, verify: bool = True
) -> dict[str, Any] | None:
    """The consumer entry point: the last COMPLETE, VERIFIED export, or None.

    Returns None when nothing has ever been published — a consumer with no artifact
    must carry on without one, which is what makes optional-if-present real.

    **But absence and CORRUPTION are different, and only one of them is normal.**
    E3 (Codex, reproduced): the first version returned any syntactically valid
    marker, so a marker naming a nonexistent Parquet with ``sha256=deadbeef`` was
    accepted as last-good. The ready marker protects PUBLISH ORDERING; it says
    nothing about what happened to the bytes afterwards — a truncated copy, a
    half-restored backup, a partial sync. Every referenced file is therefore
    checked for existence, containment in its own immutable run directory, and
    sha256 before a consumer is told the export is good, and a mismatch fails
    LOUDLY by name rather than degrading to None.
    """
    marker = export_ready_marker_path(export_root)
    if not marker.exists():
        return None
    manifest = json.loads(marker.read_text(encoding="utf-8"))
    if not verify:
        return manifest

    run_id = str(manifest.get("run_id") or "")
    run_dir = (Path(export_root) / "runs" / run_id).resolve()
    for name, entry in (manifest.get("files") or {}).items():
        path = Path(str(entry.get("path", ""))).resolve()
        if run_id and run_dir not in path.parents:
            raise UsageCaptureError(
                f"nflverse_export_escapes_run: {name} at {path} is outside the "
                f"immutable run directory {run_dir}"
            )
        if not path.exists():
            raise UsageCaptureError(
                f"nflverse_export_file_missing: {name} at {path} is named by the "
                "ready marker but is not on disk"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry.get("sha256"):
            raise UsageCaptureError(
                f"nflverse_export_hash_mismatch: {name} at {path} hashes {digest[:16]} "
                f"but the ready marker recorded {str(entry.get('sha256'))[:16]}"
            )
        # R2-E3 (Codex, reproduced): hash + existence is NOT last-good. A marker
        # recording rows=999 against a one-row Parquet whose sha256 matched was
        # accepted as good — the hash proves the file is the one that was written,
        # not that it holds what the manifest claims. A consumer sizing its join on
        # `rows` would silently under-read.
        import polars as pl

        actual_rows = pl.scan_parquet(path).select(pl.len()).collect().item()
        if int(actual_rows) != int(entry.get("rows", -1)):
            raise UsageCaptureError(
                f"nflverse_export_row_count_mismatch: {name} at {path} holds "
                f"{actual_rows} rows but the ready marker recorded {entry.get('rows')}"
            )
    return manifest


#: The NGS streams a feature build consumes, mapped to the loader-output keys the
#: existing assembly already expects. Same keys, same column names — the consumer
#: is not rewritten to suit the store.
NEXTGEN_LOADER_KEYS: dict[str, str] = {
    "ngs_passing": "nextgen_passing",
    "ngs_receiving": "nextgen_receiving",
    "ngs_rushing": "nextgen_rushing",
}


def load_nextgen_from_export(
    seasons: Sequence[int] | None = None,
    *,
    export_root: Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    """Read NGS for a feature build from the LAST-GOOD export instead of the network.

    This is the store's first consumer, and the reason the export exists. Before it,
    the 09:15 scheduled chain made three direct ``load_nextgen_stats`` calls — three
    network round-trips inside the critical path, three new ways the morning halts,
    and no cached-failure behaviour despite the source registry declaring
    ``failure_behavior="use_cached"``.

    Returns loader-output frames keyed exactly as the existing assembly expects, so
    the consumer needs no rewrite. Returns ``{}`` when no export has ever been
    published — absence is normal and must never raise, which is what makes the
    downstream optional-if-present features genuinely optional. Corruption is a
    different thing and still raises loudly (§read_last_good_export).
    """
    manifest = read_last_good_export(export_root)
    if manifest is None:
        return {}

    import polars as pl

    wanted = {int(s) for s in seasons} if seasons else None
    frames: dict[str, Any] = {}
    for stream, loader_key in NEXTGEN_LOADER_KEYS.items():
        entry = (manifest.get("files") or {}).get(stream)
        if entry is None:
            continue
        frame = pl.read_parquet(entry["path"])
        if wanted is not None and frame.height and "season" in frame.columns:
            frame = frame.filter(pl.col("season").is_in(sorted(wanted)))
        frames[loader_key] = frame.to_pandas()
    return frames


def nextgen_export_provenance(
    export_root: Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    """What the feature build should RECORD about the NGS it consumed.

    Absence is legitimate but must never be silent: a build that ran without NGS
    says so, with the reason, rather than quietly producing a candidate whose NGS
    columns are missing for no stated cause.

    ``captured_at`` is FETCH/RETRIEVAL time. Upstream publish time is UNAVAILABLE —
    no artifact distinguishes them — so nothing here implies an observed vendor
    cadence (Gemini/Codex provenance boundary, 2026-07-31).
    """
    manifest = read_last_good_export(export_root)
    if manifest is None:
        return {"source": "nflverse_usage_export", "available": False,
                "reason": "no export has been published"}
    return {
        "source": "nflverse_usage_export",
        "available": True,
        "run_id": manifest.get("run_id"),
        "captured_at_is": "fetch_time",
        "captured_at": manifest.get("captured_at"),
        "upstream_publish_time": "UNAVAILABLE",
        "seasons": manifest.get("seasons"),
        "schema_version": manifest.get("schema_version"),
        "file_sha256": {
            name: entry.get("sha256")
            for name, entry in (manifest.get("files") or {}).items()
        },
    }


def run_usage_capture(
    *,
    seasons: Sequence[int],
    specs: Sequence[StreamSpec] | None = None,
    identity: IdentityIndex | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    export_root: Path | None = None,
    fetch: Callable[[StreamSpec, int], Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Start marker -> per stream-season fetch -> raw snapshot -> normalize -> store -> marker.

    A start record is written before any fetch, so a run that dies mid-flight leaves
    ``status=running`` rather than the previous run's ``status=ok``. A stream-season that raises
    writes ``status=failed`` naming the stream, the season and the stage, then re-raises.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"nflverse-usage-{''.join(ch for ch in started_at if ch.isalnum())}"
    marker = status_marker_path(raw_root)
    specs = tuple(specs if specs is not None else build_streams())
    seasons = [int(s) for s in seasons]

    base = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "seasons": seasons,
        "streams": [spec.name for spec in specs],
    }
    def _default_fetch(spec: StreamSpec, season: int) -> Sequence[Mapping[str, Any]]:
        return _to_records(spec.loader(seasons=[season], **dict(spec.loader_kwargs)))

    fetch = fetch or _default_fetch
    export_dir = Path(export_root) if export_root is not None else Path(raw_root) / "export"
    results: list[dict[str, Any]] = []

    # The lock spans the WHOLE transaction — start marker, every DB write, the
    # export, and the terminal marker — so a second capture cannot interleave its
    # per-season commits with this one's (E4).
    with _exclusive_capture_lock(Path(db_path)):
        _atomic_write_json(marker, {**base, "status": "running"})
        return _run_locked_capture(
            base=base, marker=marker, specs=specs, seasons=seasons, fetch=fetch,
            identity=identity, db_path=db_path, raw_root=raw_root,
            export_dir=export_dir, run_id=run_id, started_at=started_at,
            results=results,
        )


def _run_locked_capture(
    *, base, marker, specs, seasons, fetch, identity, db_path, raw_root,
    export_dir, run_id, started_at, results,
) -> dict[str, Any]:
    """The capture body, run while the exclusive lock is held."""
    store: UsageStore | None = None
    stream_name = season = None

    try:
        if identity is None:
            identity = IdentityIndex.from_governed_crosswalk()
        store = UsageStore(db_path, specs)

        for spec in specs:
            for season in seasons:
                stream_name = spec.name
                if spec.min_season is not None and season < spec.min_season:
                    # Recorded, not silently omitted: a reader of the results must be able to
                    # tell "this source does not go back that far" from "we forgot to fetch it".
                    results.append(
                        {
                            "stream": spec.name,
                            "season": season,
                            "skipped": "before_min_season",
                            "min_season": spec.min_season,
                        }
                    )
                    continue
                records = fetch(spec, season)
                raw_path = write_raw_snapshot(
                    records,
                    stream=spec.name,
                    season=season,
                    captured_at=started_at,
                    raw_root=raw_root,
                )
                rows, coverage = normalize_rows(
                    records, spec=spec, season=season, identity=identity
                )
                applied = store.apply_season(
                    spec,
                    season=season,
                    rows=rows,
                    coverage=coverage,
                    ingested_at=started_at,
                )
                results.append(
                    {
                        "stream": spec.name,
                        "season": season,
                        "applied": applied,
                        "raw_snapshot": str(raw_path),
                        # The reduced per-stream gate requires "raw snapshot + manifest/hash".
                        # Recording only the path meant the export hashes proved the PARSED
                        # projection but never the PRE-PARSE bytes, so a replay could not show
                        # that what we parsed is what we fetched.
                        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                        "coverage": coverage,
                    }
                )

        # DERIVED EXPORT — inside the transaction on purpose. E2 (Codex,
        # reproduced): publishing after the except block meant an export failure
        # left the run marker reading `running` forever, with no reason and no
        # failed stage. The prior ready marker survived, but OPERATIONAL TRUTH did
        # not, and silence is never success. The export is part of the capture, so
        # its failure fails the run by name.
        stream_name, season = None, None
        export_manifest = publish_export(
            store, specs, run_id=run_id, captured_at=started_at,
            export_root=export_dir,
        )
    except Exception as exc:
        if store is not None and stream_name is not None and season is not None:
            store.record_failure(
                stream_name, season, f"{type(exc).__name__}: {exc}", started_at
            )
        _atomic_write_json(
            marker,
            {
                **base,
                "status": "failed",
                "failed_stage": "export" if stream_name is None and results else "capture",
                "failed_stream": stream_name,
                "failed_season": season,
                "reason": f"{type(exc).__name__}: {exc}",
                "captured_before_failure": [
                    {"stream": r["stream"], "season": r["season"]} for r in results
                ],
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise

    status = {
        **base,
        "status": "ok",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "export": {
            "run_id": export_manifest["run_id"],
            "rows_total": export_manifest["rows_total"],
            "unresolved_rows": export_manifest["unresolved_rows"],
            "unresolved_by_status": export_manifest["unresolved_by_status"],
            "ready_marker": str(export_ready_marker_path(export_dir)),
        },
        "results": results,
        "totals": _totals(results),
        "rows_stored": {
            spec.table: store.row_count(spec.table) for spec in specs
        },
        "identity_bridge": {
            "gsis_universe": len(identity.gsis_ids),
            "pfr_bridge_pairs": len(identity.pfr_to_gsis),
            "pfr_conflicts_held": len(identity.pfr_conflicts),
            "pfr_conflict_ids": sorted(identity.pfr_conflicts),
        },
    }
    _atomic_write_json(marker, status)
    return status


def _totals(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Totals that cannot hide a stream-season. Same rule as the transaction chain.

    Skipped stream-seasons (a season before the source's `min_season`) carry no coverage block
    and are counted separately. They are NOT folded into `stream_seasons`, because that count
    means "stream-seasons actually ingested" and quietly inflating it with skips would hide the
    very thing the skip record exists to disclose.
    """
    skipped = [r for r in results if r.get("skipped")]
    blocks = [dict(r["coverage"]) for r in results if "coverage" in r]
    keys = (
        "rows_total",
        "rows_canonical_resolved",
        "rows_source_only",
        "rows_conflict",
        "rows_unknown",
        "rows_not_canonically_identified",
    )
    return {
        **{k: sum(int(b.get(k) or 0) for b in blocks) for k in keys},
        "stream_seasons": len(blocks),
        "stream_seasons_skipped": sorted(
            f"{r['stream']}:{r['season']}" for r in skipped
        ),
        "stream_seasons_with_unresolved": sorted(
            f"{b['stream']}:{b['season']}"
            for b in blocks
            if int(b.get("rows_not_canonically_identified") or 0) > 0
        ),
        "by_stream_season": {f"{b['stream']}:{b['season']}": b for b in blocks},
    }


def load_governed_identity() -> IdentityIndex:
    return IdentityIndex.from_governed_crosswalk()
