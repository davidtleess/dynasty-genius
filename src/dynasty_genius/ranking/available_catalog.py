"""The available-player catalog (DG-178 plan T1, 2026-09-06; David: "ok go").

Who can David actually pick up, what does the model expect now and later, and what do we not
yet know? The catalog READS the accepted audit report, the SAME census bytes that report bound,
and the producers' frozen CSVs whose hashes the report records; it composes nothing.

* population = census members NOT owned in the verified league snapshot; the default pool is
  the verified NFL classes {active, practice_squad, injured_reserve}; cut, retired and unknown
  are separate, inspectable populations; owned members ride along as identity/status-only rows
  so a watched player who became owned stays resolvable; uncovered Sleeper ids and NFL rows
  without a Sleeper identity are DISCLOSURES with their dated sources, never availability;
* values are the PRODUCER's own expected season points, appearance probabilities, conditional
  points and games for the requested path (the report's forecast year and the four years after
  it), joined by verified identity only — the accepted report's gsis and the census's verified
  NFL gsis, which must AGREE when both are present; a conflict fails, it never substitutes
  another player;
* every producer file is checked against the accepted report: bytes (sha256), the selected arm
  / model declaration, the forecast-year semantics (cutoff, season labels or draft season) and
  duplicate identities; every cell is checked for finiteness, probability bounds and the
  hurdle identity e = P(appear) × E[· | appear]; aggregates are checked finite as well;
* now = the forecast year's expected points; future = the sum over the four named later years
  only when every one of them is present and finite, otherwise undefined with a reason — never
  zero, never a partial total; a negative forecast is a value; a producer row whose every year
  is blank is NO usable forecast; a member without a verified forecast is retained with a plain
  reason. Root-permitted recovery of a frozen producer row under the census's verified NFL gsis
  is flagged, counted and carries the exact gsis used.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Optional

from src.dynasty_genius.ranking.current_census_binding import CensusBinding

DEFAULT_CLASSES = ("active", "practice_squad", "injured_reserve")
SEPARATE_POPULATIONS = ("cut", "retired", "unknown")
PATH_LENGTH = 5
FORECAST_YEARS = (2026, 2027, 2028, 2029, 2030)     # the 2026 path; build() derives the path from the report
FUTURE_YEARS = (2027, 2028, 2029, 2030)
NO_REASON = "no forecast from the selected producers; no reason stated"
BLANK_ROW_REASON = "producer row found under the verified identity but every season's expected points is blank: no usable forecast"
OWNED_REASON = "owned in your league; forecasts are shown on the research board"
FORECAST_NOTE = ("values are the producers' own expected season points (nflverse default PPR, championship window) with "
                 "their appearance probabilities; not the impact number, not weekly start advice, not cross-position dynasty value")
IDENTITY_TOL = 1e-6


@dataclass(frozen=True)
class SeasonForecast:
    season: int
    e_points: float
    p_appear: Optional[float]
    e_points_given_appear: Optional[float]
    e_games: Optional[float]


@dataclass(frozen=True)
class Forecast:
    producer: str
    source_csv: str
    source_csv_sha256: str
    join_basis: str
    join_id: str                          # the exact verified identity the producer row was read under
    seasons: tuple[SeasonForecast, ...]


@dataclass(frozen=True)
class CatalogRow:
    sleeper_id: str
    player_id: Optional[str]
    name: str
    league_position: str
    fantasy_positions: str
    availability_class: str
    population: str                      # default | cut | retired | unknown | owned
    nfl_team: Optional[str]
    nfl_status_raw: Optional[str]
    join_basis: str
    identity_conflict: Optional[str]
    forecast: Optional[Forecast]
    now_points: Optional[float]
    future_points: Optional[float]
    future_years: list[int]
    future_reason: Optional[str]
    missing_reason: Optional[str]
    impact: dict[str, Optional[float]]
    readiness: Optional[str]
    owned_now: bool = False
    roster_id: Optional[int] = None
    recovered: bool = False              # forecast recovered from a frozen producer file by verified identity
    forecast_path: dict[str, Any] = field(default_factory=lambda: {"status": "none", "years_present": []})
    starting_estimate: bool = False      # root-accepted cold-start sidecar (new-only); per-year class in estimate_classes
    estimate_classes: Optional[dict[int, str]] = None

    def to_dict(self) -> dict[str, Any]:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__ if k != "forecast"}
        d["forecast"] = None if self.forecast is None else {
            "producer": self.forecast.producer, "source_csv": self.forecast.source_csv,
            "source_csv_sha256": self.forecast.source_csv_sha256, "join_basis": self.forecast.join_basis,
            "join_id": self.forecast.join_id, "seasons": [s.__dict__ for s in self.forecast.seasons]}
        return d


def _f(v, what: str = "producer value") -> Optional[float]:
    if v is None or str(v).strip() == "":
        return None
    x = float(v)
    if not math.isfinite(x):
        raise ValueError(f"non-finite {what} {v!r}")
    return x


def _seasons_from_row(prow: dict, years: tuple[int, ...], who: str) -> tuple[SeasonForecast, ...]:
    """The producer's own values for the requested path, every cell validated: finite, P(appear)
    within [0, 1], and the hurdle identity e = P(appear) × E[· | appear] for points and games."""
    seasons = []
    for j, year in enumerate(years, start=1):
        e = _f(prow.get(f"e_points_year{j}"), f"e_points_year{j} for {who}")
        p = _f(prow.get(f"p_appear_year{j}"), f"p_appear_year{j} for {who}")
        c = _f(prow.get(f"e_points_year{j}_given_appear"), f"e_points_year{j}_given_appear for {who}")
        g = _f(prow.get(f"e_games_year{j}"), f"e_games_year{j} for {who}")
        gc = _f(prow.get(f"e_games_year{j}_given_appear"), f"e_games_year{j}_given_appear for {who}")
        if p is not None and not 0.0 <= p <= 1.0:
            raise ValueError(f"{who}: p_appear_year{j} = {p} is not a probability in [0, 1]")
        if e is None:
            continue
        for label, total, cond in (("points", e, c), ("games", g, gc)):
            if total is not None and p is not None and cond is not None:
                if abs(total - p * cond) > IDENTITY_TOL * max(1.0, abs(total)):
                    raise ValueError(f"{who}: year {year} {label} break the conditional identity "
                                     f"e = P(appear) × E[{label} | appear] ({total} vs {p} × {cond})")
        seasons.append(SeasonForecast(season=year, e_points=e, p_appear=p, e_points_given_appear=c, e_games=g))
    return tuple(seasons)


def _now_future(seasons: tuple[SeasonForecast, ...], years: tuple[int, ...], *, who: str,
                unsupported: tuple[int, ...] = ()) -> tuple[Optional[float], Optional[float], Optional[str], dict[str, Any]]:
    """now = the first year's expected points; future = the later years summed only when every one is
    present and the sum is finite; otherwise undefined with the reason (missing, or unsupported by
    the producer) — never zero, never partial."""
    by_year = {s.season: s.e_points for s in seasons}
    future_years = years[1:]
    present = sorted(by_year)
    path = {"status": "complete" if present == list(years) else "incomplete", "years_present": present}
    missing_years = [y for y in future_years if y not in by_year]
    if missing_years:
        words = [f"{y} unsupported by the producer" if y in unsupported else str(y) for y in missing_years]
        if all(y in unsupported for y in missing_years):
            reason = f"{', '.join(words)}: future total undefined, not zero"
        else:
            reason = f"{', '.join(words)} forecast missing: future total undefined, not zero"
        return by_year.get(years[0]), None, reason, path
    future = float(sum(by_year[y] for y in future_years))
    if not math.isfinite(future):
        raise ValueError(f"{who}: the future total over {future_years[0]}–{future_years[-1]} is not finite")
    return by_year.get(years[0]), future, None, path


def _year_from(text: str) -> Optional[int]:
    m = re.search(r"(19|20)\d{2}", str(text or ""))
    return int(m.group(0)) if m else None


def _load_producer(path: Path, declared: dict, years: tuple[int, ...]) -> dict:
    """Read one producer CSV and validate it against the accepted report's declaration: bytes,
    arm / model, forecast-year semantics, duplicate identities."""
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    model_version, want, seasons_declared, scoring_arm = declared["model_version"], declared["sha256"], declared["seasons"], declared["arm"]
    if want != sha:
        raise ValueError(f"{path.name}: bytes do not match the sha256 the accepted report records")
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    if not rows:
        raise ValueError(f"{path.name}: the producer file has no rows")
    cols = set(rows[0].keys())
    # the selected arm / model declaration, validated row by row — a hash alone proves bytes, not the arm
    arm_cols = [c for c in ("arm", "scoring_arm_id") if c in cols]
    if not arm_cols and "model_version" not in cols:
        raise ValueError(f"{path.name}: the producer file declares no arm or model_version column; cannot verify the selected arm")
    for r in rows:
        for c in arm_cols:
            if str(r.get(c) or "").strip() != str(scoring_arm or ""):
                raise ValueError(f"{path.name}: row {r.get('player_id') or r.get('gsis_id')!s} carries arm {r.get(c)!r}, "
                                 f"not the arm the accepted report declares ({scoring_arm!r})")
        if "model_version" in cols and str(r.get("model_version") or "").strip() != str(model_version):
            raise ValueError(f"{path.name}: row model_version {r.get('model_version')!r} is not the declared {model_version!r} (arm/model mismatch)")
    # forecast-year semantics: the file must SAY it forecasts the requested path; labels are never applied over mismatched values
    year1 = years[0]
    has_season_labels = any(f"forecast_season_year{j}" in cols for j in range(1, len(years) + 1))
    if "forecast_cutoff" in cols:
        for r in rows:
            cutoff_year = _year_from(r.get("forecast_cutoff"))
            if cutoff_year is None or cutoff_year + 1 != year1:
                raise ValueError(f"{path.name}: forecast_cutoff {r.get('forecast_cutoff')!r} does not precede the requested "
                                 f"{year1}–{years[-1]} path (expected the {year1 - 1} season as cutoff)")
    if has_season_labels:
        for r in rows:
            for j, year in enumerate(years, start=1):
                label = str(r.get(f"forecast_season_year{j}") or "").strip()
                if label == "":
                    if str(r.get(f"e_points_year{j}") or "").strip() != "":
                        raise ValueError(f"{path.name}: e_points_year{j} present but forecast_season_year{j} is unlabelled")
                    continue
                if int(float(label)) != year:
                    raise ValueError(f"{path.name}: forecast_season_year{j} is {label}, not the requested {year} "
                                     f"(path {year1}–{years[-1]}); refusing to relabel")
    elif "draft_season" in cols:
        for r in rows:
            ds = _year_from(r.get("draft_season"))
            if ds != year1:
                raise ValueError(f"{path.name}: draft_season {r.get('draft_season')!r} is not the forecast year {year1}; "
                                 f"year 1 is the rookie season, so this file does not forecast the requested path")
    else:
        raise ValueError(f"{path.name}: cannot establish forecast-year semantics (no forecast_season_year columns and no draft_season)")
    if seasons_declared and seasons_declared < len(years):
        raise ValueError(f"{path.name}: the report declares {seasons_declared} seasons, fewer than the {len(years)}-year path")
    by_gsis: dict[str, dict] = {}
    by_key: dict[tuple[int, int], dict] = {}
    for r in rows:
        g = str(r.get("gsis_id") or r.get("player_id") or "").strip()
        if g:
            if g in by_gsis:
                raise ValueError(f"{path.name}: duplicate identity {g}; refusing to let one row overwrite another")
            by_gsis[g] = r
        if r.get("draft_season") and r.get("pick"):
            key = (int(float(r["draft_season"])), int(float(r["pick"])))
            if key in by_key:
                raise ValueError(f"{path.name}: duplicate draft key {key}; refusing to let one row overwrite another")
            by_key[key] = r
    return {"csv": str(path), "sha256": sha, "seasons": seasons_declared, "arm": scoring_arm, "by_gsis": by_gsis, "by_key": by_key}


@dataclass
class AvailableCatalog:
    rows: list[CatalogRow]
    sources: dict[str, Any]
    populations_note: str
    disclosures: dict[str, Any]
    ownership_as_of: Optional[str]
    nfl_status_as_of: Optional[str]
    census_run_id: str
    source_report_run: str
    forecast_years: tuple[int, ...]
    _binding: CensusBinding = field(repr=False)

    @classmethod
    def build(cls, report_path: Path | str, census_dir: Path | str, producer_csvs: Iterable[Path | str], *,
              snapshot_path: Path | str, cold_start: Any = None) -> "AvailableCatalog":
        rp, snap_p = Path(report_path), Path(snapshot_path)
        report_bytes = rp.read_bytes()
        report = json.loads(report_bytes)
        snapshot_bytes = snap_p.read_bytes()
        snapshot = json.loads(snapshot_bytes)
        snapshot_sha = hashlib.sha256(snapshot_bytes).hexdigest()
        rep_snap = (report.get("inputs") or {}).get("snapshot") or {}
        if str(rep_snap.get("sha256") or "").lower() != snapshot_sha:
            raise ValueError("the league snapshot bytes do not match the sha256 the accepted report records")
        owned = {str(pid): int(r["roster_id"]) for r in (snapshot.get("rosters") or []) for pid in (r.get("players") or [])}
        forecast_year = _year_from(report.get("forecast_date"))
        if forecast_year is None:
            raise ValueError("the accepted report states no forecast_date; the requested path cannot be established")
        years = tuple(forecast_year + i for i in range(PATH_LENGTH))
        future_years = years[1:]
        binding = CensusBinding.load(census_dir, season=forecast_year, league_snapshot_sha256=snapshot_sha, snapshot_owned=owned)
        rep_census = report.get("current_census") or {}
        # the WHOLE captured census must be the one the accepted report bound: the member CSV, the census's
        # own report (roster date, counts, identity checks) and the uncovered list — a hash of the CSV alone
        # would let a metadata-only edit change the freshness and disclosure counts under the accepted sha
        for key, actual in (("census_csv_sha256", binding.census_csv_sha256), ("report_sha256", binding.report_sha256),
                            ("uncovered_csv_sha256", binding.uncovered_csv_sha256)):
            want = str(rep_census.get(key) or "").lower()
            if not want:
                raise ValueError(f"the accepted report does not record current_census.{key}; the census cannot be bound")
            if want != actual:
                raise ValueError(f"the census bound here is not the census the accepted report bound ({key} differs)")
        # producers: the report's declarations (bytes, arm, seasons) must be met by the files read
        main = report.get("horizon_board") or report.get("comparable_board") or {}
        declared: dict[str, dict] = {}
        for m in main.get("annual_producers") or []:
            if "csv" in m and m.get("csv_sha256"):
                declared[Path(m["csv"]).name] = {"model_version": m["model_version"], "sha256": str(m["csv_sha256"]).lower(),
                                                 "seasons": int(m.get("seasons") or 0),
                                                 "arm": (m.get("evidence") or {}).get("scoring_arm")}
        producers: dict[str, dict] = {}
        seen_paths: set[Path] = set()
        for p in producer_csvs:
            p = Path(p).resolve()
            if p in seen_paths:
                raise ValueError(f"{p.name}: duplicate producer argument (the same file supplied twice)")
            seen_paths.add(p)
            if p.name not in declared:
                raise ValueError(f"{p.name} is not a producer the accepted report records")
            d = declared[p.name]
            if d["model_version"] in producers:
                raise ValueError(f"{p.name}: duplicate producer {d['model_version']!r} (two files for one declared model)")
            producers[d["model_version"]] = _load_producer(p, d, years)
        # the accepted report's rows by Sleeper id (readiness, impact, producer name, gsis); duplicates refused
        rep_rows: dict[str, dict] = {}
        gsis_owner: dict[str, str] = {}
        for x in main.get("all_inspectable") or []:
            sid = str(x.get("sleeper_id") or "")
            if not sid:
                continue
            if sid in rep_rows:
                raise ValueError(f"duplicate Sleeper identity {sid} in the accepted report's rows")
            rid = str(x.get("player_id") or "")
            if rid.startswith("00-"):
                if rid in gsis_owner and gsis_owner[rid] != sid:
                    raise ValueError(f"duplicate gsis {rid} in the accepted report's rows (Sleeper {gsis_owner[rid]} and {sid})")
                gsis_owner[rid] = sid
            rep_rows[sid] = x
        two = report.get("comparable_board") or {}
        impact2 = {str(x["sleeper_id"]): x.get("value") for x in two.get("all_inspectable") or [] if x.get("sleeper_id")}
        impact5 = {sid: x.get("value") for sid, x in rep_rows.items()}
        stated_reasons: dict[str, str] = {}
        for sid, x in rep_rows.items():
            reason = x.get("reason") or ""
            if "the producer's stated reason:" in reason:
                stated_reasons[sid] = reason.split("the producer's stated reason:", 1)[1].strip()

        out: list[CatalogRow] = []
        recovered: list[dict] = []
        for sid, c in binding._rows.items():
            name = str(c.get("name") or "")
            if sid in owned:
                out.append(CatalogRow(
                    sleeper_id=sid, player_id=(rep_rows.get(sid) or {}).get("player_id"), name=name,
                    league_position=str(c.get("league_position") or "?"), fantasy_positions=str(c.get("fantasy_positions") or ""),
                    availability_class=str(c.get("availability_class") or "unknown"), population="owned",
                    nfl_team=c.get("nfl_team") or None, nfl_status_raw=c.get("nfl_status_raw") or None,
                    join_basis=str(c.get("join_basis") or ""), identity_conflict=(c.get("identity_conflict") or "").strip() or None,
                    forecast=None, now_points=None, future_points=None, future_years=list(future_years), future_reason=None,
                    missing_reason=OWNED_REASON, impact={"h2": impact2.get(sid), "h5": impact5.get(sid)},
                    readiness=(rep_rows.get(sid) or {}).get("readiness"), owned_now=True, roster_id=owned[sid],
                    forecast_path={"status": "not_carried", "years_present": []}))
                continue
            avail_cls = str(c.get("availability_class") or "unknown")
            conflict = (c.get("identity_conflict") or "").strip() or None
            if avail_cls in DEFAULT_CLASSES and not conflict:
                population = "default"
            elif avail_cls in SEPARATE_POPULATIONS:
                population = avail_cls
            else:
                population = "unknown"
            rr = rep_rows.get(sid)
            forecast = None
            missing_reason = None
            census_gsis = str(c.get("nfl_gsis_id") or "").strip()
            if rr is not None and rr.get("readiness") == "comparable":
                producer_name = str(rr.get("producer") or "")
                prod = producers.get(producer_name)
                if prod is None:
                    raise ValueError(f"{name}: the accepted report names producer {producer_name!r} whose CSV was not supplied")
                # verified identities only: the accepted report's gsis and the census's verified NFL gsis,
                # which must agree when both are present; never Sleeper's own guess, never a name
                rid = str(rr.get("player_id") or "")
                report_gsis = rid if rid.startswith("00-") else ""
                if report_gsis and census_gsis and report_gsis != census_gsis:
                    raise ValueError(f"{name}: identity conflict — the accepted report says {report_gsis} but the census's verified "
                                     f"NFL gsis is {census_gsis}; refusing to substitute another player's forecast")
                if report_gsis:
                    basis, g = "report_gsis", report_gsis
                elif census_gsis.startswith("00-"):
                    basis, g = "census_nfl_gsis", census_gsis
                else:
                    raise ValueError(f"{name}: no verified gsis for a comparable report row (report id {rid!r}, census gsis {census_gsis!r})")
                prow = prod["by_gsis"].get(g)
                if prow is None:
                    raise ValueError(f"{name}: no producer row for {g} ({basis}) in {Path(prod['csv']).name}; "
                                     f"the accepted report calls him comparable")
                seasons = _seasons_from_row(prow, years, f"{name} ({g})")
                if seasons:
                    forecast = Forecast(producer=producer_name, source_csv=prod["csv"], source_csv_sha256=prod["sha256"],
                                        join_basis=basis, join_id=g, seasons=seasons)
                else:
                    missing_reason = BLANK_ROW_REASON
            is_recovered = False
            if forecast is None and missing_reason is None and population == "default" and census_gsis.startswith("00-"):
                # Root-permitted recovery: a frozen producer row under the census's VERIFIED NFL gsis
                # (never a Sleeper-only or contested identity), with the exact original values.
                for producer_name, prod in producers.items():
                    prow = prod["by_gsis"].get(census_gsis)
                    if prow is None:
                        continue
                    seasons = _seasons_from_row(prow, years, f"{name} ({census_gsis}, recovered)")
                    if seasons:
                        forecast = Forecast(producer=producer_name, source_csv=prod["csv"], source_csv_sha256=prod["sha256"],
                                            join_basis="recovered_census_nfl_gsis", join_id=census_gsis, seasons=seasons)
                        is_recovered = True
                        recovered.append({"sleeper_id": sid, "gsis": census_gsis, "producer": producer_name})
                        break
            if forecast is None:
                now, future, future_reason, path = None, None, None, {"status": "none", "years_present": []}
            else:
                now, future, future_reason, path = _now_future(forecast.seasons, years, who=name)
            if forecast is None and missing_reason is None:
                missing_reason = stated_reasons.get(sid) or NO_REASON
            out.append(CatalogRow(
                sleeper_id=sid, player_id=(rr.get("player_id") if rr else None), name=name,
                league_position=str(c.get("league_position") or "?"), fantasy_positions=str(c.get("fantasy_positions") or ""),
                availability_class=avail_cls, population=population, nfl_team=c.get("nfl_team") or None,
                nfl_status_raw=c.get("nfl_status_raw") or None, join_basis=str(c.get("join_basis") or ""),
                identity_conflict=conflict, forecast=forecast, now_points=now, future_points=future,
                future_years=list(future_years), future_reason=future_reason, missing_reason=missing_reason,
                impact={"h2": impact2.get(sid), "h5": impact5.get(sid)}, readiness=(rr.get("readiness") if rr else None),
                recovered=is_recovered, forecast_path=path,
            ))
        starting: list[dict] = []
        if cold_start is not None:
            # Root-accepted cold-start sidecar, NEW-ONLY: verified against the same census, the same outcome
            # target and the requested path; a player who already has a forecast is refused, never overwritten.
            forecast_ids = {r.sleeper_id for r in out if r.forecast is not None}
            forecast_gsis = {r.forecast.join_id for r in out if r.forecast is not None}
            estimates = cold_start.bind(report=report, years=years, census=binding._rows, owned=owned,
                                        forecast_ids=forecast_ids, forecast_gsis=forecast_gsis)
            index = {r.sleeper_id: i for i, r in enumerate(out)}
            for est in estimates:
                i = index[est.sleeper_id]
                row = out[i]
                if row.population != "default" or row.forecast is not None:
                    raise ValueError(f"{est.name}: not an unforecast default-pool row; a starting estimate is new-only")
                fc = Forecast(producer=cold_start.producer, source_csv=str(cold_start.estimates_path),
                              source_csv_sha256=cold_start.estimates_sha256, join_basis="cold_start_census_nfl_gsis",
                              join_id=est.gsis, seasons=est.seasons)
                now, future, future_reason, path = _now_future(est.seasons, years, who=est.name, unsupported=est.unsupported_years)
                out[i] = replace(row, forecast=fc, now_points=now, future_points=future, future_reason=future_reason,
                                 missing_reason=None, forecast_path=path, starting_estimate=True, estimate_classes=dict(est.classes))
                starting.append({"sleeper_id": est.sleeper_id, "gsis": est.gsis, "classes": dict(est.classes)})
        roster_src = (binding.sources.get("nflverse_roster") or {})
        disclosures = {
            "uncovered_sleeper_ids": binding.uncovered_count,
            "unmatched_nfl_records": binding.unmatched_nfl_records,
            "contested_nfl_records": binding.contested_nfl_records,
            "archive_unforecast_by_position": {pos: int((v or {}).get("count") or 0)
                                               for pos, v in (report.get("unforecast_eligible_census") or {}).items()},
            "note": ("uncovered Sleeper ids (no verified join to the captured roster) and NFL records without a Sleeper "
                     "identity are shown as counts only; neither is a fantasy pickup candidate here"),
        }
        sources = {"report": str(rp), "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                   "report_run": str(report.get("run")), "census_run_id": binding.run_id,
                   "census_csv_sha256": binding.census_csv_sha256, "snapshot_sha256": snapshot_sha,
                   "census": {"run_id": binding.run_id, "census_csv_sha256": binding.census_csv_sha256,
                              "report_sha256": binding.report_sha256, "uncovered_csv_sha256": binding.uncovered_csv_sha256},
                   "producers": {k: {"csv": v["csv"], "sha256": v["sha256"], "seasons": v["seasons"], "arm": v["arm"]}
                                 for k, v in producers.items()},
                   "census_identity_checks": binding.identity_checks,
                   "validation": {"bytes": "sha256 of every producer file equals the accepted report's record",
                                  "arm": "every producer row's arm / model_version equals the report's declared scoring arm / model",
                                  "years": f"cutoff, season labels or draft season place year 1 at {forecast_year}; never relabelled",
                                  "identity": "report gsis and census verified NFL gsis must agree; duplicates refused",
                                  "cells": "finite values, P(appear) in [0, 1], e = P(appear) × E[· | appear] for points and games; finite aggregates"}}
        sources["recovered"] = {"count": len(recovered), "rows": recovered,
                                "note": "frozen producer forecasts joined by verified census identity; not among the accepted 825 rows; exact original values"}
        sources["starting_estimates"] = None if cold_start is None else {
            "count": len(starting), "rows": starting, "source": cold_start.source(), "evidence": cold_start.evidence(),
            "note": ("root-accepted cold-start research candidate, new-only: a starting estimate for a drafted player with no "
                     "rookie-season record; year classes are the producer's own selection; not conditioned on remaining on a "
                     "current roster; no impact number is fabricated")}
        return cls(rows=out, sources=sources,
                   populations_note=("default = unowned census members with a verified NFL join in {active, practice squad, "
                                     "injured reserve}; cut, retired and unknown-identity members are separate; ownership "
                                     "filters availability only and never changes a forecast"),
                   disclosures=disclosures, ownership_as_of=snapshot.get("captured_at"),
                   nfl_status_as_of=roster_src.get("http_last_modified") or roster_src.get("captured_at"),
                   census_run_id=binding.run_id, source_report_run=str(report.get("run")), forecast_years=years, _binding=binding)

    def report(self) -> dict[str, Any]:
        pops: dict[str, Any] = {}
        for name in ("default",) + SEPARATE_POPULATIONS + ("owned",):
            rows = [r for r in self.rows if r.population == name]
            if not rows and name != "default":
                continue
            by_pos: dict[str, dict[str, int]] = {}
            for r in rows:
                cell = by_pos.setdefault(r.league_position, {"with_forecast": 0, "without_forecast": 0})
                cell["with_forecast" if r.forecast is not None else "without_forecast"] += 1
            pops[name] = {"total": len(rows), "with_forecast": sum(1 for r in rows if r.forecast is not None),
                          "without_forecast": sum(1 for r in rows if r.forecast is None),
                          "with_now": sum(1 for r in rows if r.now_points is not None),
                          "with_future_total": sum(1 for r in rows if r.future_points is not None),
                          "incomplete_path": sum(1 for r in rows if r.forecast_path.get("status") == "incomplete"),
                          "starting_estimates": sum(1 for r in rows if r.starting_estimate),
                          "recovered": sum(1 for r in rows if r.recovered),
                          "by_class": dict(Counter(r.availability_class for r in rows)), "by_position": by_pos}
        return {"source_report_run": self.source_report_run, "census_run_id": self.census_run_id,
                "populations": pops, "populations_note": self.populations_note, "disclosures": self.disclosures,
                "ownership_as_of": self.ownership_as_of, "nfl_status_as_of": self.nfl_status_as_of,
                "sources": {k: v for k, v in self.sources.items() if k not in ("recovered", "starting_estimates")},
                "recovered": self.sources.get("recovered"),
                "starting_estimates": self.sources.get("starting_estimates") or {"count": 0, "rows": [], "source": None, "evidence": None},
                "forecast_note": FORECAST_NOTE, "forecast_years": list(self.forecast_years),
                "future_years": list(self.forecast_years[1:]), "rows": len(self.rows),
                "available_rows": sum(1 for r in self.rows if r.population != "owned")}

    def to_json(self) -> dict[str, Any]:
        return {**self.report(), "rows_detail": [r.to_dict() for r in self.rows]}
