"""Phase 19 W2 — Feature Pipeline Build-Out (Combine + Career Dominator).

Extends app/data/training/prospects_with_outcomes_v3.csv with position-specific
feature columns required by the Engine A v3 design spec (§3.1–3.5):

  1. NFL Combine metrics via nflreadpy.load_combine — height, weight, speed,
     athletic composites, and viability boolean flags.
  2. Career dominator ratings joined from prospects_with_outcomes_cfbd_partial.csv.
  3. Explicit missingness/provenance stubs (_missing="1") for all Required features
     not yet populatable from available local sources. No CFBD API calls are made;
     player-level CFBD stats (dominator_final, era flags, RYPTPA, SP+, etc.) are
     deferred to the next W2 enrichment session.

Feature coverage decisions (§3.1–3.5 source assignments):
  POPULATED:
    height, weight — nflreadpy Combine (all positions)
    wr_vertical_jump, wr_meets_athletic_floor — nflreadpy Combine
    wr_dominator_career — prospects_with_outcomes_cfbd_partial.csv join
    rb_speed_score, rb_weight, rb_3cone, rb_meets_athletic_floor — nflreadpy Combine
    rb_career_dominator — cfbd_partial join
    rb_age_at_draft — alias of age_at_draft (already computed in W1)
    te_weight, te_bmi, te_height_adj_speed_score — nflreadpy Combine
    te_career_dominator — cfbd_partial join
    te_age_at_draft — alias of age_at_draft (already computed in W1)

  STUBBED (_missing="1"):
    rb_10_yard_split — nflreadpy combine does not include split times
    rb_final_dominator, rb_scrimmage_ypg, rb_rec_ypg, rb_school_sp_plus — CFBD deferred
    rb_ras_composite — RAS adapter is mock-only in v1
    wr_breakout_age, wr_dominator_final, wr_market_share_yds,
      wr_rec_tds_per_game_final, wr_yards_per_reception_career,
      wr_early_declare — CFBD deferred
    wr_ras_composite — RAS adapter mock-only
    te_ryptpa_final, te_yards_per_reception_career, te_deep_yard_share — CFBD deferred
    te_ras_composite — RAS adapter mock-only

  ALREADY STUBBED (W1, left unchanged):
    covid_eligibility_flag, transfer_portal_flag, early_declare,
    final_college_age — CFBD deferred from W1 pipeline

Design references:
  - §3.2 Combine philosophy: meets_athletic_floor per Szekely et al. 2023 (arXiv:2303.05774)
  - §3.4 RB speed: Barnwell 2008 Speed Score = (wt×200) / (forty^4)
  - §3.5 TE height-adjusted speed: simplified PP HASS = raw_speed × (ht/76.0)

Does NOT change production model pkl files, latest.json, PVO scoring, or market overlays.
All generated artifacts remain gitignored.

Usage:
    .venv/bin/python3.14 scripts/build_w2_features.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.head_b_contract import (  # noqa: E402
    HEAD_B_PROHIBITED_COLUMNS,
    MARKET_PROHIBITED_COLUMNS,
    PFF_GRADE_PROHIBITED_COLUMNS,
)

# ── I/O paths ─────────────────────────────────────────────────────────────────

V3_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
CFBD_PARTIAL_CSV = ROOT / "app/data/training/prospects_with_outcomes_cfbd_partial.csv"

# ── Constants ─────────────────────────────────────────────────────────────────

# Combine data years to load (covers source training CSV seasons)
COMBINE_YEARS = list(range(2015, 2026))

# Barnwell 2008 Speed Score: (weight × 200) / (40-time ^ 4)
# Canonical scale: typical drafted RBs score 80–120, average ≈ 100
SPEED_SCORE_MULTIPLIER = 200

# TE height reference: 6'4" = 76 inches — average NFL TE height
# PP HASS approximation: multiply raw speed score by (ht / reference)
MEAN_TE_HEIGHT_INCHES = 76.0

# Szekely et al. 2023 (arXiv:2303.05774) proxy thresholds
WR_VERTICAL_FLOOR = 29.0   # inches — proxy for WR viability gate
RB_SPEED_SCORE_FLOOR = 80.0  # — proxy for RB viability gate

# ── Feature stub lists (base column names, no _missing/_source suffix) ────────
# Features that require CFBD API calls or RAS data not yet available locally.
# All will be written as _missing="1" stubs.

ALL_WR_FEATURE_STUBS: frozenset[str] = frozenset({
    "wr_breakout_age",
    "wr_dominator_final",
    "wr_market_share_yds",
    "wr_rec_tds_per_game_final",
    "wr_yards_per_reception_career",
    "wr_early_declare",
    "wr_ras_composite",
})

ALL_RB_FEATURE_STUBS: frozenset[str] = frozenset({
    "rb_10_yard_split",         # Not available in nflreadpy combine
    "rb_final_dominator",
    "rb_scrimmage_ypg",
    "rb_rec_ypg",
    "rb_school_sp_plus",
    "rb_ras_composite",
})

ALL_TE_FEATURE_STUBS: frozenset[str] = frozenset({
    "te_ryptpa_final",
    "te_yards_per_reception_career",
    "te_deep_yard_share",
    "te_ras_composite",
})


# ── Computational functions ───────────────────────────────────────────────────

def parse_height_inches(ht_str: str | None) -> Optional[float]:
    """Convert NFL Combine height string "F-I" to total inches."""
    if not ht_str or not isinstance(ht_str, str):
        return None
    parts = ht_str.strip().split("-")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0]) * 12.0 + float(parts[1])
    except (ValueError, TypeError):
        return None


def compute_rb_speed_score(weight_lbs: float | None, forty_time: float | None) -> Optional[float]:
    """Barnwell 2008 Speed Score = (weight × 200) / (40-time^4)."""
    if not weight_lbs or not forty_time:
        return None
    if weight_lbs <= 0 or forty_time <= 0:
        return None
    return round((weight_lbs * SPEED_SCORE_MULTIPLIER) / (forty_time ** 4), 2)


def compute_bmi(weight_lbs: float | None, height_inches: float | None) -> Optional[float]:
    """Body mass index: weight_lbs × 703 / height_inches²."""
    if not weight_lbs or not height_inches:
        return None
    if weight_lbs <= 0 or height_inches <= 0:
        return None
    return round(weight_lbs * 703.0 / (height_inches ** 2), 2)


def compute_te_height_adj_speed_score(
    weight_lbs: float | None,
    forty_time: float | None,
    height_inches: float | None,
) -> Optional[float]:
    """Height-adjusted Speed Score for TE (simplified PP HASS approximation).

    Multiplies Barnwell Speed Score by (height_inches / MEAN_TE_HEIGHT_INCHES).
    Taller TEs with equivalent raw speed score receive a higher adjusted score,
    reflecting the PlayerProfiler hypothesis that height-normalized athleticism
    is more predictive for TEs than raw speed.

    Note: the exact PlayerProfiler HASS formula is proprietary; this is a
    documented approximation using a linear height-normalization factor.
    """
    if height_inches is None or height_inches <= 0:
        return None
    raw = compute_rb_speed_score(weight_lbs, forty_time)
    if raw is None:
        return None
    return round(raw * (height_inches / MEAN_TE_HEIGHT_INCHES), 2)


def compute_wr_meets_athletic_floor(vertical_inches: float | None) -> Optional[bool]:
    """Szekely et al. 2023 WR viability gate proxy: vertical ≥ WR_VERTICAL_FLOOR."""
    if vertical_inches is None:
        return None
    return vertical_inches >= WR_VERTICAL_FLOOR


def compute_rb_meets_athletic_floor(speed_score: float | None) -> Optional[bool]:
    """Szekely et al. 2023 RB viability gate proxy: speed score ≥ RB_SPEED_SCORE_FLOOR."""
    if speed_score is None:
        return None
    return speed_score >= RB_SPEED_SCORE_FLOOR


# ── Lookup builders ───────────────────────────────────────────────────────────

def build_combine_lookup(combine_df: pd.DataFrame) -> dict[tuple[int, int], dict]:
    """Build (draft_year, overall_pick) → combine_row dict from nflreadpy data."""
    lookup: dict[tuple[int, int], dict] = {}
    for _, row in combine_df.iterrows():
        year_raw = row.get("draft_year")
        pick_raw = row.get("draft_ovr")
        if year_raw is None or pick_raw is None:
            continue
        try:
            if pd.isna(year_raw) or pd.isna(pick_raw):
                continue
        except (TypeError, ValueError):
            continue
        try:
            year = int(float(year_raw))
            pick = int(float(pick_raw))
        except (ValueError, TypeError):
            continue
        lookup[(year, pick)] = row.to_dict()
    return lookup


def build_dominator_lookup(csv_path: Path) -> dict[str, dict]:
    """Build gsis_id → cfbd_partial_row dict for career dominator join."""
    if not csv_path.exists():
        return {}
    lookup: dict[str, dict] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gsis_id = row.get("gsis_id", "").strip()
            if gsis_id:
                lookup[gsis_id] = row
    return lookup


# ── Row enrichment functions ──────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        if isinstance(val, float) and pd.isna(val):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _str_flag(val: Optional[float | str], source: str) -> tuple[str, str, str]:
    """Return (value_str, missing_flag, source_str) triple."""
    if val is None or val == "":
        return "", "1", ""
    return str(val), "0", source


def _bool_flag(val: Optional[bool], source: str) -> tuple[str, str, str]:
    if val is None:
        return "", "1", ""
    return ("1" if val else "0"), "0", source


def compute_combine_features(row: dict, combine_lookup: dict) -> dict[str, str]:
    """Compute Combine-derived features for a single row.

    Populates universal physical measurements (height, weight) and
    position-specific athletic features for WR, RB, and TE.
    Non-relevant position features are set to _missing="1" stubs.
    """
    try:
        season = int(row.get("season", 0))
    except (ValueError, TypeError):
        season = 0
    pick_raw = row.get("pick", "")
    position = row.get("position", "")
    pick = int(float(pick_raw)) if pick_raw and _safe_float(pick_raw) is not None else None

    combine = combine_lookup.get((season, pick)) if pick is not None else None

    result: dict[str, str] = {}

    # ── Universal physical measurements ──────────────────────────────────────
    ht_inches: Optional[float] = None
    wt_lbs: Optional[float] = None
    if combine:
        ht_inches = parse_height_inches(str(combine.get("ht") or ""))
        wt_lbs = _safe_float(combine.get("wt"))

    v, m, s = _str_flag(
        str(round(ht_inches, 1)) if ht_inches else None, "nfl_combine"
    )
    result.update({"height": v, "height_missing": m, "height_source": s})

    v, m, s = _str_flag(
        str(round(wt_lbs, 1)) if wt_lbs else None, "nfl_combine"
    )
    result.update({"weight": v, "weight_missing": m, "weight_source": s})

    # ── WR features ──────────────────────────────────────────────────────────
    if position == "WR":
        vertical: Optional[float] = None
        if combine:
            vertical = _safe_float(combine.get("vertical"))

        v, m, s = _str_flag(
            str(round(vertical, 2)) if vertical else None, "nfl_combine"
        )
        result.update({"wr_vertical_jump": v, "wr_vertical_jump_missing": m,
                        "wr_vertical_jump_source": s})

        meets = compute_wr_meets_athletic_floor(vertical)
        v, m, s = _bool_flag(meets, "nfl_combine_szekely2023_proxy")
        result.update({"wr_meets_athletic_floor": v, "wr_meets_athletic_floor_missing": m,
                        "wr_meets_athletic_floor_source": s})

    else:
        for col in ("wr_vertical_jump", "wr_meets_athletic_floor"):
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})

    # ── RB features ──────────────────────────────────────────────────────────
    if position == "RB":
        forty: Optional[float] = None
        rb_wt: Optional[float] = wt_lbs
        cone: Optional[float] = None
        if combine:
            forty = _safe_float(combine.get("forty"))
            cone = _safe_float(combine.get("cone"))

        speed_score = compute_rb_speed_score(rb_wt, forty)
        v, m, s = _str_flag(str(speed_score) if speed_score is not None else None, "combine_barnwell2008")
        result.update({"rb_speed_score": v, "rb_speed_score_missing": m,
                        "rb_speed_score_source": s})

        v, m, s = _str_flag(str(round(rb_wt, 1)) if rb_wt else None, "nfl_combine")
        result.update({"rb_weight": v, "rb_weight_missing": m, "rb_weight_source": s})

        v, m, s = _str_flag(str(round(cone, 3)) if cone else None, "nfl_combine")
        result.update({"rb_3cone": v, "rb_3cone_missing": m, "rb_3cone_source": s})

        meets = compute_rb_meets_athletic_floor(speed_score)
        v, m, s = _bool_flag(meets, "combine_szekely2023_proxy")
        result.update({"rb_meets_athletic_floor": v, "rb_meets_athletic_floor_missing": m,
                        "rb_meets_athletic_floor_source": s})

    else:
        for col in ("rb_speed_score", "rb_weight", "rb_3cone", "rb_meets_athletic_floor"):
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})

    # ── TE features ──────────────────────────────────────────────────────────
    if position == "TE":
        te_wt: Optional[float] = wt_lbs
        te_forty: Optional[float] = None
        if combine:
            te_forty = _safe_float(combine.get("forty"))

        bmi = compute_bmi(te_wt, ht_inches)
        hass = compute_te_height_adj_speed_score(te_wt, te_forty, ht_inches)

        v, m, s = _str_flag(str(round(te_wt, 1)) if te_wt else None, "nfl_combine")
        result.update({"te_weight": v, "te_weight_missing": m, "te_weight_source": s})

        v, m, s = _str_flag(str(bmi) if bmi is not None else None, "nfl_combine_derived")
        result.update({"te_bmi": v, "te_bmi_missing": m, "te_bmi_source": s})

        v, m, s = _str_flag(str(hass) if hass is not None else None,
                             "combine_pp_hass_approx")
        result.update({"te_height_adj_speed_score": v,
                        "te_height_adj_speed_score_missing": m,
                        "te_height_adj_speed_score_source": s})

    else:
        for col in ("te_weight", "te_bmi", "te_height_adj_speed_score"):
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})

    return result


def compute_dominator_features(row: dict, dominator_lookup: dict) -> dict[str, str]:
    """Join career dominator rating from cfbd_partial by gsis_id."""
    gsis_id = row.get("gsis_id", "")
    position = row.get("position", "")
    partial = dominator_lookup.get(gsis_id)

    result: dict[str, str] = {}

    dom_raw = partial.get("dominator_rating", "") if partial else ""
    dom_source = partial.get("source_dominator_rating", "cfbd") if partial else ""
    dom_val = dom_raw if dom_raw and dom_raw.strip() else None

    if position == "WR":
        v, m, s = _str_flag(dom_val, dom_source or "cfbd")
        result.update({"wr_dominator_career": v, "wr_dominator_career_missing": m,
                        "wr_dominator_career_source": s})
    elif position == "RB":
        v, m, s = _str_flag(dom_val, dom_source or "cfbd")
        result.update({"rb_career_dominator": v, "rb_career_dominator_missing": m,
                        "rb_career_dominator_source": s})
    elif position == "TE":
        v, m, s = _str_flag(dom_val, dom_source or "cfbd")
        result.update({"te_career_dominator": v, "te_career_dominator_missing": m,
                        "te_career_dominator_source": s})

    # Non-applicable positions: add stubs for completeness
    if position != "WR":
        result.setdefault("wr_dominator_career", "")
        result.setdefault("wr_dominator_career_missing", "1")
        result.setdefault("wr_dominator_career_source", "")
    if position != "RB":
        result.setdefault("rb_career_dominator", "")
        result.setdefault("rb_career_dominator_missing", "1")
        result.setdefault("rb_career_dominator_source", "")
    if position != "TE":
        result.setdefault("te_career_dominator", "")
        result.setdefault("te_career_dominator_missing", "1")
        result.setdefault("te_career_dominator_source", "")

    return result


def compute_age_position_features(row: dict) -> dict[str, str]:
    """Populate position-specific age aliases from the universal age_at_draft column.

    rb_age_at_draft and te_age_at_draft are contract-required per-position features
    that mirror the universal age_at_draft value. They are listed separately in the
    contract to allow position-specific coefficient estimation in the bake-off.

    All rows receive both columns (stubs for non-applicable positions) so the
    CSV schema is uniform across all position rows.
    """
    position = row.get("position", "")
    age_val = row.get("age_at_draft", "")
    age_missing = "0" if age_val and age_val.strip() else "1"
    age_source = row.get("age_at_draft_source", "nfl_data_py" if age_missing == "0" else "")

    result: dict[str, str] = {}

    if position == "RB":
        result.update({
            "rb_age_at_draft": age_val,
            "rb_age_at_draft_missing": age_missing,
            "rb_age_at_draft_source": age_source,
            "te_age_at_draft": "",
            "te_age_at_draft_missing": "1",
            "te_age_at_draft_source": "",
        })
    elif position == "TE":
        result.update({
            "rb_age_at_draft": "",
            "rb_age_at_draft_missing": "1",
            "rb_age_at_draft_source": "",
            "te_age_at_draft": age_val,
            "te_age_at_draft_missing": age_missing,
            "te_age_at_draft_source": age_source,
        })
    else:
        # WR, QB: both are not applicable — add as stubs for schema uniformity
        result.update({
            "rb_age_at_draft": "",
            "rb_age_at_draft_missing": "1",
            "rb_age_at_draft_source": "",
            "te_age_at_draft": "",
            "te_age_at_draft_missing": "1",
            "te_age_at_draft_source": "",
        })
    return result


def _make_stub(col: str) -> dict[str, str]:
    return {col: "", f"{col}_missing": "1", f"{col}_source": ""}


def compute_all_stubs(position: str) -> dict[str, str]:
    """Build _missing='1' stubs for all CFBD-deferred Required features."""
    result: dict[str, str] = {}
    all_stubs = ALL_WR_FEATURE_STUBS | ALL_RB_FEATURE_STUBS | ALL_TE_FEATURE_STUBS
    for col in all_stubs:
        result.update(_make_stub(col))
    return result


# ── Leakage governance guard ──────────────────────────────────────────────────

def _assert_no_leakage() -> None:
    """Verify at startup that no stub column name violates leakage contracts."""
    all_stubs = ALL_WR_FEATURE_STUBS | ALL_RB_FEATURE_STUBS | ALL_TE_FEATURE_STUBS
    for col in all_stubs:
        assert col not in HEAD_B_PROHIBITED_COLUMNS, (
            f"GOVERNANCE: stub column '{col}' is in HEAD_B_PROHIBITED_COLUMNS"
        )
        assert col not in MARKET_PROHIBITED_COLUMNS, (
            f"GOVERNANCE: stub column '{col}' is in MARKET_PROHIBITED_COLUMNS"
        )
        assert col not in PFF_GRADE_PROHIBITED_COLUMNS, (
            f"GOVERNANCE: stub column '{col}' is in PFF_GRADE_PROHIBITED_COLUMNS"
        )


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    _assert_no_leakage()

    if not V3_CSV.exists():
        raise FileNotFoundError(
            f"V3 CSV not found: {V3_CSV}\n"
            "Run scripts/build_head_b_targets.py first (W1 must complete before W2)."
        )

    print("Phase 19 W2 — Feature Pipeline Build-Out")
    print(f"  Input:  {V3_CSV}")
    print(f"  Partial: {CFBD_PARTIAL_CSV}")

    # ── Source provenance ────────────────────────────────────────────────────
    source_sha256 = hashlib.sha256(V3_CSV.read_bytes()).hexdigest()
    with V3_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"  Loaded {len(rows)} rows  sha256=...{source_sha256[-8:]}")

    # ── Load Combine data ────────────────────────────────────────────────────
    print(f"\n  Loading Combine data for years {COMBINE_YEARS[0]}–{COMBINE_YEARS[-1]}...")
    try:
        import nflreadpy
        combine_raw = nflreadpy.load_combine(COMBINE_YEARS)
        combine_df = combine_raw.to_pandas() if hasattr(combine_raw, "to_pandas") else pd.DataFrame(combine_raw)
    except Exception as exc:
        print(f"  [WARN] Could not load Combine data: {exc}")
        print("  Continuing with all Combine features as _missing='1' stubs.")
        combine_df = pd.DataFrame()

    combine_lookup = build_combine_lookup(combine_df)
    print(f"  Combine lookup: {len(combine_lookup)} entries")

    # ── Load career dominator lookup ─────────────────────────────────────────
    dominator_lookup = build_dominator_lookup(CFBD_PARTIAL_CSV)
    print(f"  Dominator lookup: {len(dominator_lookup)} entries")

    # ── Enrich rows ──────────────────────────────────────────────────────────
    print("\n  Enriching rows...")
    n_combine_hit = 0
    n_dominator_hit = 0
    position_counts: dict[str, int] = {}

    for row in rows:
        position = row.get("position", "")
        position_counts[position] = position_counts.get(position, 0) + 1

        # Combine features
        combine_feats = compute_combine_features(row, combine_lookup)
        if combine_feats.get("height_missing") == "0":
            n_combine_hit += 1
        row.update(combine_feats)

        # Age position aliases (RB, TE)
        row.update(compute_age_position_features(row))

        # Career dominator join
        dom_feats = compute_dominator_features(row, dominator_lookup)
        # Check if we got a populated dominator for this position
        pos_col = {"WR": "wr_dominator_career_missing",
                   "RB": "rb_career_dominator_missing",
                   "TE": "te_career_dominator_missing"}.get(position, "")
        if pos_col and dom_feats.get(pos_col) == "0":
            n_dominator_hit += 1
        row.update(dom_feats)

        # CFBD-deferred stubs
        stubs = compute_all_stubs(position)
        for k, v in stubs.items():
            if k not in row:
                row[k] = v

    # ── Coverage summary ─────────────────────────────────────────────────────
    total = len(rows)
    print(f"\n  Position breakdown: {dict(sorted(position_counts.items()))}")
    print(f"  Combine hit (height populated): {n_combine_hit}/{total} "
          f"({100 * n_combine_hit / total:.1f}%)")
    print(f"  Dominator hit (career populated for own position): "
          f"{n_dominator_hit}/{total} ({100 * n_dominator_hit / total:.1f}%)")

    # ── Write enriched CSV ───────────────────────────────────────────────────
    if rows:
        fieldnames = list(rows[0].keys())
        with V3_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    print(f"\n  Written: {V3_CSV}")
    print(f"  Columns: {len(rows[0]) if rows else 0}")

    # ── Governance count ─────────────────────────────────────────────────────
    new_sha256 = hashlib.sha256(V3_CSV.read_bytes()).hexdigest()
    print(f"\n  New sha256=...{new_sha256[-8:]}")
    print("  promotion_decision: NOT_APPLICABLE (W2 data pipeline only)")


if __name__ == "__main__":
    main()
