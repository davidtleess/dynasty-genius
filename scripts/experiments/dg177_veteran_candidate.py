#!/usr/bin/env python3
"""DG-177 — veteran forecast candidate, evaluated with information available at the time.

REPORT-ONLY EXPERIMENT. Reads the tracked training CSV, the served Engine B manifest and
pickles (read-only, for their feature lists and version strings) and the nflverse
warehouse (read-only). Writes ONLY a new run-scoped directory inside this worktree.
Nothing here trains, promotes, publishes or restarts anything.

The question the ticket asks: do additional football inputs earn their effect on a
veteran forecast once every transform is fitted inside the training window and every
training label was known at the cutoff? DG-162 answered "three columns" under a stricter
walk-forward than necessary; this runner reproduces that table under DG-162's rule, then
asks the question again under the honest rule and with one justified feature family.

Arms, all fitted with the deployed recipe on identical test rows:
  ppg_only                             ppg_t
  recent_production_3col               ppg_t, games_t, age            (DG-162's baseline)
  deployed_recipe                      the served pickle's feature list for the position
  recent_production_3col+opportunity   baseline + raw realized opportunity per game
  deployed_recipe+opportunity          served list + raw realized opportunity per game
  exploratory:*+xfp                    the third-party expected-points columns; labelled
                                       exploratory because their fit window is not
                                       point-in-time verifiable (see opportunity_features)

Usage (from the worktree root):
    .venv/bin/python scripts/experiments/dg177_veteran_candidate.py [--draws 2000] [--seed N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import platform
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval.opportunity_features import (  # noqa: E402
    EXPLORATORY_XFP_FEATURES,
    RAW_OPPORTUNITY_FEATURES,
    SOURCE_TABLE,
    join_coverage,
    load_opportunity_season_features,
)
from src.dynasty_genius.eval.veteran_candidate import (  # noqa: E402
    CUTOFF_RULES,
    DEPLOYED_RECIPE,
    LABEL_WINDOW_SEASONS,
    run_candidate_evaluation,
    write_run_artifact,
)
from src.dynasty_genius.models.engine_b_contract import OUTCOME_COLUMN  # noqa: E402

# ── arms ──────────────────────────────────────────────────────────────────────
ARM_PPG_ONLY = "ppg_only"
ARM_RECENT_3 = "recent_production_3col"
ARM_DEPLOYED = "deployed_recipe"
ARM_RECENT_3_OPP = "recent_production_3col+opportunity"
ARM_DEPLOYED_OPP = "deployed_recipe+opportunity"
ARM_RECENT_3_XFP = "exploratory:recent_production_3col+xfp"
ARM_DEPLOYED_XFP = "exploratory:deployed_recipe+xfp"
EXPLORATORY_ARMS: frozenset[str] = frozenset({ARM_RECENT_3_XFP, ARM_DEPLOYED_XFP})

#: DG-162's "simple recent-production baseline": what he scored, how often, how old.
RECENT_PRODUCTION_FEATURES: list[str] = ["ppg_t", "games_t", "age"]

#: Two references, two questions: does the served set beat recent production, and does
#: the family earn its place OVER the served set (not merely over three columns).
REFERENCE_ARMS = [ARM_RECENT_3, ARM_DEPLOYED]
DEFAULT_TEST_SEASONS = [2020, 2021, 2022, 2023]
PRIMARY_RULE = "labels_known_at_cutoff"
REPRODUCTION_RULE = "window_closed_before_test"

#: DG-162 §1 as published (tickets/DG-162-what-the-model-actually-reads.md), pooled over
#: the same walk-forward under the strict rule. Kept here ONLY to be compared against a
#: fresh run; nothing reads these numbers as an input.
DG162_PUBLISHED: dict[str, dict[str, float]] = {
    "QB": {"n": 95, "ppg_only_r2": 0.320, "deployed_r2": 0.383, "delta_r2_full_vs_3col": 0.030},
    "RB": {"n": 284, "ppg_only_r2": 0.572, "deployed_r2": 0.600, "delta_r2_full_vs_3col": -0.000},
    "WR": {"n": 456, "ppg_only_r2": 0.623, "deployed_r2": 0.661, "delta_r2_full_vs_3col": 0.010},
    "TE": {"n": 244, "ppg_only_r2": 0.588, "deployed_r2": 0.605, "delta_r2_full_vs_3col": 0.008},
}

# ── paths (read-only inputs) ──────────────────────────────────────────────────
DATASET_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
MANIFEST_PATH = ROOT / "app" / "data" / "models" / "engine_b" / "v2_manifest.json"
WAREHOUSE_PATH = ROOT / "app" / "data" / "nflverse_usage.db"
RUNS_ROOT = ROOT / "runs"


def build_arms(served_features: list[str]) -> dict[str, list[str]]:
    """The arms for one position, given that position's served feature list."""
    served = list(served_features)
    return {
        ARM_PPG_ONLY: ["ppg_t"],
        ARM_RECENT_3: list(RECENT_PRODUCTION_FEATURES),
        ARM_DEPLOYED: served,
        ARM_RECENT_3_OPP: [*RECENT_PRODUCTION_FEATURES, *RAW_OPPORTUNITY_FEATURES],
        ARM_DEPLOYED_OPP: [*served, *RAW_OPPORTUNITY_FEATURES],
        ARM_RECENT_3_XFP: [*RECENT_PRODUCTION_FEATURES, *EXPLORATORY_XFP_FEATURES],
        ARM_DEPLOYED_XFP: [*served, *EXPLORATORY_XFP_FEATURES],
    }


def served_feature_lists(manifest_path: Path, root: Path) -> dict[str, dict[str, Any]]:
    """Position -> the served pickle's feature list, version string and manifest path.

    The pickles are the only authority on what the product reads; the contract's
    per-position sets omit the optional NGS columns the served models actually carry.
    """
    manifest = json.loads(Path(manifest_path).read_text())
    out: dict[str, dict[str, Any]] = {}
    for position, rel in manifest.items():
        with open(Path(root) / rel, "rb") as fh:
            bundle = pickle.load(fh)
        out[position] = {
            "features": list(bundle["features"]),
            "version": bundle.get("version"),
            "path": rel,
        }
    return out


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_provenance(files: dict[str, Path], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Name the actual bytes and library versions a run read. Refuses a missing file."""
    import scipy
    import sklearn

    entries: dict[str, Any] = {}
    for label, path in files.items():
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"provenance input {label!r} is missing: {path}")
        stat = path.stat()
        entries[label] = {
            "path": str(path),
            "resolved": str(path.resolve()),
            "bytes": int(stat.st_size),
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "sha256": _sha256(path),
        }
    return {
        "files": entries,
        "versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        **(extra or {}),
    }


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unavailable"


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if np.isnan(value):
            return "nan"
        return f"{value:.{digits}f}"
    return str(value)


def _fmt_delta(entry: dict[str, Any]) -> str:
    lo, hi = entry["ci90"]
    return f"{entry['point']:+.3f} [{lo:+.3f}, {hi:+.3f}]"


def render_report(results: dict[str, Any], provenance: dict[str, Any]) -> str:
    """A markdown report that prints every fold and every arm, losers and skips included."""
    cfg = results["config"]
    lines: list[str] = []
    lines.append("# DG-177 — veteran forecast candidate, evaluated at the cutoff\n")
    lines.append(f"Rule: `{cfg['rule']}` · reference arms: {cfg['reference_arms']} · "
                 f"test seasons: {cfg.get('test_seasons')} · git: `{provenance.get('git_head', '—')}`\n")
    lines.append("Deltas are metric(arm) − metric(reference) on identical rows, 90% interval from a "
                 "bootstrap that resamples players. RMSE lower is better; r², Spearman and top-k "
                 "overlap higher is better.\n")
    for position, block in results["positions"].items():
        lines.append(f"\n## {position} (k = {block.get('k')})\n")
        lines.append("| test season | train seasons | train rows / players | test rows / players | status |")
        lines.append("|---|---|---|---|---|")
        for fold in block["folds"]:
            status = "evaluated" if fold["skipped_reason"] is None else f"skipped — {fold['skipped_reason']}"
            lines.append(
                f"| {fold['test_season']} | {fold['train_seasons']} | "
                f"{fold['n_train']} / {fold['n_train_players']} | "
                f"{fold['n_test']} / {fold['n_test_players']} | {status} |"
            )
        if not block.get("pooled"):
            lines.append("\nNo fold was evaluable for this position.\n")
            continue
        lines.append("\n**Pooled over evaluated folds**\n")
        lines.append("| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for arm, m in block["pooled"].items():
            lines.append(
                f"| `{arm}` | {m['n']} | {_fmt(m['rmse'])} | {_fmt(m['mae'])} | {_fmt(m['r2'])} | "
                f"{_fmt(m['spearman'])} | {_fmt(m['topk_overlap'])} |"
            )
        for reference in cfg["reference_arms"]:
            pooled_deltas = block["deltas"].get(reference, {})
            lines.append(f"\n**Difference vs `{reference}`, pooled**\n")
            lines.append("| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |")
            lines.append("|---|---|---|---|---|---:|")
            for arm, d in pooled_deltas.items():
                lines.append(
                    f"| `{arm}` | {_fmt_delta(d['delta_rmse'])} | {_fmt_delta(d['delta_r2'])} | "
                    f"{_fmt_delta(d['delta_spearman'])} | {_fmt_delta(d['delta_topk_overlap'])} | "
                    f"{d.get('clusters', '—')} |"
                )
            arms = sorted(pooled_deltas)
            lines.append(f"\n**Per fold, Δr² vs `{reference}` [90%]**\n")
            lines.append("| test season | " + " | ".join(f"`{a}`" for a in arms) + " |")
            lines.append("|---|" + "---|" * len(arms))
            for fold in block["folds"]:
                if fold["skipped_reason"] is not None:
                    lines.append(f"| {fold['test_season']} | " + " | ".join("skipped" for _ in arms) + " |")
                    continue
                fold_deltas = fold["deltas"].get(reference, {})
                cells = [
                    _fmt_delta(fold_deltas[a]["delta_r2"]) if a in fold_deltas else "—" for a in arms
                ]
                lines.append(f"| {fold['test_season']} | " + " | ".join(cells) + " |")
    if results.get("reproduction_dg162"):
        rep = results["reproduction_dg162"]
        lines.append("\n## Reproduction of DG-162 §1 under its stricter rule\n")
        lines.append(f"Rule `{rep['rule']}`; DG-162's published values from `{rep['source']}`.\n")
        lines.append("| pos | n (this run / DG-162) | ppg_only r² (this / DG-162) | deployed r² (this / DG-162) | Δr² deployed−3col (this / DG-162) |")
        lines.append("|---|---|---|---|---|")
        for pos, row in rep["by_position"].items():
            lines.append(
                f"| {pos} | {row['n']} / {row['published_n']} | {_fmt(row['ppg_only_r2'])} / {_fmt(row['published_ppg_only_r2'])} | "
                f"{_fmt(row['deployed_r2'])} / {_fmt(row['published_deployed_r2'])} | "
                f"{_fmt(row['delta_r2_deployed_vs_3col'])} / {_fmt(row['published_delta_r2'])} |"
            )
    if results.get("coverage"):
        lines.append("\n## Opportunity family coverage (training rows joined to a season aggregate)\n")
        lines.append("| pos | " + " | ".join(results["coverage"]["seasons"]) + " |")
        lines.append("|---|" + "---|" * len(results["coverage"]["seasons"]))
        for pos, per in results["coverage"]["by_position"].items():
            lines.append(f"| {pos} | " + " | ".join(
                f"{per[s]['joined']}/{per[s]['rows']}" if s in per else "—" for s in results["coverage"]["seasons"]
            ) + " |")
    lines.append("\n## Provenance\n")
    for label, entry in provenance.get("files", {}).items():
        lines.append(f"- `{label}`: `{entry['path']}` · {entry['bytes']} bytes · modified {entry['modified_utc']} · sha256 `{entry['sha256'][:16]}…`")
    for key in ("git_head", "git_branch", "worktree", "warehouse", "served_models", "notes"):
        if key in provenance:
            lines.append(f"- {key}: `{json.dumps(provenance[key], default=str)}`")
    lines.append(f"- versions: `{json.dumps(provenance.get('versions', {}))}`")
    return "\n".join(lines) + "\n"


# ── the run ───────────────────────────────────────────────────────────────────

def _warehouse_facts(conn: sqlite3.Connection) -> dict[str, Any]:
    rows, = conn.execute(f"SELECT count(*) FROM {SOURCE_TABLE}").fetchone()
    seasons = [r[0] for r in conn.execute(
        f"SELECT DISTINCT season FROM {SOURCE_TABLE} ORDER BY season").fetchall()]
    ingested = conn.execute(
        f"SELECT min(season_ingested), max(season_ingested) FROM {SOURCE_TABLE}").fetchone()
    eras = [r[0] for r in conn.execute(
        f"SELECT DISTINCT source_era FROM {SOURCE_TABLE}").fetchall()]
    return {"table": SOURCE_TABLE, "rows": int(rows), "seasons": seasons,
            "season_ingested_range": list(ingested), "source_era": eras}


def _evaluate_all_positions(
    df: pd.DataFrame, served: dict[str, dict[str, Any]], *, rule: str, test_seasons: list[int],
    draws: int, seed: int, min_train_rows: int, k_by_position: dict[str, int],
) -> tuple[dict[str, Any], pd.DataFrame]:
    positions: dict[str, Any] = {}
    frames: list[pd.DataFrame] = []
    arms_by_position: dict[str, dict[str, list[str]]] = {}
    config: dict[str, Any] | None = None
    for position in ("QB", "RB", "WR", "TE"):
        if position not in served:
            continue
        arms = build_arms(served[position]["features"])
        arms_by_position[position] = arms
        result, predictions = run_candidate_evaluation(
            df[df["position"] == position], arms=arms, test_seasons=test_seasons,
            reference_arms=REFERENCE_ARMS, k_by_position=k_by_position, rule=rule,
            min_train_rows=min_train_rows, draws=draws, seed=seed,
        )
        positions.update(result["positions"])
        frames.append(predictions)
        config = result["config"]
    assert config is not None
    config = {**config, "arms": "see arms_by_position", "arms_by_position": arms_by_position,
              "exploratory_arms": sorted(EXPLORATORY_ARMS)}
    return {"config": config, "positions": positions}, pd.concat(frames, ignore_index=True)


def _reproduction_table(strict: dict[str, Any]) -> dict[str, Any]:
    by_position: dict[str, Any] = {}
    for pos, block in strict["positions"].items():
        pooled = block.get("pooled") or {}
        pub = DG162_PUBLISHED.get(pos, {})
        r2 = lambda arm: pooled.get(arm, {}).get("r2")  # noqa: E731
        d = block.get("deltas", {}).get(ARM_RECENT_3, {}).get(ARM_DEPLOYED, {}).get("delta_r2", {})
        by_position[pos] = {
            "n": pooled.get(ARM_PPG_ONLY, {}).get("n"),
            "published_n": pub.get("n"),
            "ppg_only_r2": r2(ARM_PPG_ONLY),
            "published_ppg_only_r2": pub.get("ppg_only_r2"),
            "deployed_r2": r2(ARM_DEPLOYED),
            "published_deployed_r2": pub.get("deployed_r2"),
            "delta_r2_deployed_vs_3col": d.get("point"),
            "delta_r2_deployed_vs_3col_ci90": d.get("ci90"),
            "published_delta_r2": pub.get("delta_r2_full_vs_3col"),
        }
    return {
        "rule": REPRODUCTION_RULE,
        "source": "~/dg-build/tickets/DG-162-what-the-model-actually-reads.md §1",
        "by_position": by_position,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rule", default=PRIMARY_RULE, choices=CUTOFF_RULES)
    parser.add_argument("--skip-reproduction", action="store_true",
                        help="do not also run DG-162's stricter rule for the reproduction table")
    parser.add_argument("--test-seasons", type=int, nargs="+", default=DEFAULT_TEST_SEASONS)
    parser.add_argument("--min-train-rows", type=int, default=60)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--out-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args(argv)

    from src.dynasty_genius.eval.backtest_harness import PRIMARY_NDCG_K

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / run_id / "dg177_veteran_candidate"

    df = pd.read_csv(DATASET_PATH, low_memory=False)
    served = served_feature_lists(MANIFEST_PATH, ROOT)
    feature_seasons = sorted(int(s) for s in df["feature_season"].unique())

    warehouse_mtime_at_open = WAREHOUSE_PATH.resolve().stat().st_mtime
    conn = sqlite3.connect(f"file:{WAREHOUSE_PATH.resolve()}?mode=ro", uri=True)
    try:
        warehouse = _warehouse_facts(conn)
        opportunity = load_opportunity_season_features(conn, feature_seasons)
    finally:
        conn.close()
    coverage = join_coverage(df, opportunity)
    merged = df.merge(opportunity, on=["player_id", "feature_season"], how="left", validate="m:1")
    if len(merged) != len(df):
        raise RuntimeError(f"opportunity join changed the row count: {len(df)} -> {len(merged)}")

    print(f"rows {len(df)} · feature seasons {feature_seasons} · opportunity rows {len(opportunity)}")
    primary, predictions = _evaluate_all_positions(
        merged, served, rule=args.rule, test_seasons=args.test_seasons, draws=args.draws,
        seed=args.seed, min_train_rows=args.min_train_rows, k_by_position=dict(PRIMARY_NDCG_K),
    )
    results: dict[str, Any] = {
        **primary,
        "coverage": {"seasons": [str(s) for s in feature_seasons], "by_position": coverage},
        "outcome": OUTCOME_COLUMN,
        "label_window_seasons": LABEL_WINDOW_SEASONS,
        "recipe": DEPLOYED_RECIPE,
        "run_id": run_id,
        "started_utc": started.isoformat(),
    }
    if not args.skip_reproduction and args.rule != REPRODUCTION_RULE:
        strict, _ = _evaluate_all_positions(
            merged, served, rule=REPRODUCTION_RULE, test_seasons=args.test_seasons, draws=args.draws,
            seed=args.seed, min_train_rows=args.min_train_rows, k_by_position=dict(PRIMARY_NDCG_K),
        )
        results["reproduction_dg162"] = _reproduction_table(strict)
        results["strict_rule_full_results"] = strict["positions"]

    files = {"training_csv": DATASET_PATH, "engine_b_manifest": MANIFEST_PATH}
    for position, info in served.items():
        files[f"served_{position.lower()}_pickle"] = ROOT / info["path"]
    provenance = collect_provenance(files, extra={
        "git_head": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty_entries": len([line for line in _git("status", "--porcelain").splitlines() if line.strip()]),
        "worktree": json.loads((ROOT / ".dg-worktree.json").read_text()) if (ROOT / ".dg-worktree.json").exists() else None,
        "warehouse": {
            "path": str(WAREHOUSE_PATH), "resolved": str(WAREHOUSE_PATH.resolve()),
            "bytes": int(WAREHOUSE_PATH.resolve().stat().st_size),
            "modified_utc": datetime.fromtimestamp(WAREHOUSE_PATH.resolve().stat().st_mtime, tz=timezone.utc).isoformat(),
            "sha256": "not computed — multi-GB store; identified by path, size, mtime and table facts",
            "modified_at_open_utc": datetime.fromtimestamp(warehouse_mtime_at_open, tz=timezone.utc).isoformat(),
            "changed_during_run": bool(WAREHOUSE_PATH.resolve().stat().st_mtime != warehouse_mtime_at_open),
            **warehouse,
        },
        "served_models": {p: {"version": i["version"], "path": i["path"]} for p, i in served.items()},
        "notes": [
            "xfp_* columns are nflverse ffopportunity expected points, a third-party fitted "
            "model. Its documentation (https://ffopportunity.ffverse.com/, read 2026-09-06) says "
            "it \"uses xgboost and tidymodels trained on public nflverse data from 2006-2020\"; "
            "the model version behind each warehouse row is not recorded. That window overlaps "
            "feature seasons 2018-2020 at play level, so arms using them are labelled "
            "exploratory and are not point-in-time evidence.",
            "opp_* columns are raw per-game counts from the feature season only.",
        ],
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    })
    report = render_report(results, provenance)
    written = write_run_artifact(out_dir, results, predictions, provenance=provenance, report_md=report)
    print(f"wrote {written} to {out_dir}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
