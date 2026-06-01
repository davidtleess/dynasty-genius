#!/usr/bin/env python3.14
"""Subpopulation / Axis-of-Edge Study CLI — Task 8.

Loads an existing G3 backtest run (`market_comparison_*.json` + `predictions_*.csv`)
plus the DynastyProcess `db_playerids` id-map, enriches each market row with
`age_at_feature_season` (joined by `(player_id, feature_season)`) and `draft_year`
(joined by `gsis_id == player_id`), runs the pure subpopulation pipeline, and writes
`subpopulation_landscape_{latest,<run>}.{json,md}`.

DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim. Inputs are read-only;
the write step posture-checks the full payload (ledger + per-slice aggregate detail)
and FAILS LOUD before writing if any banned David-facing language, `decision_supported
== True`, or an "edge" label leaks in.

Usage:
    .venv/bin/python3.14 scripts/run_subpopulation_landscape.py \
        --run-dir app/data/backtest/runs/<run_id> \
        --id-map-csv /var/tmp/dp-data/files/db_playerids.csv \
        --output-dir app/data/backtest/subpopulation

NOTE (orchestration scope): `_compute_landscape_payload` (the slice -> fold ->
aggregate -> sign-flip-p -> FDR -> ledger glue) is STUBBED by the Task 8 contract
tests; its end-to-end correctness is validated by the Task 9 e2e run + cockpit
review, not by Task 8's RED.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Sequence

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.eval.subpopulation_landscape import (  # noqa: E402
    _REPORT_HEADER,
    NEUTRAL_BAND,
    InvalidDraftYearError,
    aggregate_folds,
    aggregate_signflip_p,
    apply_fdr,
    build_slice_ledger,
    compute_slice,
    resolve_draft_year,
    tag_cohorts,
)

REEXEC_ENV = "DYNASTY_SUBPOPULATION_REEXEC"
DRAFT_YEAR_SOURCE_LABEL = "dynastyprocess_db_playerids"
# Position-primary k from the G3 framing (QB/TE @12, RB/WR @24).
POSITION_PRIMARY_K = {"QB": 12, "RB": 24, "WR": 24, "TE": 12}
N_BOOTSTRAP = 1000
RNG_SEED = 2026
# Posture guard: banned David-facing tokens. "edge" is allowed ONLY in the
# sanctioned report header (excluded below); everywhere else it is banned.
_BANNED_TOKENS = ("buy", "sell", "verdict", "grade", "tier", "recommendation", "edge")


class _DifferingArtifactError(RuntimeError):
    """Raised when a run-stamped artifact already exists with differing content."""


# ── re-exec guard ─────────────────────────────────────────────────────────────

def _reexec_under_venv() -> None:
    """Re-exec under the repo `.venv` python if not already running under it."""
    if os.environ.get(REEXEC_ENV):
        return
    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = repo_root / ".venv"
    venv_python = venv_dir / "bin" / "python3.14"
    if Path(sys.prefix).resolve() == venv_dir.resolve():
        return
    if not venv_python.exists():
        return
    os.environ[REEXEC_ENV] = "1"
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


# ── loaders + join ────────────────────────────────────────────────────────────

def _load_market_rows(run_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(run_dir.glob("market_comparison_*.json")):
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
    return rows


def _load_predictions(run_dir: Path) -> dict[tuple, float | None]:
    preds: dict[tuple, float | None] = {}
    for path in sorted(run_dir.glob("predictions_*.csv")):
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                pid = row.get("player_id")
                season = row.get("feature_season")
                if pid is None or season in (None, ""):
                    continue
                age = row.get("age_at_feature_season")
                preds[(pid, int(season))] = (
                    float(age) if age not in (None, "") else None
                )
    return preds


def _load_id_map_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _enrich(
    market_rows: list[dict],
    predictions: dict[tuple, float | None],
    draft_year_map: dict[str, int],
) -> list[dict]:
    enriched: list[dict] = []
    for row in market_rows:
        pid = row.get("player_id")
        enriched.append(
            {
                **row,
                "age_at_feature_season": predictions.get(
                    (pid, row.get("feature_season"))
                ),
                "draft_year": draft_year_map.get(pid),
            }
        )
    return enriched


# ── orchestration (STUBBED by Task 8 RED; e2e-validated at Task 9) ────────────

def _aggregate_category(median_rho_diff: float | None) -> str:
    if median_rho_diff is None:
        return "insufficient_n"
    if median_rho_diff >= NEUTRAL_BAND:
        return "model_leads_point_estimate"
    if median_rho_diff <= -NEUTRAL_BAND:
        return "consensus_leads_point_estimate"
    return "statistically_indistinguishable"


def _slice_specs():
    return [
        ("aging_cliff_transition", "aging_cliff",
         lambda r: bool(r.get("aging_cliff_transition"))),
        ("high_disagreement", "model_bullish",
         lambda r: r.get("high_disagreement") and r.get("disagreement_bucket") == "model_bullish"),
        ("high_disagreement", "model_bearish",
         lambda r: r.get("high_disagreement") and r.get("disagreement_bucket") == "model_bearish"),
        ("early_career", "eligible",
         lambda r: bool(r.get("early_career_eligible"))),
    ]


def _compute_landscape_payload(
    enriched_rows: list[dict],
    *,
    draft_year_provenance: dict,
    run_id: str,
) -> dict:
    """Slice -> fold -> aggregate -> sign-flip-p -> FDR -> ledger (spec §3/§4).

    STUBBED by the Task 8 contract tests; correctness validated at Task 9 e2e.
    """
    draft_year_map = {
        r["player_id"]: r["draft_year"]
        for r in enriched_rows
        if r.get("player_id") is not None and r.get("draft_year") is not None
    }
    tagged = tag_cohorts(enriched_rows, draft_year_map)
    positions = sorted({r.get("position") for r in tagged if r.get("position")})

    aggregates: list[dict] = []
    for axis, slice_label, predicate in _slice_specs():
        for position in positions:
            slice_rows = [
                r for r in tagged if r.get("position") == position and predicate(r)
            ]
            folds = sorted(
                {r.get("feature_season") for r in slice_rows
                 if r.get("feature_season") is not None}
            )
            fold_results: list[dict] = []
            for fold in folds:
                rows_sf = [
                    r for r in slice_rows
                    if r.get("feature_season") == fold
                    and r.get("model_rank") is not None
                    and r.get("consensus_rank") is not None
                    and r.get("realized_rank") is not None
                ]
                if not rows_sf:
                    continue
                result = compute_slice(
                    [r["model_rank"] for r in rows_sf],
                    [r["consensus_rank"] for r in rows_sf],
                    [r["realized_rank"] for r in rows_sf],
                    primary_k=POSITION_PRIMARY_K.get(position, 24),
                    n_bootstrap=N_BOOTSTRAP,
                    rng_seed=RNG_SEED,
                )
                fold_results.append(
                    {**result, "axis": axis, "slice": slice_label,
                     "position": position, "fold": fold}
                )
            agg = aggregate_folds(fold_results)
            evaluable = [
                fr["rho_diff"] for fr in fold_results if fr.get("rho_diff") is not None
            ]
            aggregates.append(
                {
                    "axis": axis,
                    "slice": slice_label,
                    "position": position,
                    "median_rho_diff": agg["median_rho_diff"],
                    "folds_covered": agg["folds_covered"],
                    "fold_rows": agg["fold_rows"],
                    "n": sum(int(fr.get("n") or 0) for fr in fold_results),
                    "boot_p_value": aggregate_signflip_p(evaluable),
                    "aggregate_p_value_method": "fold_signflip_median_exact",
                    "category": _aggregate_category(agg["median_rho_diff"]),
                }
            )

    aggregates = apply_fdr(aggregates)

    provenance, early_career_coverage = _build_provenance_and_coverage(
        tagged, positions, draft_year_provenance
    )
    invalid = draft_year_provenance.get("invalid_draft_year_error")
    ledger = build_slice_ledger(
        aggregates,
        draft_year_provenance=provenance,
        early_career_coverage=early_career_coverage,
        invalid_draft_year_error=invalid,
    )
    aggregate_details = [_safe_detail(a) for a in aggregates]
    return {"ledger": ledger, "aggregate_details": aggregate_details}


def _build_provenance_and_coverage(tagged, positions, base_provenance):
    total = len(tagged)
    covered = sum(1 for r in tagged if r.get("draft_year") is not None)
    excluded = total - covered
    invalid_neg = sum(
        1 for r in tagged
        if "invalid_negative_experience" in (r.get("cohort_exclusion_reasons") or [])
    )
    per_pos_disagreement = {
        pos: sum(
            1 for r in tagged
            if r.get("position") == pos and r.get("high_disagreement")
        )
        for pos in positions
    }
    provenance = {
        "draft_year_source": base_provenance.get("draft_year_source"),
        "db_season_snapshot": base_provenance.get("db_season_snapshot"),
        "draft_year_coverage_numerator": covered,
        "draft_year_coverage_denominator": total,
        "excluded_missing_draft_year_count": excluded,
        "invalid_negative_experience_count": invalid_neg,
        "per_position_disagreement_denominators": per_pos_disagreement,
    }
    per_position_fold = []
    seen = sorted({
        (r.get("position"), r.get("feature_season"))
        for r in tagged
        if r.get("position") and r.get("feature_season") is not None
    })
    for pos, fold in seen:
        rows = [
            r for r in tagged
            if r.get("position") == pos and r.get("feature_season") == fold
        ]
        per_position_fold.append({
            "position": pos,
            "fold": fold,
            "covered": sum(1 for r in rows if r.get("draft_year") is not None),
            "denominator": len(rows),
        })
    early_career_coverage = {
        "overall": {"covered": covered, "denominator": total},
        "per_position_fold": per_position_fold,
    }
    return provenance, early_career_coverage


def _safe_detail(aggregate: dict) -> dict:
    """Posture-safe projection of an aggregate for the artifact detail block.

    Only known numeric/enum fields are carried; no raw passthrough of arbitrary
    input keys (mirrors the Task 7 Option-A no-echo decision).
    """
    return {
        "axis": aggregate.get("axis"),
        "slice": aggregate.get("slice"),
        "position": aggregate.get("position"),
        "category": aggregate.get("category"),
        "median_rho_diff": aggregate.get("median_rho_diff"),
        "folds_covered": aggregate.get("folds_covered"),
        "n": aggregate.get("n"),
        "boot_p_value": aggregate.get("boot_p_value"),
        "aggregate_p_value_method": aggregate.get("aggregate_p_value_method"),
        "q_value": aggregate.get("q_value"),
        "powered_followup_candidate": aggregate.get("powered_followup_candidate"),
        "powered_followup_label": aggregate.get("powered_followup_label"),
    }


# ── posture guard + writers ───────────────────────────────────────────────────

def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_dicts(item)


def _assert_posture(payload: dict) -> None:
    """Fail loud (ValueError) on any posture violation before writing."""
    for record in _walk_dicts(payload):
        if record.get("decision_supported") is True:
            raise ValueError("posture violation: decision_supported=True in payload")
    for text in _walk_strings(payload):
        if text == _REPORT_HEADER:
            continue
        lowered = text.lower()
        for token in _BANNED_TOKENS:
            if token in lowered:
                raise ValueError(
                    f"posture violation: banned token {token!r} in payload string"
                )


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _render_markdown(artifact: dict) -> str:
    ledger = artifact.get("ledger", {})
    lines = [f"# {ledger.get('header', _REPORT_HEADER)}", ""]
    lines.append(f"- run_id: `{artifact.get('run_id')}`")
    prov = ledger.get("provenance", {})
    lines.append(f"- draft_year_source: `{prov.get('draft_year_source')}`")
    lines.append(f"- db_season_snapshot: `{prov.get('db_season_snapshot')}`")
    lines.append("")
    lines.append("## Axis tables")
    for axis, table in (ledger.get("axis_tables") or {}).items():
        lines.append(f"### {axis} — {table.get('status')}")
        for row in table.get("rows", []):
            lines.append(
                f"- {row.get('category')}: n={row.get('n')}, "
                f"folds_covered={row.get('folds_covered')}"
            )
    lines.append("")
    lines.append(
        "_powered_followup_candidate is structurally unreachable at K<=4 folds "
        "(sign-flip min two-sided p = 0.25); absence of candidates is a power "
        "limit, not 'no signal'._"
    )
    return "\n".join(lines) + "\n"


def _write_outputs(payload: dict, *, output_dir: Path, run_id: str) -> None:
    _assert_posture(payload)
    artifact = {"run_id": run_id, **payload}
    run_json = output_dir / f"subpopulation_landscape_{run_id}.json"
    new_json = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    if run_json.exists():
        existing = run_json.read_text(encoding="utf-8")
        if json.loads(existing) != json.loads(new_json):
            raise _DifferingArtifactError(
                f"refusing to overwrite differing artifact: {run_json}"
            )
    new_md = _render_markdown(artifact)
    _atomic_write(run_json, new_json)
    _atomic_write(output_dir / f"subpopulation_landscape_{run_id}.md", new_md)
    _atomic_write(output_dir / "subpopulation_landscape_latest.json", new_json)
    _atomic_write(output_dir / "subpopulation_landscape_latest.md", new_md)


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: Sequence[str] | None = None) -> int:
    _reexec_under_venv()
    parser = argparse.ArgumentParser(
        description="Run the subpopulation / axis-of-edge landscape study."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--id-map-csv", type=Path, default=None)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    run_id = args.run_dir.name
    market_rows = _load_market_rows(args.run_dir)
    predictions = _load_predictions(args.run_dir)

    draft_year_provenance: dict = {
        "draft_year_source": None,
        "db_season_snapshot": None,
    }
    draft_year_map: dict[str, int] = {}
    if args.id_map_csv is not None:
        draft_year_provenance["draft_year_source"] = DRAFT_YEAR_SOURCE_LABEL
        try:
            draft_year_map, snapshot = resolve_draft_year(
                _load_id_map_rows(args.id_map_csv)
            )
            draft_year_provenance["db_season_snapshot"] = snapshot
        except InvalidDraftYearError as exc:
            draft_year_map = {}
            draft_year_provenance["invalid_draft_year_error"] = str(exc)

    enriched_rows = _enrich(market_rows, predictions, draft_year_map)
    payload = _compute_landscape_payload(
        enriched_rows,
        draft_year_provenance=draft_year_provenance,
        run_id=run_id,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        _write_outputs(payload, output_dir=args.output_dir, run_id=run_id)
    except _DifferingArtifactError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"run_id={run_id} wrote subpopulation landscape to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
