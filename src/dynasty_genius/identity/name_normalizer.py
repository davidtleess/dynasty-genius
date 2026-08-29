"""The one versioned name normalizer producing staging keys (§7.1, DG-054).

Master proposal §7.1 (docs/strategies/2026-08-19-dynasty-genius-master-proposal-3.md:329):
"Exactly one versioned name normalizer produces staging keys." This module is
that normalizer. Every output carries ``normalizer_version`` so any identity
outcome that stores a staging key can cite exactly which pipeline produced it —
the precondition for identity assertions ever being evidence-grade.

WHAT A STAGING KEY IS — AND IS NOT
    A staging key is a candidate-generation / grouping key that lives BESIDE
    the existing keys (gsis_id, sleeper_id, dg_id). It is deliberately
    collision-friendly: two players who share a written name share a staging
    key, and the disagreements sources actually exhibit (generational suffixes
    present in one source and absent in the other, "A.J." vs "AJ", curly vs
    straight apostrophes, diacritics) collapse to ONE key. Disambiguation by
    position / draft year / college happens downstream; §7.1 forbids a fuzzy
    candidate from materializing into production truth without deterministic
    corroboration or human approval. The ``stgN:`` prefix makes a staging key
    self-identifying and unmistakable for a live identifier —
    :func:`is_staging_key` is the guard.

SCOPING LAW (David, ratified 2026-08-26)
    The identity migration is post-season; this module is an additive enabler.
    It re-keys NOTHING live. The scattered per-source normalizers it supersedes
    stay in place until their own migration tickets, each adopting this module
    by choice, not by tonight's rewiring:

    - src/dynasty_genius/playerprofiler.py:145            (_norm / _norm_no_suffix)
    - src/dynasty_genius/identity/__init__.py:28          (normalize_player_name → dg_id)
    - src/dynasty_genius/identity/college_prospect_identity.py:186
    - src/dynasty_genius/adapters/prospect_identity_resolver.py:26
    - src/dynasty_genius/audit/identity_coverage_matrix.py:55
    - src/dynasty_genius/eval/qb_validation/identity.py:41 (pinned F32 chain —
      registered evidence; must NEVER be silently re-pointed)
    - src/dynasty_genius/eval/qb_validation/execution.py:397
    - src/dynasty_genius/adapters/cfbd_qb_adapter.py:84

THE v1 PIPELINE (frozen — changing ANY step is a version bump, never an edit)
    1. Missing guard: None and the NaN family (float NaN, pd.NA, pd.NaT) mint
       NO key. Stringifying them would create sentinel keys ("nan") that match
       each other into false identity (the QB lane's round-6 B1 finding).
    2. NFKD-decompose, encode ASCII (ignoring what will not fold), lowercase.
    3. Remove periods and apostrophes outright ("a.j." → "aj", "d'andre" →
       "dandre") — the punctuation sources disagree on WITHIN a token.
    4. Every other non-alphanumeric run separates tokens ("amon-ra" →
       "amon ra") — token structure is kept, not concatenated away.
    5. Strip TRAILING generational suffix tokens (jr, sr, ii, iii, iv, v),
       preserving the first one stripped as metadata; never strip the only
       remaining token. Trailing-only, unlike the legacy anywhere-strip
       chains, so a middle initial "V" survives.
    6. Join with single spaces → ``normalized``; the staging key is
       ``stg1:<normalized with underscores>``, or None when nothing survived.

    Deliberate v1 divergences from the legacy chains are documented in the
    ticket build record: suffix stripping is trailing-only (qb_validation
    strips anywhere), and initials punctuation is removed rather than
    space-replaced (qb_validation would key "A.J. Brown" as "a j brown").
    Divergence is the point of versioning: v1 is a fresh, citable contract,
    not a re-implementation of any one legacy chain.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional

_VERSION_NUMBER = 1

NAME_NORMALIZER_VERSION = f"dg_name_normalizer.v{_VERSION_NUMBER}"
"""The citable version stamp carried in every output."""

_STAGING_PREFIX = f"stg{_VERSION_NUMBER}:"
_STAGING_KEY_RE = re.compile(r"stg\d+:[a-z0-9_]+")

# Step 3: punctuation that varies WITHIN a token across sources — removed.
_INTRA_TOKEN_PUNCTUATION_RE = re.compile(r"[.']")
# Step 4: everything else that is not a-z / 0-9 separates tokens.
_TOKEN_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")

_GENERATIONAL_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})


@dataclass(frozen=True, slots=True)
class NormalizedName:
    """One normalization outcome, version-stamped.

    ``to_dict()`` is the fragment an ingest identity outcome embeds so the
    outcome can cite the normalizer that produced its staging key.
    """

    raw: str
    normalized: str
    suffix: Optional[str]
    staging_key: Optional[str]
    normalizer_version: str

    def to_dict(self) -> dict[str, Optional[str]]:
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "suffix": self.suffix,
            "staging_key": self.staging_key,
            "normalizer_version": self.normalizer_version,
        }


def _is_missing(raw: Any) -> bool:
    """True for None and the NaN family — the values that must mint no key.

    Self-inequality catches float NaN and pd.NaT without truth-testing;
    pd.NA's ambiguous-bool raise on ``raw != raw`` reads as missing.
    """
    if raw is None:
        return True
    try:
        if raw != raw:
            return True
    except Exception:
        return True
    return False


def normalize_person_name(raw: Any) -> NormalizedName:
    """Run the frozen v1 pipeline. Deterministic, idempotent, total.

    Accepts any scalar: strings normalize; missing-like values (None, NaN,
    pd.NA, pd.NaT) return the empty no-key outcome rather than raising, so
    ingest lanes can call this row-wise without pre-filtering.
    """
    if _is_missing(raw):
        return NormalizedName(
            raw="",
            normalized="",
            suffix=None,
            staging_key=None,
            normalizer_version=NAME_NORMALIZER_VERSION,
        )

    text = str(raw)
    folded = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    lowered = folded.lower()
    joined = _INTRA_TOKEN_PUNCTUATION_RE.sub("", lowered)
    tokens = [token for token in _TOKEN_SEPARATOR_RE.split(joined) if token]

    suffix: Optional[str] = None
    while len(tokens) > 1 and tokens[-1] in _GENERATIONAL_SUFFIXES:
        stripped = tokens.pop()
        if suffix is None:
            suffix = stripped

    normalized = " ".join(tokens)
    staging_key = (
        _STAGING_PREFIX + normalized.replace(" ", "_") if normalized else None
    )
    return NormalizedName(
        raw=text,
        normalized=normalized,
        suffix=suffix,
        staging_key=staging_key,
        normalizer_version=NAME_NORMALIZER_VERSION,
    )


def staging_key_for(raw: Any) -> Optional[str]:
    """The staging key alone, for call sites that need nothing else."""
    return normalize_person_name(raw).staging_key


def is_staging_key(value: Any) -> bool:
    """True iff ``value`` is a staging key from ANY version of this module.

    The guard consumers use to keep staging keys out of live key columns —
    and live keys out of staging columns. gsis_id ("00-0033873"), sleeper_id
    ("4881"), and dg_id ("josh_allen_qb_1996") all fail this check.
    """
    return isinstance(value, str) and _STAGING_KEY_RE.fullmatch(value) is not None
