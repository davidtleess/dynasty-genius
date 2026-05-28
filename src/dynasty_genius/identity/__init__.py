from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Optional, Union

from src.dynasty_genius.models.player_identity import PlayerIdentity

SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b\.?", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

GIVEN_NAME_ALIASES = {
    "josh": "joshua",
    "mike": "michael",
    "mikey": "michael",
    "chris": "christopher",
    "christian": "christian",
    "matt": "matthew",
    "tom": "thomas",
    "tj": "teejay",
    "t.j": "teejay",
    "t.j.": "teejay",
}


def normalize_player_name(name: str) -> str:
    """Normalize display names for deterministic canonical ID generation."""
    text = name.lower().strip()
    text = SUFFIX_RE.sub("", text)
    text = text.replace("'", "")
    text = text.replace(".", "")
    parts = [part for part in NON_ALNUM_RE.split(text) if part]
    if not parts:
        raise ValueError("player name must contain at least one alphanumeric token")

    parts[0] = GIVEN_NAME_ALIASES.get(parts[0], parts[0])
    return "_".join(parts)

def generate_dg_id(name: str, position: str, birth_year: Optional[int] = None) -> str:
    """
    Generates a readable, canonical ID for a player.
    Format: [first_last]_[pos]_[birth_year]
    Example: josh_allen_qb_1996
    """
    pos = position.lower().strip()
    if not pos:
        raise ValueError("position is required for dg_id generation")

    clean_name = normalize_player_name(name)
    if birth_year:
        return f"{clean_name}_{pos}_{birth_year}"
    return f"{clean_name}_{pos}"


def assign_collision_suffixes(base_ids: Iterable[str]) -> list[str]:
    """
    Append deterministic _2/_3 suffixes when multiple rows share the same base dg_id.

    Input order must already be deterministic, usually by source priority and source-native ID.
    The first row keeps the base ID so existing reviewed mappings remain stable.
    """
    counts: defaultdict[str, int] = defaultdict(int)
    resolved_ids: list[str] = []
    for base_id in base_ids:
        counts[base_id] += 1
        if counts[base_id] == 1:
            resolved_ids.append(base_id)
        else:
            resolved_ids.append(f"{base_id}_{counts[base_id]}")
    return resolved_ids

# ── Fuzzy match engine ────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.95
TEAM_CONTEXT_THRESHOLD = 0.80
TEAM_JERSEY_CONTEXT_THRESHOLD = 0.60


def compute_name_confidence(name_a: str, name_b: str) -> float:
    """Return a confidence score [0.0, 1.0] that two player names refer to the same player.

    Applies normalize_player_name to both sides, then uses a token-sort ratio so
    that source name-order variation (e.g. 'Amon Ra St Brown' vs 'Amon-Ra St. Brown')
    scores correctly. Scores below CONFIDENCE_THRESHOLD should be flagged CONFLICT.
    """
    norm_a = normalize_player_name(name_a)
    norm_b = normalize_player_name(name_b)
    if norm_a == norm_b:
        return 1.0
    sorted_a = "_".join(sorted(norm_a.split("_")))
    sorted_b = "_".join(sorted(norm_b.split("_")))
    return SequenceMatcher(None, sorted_a, sorted_b).ratio()


@dataclass
class NameMatchResult:
    candidate_dg_id: str
    candidate_name: str
    confidence: float
    verification_status: str  # VERIFIED | CONFLICT | PENDING
    verification_basis: str


def _normalize_team(team: Optional[str]) -> Optional[str]:
    if not team:
        return None
    normalized = team.strip().upper()
    return normalized or None


def _normalize_jersey_number(jersey_number: Optional[Union[str, int]]) -> Optional[str]:
    if jersey_number is None:
        return None
    normalized = str(jersey_number).strip().lstrip("0")
    return normalized or "0"


class IdentityResolver:
    """Resolves source player IDs and names to canonical dg_ids.

    Operates over an in-memory list of PlayerIdentity records.
    In production, this will read from silver.player_identity via Spark.
    """

    def __init__(self, identities: list[PlayerIdentity] | None = None):
        self._identities: list[PlayerIdentity] = identities or []

    def resolve_by_name(
        self,
        name: str,
        position: str,
        team: Optional[str] = None,
        jersey_number: Optional[Union[str, int]] = None,
    ) -> NameMatchResult | None:
        """Fuzzy-match a source name + position to the best canonical dg_id.

        Returns None if no candidates exist for the position.
        Name-only matches require CONFIDENCE_THRESHOLD (0.95). Lower-confidence
        matches can verify only when team and, for weaker matches, jersey number
        agree with a unique same-position candidate.
        """
        source_team = _normalize_team(team)
        source_jersey = _normalize_jersey_number(jersey_number)
        scored: list[tuple[PlayerIdentity, float]] = []

        for identity in self._identities:
            if identity.position.upper() != position.upper():
                continue
            conf = compute_name_confidence(name, identity.full_name)
            scored.append((identity, conf))

        if not scored:
            return None

        scored.sort(key=lambda item: item[1], reverse=True)
        best_identity, best_conf = scored[0]
        status = "VERIFIED" if best_conf >= CONFIDENCE_THRESHOLD else "CONFLICT"
        basis = "name"

        if status == "CONFLICT" and source_team:
            team_matches = [
                (identity, conf)
                for identity, conf in scored
                if _normalize_team(identity.nfl_team) == source_team
            ]
            if len(team_matches) == 1:
                team_identity, team_conf = team_matches[0]
                team_jersey = _normalize_jersey_number(team_identity.jersey_number)
                if source_jersey and team_jersey == source_jersey and team_conf >= TEAM_JERSEY_CONTEXT_THRESHOLD:
                    best_identity, best_conf = team_identity, team_conf
                    status = "VERIFIED"
                    basis = "team_jersey"
                elif team_conf >= TEAM_CONTEXT_THRESHOLD:
                    best_identity, best_conf = team_identity, team_conf
                    status = "VERIFIED"
                    basis = "team"
                else:
                    best_identity, best_conf = team_identity, team_conf
                    basis = "team_needs_jersey"

        return NameMatchResult(
            candidate_dg_id=best_identity.dg_id,
            candidate_name=best_identity.full_name,
            confidence=round(best_conf, 4),
            verification_status=status,
            verification_basis=basis,
        )

    def resolve_sleeper_id(self, sleeper_id: str) -> Optional[str]:
        """Exact lookup: Sleeper player_id → dg_id."""
        for identity in self._identities:
            if identity.sleeper_id == sleeper_id:
                return identity.dg_id
        return None

    def resolve_pff_id(self, pff_id: str) -> Optional[str]:
        """Exact lookup: PFF player_id → dg_id."""
        for identity in self._identities:
            if identity.pff_id == pff_id:
                return identity.dg_id
        return None


# ── Local reconciliation demo ─────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from pathlib import Path

    mock_path = Path(__file__).resolve().parents[2] / "resources" / "mock_playerprofiler_identity.json"
    raw = json.loads(mock_path.read_text())

    identities = [
        PlayerIdentity(
            dg_id=generate_dg_id(p["full_name"], p["position"], p.get("birth_year")),
            full_name=p["full_name"],
            position=p["position"],
            birth_date=p.get("birth_date"),
            nfl_team=p.get("nfl_team"),
            jersey_number=p.get("jersey_number"),
            sleeper_id=p.get("sleeper_id"),
            pff_id=p.get("pff_id"),
            pfr_id=p.get("pfr_id"),
            playerprofiler_id=p.get("playerprofiler_id"),
        )
        for p in raw["players"]
    ]

    resolver = IdentityResolver(identities)

    # Cross-source name variants that test the confidence engine
    test_cases = [
        ("Christian McCaffrey", "RB", None, None),   # exact
        ("Amon Ra St Brown", "WR", None, None),      # punctuation stripped by PFF
        ("Luther Burden", "WR", None, None),         # missing "III" suffix
        ("Anthony Richardson", "QB", None, None),    # exact
        ("Tony Richardson", "QB", "IND", "5"),      # team+jersey resolves weaker alias
        ("Travis Kelce", "TE", None, None),          # exact
        ("C. McCaffrey", "RB", "SF", None),          # team only is not enough
        ("Puka Nacua", "WR", None, None),            # exact
    ]

    print(f"\n{'Source name':<28} {'Pos':<4} {'Candidate':<28} {'Conf':>6}  Status    Basis")
    print("-" * 82)
    for source_name, pos, team, number in test_cases:
        result = resolver.resolve_by_name(source_name, pos, team=team, jersey_number=number)
        if result:
            print(
                f"{source_name:<28} {pos:<4} {result.candidate_name:<28} "
                f"{result.confidence:>6.3f}  {result.verification_status:<8}  {result.verification_basis}"
            )
        else:
            print(f"{source_name:<28} {pos:<4} {'NO MATCH':<28} {'N/A':>6}  UNRESOLVED")
