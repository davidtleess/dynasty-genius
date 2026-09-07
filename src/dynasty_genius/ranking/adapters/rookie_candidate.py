"""Reader adapter for the DG-165 rookie candidate (research output) — DG-178.

The candidate file gives, per drafted rookie, ``p_qual_year{j}`` = P(qualifies in NFL season
j), j = 1..5, on the same bar-rank event as the DG-164 cells (QB37/RB45/WR71/TE21 by
regular-season PPR total). Nothing in it multiplies anything. This adapter maps its clock
(rookie season = NFL season 1 = the draft year) onto the contract's (h = j - 1) and builds

    ev_h = p_qual_year{h+1} x max(0, E[ppg | qualifies in season h+1] - R)

when — and only when — a conditional level exists: ``e_ppg_given_qual_year{j}`` carried in
the file (its ppg denominator note rides on every term), or one the caller names a source
for. Without either, every rookie comes back ``coverage="partial"`` with the probabilities
quoted in the reason: the probability half of the term is real, the level half is absent,
and an absent level is never filled in here.

Join key. The served artifact carries ``gsis_id=None`` for every 2026 rookie, so rows are
keyed by ``(position, draft_season, pick)``, unique for drafted players. Undrafted rookies
are not in the file and are a stated absence.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from src.dynasty_genius.ranking.contract import (
    HorizonTerm,
    ProducerRef,
    ReplacementRef,
    ServedReference,
    TargetSpec,
    TermSet,
    season_for_horizon,
)
from src.dynasty_genius.ranking.served_rows import ServedRow


@dataclass(frozen=True)
class RookieCandidateRow:
    gsis_id: str
    name: str
    position: str
    team: str
    draft_season: int
    pick: int
    round: Optional[int]
    age_at_draft: Optional[float]
    coverage_status: str
    p_qual_year: tuple[float, ...]  # index 0 = NFL season 1 = the draft year
    e_ppg_given_qual_year: Optional[tuple[float, ...]] = None  # same indexing; None if absent


def _as_mapping(value) -> dict:
    """The DG-165 manifest stores its label block as the repr of a dict. Read it as one."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _find_qualifying_definition(manifest: dict) -> str:
    """The event string, wherever the manifest keeps it (`definitions`, `labels`, or top
    level). Fail closed if it is nowhere: a probability with no stated event cannot be
    checked against anything."""
    containers = [_as_mapping(manifest.get("definitions")), _as_mapping(manifest.get("labels")), manifest]
    for container in containers:
        for key, value in container.items():
            if "qualif" in key.lower() and isinstance(value, str):
                return value
    raise ValueError("rookie candidate manifest does not define the qualifying event")


def _find_denominator_note(manifest: dict) -> Optional[str]:
    for container in (_as_mapping(manifest.get("units")), manifest):
        for key, value in container.items():
            if "denominator" in key.lower() and isinstance(value, str):
                return value
    return None


class RookieCandidate:
    def __init__(self, csv_path: Path, manifest_path: Path, csv_sha256: str, manifest_sha256: str,
                 model_version: str, rookie_season: int, qualifying_event: str,
                 rows: dict[tuple[str, int, int], RookieCandidateRow],
                 ppg_denominator_note: Optional[str] = None,
                 level_bias_by_season: Optional[dict[str, dict]] = None,
                 evaluation_sha256: Optional[str] = None) -> None:
        self.csv_path = csv_path
        self.manifest_path = manifest_path
        self.csv_sha256 = csv_sha256
        self.manifest_sha256 = manifest_sha256
        self.model_version = model_version
        self.rookie_season = rookie_season
        self.qualifying_event = qualifying_event
        self.ppg_denominator_note = ppg_denominator_note
        self.level_bias_by_season = level_bias_by_season or {}
        self.evaluation_sha256 = evaluation_sha256
        self._rows = rows

    @property
    def level_caveat(self) -> Optional[str]:
        """The level's measured out-of-time bias and how little it beats the position mean,
        as one sentence for every rookie term. None when no evaluation was read: an absent
        measurement is stated as absent, not filled in."""
        if not self.level_bias_by_season:
            return None
        biases = [(k, v.get("bias")) for k, v in sorted(self.level_bias_by_season.items(), key=lambda kv: int(kv[0]))
                  if v.get("bias") is not None]
        if not biases:
            return None
        vals = [b for _, b in biases]
        direction = "under-predicts" if max(vals) < 0 else ("over-predicts" if min(vals) > 0 else "is biased")
        by_season = ", ".join(f"season {k}: {b:+.2f}" for k, b in biases)
        gains = []
        for k, v in self.level_bias_by_season.items():
            r, r0 = v.get("rmse"), v.get("rmse_position_mean")
            if r and r0:
                gains.append((int(k), (r0 - r) / r0 * 100.0))
        gain_note = ""
        if gains:
            lo, hi = min(g for _, g in gains), max(g for _, g in gains)
            gain_note = (f"; its RMSE gain over the position-mean comparator runs from {lo:+.0f}% to {hi:+.0f}% "
                         "by season (negative = worse than the comparator)")
        return (f"level {direction} out of time by {min(abs(v) for v in vals):.1f}-{max(abs(v) for v in vals):.1f} ppg "
                f"(mean predicted minus actual, {by_season}){gain_note}")

    @property
    def seasons_covered(self) -> int:
        lengths = {len(r.p_qual_year) for r in self._rows.values()}
        if len(lengths) != 1:
            raise ValueError(f"rows cover different numbers of seasons: {sorted(lengths)}")
        return lengths.pop()

    @classmethod
    def load(cls, csv_path: Path | str, manifest_path: Path | str,
             evaluation_path: Optional[Path | str] = None) -> "RookieCandidate":
        csv_p, man_p = Path(csv_path), Path(manifest_path)
        csv_bytes, man_bytes = csv_p.read_bytes(), man_p.read_bytes()
        manifest = json.loads(man_bytes)
        level_bias: dict[str, dict] = {}
        evaluation_sha: Optional[str] = None
        if evaluation_path is not None:
            ev_bytes = Path(evaluation_path).read_bytes()
            evaluation_sha = hashlib.sha256(ev_bytes).hexdigest()
            for k, v in (json.loads(ev_bytes).get("level_by_year") or {}).items():
                level_bias[str(k)] = {key: v.get(key) for key in ("season", "n", "bias", "rmse", "rmse_position_mean")}
        model_version = str(manifest["model_version"])
        rookie_season = int((manifest.get("forecast_date") or {})["forecast_year"])
        qualifying_event = _find_qualifying_definition(manifest)
        denominator_note = _find_denominator_note(manifest)
        rows: dict[tuple[str, int, int], RookieCandidateRow] = {}
        with csv_p.open(newline="") as fh:
            for rec in csv.DictReader(fh):
                year_cols = sorted((k for k in rec if k.startswith("p_qual_year") and k[len("p_qual_year"):].isdigit()),
                                   key=lambda k: int(k[len("p_qual_year"):]))
                probs = tuple(float(rec[k]) for k in year_cols)
                for p in probs:
                    if not (math.isfinite(p) and 0.0 <= p <= 1.0):
                        raise ValueError(f"{rec.get('name')}: {p} is not a probability")
                level_cols = [f"e_ppg_given_qual_year{k[len('p_qual_year'):]}" for k in year_cols]
                levels = (tuple(float(rec[c]) for c in level_cols)
                          if all(c in rec and rec[c] not in ("", None) for c in level_cols) else None)
                if levels is not None and not all(math.isfinite(x) for x in levels):
                    raise ValueError(f"{rec.get('name')}: a level is not finite: {levels}")
                row = RookieCandidateRow(
                    gsis_id=rec.get("gsis_id") or "", name=rec["name"], position=rec["position"].upper(),
                    team=rec.get("team") or "", draft_season=int(rec["draft_season"]), pick=int(rec["pick"]),
                    round=int(rec["round"]) if rec.get("round") else None,
                    age_at_draft=float(rec["age_at_draft"]) if rec.get("age_at_draft") else None,
                    coverage_status=rec.get("coverage_status") or "", p_qual_year=probs,
                    e_ppg_given_qual_year=levels,
                )
                key = (row.position, row.draft_season, row.pick)
                if key in rows:
                    raise ValueError(f"duplicate rookie key {key}: the join is not unique")
                rows[key] = row
        return cls(csv_p, man_p, hashlib.sha256(csv_bytes).hexdigest(), hashlib.sha256(man_bytes).hexdigest(),
                   model_version, rookie_season, qualifying_event, rows, denominator_note,
                   level_bias, evaluation_sha)

    def get(self, position: str, draft_season: int, pick: int) -> Optional[RookieCandidateRow]:
        return self._rows.get((position.upper(), int(draft_season), int(pick)))


def build_rookie_term_set(row: ServedRow, replacement: ReplacementRef, candidate: RookieCandidate, *,
                          draft_pick: Optional[int], forecast_date: date,
                          level_ppg_by_h: Optional[Sequence[float]] = None,
                          level_source: str = "caller-supplied", horizons: int = 5,
                          draft_season: Optional[int] = None) -> TermSet:
    served = ServedReference(dynasty_value_score=row.dynasty_value_score,
                             dvs_engine=row.dvs_engine, captured_at=row.captured_at)
    producer = ProducerRef(name=candidate.model_version,
                           version=f"csv:{candidate.csv_sha256[:12]};manifest:{candidate.manifest_sha256[:12]}",
                           estimate_class="candidate")
    common = dict(player_id=row.player_id, position=row.position, forecast_date=forecast_date,
                  producer=producer, replacement_ref=replacement, full_name=row.full_name,
                  sleeper_id=row.sleeper_id, served=served)
    if forecast_date.year != candidate.rookie_season:
        raise ValueError(
            f"rookie candidate vintage {candidate.rookie_season} does not match the forecast date "
            f"{forecast_date}: the same prior is not a forecast for a later season. Refused rather "
            "than shifted forward; an elapsed-season update needs its own validated rule."
        )
    season = candidate.rookie_season if draft_season is None else draft_season
    cand = candidate.get(row.position, season, draft_pick) if draft_pick is not None else None
    if cand is None:
        return TermSet(terms=[], coverage="none", **common,
                       reason=f"not in the rookie candidate file {candidate.model_version} "
                              f"(key {row.position}, {season}, pick {draft_pick})")
    probs = ", ".join(f"{p:.3f}" for p in cand.p_qual_year)
    if level_ppg_by_h is None and cand.e_ppg_given_qual_year is not None:
        level_ppg_by_h = cand.e_ppg_given_qual_year
        level_source = f"from {candidate.model_version}"
        if candidate.ppg_denominator_note:
            level_source += f" (ppg denominator: {candidate.ppg_denominator_note})"
        if candidate.level_caveat:
            level_source += f"; {candidate.level_caveat}"
    if level_ppg_by_h is None:
        return TermSet(terms=[], coverage="partial", **common,
                       reason=f"rookie conditional production level E[ppg | qualifies in season j] not "
                              f"supplied by {candidate.model_version}; probabilities present "
                              f"p_qual_year1..{len(cand.p_qual_year)} = [{probs}]")
    # What this composition actually is: REG-scope, stat-row-game rates, the bar-rank
    # qualification event, one season per term. A research approximation of the annual
    # target (which needs the appearance event and season points), typed as such.
    spec = TargetSpec(scope="REG", scoring="PPR_nflverse_weekly", exposure="stat_row_games",
                      event="bar_rank_reg_total", clock="per_season", quantity="ppg_rate",
                      labels_through=forecast_date.year - 1)
    n = min(len(level_ppg_by_h), len(cand.p_qual_year), horizons + 1)
    terms = []
    for h in range(n):
        j = h + 1
        ev = cand.p_qual_year[h] * max(0.0, float(level_ppg_by_h[h]) - replacement.rate_ppg)
        terms.append(HorizonTerm(
            h=h, season=season_for_horizon(forecast_date, h), ev_above_replacement=ev,
            conditioning_event=(f"{candidate.model_version}: P(qualifies in NFL season {j}) x "
                                f"max(0, E[ppg | qualifies in NFL season {j}] - replacement); "
                                f"qualifying = {candidate.qualifying_event}; level {level_source}"),
            spec=spec,
        ))
    if len(terms) != horizons + 1:
        return TermSet(terms=terms, coverage="partial", **common,
                       reason=f"rookie candidate covers {len(cand.p_qual_year)} seasons and the level "
                              f"{len(level_ppg_by_h)}; the board sums {horizons + 1}")
    return TermSet(terms=terms, coverage="full", reason=None, **common)
