"""NEW-ONLY consumer for the root-accepted DG-165 cold-start sidecar (2026-09-07).

A starting estimate for a drafted player with no rookie-season regular-season record: year 1 is
the cold-start candidate (draft-capital hurdle) where the producer's paired evaluation selected
it, later years are the position-cell historical baseline, and a horizon the producer calls
unsupported stays MISSING (it never enters a partial future total). The consumer verifies the
exact accepted bytes (manifest and estimates hashes root named), the schema, the same outcome
artifact and target as the accepted report, the requested path (origin year, season labels),
every value (probability bounds, finiteness, the hurdle identity), the per-year class against
the producer's own selection, and the identity against the SAME captured census (Sleeper id,
verified NFL gsis, position, unowned, default pool). It is new-only: a player who already has a
forecast — one of the accepted 825, a recovered row, any other producer — is refused, never
overwritten. No impact number is fabricated for a starting estimate.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from src.dynasty_genius.ranking.available_catalog import (
    DEFAULT_CLASSES,
    SeasonForecast,
    _seasons_from_row,
)

SCHEMA_VERSION = "dg165_cold_start_candidate_v1"
ALLOWED_CLASSES = ("cold_start_candidate", "baseline_research_candidate", "unsupported")
PRODUCER_PREFIX = "DG-165 cold-start research candidate (starting estimate)"
JOIN_BASIS = "cold_start_census_nfl_gsis"
VALUE_COLS = ("p_appear_year{j}", "e_points_year{j}", "e_games_year{j}", "e_points_year{j}_given_appear", "e_games_year{j}_given_appear")


@dataclass(frozen=True)
class StartingEstimate:
    sleeper_id: str
    gsis: str
    name: str
    position: str
    route: str
    draft_status: str
    seasons: tuple[SeasonForecast, ...]
    classes: dict[int, str]
    unsupported_years: tuple[int, ...]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_year(text: Any) -> Optional[int]:
    """An exact integral four-digit year; '2026.5' or '2027.0' is not one (never truncated)."""
    t = str(text if text is not None else "").strip()
    return int(t) if re.fullmatch(r"(19|20)\d{2}", t) else None


@dataclass
class ColdStartSidecar:
    run_dir: Path
    manifest: dict[str, Any]
    evaluation: dict[str, Any]
    rows: list[dict[str, str]]
    manifest_sha256: str
    estimates_sha256: str

    @classmethod
    def load(cls, run_dir: Path | str, *, manifest_sha256: str, estimates_sha256: str) -> "ColdStartSidecar":
        d = Path(run_dir)
        if "latest" in d.as_posix().lower():
            raise ValueError(f"{d}: a mutable 'latest' path is not an accepted sidecar; bind the immutable run root named")
        manifest_bytes = (d / "manifest.json").read_bytes()
        if _sha(manifest_bytes) != str(manifest_sha256).lower():
            raise ValueError("the sidecar manifest bytes are not the manifest root accepted (manifest_sha256 differs)")
        manifest = json.loads(manifest_bytes)
        est_bytes = (d / "cold_start_estimates.csv").read_bytes()
        if _sha(est_bytes) != str(estimates_sha256).lower():
            raise ValueError("the sidecar estimates bytes are not the estimates root accepted (estimates_sha256 differs)")
        recorded = str((manifest.get("outputs_sha256") or {}).get("cold_start_estimates.csv") or "").lower()
        if recorded != _sha(est_bytes):
            raise ValueError("the sidecar estimates bytes differ from the manifest's own outputs_sha256 record")
        if str(manifest.get("schema_version")) != SCHEMA_VERSION:
            raise ValueError(f"sidecar schema_version {manifest.get('schema_version')!r} is not the consumable {SCHEMA_VERSION!r}")
        ev_path = d / "evaluation.json"
        ev_bytes = ev_path.read_bytes()
        rec_ev = str((manifest.get("outputs_sha256") or {}).get("evaluation.json") or "").lower()
        if rec_ev and rec_ev != _sha(ev_bytes):
            raise ValueError("the sidecar evaluation.json bytes differ from the manifest's outputs_sha256 record")
        evaluation = json.loads(ev_bytes)
        rows = list(csv.DictReader(io.StringIO(est_bytes.decode("utf-8"))))
        seen: set[str] = set()
        for r in rows:
            sid = str(r.get("sleeper_id") or "").strip()
            if not sid:
                raise ValueError("a sidecar row has no sleeper_id")
            if sid in seen:
                raise ValueError(f"duplicate sleeper_id {sid} in the sidecar; refusing to let one row overwrite another")
            seen.add(sid)
        return cls(run_dir=d, manifest=manifest, evaluation=evaluation, rows=rows,
                   manifest_sha256=_sha(manifest_bytes), estimates_sha256=_sha(est_bytes))

    @property
    def schema_version(self) -> str:
        return str(self.manifest.get("schema_version"))

    @property
    def producer(self) -> str:
        return f"{PRODUCER_PREFIX}:{self.schema_version}"

    @property
    def estimates_path(self) -> Path:
        return self.run_dir / "cold_start_estimates.csv"

    def source(self) -> dict[str, Any]:
        inputs = self.manifest.get("inputs") or {}
        return {"run_dir": str(self.run_dir), "manifest_sha256": self.manifest_sha256, "estimates_sha256": self.estimates_sha256,
                "schema_version": self.schema_version, "producer": self.producer, "ticket": self.manifest.get("ticket"),
                "coverage_run": (inputs.get("coverage_run") or {}),
                "partition": self.manifest.get("partition") or inputs.get("partition"),
                "git_sha": self.manifest.get("git_sha")}

    def evidence(self) -> dict[str, Any]:
        """The producer's own out-of-time evidence, carried for the Why: per-horizon arms (n, RMSE,
        Brier, bias) and the selection; never recomputed here, never a per-player certainty."""
        final = self.evaluation.get("final_origin_2026") or {}
        horizons = {}
        for h, block in (self.evaluation.get("horizons") or {}).items():
            arms = (block or {}).get("arms") or {}
            horizons[str(h)] = {arm: {k: v for k, v in (arms.get(arm) or {}).items() if k in ("n", "rmse_points", "brier", "mae_points", "bias_points", "appear_rate")}
                                for arm in ("b1", "candidate") if arms.get(arm)}
        return {"selected_per_horizon": final.get("selected_per_horizon") or {}, "horizons": horizons,
                "caveats": self.evaluation.get("caveats") or self.manifest.get("caveats") or {},
                "selection_rule": self.evaluation.get("selection_rule") or self.manifest.get("selection_rule"),
                "meaning": ("retrospective policy selection on the producer's historical population; not independent confirmation, "
                            "not a per-player certainty, not a breakout probability; a baseline year means the candidate was not "
                            "clearly better there")}

    def bind(self, *, report: Mapping[str, Any], years: tuple[int, ...], census: Mapping[str, Mapping[str, Any]],
             owned: Mapping[str, int], forecast_ids: set[str], forecast_gsis: set[str]) -> list[StartingEstimate]:
        oa = report.get("outcome_artifact") or {}
        want_art = str(oa.get("outcomes_csv_sha256") or "").lower()
        want_target = str(oa.get("target_identity") or "").lower()
        bound_oa = ((self.manifest.get("inputs") or {}).get("outcome_artifact") or {})
        if not want_art or str(bound_oa.get("sha256") or "").lower() != want_art:
            raise ValueError("the sidecar binds a different outcome artifact than the accepted report (outcomes_csv_sha256 differs)")
        if not want_target or str(bound_oa.get("target_identity") or "").lower() != want_target:
            raise ValueError("the sidecar binds a different target identity than the accepted report")
        selected = {str(k): str(v) for k, v in ((self.evaluation.get("final_origin_2026") or {}).get("selected_per_horizon") or {}).items()}
        if not selected:
            raise ValueError("the sidecar evaluation records no selected_per_horizon; the per-year class cannot be verified")
        bound = self.manifest.get("games_bound_declared")
        if not (isinstance(bound, (list, tuple)) and len(bound) == 2):
            raise ValueError("the sidecar manifest declares no games_bound_declared; conditional games cannot be checked")
        games_lo, games_hi = float(bound[0]), float(bound[1])
        year1 = years[0]
        out: list[StartingEstimate] = []
        for r in self.rows:
            sid = str(r.get("sleeper_id") or "").strip()
            gsis = str(r.get("gsis_id") or "").strip()
            name = str(r.get("name") or "")
            who = f"{name} (Sleeper {sid})"
            if _exact_year(r.get("origin_year")) != year1:
                raise ValueError(f"{who}: origin_year {r.get('origin_year')!r} is not exactly the forecast year {year1}; refusing to relabel or truncate")
            binding = {}
            try:
                binding = json.loads(r.get("source_binding") or "{}")
            except ValueError as exc:
                raise ValueError(f"{who}: source_binding is not readable JSON") from exc
            if str(binding.get("artifact_sha256") or "").lower() not in ("", want_art):
                raise ValueError(f"{who}: the row's source_binding names a different outcome artifact")
            if binding.get("origin_year") not in (None, year1):
                raise ValueError(f"{who}: the row's source_binding origin_year is not {year1}")
            classes: dict[int, str] = {}
            unsupported: list[int] = []
            for j, year in enumerate(years, start=1):
                label = str(r.get(f"season_year{j}") or "").strip()
                if _exact_year(label) != year:
                    raise ValueError(f"{who}: season_year{j} is {label!r}, not exactly the requested {year}; refusing to relabel or truncate")
                klass = str(r.get(f"estimate_class_year{j}") or "").strip()
                if klass not in ALLOWED_CLASSES:
                    raise ValueError(f"{who}: estimate_class_year{j} {klass!r} is not one of {ALLOWED_CLASSES}")
                if selected.get(str(j)) != klass:
                    raise ValueError(f"{who}: estimate_class_year{j} {klass!r} is not the class the producer's evaluation selected "
                                     f"for horizon {j} ({selected.get(str(j))!r})")
                values_present = [c.format(j=j) for c in VALUE_COLS if str(r.get(c.format(j=j)) or "").strip() != ""]
                if klass == "unsupported":
                    if values_present:
                        raise ValueError(f"{who}: horizon {j} is unsupported yet carries values {values_present}; incoherent")
                    unsupported.append(year)
                else:
                    # a supported year carries all five terms, the accepted producers' contract
                    blanks = [c.format(j=j) for c in VALUE_COLS if str(r.get(c.format(j=j)) or "").strip() == ""]
                    if blanks:
                        raise ValueError(f"{who}: horizon {j} claims {klass} but its path is incomplete (blank {', '.join(blanks)})")
                    g = float(r[f"e_games_year{j}"])
                    gc = float(r[f"e_games_year{j}_given_appear"])
                    if not g >= 0:
                        raise ValueError(f"{who}: e_games_year{j} = {g} is negative; expected games cannot be below zero")
                    if not games_lo <= gc <= games_hi:
                        raise ValueError(f"{who}: e_games_year{j}_given_appear = {gc} is outside the declared games bound [{games_lo}, {games_hi}]")
                classes[year] = klass
            seasons = _seasons_from_row(r, years, f"{who} (starting estimate)")
            # identity against the SAME captured census: member, unowned, default pool, verified gsis, position
            c = census.get(sid)
            if c is None:
                raise ValueError(f"{who}: not a member of the bound census; refusing to invent availability")
            if sid in owned or str(c.get("league_owned") or "").lower() == "true":
                raise ValueError(f"{who}: owned in the league snapshot; a starting estimate is never attached to an owned player here")
            census_gsis = str(c.get("nfl_gsis_id") or "").strip()
            if not gsis or census_gsis != gsis:
                raise ValueError(f"{who}: verified identity mismatch — sidecar gsis {gsis!r} vs the census's verified NFL gsis {census_gsis!r}")
            avail_cls = str(c.get("availability_class") or "unknown")
            conflict = (c.get("identity_conflict") or "").strip()
            if avail_cls not in DEFAULT_CLASSES or conflict:
                raise ValueError(f"{who}: not in the default pool (availability {avail_cls!r}{', ' + conflict if conflict else ''})")
            pos = str(c.get("league_position") or "")
            if str(r.get("draft_position") or "").strip() != pos:
                raise ValueError(f"{who}: position mismatch — sidecar {r.get('draft_position')!r} vs the census league placement {pos!r}")
            if sid in forecast_ids or gsis in forecast_gsis:
                raise ValueError(f"{who}: already has a forecast in this catalog (accepted rows, recoveries or another producer); "
                                 f"a starting estimate is new-only and never overwrites")
            out.append(StartingEstimate(sleeper_id=sid, gsis=gsis, name=name, position=pos, route=str(r.get("route") or ""),
                                        draft_status=str(r.get("draft_status") or ""), seasons=seasons, classes=classes,
                                        unsupported_years=tuple(unsupported)))
        return out
