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
import numbers
import os
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
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

    #: Grain columns this era permits to be NULL. Everything else in the grain must be
    #: populated. A spec-level all-or-nothing switch was too blunt: `require_populated_grain
    #: =False` for the weekly era's SBBYE null week ALSO disabled every check on the daily
    #: era, so a daily row with a null `pos_rank` was accepted (Codex 7654a19-1).
    nullable_grain_columns: tuple[str, ...] = ()

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

    #: Grain columns permitted to be NULL for a spec with no eras. Same contract as
    #: `StreamEra.nullable_grain_columns`, and the era's value wins when one matches.
    nullable_grain_columns: tuple[str, ...] = ()

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

    #: Which axis this stream is captured along. FAIL-CLOSED ENUM, not a bool (Codex D3):
    #:
    #: ``seasonal`` — the existing behaviour and the DEFAULT, so no current stream changes:
    #: one loader call per requested season, rows partitioned by ``season_ingested``.
    #:
    #: ``snapshot`` — exactly ONE no-arguments loader call per RUN. The source has no season
    #: axis at all (``load_contracts()`` accepts no ``seasons``), and passing one raises. Rows
    #: are partitioned by ``snapshot_id`` + ``observed_at`` and carry NO ``season_ingested``;
    #: inventing a synthetic season is the defect this enum exists to prevent.
    capture_axis: str = "seasonal"

    #: Columns holding a nested structure that must be stored as canonical JSON. SQLite cannot
    #: hold ``List(Struct)``. The encoder VALIDATES before serializing and never coerces.
    json_columns: tuple[str, ...] = ()

    #: Refuse a record whose top-level key set differs from the declared source columns.
    #:
    #: Opt-in and set ONLY on contracts. The non-era normalization path checks for MISSING
    #: columns and then projects the declared ones, so an ADDED upstream field is silently
    #: dropped and every digest is unchanged. Declaring a synthetic era would widen the cleared
    #: projection with `source_era`; extending exact equality globally would change the twelve
    #: frozen streams' accepted-input behaviour. This is one binary rule, so a bool is the right
    #: shape — unlike `capture_axis`, which carries distinct partition semantics.
    refuse_unexpected_columns: bool = False

    #: Exact field names each JSON column's entries must carry. Pinned, so a provider adding or
    #: dropping a nested field REFUSES rather than being silently serialized.
    nested_fields: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

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

        if self.capture_axis not in ("seasonal", "snapshot"):
            raise UsageCaptureError(
                f"stream {self.name}: unknown capture_axis {self.capture_axis!r}; "
                "expected 'seasonal' or 'snapshot'"
            )

        if self.capture_axis == "snapshot":
            # Each of these is a SEASONAL setting that is meaningless — and therefore
            # dangerous — on a source with no season axis. Refused individually so a failure
            # names the offending field rather than confounding several.
            if self.min_season is not None:
                raise UsageCaptureError(
                    f"stream {self.name}: min_season has no meaning on a snapshot stream — "
                    "there is no season axis for a floor to apply to"
                )
            if "seasons" in dict(self.loader_kwargs):
                raise UsageCaptureError(
                    f"stream {self.name}: loader_kwargs carries 'seasons' on a snapshot "
                    "stream; a snapshot loader is called with no arguments at all"
                )
            if self.require_populated_grain or self.nullable_grain_columns:
                raise UsageCaptureError(
                    f"stream {self.name}: seasonal grain/nullability settings are not valid "
                    "on a snapshot stream, whose rows are keyed by snapshot_id and content"
                )
            if self.grain:
                raise UsageCaptureError(
                    f"stream {self.name}: a snapshot stream declares no grain — its key is "
                    f"snapshot_id + content_sha256; got {self.grain!r}"
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
        base = (*columns, "dg_player_id", "identity_status", "row_key")
        if self.capture_axis == "snapshot":
            base = (*base, "content_sha256", "snapshot_id", "observed_at")
        else:
            # SEASONAL FREEZE (Codex v9). An earlier draft appended `content_sha256` here too,
            # which changed the stored schema AND the pinned projection fingerprint of every
            # already-landed stream — caught by the golden-digest contract test, which is
            # exactly what that pin exists for. Seasonal projection is byte-for-byte unchanged.
            base = (*base, "season_ingested")
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
    # Grain IS enforced; only `player_id` may be null (the residual rows). `game_id` and
    # `posteam` are never null in any measured season and must never be accepted null — a
    # blanket require_populated_grain=False permitted all three (Codex 7de9357-1).
    require_populated_grain=True,
    nullable_grain_columns=("player_id",),
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
            nullable_grain_columns=("player_id",),
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
#   * 2018-2024 WEEKLY era — 15 columns, ~37k rows/season, keyed on the game week.
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
#   a real category, not corruption. Grain enforcement is ON; `week` is declared
#   nullable ON THE WEEKLY ERA ONLY (with `depth_position`, the '\n    ' artifact), and
#   the daily era permits no null coordinate. `game_type` keeps SBBYE distinguishable.
#
# EXACT DUPLICATES: 790 of 186,074 weekly rows (2020-2024 sample) are exact full-row repeats,
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
    # `week` (SBBYE rows) and `depth_position`. The latter is NOT null upstream — it is
    # the whitespace scrape artifact '\n    ', 3,964 rows across 2018-2024, the same
    # artifact class the injury stream already normalizes. Measured: with blanks
    # normalized the weekly grain stays UNIQUE in every season. A nulls-only measurement
    # missed all of them, which is how the first nullable declaration was wrong.
    # The daily era permits nothing null.
    nullable_grain_columns=("week", "depth_position"),
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
    # week is Int32 upstream (weekly); pos_slot/pos_rank are Int32 (daily). Declaring only
    # `season` published all three as TEXT in the LIVE export — the fixtures happened to
    # carry ints, so a fixture-only assertion could not see it (Codex 7654a19-2).
    integer_columns=("season", "week", "pos_slot", "pos_rank"),
    collapse_exact_duplicates=True,
    # '\n    ' and None are two spellings of the same nothing; store one.
    blank_as_null_columns=("depth_position",),
    # Grain IS enforced; nullability is declared PER ERA.
    require_populated_grain=True,
    eras=(DEPTH_WEEKLY_ERA, DEPTH_DAILY_ERA),
)


# ---------------------------------------------------------------------------
# Contracts (board block C, stream 5 of 6) — SNAPSHOT AXIS, ACCUMULATED
# ---------------------------------------------------------------------------
#
# Measured live 2026-08-05 (`nflreadpy 0.1.5`): 51,808 rows / 25 columns and NO season
# axis — `load_contracts()` accepts no arguments. The source MOVES: two probes in one
# session measured 51,803 then 51,808 rows, which is why David ruled ACCUMULATE FROM
# CAPTURE ONE at WEEKLY cadence rather than overwrite. Retention is indefinite; the
# cadence authorizes no scheduler and this lands manual-only.
#
# NO BUSINESS KEY EXISTS. Every candidate leaves duplicates: otc_id+year_signed 9,616
# groups, +team 6,668, +position 6,350. Rather than a nine-column "everything that
# happens to differ" key — which is a set of MUTABLE MEASURES, not an identity — rows
# are keyed by snapshot_id + a content digest over the declared source columns.
#
# 2,503 duplicate groups / 3,316 EXCESS copies / 5,819 participating / max 9;
# 48,492 + 3,316 = 51,808. Post-collapse identity census: 32,198 canonical_resolved +
# 12,196 source_only + 4,098 unknown = 48,492, and the first-snapshot unresolved
# artifact is 16,294 — EVERY non-canonical row, not just the unknowns.
#
# `year_signed == 0` on 1,106 rows: preserved literally, no meaning inferred.
# `is_active` is Boolean upstream and must be declared, or it publishes as text.
# `cols` is List(Struct) of 13 cap fields; SQLite cannot hold it, so it is canonical
# JSON with the order preserved exactly — never sorted, and `year` is not always
# numeric (every one of 45,875 lists ends in a non-numeric 'Total').

_CONTRACTS_COLUMNS = (
    'player', 'position', 'team', 'is_active', 'year_signed', 'years', 'value',
    'apy', 'guaranteed', 'apy_cap_pct', 'inflated_value', 'inflated_apy',
    'inflated_guaranteed', 'player_page', 'otc_id', 'gsis_id', 'date_of_birth',
    'height', 'weight', 'college', 'draft_year', 'draft_round', 'draft_overall',
    'draft_team', 'cols',
)

CONTRACTS = StreamSpec(
    name="contracts",
    table="contracts",
    identity_column="gsis_id",
    identity_kind="gsis",
    capture_axis="snapshot",
    grain=(),  # keyed by snapshot_id + content_sha256, not by a business grain
    columns=_CONTRACTS_COLUMNS,
    loader=None,  # bound in build_streams
    loader_kwargs={},
    integer_columns=('year_signed', 'years', 'otc_id', 'draft_year', 'draft_round', 'draft_overall'),
    float_columns=('value', 'apy', 'guaranteed', 'apy_cap_pct', 'inflated_value', 'inflated_apy', 'inflated_guaranteed'),
    boolean_columns=('is_active',),
    json_columns=("cols",),
    refuse_unexpected_columns=True,
    nested_fields={
        "cols": (
            "year", "team", "base_salary", "prorated_bonus", "roster_bonus",
            "guaranteed_salary", "cap_number", "cap_percent", "cash_paid", "workout_bonus",
            "other_bonus", "per_game_roster_bonus", "option_bonus",
        )
    },
    collapse_exact_duplicates=True,
    refuse_non_finite=True,
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
            nullable_grain_columns=spec.nullable_grain_columns,
            capture_axis=spec.capture_axis,
            json_columns=spec.json_columns,
            refuse_unexpected_columns=spec.refuse_unexpected_columns,
            nested_fields=spec.nested_fields,
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
        _bind(CONTRACTS, nflreadpy.load_contracts),
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
        empty = _coverage(spec, season, [], missing_columns=[])
        # An absent counter cannot be distinguished from "nothing happened", and an empty
        # capture is exactly when a reader most needs the zero stated.
        if spec.collapse_exact_duplicates:
            empty["rows_collapsed_exact_duplicates"] = 0
        if spec.exclude_unidentified_rows:
            empty["rows_excluded_unidentified"] = 0
        return [], empty

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
    nullable_grain = spec.nullable_grain_columns
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
        nullable_grain = match.nullable_grain_columns

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
    spec = replace(
        spec, columns=columns, grain=grain, nullable_grain_columns=nullable_grain
    )

    if spec.refuse_unexpected_columns:
        # V12-1: this MUST precede the generic `missing` check below, which reads only
        # `records[0].keys()`. Ordered the other way, a field absent from row zero was
        # intercepted as `nflverse_schema_drift` — no record index, neither set named — while
        # the identical break on a later row got the precise vocabulary. A gate whose refusal
        # depends on WHICH row you break is a gate you pass by picking the row.
        #
        # It also precedes projection, collapse, digest, persistence AND the identity
        # exclusion filter, for the reason schema validation was moved ahead of that filter
        # in the first place (Codex da00235-1): drift confined to a row we were about to drop
        # is still drift, and a dropped field must never reach a digest that then claims the
        # row is unchanged. Every record, not just the first.
        declared = set(spec.columns)
        for index, record in enumerate(records):
            observed = set(record.keys())
            if observed != declared:
                raise UsageCaptureError(
                    f"nflverse_unexpected_columns: stream {spec.name} record {index} has "
                    f"unexpected {sorted(observed - declared)} and missing "
                    f"{sorted(declared - observed)}; the declared source shape is exact"
                )

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

    # (The exact-column check ran HERE until V12-1 moved it ahead of the generic `missing`
    # check and the identity exclusion filter. Not duplicated: one check, one place.)

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
        # Nested columns become canonical JSON BEFORE the digest, so the digest covers the
        # serialized form a consumer actually reads. Validation refuses; it never coerces.
        for col in spec.json_columns:
            row[col] = encode_nested_json(
                row.get(col), expected_fields=spec.nested_fields.get(col)
            )

        row["dg_player_id"] = dg_player_id
        row["identity_status"] = status
        # Identifies the OBSERVATION. Same content in two snapshots -> same digest, which is
        # what makes accumulated vintages comparable.
        if spec.capture_axis == "snapshot":
            # G2: an earlier draft stamped this on EVERY row. It is unpersisted for seasonal
            # streams, but `_rows_hash` hashes the whole row dict, so the season digest
            # changed (measured 96b09692 vs legacy da36dcc5) and an UNCHANGED capture would
            # have rewritten its partitions. I fixed `stored_columns`, verified only that, and
            # reported the whole freeze as verified. Seasonal rows never see this field.
            row["content_sha256"] = row_content_digest(spec, row)
        if spec.require_populated_grain:
            # Read the NORMALIZED row, not the raw record. Reading `record` meant
            # 2020.0/1.0 and 2020/1 normalized to identical stored coordinates yet
            # produced DIFFERENT row keys, so one observation was stored twice and
            # the duplicate gate was satisfied by the divergence it should have
            # caught (Codex B2).
            blank_grain = [
                col
                for col in spec.grain
                if col not in spec.nullable_grain_columns
                and (
                    row.get(col) is None
                    or (isinstance(row.get(col), str) and not str(row[col]).strip())
                )
            ]
            if blank_grain:
                raise UsageCaptureError(
                    f"nflverse_blank_grain: stream {spec.name} season {season} has a row "
                    f"with absent grain coordinate(s) {blank_grain} — the grain is what "
                    "makes two observations distinguishable; keying on a blank silently "
                    "collapses them"
                )
        if spec.capture_axis == "snapshot":
            # No grain, no season. `row_key` is composed in `apply_snapshot`, which is where
            # the snapshot_id lives; inventing a synthetic season here is the defect the
            # capture_axis enum exists to prevent.
            row.pop("season_ingested", None)
        else:
            row["row_key"] = _row_key(spec, row)
            row["season_ingested"] = str(season)
        rows.append(row)

    if spec.capture_axis == "snapshot":
        # Uniqueness is enforced on (snapshot_id, content_sha256) at apply time. Two rows
        # sharing a content digest after collapse would mean the collapse failed.
        digests = [r["content_sha256"] for r in rows]
        if len(digests) != len(set(digests)):
            duplicates = sorted({d for d in digests if digests.count(d) > 1})[:5]
            raise UsageCaptureError(
                f"nflverse_duplicate_content_digest: stream {spec.name} produced repeated "
                f"content digests after collapse; examples {duplicates}"
            )
        coverage = _coverage(spec, season, rows, missing_columns=[])
        if spec.collapse_exact_duplicates:
            coverage["rows_collapsed_exact_duplicates"] = collapsed_exact
        return rows, coverage

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
#: A SEPARATE, SUCCESS-ONLY ledger for snapshot-axis streams (Codex v9 ruling).
#:
#: The shared `nflverse_capture` table is keyed by `stream_season`, and `captures()`,
#: `read_only_summary` and the export's season inventory all consume that as a SEASON. Putting
#: a snapshot_id there would make the column a lie for every reader. A snapshot observation is
#: a different kind of fact, so it gets its own table rather than three nullable columns and an
#: overloaded key.
#:
#: SUCCESS-ONLY BY DESIGN: there is no `status` or `failure_reason`. A row here means a durable
#: observation exists. Failures are reported by the run marker, which already names the stream,
#: the stage and the reason.
_SNAPSHOT_CAPTURE_COLUMNS = (
    "stream",
    "snapshot_id",
    "capture_axis",
    "observed_at",
    "rows_total",
    "coverage_json",
    "content_hash",
    "raw_snapshot",
    "raw_sha256",
    "ingested_at",
)


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


#: Fields written BY the pipeline rather than read from the source. Excluded from the row
#: content digest, which must identify the OBSERVATION, not the capture that carried it.
_DERIVED_FIELDS = frozenset({
    "snapshot_id", "observed_at", "capture_axis", "dg_player_id", "identity_status",
    "row_key", "content_sha256", "season_ingested", "source_era",
})

JSON_SCALARS = (str, int, float, bool, type(None))


def encode_nested_json(
    value: Any, expected_fields: Sequence[str] | None = None
) -> str | None:
    """Canonical JSON for a nested column. VALIDATES, never coerces.

    polars hands a ``Series`` for a ``List`` column, so an explicit order-preserving conversion
    is required before encoding. The banned ``default=`` fallback would turn an unexpected type
    into a plausible-looking string; the shape is checked instead and anything else refuses by
    name. ``None`` stays ``None`` so a null nested column reaches SQLite as SQL NULL rather than
    the string "null".
    """
    if value is None:
        return None

    items = value.to_list() if hasattr(value, "to_list") else value
    if not isinstance(items, (list, tuple)):
        raise UsageCaptureError(
            f"nflverse_nested_not_a_list: nested column is {type(value).__name__}, "
            "expected a list of mappings"
        )

    plain: list[dict[str, Any]] = []
    for index, entry in enumerate(items):
        if not isinstance(entry, Mapping):
            raise UsageCaptureError(
                f"nflverse_nested_entry_not_a_mapping: entry {index} is "
                f"{type(entry).__name__}, expected a mapping"
            )
        if expected_fields is not None and set(entry) != set(expected_fields):
            raise UsageCaptureError(
                f"nflverse_nested_shape: entry {index} has fields {sorted(entry)}, "
                f"expected exactly {sorted(expected_fields)}"
            )
        for key, inner in entry.items():
            if not isinstance(inner, JSON_SCALARS):
                raise UsageCaptureError(
                    f"nflverse_nested_value_not_json: entry {index} field {key!r} is "
                    f"{type(inner).__name__}, which is not a JSON scalar"
                )
        plain.append(dict(entry))

    # Order is NEVER changed: measured across 45,875 live lists, numeric years ascend and every
    # list ends in a non-numeric 'Total'. Sorting would destroy that and `year` is not numeric.
    return json.dumps(plain, sort_keys=True, separators=(",", ":"), allow_nan=False)


def row_content_digest(spec: StreamSpec, row: Mapping[str, Any]) -> str:
    """SHA-256 over the declared SOURCE columns of one row.

    An ALLOW-LIST of `spec.columns`, not a deny-list of metadata: a deny-list silently admits
    any column added later. Identifies the observation, so two identical contracts in different
    snapshots share a digest — which is what lets accumulation be compared across vintages.
    """
    payload = {column: row.get(column) for column in spec.columns}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def snapshot_idempotence_digest(
    spec: StreamSpec,
    *,
    rows: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    observed_at: str,
    raw_sha256: str,
) -> str:
    """Identifies one OBSERVATION ATTEMPT — deliberately a different thing from a row digest.

    Includes COVERAGE, so a changed exact-duplicate count cannot hide behind an identical
    collapsed row-set, and the raw provenance hash, so a retry against different source bytes
    is not mistaken for the same observation.
    """
    parts = {
        "stream": spec.name,
        "observed_at": observed_at,
        "raw_sha256": raw_sha256,
        "rows": sorted(str(r.get("content_sha256")) for r in rows),
        "coverage": _coverage_fingerprint(coverage),
        # The PERSISTED PROJECTION, which `apply_season` has always included. Omitting it here
        # meant a projection change with identical rows and coverage would return "unchanged"
        # and leave the stored projection stale (Codex v9).
        "projection": _projection_fingerprint(spec),
    }
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
            # Created ONLY when a snapshot stream is present, so a purely seasonal store is
            # byte-for-byte what it was before this axis existed (Codex v9).
            if any(spec.capture_axis == "snapshot" for spec in specs):
                # NOT NULL on every field a row needs to describe itself, and a CHECK
                # pinning the axis. G4: an all-TEXT nullable DDL accepted a seasonal-axis row
                # with null context and empty provenance — a ledger row that cannot say what
                # it recorded is worse than no row.
                _required = (
                    "stream", "snapshot_id", "capture_axis", "observed_at",
                    "content_hash", "raw_snapshot", "raw_sha256", "ingested_at",
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS nflverse_snapshot_capture ("
                    + ", ".join(
                        f"{c} TEXT" + (" NOT NULL" if c in _required else "")
                        for c in _SNAPSHOT_CAPTURE_COLUMNS
                    )
                    + ", CHECK (capture_axis = 'snapshot')"
                    + ", PRIMARY KEY (stream, snapshot_id))"
                )
                self._assert_schema(
                    conn, "nflverse_snapshot_capture", _SNAPSHOT_CAPTURE_COLUMNS
                )
                # V12-4: the CREATE above is `IF NOT EXISTS`, a no-op against a table that
                # already exists, and `_assert_schema` compares column NAMES only. So the
                # exact partial state an earlier draft leaves behind — all-TEXT, nullable, no
                # CHECK — opened successfully and the G4 constraints were absent on every
                # store already created. Names are not a schema; verify the constraints.
                self._assert_snapshot_ledger_constrained(conn, _required)
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

    @staticmethod
    def _assert_snapshot_ledger_constrained(
        conn: sqlite3.Connection, required: Sequence[str]
    ) -> None:
        """V12-4. Verify the G4 constraints are actually ON the existing table.

        Refuses rather than migrating. Adding NOT NULL / CHECK to a populated SQLite table
        means a table rebuild, and a rebuild is a decision about existing rows — including
        what to do with any row that already violates the constraint being added. That is a
        deliberate, reviewed migration, not something a constructor does on the way past.
        """
        nullable = [
            row[1]
            for row in conn.execute("PRAGMA table_info(nflverse_snapshot_capture)")
            if row[1] in set(required) and not row[3]
        ]
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            "AND name='nflverse_snapshot_capture'"
        ).fetchone()
        ddl_text = (ddl[0] if ddl else "") or ""
        # Normalised so whitespace/quoting variants of the same CHECK still count.
        compact = "".join(ddl_text.split()).lower().replace('"', "").replace("'", "")
        has_axis_check = "check(capture_axis=snapshot)" in compact
        if nullable or not has_axis_check:
            raise UsageCaptureError(
                "nflverse_snapshot_ledger_unconstrained: nflverse_snapshot_capture exists "
                f"but is missing its G4 guarantees — nullable required columns {nullable}; "
                f"capture_axis CHECK present: {has_axis_check}. The column NAMES match, "
                "which is why this was accepted before. A ledger row that can record a null "
                "provenance or a non-snapshot axis cannot say what it recorded. Refusing "
                "rather than rebuilding the table underneath existing rows: adding these "
                "constraints is an explicit, reviewed migration"
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

    def apply_snapshot(
        self,
        spec: StreamSpec,
        *,
        rows: Sequence[Mapping[str, Any]],
        coverage: Mapping[str, Any],
        ingested_at: str,
        snapshot_id: str,
        observed_at: str,
        raw_sha256: str,
        raw_snapshot: str,
    ) -> str:
        """Persist ONE observation of a snapshot-axis stream.

        Accumulation, not replacement: a different `snapshot_id` is a DIFFERENT observation and
        is added alongside the others, even when its content is byte-identical to last week's.
        That is the property David's ruling turns on and the one a content-keyed store most
        easily breaks.

        Reusing a `snapshot_id` means retrying the SAME logical observation. It is idempotent
        only when observed_at, the row/coverage/projection digest AND the raw provenance all
        match — then nothing is rewritten. Any difference REFUSES and leaves the first success
        exactly as it was, because two different observations must never share one identity.
        """
        if spec.capture_axis != "snapshot":
            raise UsageCaptureError(
                f"nflverse_wrong_axis: apply_snapshot called for {spec.name}, which is "
                f"capture_axis={spec.capture_axis!r}"
            )
        missing = [
            name
            for name, value in (
                ("snapshot_id", snapshot_id), ("observed_at", observed_at),
                ("raw_sha256", raw_sha256), ("raw_snapshot", raw_snapshot),
            )
            if not str(value or "").strip()
        ]
        if missing:
            raise UsageCaptureError(
                f"nflverse_snapshot_provenance_missing: stream {spec.name} cannot record an "
                f"observation without {missing}"
            )

        digest = snapshot_idempotence_digest(
            spec, rows=rows, coverage=coverage,
            observed_at=observed_at, raw_sha256=raw_sha256,
        )

        # A content digest must identify exactly one payload. Two unequal payloads arriving on
        # one digest is a collision and must fail loudly rather than overwrite.
        seen: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            key = str(row.get("content_sha256"))
            prior = seen.get(key)
            if prior is not None:
                if {c: prior.get(c) for c in spec.columns} != {
                    c: row.get(c) for c in spec.columns
                }:
                    raise UsageCaptureError(
                        f"nflverse_content_digest_collision: stream {spec.name} snapshot "
                        f"{snapshot_id} has two UNEQUAL payloads on digest {key}"
                    )
            seen[key] = row

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM nflverse_snapshot_capture WHERE stream = ? AND snapshot_id = ?",
                (spec.name, snapshot_id),
            ).fetchone()

            if existing is not None:
                mismatch = [
                    field
                    for field, value in (
                        ("observed_at", observed_at),
                        ("content_hash", digest),
                        ("raw_sha256", raw_sha256),
                        ("raw_snapshot", raw_snapshot),
                    )
                    if existing[field] != value
                ]
                if mismatch:
                    raise UsageCaptureError(
                        f"nflverse_snapshot_id_reused: stream {spec.name} snapshot "
                        f"{snapshot_id} already exists and differs in {mismatch}. A snapshot id "
                        "identifies ONE observation; refusing rather than overwriting the "
                        "first success."
                    )
                return "unchanged"

            for row in rows:
                stored = dict(row)
                stored["snapshot_id"] = snapshot_id
                stored["observed_at"] = observed_at
                stored["row_key"] = f"{snapshot_id}|{row['content_sha256']}"
                conn.execute(
                    f"INSERT INTO {spec.table} "
                    f"({', '.join(spec.stored_columns)}) "
                    f"VALUES ({', '.join('?' for _ in spec.stored_columns)})",
                    [stored.get(c) for c in spec.stored_columns],
                )
            conn.execute(
                "INSERT INTO nflverse_snapshot_capture "
                f"({', '.join(_SNAPSHOT_CAPTURE_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _SNAPSHOT_CAPTURE_COLUMNS)})",
                [
                    spec.name,
                    snapshot_id,
                    "snapshot",
                    observed_at,
                    len(rows),
                    json.dumps(coverage, sort_keys=True, default=str),
                    digest,
                    raw_snapshot,
                    raw_sha256,
                    ingested_at,
                ],
            )
            return "inserted"

    def snapshot_captures(self) -> list[dict[str, Any]]:
        """Snapshot-axis capture records, `coverage_json` decoded to `coverage`.

        Deliberately separate from `captures()`, which stays exactly as it was for the seasonal
        streams that already depend on it.
        """
        with self._connect() as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='nflverse_snapshot_capture'"
                )
            }
            if not names:
                return []
            records = []
            for row in conn.execute(
                "SELECT * FROM nflverse_snapshot_capture ORDER BY stream, observed_at"
            ):
                record = dict(row)
                record["coverage"] = json.loads(record["coverage_json"])
                records.append(record)
            return records

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
    season: int | None,
    captured_at: str,
    raw_root: Path = DEFAULT_RAW_ROOT,
    partition: Mapping[str, Any] | None = None,
) -> Path:
    """Write the raw payload BEFORE parsing (`01` §Source Adapter Rules).

    G3: an earlier draft passed `season=observed_at` for snapshot streams, writing an ISO
    timestamp under a key literally named `season` into the durable pre-parse artifact — a
    synthetic season in the one file that is supposed to be the untouched source truth. A
    snapshot stream now passes `season=None` and its own `partition` instead, and NO `season`
    key is written at all.

    V12-3: G3 fixed the CALLER and left the function itself fail-open — it validated nothing, so
    four malformed envelope shapes were accepted and written. This is the pre-parse artifact
    every replay and audit starts from; a raw file that cannot say what it recorded is worse
    than no file. Exactly two envelopes are legal and they are mutually exclusive:

      seasonal  — `season` is an int and `partition` is None
      snapshot  — `season` is None and `partition` carries exactly capture_axis='snapshot',
                  a `snapshot_id` and an `observed_at`, and NO `season` key

    The seasonal branch is byte-identical to what twelve frozen streams already write.
    """
    if partition is None:
        if season is None:
            raise UsageCaptureError(
                f"nflverse_raw_envelope: stream {stream} passed neither a season nor a "
                "snapshot partition. The raw artifact would carry no axis at all, so nothing "
                "downstream could tell which kind of capture produced it"
            )
        # `numbers.Integral`, NOT `isinstance(season, int)`. The guard exists to catch the G3
        # defect — an ISO timestamp written under a key named `season` — not to police an
        # integer's provenance. A caller reading seasons off a dataframe hands over a
        # `numpy.int64`, which is a perfectly good season and which a bare `int` check would
        # refuse. No current caller does (argparse `type=int`), so this is a false refusal
        # waiting to be hit rather than a live break. `bool` is excluded explicitly: it IS an
        # Integral, and `season=True` would otherwise write `"season": true`.
        if isinstance(season, bool) or not isinstance(season, numbers.Integral):
            raise UsageCaptureError(
                f"nflverse_raw_envelope: stream {stream} seasonal season is "
                f"{season!r} ({type(season).__name__}), expected an integer — this is the "
                "key that once carried an ISO timestamp (G3)"
            )
        # Normalize to a built-in int. Accepting the type is not enough: the writer below
        # serializes with `default=str`, so a `numpy.int64` would land in the artifact as the
        # STRING "2024" while a python int lands as the NUMBER 2024 — the same capture
        # producing two different envelope shapes depending on how the caller built its list.
        # `int()` on an Integral is exact and total. Caught by this fix's own control test,
        # which is the entire point of writing the controls first.
        season = int(season)
    else:
        if season is not None:
            raise UsageCaptureError(
                f"nflverse_raw_envelope: stream {stream} passed BOTH season {season!r} and a "
                "snapshot partition. The two axes are mutually exclusive; accepting both "
                "makes the artifact's axis depend on which key a reader happens to look at"
            )
        if partition.get("capture_axis") != "snapshot":
            raise UsageCaptureError(
                f"nflverse_raw_envelope: stream {stream} partition declares capture_axis "
                f"{partition.get('capture_axis')!r}, expected 'snapshot'. A partition is the "
                "snapshot-axis envelope and has no meaning on any other axis"
            )
        absent = [
            key for key in ("snapshot_id", "observed_at")
            if not str(partition.get(key) or "").strip()
        ]
        if absent:
            raise UsageCaptureError(
                f"nflverse_raw_envelope: stream {stream} snapshot partition is missing "
                f"{absent}. A snapshot that cannot name itself or say when it was observed "
                "cannot be reconciled against a later vintage"
            )
        if "season" in partition:
            raise UsageCaptureError(
                f"nflverse_raw_envelope: stream {stream} snapshot partition carries a "
                f"`season` key ({partition['season']!r}). The source has no season axis; "
                "inventing one in the pre-parse artifact is the G3 defect wearing a partition"
            )
        # Codex F1. Validating that the required keys are PRESENT is not the same as validating
        # that they are the ONLY keys. `metadata.update(partition)` below merges the partition
        # over the authoritative envelope fields, so an extra key silently rides along and a
        # COLLIDING key overwrites the truth: Codex's probe wrote stream='spoofed_stream',
        # rows=999, captured_at='spoofed_time' and schema_version='spoofed_schema' onto a file
        # holding ONE real contracts row. An artifact that misreports its own stream and row
        # count is not a record of anything. The key set is EXACT.
        allowed = {"capture_axis", "snapshot_id", "observed_at"}
        authoritative = {"schema_version", "stream", "captured_at", "rows"}
        extra = sorted(set(partition) - allowed)
        if extra:
            collisions = sorted(set(extra) & authoritative)
            detail = ""
            if collisions:
                detail = (
                    f" {collisions} would OVERWRITE the authoritative envelope field(s) of "
                    "the same name, making the artifact misreport itself"
                )
            raise UsageCaptureError(
                f"nflverse_raw_envelope: stream {stream} snapshot partition carries "
                f"unexpected keys {extra}; exactly {sorted(allowed)} are permitted.{detail}"
            )

    raw_dir = Path(raw_root) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = "".join(ch for ch in captured_at if ch.isalnum())
    label = season if season is not None else (partition or {}).get("snapshot_id", "snapshot")
    safe = "".join(ch if ch.isalnum() else "-" for ch in str(label))
    path = raw_dir / f"{stream}_{safe}_{stamp}.json"
    metadata: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stream": stream,
        "captured_at": captured_at,
        "rows": len(records),
    }
    if partition is not None:
        metadata.update(partition)
    else:
        metadata["season"] = season
    path.write_text(
        json.dumps(
            {
                **metadata,
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
    if isinstance(frame, (list, tuple)):
        # Already records. A loader is free to return them, and a test spy always does.
        return [dict(r) for r in frame]
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


#: The unresolved-identity artifact's EXACT ordered column contract.
#:
#: The first seven preserve the shape consumers already read (measured from the
#: 2026-08-05 last-good artifact); the last three are APPENDED. Inserting into the
#: prefix would be a positional break for anything reading by index.
#:
#: Every column is String because production reads them from SQLite TEXT. Typing
#: `season` as an integer here would be a consumer-visible schema change smuggled in
#: behind a bug fix.
UNRESOLVED_IDENTITY_SCHEMA: tuple[str, ...] = (
    "stream",
    "source_id",
    "identity_kind",
    "identity_status",
    "season",
    "player",
    "position",
    "capture_axis",
    "snapshot_id",
    "observed_at",
)


def build_unresolved_identity_frame(rows: Sequence[Mapping[str, Any]]) -> Any:
    """Build the unresolved-identity frame under an EXPLICIT schema.

    WHY THIS EXISTS (live failure, run nflverse-usage-20260808T0228465894550000): the
    previous code called ``pl.DataFrame(rows)``, which infers column types from a
    BOUNDED leading window. Seasonal unresolved rows carry ``snapshot_id=None`` and
    snapshot-axis rows (contracts) carry a string. With every row in the window null,
    Polars built a Null column and the first real string afterwards could not be
    appended:

        ComputeError: could not append value "...:contracts" of type str to the builder

    The column types are known by contract, so inferring them was never necessary. An
    explicit schema also keeps the artifact's shape STABLE across runs — without it a
    run containing only seasonal rows would hand consumers a different frame than one
    containing contracts.
    """
    import polars as pl

    columns: dict[str, list[Any]] = {name: [] for name in UNRESOLVED_IDENTITY_SCHEMA}
    for row in rows:
        for name in UNRESOLVED_IDENTITY_SCHEMA:
            value = row.get(name)
            columns[name].append(None if value is None else str(value))
    return pl.DataFrame(
        columns, schema={name: pl.String for name in UNRESOLVED_IDENTITY_SCHEMA}
    )


def publish_export(
    store: "UsageStore",
    specs: Sequence[StreamSpec],
    *,
    run_id: str,
    captured_at: str,
    export_root: Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    """Publish the export, removing a PARTIAL run directory if it fails.

    WHY (live failure, 2026-08-08): the export died after writing thirteen source
    Parquets, leaving `runs/<run_id>/` populated with no manifest and no ready-marker
    promotion. Anything listing the runs directory reads that as a completed export.
    The store, the source bytes and the FAILED status marker are the honest evidence of
    the attempt; a directory that looks finished is not.

    The previous ready marker is untouched either way — it is only advanced on success,
    which is what preserved the consumer commit point when this failed live.
    """
    run_dir = Path(export_root) / "runs" / run_id
    # Only ever remove a directory THIS call created. A pre-existing run is refused by
    # the immutability check below, and deleting it would destroy a real prior export.
    preexisting = run_dir.exists()
    try:
        return _publish_export_unguarded(
            store, specs, run_id=run_id, captured_at=captured_at, export_root=export_root
        )
    except BaseException as original:
        if not preexisting and run_dir.exists():
            try:
                shutil.rmtree(run_dir)
            except OSError as cleanup_error:
                # `ignore_errors=True` silently left behind the very orphan this guard
                # exists to prevent — a directory of Parquets with no manifest, which
                # reads as a completed export. If cleanup cannot be done, say so loudly
                # rather than return a quiet lie about the export root's state.
                raise UsageCaptureError(
                    f"nflverse_export_cleanup_failed: {run_dir} could not be removed "
                    f"after a failed export ({cleanup_error}); a partial run directory "
                    "remains and must not be read as a completed export"
                ) from original
        raise


def _publish_export_unguarded(
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
            if not frame.height:
                # A zero-row export must still carry the declared types, or a consumer's
                # schema depends on whether the table happened to be empty that run.
                frame = frame.with_columns(
                    [
                        pl.col(name).cast(dtype, strict=False).alias(name)
                        for name, dtype in spec.export_dtypes.items()
                        if name in frame.columns
                    ]
                )
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
                        # EXACT DOMAIN on the RAW value, not on a coerced integer.
                        # Checking the Int64 coercion let '01' and '+1' through — both parse
                        # to 1 and published as True — and sent non-numeric values like 'yes'
                        # to the generic cast-lost-values error rather than a Boolean one
                        # (Codex 7de9357-2). SQLite holds these as TEXT '0'/'1' (measured).
                        # MEASURED, not assumed: a genuine Python bool reaches this
                        # store as TEXT '0'/'1' (probe: 235 zeros / 96 ones on the real
                        # fixture). It NEVER arrives as 'True'/'False'. An earlier version
                        # allowed those two strings "for Python bool round-trip" — a premise
                        # that is simply false, and it let a SOURCE string "True" through to
                        # publish as Boolean true (Codex 36c813c-1). Stored spellings only.
                        allowed = {"0", "1"}
                        observed = [
                            v for v in frame[name].to_list()
                            if v is not None and str(v) not in allowed
                        ]
                        if observed:
                            raise UsageCaptureError(
                                f"nflverse_export_boolean_out_of_domain: {spec.name}.{name} "
                                f"carries {len(observed)} value(s) outside "
                                f"{sorted(allowed)} (e.g. {sorted(set(map(str, observed)))[:5]}). "
                                "Casting them would silently publish a boolean we were never "
                                "given. Refusing rather than inventing one."
                            )
                        casted = (
                            pl.col(name)
                            .replace_strict({"0": False, "1": True}, default=None)
                            .cast(pl.Boolean, strict=False)
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
                            # D2: a seasonal row keeps `season`; a snapshot row carries its
                            # own partition instead. Without it, 52 weekly snapshots of the
                            # same unresolved player are indistinguishable rows.
                            "capture_axis": spec.capture_axis,
                            "snapshot_id": row.get("snapshot_id"),
                            "observed_at": row.get("observed_at"),
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
    build_unresolved_identity_frame(unresolved_frames).write_parquet(unresolved_path)
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


def capture_snapshot_stream(
    spec: StreamSpec,
    *,
    identity: IdentityIndex | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    fetch: Callable[..., Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Capture ONE snapshot-axis stream. Refuses a seasonal spec.

    The two axes have genuinely different semantics — one partition per season versus one per
    observation — so routing a spec through the wrong one would produce a plausible-looking
    store with the wrong key. The guard is here, at the entry point, rather than inferred.
    """
    if spec.capture_axis != "snapshot":
        raise UsageCaptureError(
            f"nflverse_wrong_axis: {spec.name} is capture_axis={spec.capture_axis!r} and "
            "cannot be routed through the snapshot path"
        )
    return run_usage_capture(
        seasons=[], specs=(spec,), identity=identity,
        db_path=db_path, raw_root=raw_root, fetch=fetch,
    )


def capture_seasonal_stream(
    spec: StreamSpec,
    *,
    season: int,
    identity: IdentityIndex | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    fetch: Callable[..., Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Capture ONE seasonal-axis stream for one season. Refuses a snapshot spec."""
    if spec.capture_axis != "seasonal":
        raise UsageCaptureError(
            f"nflverse_wrong_axis: {spec.name} is capture_axis={spec.capture_axis!r} and "
            "cannot be routed through the seasonal path"
        )
    return run_usage_capture(
        seasons=[season], specs=(spec,), identity=identity,
        db_path=db_path, raw_root=raw_root, fetch=fetch,
    )


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
        if spec.capture_axis == "snapshot":
            # NO arguments at all — `load_contracts()` accepts none, and passing `seasons`
            # is the C5 defect this axis exists to prevent.
            return _to_records(spec.loader())
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
            if spec.capture_axis == "snapshot":
                # EXACTLY ONE no-arguments call per RUN, regardless of how many seasons the
                # run requests. The source has no season axis; passing one raises.
                stream_name, season = spec.name, None
                records = fetch(spec, None)
                # Stamped AFTER the fetch returns, never at run start (Codex D4-2).
                observed_at = datetime.now(timezone.utc).isoformat()
                snapshot_id = f"{run_id}:{spec.name}"
                raw_path = write_raw_snapshot(
                    records,
                    stream=spec.name,
                    season=None,
                    captured_at=started_at,
                    raw_root=raw_root,
                    partition={
                        "capture_axis": "snapshot",
                        "snapshot_id": snapshot_id,
                        "observed_at": observed_at,
                    },
                )
                raw_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
                rows, coverage = normalize_rows(
                    records, spec=spec, season=None, identity=identity
                )
                applied = store.apply_snapshot(
                    spec,
                    rows=rows,
                    coverage=coverage,
                    ingested_at=started_at,
                    snapshot_id=snapshot_id,
                    observed_at=observed_at,
                    raw_sha256=raw_sha256,
                    raw_snapshot=str(raw_path),
                )
                results.append(
                    {
                        "stream": spec.name,
                        "capture_axis": "snapshot",
                        "snapshot_id": snapshot_id,
                        "observed_at": observed_at,
                        "season": None,
                        "applied": applied,
                        "raw_snapshot": str(raw_path),
                        "raw_sha256": raw_sha256,
                        "coverage": coverage,
                    }
                )
                continue

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
        failed_axis = next(
            (spec.capture_axis for spec in specs if spec.name == stream_name), None
        )
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
                "capture_axis": failed_axis,
                "reason": f"{type(exc).__name__}: {exc}",
                # Per-axis partition context. A bare {stream, season} entry cannot describe a
                # snapshot observation at all — `season` is None for it, so a reader could not
                # tell WHICH weekly capture had already landed before the run died.
                "captured_before_failure": [
                    (
                        {
                            "stream": r["stream"],
                            "capture_axis": "snapshot",
                            "snapshot_id": r.get("snapshot_id"),
                            "observed_at": r.get("observed_at"),
                            "season": None,
                        }
                        if r.get("capture_axis") == "snapshot"
                        else {
                            "stream": r["stream"],
                            "capture_axis": "seasonal",
                            "season": r.get("season"),
                        }
                    )
                    for r in results
                    if not r.get("skipped")
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


#: V12-5: the ONE census vocabulary, shared by all three views `_totals` reports — the
#: seasonal roll-up, the `snapshot_*` aggregates, and the per-stream `by_stream_snapshot`
#: entries. They were three hand-written tuples and the third quietly lacked
#: `rows_not_canonically_identified`. Driving them off one constant makes that drift
#: impossible rather than merely fixed once.
_SNAPSHOT_CENSUS_KEYS = (
    "rows_total",
    "rows_canonical_resolved",
    "rows_source_only",
    "rows_conflict",
    "rows_unknown",
    "rows_not_canonically_identified",
)


def _totals(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Totals that cannot hide a stream-season. Same rule as the transaction chain.

    Skipped stream-seasons (a season before the source's `min_season`) carry no coverage block
    and are counted separately. They are NOT folded into `stream_seasons`, because that count
    means "stream-seasons actually ingested" and quietly inflating it with skips would hide the
    very thing the skip record exists to disclose.
    """
    skipped = [r for r in results if r.get("skipped")]
    snapshots = [r for r in results if r.get("capture_axis") == "snapshot"]
    blocks = [
        dict(r["coverage"])
        for r in results
        if "coverage" in r and r.get("capture_axis") != "snapshot"
    ]
    snapshot_blocks = [dict(r["coverage"]) for r in snapshots]
    return {
        **{
            k: sum(int(b.get(k) or 0) for b in blocks) for k in _SNAPSHOT_CENSUS_KEYS
        },
        "stream_seasons": len(blocks),
        # A snapshot is counted ONCE under its OWN vocabulary. `stream_seasons` means
        # stream-seasons actually ingested and folding a snapshot into it would be the
        # synthetic-season defect wearing a different coat (Codex D3).
        "stream_snapshots": len(snapshots),
        # V12-5: `rows_not_canonically_identified` was carried at top level and in the
        # `snapshot_*` aggregates but omitted HERE — while the GREEN report claimed "the same
        # census in by_stream_snapshot". A census complete in two views and silently short in
        # the third is how an unresolved population goes invisible to whoever reads the
        # per-stream view. Driven off one key tuple so the three views cannot drift again.
        "by_stream_snapshot": {
            entry["stream"]: {
                "snapshot_id": entry["snapshot_id"],
                "observed_at": entry["observed_at"],
                **{key: entry["coverage"][key] for key in _SNAPSHOT_CENSUS_KEYS},
            }
            for entry in snapshots
        },
        # G5: excluding snapshot blocks from the seasonal counters without adding the
        # snapshot equivalents made the unresolved population INVISIBLE at run level — a
        # controlled 49 source_only + 1 unknown reported as zeros. Snapshot-prefixed, so the
        # seasonal counters stay untouched.
        **{
            f"snapshot_{key}": sum(int(b.get(key) or 0) for b in snapshot_blocks)
            for key in _SNAPSHOT_CENSUS_KEYS
        },
        "snapshot_unresolved_by_stream": {
            entry["stream"]: {
                "snapshot_id": entry["snapshot_id"],
                "rows_source_only": entry["coverage"]["rows_source_only"],
                "rows_conflict": entry["coverage"]["rows_conflict"],
                "rows_unknown": entry["coverage"]["rows_unknown"],
                "rows_not_canonically_identified": entry["coverage"][
                    "rows_not_canonically_identified"
                ],
            }
            for entry in snapshots
        },
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
