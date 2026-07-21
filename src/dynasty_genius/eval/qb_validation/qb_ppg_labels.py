"""QB-1 D2: the Sleeper-scored QB PPG label table (spec v8, SHA 8fa244c1…).

Spec rows implemented here:
- F11 ``validate_label_table`` — the label table's fail-closed law: duplicate
  player-seasons, non-finite PPG, and missing games are NAMED rejections.
- F21 ``validate_scoring_edges`` — golden scoring rows for the edge components
  (QB receiving, fumbles lost, every 2-point path, ``pass_int``) must match
  EXACTLY, and the settings hash must match the registered pin; a mismatch
  fails the run.
- F28 ``validate_attrition_classes`` — the v9 two-axis outcome-class
  vocabulary is exhaustive ({evaluable, no_target_season, rookie_no_priors,
  cohort_ineligible_prior, cohort_ineligible_unobserved}), counts reconcile,
  and an attrition row never carries imputed metrics (a zero PPG is a
  fabricated number, not an honest absence).

The D2 contract (spec §2):
- ``y(p,t)`` = regular-season Sleeper-scored fantasy points per qualifying
  game. Postseason is excluded everywhere — D1 ingests REG-only, and a
  non-REG row reaching this module is upstream corruption, refused named.
- A qualifying game is a weekly REG row with
  ``(attempts + sacks_suffered) >= 1 OR carries >= 1`` (the pinned D1
  derivation; ``sacks := sacks_suffered``). Non-qualifying REG rows are
  excluded from numerator AND denominator by the pinned predicate — that is
  the registered definition, not a silent drop.
- Scoring is DERIVED from a versioned league-settings snapshot + hash, never
  hardcoded (``pass_int = -2`` is a fact about David's league snapshot and
  lives in fixtures/registration, not in this code). Component coverage is
  the pinned full set: passing, rushing, receiving, fumbles lost (the THREE
  split weekly columns), and every 2-point path (pass/rush/receive).
- Arithmetic is ``Decimal`` end-to-end from canonical string conversion, so
  golden rows match exactly and totals carry no float-summation artifacts;
  PPG is the Decimal quotient converted to float at the boundary.
- Rookie/no-target classification needs feature-presence knowledge D2 does
  not have: ``build_label_table`` emits evaluable labels plus the observed
  zero-qualifying player-seasons; the D2a/D3 owners assign
  ``no_target_season`` vs ``rookie_no_priors`` and this module's F28 law
  validates the classified result.

Numeric/missing-value laws mirror the slice-2-ratified identity.py closures
(one law, restated locally to keep reviewed surfaces untouched): boolean-kind
scalars of every representation are categorical, never numeric (round-5 B1);
missing-like scalars (None / NaN-family via self-inequality / pd.NA via its
caught ambiguous-bool raise) are the no-value state, never truth-tested
(rounds 4/6/7); integrality is proven losslessly in the value's own
arithmetic (round-4 B1); integral seasons must be date-representable
(1..9999, round-6 H1's domain law).
"""
from __future__ import annotations

import decimal
import hashlib
import json
import math
from decimal import Decimal, localcontext
from typing import Any, Iterable, Mapping

import numpy as np

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure

# The exhaustive outcome-class vocabulary (spec D2; rookie_no_priors is
# ASSIGNED by D3's cohort route — the vocabulary itself is D2 law).
# v9 two-axis vocabulary (amendment §B3/§B5, David-ratified 2026-07-20).
OUTCOME_CLASSES = (
    "evaluable",
    "no_target_season",
    "rookie_no_priors",
    "cohort_ineligible_prior",
    "cohort_ineligible_unobserved",
)
ATTRITION_CLASSES = (
    "no_target_season",
    "rookie_no_priors",
    "cohort_ineligible_prior",
    "cohort_ineligible_unobserved",
)
_ELIGIBILITY_AXIS = ("cohort_admitted", "rookie_no_priors", "cohort_ineligible_prior")
_TARGET_AXIS = ("target_evaluable", "no_target_season")
# The pinned total (eligibility, target) → outcome_class mapping. The absent
# combination (rookie_no_priors, no_target_season) is unreachable by
# construction and refuses by name.
_OUTCOME_BY_AXES = {
    ("cohort_admitted", "target_evaluable"): "evaluable",
    ("cohort_admitted", "no_target_season"): "no_target_season",
    ("rookie_no_priors", "target_evaluable"): "rookie_no_priors",
    ("cohort_ineligible_prior", "target_evaluable"): "cohort_ineligible_prior",
    ("cohort_ineligible_prior", "no_target_season"): "cohort_ineligible_unobserved",
}
_INELIGIBLE_REASONS = ("zero_career_dropbacks", "no_prior_roster_presence")
# Games law per class: target_evaluable classes require games > 0; the
# no-target classes require games = 0.
_POSITIVE_GAMES_CLASSES = frozenset(
    {"evaluable", "rookie_no_priors", "cohort_ineligible_prior"}
)

# Pinned weekly stat column → Sleeper scoring-settings key (full component
# coverage per spec D2). Column names are the D1.1 post-parse pins
# (VALIDATION_DATASET_COLUMNS["weekly"]); settings keys are Sleeper's
# scoring_settings vocabulary as captured by the league snapshot
# (sleeper_universe.py league capture). The three split fumble columns all
# score under the one ``fum_lost`` setting.
SCORING_COMPONENTS: tuple[tuple[str, str], ...] = (
    ("passing_yards", "pass_yd"),
    ("passing_tds", "pass_td"),
    ("passing_interceptions", "pass_int"),
    ("passing_2pt_conversions", "pass_2pt"),
    ("rushing_yards", "rush_yd"),
    ("rushing_tds", "rush_td"),
    ("rushing_2pt_conversions", "rush_2pt"),
    ("receptions", "rec"),
    ("receiving_yards", "rec_yd"),
    ("receiving_tds", "rec_td"),
    ("receiving_2pt_conversions", "rec_2pt"),
    ("sack_fumbles_lost", "fum_lost"),
    ("rushing_fumbles_lost", "fum_lost"),
    ("receiving_fumbles_lost", "fum_lost"),
)

_STAT_COLUMNS = tuple(column for column, _ in SCORING_COMPONENTS)
_SETTINGS_KEYS = tuple(dict.fromkeys(key for _, key in SCORING_COMPONENTS))

# Yardage may be negative; every other pinned stat is a non-negative count.
_YARDAGE_COLUMNS = frozenset(
    {"passing_yards", "rushing_yards", "receiving_yards"}
)

# The F21 edge components: a golden set that does not exercise QB receiving,
# fumbles lost, every 2-point path, and the interception term is not a
# scoring-edge proof — the seam refuses it rather than trusting fixtures.
_EDGE_COLUMNS = (
    "passing_interceptions",
    "passing_2pt_conversions",
    "rushing_2pt_conversions",
    "receptions",
    "receiving_yards",
    "receiving_tds",
    "receiving_2pt_conversions",
    "sack_fumbles_lost",
    "rushing_fumbles_lost",
    "receiving_fumbles_lost",
)

# The pinned qualifying-game predicate's inputs (the D1 derivation:
# ``(attempts + sacks_suffered) >= 1 OR carries >= 1``). These are NOT
# scoring components — they are validated as counts alongside the stat
# manifest so the predicate never reads an unvalidated or absent cell.
_PREDICATE_COLUMNS = ("attempts", "sacks_suffered", "carries")

_ROW_IDENTITY_COLUMNS = ("player_id", "season", "week", "season_type")


# System/process failures are never "malformed data" (round-6 H3): the broad
# conversion catches below must not relabel resource exhaustion or
# interpreter faults as a named data refusal — they re-raise these and
# refuse only ordinary conversion failures. (SystemExit/KeyboardInterrupt
# are BaseException and never enter an ``except Exception``.)
_NON_DATA_EXCEPTIONS = (MemoryError, RecursionError, SystemError)

# Module-owned Decimal arithmetic policy (round-9 B1/B2): scoring must be
# byte-stable regardless of the CALLER'S ambient context — the same stat
# line under ``localcontext(prec=2)`` scored 11 where the contract computes
# 10.68. The exact context traps Inexact, so a scoring sum either computes
# EXACTLY within 60 digits (real stat×multiplier products are ≤~15) or
# refuses named — never silently rounds; the quotient context (PPG is a
# division and legitimately inexact, e.g. 29/3) rounds deterministically at
# the module precision. Emin/Emax bound the exponent so an extreme-but-
# finite admitted operand overflows HERE — translated to the named refusal
# — instead of raising raw or emitting Infinity under a caller's trap
# configuration. ``localcontext`` swaps in a COPY, so ambient trap state
# never leaks in either direction.
_EXACT_CONTEXT = decimal.Context(
    prec=60,
    Emin=-100_000,
    Emax=100_000,
    traps=[
        decimal.InvalidOperation,
        decimal.Overflow,
        decimal.DivisionByZero,
        decimal.Inexact,
    ],
)
_QUOTIENT_CONTEXT = decimal.Context(
    prec=60,
    Emin=-100_000,
    Emax=100_000,
    traps=[decimal.InvalidOperation, decimal.Overflow, decimal.DivisionByZero],
)


def _score_components(
    values: Mapping[str, Decimal], multipliers: Mapping[str, Decimal]
) -> Decimal:
    """Sum stat×multiplier products under the module-owned exact context.

    Ordinary Decimal arithmetic failures (Overflow at the module bounds,
    Inexact beyond exact precision, InvalidOperation) translate to the named
    ``stat_value_invalid`` refusal — an unscorable line is malformed
    evidence, never a raw escape; system failures re-raise. The trailing
    finiteness check is deliberately redundant with the traps: it holds even
    if the trap configuration is ever loosened (round-9 B2's
    trap-independence requirement).
    """
    try:
        with localcontext(_EXACT_CONTEXT):
            total = Decimal(0)
            for column, key in SCORING_COMPONENTS:
                if column in values:
                    total += values[column] * multipliers[key]
    except _NON_DATA_EXCEPTIONS:
        raise
    except decimal.DecimalException as exc:
        raise QBValidationFailure(
            "stat_value_invalid",
            "scoring arithmetic cannot compute exactly within the module "
            "policy: " + _safe_repr(exc),
        ) from exc
    if not total.is_finite():
        raise QBValidationFailure(
            "stat_value_invalid",
            "non-finite scoring total — refused independent of trap "
            "configuration",
        )
    return total


def _safe_type_name(value: Any) -> str:
    """Total type-name lookup: a metaclass with a raising ``__name__``
    must not break refusal-message construction (round-6 H2)."""
    try:
        return type(value).__name__
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception:
        return "<unnamed type>"


def _safe_repr(value: Any) -> str:
    """A TOTAL diagnostic renderer (rounds 5-6 H2): malformed row/stat
    content is in-contract, so building the refusal message must stay total
    even when a value's overridden ``__repr__`` raises — and the fallback
    itself invokes a guarded type-name lookup with a constant final form."""
    try:
        return repr(value)
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception:
        pass
    try:
        return f"<unrepresentable {_safe_type_name(value)}>"
    except _NON_DATA_EXCEPTIONS:
        # Round-7 H1: a preserved system exception re-raised by the guarded
        # type-name lookup must pass through this stage too — the constant
        # fallback is for ordinary failures only.
        raise
    except Exception:
        return "<unrepresentable value>"


def _usable_text(value: Any) -> str | None:
    """An EXACT plain str, else None (round-6 B1/H1 — the general text
    boundary): a str subclass carries its own comparison/method dunders into
    categorical gates (an overridden ``__ne__`` answering False admitted a
    POST row as REG; an overridden ``strip`` raised mid-validation). Exact
    type at the data boundary makes every later compare/strip trusted."""
    if type(value) is not str:
        return None
    return value


def _is_missing(value: Any) -> bool:
    """Missing-like without truth-testing: None, the NaN family, pd.NA."""
    if value is None:
        return True
    try:
        return bool(value != value)
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception:
        return True


def _lossless_int(value: Any) -> int | None:
    """Integrality proven in the value's own arithmetic; bool-kind refused;
    the result is ALWAYS an exact plain ``int``.

    Only ``type(value) is int`` returns unconverted (round-6 B2): an int
    SUBCLASS keeps its own comparison dunders, and returning it would carry
    overridden ``__lt__``/``__ne__`` behavior into the week/games/count
    gates — subclasses go through the generic proof and come back as the
    trusted plain conversion. Broad catches are deliberate (round-5 H2
    totality): conversion runs untrusted dunders that may raise anything;
    ordinary failure means "not a lossless int", named by the caller —
    while system/resource failures re-raise (round-6 H3).
    """
    if value is None or isinstance(value, (bool, np.bool_)):
        return None
    if type(value) is int:
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except _NON_DATA_EXCEPTIONS:
            raise
        except Exception:
            return None
    try:
        converted = int(value)
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception:
        return None
    try:
        if value != converted:
            return None
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception:
        return None
    return converted


def _finite_decimal(value: Any) -> Decimal | None:
    """A finite real as an exact plain ``Decimal``, else None.

    A Decimal subclass is copied to a plain Decimal before the finiteness
    read (round-6 B2's law applied to this scalar family too), so no caller
    dunder survives into downstream arithmetic/comparison. Broad catches
    are deliberate (round-5 H2 totality); system/resource failures re-raise
    (round-6 H3).
    """
    if _is_missing(value) or isinstance(value, (bool, np.bool_)):
        return None
    if isinstance(value, Decimal):
        try:
            plain = Decimal(value)
            return plain if plain.is_finite() else None
        except _NON_DATA_EXCEPTIONS:
            raise
        except Exception:
            return None
    try:
        converted = Decimal(str(value))
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception:
        return None
    return converted if converted.is_finite() else None


def _stat_decimal(column: str, value: Any) -> Decimal | None:
    """One validated stat value: counts are non-negative lossless integers
    (a negative reception count is impossible evidence, round-3 B2's
    semantic-domain law); yardage is any finite real."""
    if column in _YARDAGE_COLUMNS:
        return _finite_decimal(value)
    count = _lossless_int(value)
    if count is None or count < 0:
        return None
    return Decimal(count)


def _frozen_settings(settings: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Freeze a settings mapping into ``(decoded_snapshot, canonical_json)``.

    Every public boundary freezes the caller's object exactly once and then
    hashes, classifies, and scores ONLY the frozen state. Two laws compose:

    - **One read** (round-3 B1): the caller's ``Mapping`` is materialized in
      a single pass, so a mutating-but-legal mapping cannot present one
      value to the fingerprint and another to the scorer.
    - **Value semantics, not references** (round-4 B1): the snapshot that is
      scored is ``json.loads`` of the SAME canonical bytes the hash
      fingerprints. A shallow reference copy would let a JSON-native scalar
      subclass encode one number for the hash while ``str()``-converting to
      another for Decimal scoring; decoding the canonical form makes every
      downstream value a plain primitive whose semantics ARE the hashed
      bytes, by construction.

    Keys must be real strings, refused named otherwise (round-3 H1) — and
    the refusal diagnostic never executes an untrusted key's ``__repr__``
    (round-4 H1): position and type name are sufficient to name the defect,
    and a hostile ``__repr__`` must not turn the named refusal into a raw
    error. ``allow_nan=False`` keeps NaN/Infinity out of the canonical form
    (round-1 H3).
    """
    if not isinstance(settings, Mapping):
        raise QBValidationFailure(
            "settings_snapshot_invalid",
            f"settings must be a mapping, got {_safe_type_name(settings)}",
        )
    raw: dict[str, Any] = {}
    bad_keys: list[str] = []
    for position, (key, value) in enumerate(settings.items()):
        # EXACT str only (round-5 H1): an accepted str SUBCLASS keeps its
        # own dunders — an overridden __lt__ that raises would surface as a
        # raw error from sort_keys mid-hash. Exact keys make every later
        # sort/compare trusted.
        if type(key) is str:
            raw[key] = value
        else:
            bad_keys.append(f"[{position}] {_safe_type_name(key)}")
    if bad_keys:
        raise QBValidationFailure(
            "settings_snapshot_invalid",
            "non-exact-string settings keys (position, type): "
            + ", ".join(bad_keys),
        )
    try:
        canonical = json.dumps(
            raw, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception as exc:
        # Round-7 H2: serialization walks nested container VALUES, so a
        # dict/list subclass whose iteration raises surfaces here — that is
        # malformed settings content, refused named; only the preserved
        # system classes above pass through raw.
        raise QBValidationFailure(
            "settings_snapshot_invalid",
            "settings snapshot is not canonically serializable: "
            + _safe_repr(exc),
        ) from exc
    return json.loads(canonical), canonical


def settings_hash(settings: Mapping[str, Any]) -> str:
    """SHA-256 over the canonical JSON of the league-settings snapshot.

    Canonical = sorted string keys, minimal separators, standard JSON
    numerics only. The fingerprint and every scored multiplier derive from
    the same canonical bytes (see ``_frozen_settings``).
    """
    _, canonical = _frozen_settings(settings)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# The EXACT, versioned vocabulary of settings keys disclosable while active
# (round-2 B1/H1). The proof standard is structural: a key is disclosable
# ONLY when no player-level source stat exists for it in the nflreadr
# player-stat dictionary — the Sleeper team-defense points/yards-allowed
# brackets are properties of a TEAM's game outcome that no individual player
# row can carry. Everything else fails closed: Sleeper's Special Teams
# Player and IDP sections are individual-player scoring, miscellaneous
# fumble rules apply to any player on any play, defensive scoring settings
# apply to all players (the Travis Hunter dual-position precedent), and
# kicker stats are player-level — none is provably QB-unreachable. EXACT
# keys only, never prefix families: a prefix admits arbitrary future keys
# (``fg_qb_bonus``) and cannot be fail-closed. Widening this list is a
# reviewed, versioned change adjudicated at the registration gate.
_TEAM_ONLY_SETTING_KEYS_V1 = frozenset(
    {
        "pts_allow", "pts_allow_0", "pts_allow_1_6", "pts_allow_7_13",
        "pts_allow_14_20", "pts_allow_21_27", "pts_allow_28_34",
        "pts_allow_35p",
        "yds_allow", "yds_allow_0_100", "yds_allow_100_199",
        "yds_allow_200_299", "yds_allow_300_349", "yds_allow_350_399",
        "yds_allow_400_449", "yds_allow_450_499", "yds_allow_500_549",
        "yds_allow_550p",
    }
)


def _classify_settings(
    settings: Mapping[str, Any],
) -> tuple[dict[str, Decimal], list[str]]:
    """Validate the pinned multipliers AND adjudicate every extra key.

    Returns ``(multipliers, disclosed_team_only_keys)``. Every pinned key
    must be PRESENT — full component coverage is the contract, and an absent
    ``rec`` would silently zero QB receiving. Extra keys (rounds 1-2 B1/H1),
    in order: an UNPARSEABLE value refuses before any vocabulary
    classification (a malformed snapshot is never read through); a provably
    zero value is inert; a key on the exact versioned team-only allowlist is
    disclosed; anything else active REFUSES — an unimplemented
    player-scoring rule makes every "Sleeper-scored" label knowingly wrong,
    and disclosure does not make a wrong number right.

    Operates on the frozen decoded snapshot (rounds 3-4 B1/H1): one caller
    read, canonical value semantics, so hash, pinned validation, and
    classification can never observe different states.
    """
    frozen, _ = _frozen_settings(settings)
    missing = [key for key in _SETTINGS_KEYS if key not in frozen]
    if missing:
        raise QBValidationFailure(
            "scoring_setting_missing",
            "pinned scoring components absent from the settings snapshot: "
            + ", ".join(missing),
        )
    validated: dict[str, Decimal] = {}
    invalid: list[str] = []
    for key in _SETTINGS_KEYS:
        value = _finite_decimal(frozen[key])
        if value is None:
            invalid.append(f"{key}={frozen[key]!r}")
        else:
            validated[key] = value
    if invalid:
        raise QBValidationFailure(
            "settings_snapshot_invalid",
            "non-numeric or non-finite scoring values: " + ", ".join(invalid),
        )
    disclosed: list[str] = []
    unsupported: list[str] = []
    malformed: list[str] = []
    for key in frozen:
        if key in _SETTINGS_KEYS:
            continue
        value = _finite_decimal(frozen[key])
        if value is None:
            # Refused BEFORE classification (round-2 H1): an unparseable
            # value on ANY extra key — allowlisted or not — is a malformed
            # snapshot, never lawful disclosure or silence.
            malformed.append(f"{key}={frozen[key]!r}")
            continue
        if value == Decimal(0):
            continue  # provably inert
        # Raw validated strings only — never str()-coerced (round-3 H1): a
        # non-string key was already refused at the freeze boundary.
        if key in _TEAM_ONLY_SETTING_KEYS_V1:
            disclosed.append(key)
        else:
            unsupported.append(f"{key}={frozen[key]!r}")
    if malformed:
        raise QBValidationFailure(
            "settings_snapshot_invalid",
            "unparseable extra scoring values: " + ", ".join(sorted(malformed)),
        )
    if unsupported:
        raise QBValidationFailure(
            "scoring_setting_unsupported",
            "active scoring rules outside the pinned component set that are "
            "not provably team-only: " + ", ".join(sorted(unsupported)),
        )
    return validated, sorted(disclosed)


def _validated_settings(settings: Mapping[str, Any]) -> dict[str, Decimal]:
    return _classify_settings(settings)[0]


def _require_settings_hash(
    settings: Mapping[str, Any], expected_hash: Any
) -> str:
    # The registered pin must be an EXACT plain str (round-5 B1): a str
    # subclass carries its own comparison dunders — an overridden __ne__
    # answering False for a mismatched pin bypassed the gate. With exact
    # types on both sides the comparison below runs trusted str semantics.
    if type(expected_hash) is not str:
        raise QBValidationFailure(
            "settings_hash_mismatch",
            "expected settings hash must be an exact plain string, got "
            + _safe_type_name(expected_hash),
        )
    if len(expected_hash) != 64 or any(
        c not in "0123456789abcdef" for c in expected_hash
    ):
        raise QBValidationFailure(
            "settings_hash_mismatch",
            "expected settings hash is not a 64-char lowercase SHA-256 hex "
            f"digest: {expected_hash!r}",
        )
    computed = settings_hash(settings)
    if computed != expected_hash:
        raise QBValidationFailure(
            "settings_hash_mismatch",
            f"settings snapshot hashes {computed}, registration pins {expected_hash}",
        )
    return computed


def score_stat_line(
    stats: Mapping[str, Any], settings: Mapping[str, Any]
) -> Decimal:
    """Sleeper points for one stat line, derived from the settings snapshot.

    Sparse stat lines are legal (an absent component contributes zero — a
    week with no receptions truly scores nothing from ``rec``); a PRESENT
    but invalid value, or a key outside the pinned component set (a typo'd
    column would otherwise silently score zero), is refused named.
    """
    if not isinstance(stats, Mapping):
        raise QBValidationFailure(
            "stat_value_invalid", f"stats must be a mapping, got {_safe_type_name(stats)}"
        )
    # The freeze happens exactly once inside classification (rounds 3-4 B1):
    # one caller read, canonical value semantics.
    multipliers = _validated_settings(settings)
    unknown = [key for key in stats.keys() if key not in _STAT_COLUMNS]
    if unknown:
        raise QBValidationFailure(
            "unknown_stat_column",
            "stat keys outside the pinned component set: "
            + ", ".join(_safe_repr(key) for key in unknown),
        )
    values: dict[str, Decimal] = {}
    invalid: list[str] = []
    for column in _STAT_COLUMNS:
        if column not in stats:
            continue
        value = _stat_decimal(column, stats[column])
        if value is None:
            invalid.append(f"{column}={_safe_repr(stats[column])}")
        else:
            values[column] = value
    if invalid:
        raise QBValidationFailure(
            "stat_value_invalid", "invalid stat values: " + ", ".join(invalid)
        )
    return _score_components(values, multipliers)


def _finite_float(value: Decimal) -> float | None:
    """The Decimal→float projection boundary (round-8 B1): a FINITE Decimal
    beyond binary-float range (``Decimal('1e10000')``) converts to ``inf`` —
    the projected primitive must be validated too, or a non-finite number
    escapes the very gate that just proved Decimal finiteness."""
    try:
        converted = float(value)
    except _NON_DATA_EXCEPTIONS:
        raise
    except Exception:
        return None
    return converted if math.isfinite(converted) else None


def _usable_player_id(value: Any) -> str | None:
    # Exact plain str via the general text boundary (round-6 H1): strip()
    # then runs trusted base-str semantics only.
    text = _usable_text(value)
    if text is None:
        return None
    stripped = text.strip()
    return stripped or None


def _valid_label_season(value: Any) -> int | None:
    season = _lossless_int(value)
    if season is None or not 1 <= season <= 9999:
        return None
    return season


def build_label_table(
    weekly_rows: Iterable[Any],
    settings: Mapping[str, Any],
    *,
    expected_settings_hash: str,
) -> dict[str, Any]:
    """Build the D2 label table from D1 weekly rows + the settings snapshot.

    Output: ``labels`` (evaluable player-seasons: qualifying_games,
    points_total, ppg), ``zero_qualifying_player_seasons`` (observed but
    never-qualifying — classification into the attrition vocabulary belongs
    to the feature-aware D2a/D3 owners), the computed ``settings_hash``, and
    ``unscored_settings_keys`` (active keys on the exact versioned TEAM-ONLY
    allowlist — the points/yards-allowed brackets no individual player row
    can carry — disclosed for the registration review). An active non-pinned
    key outside that allowlist, or any unparseable extra value, refuses the
    whole build (rounds 1-2 B1/H1): a label computed under an unimplemented
    player-scoring rule is knowingly wrong, and disclosure does not license
    it.

    Every weekly row must carry the full pinned stat manifest; absence is
    refusal, never substitution (the F15 law applied at this boundary).
    """
    # ONE materialization of the caller's mapping (rounds 3-4 B1): the hash,
    # the classification, and every scored row below read the same decoded
    # canonical state — neither a mutating Mapping nor a scalar subclass can
    # decouple the returned fingerprint from the multipliers applied.
    frozen_settings, _ = _frozen_settings(settings)
    verified_hash = _require_settings_hash(frozen_settings, expected_settings_hash)
    multipliers, unscored = _classify_settings(frozen_settings)

    if isinstance(weekly_rows, Mapping) or not hasattr(weekly_rows, "__iter__"):
        raise QBValidationFailure(
            "label_row_invalid",
            f"weekly rows must be an iterable of mappings, got "
            f"{_safe_type_name(weekly_rows)}",
        )

    totals: dict[tuple[str, int], dict[str, Any]] = {}
    observed: set[tuple[str, int]] = set()
    seen_weeks: set[tuple[str, int, int]] = set()

    for index, row in enumerate(weekly_rows):
        if not isinstance(row, Mapping):
            raise QBValidationFailure(
                "label_row_invalid",
                f"weekly row [{index}] is {_safe_type_name(row)}, not a mapping",
            )
        absent = [
            column
            for column in (
                *_ROW_IDENTITY_COLUMNS,
                *_PREDICATE_COLUMNS,
                *_STAT_COLUMNS,
            )
            if column not in row
        ]
        if absent:
            raise QBValidationFailure(
                "label_row_invalid",
                f"weekly row [{index}] lacks pinned columns: " + ", ".join(absent),
            )
        player_id = _usable_player_id(row["player_id"])
        season = _valid_label_season(row["season"])
        week = _lossless_int(row["week"])
        # Weeks are 1-indexed regular-season keys: week 0 is malformed source
        # evidence, never a countable game (round-1 H2); no upper ceiling is
        # guessed — season length has changed within the study window.
        if player_id is None or season is None or week is None or week < 1:
            raise QBValidationFailure(
                "label_row_invalid",
                f"weekly row [{index}] has unusable identity: "
                f"player_id={_safe_repr(row['player_id'])} "
                f"season={_safe_repr(row['season'])} "
                f"week={_safe_repr(row['week'])}",
            )
        if _usable_text(row["season_type"]) != "REG":
            raise QBValidationFailure(
                "non_regular_season_row",
                f"weekly row [{index}] ({player_id}, {season}, week {week}) has "
                f"season_type {_safe_repr(row['season_type'])}; postseason is excluded "
                "everywhere and D1 ingests REG-only — upstream corruption",
            )
        week_key = (player_id, season, week)
        if week_key in seen_weeks:
            raise QBValidationFailure(
                "duplicate_weekly_row",
                f"weekly row [{index}] duplicates ({player_id}, {season}, "
                f"week {week}); double-counting refused",
            )
        seen_weeks.add(week_key)

        values: dict[str, Decimal] = {}
        invalid: list[str] = []
        for column in (*_PREDICATE_COLUMNS, *_STAT_COLUMNS):
            value = _stat_decimal(column, row[column])
            if value is None:
                invalid.append(f"{column}={_safe_repr(row[column])}")
            else:
                values[column] = value
        if invalid:
            raise QBValidationFailure(
                "stat_value_invalid",
                f"weekly row [{index}] ({player_id}, {season}, week {week}): "
                + ", ".join(invalid),
            )

        observed.add((player_id, season))
        # The pinned predicate is `(attempts + sacks_suffered) >= 1 OR
        # carries >= 1`; the counts are validated non-negative, so the sum
        # test is ALGEBRAICALLY IDENTICAL to the individual comparisons
        # below — written arithmetic-free (round-10 B1) so no Decimal
        # addition ever runs under the caller's ambient context (a
        # constrained ambient Emax made ordinary attempts=10 overflow raw).
        # Comparisons are context-independent.
        qualifying = (
            values["attempts"] >= 1
            or values["sacks_suffered"] >= 1
            or values["carries"] >= 1
        )
        if not qualifying:
            continue
        # Row points via the module-owned exact context; per-bucket totals
        # accumulate as a LIST and sum under the same policy at construction
        # — an ambient-context += would silently round (round-9 B1).
        points = _score_components(values, multipliers)
        bucket = totals.setdefault(
            (player_id, season), {"points": [], "games": 0}
        )
        bucket["points"].append(points)
        bucket["games"] += 1

    labels = []
    for (player_id, season), bucket in sorted(totals.items()):
        # Aggregate under the module-owned policy (round-9 B1/B2), then the
        # projected-primitive law (round-8 B1): named refusal at every
        # stage, never a raw Decimal error or a non-finite emission.
        try:
            with localcontext(_EXACT_CONTEXT):
                total = Decimal(0)
                for row_points in bucket["points"]:
                    total += row_points
            with localcontext(_QUOTIENT_CONTEXT):
                ppg_decimal = total / Decimal(bucket["games"])
        except _NON_DATA_EXCEPTIONS:
            raise
        except decimal.DecimalException as exc:
            raise QBValidationFailure(
                "non_finite_ppg",
                f"({player_id}, {season}) aggregate arithmetic cannot "
                "compute within the module policy: " + _safe_repr(exc),
            ) from exc
        if not total.is_finite() or not ppg_decimal.is_finite():
            raise QBValidationFailure(
                "non_finite_ppg",
                f"({player_id}, {season}) non-finite aggregate — refused "
                "independent of trap configuration",
            )
        points_total = _finite_float(total)
        ppg = _finite_float(ppg_decimal)
        if points_total is None or ppg is None:
            raise QBValidationFailure(
                "non_finite_ppg",
                f"({player_id}, {season}) aggregates beyond finite float "
                "range — refused at the projection boundary",
            )
        labels.append(
            {
                "player_id": player_id,
                "season": season,
                "outcome_class": "evaluable",
                "qualifying_games": bucket["games"],
                "points_total": points_total,
                "ppg": ppg,
            }
        )
    zero_qualifying = [
        {"player_id": player_id, "season": season}
        for (player_id, season) in sorted(observed - set(totals))
    ]

    validate_label_table(labels)
    return {
        "labels": labels,
        "zero_qualifying_player_seasons": zero_qualifying,
        "settings_hash": verified_hash,
        "season_type": "REG",
        "unscored_settings_keys": unscored,
    }


def validate_label_table(labels: Iterable[Any]) -> list[dict[str, Any]]:
    """The F11 fail-closed law over a label table.

    The label table proper carries ONLY evaluable rows (classified attrition
    lives in the attrition table, F28's surface). Named rejections:
    ``duplicate_player_season``, ``missing_games`` (an evaluable row without
    a positive lossless games count is impossible evidence), and
    ``non_finite_ppg`` (absent, non-numeric, boolean, NaN, or infinite —
    detail names which).

    The return is the NORMALIZED plain-primitive projection of each row
    (player_id, season, outcome_class, qualifying_games, ppg, and
    points_total when present) — never the caller's objects (round-7 H3: a
    validated result that still carries caller-defined scalar behavior is
    not a validated result). Fields outside the projection do not survive
    the boundary.
    """
    if isinstance(labels, Mapping) or not hasattr(labels, "__iter__"):
        raise QBValidationFailure(
            "label_row_invalid",
            f"label table must be an iterable of mappings, got "
            f"{_safe_type_name(labels)}",
        )
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for index, row in enumerate(labels):
        if not isinstance(row, Mapping):
            raise QBValidationFailure(
                "label_row_invalid",
                f"label row [{index}] is {_safe_type_name(row)}, not a mapping",
            )
        player_id = _usable_player_id(row.get("player_id"))
        season = _valid_label_season(row.get("season"))
        if player_id is None or season is None:
            raise QBValidationFailure(
                "label_row_invalid",
                f"label row [{index}] has unusable identity: "
                f"player_id={_safe_repr(row.get('player_id'))} "
                f"season={_safe_repr(row.get('season'))}",
            )
        if _usable_text(row.get("outcome_class")) != "evaluable":
            raise QBValidationFailure(
                "label_row_invalid",
                f"label row [{index}] ({player_id}, {season}) has outcome_class "
                f"{_safe_repr(row.get('outcome_class'))}; the label table carries only "
                "evaluable rows — classified attrition belongs to the "
                "attrition table",
            )
        key = (player_id, season)
        if key in seen:
            raise QBValidationFailure(
                "duplicate_player_season",
                f"label row [{index}] duplicates ({player_id}, {season})",
            )
        seen.add(key)
        games = _lossless_int(row.get("qualifying_games"))
        if games is None or games < 1:
            raise QBValidationFailure(
                "missing_games",
                f"label row [{index}] ({player_id}, {season}) has "
                f"qualifying_games={_safe_repr(row.get('qualifying_games'))}; an evaluable "
                "row requires a positive integral games denominator",
            )
        ppg = _finite_decimal(row.get("ppg"))
        if ppg is None:
            raise QBValidationFailure(
                "non_finite_ppg",
                f"label row [{index}] ({player_id}, {season}) has "
                f"ppg={_safe_repr(row.get('ppg'))}",
            )
        projected_ppg = _finite_float(ppg)
        if projected_ppg is None:
            raise QBValidationFailure(
                "non_finite_ppg",
                f"label row [{index}] ({player_id}, {season}) has "
                f"ppg={_safe_repr(row.get('ppg'))} — finite as Decimal but "
                "non-finite when projected to float",
            )
        normalized: dict[str, Any] = {
            "player_id": player_id,
            "season": season,
            "outcome_class": "evaluable",
            "qualifying_games": games,
            "ppg": projected_ppg,
        }
        if "points_total" in row:
            points_total = _finite_decimal(row["points_total"])
            projected_total = (
                None if points_total is None else _finite_float(points_total)
            )
            if projected_total is None:
                raise QBValidationFailure(
                    "non_finite_ppg",
                    f"label row [{index}] ({player_id}, {season}) has "
                    f"points_total={_safe_repr(row['points_total'])}",
                )
            normalized["points_total"] = projected_total
        rows.append(normalized)
    return rows


def validate_scoring_edges(
    golden_rows: Iterable[Any],
    settings: Mapping[str, Any],
    *,
    expected_hash: str,
) -> None:
    """The F21 golden-row law: exact scoring + the settings-hash assertion.

    Each golden row is ``{"stats": <sparse stat mapping>, "expected_points":
    <finite real>}``. Comparison is exact Decimal equality — never tolerance
    — and the golden SET must collectively exercise the pinned edge
    components (QB receiving, all three fumbles-lost columns, every 2-point
    path, the interception term); an under-covering set is refused rather
    than trusted as a proof. An edge counts as covered ONLY when a golden
    row supplies it with a NONZERO validated stat — a zero-valued key proves
    nothing about its multiplier (round-1 B2: key presence alone is vacuous
    coverage).
    """
    # One freeze at this public boundary (rounds 3-4 B1): the hash assertion
    # and every golden row score against the same decoded canonical state.
    frozen_settings, _ = _frozen_settings(settings)
    _require_settings_hash(frozen_settings, expected_hash)
    if isinstance(golden_rows, Mapping) or not hasattr(golden_rows, "__iter__"):
        raise QBValidationFailure(
            "golden_row_invalid",
            f"golden rows must be an iterable of mappings, got "
            f"{_safe_type_name(golden_rows)}",
        )
    covered: set[str] = set()
    mismatches: list[str] = []
    count = 0
    for index, row in enumerate(golden_rows):
        count += 1
        if not isinstance(row, Mapping) or not isinstance(row.get("stats"), Mapping):
            raise QBValidationFailure(
                "golden_row_invalid",
                f"golden row [{index}] must be a mapping with a 'stats' mapping",
            )
        expected = _finite_decimal(row.get("expected_points"))
        if expected is None:
            raise QBValidationFailure(
                "golden_row_invalid",
                f"golden row [{index}] expected_points="
                f"{_safe_repr(row.get('expected_points'))} is not a finite real",
            )
        computed = score_stat_line(row["stats"], frozen_settings)
        # score_stat_line has already refused invalid values, so every
        # remaining stat parses; only nonzero contributions earn coverage.
        covered.update(
            column
            for column, value in row["stats"].items()
            if _stat_decimal(column, value) not in (None, Decimal(0))
        )
        if computed != expected:
            mismatches.append(
                f"golden row [{index}]: computed {computed} != expected {expected}"
            )
    if count == 0:
        raise QBValidationFailure(
            "golden_row_invalid", "the golden set is empty — nothing was proven"
        )
    uncovered = [column for column in _EDGE_COLUMNS if column not in covered]
    if uncovered:
        raise QBValidationFailure(
            "golden_coverage_missing",
            "golden set never exercises pinned edge components: "
            + ", ".join(uncovered),
        )
    if mismatches:
        raise QBValidationFailure("golden_scoring_mismatch", "; ".join(mismatches))


def validate_attrition_classes(
    rows: Iterable[Any], attrition: Mapping[str, Any]
) -> None:
    """The v9 two-axis F28 law over a CLASSIFIED collection (amendment §B5):
    exhaustive vocabulary, honest counts, no silent drops, no imputed metrics.

    - every row's ``outcome_class`` is in the pinned five-class vocabulary
      (``attrition_class_unknown`` otherwise — including absent);
    - every classified row carries usable identity under the shipped key
      ``(player_id, season)`` (``target_season`` is rejected), and a
      player-season appears at most once (``duplicate_player_season``);
    - every row carries valid axes; the total (eligibility, target) mapping
      must agree with ``outcome_class`` (``outcome_class_conflict``); the
      unreachable (rookie, no-target) combination refuses
      ``universe_membership_violation``;
    - the games law binds both ways per class: target-evaluable classes
      require ``qualifying_games >= 1``; no-target classes require an
      explicit zero (``outcome_class_conflict``);
    - a PRESENT-but-malformed games value (boolean, negative, unparseable)
      is corrupted evidence, never read as honest absence
      (``label_row_invalid``);
    - an attrition row carrying ``ppg``/``points_total`` — even zero — is an
      imputed number, not an honest absence (``attrition_row_carries_metrics``);
    - the attrition table names EVERY attrition class with a lossless
      non-negative count (explicit zeros, no omission) and each count equals
      the classified rows (``attrition_count_mismatch``).
    """
    if not isinstance(attrition, Mapping):
        raise QBValidationFailure(
            "attrition_count_mismatch",
            f"attrition table must be a mapping, got {_safe_type_name(attrition)}",
        )
    if isinstance(rows, Mapping) or not hasattr(rows, "__iter__"):
        raise QBValidationFailure(
            "label_row_invalid",
            f"classified rows must be an iterable of mappings, got "
            f"{_safe_type_name(rows)}",
        )
    counts = {name: 0 for name in ATTRITION_CLASSES}
    seen: set[tuple[str, int]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise QBValidationFailure(
                "label_row_invalid",
                f"classified row [{index}] is {_safe_type_name(row)}, not a mapping",
            )
        outcome = _usable_text(row.get("outcome_class"))
        if outcome not in OUTCOME_CLASSES:
            raise QBValidationFailure(
                "attrition_class_unknown",
                f"classified row [{index}] has outcome_class "
                f"{_safe_repr(row.get('outcome_class'))}; the "
                "pinned vocabulary is " + ", ".join(OUTCOME_CLASSES),
            )
        player_id = _usable_player_id(row.get("player_id"))
        season = _valid_label_season(row.get("season"))
        if player_id is None or season is None:
            raise QBValidationFailure(
                "label_row_invalid",
                f"classified row [{index}] has unusable identity: "
                f"player_id={_safe_repr(row.get('player_id'))} "
                f"season={_safe_repr(row.get('season'))}",
            )
        key = (player_id, season)
        if key in seen:
            raise QBValidationFailure(
                "duplicate_player_season",
                f"classified row [{index}] duplicates ({player_id}, {season}); "
                "a duplicated row silently inflates its class count",
            )
        seen.add(key)
        # v9 §B5: the shipped identity key is `season`; `target_season` is the
        # D2a-internal key and is rejected at this boundary (S34).
        if "target_season" in row:
            raise QBValidationFailure(
                "label_row_invalid",
                f"classified row [{index}] carries target_season; the F28 "
                "identity key is (player_id, season)",
            )
        eligibility = _usable_text(row.get("eligibility"))
        target = _usable_text(row.get("target"))
        if eligibility not in _ELIGIBILITY_AXIS or target not in _TARGET_AXIS:
            raise QBValidationFailure(
                "label_row_invalid",
                f"classified row [{index}] ({player_id}, {season}) lacks valid "
                f"axes: eligibility={_safe_repr(row.get('eligibility'))} "
                f"target={_safe_repr(row.get('target'))}",
            )
        if (eligibility, target) not in _OUTCOME_BY_AXES:
            raise QBValidationFailure(
                "universe_membership_violation",
                f"classified row [{index}] ({player_id}, {season}) is "
                f"({eligibility}, {target}); a rookie can enter the universe "
                "only through the label pool",
            )
        if _OUTCOME_BY_AXES[(eligibility, target)] != outcome:
            raise QBValidationFailure(
                "outcome_class_conflict",
                f"classified row [{index}] ({player_id}, {season}) declares "
                f"outcome_class {outcome!r} but its axes map to "
                f"{_OUTCOME_BY_AXES[(eligibility, target)]!r}",
            )
        if row.get("decision_supported") is not False:
            raise QBValidationFailure(
                "label_row_invalid",
                f"classified row [{index}] ({player_id}, {season}) lacks "
                "decision_supported=False",
            )
        reasons = row.get("reasons")
        reasons_valid = isinstance(reasons, list) and [
            r for r in _INELIGIBLE_REASONS if r in reasons
        ] == reasons
        if not reasons_valid or (
            (eligibility == "cohort_ineligible_prior") != bool(reasons)
        ):
            raise QBValidationFailure(
                "label_row_invalid",
                f"classified row [{index}] ({player_id}, {season}) has invalid "
                f"reasons={_safe_repr(row.get('reasons'))}: an ordered subset of "
                + ", ".join(_INELIGIBLE_REASONS)
                + ", non-empty exactly on the cohort_ineligible classes",
            )
        games_raw = row.get("qualifying_games")
        games = (
            _lossless_int(games_raw) if "qualifying_games" in row else None
        )
        if "qualifying_games" in row and (games is None or games < 0):
            raise QBValidationFailure(
                "label_row_invalid",
                f"classified row [{index}] ({player_id}, {season}) has a "
                f"malformed qualifying_games={_safe_repr(games_raw)}; corrupted "
                "evidence is never read as absence",
            )
        if outcome in _POSITIVE_GAMES_CLASSES:
            if games is None or games < 1:
                raise QBValidationFailure(
                    "outcome_class_conflict",
                    f"classified row [{index}] ({player_id}, {season}) is "
                    f"{outcome} with qualifying_games={_safe_repr(games_raw)}; "
                    "a target-evaluable class means >=1 qualifying game",
                )
        elif games is None or games != 0:
            raise QBValidationFailure(
                "outcome_class_conflict",
                f"classified row [{index}] ({player_id}, {season}) is "
                f"{outcome} with qualifying_games={_safe_repr(games_raw)}; a "
                "no-target class requires an explicit zero",
            )
        if outcome == "evaluable":
            continue
        carried = [
            field for field in ("ppg", "points_total") if field in row
        ]
        if carried:
            raise QBValidationFailure(
                "attrition_row_carries_metrics",
                f"classified row [{index}] ({outcome}) carries "
                + ", ".join(carried)
                + "; an excluded row is never imputed a number",
            )
        counts[outcome] += 1
    problems: list[str] = []
    for name in ATTRITION_CLASSES:
        if name not in attrition:
            problems.append(f"{name}: absent from the attrition table")
            continue
        declared = _lossless_int(attrition[name])
        if declared is None or declared < 0:
            problems.append(f"{name}: declared count {_safe_repr(attrition[name])} invalid")
        elif declared != counts[name]:
            problems.append(
                f"{name}: declared {declared}, classified rows carry {counts[name]}"
            )
    unknown = [_safe_repr(key) for key in attrition.keys() if key not in ATTRITION_CLASSES]
    if unknown:
        problems.append("unknown attrition classes declared: " + ", ".join(unknown))
    if problems:
        raise QBValidationFailure("attrition_count_mismatch", "; ".join(problems))
