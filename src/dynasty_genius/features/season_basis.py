"""DG-154 — the season basis cannot change unattended.

``run_daily_chain.py`` invokes ``run_feature_refresh.py`` with no ``--season-end``, so the
refresh derives ``season_end`` from the live feed's newest ``player_stats`` season and uses it
as ``inference_season``. The day nflverse publishes the first 2026 row — roughly 2026-09-15 —
that flips 2025 → 2026 by itself. ``feature_assembly`` then keeps
``(feature_season < inference_season - 1) | (feature_season == inference_season)``, which drops
the COMPLETED 2025 rows in favour of a 2026 partition that is empty until players reach the
four-game threshold. When the board returns, ``ppg_t`` no longer means "a full season"; it
means "the four games he has played so far" — on the feature with the largest coefficient at
every position.

**This module decides nothing.** Whether the board should stay on the completed season, advance
at a threshold, or carry both is David's ruling, and pinning it here would be worse than the
default because then we would own it. All this does is make the change require a decision
instead of a feed publication. Today, with the feed's newest season equal to the season already
published, it is a no-op.

The release valve is a declaration with an author and a date, the same governance shape as
``realized_outcome_frozen_predictions.json``: a rule with no author is not a decision, it is a
value someone typed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

# The refusal token. Named specifically, and NOT reusing the vocabulary of a feed failure:
# during the fail-closed window this exits non-zero every morning for a CORRECT reason, and an
# operator has to be able to tell that apart from a broken feed at a glance (DG-136's lesson —
# a refusal that reads like a break gets triaged as a break, or worse, ignored).
SEASON_BASIS_CHANGE_BLOCKED = "season_basis_change_blocked"

RUNTIME_MARKER_NAME = "engine_b_features_runtime.ready.json"
RUNTIME_CSV_NAME = "engine_b_features_runtime.csv"

# Where a ruling would be recorded. Absent by design until David makes one — its absence is
# what keeps the guard closed, so nothing here creates it.
SEASON_BASIS_DECLARATION = (
    Path(__file__).resolve().parents[3] / "app" / "config" / "feature_season_basis.json"
)


class SeasonBasisRefusal(RuntimeError):
    """The feed's season differs from the published one and nothing authorises the change.

    Raised rather than returned: an unauthorised rebase must stop the publish, and a return
    value can be dropped by a caller that never checked it.
    """

    def __init__(self, reason: str, *, derived: int, published: Optional[int], detail: str = ""):
        self.reason = reason
        self.derived = derived
        self.published = published
        self.detail = detail
        message = (
            f"{reason}: the feed's newest season is {derived} but the board publishes "
            f"{published}. Changing the basis rebases every ranked player from a complete "
            f"season onto a partial one; it needs a declaration, not a feed publication."
        )
        super().__init__(f"{message} {detail}".strip())


def published_inference_season(runtime_dir: Path | str) -> Optional[int]:
    """The season the LIVE board is built on, read from the runtime ready-marker.

    ``None`` when there is no readable marker: a first-ever publish has no basis to protect,
    and a corrupt marker must not be read as "season zero" and used to block or authorise
    anything.
    """
    marker = Path(runtime_dir) / RUNTIME_MARKER_NAME
    try:
        payload = json.loads(marker.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    season = payload.get("inference_season")
    try:
        return int(season)
    except (TypeError, ValueError):
        return None


def published_basis(runtime_dir: Path | str) -> dict[str, Any]:
    """What the live runtime says its basis is, AND whether a runtime exists at all.

    The two are different questions and conflating them fails OPEN: a runtime CSV can be
    present while its marker is missing or corrupt, and treating that as "nothing to
    protect" would authorise exactly the rebase this guard exists to stop. Only a directory
    with no published runtime is a genuine first publish.
    """
    directory = Path(runtime_dir)
    return {
        "season": published_inference_season(directory),
        "runtime_present": (directory / RUNTIME_CSV_NAME).exists(),
    }


def load_declaration(path: Path | str | None = None) -> Optional[dict[str, Any]]:
    """The governed authorisation, or None when there is none. Absence is the normal state."""
    target = Path(path) if path is not None else SEASON_BASIS_DECLARATION
    try:
        payload = json.loads(target.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def authorise_inference_season(
    *,
    derived: int,
    published: Optional[int],
    declaration: Optional[dict[str, Any]],
    runtime_present: bool = False,
) -> int:
    """Return the season the refresh may publish on, or refuse.

    Proceeds silently when the basis is unchanged (today's case) or when nothing is published
    yet. Otherwise a declaration must name EXACTLY the season the feed has, and carry its own
    author and date.
    """
    derived = int(derived)
    if published is None and runtime_present:
        # A runtime IS published but will not say what it is built on. Proceeding here would
        # authorise the rebase on the strength of a file we could not read.
        raise SeasonBasisRefusal(
            SEASON_BASIS_CHANGE_BLOCKED,
            derived=derived,
            published=None,
            detail=(
                "A runtime feature table is published but its ready-marker is missing or "
                "unreadable, so the season it was built on cannot be established."
            ),
        )
    if published is None or int(published) == derived:
        return derived

    if not isinstance(declaration, dict):
        raise SeasonBasisRefusal(
            SEASON_BASIS_CHANGE_BLOCKED,
            derived=derived,
            published=published,
            detail="No declaration exists. This is David's ruling to make.",
        )

    for field in ("declared_inference_season", "declared_by", "declared_at"):
        if not declaration.get(field):
            raise SeasonBasisRefusal(
                SEASON_BASIS_CHANGE_BLOCKED,
                derived=derived,
                published=published,
                detail=f"Declaration is missing '{field}'.",
            )

    try:
        declared = int(declaration["declared_inference_season"])
    except (TypeError, ValueError):
        raise SeasonBasisRefusal(
            SEASON_BASIS_CHANGE_BLOCKED,
            derived=derived,
            published=published,
            detail="declared_inference_season is not a season number.",
        ) from None

    if declared != derived:
        # A declaration names WHICH change is allowed; it never invents data the feed does not
        # have, and last rollover's declaration must not wave through the next one.
        raise SeasonBasisRefusal(
            SEASON_BASIS_CHANGE_BLOCKED,
            derived=derived,
            published=published,
            detail=(
                f"The declaration authorises {declared}, which is not the season the feed "
                f"has ({derived})."
            ),
        )
    return derived
