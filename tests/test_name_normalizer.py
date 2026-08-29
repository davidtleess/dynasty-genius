"""DG-054 — the one versioned name normalizer producing staging keys (§7.1).

Verifies the four contracts the ticket names:
  - ONE deterministic pipeline, version-stamped in every output.
  - Staging keys are produced BESIDE existing keys: recognizably staging
    (versioned prefix), never mistakable for gsis / sleeper / dg_id keys.
  - Idempotence and determinism, property-tested over arbitrary input.
  - Known collision cases: the real cross-source disagreements that motivated
    the ticket (suffixes both directions, initials punctuation, unicode) DO
    collide; middle initials and genuinely different names do NOT.

Missing-like scalars (None, NaN family, pd.NA) must mint NO key — stringifying
them would create sentinel keys ("nan") that match each other into false
identity, the exact failure the QB eval lane already documented (round-6 B1).
"""
from __future__ import annotations

import math
import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.dynasty_genius.identity.name_normalizer import (
    NAME_NORMALIZER_VERSION,
    NormalizedName,
    is_staging_key,
    normalize_person_name,
    staging_key_for,
)

# ---------------------------------------------------------------------------
# Property-style tests (derandomized: the suite must be deterministic)
# ---------------------------------------------------------------------------

_any_text = st.text(max_size=64)
_ascii_text = st.text(
    alphabet=" ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.'-",
    max_size=48,
)
_prop = settings(max_examples=300, deadline=None, derandomize=True)


@_prop
@given(_any_text)
def test_idempotence(raw: str) -> None:
    """Normalizing an already-normalized name changes nothing."""
    first = normalize_person_name(raw)
    second = normalize_person_name(first.normalized)
    assert second.normalized == first.normalized
    assert second.staging_key == first.staging_key


@_prop
@given(_any_text)
def test_determinism(raw: str) -> None:
    """Same input, same output — every field, every call."""
    assert normalize_person_name(raw) == normalize_person_name(raw)


@_prop
@given(_any_text)
def test_version_stamp_and_key_shape(raw: str) -> None:
    """Every output carries the version; a key exists iff a name survived."""
    result = normalize_person_name(raw)
    assert result.normalizer_version == NAME_NORMALIZER_VERSION
    if result.normalized:
        assert re.fullmatch(r"[a-z0-9]+(?: [a-z0-9]+)*", result.normalized)
        assert result.staging_key == "stg1:" + result.normalized.replace(" ", "_")
        assert is_staging_key(result.staging_key)
    else:
        assert result.staging_key is None


@_prop
@given(_ascii_text)
def test_ascii_case_and_outer_whitespace_invariance(raw: str) -> None:
    """Casing and surrounding whitespace never change the staging key."""
    base = normalize_person_name(raw)
    assert normalize_person_name(raw.upper()).staging_key == base.staging_key
    assert normalize_person_name(f"  {raw}  ").staging_key == base.staging_key


# ---------------------------------------------------------------------------
# Known collision cases — the cross-source disagreements from the ticket
# ---------------------------------------------------------------------------

KNOWN_COLLISIONS = [
    # Generational suffixes disagree in BOTH directions between sources
    # (playerprofiler.py NameIdentityIndex docstring: the export says
    # "Calvin Austin" where the crosswalk says "Calvin Austin III", and
    # "Efton Chism III" where the crosswalk says "Efton Chism").
    ("Calvin Austin III", "Calvin Austin"),
    ("Efton Chism III", "Efton Chism"),
    ("Odell Beckham Jr.", "Odell Beckham"),
    ("Kenneth Walker III", "Kenneth Walker"),
    # Initials punctuation varies per source.
    ("A.J. Brown", "AJ Brown"),
    # Apostrophes: straight, curly, or absent.
    ("D'Andre Swift", "DAndre Swift"),
    ("D’Andre Swift", "D'Andre Swift"),
    # Diacritics fold to ASCII.
    ("José Ramírez", "Jose Ramirez"),
    # Hyphen vs space keeps token structure; trailing period on "St." drops.
    ("Amon-Ra St. Brown", "Amon Ra St Brown"),
    # Case and interior whitespace.
    ("MARVIN HARRISON JR", "Marvin  Harrison"),
]


@pytest.mark.parametrize("left,right", KNOWN_COLLISIONS)
def test_known_source_disagreements_collide(left: str, right: str) -> None:
    a = normalize_person_name(left)
    b = normalize_person_name(right)
    assert a.staging_key is not None
    assert a.staging_key == b.staging_key


NON_COLLISIONS = [
    # A middle initial "V" is not a generational suffix (trailing-only strip).
    ("Michael V Smith", "Michael Smith"),
    # v1 does no nickname aliasing — that is resolver enrichment, not
    # normalization (identity/__init__.py GIVEN_NAME_ALIASES stays put).
    ("Josh Allen", "Joshua Allen"),
    ("Lamar Jackson", "Lamar Johnson"),
]


@pytest.mark.parametrize("left,right", NON_COLLISIONS)
def test_distinct_names_do_not_collide(left: str, right: str) -> None:
    a = normalize_person_name(left)
    b = normalize_person_name(right)
    assert a.staging_key != b.staging_key


def test_same_name_distinct_players_collide_by_design() -> None:
    """Two real players named Josh Allen share ONE staging key.

    A staging key is a candidate-generation key, disambiguated downstream by
    position / draft year / college — never identity truth (§7.1: fuzzy
    candidates never materialize without corroboration).
    """
    qb = normalize_person_name("Josh Allen")  # QB, BUF
    lb = normalize_person_name("Josh Allen")  # LB/DE
    assert qb.staging_key == lb.staging_key == "stg1:josh_allen"


# ---------------------------------------------------------------------------
# Suffix handling — stripped from the key, preserved as metadata
# ---------------------------------------------------------------------------


def test_suffix_preserved_as_metadata() -> None:
    result = normalize_person_name("Odell Beckham Jr.")
    assert result.normalized == "odell beckham"
    assert result.suffix == "jr"
    assert normalize_person_name("Odell Beckham").suffix is None


def test_roman_numeral_suffixes() -> None:
    assert normalize_person_name("Robert Griffin III").suffix == "iii"
    assert normalize_person_name("William Fuller V").suffix == "v"


def test_suffix_only_token_is_kept_as_name() -> None:
    """A name that IS a suffix token is never stripped to emptiness."""
    result = normalize_person_name("Jr")
    assert result.normalized == "jr"
    assert result.suffix is None
    assert result.staging_key == "stg1:jr"


def test_stacked_suffixes_strip_deterministically() -> None:
    result = normalize_person_name("John Smith II Jr")
    assert result.normalized == "john smith"
    assert result.suffix == "jr"  # rightmost stripped first, first recorded


# ---------------------------------------------------------------------------
# Missing-like input mints NO key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing", [None, float("nan"), math.nan])
def test_missing_like_scalars_mint_no_key(missing: object) -> None:
    result = normalize_person_name(missing)
    assert result.raw == ""
    assert result.normalized == ""
    assert result.staging_key is None
    assert result.normalizer_version == NAME_NORMALIZER_VERSION


def test_pandas_missing_scalars_mint_no_key() -> None:
    pd = pytest.importorskip("pandas")
    for missing in (pd.NA, pd.NaT):
        result = normalize_person_name(missing)
        assert result.normalized == ""
        assert result.staging_key is None


@pytest.mark.parametrize("raw", ["", "   ", "...", "?!", "-", "'"])
def test_empty_and_punctuation_only_mint_no_key(raw: str) -> None:
    result = normalize_person_name(raw)
    assert result.normalized == ""
    assert result.staging_key is None


# ---------------------------------------------------------------------------
# Output surface: dict form for identity outcomes, key recognizer, helper
# ---------------------------------------------------------------------------


def test_to_dict_carries_the_version_stamp() -> None:
    d = normalize_person_name("Justin Jefferson").to_dict()
    assert d == {
        "raw": "Justin Jefferson",
        "normalized": "justin jefferson",
        "suffix": None,
        "staging_key": "stg1:justin_jefferson",
        "normalizer_version": NAME_NORMALIZER_VERSION,
    }


def test_result_is_immutable() -> None:
    result = normalize_person_name("Justin Jefferson")
    assert isinstance(result, NormalizedName)
    with pytest.raises(Exception):
        result.normalized = "tampered"  # type: ignore[misc]


def test_is_staging_key_recognizes_only_staging_keys() -> None:
    assert is_staging_key("stg1:justin_jefferson")
    assert is_staging_key("stg2:someone")  # future versions stay recognizable
    assert not is_staging_key("00-0033873")  # gsis_id
    assert not is_staging_key("4881")  # sleeper_id
    assert not is_staging_key("josh_allen_qb_1996")  # dg_id
    assert not is_staging_key("stg1:")  # empty body is not a key
    assert not is_staging_key("")
    assert not is_staging_key(None)


def test_staging_key_for_convenience_helper() -> None:
    assert staging_key_for("A.J. Brown") == "stg1:aj_brown"
    assert staging_key_for(None) is None
