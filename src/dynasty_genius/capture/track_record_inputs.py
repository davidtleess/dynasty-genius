"""Build one track-record enrollment: what was registered, what could not be, and why.

This module freezes the inputs a later evaluation will be graded on. It performs no network call and
no write. Its whole job is to be unable to fill in a blank.

Three rules do the heavy lifting, and each exists because of a specific way this could go wrong:

**A missing value stays missing.** Absence from the prior-season table is `null` with a stated reason.
Only a verified non-participation — a row that exists and says the player did not play — may be zero.
A roster status is not evidence of a zero season.

**A baseline is only contemporaneous if that can be proven.** `source_as_of` is what a source says
about itself and never proves it was available at a historical cutoff. Without a proven
`source_available_at`, the stream is `reconstructed`, even when the underlying facts predate the save.

**Targets are compared field by field, never by identity.** A target identity hashes whole admitted
season windows, so a 2026 source differs from a 2025 one even when it measures exactly the same thing.
So the measurement fields and the window are compared, `labels_through` is checked against the cutoff
and the target season rather than required equal, and the raw source bytes are bound by hash
separately.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo

SCHEMA_VERSION = "track_record.enrollment.v1"

#: Compared field by field between the baseline source and the archived forecast. `labels_through` is
#: deliberately absent: it is a knowledge vintage, checked against the cutoff, not a measurement.
MEASUREMENT_FIELDS = ("scope", "scoring", "window", "exposure", "event", "clock", "quantity")

#: The frozen prior-season position convention: raw historical statistical position, never current
#: fantasy eligibility. Raw FB and CB participants are EXCLUDED from a median rather than remapped —
#: remapping them would silently change the denominator the baseline is measured against.
MEDIAN_POSITIONS = ("QB", "RB", "WR", "TE")

_SHA256_HEX = re.compile(r"\A[0-9a-f]{64}\Z")

#: The declaration is REG weeks 1 to 17. A schedule that does not cover them is not evidence about
#: them, whatever else it contains.
DECLARED_WEEKS = tuple(range(1, 18))

#: The declaration is the 2026 season. A schedule for another season is not evidence about it.
TARGET_SEASON = 2026

SIX_SOURCE_FIELDS = (
    "report_run", "report_sha256", "market_sha256", "league_sha256",
    "catalog_run", "catalog_content_sha256",
)

STATES = {
    "not_registered", "awaiting_horizon", "awaiting_capture", "input_unavailable",
    "cutoff_ineligible", "insufficient_evidence", "graded",
}
PROVENANCE_CLASSES = {"contemporaneous", "reconstructed", "unavailable"}

#: How fresh the archived market reading must be to serve as a prospective start price.
MARKET_START_MAX_AGE = timedelta(hours=24)


class TrackRecordInputError(ValueError):
    """An input cannot be registered as given; the message names the field that failed."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise TrackRecordInputError(message)


def _stamp(value: datetime | str, what: str) -> str:
    if isinstance(value, datetime):
        _require(value.tzinfo is not None, f"{what} must carry a timezone")
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _require(isinstance(value, str) and value, f"{what} is empty")
    return str(value)


def _parse(value: Any, what: str) -> datetime:
    _require(isinstance(value, str) and value, f"{what} is empty")
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as bad:
        raise TrackRecordInputError(f"{what} is not a timestamp: {value!r}") from bad
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _strict_number(value: Any, what: str) -> float | None:
    """A number, or None for an explicit null. A boolean or a non-finite value is a REFUSAL.

    Coercing `True` or `NaN` to "missing" would hide a corrupt source behind a reason string that
    reads like an honest absence.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise TrackRecordInputError(f"{what} is the boolean {value!r}, not a number")
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise TrackRecordInputError(f"{what} is {value!r}, which is not a finite number")
        return float(value)
    raise TrackRecordInputError(f"{what} is {type(value).__name__}, not a number")


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _interval(rank: Any) -> list[int] | None:
    """A rank stays an interval. A tie is a range and both of its ends are real."""
    if not isinstance(rank, Mapping):
        return None
    start, end = rank.get("start"), rank.get("end")
    if not (isinstance(start, int) and isinstance(end, int)) or isinstance(start, bool):
        return None
    return [int(start), int(end)]


# ── source envelopes ────────────────────────────────────────────────────────────────────────────

def _validate_source_artifacts(artifacts: list, role: str) -> dict[str, bytes]:
    """Read each named artifact once, verify its hash AND its length, and keep those exact buffers.

    Hashing a file and then reopening it is how a validated buffer and a stored buffer drift apart, so
    the bytes checked here are the bytes returned.
    """
    seen: dict[str, bytes] = {}
    for entry in artifacts:
        _require(isinstance(entry, Mapping), f"{role}: a source_artifacts entry is not an object")
        name = entry.get("name")
        _require(isinstance(name, str) and name and "/" not in name and name not in {".", ".."},
                 f"{role}: the source artifact name {name!r} is not a plain file name")
        _require(name not in seen, f"{role}: two source artifacts are both named {name!r}")
        payload = entry.get("raw_bytes")
        _require(isinstance(payload, (bytes, bytearray)),
                 f"{role}: the source artifact {name} was not read into a buffer")
        payload = bytes(payload)
        _require(entry.get("sha256") == _sha256(payload),
                 f"{role}: the source artifact {name} hashes to {_sha256(payload)}, "
                 f"not the {entry.get('sha256')} its receipt declares")
        declared_length = entry.get("bytes")
        _require(declared_length is None or int(declared_length) == len(payload),
                 f"{role}: the source artifact {name} is {len(payload)} bytes, "
                 f"not the {declared_length} its receipt declares")
        seen[name] = payload
    return seen


def _source_raw_bytes(envelope: Mapping[str, Any], what: str) -> bytes:
    """The file's own bytes. Re-serialising a parsed object would store a different file."""
    payload = envelope.get("raw_bytes")
    _require(isinstance(payload, (bytes, bytearray)),
             f"the {what} envelope carries no raw_bytes, so the enrollment could not preserve the "
             "exact file it was validated against")
    return bytes(payload)


def _source_evidence(envelope: Mapping[str, Any], role: str, hashes: Mapping[str, str]) -> dict:
    """The five knowledge fields every source carries, kept apart on purpose.

    `captured_at` is when we read the bytes, `source_as_of` is what the source says about itself,
    `source_available_at` is when it can be PROVEN to have been obtainable, and it is nullable
    because that proof usually does not exist.
    """
    available = envelope.get("source_available_at")
    _require(available is None or isinstance(available, str),
             f"{role}: source_available_at must be a timestamp or null")
    captured = _parse(envelope.get("captured_at"), f"{role}: captured_at")
    if available is not None and _parse(available, f"{role}: source_available_at") > captured:
        raise TrackRecordInputError(
            f"{role}: source_available_at {available} is in the future relative to the moment it was "
            f"captured; availability cannot postdate possession"
        )
    return {
        "role": role,
        "kind": envelope.get("kind"),
        "captured_at": _stamp(envelope.get("captured_at"), f"{role}: captured_at"),
        "source_as_of": _stamp(envelope.get("source_as_of"), f"{role}: source_as_of"),
        "source_available_at": available,
        "source_revision": envelope.get("source_revision"),
        "hashes": dict(hashes),
    }


def _validate_baseline(baseline: Mapping[str, Any], forecast_target: Mapping[str, Any],
                       target_season: int | None = None) -> dict:
    """Read the prior-season bytes once, hash those buffers, and validate from the same buffers."""
    _require(isinstance(baseline, Mapping), "the baseline source must be a mapping")
    csv_bytes = baseline.get("csv_bytes")
    manifest_bytes = baseline.get("manifest_bytes")
    _require(isinstance(csv_bytes, (bytes, bytearray)), "the baseline source carries no csv_bytes")
    _require(isinstance(manifest_bytes, (bytes, bytearray)),
             "the baseline source carries no manifest_bytes")

    try:
        manifest = json.loads(bytes(manifest_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as bad:
        raise TrackRecordInputError(
            f"the baseline manifest is not readable JSON, so its coverage and target claims cannot "
            f"be checked: {bad}"
        ) from bad
    _require(isinstance(manifest, Mapping), "the baseline manifest is not a JSON object")

    # The manifest is the source's own account of itself. Checking only that the receipt is
    # self-consistent would let an envelope claim any coverage, season or scoring it liked.
    outputs = manifest.get("outputs") or {}
    declared_csv = outputs.get("outcomes.csv")
    _require(isinstance(declared_csv, Mapping),
             "the baseline manifest declares no outputs['outcomes.csv']")
    _require(declared_csv.get("sha256") == _sha256(bytes(csv_bytes)),
             "the manifest's outcomes.csv sha256 does not match the CSV bytes supplied")
    _require(declared_csv.get("bytes") == len(bytes(csv_bytes)),
             f"the manifest declares {declared_csv.get('bytes')} CSV bytes, but "
             f"{len(bytes(csv_bytes))} were supplied")
    _require(manifest.get("schema_version") == baseline.get("kind"),
             f"the manifest's schema_version {manifest.get('schema_version')!r} is not the receipt's "
             f"kind {baseline.get('kind')!r}")
    _require(manifest.get("scoring_preset") == baseline.get("scoring_preset", manifest.get("scoring_preset")),
             "the receipt and the manifest disagree about the scoring preset")
    _require(manifest.get("league_scoring_exact") is False,
             "the manifest claims exact league scoring, which this product never claims")
    _require(manifest.get("coverage_status") == baseline.get("coverage_status"),
             f"the receipt's coverage_status {baseline.get('coverage_status')!r} is not the "
             f"manifest's {manifest.get('coverage_status')!r}")

    for name, payload in (("csv_sha256", bytes(csv_bytes)), ("manifest_sha256", bytes(manifest_bytes))):
        declared = baseline.get(name)
        actual = _sha256(payload)
        _require(declared == actual,
                 f"the baseline source's {name} is {declared!r} but its bytes hash to {actual}")

    target = baseline.get("target")
    _require(isinstance(target, Mapping), "the baseline source carries no target")
    assert isinstance(target, Mapping)
    differing = [f for f in MEASUREMENT_FIELDS if target.get(f) != forecast_target.get(f)]
    if differing:
        raise TrackRecordInputError(
            "the baseline measures something else than the forecast; these fields differ: "
            + ", ".join(differing)
        )
    _require(baseline.get("league_scoring_exact") is False,
             "the baseline claims exact league scoring, which this product never claims")

    prior_season = baseline.get("prior_season")
    _require(isinstance(prior_season, int) and not isinstance(prior_season, bool),
             "the baseline source carries no prior_season")
    windows = manifest.get("season_windows") or {}
    _require(str(prior_season) in {str(k) for k in windows},
             f"the manifest declares no window for the prior season {prior_season}")
    _require(target_season is None or int(prior_season) == int(target_season) - 1,
             f"the prior season {prior_season} is not the season before the target {target_season}")
    admitted = baseline.get("admitted_seasons")
    _require(isinstance(admitted, list) and prior_season in admitted,
             f"the prior season {prior_season} is not among the source's admitted seasons")
    _require(baseline.get("coverage_status"), "the baseline source carries no coverage_status")

    # The vintage is checked against the season being forecast, never required to match the forecast's
    # own. A vintage at or after the target season would be knowledge the forecast could not have had.
    vintage = target.get("labels_through")
    _require(isinstance(vintage, int) and not isinstance(vintage, bool),
             "the baseline target carries no labels_through")
    _require(int(vintage) <= int(prior_season),
             f"the baseline's labels_through {vintage} is later than the prior season {prior_season}; "
             "that would be future knowledge")

    positions = baseline.get("positions")
    _require(isinstance(positions, Mapping) and positions,
             "the baseline source carries no prior-season positions; the position median spans every "
             "verified participant, including players no longer forecast, so their positions cannot "
             "come from the current board")
    # A bare map is a claim, not lineage. The prepared artifacts it was derived from must be present
    # and hash to what the receipt says, or a survivor-only map could reproduce exactly the
    # prohibited median.
    artifacts = baseline.get("source_artifacts")
    _require(isinstance(artifacts, list) and artifacts,
             "the baseline receipt names no source_artifacts, so the positions have no lineage")
    artifact_bytes = _validate_source_artifacts(artifacts, "baseline")
    # A verified receipt does not authorise an arbitrary map. The positions are re-derived from the
    # hash-bound raw source and compared VALUE for value: a map with every key present but one wrong
    # value would move a position median without touching a single byte of the source.
    _check_positions_against_source(positions, artifact_bytes, int(prior_season))

    rows: dict[str, dict[str, Any]] = {}
    reader = csv.DictReader(io.StringIO(bytes(csv_bytes).decode("utf-8")))
    for line in reader:
        if int(line["season"]) != prior_season:
            continue
        player = str(line["player_id"])
        points = _number(float(line["points"])) if line.get("points") not in (None, "") else None
        record = {"points": points, "games": int(line["games"]),
                  "appeared": _appeared(line.get("appeared"), player)}
        if player in rows and rows[player] != record:
            raise TrackRecordInputError(
                f"the prior-season source gives player {player} two different {prior_season} records; "
                "a disagreement is refused rather than resolved by last write"
            )
        rows[player] = record
    participants = {p for p, r in rows.items() if r.get("appeared") is True}
    unmapped = sorted(participants - set(positions))
    _require(not unmapped,
             f"the positions map covers {len(participants) - len(unmapped)} of {len(participants)} "
             f"verified {prior_season} participants; a partial map would reproduce exactly the "
             f"survivor median this baseline exists to avoid (first missing: {unmapped[:3]})")
    return {
        "envelope": baseline, "rows": rows, "positions": dict(positions),
        "prior_season": prior_season,
        "evidence": _source_evidence(baseline, "prior_season_outcomes", {
            "csv_sha256": str(baseline["csv_sha256"]),
            "manifest_sha256": str(baseline["manifest_sha256"]),
        }),
    }


def _kickoffs(schedule: Mapping[str, Any],
              zone: ZoneInfo | None = None) -> tuple[list[datetime], set[int], list[str]]:
    """Kickoffs in UTC, and the declared weeks the source actually covers.

    The preserved schedule writes a local wall clock with no offset, and the source receipt is what
    says which zone that is. So a zone must be supplied and is applied with its daylight-saving rules;
    nothing here assumes a fixed offset and nothing hardcodes a date.
    """
    season = schedule.get("season")
    _require(season == TARGET_SEASON,
             f"the schedule is for season {season!r}, not the declared {TARGET_SEASON}")

    kickoffs: list[datetime] = []
    weeks: set[int] = set()
    game_ids: list[str] = []
    seen: set[str] = set()
    for game in schedule.get("games") or []:
        reg = game.get("reg")
        _require(isinstance(reg, bool), f"a schedule game carries reg {reg!r}, which is not a boolean")
        finalized = game.get("finalized")
        _require(finalized is None or isinstance(finalized, bool),
                 f"a schedule game carries finalized {finalized!r}, which is neither a boolean nor "
                 "an explicit unknown")
        if not reg:
            continue
        week = game.get("week")
        _require(isinstance(week, int) and not isinstance(week, bool),
                 f"a schedule game carries week {week!r}, which is not a week number")
        if int(week) not in DECLARED_WEEKS:
            continue
        identifier = game.get("game_id")
        _require(isinstance(identifier, str) and identifier, "a schedule game carries no game_id")
        _require(identifier not in seen, f"the schedule lists {identifier} twice")
        seen.add(identifier)
        game_ids.append(str(identifier))
        weeks.add(int(week))
        if game.get("kickoff_at"):
            moment = _parse(game["kickoff_at"], "a schedule kickoff")
            _require("+" in str(game["kickoff_at"]) or str(game["kickoff_at"]).endswith("Z"),
                     "a schedule kickoff carries no timezone offset; the zone must be stated, "
                     "never assumed")
        else:
            day, clock = game.get("gameday"), game.get("gametime")
            _require(day and clock,
                     "a schedule game carries neither kickoff_at nor gameday and gametime")
            _require(zone is not None,
                     "the schedule states a local gametime but no timezone; the source receipt must "
                     "say which zone it is")
            local = datetime.fromisoformat(f"{day}T{clock}")
            moment = local.replace(tzinfo=zone).astimezone(timezone.utc)
        kickoffs.append(moment)
    return kickoffs, weeks, sorted(game_ids)


SCHEDULE_SOURCE = "schedule-raw.csv"
SCHEDULE_DICTIONARY = "dictionary_schedules.csv"

#: The only zone the source's own dictionary licenses for its `gametime` column. A freeform zone on
#: the prepared file is a claim; this is the claim's evidence, and the two must agree.
ACCEPTED_SCHEDULE_ZONE = "America/New_York"


def _checked_schedule_zone(schedule: Mapping[str, Any],
                           artifact_bytes: Mapping[str, bytes]) -> ZoneInfo:
    """The zone the BOUND dictionary licenses, cross-checked against what the file claims.

    A prepared schedule that simply relabels its zone would move every kickoff — three hours, in the
    Pacific case — while every hash stayed valid and every week stayed present. So the zone is read
    from the dictionary's own description of the `gametime` column, and the prepared claim must match
    it rather than be believed.
    """
    payload = artifact_bytes.get(SCHEDULE_DICTIONARY)
    _require(payload is not None,
             f"the schedule carries no {SCHEDULE_DICTIONARY}, so its stated timezone has no evidence")
    assert payload is not None

    described = ""
    for line in csv.reader(io.StringIO(payload.decode("utf-8"))):
        if line and line[0].strip() == "gametime":
            described = " ".join(line[1:]).lower()
            break
    _require(described,
             f"the bound {SCHEDULE_DICTIONARY} describes no gametime column, so the zone is unproven")
    _require("eastern" in described,
             f"the bound {SCHEDULE_DICTIONARY} describes gametime as {described[:80]!r}, which does "
             "not state the Eastern zone this recipe depends on")

    claimed = str(schedule.get("timezone") or "")
    _require(claimed == ACCEPTED_SCHEDULE_ZONE,
             f"the prepared schedule states the timezone {claimed!r}, but its own bound dictionary "
             f"describes gametime as Eastern, which is {ACCEPTED_SCHEDULE_ZONE}")
    return ZoneInfo(ACCEPTED_SCHEDULE_ZONE)
POSITION_SOURCE = "prior-positions.parquet"


def _reconcile_schedule(schedule: Mapping[str, Any], game_ids: list[str],
                        kickoffs: list[datetime], artifact_bytes: Mapping[str, bytes]) -> None:
    """The prepared schedule must be exactly what the hash-bound raw source says, replayed.

    Otherwise the frozen universe can shrink at enrollment: dropping one game keeps every declared
    week present and every proof hash intact, and simply moves the start of the season. Nothing here
    assumes a game count; the count comes from the source.
    """
    payload = artifact_bytes.get(SCHEDULE_SOURCE)
    _require(payload is not None,
             f"the schedule receipt carries no {SCHEDULE_SOURCE}, so its games cannot be reconciled "
             "against the source they claim to come from")
    assert payload is not None
    zone = _checked_schedule_zone(schedule, artifact_bytes)

    expected: dict[str, datetime] = {}
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8")))
    for line in reader:
        if line.get("season") != str(TARGET_SEASON) or line.get("game_type") != "REG":
            continue
        week = int(line["week"])
        if week not in DECLARED_WEEKS:
            continue
        day, clock = line.get("gameday"), line.get("gametime")
        _require(day and clock,
                 f"the raw schedule row {line.get('game_id')} carries no gameday or gametime")
        local = datetime.fromisoformat(f"{day}T{clock}")
        expected[str(line["game_id"])] = local.replace(tzinfo=zone).astimezone(timezone.utc)

    missing = sorted(set(expected) - set(game_ids))
    added = sorted(set(game_ids) - set(expected))
    _require(not missing,
             f"the prepared schedule drops {len(missing)} game(s) the raw source lists for the "
             f"declared weeks (first: {missing[:3]}); the frozen universe cannot shrink at enrollment")
    _require(not added,
             f"the prepared schedule adds {len(added)} game(s) the raw source does not list "
             f"(first: {added[:3]})")

    by_id = {}
    for game in schedule.get("games") or []:
        if game.get("reg") and int(game.get("week", 0)) in DECLARED_WEEKS:
            by_id[str(game["game_id"])] = game
    for identifier, moment in expected.items():
        game = by_id[identifier]
        stated = (_parse(game["kickoff_at"], "a prepared kickoff") if game.get("kickoff_at")
                  else datetime.fromisoformat(f"{game['gameday']}T{game['gametime']}")
                  .replace(tzinfo=zone).astimezone(timezone.utc))
        _require(stated == moment,
                 f"the prepared schedule states {identifier} kicks off at {_stamp(stated, 'kickoff')} "
                 f"but the raw source and its timezone recipe give {_stamp(moment, 'kickoff')}")


def _positions_from_source(payload: bytes, season: int) -> dict[str, str]:
    """Each participant's raw statistical position, read from the source bytes themselves."""
    import io as _io

    import pandas as pd

    frame = pd.read_parquet(_io.BytesIO(payload),
                            columns=["player_id", "position", "season", "week", "season_type"])
    window = frame[(frame["season"] == season) & (frame["season_type"] == "REG")
                   & (frame["week"].between(DECLARED_WEEKS[0], DECLARED_WEEKS[-1]))]
    pairs = window[["player_id", "position"]].dropna().drop_duplicates()
    duplicated = pairs["player_id"][pairs["player_id"].duplicated()].tolist()
    _require(not duplicated,
             f"the raw position source gives more than one position to {duplicated[:3]}")
    return {str(row.player_id): str(row.position) for row in pairs.itertuples()}


def _check_positions_against_source(positions: Mapping[str, str],
                                    artifact_bytes: Mapping[str, bytes], season: int) -> None:
    payload = artifact_bytes.get(POSITION_SOURCE)
    _require(payload is not None,
             f"the baseline receipt supplies positions but no {POSITION_SOURCE} to derive them from")
    assert payload is not None
    derived = _positions_from_source(payload, season)

    extra = sorted(set(positions) - set(derived))
    absent = sorted(set(derived) - set(positions))
    _require(not extra,
             f"the receipt declares positions for {len(extra)} players the raw source does not list "
             f"as {season} participants (first: {extra[:3]})")
    _require(not absent,
             f"the receipt omits {len(absent)} verified {season} participants the raw source lists "
             f"(first: {absent[:3]})")
    wrong = {p: (positions[p], derived[p]) for p in positions if str(positions[p]) != derived[p]}
    _require(not wrong,
             f"the receipt disagrees with the raw position source for {len(wrong)} player(s): "
             + ", ".join(f"{p} says {a} but the source says {b}" for p, (a, b) in list(wrong.items())[:3]))


def _appeared(value: Any, player: str) -> bool:
    """The real CSV writes booleans as text. `int("true")` raises, and a coerced 0 would be a lie."""
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    raise TrackRecordInputError(f"player {player}: appeared is {value!r}, which is not a boolean")


def _position_medians(rows: Mapping[str, Mapping[str, Any]], positions: Mapping[str, str]) -> dict:
    """The median over EVERY verified prior participant at a position.

    Not the survivors, and not the forecast-covered subset: taking the median over who is still on the
    board is how a baseline quietly flatters the forecast it is being compared against.
    """
    buckets: dict[str, list[float]] = {}
    for player, record in rows.items():
        points = _number(record.get("points"))
        position = str(positions.get(player) or "")
        # A player who did not appear is not a prior participant, so he is not in the denominator.
        # A participant who scored zero or negative IS, and stays.
        if points is None or record.get("appeared") is not True:
            continue
        if position not in MEDIAN_POSITIONS:
            continue
        buckets.setdefault(position, []).append(points)
    medians: dict[str, float] = {}
    for position, values in buckets.items():
        ordered = sorted(values)
        middle = len(ordered) // 2
        medians[position] = (
            ordered[middle] if len(ordered) % 2
            else (ordered[middle - 1] + ordered[middle]) / 2.0
        )
    return medians


# ── population ──────────────────────────────────────────────────────────────────────────────────

UNION_MODEL = "union_replacement"
REFERENCE_QUANTITY = "expected_season_points_same_window"


def _document(artifacts: Mapping[str, bytes], name: str) -> dict[str, Any]:
    payload = artifacts.get(name)
    _require(isinstance(payload, (bytes, bytearray)), f"the archived {name} is missing")
    try:
        parsed = json.loads(bytes(payload).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as bad:
        raise TrackRecordInputError(f"the archived {name} is not readable JSON: {bad}") from bad
    _require(isinstance(parsed, dict), f"the archived {name} is not a JSON object")
    return parsed


def _reference_series(board: Mapping[str, Any], seasons: int) -> dict[str, list[float]]:
    """The union_replacement producer's per-position reference, one entry per season of the window.

    This is the accepted reconstruction rule, not a new one: the board carries signed MARGINS above a
    reference, so a season's points are that margin plus that season's reference. Reading `advantage`
    or a served value as points would be a different quantity wearing the same name.
    """
    producers = [
        m for m in board.get("annual_producers") or []
        if isinstance(m, Mapping) and m.get("model_version") == UNION_MODEL
    ]
    _require(len(producers) == 1,
             f"the board declares {len(producers)} {UNION_MODEL} producers, not exactly one")
    out: dict[str, list[float]] = {}
    for position, entries in (producers[0].get("replacement") or {}).items():
        entries = entries or []
        _require(len(entries) == seasons,
                 f"the {position} reference series has {len(entries)} seasons, not {seasons}")
        series: list[float] = []
        for index, entry in enumerate(entries):
            _require(str(entry.get("rate_quantity")) == REFERENCE_QUANTITY,
                     f"the {position} reference season {index + 1} is not {REFERENCE_QUANTITY}")
            value = _strict_number(entry.get("rate_ppg"),
                                   f"the {position} reference season {index + 1}")
            _require(value is not None, f"the {position} reference season {index + 1} is absent")
            series.append(float(value))
        out[str(position)] = series
    return out


GSIS_ID = re.compile(r"\A00-\d{7}\Z")


def _identity_bridge(board: list, catalog_rows: list) -> dict[str, dict[str, Any]]:
    """Sleeper id to the outcome source's own GSIS id, from saved evidence only.

    Names are never joined. A saved `player_id` that is not GSIS-shaped is not GSIS evidence — the
    catalog carries Sleeper ids in that field for 333 rows — so it is recorded as unresolved rather
    than treated as a conflicting identity. Only two VERIFIED GSIS ids that disagree are a refusal.
    """
    bridge: dict[str, dict[str, Any]] = {}

    def offer(sleeper: Any, candidate: Any, basis: str) -> None:
        if not sleeper:
            return
        key = str(sleeper)
        entry = bridge.setdefault(key, {"source_player_id": None, "basis": None, "unresolved": []})
        if candidate is None or not GSIS_ID.match(str(candidate)):
            if candidate is not None:
                entry["unresolved"].append({"value": str(candidate), "basis": basis})
            return
        if entry["source_player_id"] and entry["source_player_id"] != str(candidate):
            raise TrackRecordInputError(
                f"the saved sources give player {key} two different verified source ids: "
                f"{entry['source_player_id']!r} ({entry['basis']}) and {candidate!r} ({basis})"
            )
        entry["source_player_id"] = str(candidate)
        entry["basis"] = basis

    for row in board:
        offer(row.get("sleeper_id"), row.get("player_id"), "report_horizon_board")
    for row in catalog_rows:
        forecast = row.get("forecast") or {}
        offer(row.get("sleeper_id"), forecast.get("join_id"),
              str(row.get("join_basis") or "catalog_forecast_join_id"))
        offer(row.get("sleeper_id"), row.get("player_id"), "catalog_player_id")
    return bridge


def _population(artifacts: Mapping[str, bytes]) -> tuple[list[dict[str, Any]], dict[str, Any], dict]:
    """The union of the archived report board and the archived catalog: every saved player, once.

    The derived ranks and comparison documents are a display cohort, not the enrolled population, and
    reading them instead is how a player who belongs to neither source appeared in an earlier build.
    """
    report = _document(artifacts, "report.json")
    catalog = _document(artifacts, "catalog.json")
    target = report.get("board_target")
    _require(isinstance(target, Mapping) and target,
             "the archived report carries no board_target, so the forecast has no declared target")

    board_block = report.get("horizon_board") or {}
    board = board_block.get("all_inspectable")
    _require(isinstance(board, list) and board, "the archived report carries no horizon board rows")
    catalog_rows = catalog.get("rows_detail")
    _require(isinstance(catalog_rows, list) and catalog_rows,
             "the archived catalog carries no rows_detail")

    years = [int(y) for y in (catalog.get("forecast_years") or [])]
    _require(years, "the archived catalog declares no forecast years")
    series = _reference_series(board_block, len(years))
    bridge = _identity_bridge(board, catalog_rows)

    catalog_by_id = {str(r["sleeper_id"]): r for r in catalog_rows if r.get("sleeper_id")}
    board_by_id = {str(r["sleeper_id"]): r for r in board if r.get("sleeper_id")}

    people: list[dict[str, Any]] = []
    for sleeper in sorted(set(board_by_id) | set(catalog_by_id)):
        board_row = board_by_id.get(sleeper)
        catalog_row = catalog_by_id.get(sleeper) or {}
        forecast, reason = _annual_forecast(board_row, catalog_row, series, years)
        if catalog_row.get("recovered") is True:
            provenance = "recovered"
        elif catalog_row.get("starting_estimate") is True:
            provenance = "starting_estimate"
        elif board_row is not None:
            provenance = "original"
        else:
            provenance = "unforecast"
        identity = board_row or catalog_row
        people.append({
            "sleeper_id": sleeper,
            "name": identity.get("name"),
            "position": (board_row or {}).get("position") or catalog_row.get("league_position"),
            "producer": (board_row or {}).get("producer") or (catalog_row.get("forecast") or {}).get("producer"),
            "provenance": provenance,
            "forecast": forecast,
            "forecast_missing_reason": reason,
            "source_player_id": (bridge.get(sleeper) or {}).get("source_player_id"),
            "identity_basis": (bridge.get(sleeper) or {}).get("basis"),
        })
    return people, dict(target), bridge


def _annual_forecast(board_row, catalog_row, series, years) -> tuple[float | None, str | None]:
    """The first target season's expected points, reconstructed the accepted way. Negatives survive."""
    if board_row is not None:
        accepted = (board_row.get("readiness") == "comparable"
                    and board_row.get("evidence_verified") is True)
        margins = {}
        for entry in board_row.get("seasons") or []:
            season = entry.get("season")
            if season is None:
                continue
            margins[int(season)] = _strict_number(entry.get("expected_margin"),
                                                  f"player {board_row.get('sleeper_id')} expected_margin")
        if not accepted:
            return None, (board_row.get("reason")
                          or "the board did not accept this forecast for the declared target")
        margin = margins.get(years[0])
        if margin is None:
            return None, f"the board carries no {years[0]} margin for this player"
        position = board_row.get("position")
        reference = series.get(str(position))
        if reference is None:
            return None, f"the board has no {position} reference series"
        value = float(margin) + reference[0]
        _require(math.isfinite(value), f"player {board_row.get('sleeper_id')} reconstructs to {value}")
        return value, None
    seasons = (catalog_row.get("forecast") or {}).get("seasons") or []
    for entry in seasons:
        if entry.get("season") == years[0]:
            points = _strict_number(entry.get("e_points"),
                                    f"player {catalog_row.get('sleeper_id')} e_points")
            if points is not None:
                return float(points), None
    return None, (catalog_row.get("missing_reason")
                  or "no accepted forecast for this player in either saved source")


# ── the streams ─────────────────────────────────────────────────────────────────────────────────

def _production_stream(
    *, people: list[dict[str, Any]], plan: Mapping[str, Any], plan_bytes: bytes | None,
    target: Mapping[str, Any], baseline: dict | None, schedule: Mapping[str, Any] | None,
    saved_at: str,
) -> dict[str, Any]:
    # The archive's own plan bytes. A hash over anything this process re-encoded would prove only
    # that this process is self-consistent, and would not match the archive.
    _require(plan_bytes, "the archived evaluation-plan.json bytes are required for the policy hash")
    assert plan_bytes is not None
    # Read the declaration from the archive's own bytes, not from the receipt's embedded copy.
    plan = json.loads(bytes(plan_bytes).decode("utf-8"))
    _require(plan.get("plan_id"), "the archived evaluation plan carries no plan_id")
    window = {"label": "2026 REG weeks 1-17", "start_at": None, "end_at": None}
    stream: dict[str, Any] = {
        "state": "input_unavailable", "reason": "", "plan": plan.get("plan_id"),
        "plan_sha256": _sha256(plan_bytes), "target": dict(target), "window": window,
        "provenance_class": "unavailable", "cutoff_at": saved_at,
        "target_start_at": None, "target_end_at": None,
        "expected_game_ids": [], "weeks_expected": list(DECLARED_WEEKS),
        "rows": [], "sources": [],
    }

    if baseline is None:
        stream["reason"] = ("No prior-season baseline source was supplied, so no production baseline "
                            "can be registered.")
        stream["rows"] = _production_rows(people, None, {})
        return stream
    stream["sources"].append(baseline["evidence"])

    if schedule is None:
        stream["reason"] = ("No schedule source was supplied, so the forecast freeze cannot be "
                            "demonstrated. The date alone is not evidence of a preseason capture.")
        stream["rows"] = _production_rows(people, baseline, {})
        return stream
    stream["sources"].append(_source_evidence(schedule, "schedule",
                                              {"source_sha256": str(schedule.get("source_sha256"))}))

    schedule_bytes = _validate_source_artifacts(schedule.get("source_artifacts") or [], "schedule")
    zone = _checked_schedule_zone(schedule, schedule_bytes)
    kickoffs, weeks, game_ids = _kickoffs(schedule, zone)
    _reconcile_schedule(schedule, game_ids, kickoffs, schedule_bytes)
    absent = [w for w in DECLARED_WEEKS if w not in weeks]
    # A schedule that says nothing about the declared weeks is a MISSING input, not a corrupt one.
    if absent:
        stream["reason"] = (
            f"The schedule source carries no regular-season games for week(s) "
            f"{', '.join(str(w) for w in absent)}, so it is not evidence about the declared "
            f"weeks {DECLARED_WEEKS[0]} to {DECLARED_WEEKS[-1]}."
        )
        stream["rows"] = _production_rows(people, baseline, {})
        return stream
    # The frozen membership a grader must match observed outcomes against, so a self-declared
    # one-game outcome cannot be graded as if it were the season.
    stream["expected_game_ids"] = game_ids
    stream["weeks_expected"] = list(DECLARED_WEEKS)
    stream["target_start_at"] = _stamp(min(kickoffs), "target_start_at")
    stream["target_end_at"] = _stamp(max(kickoffs), "target_end_at")
    stream["window"] = {"label": window["label"], "start_at": stream["target_start_at"],
                        "end_at": stream["target_end_at"]}

    # A baseline computed NOW is retrospective relative to the earlier forecast save, whatever the
    # age of the facts it is built from. There is no branch here on purpose.
    stream["provenance_class"] = "reconstructed"

    medians = _position_medians(baseline["rows"], baseline["positions"])
    stream["rows"] = _production_rows(people, baseline, medians)

    freeze = _parse(saved_at, "the archive saved_at")
    if min(kickoffs) < freeze:
        stream["state"] = "cutoff_ineligible"
        stream["reason"] = (
            f"A declared target game kicked off at {_stamp(min(kickoffs), 'kickoff')}, before the "
            f"forecast freeze at {saved_at}, so this window cannot be graded prospectively."
        )
        return stream

    stream["state"] = "awaiting_horizon"
    stream["reason"] = ("Registered. The 2026 target window has not closed, so no outcome is "
                        "available yet.")
    return stream


def _production_rows(people: list[dict[str, Any]], baseline: dict | None,
                     medians: Mapping[str, float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for person in people:
        reasons: dict[str, str] = {}
        prior: float | None = None
        median: float | None = None
        if person["forecast"] is None:
            reasons["forecast"] = person["forecast_missing_reason"] or "no archived forecast value"
        if baseline is None:
            reasons["prior_season"] = "no prior-season baseline source was supplied"
            reasons["position_median"] = "no prior-season baseline source was supplied"
        else:
            # The outcome source keys on its own player id, so the bridge is what joins them. An
            # unresolved identity is UNKNOWN, never a zero and never a name match.
            source_id = person.get("source_player_id")
            if not source_id:
                reasons["prior_season"] = (
                    "no verified source id for this player, so his prior season cannot be looked up"
                )
                record = None
            else:
                record = baseline["rows"].get(str(source_id))
            if record is None:
                # Absence from the table is not a zero. It is an unknown, and it says so.
                # (An unresolved identity already set its own reason above.)
                reasons.setdefault(
                    "prior_season",
                    f"no {baseline['prior_season']} row for this player in the verified source",
                )
            else:
                prior = _number(record.get("points"))
                if prior is None:
                    reasons["prior_season"] = "the verified row carries no points value"
            position = person["position"]
            if position and str(position) in medians:
                median = medians[str(position)]
            else:
                reasons["position_median"] = (
                    "no verified prior participants at this position in the source"
                    if position else "the archived row carries no position"
                )
        rows.append({
            "sleeper_id": person["sleeper_id"], "name": person["name"],
            "position": person["position"], "producer": person["producer"],
            "provenance": person["provenance"], "forecast": person["forecast"],
            "baselines": {"prior_season": prior, "position_median": median},
            "missing_reasons": reasons,
        })
    return rows


COMPARATOR_OFFSET_DAYS = 30
COMPARATOR_TOLERANCE_DAYS = 3


def _select_history_capture(inventory: Mapping[str, Any], *, t0: datetime,
                            configuration: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, str]:
    """The frozen trailing capture the declaration names, chosen by its rule and not by its result.

    The latest COMPLETE COMPATIBLE capture whose source as-of is at or before T0 minus 30 days and no
    more than 3 days earlier than that, and which was already known at T0. Selection is by timestamp,
    with ties broken on content hash — never by the momentum it would produce, and never by a nearest
    capture outside the window.
    """
    captures = inventory.get("captures")
    if not isinstance(captures, list) or not captures:
        return None, "the history inventory carries no captures"

    latest = t0 - timedelta(days=COMPARATOR_OFFSET_DAYS)
    earliest = latest - timedelta(days=COMPARATOR_TOLERANCE_DAYS)
    eligible: list[tuple[datetime, str, Mapping[str, Any]]] = []
    for capture in captures:
        _require(isinstance(capture, Mapping), "a history capture is not an object")
        # A capture with no stated availability cannot be dated: defaulting known_at to as_of would
        # INVENT the moment we could first have seen it, which is the whole question.
        _require(capture.get("known_at"),
                 f"the history capture {capture.get('capture_id')!r} states no known_at; when it "
                 "became available cannot be assumed from its own as-of")
        payload = capture.get("raw_bytes")
        _require(isinstance(payload, (bytes, bytearray)),
                 f"the history capture {capture.get('capture_id')!r} carries no bytes, so its prices "
                 "are unbound")
        digest = capture.get("sha256")
        _require(isinstance(digest, str) and _SHA256_HEX.match(digest),
                 f"the history capture {capture.get('capture_id')!r} carries no sha256 digest")
        _require(digest == _sha256(bytes(payload)),
                 f"the history capture {capture.get('capture_id')!r} hashes to "
                 f"{_sha256(bytes(payload))}, not the {digest} it declares")
        as_of = _parse(capture.get("as_of"), "a history capture as_of")
        known_at = _parse(capture.get("known_at"), "a history capture known_at")
        if known_at > t0:
            continue  # not yet knowable at enrollment; using it would be hindsight
        if not (earliest <= as_of <= latest):
            continue
        content = _capture_content(capture)
        _require(content.get("as_of") == capture.get("as_of"),
                 f"the history capture {capture.get('capture_id')!r} states an as-of its own bytes "
                 "do not agree with")
        if content.get("complete") is not True:
            continue
        if dict(content.get("configuration") or {}) != dict(configuration):
            continue
        eligible.append((as_of, str(capture.get("sha256") or ""), capture))
    if not eligible:
        return None, (
            f"no complete compatible capture was already known at enrollment with a source as-of in "
            f"[{_stamp(earliest, 'window start')}, {_stamp(latest, 'window end')}]"
        )
    eligible.sort(key=lambda item: (item[0], item[1]))
    return eligible[-1][2], ""


def _capture_content(capture: Mapping[str, Any]) -> dict[str, Any]:
    """The capture's own verified bytes, parsed. Sibling keys are never trusted over the file."""
    try:
        content = json.loads(bytes(capture["raw_bytes"]).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as bad:
        raise TrackRecordInputError(
            f"the history capture {capture.get('capture_id')!r} is not readable JSON: {bad}"
        ) from bad
    _require(isinstance(content, Mapping),
             f"the history capture {capture.get('capture_id')!r} is not a JSON object")
    return dict(content)


def _momentum(start_prices: Mapping[str, float | None],
              capture: Mapping[str, Any]) -> dict[str, float | None]:
    """P0 over the trailing price, minus one. Both prices must be positive; nothing is invented."""
    history = _capture_content(capture).get("prices") or {}
    out: dict[str, float | None] = {}
    for player, start in start_prices.items():
        before = _strict_number(history.get(player), f"the trailing price for {player}")
        if start is None or before is None or start <= 0 or before <= 0:
            continue
        out[player] = start / before - 1.0
    return out


def _market_configuration(artifacts: Mapping[str, bytes]) -> dict[str, Any]:
    """The capture configuration a compatible history must match, from the RAW saved market bytes."""
    market = _document(artifacts, "market.json")
    settings = market.get("settings")
    _require(isinstance(settings, Mapping) and settings,
             "the archived market capture states no settings, so no capture can be checked against it")
    return {"source": market.get("source"), "settings_hash": market.get("settings_hash"),
            **{k: settings[k] for k in sorted(settings)}}


def _league_configuration(artifacts: Mapping[str, bytes]) -> dict[str, Any]:
    """The league and market settings, read from the archived league bytes rather than a policy key."""
    document = _document(artifacts, "league.json")
    league = document.get("league") or document
    settings = league.get("scoring_settings") or {}
    # The saved league states its size by the rosters it carries, not by a total_rosters field.
    teams = league.get("total_rosters") or len(document.get("rosters") or []) or None
    _require(teams, "the archived league states no team count, so the cohort's league size is unknown")
    return {
        "teams": teams,
        "roster_positions": league.get("roster_positions"),
        "scoring": {k: settings[k] for k in ("rec", "bonus_rec_te", "pass_td") if k in settings},
        "read_from": "league.json",
    }


def _market_stream(
    *, people: list[dict[str, Any]], plan: Mapping[str, Any], receipt: Mapping[str, Any],
    history: Mapping[str, Any] | None, t0: str, ranks: Mapping[str, Any],
    configuration: Mapping[str, Any], capture_configuration: Mapping[str, Any],
) -> dict[str, Any]:
    plan_bytes = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode("utf-8")
    endpoints = plan.get("endpoints") or {}
    primary = endpoints.get("primary") or {}
    horizon = int(primary.get("offset_days") or plan.get("horizon_days") or 90)
    window_days = int(primary.get("window_days") or 3)
    opens = _parse(t0, "t0") + timedelta(days=horizon)
    stream: dict[str, Any] = {
        "state": "awaiting_capture", "reason": "", "plan": plan.get("plan_id") or plan.get("plan"),
        "plan_sha256": _sha256(plan_bytes), "t0": t0,
        "window": {"label": f"{horizon}-day movement",
                   "start_at": _stamp(opens, "window start"),
                   "end_at": _stamp(opens + timedelta(days=window_days), "window end")},
        "provenance_class": "contemporaneous",
        # The league and market settings come from the validated archived sources, never from an
        # empty key on the policy file.
        "configuration": dict(configuration),
        "capture_configuration": dict(capture_configuration),
        "comparator_capture": None, "comparator_reason": "", "rows": [], "sources": [],
    }
    if history is not None:
        stream["sources"].append(_source_evidence(history, "market_history",
                                                  {"source_sha256": str(history.get("source_sha256"))}))

    market_as_of = receipt.get("market_as_of")
    age = _parse(t0, "t0") - _parse(market_as_of, "the archived market_as_of")
    rank_rows = {str(r["sleeper_id"]): r for r in (ranks.get("rows") or []) if r.get("sleeper_id")}
    start_prices = {
        person["sleeper_id"]: _number((rank_rows.get(person["sleeper_id"]) or {}).get("market_value"))
        for person in people
    }
    momentum: dict[str, float | None] = {}
    comparator_reason = "no trailing price history was supplied"
    if history is not None:
        selected, why = _select_history_capture(history, t0=_parse(t0, "t0"),
                                                configuration=capture_configuration)
        if selected is None:
            comparator_reason = why
        else:
            momentum = _momentum(start_prices, selected)
            comparator_reason = ""
            stream["comparator_capture"] = {
                "capture_id": selected.get("capture_id"), "as_of": selected.get("as_of"),
                "known_at": selected.get("known_at"), "sha256": selected.get("sha256"),
            }
    stream["comparator_reason"] = comparator_reason
    stream["rows"] = _market_rows(people, momentum, comparator_reason == "", rank_rows)

    if age > MARKET_START_MAX_AGE or age.total_seconds() < 0:
        stream["state"] = "input_unavailable"
        stream["provenance_class"] = "unavailable"
        stream["reason"] = (
            f"The archived market reading is dated {market_as_of}, which is not within "
            f"{int(MARKET_START_MAX_AGE.total_seconds() // 3600)} hours of this enrollment. "
            "A fresh verified reading is required before start prices can be registered."
        )
        return stream

    stream["reason"] = (
        "Registered. The primary endpoint capture is not due until the window opens."
        if history is not None else
        "Registered. No trailing price history was supplied, so the momentum comparator is "
        "unavailable and the association stays descriptive."
    )
    return stream


def _market_rows(people: list[dict[str, Any]], momentum: Mapping[str, float | None],
                 has_history: bool, rank_rows: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for person in people:
        rank_row = rank_rows.get(person["sleeper_id"]) or {}
        reasons: dict[str, str] = {}
        ours = _interval(rank_row.get("our_rank"))
        theirs = _interval(rank_row.get("market_rank"))
        if ours is None:
            reasons["our_rank"] = rank_row.get("missing_reason") or "no archived rank from us"
        if theirs is None:
            reasons["market_rank"] = "no archived market rank"
        start_price = _number(rank_row.get("market_value"))
        if start_price is None:
            reasons["start_price"] = "no archived market price"
        value = momentum.get(person["sleeper_id"])
        if value is None:
            reasons["momentum"] = ("no positive price at both points for this player"
                                   if has_history else "no frozen trailing capture was selected")
        rows.append({
            "sleeper_id": person["sleeper_id"], "name": person["name"],
            "position": person["position"], "our_rank": ours, "market_rank": theirs,
            "start_price": start_price, "momentum": value, "missing_reasons": reasons,
        })
    return rows


# ── the builder ─────────────────────────────────────────────────────────────────────────────────

def build_evaluation_inputs(
    *, snapshot: Mapping[str, Any], artifacts: Mapping[str, bytes],
    baseline_source: Mapping[str, Any] | None, schedule_source: Mapping[str, Any] | None,
    market_history_source: Mapping[str, Any] | None, market_plan: Mapping[str, Any],
    captured_at: datetime,
) -> dict[str, Any]:
    """One validated enrollment plus the raw bytes it was built from. No network, no writes.

    A complete enrollment is always returned when the snapshot itself is sound: an optional source
    that is absent yields a precise per-stream `input_unavailable`, never an invented input, and never
    the deletion of the stream that WAS ready. Corrupt or contradictory bytes raise instead, because
    that is a different thing from a missing input.
    """
    _require(isinstance(snapshot, Mapping), "the snapshot must be the read_snapshot result")
    working = copy.deepcopy(dict(snapshot))  # the archive is never mutated by building a record
    receipt = working.get("snapshot")
    _require(isinstance(receipt, Mapping), "the snapshot carries no receipt")
    assert isinstance(receipt, Mapping)

    source = receipt.get("source")
    _require(isinstance(source, Mapping), "the snapshot receipt carries no source tuple")
    assert isinstance(source, Mapping)
    missing = [f for f in SIX_SOURCE_FIELDS if not source.get(f)]
    _require(not missing, f"the snapshot source tuple is missing {', '.join(missing)}")

    plan_block = receipt.get("evaluation_plan") or {}
    checked_artifacts = {str(k): bytes(v) for k, v in dict(artifacts).items()}
    enrolled_at = _stamp(captured_at, "captured_at")

    people, forecast_target, bridge = _population(checked_artifacts)
    target_season = None
    catalog_years = _document(checked_artifacts, "catalog.json").get("forecast_years") or []
    if catalog_years:
        target_season = int(catalog_years[0])
    baseline = (_validate_baseline(baseline_source, forecast_target, target_season)
                if baseline_source else None)

    production = _production_stream(
        people=people, plan=plan_block, plan_bytes=checked_artifacts.get("evaluation-plan.json"),
        target=forecast_target, baseline=baseline, schedule=schedule_source,
        saved_at=_stamp(receipt.get("saved_at"), "the archive saved_at"),
    )
    market = _market_stream(
        people=people, plan=market_plan, receipt=receipt, history=market_history_source,
        t0=enrolled_at, ranks=working.get("ranks") or {},
        configuration=_league_configuration(checked_artifacts),
        capture_configuration=_market_configuration(checked_artifacts),
    )
    for stream in (production, market):
        _require(stream["state"] in STATES, f"{stream['state']!r} is not a declared stream state")
        _require(stream["provenance_class"] in PROVENANCE_CLASSES,
                 f"{stream['provenance_class']!r} is not a declared provenance class")

    # An enrollment that does not keep its own inputs is not immutable in any useful sense: a later
    # deletion or revision of a source file would make it unreplayable. Every buffer that was
    # validated is stored, and every one of them is bound in input_hashes.
    if baseline is not None:
        envelope = baseline["envelope"]
        checked_artifacts["baseline-outcomes.csv"] = bytes(envelope["csv_bytes"])
        checked_artifacts["baseline-manifest.json"] = bytes(envelope["manifest_bytes"])
        checked_artifacts["baseline-receipt.json"] = _source_raw_bytes(envelope, "baseline receipt")
        for name, payload in _validate_source_artifacts(
            envelope.get("source_artifacts") or [], "baseline"
        ).items():
            checked_artifacts[f"source-{name}"] = payload
    if schedule_source is not None:
        checked_artifacts["schedule-source.json"] = _source_raw_bytes(schedule_source, "schedule")
        for name, payload in _validate_source_artifacts(
            schedule_source.get("source_artifacts") or [], "schedule"
        ).items():
            key = f"source-{name}"
            # The baseline and the schedule may legitimately cite the same prepared file. Identical
            # bytes are one artifact; different bytes under one name is a conflict, not a merge.
            if key in checked_artifacts and checked_artifacts[key] != payload:
                raise TrackRecordInputError(
                    f"two sources supply different bytes for the artifact {name}"
                )
            checked_artifacts[key] = payload
    if market_history_source is not None:
        checked_artifacts["market-history.json"] = _source_raw_bytes(
            market_history_source, "market history"
        )
        # Every capture the inventory names is preserved too, so the comparator can be recomputed
        # from the enrollment alone rather than from files that may later move.
        for capture in market_history_source.get("captures") or []:
            identifier = str(capture.get("capture_id") or "")
            _require(identifier and "/" not in identifier,
                     f"the history capture id {identifier!r} is not a plain name")
            key = f"market-history-capture-{identifier}.json"
            payload = bytes(capture["raw_bytes"])
            if key in checked_artifacts and checked_artifacts[key] != payload:
                raise TrackRecordInputError(
                    f"two history captures share the id {identifier} with different bytes"
                )
            checked_artifacts[key] = payload

    identity = {
        "report_sha256": source["report_sha256"], "target": forecast_target,
        "producers": sorted({str(p["producer"]) for p in people if p["producer"]}),
        "forecasts": {p["sleeper_id"]: p["forecast"] for p in people},
    }
    document = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": receipt.get("snapshot_id"),
        # Identity is the forecast itself — its report, its target, its producers and its numbers —
        # so a re-save that only changed a market date is not a new forecast.
        "forecast_identity": _sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ),
        "enrolled_at": enrolled_at,
        "source": {f: source[f] for f in SIX_SOURCE_FIELDS},
        "snapshot": dict(receipt),
        "input_hashes": {name: _sha256(payload) for name, payload in sorted(checked_artifacts.items())},
        "production": production,
        "market": market,
    }
    return {"document": document, "artifacts": checked_artifacts}
