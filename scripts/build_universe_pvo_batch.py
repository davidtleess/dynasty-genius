"""Build Phase 17.2 full-universe PVO batch artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.engine_b_service import score_inference_partition  # noqa: E402
from scripts.compute_dvs_pct_batch import compute_dvs_pct_batch  # noqa: E402
from src.dynasty_genius.draft_capital import (  # noqa: E402
    DRAFT_CAPITAL_SNAPSHOT_PATH,
    load_draft_capital,
)
from src.dynasty_genius.features.feature_source import (  # noqa: E402
    resolve_feature_source,
)
from src.dynasty_genius.features.inference_partition import (  # noqa: E402
    select_inference_partition,
)
from src.dynasty_genius.league_capture import load_league_set_for_root  # noqa: E402
from src.dynasty_genius.models.dvs_band import (  # noqa: E402
    ENGINE_A_SIGMA_RUN,
    ENGINE_B_SIGMA_RUN,
    assert_band_sigma_runs_match_served_models,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity  # noqa: E402
from src.dynasty_genius.pvo_assembler import assemble_pvo  # noqa: E402
from src.dynasty_genius.universe_pvo_batch import (  # noqa: E402
    build_universe_pvo_batch,
    write_universe_pvo_artifacts,
)

SNAPSHOT_PATH = load_league_set_for_root(ROOT).paths["snapshot.json"]
PROSPECT_CARDS_PATH = ROOT / "resources" / "prospect_cards.json"
FF_PLAYERIDS_PATH = ROOT / "app" / "data" / "identity" / "_runs" / "ff_playerids_20260516.json"
ENGINE_B_FEATURES_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
FEATURES_RUNTIME_DIR = ROOT / "app" / "data" / "features_runtime"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"
# DG-128: the governed offline snapshot that hands a veteran his pick / round / draft-season
# age — the Engine A prior's inputs. Module-level so a test or shadow run can steer it.
DRAFT_CAPITAL_PATH = DRAFT_CAPITAL_SNAPSHOT_PATH


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _load_prospect_pvos(path: Path = PROSPECT_CARDS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cards = _load_json(path)
    return [card for card in cards if card.get("sleeper_id")]


# ── TW28 Units A + B: identity-join hardening ────────────────────────────────
# The crosswalk is the only join between Engine B's gsis-keyed predictions and the
# Sleeper-keyed universe. Before TW28 a missing file returned empty maps and every
# modeled player was then dropped by a bare `continue`, so a refresh could publish a
# universe with zero model values while passing every exit check.
#
# Every failure below raises a BARE machine token as its message: `run_pvo_refresh`
# copies `str(exc)` straight into the governed report's `aborted_reason`, so prose in
# the message would corrupt that truth surface.


class _CrosswalkIndex(dict):
    """A crosswalk index that also carries its parse-time duplicate count.

    ``_load_ff_playerids`` must keep returning exactly two mappings — callers unpack a
    2-tuple. Carrying the count on the mapping keeps the payload parsed exactly once,
    so the count can never describe different bytes than the index it came from.
    """

    duplicate_count: int = 0


def _crosswalk_identifier(entry: dict[str, Any], field: str) -> str | None:
    """Return a source identifier, or None when absent.

    JSON null stays absent rather than becoming the string ``"None"``. A non-string,
    non-null value fails closed instead of being coerced: ``bool`` is an ``int``
    subclass, so an explicit ``str`` check is what makes ``False`` and ``123`` both
    reject. Empty and whitespace-only values are treated as absent, which preserves
    the pre-TW28 loader's truthiness semantics so this change cannot silently alter
    which rows join.
    """
    value = entry.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("ff_playerids_identifier_wrong_type")
    return value.strip() or None


def _is_identical_crosswalk_duplicate(
    entry: dict[str, Any],
    gsis_id: str | None,
    sleeper_id: str | None,
    by_gsis: dict[str, dict[str, Any]],
    by_sleeper: dict[str, dict[str, Any]],
) -> bool:
    """True when this row repeats an already-indexed row exactly.

    "Identical" is Python mapping equality AFTER JSON parsing, not serialized-slice
    identity, so key order and whitespace in the source file are irrelevant.
    """
    if gsis_id is not None and by_gsis.get(gsis_id) == entry:
        return True
    return sleeper_id is not None and by_sleeper.get(sleeper_id) == entry


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Fail closed on a key repeated inside one JSON object.

    ``json.loads`` keeps the LAST value for a repeated key, so
    ``{"gsis_id": "00-good", "gsis_id": "00-wrong"}`` decodes as ``00-wrong`` and the
    first value is already gone before any entry-level conflict check can see it.
    Hardening the INDEX against last-write-wins was therefore not enough — the decoder
    did it first, one level lower. Runs for every object in the payload, so a repeated
    key anywhere fails the load rather than only inside an entry.
    """
    seen: set[str] = set()
    for key, _value in pairs:
        if key in seen:
            raise ValueError("ff_playerids_duplicate_json_key")
        seen.add(key)
    return dict(pairs)


def _load_ff_playerids(path: Path = FF_PLAYERIDS_PATH) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not path.exists():
        raise ValueError("ff_playerids_crosswalk_missing")
    try:
        # Decode explicitly rather than via `read_text()`. Undecodable bytes raise
        # `UnicodeDecodeError`, which is itself a `ValueError` — so left uncaught it
        # reaches the governed refresh report as an `aborted_reason` full of codec
        # prose AND is type-indistinguishable from the named machine tokens above.
        # Naming the encoding also removes a locale dependency from the load.
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("ff_playerids_crosswalk_invalid_json") from exc
    try:
        # A ValueError from the hook is not a JSONDecodeError, so the duplicate-key
        # reason propagates unchanged through the clause below.
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except json.JSONDecodeError as exc:
        raise ValueError("ff_playerids_crosswalk_invalid_json") from exc
    if not isinstance(payload, dict):
        raise ValueError("ff_playerids_payload_not_object")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("ff_playerids_entries_not_list")

    by_gsis = _CrosswalkIndex()
    by_sleeper = _CrosswalkIndex()
    duplicate_count = 0

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("ff_playerids_entry_not_object")
        gsis_id = _crosswalk_identifier(entry, "gsis_id")
        sleeper_id = _crosswalk_identifier(entry, "sleeper_id")

        # A row carrying neither identifier joins nothing. That is not an error and
        # not a duplicate — it simply never participates.
        if gsis_id is None and sleeper_id is None:
            continue

        if _is_identical_crosswalk_duplicate(entry, gsis_id, sleeper_id, by_gsis, by_sleeper):
            duplicate_count += 1
            continue

        # Validate both directions BEFORE committing either, so a rejected row never
        # leaves a half-written index behind. A conflicting mapping fails closed;
        # the pre-TW28 dict comprehensions resolved it by last-write-wins, silently
        # choosing one player's identity over another's.
        if gsis_id is not None and gsis_id in by_gsis:
            raise ValueError("ff_playerids_conflicting_gsis_mapping")
        if sleeper_id is not None and sleeper_id in by_sleeper:
            raise ValueError("ff_playerids_conflicting_sleeper_mapping")

        if gsis_id is not None:
            by_gsis[gsis_id] = entry
        if sleeper_id is not None:
            by_sleeper[sleeper_id] = entry

    by_gsis.duplicate_count = duplicate_count
    by_sleeper.duplicate_count = duplicate_count
    return by_gsis, by_sleeper


def _load_engine_b_feature_rows(path: Path = ENGINE_B_FEATURES_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    # DG-133: the inference partition is the assembler's inference SEASON, selected and
    # verified one-row-per-player by the shared selector. The former mask (the
    # complement of the training flag) also admitted every complete-window washout row
    # (kept with a null outcome since the attrition fix). On the live table that put
    # 1,114 keys in this dict where the partition has 505: 609 players whose only rows
    # were washouts were loaded — and handed to `score_rows` below — as if they were
    # this season's cohort, and the 20 players carrying both a washout row and a 2025
    # row kept the 2025 row only because file order put it last. The double prediction
    # that fired the collision guard came from `EngineBService` scoring every masked
    # ROW, not from this dict; the selector now refuses both shapes before either.
    inference = select_inference_partition(frame)
    rows: dict[str, dict[str, Any]] = {}
    for _, row in inference.iterrows():
        player_id = row.get("player_id")
        if pd.isna(player_id):
            continue
        raw = row.to_dict()
        rows[str(player_id)] = {
            key: (None if pd.isna(value) else value)
            for key, value in raw.items()
        }

    # P(plays) for the hurdle. The assembler multiplies the points projection by this, so
    # a player's served value becomes P(plays) x E[points | plays] rather than the second
    # factor alone. Absent for anyone the model cannot score, and apply_availability passes
    # an absent value through UNCHANGED rather than reading it as certain attrition.
    from src.dynasty_genius.models.availability import score_rows

    for player_id, probability in score_rows(rows, repo_root=ROOT).items():
        rows[player_id]["availability_p"] = probability
    return rows


class _ActivePvoBatch(list):
    """Active PVO rows, plus the identity-join accounting for the coverage report.

    ``main`` calls ``_active_pvos_from_engine_b()`` with no arguments, and an existing
    sibling contract (``tests/contract/test_pvo_refresh_runner.py``) replaces it with a
    zero-argument lambda returning a plain ``list``. Carrying the accounting on the
    returned list preserves both that arity and that return type, so hardening this
    producer cannot break a contract that predates it.
    """

    join_accounting: dict[str, Any]


def _orphan_record(
    gsis_id: str,
    ff_entry: dict[str, Any] | None,
    feature_row: dict[str, Any] | None,
    prediction: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    """One dropped prediction, described only by facts that actually exist.

    A value we do not have stays JSON null; nothing here is inferred from a name or
    filled in from a neighbouring row. When the crosswalk entry exists its facts win,
    because they are the join side that failed.
    """
    row = feature_row or {}
    if ff_entry is not None:
        name = ff_entry.get("name")
        position = ff_entry.get("position")
    else:
        name = row.get("full_name")
        position = row.get("position") or prediction.get("position")
    return {"gsis_id": gsis_id, "name": name, "position": position, "reason": reason}


def _active_pvos_from_engine_b() -> list[dict[str, Any]]:
    ff_by_gsis, _ = _load_ff_playerids()
    # DG-128: a missing or tampered snapshot aborts the refresh with a bare token, like a
    # missing crosswalk — the alternative is a universe where every veteran silently lost
    # his prior and the eight-game gate's blanks came back with no marker saying why.
    draft_capital = load_draft_capital(DRAFT_CAPITAL_PATH)
    # DG-128: the band's half-widths are pinned to two model runs. Before scoring a
    # single row, confirm those are the runs this tree serves — a retrain that moved a
    # manifest without moving the pin would otherwise ship a band describing a model
    # that no longer exists in the serving path, silently.
    assert_band_sigma_runs_match_served_models()
    # Resolve the feature source ONCE so the row-read and the predictions share a single,
    # consistent feature CSV (published runtime when available, else the committed seed).
    feature_source = resolve_feature_source(
        seed_path=ENGINE_B_FEATURES_PATH, runtime_dir=FEATURES_RUNTIME_DIR
    )
    feature_meta = feature_source.metadata()
    feature_rows = _load_engine_b_feature_rows(feature_source.path)
    predictions = score_inference_partition(feature_source=feature_source)
    if not predictions:
        raise ValueError("engine_b_predictions_empty")

    # Collapse repeated predictions on the gsis key BEFORE joining. The pre-TW28 loop
    # deduplicated on the SLEEPER side through a `seen_sleepers` set and said nothing
    # about what it dropped — the same silent-resolution defect as the crosswalk's
    # last-write-wins indexes. That set is gone rather than merely reported: because
    # conflicting Sleeper mappings now fail closed at parse time, two distinct gsis
    # can no longer resolve to one Sleeper id, so the condition it guarded is
    # unreachable.
    #
    # DG-133: this loop is a VALUE-collision guard, not a partition assertion. Two
    # equal predictions for one gsis pass it (counted, one kept); only unequal ones
    # raise. What guarantees one prediction per player is the partition selector
    # upstream (`select_inference_partition` inside `score_inference_partition`),
    # which refuses a duplicate player_id before anything is scored. This stays as
    # defence in depth for a prediction list assembled by some other path.
    unique_predictions: dict[str, dict[str, Any]] = {}
    prediction_duplicate_count = 0
    for prediction in predictions:
        raw_gsis = prediction.get("player_id")
        if not raw_gsis:
            # Not in the RED's rows. Failing closed is the deliberate choice: a
            # prediction with no identifier cannot be joined, reported as an orphan
            # (it has no key to sort or name), or dropped without repeating the exact
            # silence this unit removes.
            raise ValueError("engine_b_prediction_gsis_missing")
        gsis_key = str(raw_gsis)
        existing = unique_predictions.get(gsis_key)
        if existing is not None:
            if existing == prediction:
                prediction_duplicate_count += 1
                continue
            raise ValueError("engine_b_prediction_conflict")
        unique_predictions[gsis_key] = prediction

    pvo_objects: list[Any] = []
    orphan_records: list[dict[str, Any]] = []
    draft_capital_matched = 0
    draft_capital_unmatched = 0
    draft_capital_age_missing = 0

    for gsis_id, prediction in unique_predictions.items():
        ff_entry = ff_by_gsis.get(gsis_id)
        if ff_entry is None:
            orphan_records.append(
                _orphan_record(
                    gsis_id, None, feature_rows.get(gsis_id), prediction, "crosswalk_entry_missing"
                )
            )
            continue
        sleeper_id = _crosswalk_identifier(ff_entry, "sleeper_id")
        if sleeper_id is None:
            orphan_records.append(
                _orphan_record(
                    gsis_id, ff_entry, feature_rows.get(gsis_id), prediction, "sleeper_id_missing"
                )
            )
            continue

        features = feature_rows.get(str(gsis_id), {}).copy()
        features["engine_b_score"] = prediction
        # DG-128: hand the veteran his draft capital so the Phase 15 blend can fire for a
        # player under the eight-game gate. Three keys, never `age`: the feature row's
        # `age` is his CURRENT age and the assembler reads the draft-season age from
        # `age_at_nfl_entry` only. setdefault, so a feature column of the same name (none
        # exists today) would win over the snapshot rather than be silently overwritten.
        # No draft row means undrafted: no keys, no prior, counted — never imputed.
        capital = draft_capital.get(gsis_id)
        if capital is None:
            draft_capital_unmatched += 1
        else:
            draft_capital_matched += 1
            if capital.age is None:
                draft_capital_age_missing += 1
            for key, value in capital.engine_a_features().items():
                features.setdefault(key, value)
        identity = PlayerIdentity(
            dg_id=str(gsis_id),
            full_name=str(ff_entry.get("name") or gsis_id),
            position=str(ff_entry.get("position") or prediction.get("position") or features.get("position")),
            birth_date=ff_entry.get("birthdate"),
            nfl_team=prediction.get("team") or features.get("team"),
            sleeper_id=sleeper_id,
            pfr_id=ff_entry.get("pfr_id"),
            verification_status="VERIFIED",
            identity_verified=True,
            age_verified=bool(ff_entry.get("birthdate")),
        )
        pvo = assemble_pvo(
            identity,
            features=features,
            is_prospect=False,
            source_versions={
                "engine_b_features": str(feature_meta["feature_csv_path"]),
                "engine_b_feature_source_kind": str(feature_meta["feature_source_kind"]),
                "engine_b_feature_csv_sha256": str(feature_meta["feature_csv_sha256"]),
                "ff_playerids": str(FF_PLAYERIDS_PATH.relative_to(ROOT)),
                "draft_capital": "resources/draft_capital/nflverse_draft_picks.json",
                "draft_capital_sha256": draft_capital.content_sha256,
                # DG-128: the band's half-widths are pinned to these two runs; a
                # retrain that moves a manifest shows up here, not silently.
                "dvs_band_sigma_run_b": ENGINE_B_SIGMA_RUN,
                "dvs_band_sigma_run_a": ENGINE_A_SIGMA_RUN,
            },
        )
        pvo_objects.append(pvo)

    # Zero successful joins is refused. David's split rationale names the empty-board
    # publication risk directly, so an artifact carrying no model value at all does not
    # ship. This deliberately states NO partial-coverage floor: what fraction of missing
    # joins makes the artifact untrustworthy is a David-owned policy question (framing
    # v4 §0.2), and neither this code nor its comments assert that no threshold exists.
    if not pvo_objects:
        raise ValueError("engine_b_identity_join_zero_success")

    # DG-086: the within-position percentile is a POPULATION statistic, so it runs after
    # the whole join, on the objects, before any dump. compute_dvs_pct_batch is the one
    # authority (David 2026-08-29: wire it, no twin); it also stamps dvs_pct_as_of on the
    # objects. The stamp deliberately stays OUT of the published artifact: the capture
    # vintage excludes only top-level volatile row keys, so a wall-clock value inside a
    # row would mint a new semantic_output_hash on every rerun of the same content.
    compute_dvs_pct_batch(pvo_objects)
    pvos: list[dict[str, Any]] = [pvo.model_dump() for pvo in pvo_objects]

    batch = _ActivePvoBatch(pvos)
    batch.join_accounting = {
        # The raw input count, duplicates included — it answers "how many rows arrived",
        # which is a different question from how many distinct players were joined.
        "prediction_count": len(predictions),
        "join_success_count": len(pvos),
        "orphan_count": len(orphan_records),
        "orphan_records": sorted(orphan_records, key=lambda record: record["gsis_id"]),
        "crosswalk_duplicate_count": getattr(ff_by_gsis, "duplicate_count", 0),
        "prediction_duplicate_count": prediction_duplicate_count,
        # DG-128: who was handed draft capital. `unmatched` is "no draft row on this gsis" —
        # undrafted and unmatched are the same fact from here; the snapshot's own
        # accounting (indexed / gsis_missing / gsis_conflict) says how much of the source
        # was joinable at all.
        "draft_capital": {
            "matched_count": draft_capital_matched,
            "unmatched_count": draft_capital_unmatched,
            "age_missing_count": draft_capital_age_missing,
            **draft_capital.accounting,
        },
    }
    return batch


def main(argv: list[str] | None = None) -> None:
    # F-seed-split T2a: the output dir is now injectable so a scheduled refresh can steer the
    # producer at a temp/runtime location instead of the tracked seed dir. Default stays
    # OUTPUT_DIR for back-compat (a bare manual run still writes the tracked latest paths).
    parser = argparse.ArgumentParser(
        description="Build Phase 17.2 full-universe PVO batch artifacts."
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    snapshot = _load_json(SNAPSHOT_PATH)
    captured_at = datetime.now(timezone.utc).isoformat()
    active_pvos = _active_pvos_from_engine_b()
    batch = build_universe_pvo_batch(
        snapshot,
        prospect_pvos=_load_prospect_pvos(),
        active_pvos=active_pvos,
        captured_at=captured_at,
    )
    # Unit B: the identity-join accounting rides into the coverage report here rather
    # than inside `build_universe_pvo_batch`, which keeps this thread's change inside
    # the producer script and out of the shared batch module.
    #
    # The attribute is absent only when a caller has replaced the producer function
    # entirely (the sibling runner contract substitutes a plain list to bypass Engine B).
    # In that case no join ran, so there is no accounting to report — this is not a
    # silent skip of a real result.
    join_accounting = getattr(active_pvos, "join_accounting", None)
    if join_accounting is not None:
        batch["coverage"]["engine_b_identity_join"] = join_accounting
    run_id = args.run_id or datetime.now(timezone.utc).strftime("phase17-2-%Y%m%dT%H%M%SZ")
    paths = write_universe_pvo_artifacts(batch, output_dir=output_dir, run_id=run_id)
    print(f"Wrote Phase 17.2 universe PVO batch: {paths['batch']}")
    print(f"Wrote Phase 17.2 PVO coverage report: {paths['coverage']}")


if __name__ == "__main__":
    main(sys.argv[1:])
