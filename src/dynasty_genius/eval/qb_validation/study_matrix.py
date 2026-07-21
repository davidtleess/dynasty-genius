"""D2a — the v9 study matrix builder (`build_study_matrix`, F3).

Contract of record: frozen spec v9 (SHA-256 347c2d6e30d2…) + the ratified
computability amendment (SHA-256 b7221a7a8b69…), sections A1-A5 / B1-B7.

Boundary order is law (§B1): registration hash gate (F7) → seven-dataset F1
provenance admission → shape/column validation (F14/F15) on defensive copies →
semantic row validation (§A3) → construction. Every emitted scalar is an
exact-plain primitive; system exceptions (MemoryError/RecursionError/
SystemError) propagate untouched — no broad catch exists on this path.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Iterable, Mapping

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
from src.dynasty_genius.eval.qb_validation.identity import resolve_draft_join
from src.dynasty_genius.eval.qb_validation.qb_ppg_labels import (
    _lossless_int,
    _safe_repr,
    _safe_type_name,
    _usable_player_id,
    _usable_text,
    _valid_label_season,
)
from src.dynasty_genius.eval.qb_validation.registration import (
    require_registration_hash,
)
from src.dynasty_genius.eval.qb_validation.sources import (
    VALIDATION_DATASETS,
    load_validation_sources,
)

MATRIX_VERSION = "qb_validation_matrix.v1"
TARGET_SEASONS = tuple(range(2016, 2026))
_STUDY_SEASONS = tuple(range(2015, 2026))

# §A3: the seven weekly fields under the null/corruption law. passing_epa is
# the sole expressly-paired null route (§A2) and is validated separately.
_NULL_LAW_COUNT_FIELDS = (
    "attempts",
    "completions",
    "sacks_suffered",
    "passing_tds",
    "passing_interceptions",
)
_NULL_LAW_SIGNED_FIELDS = ("sack_yards_lost", "passing_yards")
# Consumed by the qualifying predicate / H2; held to the same corruption law
# (a consumed field is never silently skipped), documented extension.
_EXTRA_COUNT_FIELDS = ("carries", "rushing_tds")

# §B7: module-owned immutable manifest declarations. Declared ONCE here; D3
# consumes by import and never redeclares (F27's validator stays parked).
H1_MANIFEST = (
    ("epa_per_dropback", "t1"),
    ("cpoe", "t1"),
    ("sack_rate", "t1"),
    ("any_a", "t1"),
    ("completion_pct", "t1"),
)
H2_MANIFEST = (
    ("rush_att_per_game", "t1"),
    ("rush_yds_per_game", "t1"),
    ("rush_td_share", "t1"),
    ("rush_yds_per_att", "t1"),
)
H3_MANIFEST = (
    ("dropbacks_per_game", "t1"),
    ("pass_att_per_game", "t1"),
    ("qualifying_games", "t1"),
    ("career_dropbacks", "career"),
    ("team_proe", "t1"),
)
_IDENTITY_GROUPS = (
    ("age_at_season_start", "static"),
    ("draft_round", "static"),
    ("draft_overall", "static"),
    ("is_udfa", "static"),
)
H4_MANIFEST = H1_MANIFEST + H2_MANIFEST + H3_MANIFEST + _IDENTITY_GROUPS
_ALL_FEATURES = tuple(name for name, _ in H4_MANIFEST)


def _refuse(reason: str, detail: str) -> None:
    raise QBValidationFailure(reason, detail)


def _finite_float(value: Any, field: str, where: str) -> float:
    """Exact-plain finite float from an untrusted signed numeric."""
    if type(value) is int:
        return float(value)
    if isinstance(value, float):
        result = float(value)
    elif isinstance(value, int) and not isinstance(value, bool):
        result = float(int(value))
    else:
        _refuse(
            "stat_value_invalid",
            f"{where}: {field}={_safe_repr(value)} is {_safe_type_name(value)}, "
            "not a finite numeric",
        )
    if not math.isfinite(result):
        _refuse("stat_value_invalid", f"{where}: {field}={result!r} is not finite")
    return result


def _is_null(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _records(frame: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in frame.to_dict("records")]


def _validated_weekly_row(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    """§A3 semantic law over one weekly row → exact-plain primitives."""
    where = f"weekly row [{index}]"
    out: dict[str, Any] = {}
    player_id = _usable_player_id(row.get("player_id"))
    season = _valid_label_season(row.get("season"))
    if player_id is None or season is None:
        _refuse(
            "stat_value_invalid",
            f"{where}: unusable identity player_id="
            f"{_safe_repr(row.get('player_id'))} season={_safe_repr(row.get('season'))}",
        )
    out["player_id"], out["season"] = player_id, season
    out["position"] = _usable_text(row.get("position")) or ""
    out["team"] = _usable_text(row.get("team")) or ""
    out["week"] = _lossless_int(row.get("week")) or 0
    for field in _NULL_LAW_COUNT_FIELDS + _EXTRA_COUNT_FIELDS:
        value = row.get(field)
        if _is_null(value):
            _refuse(
                "stat_value_invalid",
                f"{where}: {field} is null — a null consumed stat is corruption, "
                "never silently skipped",
            )
        parsed = _lossless_int(value)
        if parsed is None or parsed < 0:
            _refuse(
                "stat_value_invalid",
                f"{where}: {field}={_safe_repr(value)} must be a non-negative "
                "integral count",
            )
        out[field] = parsed
    if out["completions"] > out["attempts"]:
        _refuse(
            "stat_value_invalid",
            f"{where}: completions={out['completions']} > attempts={out['attempts']}",
        )
    syl = row.get("sack_yards_lost")
    if _is_null(syl):
        _refuse("stat_value_invalid", f"{where}: sack_yards_lost is null")
    syl_int = _lossless_int(syl)
    if syl_int is None:
        _refuse(
            "stat_value_invalid",
            f"{where}: sack_yards_lost={_safe_repr(syl)} is not integral",
        )
    if syl_int > 0:
        # §A2/§A3: the source signs sack yardage <= 0; positive is corruption.
        _refuse(
            "stat_value_invalid",
            f"{where}: sack_yards_lost={syl_int} is positive; the source signs "
            "this field <= 0",
        )
    out["sack_yards_lost"] = syl_int
    py = row.get("passing_yards")
    if _is_null(py):
        _refuse("stat_value_invalid", f"{where}: passing_yards is null")
    out["passing_yards"] = _finite_float(py, "passing_yards", where)
    ry = row.get("rushing_yards")
    if _is_null(ry):
        # Round-1 H1: null on a consumed field is corruption — never an
        # observed zero; passing_epa stays the sole paired-null route.
        _refuse("stat_value_invalid", f"{where}: rushing_yards is null")
    out["rushing_yards"] = _finite_float(ry, "rushing_yards", where)
    epa = row.get("passing_epa")
    out["passing_epa"] = (
        None if _is_null(epa) else _finite_float(epa, "passing_epa", where)
    )
    kind = _usable_text(row.get("season_type"))
    out["season_type"] = kind or ""
    return out


def _qualifying(row: Mapping[str, Any]) -> bool:
    return (row["attempts"] + row["sacks_suffered"]) >= 1 or row["carries"] >= 1


def build_study_matrix(
    sources: Mapping[str, Any],
    *,
    registration: dict[str, Any],
    expected_registration_hash: str,
) -> dict[str, Any]:
    """Build the v9 D2a candidate matrix (frozen spec §D2a + amendment §B)."""
    # (1) F7/F23 registration gate — before any computation.
    require_registration_hash(registration, expected_registration_hash)

    # First source touch uses .get so system exceptions from a hostile mapping
    # propagate untouched (S31); a non-mapping refuses at the F1 gate below.
    if isinstance(sources, Mapping):
        for name in VALIDATION_DATASETS:
            sources.get(name)

    # (2) Seven-dataset F1 provenance admission (state envelopes, snapshots).
    pool = load_validation_sources(sources)

    # (3) True defensive copy FIRST, then the REAL F14 shape gate and F15
    # column gate on that copy (round-1 B3 — no local surrogate, no TOCTOU).
    # The pbp pin `posteam` is consumed under its post-parse name
    # `offense_team` (VALIDATION_PARSED_RENAMES). F14 runs shape-only here so
    # an absent pinned column earns F15's named `manifest_column_missing`.
    from src.dynasty_genius.adapters.nflreadpy_qb_adapter import (
        VALIDATION_DATASET_COLUMNS,
        VALIDATION_PARSED_RENAMES,
    )
    from src.dynasty_genius.eval.qb_validation.guards import (
        validate_dataset_shape,
        validate_manifest_columns,
    )

    frames: dict[str, list[dict[str, Any]]] = {}
    for name in VALIDATION_DATASETS:
        frame = pool[name]["frame"].copy()
        renames = VALIDATION_PARSED_RENAMES.get(name, {})
        pinned = tuple(
            renames.get(column, column)
            for column in VALIDATION_DATASET_COLUMNS[name]
        )
        validate_dataset_shape(frame, dataset=name)
        validate_manifest_columns(frame, pinned, dataset=name)
        frames[name] = _records(frame)

    # (4) Semantic validation + exact-plain normalization.
    weekly_all: list[dict[str, Any]] = []
    for index, raw in enumerate(frames["weekly"]):
        row = _validated_weekly_row(raw, index)
        if row["season_type"] == "REG":
            weekly_all.append(row)

    # Round-1 B1 + round-2 B1: study-season coverage is an EXACT SET at D2a
    # for EVERY time-scoped dataset — weekly, season_summary, REG rosters,
    # REG pbp. A missing season is a silent CPOE/roster/PROE gap; a SURPLUS
    # out-of-window season would leak into career aggregates outside the
    # registered window. Both directions refuse by name (loader bypass via
    # provenance-shaped injected states is exactly why this re-check exists).
    def _require_season_coverage(name: str, observed: set[int]) -> None:
        missing = [s for s in _STUDY_SEASONS if s not in observed]
        if missing:
            _refuse(
                "source_season_missing",
                f"{name} source lacks study season(s): "
                + ", ".join(str(s) for s in missing)
                + " — a coverage gap is a refusal, never a silent hole",
            )
        surplus = sorted(observed - set(_STUDY_SEASONS))
        if surplus:
            _refuse(
                "season_out_of_scope",
                f"{name} source carries out-of-window season(s): "
                + ", ".join(str(s) for s in surplus)
                + " — rows outside the registered window are refused, never "
                "silently kept or dropped",
            )

    _require_season_coverage("weekly", {row["season"] for row in weekly_all})
    _require_season_coverage(
        "season_summary",
        {
            _valid_label_season(raw.get("season"))
            for raw in frames["season_summary"]
        }
        - {None},
    )
    _require_season_coverage(
        "rosters",
        {
            _valid_label_season(raw.get("season"))
            for raw in frames["rosters"]
            if _usable_text(raw.get("game_type")) == "REG"
        }
        - {None},
    )
    _require_season_coverage(
        "pbp",
        {
            _valid_label_season(raw.get("season"))
            for raw in frames["pbp"]
            if _usable_text(raw.get("season_type")) == "REG"
        }
        - {None},
    )

    # 1b season summary: duplicate refusal BEFORE the one-to-one join (S33).
    summary: dict[tuple[str, int], dict[str, Any]] = {}
    for index, raw in enumerate(frames["season_summary"]):
        pid = _usable_player_id(raw.get("player_id"))
        season = _valid_label_season(raw.get("season"))
        if pid is None or season is None:
            _refuse(
                "stat_value_invalid",
                f"season_summary row [{index}] has unusable identity",
            )
        key = (pid, season)
        if key in summary:
            _refuse(
                "duplicate_player_season",
                f"season_summary duplicates ({pid}, {season}); the CPOE join "
                "is one-to-one by contract",
            )
        cpoe = raw.get("passing_cpoe")
        summary[key] = {
            "position": _usable_text(raw.get("position")) or "",
            "passing_cpoe": None
            if _is_null(cpoe)
            else _finite_float(cpoe, "passing_cpoe", f"season_summary row [{index}]"),
        }

    roster_presence: set[tuple[str, int]] = set()  # any REG row, any status
    roster_qb: set[tuple[str, int]] = set()  # REG + roster position QB
    for raw in frames["rosters"]:
        pid = _usable_player_id(raw.get("player_id") or raw.get("gsis_id"))
        season = _valid_label_season(raw.get("season"))
        if pid is None or season is None:
            continue
        if _usable_text(raw.get("game_type")) != "REG":
            continue  # S28: postseason rows never qualify
        roster_presence.add((pid, season))
        if _usable_text(raw.get("position")) == "QB":
            roster_qb.add((pid, season))

    players_by_id = {
        _usable_player_id(row.get("gsis_id")): row
        for row in frames["players"]
        if _usable_player_id(row.get("gsis_id")) is not None
    }
    draft_rows = frames["draft_picks"]

    # Per-player QB aggregates; team aggregates stay ALL-POSITION (S27).
    qb_rows = [r for r in weekly_all if r["position"] == "QB"]
    qb_qualifying: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for row in qb_rows:
        if _qualifying(row):
            qb_qualifying.setdefault(row["player_id"], {}).setdefault(
                row["season"], []
            ).append(row)
    # Round-1 B2: rookie-history evidence is ALL-POSITION REG weekly presence
    # (the amendment's predicate carries no position qualifier); the QB filter
    # applies only to label_pool / features / career dropbacks.
    any_week_all: dict[str, set[int]] = {}
    for row in weekly_all:
        any_week_all.setdefault(row["player_id"], set()).add(row["season"])

    def dropbacks(rows: Iterable[Mapping[str, Any]]) -> int:
        return sum(r["attempts"] + r["sacks_suffered"] for r in rows)

    def career_dropbacks_through(pid: str, season: int) -> int:
        seasons = qb_qualifying.get(pid, {})
        return sum(
            dropbacks(rows) for s, rows in seasons.items() if s <= season
        )

    team_rush_tds: dict[tuple[str, int], int] = {}
    for row in weekly_all:  # pre-QB-filter, all positions (S27)
        key = (row["team"], row["season"])
        team_rush_tds[key] = team_rush_tds.get(key, 0) + row["rushing_tds"]

    proe_by_team_season: dict[tuple[str, int], list[float]] = {}
    for index, raw in enumerate(frames["pbp"]):
        if _usable_text(raw.get("season_type")) != "REG":
            continue
        team = _usable_text(raw.get("offense_team")) or ""
        season = _valid_label_season(raw.get("season"))
        oe = raw.get("pass_oe")
        if season is None or _is_null(oe):
            continue
        proe_by_team_season.setdefault((team, season), []).append(
            _finite_float(oe, "pass_oe", f"pbp row [{index}]")
        )

    # H2 audit fact (amendment r7 §B4/S35, David-ratified): per target season,
    # the count of MATRIX rows whose t−1 CPOE join found a 1b row that does not
    # read QB. Populated inside h_features, which runs once per matrix row.
    cpoe_non_qb_counts: dict[int, int] = {t: 0 for t in TARGET_SEASONS}

    def attributed_team(rows: list[dict[str, Any]]) -> str | None:
        """Most t−1 qualifying games; tie → the later-in-season stint."""
        if not rows:
            return None
        games: dict[str, int] = {}
        latest: dict[str, int] = {}
        for row in rows:
            games[row["team"]] = games.get(row["team"], 0) + 1
            latest[row["team"]] = max(latest.get(row["team"], 0), row["week"])
        best = max(games.values())
        tied = [team for team, count in games.items() if count == best]
        return max(tied, key=lambda team: latest[team])

    def h_features(pid: str, target: int) -> dict[str, Any]:
        prior = target - 1
        rows = qb_qualifying.get(pid, {}).get(prior, [])
        games = len(rows)
        db = dropbacks(rows)
        att = sum(r["attempts"] for r in rows)
        features: dict[str, Any] = {}
        # H1 — ALL teams, no attribution (amendment §A2 / veto B7).
        features["completion_pct"] = (
            sum(r["completions"] for r in rows) / att if att else None
        )
        features["sack_rate"] = (
            sum(r["sacks_suffered"] for r in rows) / db if db else None
        )
        features["any_a"] = (
            (
                sum(r["passing_yards"] for r in rows)
                + 20 * sum(r["passing_tds"] for r in rows)
                - 45 * sum(r["passing_interceptions"] for r in rows)
                + sum(r["sack_yards_lost"] for r in rows)
            )
            / db
            if db
            else None
        )
        epa_rows = [r for r in rows if r["passing_epa"] is not None]
        epa_db = dropbacks(epa_rows)
        features["epa_per_dropback"] = (
            sum(r["passing_epa"] for r in epa_rows) / epa_db if epa_db else None
        )
        # Total precedence rule (r7 §B4): position is tested INDEPENDENTLY of
        # value. (a) no 1b row → null, not counted; (b) joined non-QB row →
        # null, counted whether its CPOE is null or present; (c) joined
        # QB-position row with null CPOE → null, not counted.
        joined = summary.get((pid, prior))
        if joined is not None and joined["position"] != "QB":
            cpoe_non_qb_counts[target] += 1
            features["cpoe"] = None
        else:
            features["cpoe"] = None if joined is None else joined["passing_cpoe"]
        # H2 — attributed team for the share only.
        carries = sum(r["carries"] for r in rows)
        features["rush_att_per_game"] = carries / games if games else None
        features["rush_yds_per_game"] = (
            sum(r["rushing_yards"] for r in rows) / games if games else None
        )
        features["rush_yds_per_att"] = (
            sum(r["rushing_yards"] for r in rows) / carries if carries else None
        )
        team = attributed_team(rows)
        share = None
        if team is not None:
            denominator = team_rush_tds.get((team, prior), 0)
            if denominator > 0:
                numerator = sum(
                    r["rushing_tds"] for r in rows if r["team"] == team
                )
                share = numerator / denominator
        features["rush_td_share"] = share
        # H3.
        features["dropbacks_per_game"] = db / games if games else None
        features["pass_att_per_game"] = att / games if games else None
        features["qualifying_games"] = games
        features["career_dropbacks"] = career_dropbacks_through(pid, prior)
        proe = proe_by_team_season.get((team, prior)) if team is not None else None
        features["team_proe"] = sum(proe) / len(proe) if proe else None
        # H4 identity groups.
        player_row = players_by_id.get(pid)
        features["age_at_season_start"] = _age_at(player_row, target)
        features.update(_draft_capital(player_row, pid, draft_rows))
        return features

    def _age_at(player_row: Mapping[str, Any] | None, target: int) -> float | None:
        birth = _usable_text(player_row.get("birth_date")) if player_row else None
        if not birth:
            return None
        try:
            year, month, day = (int(part) for part in birth.split("-"))
            born = date(year, month, day)
        except (ValueError, TypeError):
            return None
        return (date(target, 9, 1) - born).days / 365.25

    def _draft_capital(
        player_row: Mapping[str, Any] | None,
        pid: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        study = dict(player_row) if player_row else {"gsis_id": pid}
        record = resolve_draft_join(study, rows)
        if record["resolution"] in {"UDFA", "DRAFTED"}:
            return {
                "is_udfa": record["is_udfa"],
                "draft_round": record["draft_round"],
                "draft_overall": record["draft_overall"],
            }
        # TRIAGE never becomes imputed capital (S30).
        return {"is_udfa": None, "draft_round": None, "draft_overall": None}

    # (5) Universe + two-axis classification (§B2/§B3).
    matrix: list[dict[str, Any]] = []
    audit_by_season: dict[int, list[dict[str, Any]]] = {t: [] for t in TARGET_SEASONS}
    no_target_counts: dict[int, int] = {t: 0 for t in TARGET_SEASONS}
    for target in TARGET_SEASONS:
        prior = target - 1
        label_pool = {
            pid
            for pid, seasons in qb_qualifying.items()
            if target in seasons
        }
        roster_pool = {pid for pid, season in roster_qb if season == prior}
        cohort = {
            pid
            for pid in set(qb_qualifying) | roster_pool
            if career_dropbacks_through(pid, prior) >= 1
            and (pid, prior) in roster_presence
        }
        for pid in sorted(label_pool | roster_pool | cohort):
            evaluable_target = pid in label_pool
            if pid in cohort:
                target_axis = (
                    "target_evaluable" if evaluable_target else "no_target_season"
                )
                if target_axis == "no_target_season":
                    no_target_counts[target] += 1
                row = {
                    "player_id": pid,
                    "target_season": target,
                    "eligibility": "cohort_admitted",
                    "target": target_axis,
                    "decision_supported": False,
                }
                features = h_features(pid, target)
                # Round-1 B4: every manifest feature is exact plain float|None
                # at the output boundary; identity/coverage ints are pinned
                # separately.
                row.update(
                    {
                        name: (None if value is None else float(value))
                        for name, value in features.items()
                    }
                )
                matrix.append(row)
                continue
            prior_weekly = any(
                season <= prior for season in any_week_all.get(pid, set())
            )
            prior_roster = any(
                season <= prior and key == pid for key, season in roster_presence
            )
            if not prior_weekly and not prior_roster:
                eligibility = "rookie_no_priors"
                reasons: list[str] = []
            else:
                eligibility = "cohort_ineligible_prior"
                reasons = []
                if career_dropbacks_through(pid, prior) < 1:
                    reasons.append("zero_career_dropbacks")
                if (pid, prior) not in roster_presence:
                    reasons.append("no_prior_roster_presence")
            target_axis = (
                "target_evaluable" if evaluable_target else "no_target_season"
            )
            if eligibility == "rookie_no_priors" and target_axis == "no_target_season":
                _refuse(
                    "universe_membership_violation",
                    f"({pid}, {target}): a rookie can enter the universe only "
                    "through the label pool",
                )
            outcome = (
                eligibility
                if target_axis == "target_evaluable"
                else "cohort_ineligible_unobserved"
            )
            audit_by_season[target].append(
                {
                    "player_id": pid,
                    "target_season": target,
                    "eligibility": eligibility,
                    "target": target_axis,
                    "outcome_class": outcome,
                    "reasons": reasons,
                    "decision_supported": False,
                }
            )

    matrix.sort(key=lambda row: (row["target_season"], row["player_id"]))
    seen_keys: set[tuple[str, int]] = set()
    for row in matrix:
        key = (row["player_id"], row["target_season"])
        if key in seen_keys:
            _refuse("duplicate_player_season", f"matrix duplicates {key}")
        seen_keys.add(key)

    manifests = {
        name: {
            "features": [
                {"name": feature, "lookback": lookback, "decision_supported": False}
                for feature, lookback in declaration
            ]
        }
        for name, declaration in (
            ("h1", H1_MANIFEST),
            ("h2", H2_MANIFEST),
            ("h3", H3_MANIFEST),
            ("h4", H4_MANIFEST),
        )
    }

    attrition = {
        str(target): {
            "counts": {
                "no_target_season": no_target_counts[target],
                "rookie_no_priors": sum(
                    1
                    for row in audit_by_season[target]
                    if row["outcome_class"] == "rookie_no_priors"
                ),
                "cohort_ineligible_prior": sum(
                    1
                    for row in audit_by_season[target]
                    if row["outcome_class"] == "cohort_ineligible_prior"
                ),
                "cohort_ineligible_unobserved": sum(
                    1
                    for row in audit_by_season[target]
                    if row["outcome_class"] == "cohort_ineligible_unobserved"
                ),
            },
            "audit": sorted(
                audit_by_season[target],
                key=lambda row: (row["target_season"], row["player_id"]),
            ),
        }
        for target in TARGET_SEASONS
    }

    return {
        "matrix_version": MATRIX_VERSION,
        "decision_supported": False,
        "matrix": matrix,
        "manifests": manifests,
        "attrition": attrition,
        "coverage": {
            "target_seasons": list(TARGET_SEASONS),
            "rows_per_season": {
                str(target): sum(
                    1 for row in matrix if row["target_season"] == target
                )
                for target in TARGET_SEASONS
            },
            "cpoe_non_qb_joins": {
                str(target): cpoe_non_qb_counts[target] for target in TARGET_SEASONS
            },
        },
    }
