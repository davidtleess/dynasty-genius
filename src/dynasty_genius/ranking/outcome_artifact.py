"""DG-179's shared league-season outcome artifact, read as Codex implemented it
(`dg179_league_season_outcomes_v1`, 2026-09-06 evening). ONE global artifact is shared by both
producers; DG-178 reads it read-only, hashes its CSV and manifest, checks the schema, the
exactness claim (must be False), the window rule and the columns, and reads `coverage_status`
as a RESEARCH qualification — admitted game ids match the source and the exact unattributed-row
quarantine is disclosed — never as proof of perfect individual statistics. Labels outside the
admitted seasons are UNKNOWN, never zero.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from src.dynasty_genius.ranking.contract import TargetSpec

SCHEMA_VERSION = "dg179_league_season_outcomes_v1"
SCORING_PRESET = "nflverse_default_ppr_championship_window_v1"
EXPOSURE_DEFINITION = "unique stat_record weeks within the outcome window"
QUALIFIED = "qualified_research_game_complete_identified_rows"
CALENDAR_ONLY = "calendar_checked_game_coverage_unverified"
QUALIFICATION_NOTE = ("research qualification: admitted game ids match the source and the exact unattributed-row "
                      "quarantine is disclosed; not proof of perfect individual stats, and not David's exact league scoring")
COLUMNS = ["player_id", "season", "points", "games", "appeared"]


@dataclass(frozen=True)
class OutcomeArtifact:
    manifest_path: str
    csv_path: str
    manifest_sha256: str
    csv_sha256: str
    rows: int
    schema_version: str
    scoring_preset: str
    league_scoring_exact: bool
    exact_league_scoring_gaps: dict[str, Any]
    exposure_definition: str
    admitted_seasons: list[int]
    last_complete_season: int
    coverage_status: str
    research_qualified: bool
    qualification_note: str
    source_identity_sha256: Optional[str]
    scoring_identity: str
    window_identity: str
    target_identity: str
    source_validation_limitations: Optional[str]
    zero_definition: Optional[str]
    _outcomes: dict[tuple[str, int], dict[str, Any]] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, manifest_path: Path | str, csv_path: Path | str) -> "OutcomeArtifact":
        man_p, csv_p = Path(manifest_path), Path(csv_path)
        man_bytes, csv_bytes = man_p.read_bytes(), csv_p.read_bytes()
        m = json.loads(man_bytes)
        if m.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"outcome artifact schema {m.get('schema_version')!r} is not {SCHEMA_VERSION}")
        declared = ((m.get("outputs") or {}).get("outcomes.csv") or {})
        csv_sha = hashlib.sha256(csv_bytes).hexdigest()
        if str(declared.get("sha256") or "").lower() != csv_sha or int(declared.get("bytes") or -1) != len(csv_bytes):
            raise ValueError("outcomes.csv bytes do not match the sha256/bytes the manifest declares under outputs")
        if m.get("league_scoring_exact") is not False:
            raise ValueError("league_scoring_exact must be False: no exact-league claim is supported by this artifact")
        if m.get("scoring_preset") != SCORING_PRESET:
            raise ValueError(f"scoring_preset {m.get('scoring_preset')!r} is not {SCORING_PRESET}")
        if m.get("exposure_definition") != EXPOSURE_DEFINITION:
            raise ValueError(f"exposure_definition {m.get('exposure_definition')!r} is not {EXPOSURE_DEFINITION!r}")
        windows = m.get("season_windows") or {}
        seasons = sorted(int(y) for y in windows)
        for y in seasons:
            w = windows[str(y)]
            final = 18 if y >= 2021 else 17
            if (int(w.get("excluded_final_reg_week", -1)) != final or list(w.get("included_reg_weeks") or []) != list(range(1, final))
                    or float(w.get("weekly_weight", 0)) != 1.0):
                raise ValueError(f"season window for {y} does not follow the rule (weeks 1-{final - 1}, final week {final} "
                                 f"excluded, equal weekly weighting): {w}")
        with csv_p.open(newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != COLUMNS:
                raise ValueError(f"outcomes.csv columns {reader.fieldnames} are not {COLUMNS}")
            outcomes: dict[tuple[str, int], dict[str, Any]] = {}
            for rec in reader:
                key = (str(rec["player_id"]), int(rec["season"]))
                if key in outcomes:
                    raise ValueError(f"duplicate player-season {key} in outcomes.csv")
                outcomes[key] = {"points": float(rec["points"]), "games": int(rec["games"]),
                                 "appeared": str(rec["appeared"]).strip().lower() == "true"}
        if int(m.get("outcome_rows") or -1) != len(outcomes):
            raise ValueError(f"outcome_rows {m.get('outcome_rows')} does not equal the {len(outcomes)} rows read")
        coverage = str(m.get("coverage_status") or "")
        if coverage == QUALIFIED:
            qualified, note = True, QUALIFICATION_NOTE
        elif coverage == CALENDAR_ONLY:
            qualified, note = False, f"not research-qualified: {coverage} (calendar checked; game coverage unverified)"
        else:
            qualified, note = False, f"not research-qualified: unknown coverage status {coverage!r}"
        return cls(
            manifest_path=str(man_p), csv_path=str(csv_p), manifest_sha256=hashlib.sha256(man_bytes).hexdigest(),
            csv_sha256=csv_sha, rows=len(outcomes), schema_version=SCHEMA_VERSION, scoring_preset=SCORING_PRESET,
            league_scoring_exact=False, exact_league_scoring_gaps=dict(m.get("exact_league_scoring_gaps") or {}),
            exposure_definition=EXPOSURE_DEFINITION, admitted_seasons=seasons,
            last_complete_season=int(m.get("last_complete_season")), coverage_status=coverage,
            research_qualified=qualified, qualification_note=note,
            source_identity_sha256=m.get("source_identity_sha256"), scoring_identity=str(m.get("scoring_identity")),
            window_identity=str(m.get("window_identity")), target_identity=str(m.get("target_identity")),
            source_validation_limitations=m.get("source_validation_limitations"), zero_definition=m.get("zero_definition"),
            _outcomes=outcomes,
        )

    def outcome(self, player_id: str, season: int) -> Optional[dict[str, Any]]:
        """The labelled outcome, or None when the season is outside the admitted years or the
        player-season is not in the artifact: UNKNOWN, never zero."""
        if season not in self.admitted_seasons:
            return None
        return self._outcomes.get((str(player_id), int(season)))

    def target_spec(self) -> TargetSpec:
        return TargetSpec(scope="REG", scoring="PPR_nflverse_default", window="championship_week17",
                          exposure="stat_record_weeks_in_window", event="appearance", clock="per_season",
                          quantity="season_points", labels_through=self.last_complete_season)

    def identity(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "scoring_preset": self.scoring_preset,
                "target_identity": self.target_identity, "scoring_identity": self.scoring_identity,
                "window_identity": self.window_identity, "source_identity_sha256": self.source_identity_sha256,
                "outcomes_csv_sha256": self.csv_sha256, "manifest_sha256": self.manifest_sha256,
                "coverage_status": self.coverage_status, "research_qualified": self.research_qualified,
                "qualification_note": self.qualification_note, "last_complete_season": self.last_complete_season,
                "admitted_seasons": self.admitted_seasons, "league_scoring_exact": False,
                "exact_league_scoring_gaps": self.exact_league_scoring_gaps,
                "source_validation_limitations": self.source_validation_limitations}


def producer_binding_matches(binding: Optional[Mapping[str, Any]], artifact: OutcomeArtifact) -> list[str]:
    """Which fields of a producer's outcome binding disagree with the shared artifact; empty
    when they agree on everything named. No binding at all is a mismatch, not agreement."""
    if not binding:
        return ["no outcome binding"]
    expected = {"target_identity": artifact.target_identity, "outcomes_csv_sha256": artifact.csv_sha256,
                "manifest_sha256": artifact.manifest_sha256, "scoring_preset": artifact.scoring_preset,
                "coverage_status": artifact.coverage_status, "last_complete_season": artifact.last_complete_season}
    bad = []
    for key, want in expected.items():
        got = binding.get(key)
        if got is None or str(got).lower() != str(want).lower():
            bad.append(key)
    return bad


CORE_BINDING_FIELDS = ("target_identity", "outcomes_csv_sha256", "manifest_sha256", "scoring_preset",
                       "coverage_status", "last_complete_season")


def bindings_disagree(a: Optional[Mapping[str, Any]], b: Optional[Mapping[str, Any]]) -> list[str]:
    """Core binding fields on which two producers' bindings differ or one is missing; empty
    when both name the same artifact. Extra identity fields one side states do not matter."""
    if not a or not b:
        return ["no outcome binding"]
    bad = []
    for key in CORE_BINDING_FIELDS:
        va, vb = a.get(key), b.get(key)
        if va is None or vb is None or str(va).lower() != str(vb).lower():
            bad.append(key)
    return bad
