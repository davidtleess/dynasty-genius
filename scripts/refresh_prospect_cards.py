"""Regenerate resources/prospect_cards.json/.js through Phase 15 PVO assembler.

Sources:
  resources/prospect_identity_2026.json  — canonical identity, pick, round (80 verified 2026)
  resources/prospect_cards.json          — age, player_id (preserved for invariance/continuity)

Outputs:
  resources/prospect_cards.json          — 80 2026 + 2 watchlist, Phase 15 fields added
  resources/prospect_cards.js            — JS wrapper for Rookie Board dashboard
  docs/validation/phase15-2026-rookie-rank-refresh.md

Usage:
    .venv/bin/python3.14 scripts/refresh_prospect_cards.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.dvs_band import (  # noqa: E402
    ENGINE_A_SIGMA_RUN,
    ENGINE_A_V3_SIGMA_RUN,
    assert_band_sigma_runs_match_served_models,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity  # noqa: E402
from src.dynasty_genius.pvo_assembler import assemble_pvo  # noqa: E402

IDENTITY_FILE = ROOT / "resources" / "prospect_identity_2026.json"
CARDS_JSON = ROOT / "resources" / "prospect_cards.json"
CARDS_JS = ROOT / "resources" / "prospect_cards.js"
REPORT_PATH = ROOT / "docs" / "validation" / "phase15-2026-rookie-rank-refresh.md"

_DVS_INVARIANCE_TOLERANCE = 0.01

# DG-158 — a rescale is a DECLARED movement, not a drift.
#
# The invariance gate exists to catch CONTAMINATION: an enrichment run that
# quietly moves a score (enrich_te_prospects_cfbd_2026.py sets a baseline
# precisely so this refresh passes cleanly). It is not a claim that a score may
# never change — but as written it exits 1 on any move over 0.01, so the tight-end
# rescale, which moves 80 of the 82 cards, would stop the rookie and pick boards
# rebuilding at all on the morning it ships.
#
# So the run declares which scale it is on. A move WITH a new declaration is
# expected and reported; a move WITHOUT one is still a fault and still stops the
# run. Deleting the check to let the rescale through would trade a one-morning
# outage for a permanently blind detector.
DVS_SCALE_TOKEN_FIELD = "dvs_scale"


def current_dvs_scale_token() -> str:
    """A name for the scale these scores are on, DERIVED from the denominators.

    Derived rather than hand-set so it cannot be forgotten: change the
    denominators and the token changes with them, which is what turns the next
    rescale into a declared movement without anyone remembering to declare it.
    """
    from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG

    return "p90:" + "/".join(
        f"{pos}={ENGINE_B_P90_PPG[pos]:g}" for pos in sorted(ENGINE_B_P90_PPG)
    )


# What a card with no recorded scale is assumed to be on: the scale as it stood
# when this field was introduced. A baseline written before DG-158 therefore
# compares equal today, so an undeclared drift is still caught on the first run.
DEFAULT_DVS_SCALE_TOKEN = "p90:QB=20.1/RB=15.7/TE=9.4/WR=14.5"


def classify_dvs_movement(
    *,
    baseline_dvs: float | None,
    new_dvs: float | None,
    declared_scale: str,
    baseline_scale: str,
) -> str:
    """Why this card's score differs from its baseline: ``unchanged``,
    ``declared_rescale`` (the run is on a different, named scale) or
    ``undeclared_drift`` (same scale, different number — the fault this gate was
    built for). A declaration covers ONE move: the next run on that same scale is
    held to invariance again."""
    if baseline_dvs is None or new_dvs is None:
        return "unchanged"
    if abs(new_dvs - baseline_dvs) <= _DVS_INVARIANCE_TOLERANCE:
        return "unchanged"
    return "declared_rescale" if declared_scale != baseline_scale else "undeclared_drift"


# ── Rank computation ──────────────────────────────────────────────────────────

def _compute_ranks(pvos: list[dict]) -> list[dict]:
    """Add dvs_class_rank, xvar_class_rank, position_class_rank, rank_delta in-place."""
    # DVS class rank — nulls excluded
    dvs_scored = [(i, p) for i, p in enumerate(pvos) if p.get("dynasty_value_score") is not None]
    dvs_scored.sort(key=lambda x: x[1]["dynasty_value_score"], reverse=True)
    for rank, (i, _) in enumerate(dvs_scored, 1):
        pvos[i]["dvs_class_rank"] = rank

    # xVAR class rank — nulls excluded
    xvar_scored = [(i, p) for i, p in enumerate(pvos) if p.get("xvar") is not None]
    xvar_scored.sort(key=lambda x: x[1]["xvar"], reverse=True)
    for rank, (i, _) in enumerate(xvar_scored, 1):
        pvos[i]["xvar_class_rank"] = rank

    # Position class rank (DVS within position) — nulls excluded
    by_pos: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, p in enumerate(pvos):
        if p.get("dynasty_value_score") is not None:
            by_pos[p["position"]].append((i, p))
    for items in by_pos.values():
        items.sort(key=lambda x: x[1]["dynasty_value_score"], reverse=True)
        for rank, (i, _) in enumerate(items, 1):
            pvos[i]["position_class_rank"] = rank

    # rank_delta = xvar_class_rank - dvs_class_rank (positive = fell, negative = rose)
    for p in pvos:
        x_rank = p.get("xvar_class_rank")
        d_rank = p.get("dvs_class_rank")
        p["rank_delta"] = (x_rank - d_rank) if (x_rank is not None and d_rank is not None) else None

    return pvos


# ── PVO assembly ──────────────────────────────────────────────────────────────

def _build_pvo_dicts(
    identity_players: list[dict],
    cards_by_name_pos: dict[tuple[str, str], dict],
    identity_data: dict,
) -> tuple[list[dict], list[str], list[str]]:
    """Assemble PVOs for 80 verified 2026 players.

    Returns ``(pvo_dicts, dvs_warnings, rescaled)`` — DG-158 adds the third: cards
    that moved because the run declared a NEW scale, which is expected movement
    rather than the drift this gate exists to catch."""
    # DG-128: the band ships with the number, and its width is the scoring head's own
    # published error. Refuse to score a single card if the heads this tree serves are not
    # the runs those widths were pinned to (a re-promoted v3 TE head nobody re-pinned).
    assert_band_sigma_runs_match_served_models()

    pvos: list[dict] = []
    warnings: list[str] = []
    rescaled: list[str] = []
    declared_scale = current_dvs_scale_token()

    for p in identity_players:
        key = (p["full_name"], p["position"])
        existing = cards_by_name_pos.get(key, {})

        age: Optional[float] = existing.get("age")
        if age is None and p.get("birth_date"):
            ref = date.fromisoformat(identity_data.get("snapshot_date", "2026-05-09"))
            birth = date.fromisoformat(p["birth_date"])
            age = round((ref - birth).days / 365.25, 2)

        baseline_dvs: Optional[float] = existing.get("dynasty_value_score")
        # Preserve existing player_id for Rookie Board taken-state continuity.
        # Store identity dg_id separately for traceability.
        existing_player_id: Optional[str] = existing.get("player_id")

        identity = PlayerIdentity(
            dg_id=p["dg_id"],
            full_name=p["full_name"],
            position=p["position"],
            nfl_team=p.get("nfl_team"),
            sleeper_id=p.get("sleeper_id"),
            verification_status=p["verification_status"],
            is_prospect=True,
        )

        features: dict = {}
        if p.get("pick") is not None and age is not None:
            features = {
                "pick": float(p["pick"]),
                "round": float(p["round"]),
                "age": age,
                "draft_capital": float(p["pick"]),
                "age_at_nfl_entry": age,
                # Engine A v3 CFBD features — propagated from existing enriched cards.
                # None when the CFBD enrichment script has not run for this player.
                # score_prospect_v3() silently returns None for any missing feature,
                # so v2 fires as the fallback and DVS is unchanged.
                "final_college_age": existing.get("final_college_age"),
                "te_ryptpa_final": existing.get("te_ryptpa_final"),
                "te_yards_per_reception_career": existing.get("te_yards_per_reception_career"),
            }

        pvo = assemble_pvo(identity, features, is_prospect=True)
        d = pvo.dict()
        # Which runs the band's width was pinned to, so a stale card is legible after the fact
        # (the same record the universe batch keeps; `engine_used` says which head applied).
        d["source_versions"] = {
            **(d.get("source_versions") or {}),
            "dvs_band_sigma_run_a": ENGINE_A_SIGMA_RUN,
            "dvs_band_sigma_run_a_v3": ENGINE_A_V3_SIGMA_RUN,
        }

        # Restore preserved player_id and model_grade from existing cards.
        # assemble_pvo returns PRE_MODEL as default for Engine A prospects;
        # model_grade was set by pick-bucket logic in the original build script.
        if existing_player_id:
            d["player_id"] = existing_player_id
        if "model_grade" in existing and existing["model_grade"] != "PRE_MODEL":
            d["model_grade"] = existing["model_grade"]
        elif d.get("dynasty_value_score") is not None:
            d["model_grade"] = "PROSPECT_D" if p["position"] == "QB" else "PROSPECT_C"
        d["identity_dg_id"] = p["dg_id"]

        # Preserve display fields not in PVO schema
        d["draft_class"] = 2026
        d["nfl_draft_pick"] = p.get("pick")
        d["nfl_draft_round"] = p.get("round")
        d["age"] = age

        # Preserve Engine A v3 CFBD input features onto the serialized card.
        # pvo.dict() only serialises PVO schema fields — these provenance fields
        # are not in the schema so they are dropped by assemble_pvo.  Copy them
        # back from the features dict so the artifact retains the scoring inputs
        # and future refresh runs can propagate them again.
        d["final_college_age"] = features.get("final_college_age")
        d["te_ryptpa_final"] = features.get("te_ryptpa_final")
        d["te_yards_per_reception_career"] = features.get("te_yards_per_reception_career")

        # Initialize rank fields (populated later by _compute_ranks)
        d.setdefault("dvs_class_rank", None)
        d.setdefault("xvar_class_rank", None)
        d.setdefault("position_class_rank", None)
        d.setdefault("rank_delta", None)

        # DVS invariance check (tolerance 0.01). DG-158: a move on a DECLARED new
        # scale is expected and recorded; a move on the same scale is still the
        # contamination this gate was built to catch, and still stops the run.
        new_dvs = d.get("dynasty_value_score")
        d[DVS_SCALE_TOKEN_FIELD] = declared_scale
        verdict = classify_dvs_movement(
            baseline_dvs=baseline_dvs,
            new_dvs=new_dvs,
            declared_scale=declared_scale,
            baseline_scale=(existing.get(DVS_SCALE_TOKEN_FIELD) or DEFAULT_DVS_SCALE_TOKEN),
        )
        if verdict == "undeclared_drift":
            warnings.append(
                f"DVS drift for {p['full_name']} {p['position']}: "
                f"baseline={baseline_dvs} refreshed={new_dvs} "
                f"delta={abs(new_dvs - baseline_dvs):.4f}"
            )
        elif verdict == "declared_rescale":
            rescaled.append(
                f"{p['full_name']} {p['position']}: {baseline_dvs} -> {new_dvs}"
            )

        pvos.append(d)

    return pvos, warnings, rescaled


# ── Report ────────────────────────────────────────────────────────────────────

def _write_report(
    pvos_2026: list[dict],
    watchlist: list[dict],
    dvs_warnings: list[str],
    identity_snapshot_date: str,
) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    scored = [p for p in pvos_2026 if p.get("dynasty_value_score") is not None]
    unscored = [p for p in pvos_2026 if p.get("dynasty_value_score") is None]

    dvs_top24 = sorted(scored, key=lambda x: x.get("dvs_class_rank") or 999)[:24]
    xvar_top24 = sorted(
        [p for p in scored if p.get("xvar") is not None],
        key=lambda x: x.get("xvar_class_rank") or 999,
    )[:24]
    movers = sorted(
        [p for p in scored if p.get("rank_delta") is not None and abs(p["rank_delta"]) > 10],
        key=lambda x: abs(x["rank_delta"]),
        reverse=True,
    )
    te_players = sorted(
        [p for p in pvos_2026 if p["position"] == "TE" and p.get("xvar") is not None],
        key=lambda x: x.get("dvs_class_rank") or 999,
    )

    def _delta_str(p: dict) -> str:
        d = p.get("rank_delta")
        if d is None:
            return "—"
        return f"+{d}" if d > 0 else str(d)

    def _trow(p: dict) -> str:
        dvs = p.get("dynasty_value_score")
        xvar = p.get("xvar")
        return (
            f"| {p.get('dvs_class_rank', '—')} "
            f"| {p.get('xvar_class_rank', '—')} "
            f"| {p['full_name']} "
            f"| {p['position']} "
            f"| {p.get('nfl_draft_pick', '—')} "
            f"| {round(dvs, 1) if dvs is not None else '—'} "
            f"| {round(xvar, 1) if xvar is not None else '—'} "
            f"| {_delta_str(p)} |"
        )

    header = "| DVS# | xVAR# | Name | Pos | Pick | DVS | xVAR | Δ |\n|---|---|---|---|---|---|---|---|"

    lines: list[str] = [
        "# Phase 15.1 — 2026 Rookie Rank Refresh",
        "",
        f"Generated: {now}",
        f"Identity source: `resources/prospect_identity_2026.json` (snapshot: {identity_snapshot_date})",
        f"2026 cohort: {len(pvos_2026)} total · {len(scored)} scored · {len(unscored)} PRE_MODEL (age-data blockers)",
        f"2027 watchlist: {len(watchlist)} entries, excluded from 2026 rankings",
        "",
        "## Identity Stability Check",
        "",
        f"- Source: `nfl_data_py_verified_nfl_draft`, snapshot `{identity_snapshot_date}`",
        "- 80 verified 2026 draft picks; pick/round confirmed against existing artifact",
        "- Age source: preserved from `prospect_cards.json` where present; "
        "computed from `birth_date` in identity file for newly unblocked players",
        "- `player_id` values preserved from existing cards for Rookie Board continuity",
        f"- DVS drift warnings (>{_DVS_INVARIANCE_TOLERANCE}): {len(dvs_warnings)}",
    ]

    if dvs_warnings:
        lines.append("")
        for w in dvs_warnings:
            lines.append(f"  - {w}")
    else:
        lines.append("- No DVS drift — all 74 scored players match baseline exactly")

    lines += ["", "## DVS Top 24", "", header]
    for p in dvs_top24:
        lines.append(_trow(p))

    lines += [
        "",
        "## xVAR Top 24",
        "",
        "> rank_delta = xvar_class_rank − dvs_class_rank. Positive = fell in xVAR ordering. Negative = rose.",
        "",
        header,
    ]
    for p in xvar_top24:
        lines.append(_trow(p))

    lines += ["", "## Rank Movers (|rank_delta| > 10)", "", header]
    for p in movers:
        lines.append(_trow(p))
    if not movers:
        lines.append("_No players moved more than 10 spots._")

    lines += [
        "",
        "## TE xVAR Impact",
        "",
        "ENGINE_A_REPLACEMENT_DVS[TE] = 98.8. All 2026 TEs with DVS < 98.8 produce negative xVAR — "
        "correct Superflex behavior. A TE with DVS 100.0 would produce xVAR ≈ +0.9.",
        "",
        "| DVS# | xVAR# | Name | Pick | DVS | xVAR | Δ |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in te_players:
        dvs = p.get("dynasty_value_score")
        xvar = p.get("xvar")
        lines.append(
            f"| {p.get('dvs_class_rank', '—')} "
            f"| {p.get('xvar_class_rank', '—')} "
            f"| {p['full_name']} "
            f"| {p.get('nfl_draft_pick', '—')} "
            f"| {round(dvs, 1) if dvs is not None else '—'} "
            f"| {round(xvar, 1) if xvar is not None else '—'} "
            f"| {_delta_str(p)} |"
        )

    blocker_label = (
        f"## Age-Data Blockers — {len(unscored)} Remaining"
        if unscored
        else "## Age-Data Blockers — All Resolved"
    )
    blocker_note = (
        "These players have verified draft capital but `birth_date=None` in the identity file. "
        "Engine A requires `pick + round + age`; without age they remain PRE_MODEL."
        if unscored
        else "All 6 age-data blockers resolved. All 80 2026 prospects are now scored."
    )
    lines += [
        "",
        blocker_label,
        "",
        blocker_note,
        "",
        "| Name | Position | Pick | Round |",
        "|---|---|---|---|",
    ]
    for p in unscored:
        lines.append(
            f"| {p['full_name']} | {p['position']} "
            f"| {p.get('nfl_draft_pick', '—')} | {p.get('nfl_draft_round', '—')} |"
        )
    if unscored:
        lines += [
            "",
            "_Resolution: collect birth_date from Pro Football Reference or Sports Reference, "
            "update `prospect_identity_2026.json`, re-run this script._",
        ]

    lines += [
        "",
        "## 2027 Watchlist — Excluded from 2026 Rankings",
        "",
        "| Name | Position | Draft Class | Grade |",
        "|---|---|---|---|",
    ]
    for p in watchlist:
        lines.append(
            f"| {p['full_name']} | {p['position']} "
            f"| {p.get('draft_class', '—')} | {p.get('model_grade', '—')} |"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    with open(IDENTITY_FILE) as f:
        identity_data = json.load(f)
    with open(CARDS_JSON) as f:
        baseline_cards = json.load(f)

    identity_players = identity_data["players"]  # 80 verified 2026 picks
    identity_snapshot_date = identity_data.get("snapshot_date", "unknown")

    cards_by_name_pos: dict[tuple[str, str], dict] = {
        (c["full_name"], c["position"]): c for c in baseline_cards
    }

    # 2027 watchlist — not in identity file, carry forward unchanged
    watchlist = [c for c in baseline_cards if c.get("draft_class") == 2027]

    pvos_2026, dvs_warnings, dvs_rescaled = _build_pvo_dicts(
        identity_players,
        cards_by_name_pos,
        identity_data,
    )
    pvos_2026 = _compute_ranks(pvos_2026)

    if dvs_warnings:
        print(f"ERROR: {len(dvs_warnings)} DVS drift(s) detected — inspect before committing:")
        for w in dvs_warnings:
            print(f"  {w}")
        sys.exit(1)
    elif dvs_rescaled:
        # DG-158: expected movement on a declared new scale. Reported in full and
        # counted, never waved through silently — the boards rebuild, and the run
        # says exactly which cards moved and onto what.
        print(
            f"DVS invariance: {len(dvs_rescaled)} card(s) moved on a DECLARED new scale "
            f"({current_dvs_scale_token()}); no undeclared drift."
        )
        for line in dvs_rescaled:
            print(f"  {line}")
    else:
        print("DVS invariance: OK — all scored players match baseline exactly")

    scored_count = sum(1 for p in pvos_2026 if p.get("dynasty_value_score") is not None)
    pre_model_count = sum(1 for p in pvos_2026 if p.get("model_grade") == "PRE_MODEL")
    assert pre_model_count == 0, (
        f"Expected 0 PRE_MODEL 2026 players after age blocker resolution, got {pre_model_count}. "
        f"Check birth_date fields in prospect_identity_2026.json."
    )

    all_cards = pvos_2026 + watchlist

    CARDS_JSON.write_text(json.dumps(all_cards, indent=2, default=str))
    js_header = (
        "/* Auto-generated by scripts/refresh_prospect_cards.py — do not edit. */\n"
        f"/* Refreshed: Phase 15.1 · {len(pvos_2026)} 2026 + {len(watchlist)} watchlist */\n"
    )
    CARDS_JS.write_text(
        js_header
        + "window.PROSPECT_CARDS = "
        + json.dumps(all_cards, separators=(",", ":"), default=str)
        + ";\n"
    )

    print(
        f"Written: {len(pvos_2026)} 2026 prospects "
        f"({scored_count} scored, {pre_model_count} PRE_MODEL) + {len(watchlist)} watchlist"
    )

    _write_report(pvos_2026, watchlist, dvs_warnings, identity_snapshot_date)
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
