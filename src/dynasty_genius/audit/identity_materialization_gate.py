"""Identity gates before training feature materialization."""
from __future__ import annotations

import dataclasses

COLLEGE_SOURCE_NAMES = {
    "pff",
    "college_pff",
    "cfbd",
    "college_football_data",
    "cfbfastR",
    "playerprofiler_college",
    "college",
}

RESOLVED_STATUSES = {
    "RESOLVED_DETERMINISTIC",
    "RESOLVED_MANUAL",
}


class UnresolvedIdentityGateError(ValueError):
    """Raised when unresolved PFF/college rows would enter feature materialization."""


@dataclasses.dataclass(frozen=True)
class IdentityMaterializationRow:
    row_id: str
    source: str
    player_id: str | None
    identity_status: str

    @property
    def is_college_feature_source(self) -> bool:
        return self.source in COLLEGE_SOURCE_NAMES

    @property
    def is_training_eligible(self) -> bool:
        return bool(self.player_id) and self.identity_status in RESOLVED_STATUSES


def assert_identity_materialization_allowed(rows: list[IdentityMaterializationRow]) -> None:
    """Fail closed if unresolved PFF/college rows would reach training materialization."""
    violations = [
        row
        for row in rows
        if row.is_college_feature_source and not row.is_training_eligible
    ]
    if not violations:
        return

    detail = "; ".join(
        f"{row.row_id} source={row.source} status={row.identity_status} player_id={row.player_id}"
        for row in violations
    )
    raise UnresolvedIdentityGateError(
        "unresolved PFF/college identity rows cannot enter training materialization: "
        f"{detail}"
    )
