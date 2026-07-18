"""QB-1 identity resolution: join gates and the draft-capital join closure.

Spec rows implemented here (v8, SHA 8fa244c1…):
- F17 ``validate_identity_overlap`` — a zero-overlap identity join aborts with
  the named ``identity_join_empty`` reason; no empty-pool metrics are emitted.
- F34 ``resolve_draft_join`` — the D1 dataset-5 join contract, every resolution
  state driven: gsis-joined DRAFTED; fallback-joined DRAFTED (age check ±1 via
  the DOB formula, college via the pinned normalization); fallback-ambiguous /
  cross-check conflict / missing draft-row season / drafted-but-unjoinable /
  missing identity keys (``missing_identity_keys``, Amendment A, David-ratified
  2026-07-18) → TRIAGE, never silently UDFA; UDFA only after both USABLE keys
  miss (pinned constants one past the 7-round/262-pick maximum).

The name-normalization algorithm is the F32 pin (NFKD → ASCII fold → lowercase
→ strip punctuation and generational suffixes → collapse whitespace); the F32
reconciliation gate itself is a later slice and is deliberately not exported.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any, Mapping, Sequence

import numpy as np

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure

# Pinned UDFA constants: one past the 7-round / 262-pick maximum (spec D1.5).
UDFA_DRAFT_ROUND = 8
UDFA_DRAFT_OVERALL = 263

# Pinned age-check tolerance: covers the April-draft / Sept-1 reference offset.
_AGE_TOLERANCE_YEARS = 1

_GENERATIONAL_SUFFIXES = re.compile(r"\b(jr|sr|ii|iii|iv)\b\.?", re.IGNORECASE)
_PUNCTUATION = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def normalize_name(name: Any) -> str:
    """The pinned F32 normalization: NFKD → ASCII → lowercase → strip → collapse.

    Missing-like scalars (None, NaN, NaT, pd.NA) normalize to the EMPTY no-key
    state — stringifying them would mint sentinel keys ("nan") that match each
    other into false identity (round-6 B1). The self-inequality test catches
    the NaN family without truth-testing; pd.NA's ambiguous-bool raise is
    caught and reads as missing.
    """
    if name is None:
        return ""
    try:
        if name != name:
            return ""
    except Exception:
        return ""
    folded = unicodedata.normalize("NFKD", str(name))
    folded = folded.encode("ascii", "ignore").decode("ascii").lower()
    folded = _GENERATIONAL_SUFFIXES.sub(" ", folded)
    folded = _PUNCTUATION.sub(" ", folded)
    return _WHITESPACE.sub(" ", folded).strip()


def validate_identity_overlap(joined_pairs: Sequence[Any]) -> list[Any]:
    """Zero identity-join overlap is a named abort, never an empty-pool run (F17)."""
    pairs = list(joined_pairs)
    if not pairs:
        raise QBValidationFailure(
            "identity_join_empty",
            "the identity join produced zero gsis-sleeper pairs; no metrics emitted",
        )
    return pairs


def _computed_age(birth_date: date, draft_season: int) -> int:
    reference = date(int(draft_season), 9, 1)
    return int((reference - birth_date).days / 365.25)


def _parse_birth_date(value: Any) -> date | None:
    if value is None:
        return None
    # pandas NaT self-compares unequal (like NaN) yet ISA datetime, and its
    # .date() returns NaT again — catch it BEFORE the datetime branch or the
    # later date-arithmetic raises raw TypeError (round-4 H1). A missing
    # datetime64 DOB is a normal pandas state, not API misuse.
    try:
        if value != value:
            return None
    except Exception:
        return None
    # datetime (and pandas Timestamp, a datetime subclass) IS a date subclass:
    # normalize FIRST, or date-arithmetic against a plain date raises raw
    # TypeError (round-3 H1 — the same subclass defect repaired in F19).
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> int | None:
    """Robust int coercion: malformed external values become None, never raise.

    Non-integral numerics are MALFORMED, not truncatable — an external
    temporal, age, or capital key is never silently rounded, in ANY numeric
    representation (round-4 B1: np.float32(1.5) and Decimal("1.5") are as
    fractional as float 1.5). Integrality is proven by comparing the converted
    int back against the ORIGINAL value in its own arithmetic — lossless,
    type-independent; NaN fails the comparison, inf fails the conversion.
    Boolean-kind scalars of EVERY representation are categorical, not numeric:
    np.bool_ is not a Python-bool instance and would otherwise convert to a
    "valid" 0/1 through the generic path (round-5 B1 — truth is not capital).
    """
    if value is None or isinstance(value, (bool, np.bool_)):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    try:
        converted = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    try:
        if value != converted:
            return None
    except Exception:
        return None
    return converted


def _valid_season(value: Any) -> int | None:
    """An integral season that ``date()`` can represent (1..9999); anything
    else is no season key at all — date-arithmetic must never see it
    (round-6 H1: year-domain ValueErrors are not a named closure)."""
    season = _parse_int(value)
    if season is None or not 1 <= season <= 9999:
        return None
    return season


def _draft_row_id(draft_row: Mapping[str, Any] | None) -> Any:
    """Stable draft-row identity: gsis when present, else the season/round/pick
    composite — the 108/597 null-gsis rows stay recoverable (round-2 B3)."""
    if draft_row is None:
        return None
    gsis = _usable_key(draft_row.get("gsis_id"))
    if gsis is not None:
        return gsis
    season = _parse_int(draft_row.get("season"))
    rnd = _parse_int(draft_row.get("round"))
    pick = _parse_int(draft_row.get("pick"))
    if season is None or rnd is None or pick is None:
        return None
    return f"draft:{season}:r{rnd}:p{pick}"


def _usable_key(value: Any) -> Any:
    """A usable identity-key value, or None — WITHOUT truth-testing.

    Missing-like scalars (NaN family via self-inequality, pd.NA via its caught
    ambiguous-bool) and empty/whitespace strings read as absent (round-7 B1:
    raw truthiness raises on pd.NA and leaks NaN/NaT into pinned audit
    identity).
    """
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _first_usable_name(row: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    """First candidate whose normalization is non-empty — NO scalar truthiness
    (``a or b`` raises on pd.NA's ambiguous bool; round-6 B1)."""
    for key in keys:
        value = row.get(key)
        if normalize_name(value):
            return value
    return None


def _row_name(row: Mapping[str, Any]) -> Any:
    """The draft list's name field is ``pfr_player_name`` (live-verified +
    frozen fixture); ``name`` is accepted for hermetic fixtures."""
    return _first_usable_name(row, ("pfr_player_name", "name"))


def _study_name(row: Mapping[str, Any]) -> Any:
    """The players dataset's name field is ``display_name`` (live-verified);
    ``name`` is accepted for hermetic fixtures."""
    return _first_usable_name(row, ("display_name", "name"))


def _age_check(
    study_row: Mapping[str, Any], draft_row: Mapping[str, Any]
) -> dict[str, Any]:
    """Computed-vs-recorded draft age (±1 pinned tolerance).

    ``computable`` distinguishes a check that RAN and failed (a source
    conflict) from one that could not run (degraded inputs) — the two have
    different closure consequences on the gsis-joined path.
    """
    birth_date = _parse_birth_date(study_row.get("birth_date"))
    draft_age = _parse_int(draft_row.get("age"))
    season = _valid_season(draft_row.get("season"))
    if birth_date is None or draft_age is None or season is None:
        return {
            "draft_age": draft_age,
            "computed_age": None,
            "delta": None,
            "pass": False,
            "computable": False,
        }
    computed = _computed_age(birth_date, season)
    delta = abs(computed - draft_age)
    return {
        "draft_age": draft_age,
        "computed_age": computed,
        "delta": delta,
        "pass": delta <= _AGE_TOLERANCE_YEARS,
        "computable": True,
    }


def _college_check(
    study_row: Mapping[str, Any], draft_row: Mapping[str, Any]
) -> dict[str, Any]:
    study_college = normalize_name(study_row.get("college_name"))
    draft_college = normalize_name(draft_row.get("college"))
    if not study_college or not draft_college:
        return {"result": "missing"}
    return {"result": "pass" if study_college == draft_college else "conflict"}


def _cross_check_conflict(
    age_check: Mapping[str, Any], college_check: Mapping[str, Any]
) -> bool:
    """A check that RAN and failed is a dataset-2 source conflict (spec D1.5:
    fail-closed to triage, never imputed). Uncomputable checks are degraded
    inputs, not conflicts."""
    if college_check["result"] == "conflict":
        return True
    return bool(age_check["computable"]) and not age_check["pass"]


def _audit(
    study_row: Mapping[str, Any],
    draft_row: Mapping[str, Any] | None,
    matched_by: str | None,
    resolution: str,
    *,
    reason: str | None = None,
    age_check: dict[str, Any] | None = None,
    college_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    study_id = _usable_key(study_row.get("gsis_id"))
    if study_id is None:
        study_id = _usable_key(study_row.get("player_id"))
    record: dict[str, Any] = {
        "study_player_id": study_id,
        "draft_row_id": _draft_row_id(draft_row),
        "matched_by": matched_by,
        "normalized_study_name": normalize_name(_study_name(study_row)),
        "normalized_draft_name": normalize_name(_row_name(draft_row)) if draft_row else None,
        "age_check": age_check,
        "college_check": college_check,
        "resolution": resolution,
    }
    if reason is not None:
        record["reason"] = reason
    if resolution == "UDFA":
        record["is_udfa"] = 1
        record["draft_round"] = UDFA_DRAFT_ROUND
        record["draft_overall"] = UDFA_DRAFT_OVERALL
    elif resolution == "DRAFTED":
        # Dataset 5 is the authoritative capital source and H4 consumes
        # {draft_round, draft_overall, is_udfa}: a DRAFTED record without its
        # joined capital would discard the very data the join exists to carry
        # (round-2 B3). Callers guarantee parseability before choosing DRAFTED.
        record["is_udfa"] = 0
        record["draft_round"] = _parse_int(draft_row.get("round")) if draft_row else None
        record["draft_overall"] = _parse_int(draft_row.get("pick")) if draft_row else None
    return record


def _drafted_or_unjoinable(
    study_row: Mapping[str, Any],
    draft_row: Mapping[str, Any],
    matched_by: str,
    *,
    age_check: dict[str, Any],
    college_check: dict[str, Any],
) -> dict[str, Any]:
    """Finalize a joined row: DRAFTED only with parseable capital, else TRIAGE.

    A matched draft row whose round/pick cannot be read — or reads as a
    semantically impossible non-positive value (round-3 B2: draft capital is
    1-indexed; zero and negatives are corruption, not capital) — is a true
    source gap: fail-closed to triage, never imputed (spec D1.5). No upper
    bound is imposed: the registered 1980-2025 coverage includes 12-round
    drafts, and guessing a ceiling would be its own defect.
    """
    rnd = _parse_int(draft_row.get("round"))
    pick = _parse_int(draft_row.get("pick"))
    if rnd is None or pick is None or rnd < 1 or pick < 1:
        return _audit(
            study_row,
            draft_row,
            matched_by,
            "TRIAGE",
            reason="drafted_but_unjoinable",
            age_check=age_check,
            college_check=college_check,
        )
    return _audit(
        study_row,
        draft_row,
        matched_by,
        "DRAFTED",
        age_check=age_check,
        college_check=college_check,
    )


def resolve_draft_join(
    study_row: Mapping[str, Any], draft_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Resolve one study QB against the authoritative drafted list (F34).

    Resolution states are exhaustive: DRAFTED (gsis- or fallback-joined with the
    pinned audit fields), TRIAGE (fallback-ambiguous, cross-check conflict,
    missing draft-row season, drafted-but-unjoinable, duplicate gsis, missing
    identity keys — ``missing_identity_keys``, Amendment A), and UDFA only after
    both usable keys match nothing in the drafted list.
    """
    gsis_id = _usable_key(study_row.get("gsis_id"))
    if gsis_id is not None:
        # Draft-side keys pass through the same helper: a missing-like draft
        # GSIS never raises and never equals a real key (round-7 B1).
        gsis_matches = [
            row for row in draft_rows if _usable_key(row.get("gsis_id")) == gsis_id
        ]
        if len(gsis_matches) == 1:
            row = gsis_matches[0]
            age_check = _age_check(study_row, row)
            college_check = _college_check(study_row, row)
            if _cross_check_conflict(age_check, college_check):
                # A ran-and-failed cross-check on the primary key is a true
                # dataset-2 source conflict → TRIAGE, never imputed (B5).
                return _audit(
                    study_row,
                    row,
                    "gsis",
                    "TRIAGE",
                    reason="cross_check_conflict",
                    age_check=age_check,
                    college_check=college_check,
                )
            return _drafted_or_unjoinable(
                study_row, row, "gsis", age_check=age_check, college_check=college_check
            )
        if len(gsis_matches) > 1:
            return _audit(
                study_row, None, "gsis", "TRIAGE", reason="duplicate_gsis_in_draft_list"
            )

    study_name = normalize_name(_study_name(study_row))
    if not study_name:
        # UDFA requires MISSING BY BOTH USABLE KEYS; a study row with no usable
        # name (and no gsis match above) has no fallback key to miss —
        # unverifiable is TRIAGE, never a silent UDFA and never a sentinel-key
        # match (round-6 B1). The fifth TRIAGE reason per spec v8 Amendment A
        # (David-ratified 2026-07-18).
        return _audit(
            study_row, None, None, "TRIAGE", reason="missing_identity_keys"
        )
    candidates = [
        row for row in draft_rows if normalize_name(_row_name(row)) == study_name
    ]

    if not candidates:
        return _audit(study_row, None, None, "UDFA")
    if len(candidates) >= 2:
        return _audit(
            study_row, None, "name_season", "TRIAGE", reason="fallback_ambiguous"
        )

    row = candidates[0]
    if _valid_season(row.get("season")) is None:
        # Absent, unparseable, AND date-unrepresentable season keys land here:
        # no valid season key, no fallback join (rounds 2/6: malformed values
        # stay inside the named closure, never a raw date error).
        return _audit(
            study_row, row, "name_season", "TRIAGE", reason="missing_draft_row_season"
        )
    age_check = _age_check(study_row, row)
    college_check = _college_check(study_row, row)
    if college_check["result"] == "conflict":
        return _audit(
            study_row,
            row,
            "name_season",
            "TRIAGE",
            reason="cross_check_conflict",
            age_check=age_check,
            college_check=college_check,
        )
    if not age_check["pass"]:
        # On the fallback path the age check must PASS (degraded-college rule):
        # failed OR uncomputable → drafted-but-unjoinable, never silently UDFA.
        return _audit(
            study_row,
            row,
            "name_season",
            "TRIAGE",
            reason="drafted_but_unjoinable",
            age_check=age_check,
            college_check=college_check,
        )
    return _drafted_or_unjoinable(
        study_row, row, "name_season", age_check=age_check, college_check=college_check
    )
