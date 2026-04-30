from pathlib import Path

import pandas as pd
import nfl_data_py as nfl

POSITIONS = {"WR", "RB", "TE", "QB"}
DRAFT_YEARS = list(range(2015, 2026))
SEASONAL_YEARS = list(range(2016, 2025))

BASE_DIR = Path(__file__).resolve().parents[3]
OUTPUT_PATH = BASE_DIR / "app" / "data" / "training" / "prospects_with_outcomes.csv"

OUTPUT_COLUMNS = [
    "gsis_id", "pfr_player_name", "position", "season", "pick", "round",
    "team", "college", "age",
    "y2_games", "y2_points", "y3_games", "y3_points", "y4_games", "y4_points",
    "total_games", "total_points", "y24_ppg", "low_sample_flag", "is_training",
]


def pivot_outcomes(gsis_id: str, draft_year: int, seasonal: pd.DataFrame) -> dict:
    player_seasons = seasonal[seasonal["player_id"] == gsis_id].set_index("season")
    result = {}
    for offset, label in [(1, "y2"), (2, "y3"), (3, "y4")]:
        year = draft_year + offset
        if year in player_seasons.index:
            result[f"{label}_games"] = player_seasons.loc[year, "games"] or 0
            result[f"{label}_points"] = player_seasons.loc[year, "fantasy_points_ppr"] or 0.0
        else:
            result[f"{label}_games"] = 0
            result[f"{label}_points"] = 0.0
    return result


def run() -> None:
    # --- Load data ---
    print("Loading draft picks...")
    draft_df = nfl.import_draft_picks(DRAFT_YEARS)
    draft_df = draft_df[draft_df["position"].isin(POSITIONS)].copy()
    print(f"  {len(draft_df)} rows after position filter")

    print("Loading seasonal data...")
    seasonal_df = nfl.import_seasonal_data(SEASONAL_YEARS, s_type="REG")
    seasonal_df = seasonal_df[seasonal_df["season_type"] == "REG"].copy()
    print(f"  {len(seasonal_df)} seasonal rows")

    # --- Step 1: Drop rows with null gsis_id ---
    before = len(draft_df)
    draft_df = draft_df[draft_df["gsis_id"].notna()]
    print(f"\nDropped {before - len(draft_df)} rows with null gsis_id ({len(draft_df)} remaining)")

    # --- Steps 2–4: Join and pivot Y2/Y3/Y4 outcomes ---
    print("Computing Y2/Y3/Y4 outcomes...")
    records = []
    for _, row in draft_df.iterrows():
        outcomes = pivot_outcomes(row["gsis_id"], int(row["season"]), seasonal_df)

        total_games = outcomes["y2_games"] + outcomes["y3_games"] + outcomes["y4_games"]
        total_points = outcomes["y2_points"] + outcomes["y3_points"] + outcomes["y4_points"]
        y24_ppg = round(total_points / total_games, 3) if total_games > 0 else 0.0

        records.append({
            "gsis_id":         row["gsis_id"],
            "pfr_player_name": row["pfr_player_name"],
            "position":        row["position"],
            "season":          int(row["season"]),
            "pick":            int(row["pick"]) if pd.notna(row["pick"]) else None,
            "round":           int(row["round"]) if pd.notna(row["round"]) else None,
            "team":            row["team"],
            "college":         row["college"],
            "age":             row["age"],
            **outcomes,
            "total_games":     total_games,
            "total_points":    round(total_points, 2),
            "y24_ppg":         y24_ppg,
            "low_sample_flag": 1 if total_games < 16 else 0,
            "is_training":     1 if int(row["season"]) <= 2022 else 0,
        })

    result_df = pd.DataFrame(records, columns=OUTPUT_COLUMNS)

    # --- Step 6: Write CSV ---
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nWrote {len(result_df)} rows to {OUTPUT_PATH}")

    # --- Step 7: Summary ---
    print("\n=== Summary ===")
    print(f"Total rows: {len(result_df)}")

    print("\nRows by position:")
    print(result_df["position"].value_counts().to_string())

    print("\nis_training distribution:")
    print(result_df["is_training"].value_counts().sort_index().to_string())

    bust_count = (result_df["y24_ppg"] == 0.0).sum()
    print(f"\nBust count (y24_ppg == 0): {bust_count}")

    print("\nFirst 5 rows:")
    print(result_df.head().to_string(index=False))


if __name__ == "__main__":
    run()
