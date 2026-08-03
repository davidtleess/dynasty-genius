"""Property-based contract for ingestion grain and normalization.

`hypothesis` has been installed in this project (6.161.0) and used ZERO times —
0 library imports across `tests/` and `src/`; every grep match for the word is
the English noun from the QB-1 study prose. This file is the first use.

Why it exists: on 2026-08-02 the injuries stream shipped a defect where
`week=15` and `week=15.0` — the same observation — produced two different
`row_key` values and were stored as two rows. It was found because Codex pointed
at it. The property below states the invariant that was missing, and Hypothesis
searches for its counterexample rather than waiting for someone to think of one.

WHAT THESE TESTS ACTUALLY EARN, stated exactly — an earlier version of this
docstring repeated an overclaim that had already been retracted, which made it a
DURABLE record of a corrected mistake (Codex R2-M1):

  * The invariants and the axes are CHOSEN BY HAND. The first test explicitly
    constructs the int / float / text spellings; the second generates whitespace
    strings only. Neither generates None, duplicate rows, or grain combinations.
  * What Hypothesis contributes is GENERATED VALUE COVERAGE AND SHRINKING INSIDE
    those chosen invariants: it confirmed the key divergence held across the whole
    generated range rather than at one lucky value, minimized to week=1 /
    season=2015, and reported it as structural rather than value-specific.

That is real and it is narrower than "finds these cases on its own".
"""
from __future__ import annotations

from functools import lru_cache

from hypothesis import given, settings
from hypothesis import strategies as st

from src.dynasty_genius.nflverse_usage import build_streams, normalize_rows

SEASON = 2024


class _Identity:
    def resolve(self, value, *, kind):
        return value, "canonical_resolved"


@lru_cache(maxsize=1)
def _bound_injuries():
    # Cached: build_streams() imports nflreadpy, and paying that inside the
    # per-example path trips Hypothesis's deadline on the first call only.
    return {spec.name: spec for spec in build_streams()}["injuries"]


def _record(**overrides):
    base = {
        "season": SEASON,
        "game_type": "REG",
        "team": "HOU",
        "week": 15,
        "gsis_id": "00-0039359",
        "position": "TE",
        "full_name": "Cade Stover",
        "first_name": "Cade",
        "last_name": "Stover",
        "report_primary_injury": "Illness",
        "report_secondary_injury": None,
        "report_status": "Out",
        "practice_primary_injury": "Illness",
        "practice_secondary_injury": None,
        "practice_status": "Did Not Participate In Practice",
        "date_modified": "2024-12-15T14:17:06+00:00",
    }
    base.update(overrides)
    return base


def _key_for(record) -> str:
    rows, _ = normalize_rows(
        [record], spec=_bound_injuries(), season=SEASON, identity=_Identity()
    )
    return rows[0]["row_key"]


@settings(max_examples=50, deadline=None)
@given(
    week=st.integers(min_value=1, max_value=22),
    season=st.integers(min_value=2015, max_value=2030),
)
def test_semantically_equal_grain_coordinates_key_identically(week, season):
    """The same observation must key identically however the provider typed it.

    nflverse types `season`/`week` as Float64 in 2020 and Int32 from 2021, so a
    single stream genuinely carries both. If the key is built from the RAW record
    rather than the normalized row, one observation gets two keys and is stored
    twice — silently, because the grain-uniqueness check sees two distinct keys
    and is satisfied.
    """
    as_int = _record(week=week, season=season)
    as_float = _record(week=float(week), season=float(season))
    as_text = _record(week=str(week), season=str(season))

    assert _key_for(as_int) == _key_for(as_float), (
        "int and float spellings of one observation produced different row_keys"
    )
    assert _key_for(as_int) == _key_for(as_text), (
        "text and numeric spellings of one observation produced different row_keys"
    )


@settings(max_examples=50, deadline=None)
@given(blank=st.text(alphabet=" \t\n\r", max_size=6))
def test_any_whitespace_token_normalizes_to_the_same_absence(blank):
    """45 true nulls and 69 whitespace scrape artifacts are one absence, not two.

    The hand-written contract enumerated None, "", "   " and "\\n    ". This
    searches the whole whitespace space instead of the four someone thought of.
    """
    rows, _ = normalize_rows(
        [_record(practice_status=blank)],
        spec=_bound_injuries(),
        season=SEASON,
        identity=_Identity(),
    )
    assert rows[0]["practice_status"] is None
