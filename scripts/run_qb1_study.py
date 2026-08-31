"""QB-1 study end-to-end composition (TW14-QB1-1, green-review G4).

This script is the ONE reviewed composition of the pinned QB-1 components:

    D1 admission (``admit_and_load_validation_pool``, hash-before-parse +
    registration-pin binding) → D2 labels (``build_label_table``, the
    registration's OWN 12-key scoring rule, settings-hash gated) → D2a matrix
    (``build_study_matrix``) → the 8 registered expanding folds
    (``run_expanding_folds``) → per fold H1–H4 ridge lanes (``fit_ridge_lane``)
    + the registered naive baseline (``build_naive_lane``) + the §9.3 H5 static
    market lane (``load_h5_snapshots`` + ``build_h5_static_join`` behind the
    registered per-fold coverage/reconciliation gates) → the 14 registered
    contrasts (``build_primary_comparisons``) → registered inference
    (``run_primary_inference``, seeds 20260716) → the §9.2/F30 statuses
    (``evaluate_power_and_status``) → the D5 panels (F10 case panel, F13
    threshold panel, F29 sensitivity panel) → ``assemble_terminal_report`` →
    the atomic named-failure runner (``run_qb1_study``) under the frozen root.

Every stage re-verifies the binding registration pin and fails closed through
its own shipped gates. THE COMPOSITION ADDS NO ANALYTICAL CHOICE NOT ALREADY
REGISTERED: every constant consumed here is read from the canonical
registration object or is a registered/spec-pinned literal cited in place.
All outputs are descriptive; ``decision_supported=False`` recursively. H2 QB
rushing remains a registered hypothesis UNDER TEST until execution and David's
ruling — this script computes the registered readout, never a verdict.

Execution gate of record: David's word, 2026-08-14 — "run the study when codex
clears the review." This script must hold GREEN-review CLEAR before any run.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd  # noqa: E402

import src.dynasty_genius.eval.qb_validation as qb  # noqa: E402

# ── Pinned inputs (all overridable in tests via explicit arguments) ────────────

REGISTRATION_JSON = Path("docs/validation/2026-07-21-qb-1-study-registration.json")
RAW_ROOT = Path("app/data/backtest/qb_validation/raw")
DP_VALUES_ROOT = RAW_ROOT / "dp_values"
OUTPUT_PATH = Path("app/data/backtest/qb_validation/qb_validation_report.json")

# The §9.3 H5 join instrument: the pinned 2026-05-16 crosswalk COPY (framing v5
# — "two artifacts, two roles, no aliasing": the fresh D1 ``ff_playerids``
# fetch is the identity DATASET; this pinned copy is the H5 join instrument
# whose ``observed_at`` disclosure semantics the registration fixes).
CROSSWALK_PATH = Path("app/data/identity/_runs/ff_playerids_20260516.json")
CROSSWALK_SHA256 = "8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593"

# The registered DP market provenance (comparisons._DP_PROVENANCE mirrors this).
DP_PROVENANCE = "dynastyprocess_ecr_2qb"

# The SHIPPED binary dual-threat gate (spec F13 scope, quoted: "the existing
# binary `is_dual_threat` flag ... is in the panel's scope"): season rushing
# yards strictly greater than this threshold in ANY of the three trailing
# seasons (src/dynasty_genius/models/engine_b_contract.py:110 and
# src/dynasty_genius/features/feature_assembly.py:304-308).
# R6-G1-3: one source of truth — the computation's threshold and the
# publication gate's required value can never drift apart.
DUAL_THREAT_RUSHING_THRESHOLD = qb.execution.DUAL_THREAT_RUSHING_YARDS
# R7-G3: one source of truth with the publication gate's window check.
ARCHETYPE_WINDOW_SEASONS = qb.execution.ARCHETYPE_WINDOW_SEASONS

# The REGISTERED F25 frozen set (R3-G4, program contract; hashes independently
# measured by Codex in the round-3 review and reproduced before pinning): the
# existing product/model boundary the study must never disturb — the qb_v2
# registry pointer, model artifact, and manifest, the qb_v3 research
# walk-forward, and the promotion decision record. RUNNER-OWNED: resolved
# against THIS script's own repository root, never caller-selected.
F25_FROZEN_SET: dict[str, str] = {
    # RE-PINNED 2026-08-31 on David's ruling. Held 307200148e2c251e… from
    # 2026-07-02 until DG-028 (99c238d6, 2026-08-28) added 17 lines registering
    # engine_b:v1_fallback, moving the file to ad981800711a322e… . That entry is
    # a CUSTODIAL registration — its own approved_by records the already-served
    # fallback engine_b_service._load_v1_bundle scans for, explicitly "not a new
    # approval" — so the boundary move is authorized after the fact, not a
    # study-invalidating edit. Nothing published by QB-1 is affected: the study
    # ran against the old pin; only a RE-RUN would have refused.
    # The drift went unseen for three days because dg-land.sh gates in a fresh
    # worktree where the gitignored model pickles are absent, so the seven
    # contract tests covering this boundary SKIP on every land. Re-pinning
    # restores the guard; it does not fix that blindness.
    "app/config/model_registry.json": (
        "ad981800711a322e82eb7691c5bfe035db6c7c95ad1972611f86b9642f2d0be9"
    ),
    "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl": (
        "d7acb6808e4a6caf412ec05b41aa90324e04f90ef219bbf78f680f66ea7d304f"
    ),
    "app/data/models/engine_b/v2_manifest.json": (
        "86f199bd069823cc292f8d56553dadc91f07f78bd47ac26498a06f16440984bc"
    ),
    "src/dynasty_genius/eval/qb_v3_walk_forward.py": (
        "7f3e9283afac1928629b3c04ef2ec71e85c99f3e55278f2237fcf9bedab4a3b5"
    ),
    "docs/validation/2026-07-04-build4-qb-v3-promotion-decision-record.md": (
        "a963b671dc6a1ef88bb73283acac594201b7cee3bda59a84681a03b810f6bd63"
    ),
}


def f25_frozen_expected() -> dict[Path, str]:
    """The F25 set resolved against the script's OWN repo root — the caller
    cannot select, reduce, or redirect it (R3-G4)."""
    return {
        _REPO_ROOT / relative: sha for relative, sha in F25_FROZEN_SET.items()
    }

# The F10 case panel — spec v8 D5, quoted: "Daniels/Nix 2024→2025 (second-season,
# per the rookie re-scope), Mayfield 2025, Richardson 2025, Maye 2025, and the
# ex-ante Allen-2019/Richardson-2024 twin test of the efficiency screen — both
# outcomes reported, no cherry-pick." Ids are pinned by the frozen execution RED.
CASE_TABLE: tuple[tuple[str, str, int, str], ...] = (
    (
        "daniels_2025",
        "Jayden Daniels",
        2025,
        "second-season prediction (2025 from 2024 rookie-season features; "
        "registration §4 rookie exclusion)",
    ),
    (
        "nix_2025",
        "Bo Nix",
        2025,
        "second-season prediction (2025 from 2024 rookie-season features; "
        "registration §4 rookie exclusion)",
    ),
    ("mayfield_2025", "Baker Mayfield", 2025, "registered case"),
    ("richardson_2025", "Anthony Richardson", 2025, "registered case"),
    ("maye_2025", "Drake Maye", 2025, "registered case"),
    (
        "allen_2019_twin",
        "Josh Allen",
        2019,
        "efficiency-screen twin (ex-ante pair with richardson_2024_twin; "
        "both outcomes reported, no cherry-pick)",
    ),
    (
        "richardson_2024_twin",
        "Anthony Richardson",
        2024,
        "efficiency-screen twin (ex-ante pair with allen_2019_twin; "
        "both outcomes reported, no cherry-pick)",
    ),
)

# R5-G1: one source of truth — the runner's manifest_missing keys and the
# publication gate's required ridge-lane set can never drift apart.
_RIDGE_LANES = qb.execution.RIDGE_LANE_NAMES
_ALL_LANES = ("naive", "h1", "h2", "h3", "h4")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ── Input loading (real-substrate side; every input hash-verified) ─────────────


def load_registration(repo_root: Path) -> dict[str, Any]:
    """Load and PIN-VERIFY the canonical registration object."""
    payload = json.loads((Path(repo_root) / REGISTRATION_JSON).read_text())
    qb.require_registration_hash(payload, qb.REGISTRATION_PIN)
    return payload


def load_crosswalk(
    repo_root: Path,
    *,
    path: Path | None = None,
    expected_sha256: str = CROSSWALK_SHA256,
) -> tuple[list[dict[str, Any]], str]:
    """Load the pinned §9.3 crosswalk instrument: hash verified BEFORE parse.

    Returns ``(entries, observed_at)`` where ``observed_at`` is the file's own
    recorded pull timestamp — the honest retrospective provenance every joined
    H5 row must carry (registration h5.join.provenance_fields).
    """
    crosswalk_path = Path(repo_root) / (path or CROSSWALK_PATH)
    if not crosswalk_path.is_file():
        raise qb.QBValidationFailure(
            "source_unavailable", f"pinned crosswalk missing: {crosswalk_path}"
        )
    actual = _sha256_file(crosswalk_path)
    if actual != expected_sha256:
        raise qb.QBValidationFailure(
            "source_snapshot_drift",
            f"crosswalk {crosswalk_path.name}: sha256 {actual} != pinned "
            f"{expected_sha256}",
        )
    payload = json.loads(crosswalk_path.read_text())
    entries = payload.get("entries")
    observed_at = (payload.get("metadata") or {}).get("pull_timestamp")
    if not isinstance(entries, list) or not entries or not observed_at:
        raise qb.QBValidationFailure(
            "source_unavailable",
            f"crosswalk {crosswalk_path.name} lacks entries/pull_timestamp",
        )
    return entries, str(observed_at)


def load_dp_snapshot_rows(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Parse ONE registered DP values snapshot (already SHA-verified by
    ``load_h5_snapshots``) into join-ready QB rows.

    Row shape: ``fp_id`` (join key), ``dp_name`` (the F32 reconciliation
    input), ``value_2qb`` (the rank-only higher-is-better market value the H5
    lane predicts with). QB filter = the snapshot's own ``pos`` column — the
    registration's per-snapshot ``qb_rows`` counts are counts of exactly this
    filter.
    """
    rows: list[dict[str, Any]] = []
    with Path(snapshot["path"]).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("pos") or "").strip() != "QB":
                continue
            fp_id = (row.get("fp_id") or "").strip()
            value_raw = (row.get("value_2qb") or "").strip()
            try:
                value = float(value_raw)
            except ValueError:
                raise qb.QBValidationFailure(
                    "source_snapshot_drift",
                    f"{Path(snapshot['path']).name}: non-numeric value_2qb "
                    f"{value_raw!r} for {row.get('player')!r}",
                ) from None
            rows.append(
                {
                    "fp_id": fp_id or None,
                    "dp_name": (row.get("player") or "").strip(),
                    "value_2qb": value,
                }
            )
    if not rows:
        raise qb.QBValidationFailure(
            "source_snapshot_drift",
            f"{Path(snapshot['path']).name}: zero QB rows parsed",
        )
    return rows


def filter_reg_weekly_records(frame: Any) -> list[dict[str, Any]]:
    """REG-only weekly records — the registered postseason exclusion
    (registration target.postseason = "excluded") applied mechanically before
    the label builder, which itself REFUSES any non-REG row (defense in
    depth, not a second authority)."""
    records = frame.to_dict("records")
    return [row for row in records if row.get("season_type") == "REG"]


# R16 (David's bounded word — ONE shared classifier for BOTH consumers): the
# placeholder classifier and its 17-column set now LIVE in qb_ppg_labels,
# beside the _stat_decimal semantics they mirror. The label seam below and
# study_matrix's weekly-record seam call the SAME function object; these
# re-exports keep this module's public surface (and its contracts) stable.
from src.dynasty_genius.eval.qb_validation.qb_ppg_labels import (  # noqa: E402
    PLACEHOLDER_D2_COLUMNS,  # noqa: F401 — deliberate re-export (R16 contracts)
    exclude_provider_placeholder_rows,
)

# ── H5 lane construction (per fold, behind the registered gates) ───────────────


def build_h5_lane(
    fold: Mapping[str, Any],
    *,
    dp_rows: list[Mapping[str, Any]],
    crosswalk_entries: list[Mapping[str, Any]],
    observed_at: str,
    registration: Mapping[str, Any],
    label_lookup: Mapping[tuple[str, int], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build ONE fold's H5 market lane behind the registered join gates.

    Gate order (all registered, h5.join): the fp_id-only static join → the
    F18 coverage floor over **the fold's evaluable pool** — registration §9.3,
    verbatim: "coverage <70% of the fold's evaluable pool → ``join_coverage_low``,
    fold excluded" (round-2 finding R2-G2: an earlier version divided by the
    market snapshot's row count, which admitted a nearly-empty lane) → the
    independent F32 name reconciliation over the joined pairs
    (``reconcile_identity_names``). A refusal carrying one of the REGISTERED
    ``h5.join.failure_states`` EXCLUDES the fold: the lane is emitted with
    zero predictions (downstream this is ``fold_starved`` → the fold does not
    contribute → ``evaluable_folds`` shrinks → the registered below-floor
    status by rule). Any other refusal propagates and fails the run.

    Returns ``(lane, audit)`` — the audit records every denominator the gates
    used, separately, so the exclusion basis is visible in the terminal
    report, never silent.
    """
    test_season = fold["test_season"]
    evaluable_keys = {
        (row["player_id"], test_season)
        for row in fold["test_rows"]
        if row.get("target") == "target_evaluable"
    }
    join = qb.build_h5_static_join(
        dp_rows=list(dp_rows),
        crosswalk_rows=list(crosswalk_entries),
        observed_at=observed_at,
        registration=registration,
    )
    joined_rows = join["joined_rows"]
    in_pool_rows = [
        row
        for row in sorted(joined_rows, key=lambda entry: str(entry.get("gsis_id")))
        if (row["gsis_id"], test_season) in evaluable_keys
        and (row["gsis_id"], test_season) in label_lookup
    ]
    audit: dict[str, Any] = {
        "test_season": test_season,
        "dp_qb_rows": len(dp_rows),
        "joined": len(joined_rows),
        "evaluable_pool": len(evaluable_keys),
        "in_evaluable_pool": len(in_pool_rows),
        "unresolved": join["unresolved_count"],
        "identity_conflicts": join["conflict_count"],
        "excluded": False,
        "exclusion_reason": None,
        "decision_supported": False,
    }
    failure_states = set(
        ((registration.get("h5") or {}).get("join") or {}).get("failure_states") or ()
    )
    try:
        coverage = qb.validate_join_coverage(
            len(in_pool_rows), len(evaluable_keys), registration=registration
        )
        audit["coverage"] = coverage["coverage"]
        pairs = [
            {"dp_name": row.get("dp_name"), "crosswalk_name": row.get("crosswalk_name")}
            for row in joined_rows
        ]
        reconciliation = qb.reconcile_identity_names(pairs, registration=registration)
        audit["mismatch_rate"] = reconciliation["mismatch_rate"]
        audit["mismatch_count"] = reconciliation["mismatch_count"]
    except qb.QBValidationFailure as failure:
        if failure.reason not in failure_states:
            raise
        audit["excluded"] = True
        audit["exclusion_reason"] = failure.reason
        lane = {
            "lane": "h5",
            "test_season": test_season,
            "lane_source": DP_PROVENANCE,
            "n_predicted": 0,
            "predictions": [],
            "decision_supported": False,
        }
        return lane, audit

    predictions: list[dict[str, Any]] = [
        {
            "player_id": row["gsis_id"],
            "target_season": test_season,
            "y_pred": float(row["value_2qb"]),
            "y_true": float(label_lookup[(row["gsis_id"], test_season)]),
            "source_provenance": DP_PROVENANCE,
            "decision_supported": False,
        }
        for row in in_pool_rows
    ]
    lane = {
        "lane": "h5",
        "test_season": test_season,
        "lane_source": DP_PROVENANCE,
        "n_predicted": len(predictions),
        "predictions": predictions,
        "decision_supported": False,
    }
    return lane, audit


# ── F13: the archetype threshold-sensitivity panel (binary gate vs continuous) ─


def build_season_rushing(
    weekly_records: list[Mapping[str, Any]],
) -> dict[tuple[str, int], dict[str, Any]]:
    """Per (player, season) REG rushing totals + QUALIFYING games — the
    mechanical substrate for the shipped binary dual-threat rule.

    R3-G5 ruling: the ±1 yd/game arithmetic must use the exact REGISTERED
    qualifying-game population — ``(attempts + sacks_suffered) >= 1 OR
    carries >= 1`` (registration ``target.qualifying_game_predicate``) — never
    a raw weekly-row count. Rushing yards still sum over every REG row (the
    shipped binary gate reads season totals); only the games denominator is
    predicate-gated.
    """
    totals: dict[tuple[str, int], dict[str, Any]] = {}
    for row in weekly_records:
        key = (str(row.get("player_id")), row.get("season"))
        entry = totals.setdefault(key, {"rushing_yards": 0.0, "weeks": 0})
        yards = row.get("rushing_yards")
        entry["rushing_yards"] += float(yards) if yards is not None else 0.0
        attempts = row.get("attempts") or 0
        sacks = row.get("sacks_suffered") or 0
        carries = row.get("carries") or 0
        if (attempts + sacks) >= 1 or carries >= 1:
            entry["weeks"] += 1
    return totals


def build_archetype_threshold_panel(
    folds: list[Mapping[str, Any]],
    season_rushing: Mapping[tuple[str, int], Mapping[str, Any]],
) -> dict[str, Any]:
    """The F13 panel, COMPUTED (round-2 finding R2-G5): the shipped binary
    ``is_dual_threat`` gate versus the continuous rushing moderator, with the
    ±1 yd/game boundary cases, per fold over the evaluable pool.

    Mechanics, all from shipped rules — no invented analytical choice:
    - Binary gate: season rushing yards > 400 in ANY of the three trailing
      seasons ending at the registered t−1 feature season (the shipped rule).
    - Boundary case (±1 yd/g): a player with at least one trailing-window
      season whose distance from the 400 threshold is within that season's
      REGISTERED qualifying-game count × 1 yard/game (R3-G5 ruling) — the
      population where the binary gate is one yard per game from flipping.
    - Flip sensitivity: the classification recomputed with every trailing
      season's threshold shifted by ±(qualifying games × 1) — how many
      evaluable players the binary gate reclassifies at ±1 yd/game, per fold.
    - Full-evidence disclosure (R11, David's redesign word — extending
      R9-G2's window rows from boundary cases to the whole pool): the fold
      carries ``evaluable_players`` — one row per evaluable player with
      EVERY observed trailing-window row (season, rushing yards, qualifying
      games) the shipped classification read. The publication gate derives
      the dual/pocket partition, exact boundary membership, both flip
      booleans per case, and the fold flip totals from that evidence; each
      boundary case repeats its player's rows as ``window_seasons`` and is
      a view over the same evidence, never a second source.
    - Continuous moderator: the registered h2 manifest's ``rush_yds_per_game``
      (t−1) for each boundary player, read from the fold row — the value that
      moves smoothly where the gate snaps.
    """
    per_fold: list[dict[str, Any]] = []
    for fold in folds:
        test_season = fold["test_season"]
        window = [test_season - offset for offset in range(1, ARCHETYPE_WINDOW_SEASONS + 1)]
        dual_threat = 0
        boundary_cases: list[dict[str, Any]] = []
        evaluable_players: list[dict[str, Any]] = []
        flips_minus_1 = 0
        flips_plus_1 = 0
        evaluable_rows = [
            row for row in fold["test_rows"] if row.get("target") == "target_evaluable"
        ]
        for row in evaluable_rows:
            player_id = row["player_id"]
            seasons = [
                (season, season_rushing.get((player_id, season)))
                for season in window
            ]
            observed = [
                (season, entry) for season, entry in seasons if entry is not None
            ]
            base = any(
                entry["rushing_yards"] > DUAL_THREAT_RUSHING_THRESHOLD
                for _season, entry in observed
            )
            minus = any(
                entry["rushing_yards"]
                > DUAL_THREAT_RUSHING_THRESHOLD - entry["weeks"] * 1.0
                for _season, entry in observed
            )
            plus = any(
                entry["rushing_yards"]
                > DUAL_THREAT_RUSHING_THRESHOLD + entry["weeks"] * 1.0
                for _season, entry in observed
            )
            if base:
                dual_threat += 1
            if minus != base:
                flips_minus_1 += 1
            if plus != base:
                flips_plus_1 += 1
            near = [
                {
                    "season": season,
                    "rushing_yards": entry["rushing_yards"],
                    "qualifying_games": entry["weeks"],
                    "decision_supported": False,
                }
                for season, entry in observed
                if abs(entry["rushing_yards"] - DUAL_THREAT_RUSHING_THRESHOLD)
                <= entry["weeks"] * 1.0
            ]
            # R11 (full-evidence redesign): EVERY evaluable player disclosed
            # with the full observed trailing-window rows the classification
            # above actually read — so the publication gate derives the
            # dual/pocket partition, boundary membership, and flip totals
            # from evidence, with no caller total left to trust (R10-G1).
            window_rows = [
                {
                    "season": season,
                    "rushing_yards": entry["rushing_yards"],
                    "qualifying_games": entry["weeks"],
                    "decision_supported": False,
                }
                for season, entry in observed
            ]
            evaluable_players.append(
                {
                    "player_id": player_id,
                    "window_seasons": [dict(window_row) for window_row in window_rows],
                    "decision_supported": False,
                }
            )
            if near:
                # A boundary case is a VIEW over that same evidence for the
                # band players — same rows, plus the continuous-moderator
                # readout. A near season plus a strong out-of-boundary season
                # honestly reports no plus-flip, and with the strong row
                # disclosed the gate reaches the same answer mechanically.
                boundary_cases.append(
                    {
                        "player_id": player_id,
                        "binary_dual_threat": base,
                        "flips_at_minus_1_ypg": minus != base,
                        "flips_at_plus_1_ypg": plus != base,
                        "window_seasons": window_rows,
                        "boundary_seasons": near,
                        "continuous_rush_yds_per_game_t_minus_1": row.get(
                            "rush_yds_per_game"
                        ),
                        "continuous_rush_att_per_game_t_minus_1": row.get(
                            "rush_att_per_game"
                        ),
                        "decision_supported": False,
                    }
                )
        per_fold.append(
            {
                "test_season": test_season,
                "n_evaluable": len(evaluable_rows),
                "dual_threat_count": dual_threat,
                "pocket_count": len(evaluable_rows) - dual_threat,
                "evaluable_players": evaluable_players,
                "boundary_case_count": len(boundary_cases),
                "boundary_cases": boundary_cases,
                "flips_at_minus_1_ypg": flips_minus_1,
                "flips_at_plus_1_ypg": flips_plus_1,
                "decision_supported": False,
            }
        )
    return {
        "id": "archetype_threshold",
        "binary_dual_threat_gate": {
            "rule": "season rushing yards > 400 in any of the three trailing "
            "seasons (shipped is_dual_threat, engine_b_contract.py:110)",
            "threshold_yards": DUAL_THREAT_RUSHING_THRESHOLD,
            "per_fold": per_fold,
            "decision_supported": False,
        },
        "continuous_rushing_moderator": {
            "basis": "registered manifest h2 (rush_att_per_game, "
            "rush_yds_per_game, rush_td_share, rush_yds_per_att — continuous, "
            "lookback t-1); boundary players' values reported per fold above",
            "decision_supported": False,
        },
        "boundary_cases_yards_per_game": [-1, 1],
        "decision_supported": False,
    }


def lane_manifest_missing(lane: Mapping[str, Any]) -> int:
    """R3-G3: the ridge lanes report ``test_manifest_missing`` as a mapping
    ``{"count": n, "keys": [...]}`` — read the count and REFUSE an unreadable
    shape, never silently zero it."""
    value = (lane.get("missingness") or {}).get("test_manifest_missing")
    if isinstance(value, Mapping):
        count = value.get("count")
        if isinstance(count, int) and not isinstance(count, bool):
            return count
        raise qb.QBValidationFailure(
            "report_schema_invalid",
            f"test_manifest_missing mapping lacks an int count: {value!r}",
        )
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return len(value)
    raise qb.QBValidationFailure(
        "report_schema_invalid",
        f"unreadable test_manifest_missing shape: {value!r}",
    )


# ── Status mapping (registered §9.2 / F30 through the shipped decision fn) ─────


def _canonical_excluded_folds(excluded: Any) -> Any:
    """R20 (registration read 0453ca80…): the terminal-report projection of
    the internal exclusion record.

    The comparison/inference layer LOSSLESSLY records ``empty_common_pool``
    for an empty pair intersection; the frozen terminal vocabulary does not
    register that word. The registration's own implication —
    ``common_pool_n == 0`` is necessarily below the registered
    ``fold_min_evaluable_n`` floor of 20, whose registered
    ``below_min_n_flag`` is ``fold_starved`` — lets THIS adapter, and only
    this adapter, drop the internal word where ``fold_starved`` co-occurs in
    the same entry (no count is read or serialized). Outside that exact
    implication the adapter refuses ``report_schema_invalid`` by name:
    ``empty_common_pool`` without ``fold_starved``, or duplicated, in a
    structurally readable entry. Unreadable entry/reasons shapes pass through
    UNCHANGED to the registered validator for their named refusal — the
    adapter performs ZERO repr/str/derivation inspection of them (R21/R22,
    finding R20-G1). Every other word — registered or unknown — passes
    through untouched so the UNCHANGED publication gate keeps authority over
    schema drift, and ``None``/empty collections and all entry
    metadata/order are preserved exactly. The input record is never mutated
    (the internal diagnostic contract stays lossless), and reprojection uses
    BUILT-IN list/tuple construction only — never a payload-supplied
    subclass constructor."""
    if excluded is None or not isinstance(excluded, list):
        return excluded
    canonical: list[Any] = []
    for entry in excluded:
        reasons = entry.get("reasons") if isinstance(entry, Mapping) else None
        if not isinstance(entry, Mapping) or not isinstance(
            reasons, (list, tuple)
        ):
            # R21/R22 (finding R20-G1): NO repr/str/derivation inspection of
            # unreadable shapes — the token is inspected ONLY in structurally
            # readable entries. Unreadable shapes pass through UNTOUCHED; the
            # unchanged registered validator owns their named refusal.
            canonical.append(entry)
            continue
        occurrences = sum(
            1 for reason in reasons if reason == "empty_common_pool"
        )
        if occurrences == 0:
            canonical.append(entry)
            continue
        if occurrences > 1:
            raise qb.QBValidationFailure(
                "report_schema_invalid",
                "internal reason empty_common_pool is duplicated in one "
                "exclusion entry",
            )
        if "fold_starved" not in reasons:
            raise qb.QBValidationFailure(
                "report_schema_invalid",
                "internal reason empty_common_pool appears without its "
                "registered implication fold_starved",
            )
        kept = [reason for reason in reasons if reason != "empty_common_pool"]
        # Built-in construction ONLY (R22): a payload-supplied list/tuple
        # SUBCLASS constructor must never execute inside the adapter.
        projected: Any = tuple(kept) if isinstance(reasons, tuple) else kept
        canonical.append({**entry, "reasons": projected})
    return canonical


def contrast_status(
    result: Mapping[str, Any],
    *,
    fdr_adjusted: Mapping[str, Any],
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    """Map ONE inference result into the shipped status function's payload and
    return the report's comparison row.

    The ONLY direct assignment this function ever makes is the REGISTERED
    below-floor rule (fold_floors.below_floor_status) when the H5 lane's
    inference numerics are honestly unavailable below the floor — every other
    path routes through ``evaluate_power_and_status`` unchanged. Missing
    numerics AT OR ABOVE the floor are a fail-closed refusal, never a default.
    """
    contrast_id = result["id"]
    lane = result["lane"]
    # The registered direction binds from the REGISTRATION's own contrast spec
    # (the inference result does not carry it — found by the R4-G1 deep gate).
    spec = next(
        (row for row in registration["contrasts"] if row["id"] == contrast_id), None
    )
    if spec is None or spec["lane"] != lane:
        raise qb.QBValidationFailure(
            "report_schema_invalid",
            f"{contrast_id}: no registered contrast with this id/lane",
        )
    pooled = result["pooled"]
    interval = result["interval"]
    permutation = result["permutation"]
    folds = pooled["evaluable_folds"]
    pooled_delta = pooled["pooled_delta"]
    ci_low = interval.get("ci95_low")
    ci_high = interval.get("ci95_high")
    q = registration["inference"]["fdr_q"]
    adjusted = fdr_adjusted.get(contrast_id)

    row: dict[str, Any] = {
        "id": contrast_id,
        "lane": lane,
        "registered_direction": spec["direction"],
        "pooled_delta": pooled_delta,
        "ci95": [ci_low, ci_high],
        "p_perm": permutation.get("p_two"),
        "adjusted_p": adjusted,
        "evaluable_folds": folds,
        # R20: the terminal row carries the CANONICAL projection; the internal
        # inference record keeps its lossless reasons untouched.
        "excluded_folds": _canonical_excluded_folds(pooled.get("excluded_folds")),
        "decision_supported": False,
    }

    if lane == "model":
        payload: dict[str, Any] = {"folds": folds}
        if pooled_delta is not None:
            payload["pooled_delta"] = pooled_delta
            # Every registered model direction is left_gt_right, so a positive
            # pooled delta IS the registered direction (registration §8).
            if pooled_delta > 0:
                payload["direction"] = "registered"
            elif pooled_delta < 0:
                payload["direction"] = "wrong"
        if ci_low is not None and ci_high is not None:
            payload["ci_excludes_zero"] = bool(ci_low > 0 or ci_high < 0)
        if adjusted is not None:
            payload["passes_fdr"] = bool(adjusted <= q)
        status = qb.evaluate_power_and_status(payload)
        row["support_status"] = status["support_status"]
        return row

    # H5 lane: registered margin_m selects the primary margin leaf.
    margin_m = registration["h5"]["margin_m"]
    leaf = (result.get("margin_sensitivity") or {}).get(margin_m) or {}
    p_ni = leaf.get("p_ni")
    adjusted_p_ni = leaf.get("adjusted_p_ni")
    one_sided = interval.get("one_sided_lower_95")
    numerics = (pooled_delta, ci_low, ci_high, one_sided, p_ni, adjusted_p_ni)
    row["p_ni"] = p_ni
    row["adjusted_p_ni"] = adjusted_p_ni
    row["one_sided_lower_95"] = one_sided
    row["ni_met"] = bool(leaf.get("ni_met", False))

    if all(value is not None for value in numerics):
        status = qb.evaluate_power_and_status(
            {
                "lane": "h5",
                "folds": folds,
                "pooled_delta": pooled_delta,
                "ci95": [ci_low, ci_high],
                "one_sided_lower_95": one_sided,
                "p_ni": p_ni,
                "adjusted_p_ni": adjusted_p_ni,
            }
        )
        row["support_status"] = status["support_status"]
        row["ni_met"] = status["ni_met"]
        row["flags"] = status.get("flags", [])
        return row

    h5_floor = registration["fold_floors"]["h5_lane"]
    if folds < h5_floor and all(value is None for value in numerics):
        # The REGISTERED rule, applied directly ONLY because the shipped
        # status function requires numerics that inference honestly could not
        # produce below the floor: fold_floors.below_floor_status. R8-G1:
        # the special case is EXACT — wholly unavailable numerics and
        # ni_met=False; partial evidence refuses below.
        row["support_status"] = registration["fold_floors"]["below_floor_status"]
        row["ni_met"] = False
        row["flags"] = ["registered_below_floor_rule"]
        return row

    raise qb.QBValidationFailure(
        "inference_evidence_incomplete",
        f"{contrast_id}: {folds} evaluable folds with partially available "
        f"inference numerics (registered floor {h5_floor}) — evidence that "
        "is neither complete nor wholly unavailable cannot carry a label",
    )


# ── D5 panels ──────────────────────────────────────────────────────────────────


def resolve_case_players(players_frame: Any) -> dict[str, dict[str, Any]]:
    """Resolve the F10 case players to gsis ids: exact display name + position
    QB, refusing on zero or multiple hits (two NFL 'Josh Allen's exist; the
    QB filter plus a uniqueness refusal is the mechanical resolution)."""
    frame = players_frame
    missing_columns = [
        column
        for column in ("display_name", "position", "gsis_id")
        if column not in getattr(frame, "columns", ())
    ]
    if missing_columns:
        raise qb.QBValidationFailure(
            "case_identity_unresolved",
            f"players frame lacks pinned columns {missing_columns} — case "
            "resolution refuses, never guesses",
        )
    resolved: dict[str, dict[str, Any]] = {}
    for case_id, display_name, fold_season, scope_note in CASE_TABLE:
        hits = frame[
            (frame["display_name"] == display_name) & (frame["position"] == "QB")
        ]
        if len(hits) != 1:
            raise qb.QBValidationFailure(
                "case_identity_unresolved",
                f"{case_id}: {len(hits)} QB rows match display_name "
                f"{display_name!r} — exactly one is required",
            )
        resolved[case_id] = {
            "player_name": display_name,
            "gsis_id": str(hits.iloc[0]["gsis_id"]),
            "fold": fold_season,
            "scope_note": scope_note,
        }
    return resolved


def build_case_panel(
    resolved_cases: Mapping[str, Mapping[str, Any]],
    lanes_by_fold: Mapping[int, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """The F10 case panel: per registered case, every lane's prediction row
    for that (player, fold), reported verbatim; absence is an honest named
    state, never an imputed number. Both twins are reported — no cherry-pick
    is structurally possible because the table is a pinned literal."""
    panel: list[dict[str, Any]] = []
    for case_id, _display_name, _fold_season, _scope_note in CASE_TABLE:
        case = resolved_cases[case_id]
        fold_season = case["fold"]
        gsis_id = case["gsis_id"]
        lanes_out: dict[str, Any] = {}
        found_any = False
        fold_lanes = lanes_by_fold.get(fold_season) or {}
        for lane_name, lane in fold_lanes.items():
            match = next(
                (
                    row
                    for row in lane.get("predictions", [])
                    if row.get("player_id") == gsis_id
                ),
                None,
            )
            if match is None:
                lanes_out[lane_name] = {
                    "state": "not_in_lane_pool",
                    "decision_supported": False,
                }
            else:
                found_any = True
                lanes_out[lane_name] = {
                    "state": "reported",
                    "y_pred": match["y_pred"],
                    "y_true": match["y_true"],
                    "decision_supported": False,
                }
        panel.append(
            {
                "id": case_id,
                "player_name": case["player_name"],
                "gsis_id": gsis_id,
                "fold": fold_season,
                "scope_note": case["scope_note"],
                "state": "reported" if found_any else "not_in_evaluable_pool",
                "lanes": lanes_out,
                "decision_supported": False,
            }
        )
    return qb.require_case_panel(panel)


def build_min_games_slice(
    lanes_by_fold: Mapping[int, Mapping[str, Any]],
    labels: list[Mapping[str, Any]],
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    """The registered F29 secondary slice (target.sensitivity_slice_min_games):
    every lane's predictions restricted to player-seasons with ≥4 qualifying
    games, re-scored per contrast per fold, pooled DESCRIPTIVELY. Reported
    alongside — never substituted for — the unfiltered primary; no second
    inference family is registered so none is run."""
    min_games = registration["target"]["sensitivity_slice_min_games"]
    qualifying = {
        (row["player_id"], row["season"]): row["qualifying_games"] for row in labels
    }
    pooled_by_contrast: dict[str, Any] = {}
    for spec in registration["contrasts"]:
        lane_folds = (
            registration["folds"]["test_seasons"]
            if spec["lane"] == "model"
            else registration["h5"]["folds"]
        )
        per_fold: list[dict[str, Any]] = []
        for fold_season in lane_folds:
            fold_lanes = lanes_by_fold[fold_season]
            sides = []
            for side in (spec["left"], spec["right"]):
                lane = fold_lanes[side]
                kept = [
                    row
                    for row in lane["predictions"]
                    if qualifying.get((row["player_id"], row["target_season"]), 0)
                    >= min_games
                ]
                sides.append({**lane, "predictions": kept, "n_predicted": len(kept)})
            per_fold.append(
                qb.score_comparisons(sides[0], sides[1], contrast=spec)
            )
        pooled = qb.pool_paired_deltas(
            {**{f: spec[f] for f in ("id", "lane", "left", "right")},
             "registered_direction": spec["direction"],
             "per_fold": per_fold,
             "folds_present": len(per_fold),
             "decision_supported": False},
            registration=registration,
        )
        pooled_by_contrast[spec["id"]] = {
            "pooled_delta": pooled["pooled_delta"],
            "evaluable_folds": pooled["evaluable_folds"],
            "decision_supported": False,
        }
    return {
        "min_qualifying_games": min_games,
        "pooled_deltas": pooled_by_contrast,
        "decision_supported": False,
    }


def build_sensitivity_panels(
    comparisons_block: list[Mapping[str, Any]],
    inference_out: Mapping[str, Any],
    min_games_slice: Mapping[str, Any],
    registration: Mapping[str, Any],
    *,
    archetype_panel: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """The three D5 panels (F13 archetype — COMPUTED, see
    ``build_archetype_threshold_panel`` — F29 qualifying-games, §9.2 margin
    readout), each validated through its shipped gate before assembly."""
    threshold_panel = dict(archetype_panel)
    qb.require_threshold_sensitivity(threshold_panel)

    unfiltered_primary = {
        "min_qualifying_games": None,
        "pooled_deltas": {
            row["id"]: {
                "pooled_delta": row["pooled_delta"],
                "evaluable_folds": row["evaluable_folds"],
                "decision_supported": False,
            }
            for row in comparisons_block
        },
        "decision_supported": False,
    }

    margins = registration["h5"]["margin_sensitivity"]
    margin_readout: dict[str, Any] = {}
    for result in inference_out["contrasts"]:
        if result["lane"] != "h5":
            continue
        computed = {
            str(margin): leaf
            for margin, leaf in (result.get("margin_sensitivity") or {}).items()
        }
        # R6-G1-2 / R7-G2 (registration §9.2): every registered margin cell is
        # reported for every H5 contrast, under the CLOSED leaf schemas — a
        # cell is computed only when all three outputs exist; a present-but-
        # null inference leaf is semantically unavailable and says so.
        cells: dict[str, Any] = {}
        for margin in margins:
            leaf = computed.get(str(margin)) or {}
            outputs = (
                leaf.get("p_ni"),
                leaf.get("adjusted_p_ni"),
                leaf.get("ni_met"),
            )
            if all(value is not None for value in outputs):
                cells[str(margin)] = {
                    "p_ni": outputs[0],
                    "adjusted_p_ni": outputs[1],
                    "ni_met": outputs[2],
                    "decision_supported": False,
                }
            else:
                cells[str(margin)] = {
                    "state": "unavailable",
                    "p_ni": None,
                    "adjusted_p_ni": None,
                    "ni_met": None,
                    "decision_supported": False,
                }
        margin_readout[result["id"]] = cells
    h5_margin_panel = {
        "id": "h5_margin",
        "margins": list(margins),
        "readout": margin_readout,
        "decision_supported": False,
    }

    qualifying_panel = {
        "id": "qualifying_games",
        "unfiltered_primary": unfiltered_primary,
        "min_four_games": dict(min_games_slice),
        "decision_supported": False,
    }
    # F29's shipped validator consumes the combined view of all three slices.
    qb.validate_sensitivity_panel(
        {
            "unfiltered_primary": unfiltered_primary,
            "min_four_games": dict(min_games_slice),
            "h5_margin_sensitivity": {"margins": list(margins)},
        }
    )
    return [threshold_panel, qualifying_panel, h5_margin_panel]


# ── The composition ────────────────────────────────────────────────────────────


def compose_study(
    *,
    registration: Mapping[str, Any],
    pool: Mapping[str, Mapping[str, Any]],
    crosswalk_entries: list[Mapping[str, Any]],
    crosswalk_observed_at: str,
    dp_snapshots: list[Mapping[str, Any]],
    dp_rows_by_season: Mapping[int, list[Mapping[str, Any]]],
    repo_root: Path,
    frozen_inputs: Mapping[Path, str] | None = None,
) -> dict[str, Any]:
    """The full analytical composition, hermetically drivable: consumes an
    ADMITTED source pool plus verified H5 inputs and returns the terminal
    report blocks (``run_status="ok"`` + the five metric blocks + the
    registered disclosures). The runner stamps, schema-gates,
    No-Verdict-validates, and atomically publishes.

    F25 (R2-G4 + the R3-G4 correction): the REGISTERED frozen set — the five
    runner-owned product/model boundary artifacts in ``F25_FROZEN_SET``,
    resolved against this script's own repository root and never
    caller-selected — is validated through ``qb.validate_frozen_hashes``
    BEFORE the analytical work and AGAIN immediately before the success
    blocks are returned for publication; one byte of drift refuses named
    (``frozen_boundary_drift``) and, inside the runner boundary, publishes as
    a metric-free failed artifact. The STUDY INPUTS (DP snapshots + the
    pinned crosswalk via ``frozen_inputs``) carry their own admission pins
    and are re-verified alongside as defense in depth — they are input
    admission, not F25.
    """
    qb.require_registration_hash(registration, qb.REGISTRATION_PIN)
    input_expected: dict[Path, str] = dict(frozen_inputs or {})
    for snapshot in dp_snapshots:
        input_expected[Path(snapshot["path"])] = str(snapshot["sha256"])
    qb.validate_frozen_hashes(f25_frozen_expected())
    qb.validate_frozen_hashes(input_expected)

    # D2 labels — the registration's OWN 12-key rule, settings-hash gated.
    # R14: the provider PLACEHOLDER rows leave ONLY the label input;
    # ``weekly_records`` itself stays unfiltered for the F13 season-rushing
    # panel below, and the untouched ``pool`` reaches build_study_matrix —
    # the §5 all-position team aggregation never sees this classification.
    weekly_records = filter_reg_weekly_records(pool["weekly"]["frame"])
    label_out = qb.build_label_table(
        exclude_provider_placeholder_rows(weekly_records),
        registration["scoring"]["components"],
        expected_settings_hash=registration["scoring"]["settings_hash"],
    )
    labels = label_out["labels"]
    label_lookup = {
        (row["player_id"], row["season"]): float(row["ppg"]) for row in labels
    }

    # D2a matrix + the registered expanding folds.
    matrix = qb.build_study_matrix(
        pool,
        registration=dict(registration),
        expected_registration_hash=qb.REGISTRATION_PIN,
    )
    folds = qb.run_expanding_folds(
        matrix,
        train_start_season=registration["folds"]["train_start_season"],
        test_seasons=tuple(registration["folds"]["test_seasons"]),
    )

    # Prediction lanes per fold.
    h5_fold_seasons = set(registration["h5"]["folds"])
    lanes_by_fold: dict[int, dict[str, Any]] = {}
    h5_audits: list[dict[str, Any]] = []
    for fold in folds:
        season = fold["test_season"]
        lanes: dict[str, Any] = {}
        for lane_name in _RIDGE_LANES:
            lanes[lane_name] = qb.fit_ridge_lane(fold, labels, lane=lane_name)
        lanes["naive"] = qb.build_naive_lane(fold, labels)
        if season in h5_fold_seasons:
            lane, audit = build_h5_lane(
                fold,
                dp_rows=dp_rows_by_season[season],
                crosswalk_entries=crosswalk_entries,
                observed_at=crosswalk_observed_at,
                registration=registration,
                label_lookup=label_lookup,
            )
            lanes["h5"] = lane
            h5_audits.append(audit)
        lanes_by_fold[season] = lanes

    # The 14 registered contrasts + the registered inference family.
    comparisons = qb.build_primary_comparisons(
        lanes_by_fold,
        registration=registration,
        expected_registration_hash=qb.REGISTRATION_PIN,
    )
    inference_out = qb.run_primary_inference(
        comparisons,
        registration=registration,
        expected_registration_hash=qb.REGISTRATION_PIN,
    )

    # §9.2 / F30 statuses through the shipped decision function.
    fdr_adjusted = inference_out["fdr"]["adjusted"]
    comparisons_block = [
        contrast_status(
            result, fdr_adjusted=fdr_adjusted, registration=registration
        )
        for result in inference_out["contrasts"]
    ]

    # Fold census rows: the REGISTERED five-key attrition vocabulary (R2-G3) —
    # the four outcome-class attrition states from the matrix's own per-season
    # audit, plus the per-lane manifest-driven drops the ridge lanes report —
    # and the per-fold metrics readout.
    matrix_attrition = matrix.get("attrition") or {}
    per_fold_metrics: dict[int, dict[str, Any]] = {
        fold["test_season"]: {} for fold in folds
    }
    for contrast in comparisons["contrasts"]:
        for fold_row in contrast["per_fold"]:
            per_fold_metrics[fold_row["test_season"]][contrast["id"]] = {
                "paired_delta": fold_row["paired_delta"],
                "spearman_left": fold_row["spearman_left"],
                "spearman_right": fold_row["spearman_right"],
                "common_pool_n": fold_row["common_pool_n"],
                # CIs are REGISTERED at the pooled level only
                # (inference.ci = bca_cluster_by_player over pooled deltas);
                # a per-fold CI would be an unregistered quantity, so the
                # state names the fact rather than fabricating a number.
                "ci": {"state": "pooled_level_only", "decision_supported": False},
                "decision_supported": False,
            }
    folds_block: list[dict[str, Any]] = []
    for fold in folds:
        season = fold["test_season"]
        test_rows = fold["test_rows"]
        n_evaluable = sum(
            1 for row in test_rows if row.get("target") == "target_evaluable"
        )
        season_attrition = (matrix_attrition.get(str(season)) or {}).get("counts") or {}

        attrition = {
            "no_target_season": season_attrition.get(
                "no_target_season",
                sum(1 for row in test_rows if row.get("target") == "no_target_season"),
            ),
            "rookie_no_priors": season_attrition.get("rookie_no_priors", 0),
            "cohort_ineligible_prior": season_attrition.get(
                "cohort_ineligible_prior", 0
            ),
            "cohort_ineligible_unobserved": season_attrition.get(
                "cohort_ineligible_unobserved", 0
            ),
            "manifest_missing": {
                lane_name: lane_manifest_missing(lanes_by_fold[season][lane_name])
                for lane_name in _RIDGE_LANES
            },
        }
        flags = []
        h5_audit = next(
            (audit for audit in h5_audits if audit["test_season"] == season), None
        )
        if h5_audit and h5_audit["excluded"]:
            # R3-G2: the flag IS the registered reason itself — the closed D5
            # vocabulary admits no composed prefix strings.
            flags.append(h5_audit["exclusion_reason"])
        folds_block.append(
            {
                "test_season": season,
                "n_evaluable": n_evaluable,
                "attrition": attrition,
                "metrics_with_CIs": per_fold_metrics[season],
                "lanes": {
                    name: lanes_by_fold[season][name]["n_predicted"]
                    for name in lanes_by_fold[season]
                },
                "flags": flags,
                "decision_supported": False,
            }
        )

    # D5 panels.
    resolved_cases = resolve_case_players(pool["players"]["frame"])
    case_panel = build_case_panel(resolved_cases, lanes_by_fold)
    min_games_slice = build_min_games_slice(lanes_by_fold, labels, registration)
    archetype_panel = build_archetype_threshold_panel(
        folds, build_season_rushing(weekly_records)
    )
    sensitivity_panels = build_sensitivity_panels(
        comparisons_block,
        inference_out,
        min_games_slice,
        registration,
        archetype_panel=archetype_panel,
    )

    inputs_block = {
        "registration_pin": qb.REGISTRATION_PIN,
        "settings_hash": label_out["settings_hash"],
        "matrix_version": matrix["matrix_version"],
        # R2-G6: EVERY admitted snapshot hash reaches terminal provenance —
        # the per-dataset "snapshots" lists carry all of them (pbp: 11), and
        # the single-hash metadata field is only the first-file convenience.
        # sha256 fields are present on every real seam-admitted envelope; the
        # F1 gate itself does not require them, so absence (a hermetic
        # fixture) is tolerated by omission, never fabricated.
        "snapshot_ids": sorted(
            {
                str(entry.get("sha256"))
                for state in pool.values()
                for entry in (state["metadata"].get("snapshots") or ())
                if entry.get("sha256")
            }
            | {
                str(sha)
                for sha in (
                    state["metadata"].get("sha256") for state in pool.values()
                )
                if sha
            }
            | {str(snapshot["sha256"]) for snapshot in dp_snapshots}
            | {CROSSWALK_SHA256}
        ),
        "dataset_rows": {
            name: pool[name].get("rows", len(pool[name]["frame"]))
            for name in pool
        },
        "h5_join_audits": h5_audits,
        "inference_provenance": inference_out["provenance"],
    }

    blocks = {
        "run_status": "ok",
        "inputs": inputs_block,
        "folds": folds_block,
        "comparisons": comparisons_block,
        "case_panel": case_panel,
        "sensitivity_panels": sensitivity_panels,
        # R2-G3: the registration's exact eight disclosures ride every ok
        # report — text verbatim, plus the recursive No-Verdict flag every
        # list-element mapping must carry (F26).
        "disclosures": [
            {**row, "decision_supported": False}
            for row in registration["disclosures"]
        ],
    }
    # R2-G3: the registered-schema gate, inside the terminal-runner boundary —
    # an incomplete success is a named refusal, never published as ok. (The
    # runner re-runs this gate unconditionally at publication, R3-G1; this
    # call is defense in depth at the composition seam.)
    qb.validate_registered_report_blocks(blocks, registration=registration)
    # R2-G4/R3-G4 second pass: the registered frozen set and the study-input
    # pins re-validated immediately before the success blocks leave for
    # publication.
    qb.validate_frozen_hashes(f25_frozen_expected())
    qb.validate_frozen_hashes(input_expected)
    return blocks


def main(repo_root: Path | None = None, output_path: Path | None = None) -> int:
    """The CLI entry: EVERY fallible step — registration load, F33 wall, D1
    admission, crosswalk load, H5 snapshot admission, DP parsing, and the
    composition itself — runs INSIDE the terminal-runner boundary (round-2
    finding R2-G1: preflight failures previously escaped artifact-less), so
    every invocation ends in an atomic named terminal artifact. Only the
    binding constants the runner itself needs (the registration PIN, the
    frozen output path) live outside it."""
    repo_root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    output = (
        Path(output_path) if output_path is not None else repo_root / OUTPUT_PATH
    )
    generated_at = datetime.now(timezone.utc).isoformat()

    # R19 (registration read 86bace11…): the runner exposes a closed,
    # metric-free failure-origin diagnostic — {"phase", "sites"} with
    # repository-relative path/function/line frames only — for FAILED runs.
    # The CLI stdout summary is its ONLY persistence surface; the six-key
    # terminal artifact and the success surface are untouched, and raw
    # failure detail is never serialized anywhere.
    failure_diagnostics: list[Mapping[str, Any]] = []

    def _stdout_summary(report: Mapping[str, Any]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "run_status": report["run_status"],
            "failure_reason": report.get("failure_reason"),
            "terminal_artifact": str(output),
            "decision_supported": False,
        }
        if report["run_status"] != "ok" and failure_diagnostics:
            summary["failure_origin"] = failure_diagnostics[0]
        return summary

    # The registration load is fallible and the runner's ok-path gate needs
    # the loaded object (R3-G1), so it loads under an OUTER terminal-artifact
    # boundary: a load failure re-raises inside a trivial runner invocation
    # and publishes as a named failed artifact (the R2-G1 guarantee holds).
    try:
        registration = load_registration(repo_root)
    except BaseException as load_exc:
        if not isinstance(load_exc, Exception):
            raise  # process-control exceptions are never converted
        # Rebind: Python unbinds the except target at block exit, and the
        # closure must hold the exception beyond it.
        load_failure = load_exc

        def reraise() -> dict[str, Any]:
            raise load_failure

        report = qb.run_qb1_study(
            execute=reraise,
            output_path=output,
            registration_hash=qb.REGISTRATION_PIN,
            generated_at=generated_at,
            repo_root=repo_root,
            failure_observer=failure_diagnostics.append,
        )
        print(json.dumps(_stdout_summary(report), indent=2))
        return 1

    def execute() -> dict[str, Any]:
        qb.enforce_consumer_boundary(repo_root=repo_root)
        crosswalk_entries, observed_at = load_crosswalk(repo_root)
        pool = qb.admit_and_load_validation_pool(
            repo_root / RAW_ROOT,
            repo_root=repo_root,
            frame_loader=pd.read_parquet,
        )
        dp_snapshots = qb.load_h5_snapshots(
            repo_root / DP_VALUES_ROOT, registration=registration
        )
        dp_rows_by_season = {
            snapshot["season"]: load_dp_snapshot_rows(snapshot)
            for snapshot in dp_snapshots
        }
        return compose_study(
            registration=registration,
            pool=pool,
            crosswalk_entries=crosswalk_entries,
            crosswalk_observed_at=observed_at,
            dp_snapshots=dp_snapshots,
            dp_rows_by_season=dp_rows_by_season,
            repo_root=repo_root,
            frozen_inputs={
                repo_root / CROSSWALK_PATH: CROSSWALK_SHA256,
            },
        )

    report = qb.run_qb1_study(
        execute=execute,
        output_path=output,
        registration_hash=qb.REGISTRATION_PIN,
        generated_at=generated_at,
        repo_root=repo_root,
        registration=registration,
        failure_observer=failure_diagnostics.append,
    )
    print(json.dumps(_stdout_summary(report), indent=2))
    return 0 if report["run_status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
