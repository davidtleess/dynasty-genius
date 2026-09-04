"""DG-155 — the annual consensus snapshot, and the rule that makes it comparable.

The only evidence this project holds that a free consensus ranking orders players better than
Engine B is a series of dated snapshots of ``files/values.csv`` from
``github.com/dynastyprocess/data``. The values are FantasyPros-ECR-derived (source family
``dynastyprocess_ecr_2qb``), so a verdict from them reads as "beats expert consensus", never
"beats the trade market" — that is a different object, captured daily from FantasyCalc.

**Provenance, checked rather than inherited (Fred, 2026-09-04).** The licence is GPL-3.0, read
out of the repository itself rather than taken from the docstring in
``scripts/verify_dynastyprocess_source.py`` that asserts it. Access is a read-only git clone,
not scraping, and GPL-3.0 grants copying. The source is absent from the prohibited registry
(which names KTC, FootballGuys and Dynasty Nerds), and the verification script records David's
own sign-off for it.

**Two things the filing assumed that are not true, and the reason this module exists in this
shape rather than as a one-off fetch on a deadline:**

1. There is NO hard capture deadline. The four stored files were extracted from git history,
   not downloaded on their dates. History reaches back to 2019 across 361 commits touching the
   file, and git history is immutable, so a 2026-09-08 snapshot captured in October is the same
   bytes as one captured on the day. Verified end to end: the nearest commit on-or-before
   2024-09-08 (``1f17c551``, committed 2024-09-06) reproduces the stored ``values_2024-09-08``
   byte for byte.
2. 2025 is NOT a permanent gap. A commit sits at 2025-09-05, exactly what the rule below
   selects for a 2025-09-08 target.

So this takes a target date rather than hard-coding a year, and any missing year in the series
can be recovered whenever someone asks.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Optional, Sequence

SOURCE_URL = "https://github.com/dynastyprocess/data"
SOURCE_LICENSE = "GPL-3.0"
SOURCE_FAMILY = "dynastyprocess_ecr_2qb"
SOURCE_PATH = "files/values.csv"

# The annual convention the existing four files follow. A snapshot taken on a different date
# is not comparable to them: roster news, injuries and camp movement between the dates are
# exactly what holding the date constant controls for.
SNAPSHOT_MONTH_DAY = (9, 8)

# ±7 days, matching scripts/verify_dynastyprocess_source.py's _PIT_WINDOW_DAYS. Widening this
# silently is how a snapshot stops being the same object as the ones it is compared against.
WINDOW_DAYS = 7

# The shape of the stored snapshots, pinned by a test against values_2024-09-08.csv.
SNAPSHOT_COLUMNS: Sequence[str] = (
    "player",
    "pos",
    "team",
    "age",
    "draft_year",
    "ecr_1qb",
    "ecr_2qb",
    "ecr_pos",
    "value_1qb",
    "value_2qb",
    "scrape_date",
    "fp_id",
)

# Without these the file cannot serve the comparison it is captured for, so their absence is a
# refusal rather than a warning. `value_2qb` is the ranking signal in a superflex league;
# `fp_id` is the only join key back to our own identities.
REQUIRED_COLUMNS = ("value_2qb", "ecr_2qb", "fp_id", "player", "pos")


class NoCommitInWindow(RuntimeError):
    """No commit touched the values file within the window around the target date.

    Raised rather than returning the nearest commit at any distance: reaching further is how a
    snapshot silently stops being comparable to the series it joins.
    """


def snapshot_target(year: int) -> date:
    """The annual capture date for a season, following the existing files' convention."""
    return date(year, *SNAPSHOT_MONTH_DAY)


def select_snapshot_commit(
    commits: Iterable[dict[str, Any]],
    *,
    target: date,
    window_days: int = WINDOW_DAYS,
) -> dict[str, Any]:
    """Choose the commit whose snapshot represents ``target``.

    Prefers the closest commit ON OR BEFORE the target, and only falls back to a later one when
    nothing precedes it inside the window. The preference is the point: a commit taken after the
    target carries roster news the comparison exists to hold constant, so using one would leak
    information backwards into a point-in-time measurement.
    """
    in_window = [
        commit
        for commit in commits
        if abs((commit["committed"] - target).days) <= window_days
    ]
    if not in_window:
        raise NoCommitInWindow(
            f"no commit touching {SOURCE_PATH} within {window_days} days of {target.isoformat()}"
        )
    on_or_before = [c for c in in_window if c["committed"] <= target]
    if on_or_before:
        return max(on_or_before, key=lambda c: c["committed"])
    return min(in_window, key=lambda c: c["committed"])


def validate_snapshot_columns(columns: Sequence[str]) -> None:
    """Refuse a snapshot that cannot serve the comparison.

    Additive upstream drift is fine — the readers select named columns — but a MISSING
    load-bearing column means the file is not the same object as the four it would join, and
    writing it anyway would quietly corrupt the series.
    """
    present = set(columns)
    missing = [name for name in REQUIRED_COLUMNS if name not in present]
    if missing:
        raise ValueError(
            f"snapshot is missing required column(s) {', '.join(missing)} — refusing to write "
            f"a file that is not comparable to the existing series"
        )


def snapshot_filename(target: date) -> str:
    return f"values_{target.isoformat()}.csv"


def provenance_record(
    *,
    target: date,
    commit_sha: str,
    commit_date: date,
    sha256: str,
    fetched_at: str,
    scrape_date: Optional[str] = None,
) -> dict[str, Any]:
    """What has to be recorded for the file to be evidence rather than a CSV.

    ``commit_date`` is deliberately kept alongside ``target``: they differ by design (the
    window rule), and a reader comparing two snapshots needs to see how far each sits from its
    nominal date.
    """
    return {
        "source_url": SOURCE_URL,
        "source_license": SOURCE_LICENSE,
        "source_family": SOURCE_FAMILY,
        "source_path": SOURCE_PATH,
        "target_date": target.isoformat(),
        "commit_sha": commit_sha,
        "commit_date": commit_date.isoformat(),
        "days_from_target": (commit_date - target).days,
        "window_days": WINDOW_DAYS,
        "scrape_date": scrape_date,
        "sha256": sha256,
        "fetched_at": fetched_at,
        "access_method": "read-only git clone (no scraping)",
        "decision_supported": False,
    }
