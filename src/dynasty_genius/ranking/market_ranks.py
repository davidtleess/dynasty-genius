"""Source-bound independent five-year ranks versus FantasyCalc. No model fitting or I/O writes."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import date as calendar_date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POSITIONS = {"QB", "RB", "WR", "TE"}
ROW_HASH_FIELDS = (
    "sleeper_id",
    "player_name",
    "position",
    "value",
    "overall_rank",
    "position_rank",
    "trend_30day",
    "market_volatility",
    "market_volatility_status",
)


class SourceError(ValueError):
    """The configured source cannot support a comparison."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceError(message)


def digest(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def ranks(values: dict[str, float]) -> dict[str, dict[str, int]]:
    require(all(number(v) and v >= 0 for v in values.values()), "Invalid rank value")
    counts = Counter(values.values())
    intervals = {}
    above = 0
    for value in sorted(counts, reverse=True):
        intervals[value] = dict(
            start=above + 1, end=above + counts[value], total=len(values)
        )
        above += counts[value]
    return {key: intervals[value].copy() for key, value in values.items()}


def compare(ours: dict | None, market: dict | None) -> dict:
    if ours is None or market is None:
        return dict(direction="unavailable", gap_min=None, gap_max=None)
    require(ours["total"] == market["total"], "Different rank populations")
    low, high = market["start"] - ours["end"], market["end"] - ours["start"]
    direction = (
        "higher"
        if low > 0
        else "lower"
        if high < 0
        else "same"
        if low == high == 0
        else "overlap"
    )
    return dict(direction=direction, gap_min=low, gap_max=high)


def indexed(rows: list[dict], key: str) -> dict[str, dict]:
    out = {}
    for row in rows:
        sid = row[key]
        require(
            isinstance(sid, str) and bool(sid) and sid not in out,
            "Missing or duplicate player identity",
        )
        out[sid] = row
    return out


def build_market_ranks(report: dict, market: dict, snapshot: dict) -> dict:
    """Validate semantic bindings in addition to the manifest's byte-level bindings."""
    try:
        return _build(report, market, snapshot)
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise SourceError("Incomplete comparison source") from exc


def build_forward_market_ranks(report: dict, market: dict, snapshot: dict) -> dict:
    """Explicit research pairing of a frozen forecast with a later market capture.

    Ownership and football assumptions remain those of the original forecast. This
    creates a new reading; callers must never replace an archived market or date.
    The ordinary same-day reader retains its stricter temporal contract.
    This factory enforces date ordering, not enrollment freshness or endpoint
    windows; the tracker and declared evaluator enforce those bounds separately.
    """
    try:
        return _build(report, market, snapshot, forward_market=True)
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise SourceError("Incomplete forward comparison source") from exc


def _build(report: dict, market: dict, snapshot: dict, *, forward_market=False) -> dict:
    league = snapshot["league"]
    scoring = league["scoring_settings"]
    settings = market["settings"]
    require(
        settings == dict(isDynasty=True, numQbs=2, numTeams=12, ppr=1),
        "Market settings do not match the approved league",
    )
    require(
        league["settings"]["num_teams"] == 12
        and league["settings"]["type"] == 2
        and "SUPER_FLEX" in league["roster_positions"]
        and scoring["rec"] == 1,
        "Saved league settings do not match",
    )
    require(
        not any(
            value
            for key, value in scoring.items()
            if "te" in key.lower().split("_") and ("rec" in key or "bonus" in key)
        ),
        "TE premium is not supported by this market capture",
    )
    require(
        report["league"]["scoring"] == scoring
        and report["league"]["teams"] == 12
        and report["league"]["te_premium"] == 0,
        "Report league context differs",
    )
    require(
        dict(Counter(league["roster_positions"])) == report["league"]["slots"],
        "Report and league starting slots differ",
    )
    require(
        report["league"]["captured_at"] == snapshot["captured_at"],
        "Report and ownership captures differ",
    )
    target = report["board_target"]
    require(
        target["window"] == "championship_week17"
        and target["scoring"] == "PPR_nflverse_default"
        and target["quantity"] == "season_points"
        and target["scope"] == "REG"
        and target["event"] == "appearance"
        and target["clock"] == "per_season"
        and target["labels_through"] < int(report["forecast_date"][:4]),
        "Unexpected forecast target",
    )
    date = report["forecast_date"]
    if forward_market:
        try:
            forecast_day = calendar_date.fromisoformat(date)
            market_day = calendar_date.fromisoformat(market["snapshot_date"])
            observed = datetime.fromisoformat(market["retrieved_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise SourceError("Invalid forward comparison date") from exc
        require(
            observed.tzinfo is not None
            and date == snapshot["captured_at"][:10]
            and market_day == observed.astimezone(timezone.utc).date()
            and market_day >= forecast_day,
            "Forward comparison source dates differ or precede forecast",
        )
    else:
        require(
            date
            == market["snapshot_date"]
            == snapshot["captured_at"][:10]
            == market["retrieved_at"][:10],
            "Comparison source dates differ",
        )
    require(str(league["season"]) == date[:4], "League season differs from forecast")
    board = report[report["comparable_views"]["h5"]]
    require(
        board["horizons_summed"] == 5
        and board["readiness"]["comparable"] == len(board["all_inspectable"]),
        "Five-year board is not ready",
    )
    models = indexed(board["all_inspectable"], "sleeper_id")
    require(bool(models), "No model players")
    roster = next(
        (
            r
            for r in snapshot["rosters"]
            if r["roster_id"] == snapshot["david_roster_id"]
        ),
        None,
    )
    require(roster is not None, "Saved roster missing")
    owned = set(roster["players"])
    require(len(owned) == len(roster["players"]), "Duplicate roster identity")
    taxi = set(roster.get("taxi") or []) | set(roster.get("reserve") or [])
    require(taxi <= owned, "Invalid taxi or reserve membership")
    require(
        set(report["davids_best_lineup_served_h0"]["excluded_taxi_or_reserve"]) == taxi,
        "Report taxi/reserve context differs",
    )
    identities = indexed(snapshot["players"], "sleeper_player_id")
    require(owned <= models.keys(), "Saved roster is not covered by accepted board")
    years = list(range(int(date[:4]), int(date[:4]) + 5))
    for sid, row in models.items():
        require(
            row["position"] in POSITIONS and bool(row["name"]), "Invalid model identity"
        )
        require(
            sid in identities and row["position"] in row["fantasy_positions"],
            "Model identity differs from saved league",
        )
        require(
            row["readiness"] == "comparable" and row["evidence_verified"] is True,
            "Unaccepted model evidence",
        )
        require(number(row["value"]) and row["value"] >= 0, "Invalid model value")
        require(
            row["on_davids_roster"] is (sid in owned),
            "Report roster flags disagree with saved roster",
        )
        if sid in owned:
            require(
                row["rostered_by"] == snapshot["david_roster_id"],
                "Report owner differs",
            )
        seasons = row["seasons"]
        require(
            [s["season"] for s in seasons] == years, "Incomplete five-year forecast"
        )
        require(
            all(
                number(s["expected_margin"])
                and number(s["advantage"])
                and s["advantage"] == max(0, s["expected_margin"])
                for s in seasons
            ),
            "Invalid annual advantage",
        )
        require(
            math.isclose(
                sum(s["advantage"] for s in seasons),
                row["value"],
                rel_tol=1e-12,
                abs_tol=1e-9,
            ),
            "Five-year total differs from annual advantages",
        )
    capture = market["capture_report"]
    require(
        market["schema_version"] == 1
        and market["source"] == "fc_native"
        and capture["status"] == "ok",
        "Market capture is not usable",
    )
    require(
        market["settings_hash"]
        == hashlib.sha256(b"isDynasty=true&numQbs=2&numTeams=12&ppr=1").hexdigest()[
            :16
        ],
        "Market settings hash mismatch",
    )
    for key in ("source", "snapshot_date", "settings_hash", "retrieved_at"):
        require(capture[key] == market[key], "Market capture metadata differs")
    raw_assets = market["entries"]
    # Preserve and attest the entire raw capture. Only resolved identities can
    # participate in a player comparison; no synthetic player IDs are invented.
    assets = indexed(
        [e for e in raw_assets if e.get("sleeper_id")] if forward_market else raw_assets,
        "sleeper_id",
    )
    require(
        len({e["player_key"] for e in raw_assets}) == len(raw_assets),
        "Duplicate market key",
    )
    for entry in raw_assets:
        require(
            entry["position"] in POSITIONS | {"PICK"} | ({"UNK"} if forward_market else set()),
            "Unexpected market asset type",
        )
        require(number(entry["value"]) and entry["value"] >= 0, "Invalid market value")
        require(
            isinstance(entry["overall_rank"], int)
            and not isinstance(entry["overall_rank"], bool)
            and entry["overall_rank"] > 0,
            "Missing published market rank",
        )
        require(
            digest({key: entry[key] for key in ROW_HASH_FIELDS})
            == entry["payload_hash"],
            "Market row content hash mismatch",
        )
        require(
            all(
                entry[key] == market[key]
                for key in ("source", "snapshot_date", "settings_hash", "retrieved_at")
            ),
            "Market row metadata differs",
        )
    require(
        capture["joinable_rows_written"] == len(assets)
        and capture["raw_entries_written"] == len(raw_assets),
        "Market capture count differs",
    )
    require(
        digest(
            {
                "sigs": sorted(
                    e["player_key"] + ":" + e["payload_hash"] for e in raw_assets
                )
            }
        )
        == capture["store_hash"],
        "Market store hash mismatch",
    )
    prices = {
        sid: e for sid, e in assets.items()
        if e["position"] in POSITIONS or (forward_market and e["position"] == "UNK")
    }
    unresolved = {sid for sid, e in prices.items() if e["position"] == "UNK"}
    common = (models.keys() & prices.keys()) - unresolved
    require(bool(common), "No comparable players")
    require(
        all(models[s]["position"] == prices[s]["position"] for s in common),
        "Market and model positions disagree",
    )
    model_ranks = ranks({s: models[s]["value"] for s in common})
    market_ranks = ranks({s: prices[s]["value"] for s in common})
    all_ranks = ranks({s: r["value"] for s, r in models.items()})
    rows = []
    for sid in sorted(models.keys() | prices.keys()):
        model, price = models.get(sid), prices.get(sid)
        identity = model or dict(name=price["player_name"], position=price["position"])
        missing = (
            None
            if sid in common
            else (
                "FantasyCalc position is unresolved; the price is retained but excluded from the paired ranking."
                if sid in unresolved
                else "No saved FantasyCalc price for this player."
                if price is None
                else "No accepted five-year valuation. Starting estimates on other pages are not included in this ranking."
            )
        )
        rows.append(
            dict(
                sleeper_id=sid,
                name=identity["name"],
                position=identity["position"],
                team=(
                    identities.get(sid, {}).get("player", {}).get("team")
                    or identity.get("team")
                ),
                on_roster=sid in owned,
                league_ownership=(
                    "Your roster"
                    if sid in owned
                    else "Rostered in your league"
                    if identities.get(sid, {}).get("league_context", {}).get("rostered")
                    is True
                    else "League free agent"
                    if identities.get(sid, {}).get("league_context", {}).get("rostered")
                    is False
                    else "League ownership unknown"
                ),
                taxi_or_reserve=(sid in taxi) if sid in owned else None,
                model_value=model["value"] if model else None,
                market_value=price["value"] if price else None,
                our_rank=model_ranks.get(sid),
                market_rank=market_ranks.get(sid),
                model_rank_all=all_ranks.get(sid),
                market_rank_published=price["overall_rank"] if price else None,
                comparison=compare(model_ranks.get(sid), market_ranks.get(sid)),
                missing_reason=missing,
                model_zero_tie=model is not None and model["value"] == 0,
                seasons=[
                    dict(season=s["season"], advantage=s["advantage"])
                    for s in model["seasons"]
                ]
                if model
                else [],
                reference_player=model["reference_player"] if model else None,
            )
        )
    return dict(
        status="available",
        source=dict(
            report_run=str(report["run"]),
            report_sha256="",
            market_sha256="",
            league_sha256="",
            forecast_date=date,
            market_as_of=market["retrieved_at"],
            ownership_as_of=snapshot["captured_at"],
        ),
        basis=dict(
            years=years,
            season_weights=[1] * 5,
            summary=f"Our rank sums projected advantage above an available replacement at each position over five equally weighted seasons, {years[0]}–{years[-1]}. The same replacement reference is assumed in future years; future waiver access is not guaranteed.",
            market_proxy_note="FantasyCalc represents the broader market, not what a specific manager in your league would pay.",
            scoring_note="12-team Superflex, full PPR, no TE premium; championship through Week 17. Forecasts use research PPR scoring, not every custom league rule. This is an exploratory valuation, not a proven trading edge or your lineup improvement.",
        ),
        coverage=dict(
            model_players=len(models),
            market_players=len(prices),
            market_picks=sum(e["position"] == "PICK" for e in raw_assets),
            common_players=len(common),
            total_players=len(rows),
            roster_players=len(owned),
            roster_common_players=len(owned & common),
            **({"market_unresolved_positions": len(unresolved),
                "market_unresolved_identities": len(raw_assets) - len(assets)} if forward_market else {}),
        ),
        rows=rows,
    )


def load_market_ranks(manifest_path: Path) -> dict:
    try:
        manifest = json.loads(manifest_path.read_bytes())
        require(manifest["schema_version"] == 1, "Unsupported comparison manifest")
        data, hashes = {}, {}
        for key in ("report", "market", "league"):
            spec = manifest["files"][key]
            path = Path(spec["path"])
            require(path.is_absolute(), "Source paths must be absolute")
            raw = path.read_bytes()
            hashes[key] = hashlib.sha256(raw).hexdigest()
            require(
                hashes[key] == spec["sha256"], f"{key} source integrity check failed"
            )
            data[key] = json.loads(raw)
        require(
            data["report"]["inputs"]["snapshot"]["sha256"] == hashes["league"],
            "Report-bound ownership bytes differ",
        )
        require(
            str(data["report"]["run"]) == manifest["report_run"],
            "Report run binding differs",
        )
        payload = build_market_ranks(data["report"], data["market"], data["league"])
        payload["source"].update(
            {f"{key}_sha256": value for key, value in hashes.items()}
        )
        return payload
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, SourceError):
            raise
        raise SourceError("Configured comparison sources could not be read") from exc
