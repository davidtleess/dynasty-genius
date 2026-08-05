"""Read-only shape probe for the six zero-caller nflverse loaders.

Measures, per stream: column set, row count, season coverage, candidate identity
columns, and duplicate-group counts on a candidate grain. Writes JSON to stdout.
No writes to app/data. No repo mutation.
"""

from __future__ import annotations

import json
import sys
import traceback

import nflreadpy as nr
import polars as pl

SEASONS = [2023, 2024, 2025]

LOADERS = {
    "contracts": (nr.load_contracts, {}),
    "depth_charts": (nr.load_depth_charts, {"seasons": SEASONS}),
    "ff_opportunity": (nr.load_ff_opportunity, {"seasons": SEASONS}),
    "ff_rankings": (nr.load_ff_rankings, {}),
    "pfr_advstats_rec": (nr.load_pfr_advstats, {"seasons": SEASONS, "stat_type": "rec"}),
    "ftn_charting": (nr.load_ftn_charting, {"seasons": SEASONS}),
}

ID_CANDIDATES = (
    "gsis_id", "player_gsis_id", "pfr_player_id", "pfr_id", "player_id",
    "otc_id", "sleeper_id", "espn_id", "fantasypros_id", "nflverse_id",
    "player", "player_name", "full_name", "player_display_name", "name",
)


def probe(name, loader, kwargs):
    out = {"stream": name, "kwargs": {k: str(v) for k, v in kwargs.items()}}
    frame = loader(**kwargs)
    if not isinstance(frame, pl.DataFrame):
        frame = frame.collect() if hasattr(frame, "collect") else pl.DataFrame(frame)
    out["rows"] = frame.height
    out["n_columns"] = frame.width
    out["columns"] = list(frame.columns)
    out["dtypes"] = {c: str(t) for c, t in zip(frame.columns, frame.dtypes)}

    for season_col in ("season", "year"):
        if season_col in frame.columns:
            counts = (
                frame.group_by(season_col).len().sort(season_col).to_dicts()
            )
            out["season_coverage"] = {str(r[season_col]): r["len"] for r in counts}
            break

    present = [c for c in ID_CANDIDATES if c in frame.columns]
    out["identity_candidates"] = {
        c: {
            "non_null": int(frame[c].is_not_null().sum()),
            "distinct": int(frame[c].n_unique()),
        }
        for c in present
    }
    out["sample_row"] = frame.head(1).to_dicts()[0] if frame.height else None
    return out


def main():
    results = []
    only = sys.argv[1:] or list(LOADERS)
    for name in only:
        loader, kwargs = LOADERS[name]
        try:
            results.append(probe(name, loader, kwargs))
        except Exception as exc:  # noqa: BLE001 - probe reports, never masks
            results.append({
                "stream": name,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()[-1500:],
            })
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
