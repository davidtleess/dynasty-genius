"""Build Phase 17.2 full-universe PVO batch artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.engine_b_service import score_inference_partition  # noqa: E402
from src.dynasty_genius.models.player_identity import PlayerIdentity  # noqa: E402
from src.dynasty_genius.pvo_assembler import assemble_pvo  # noqa: E402
from src.dynasty_genius.universe_pvo_batch import (  # noqa: E402
    build_universe_pvo_batch,
    write_universe_pvo_artifacts,
)

SNAPSHOT_PATH = ROOT / "app" / "data" / "league_snapshots" / "sleeper_universe_snapshot_latest.json"
PROSPECT_CARDS_PATH = ROOT / "resources" / "prospect_cards.json"
FF_PLAYERIDS_PATH = ROOT / "app" / "data" / "identity" / "_runs" / "ff_playerids_20260516.json"
ENGINE_B_FEATURES_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _load_prospect_pvos(path: Path = PROSPECT_CARDS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cards = _load_json(path)
    return [card for card in cards if card.get("sleeper_id")]


def _load_ff_playerids(path: Path = FF_PLAYERIDS_PATH) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not path.exists():
        return {}, {}
    payload = _load_json(path)
    entries = payload.get("entries") or []
    by_gsis = {
        str(entry["gsis_id"]): entry
        for entry in entries
        if entry.get("gsis_id")
    }
    by_sleeper = {
        str(entry["sleeper_id"]): entry
        for entry in entries
        if entry.get("sleeper_id")
    }
    return by_gsis, by_sleeper


def _load_engine_b_feature_rows(path: Path = ENGINE_B_FEATURES_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    inference = frame[frame["training_eligible"] == False].copy()  # noqa: E712
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
    return rows


def _active_pvos_from_engine_b() -> list[dict[str, Any]]:
    ff_by_gsis, _ = _load_ff_playerids()
    feature_rows = _load_engine_b_feature_rows()
    predictions = score_inference_partition()
    pvos: list[dict[str, Any]] = []
    seen_sleepers: set[str] = set()

    for prediction in predictions:
        gsis_id = prediction.get("player_id")
        if not gsis_id:
            continue
        ff_entry = ff_by_gsis.get(str(gsis_id))
        if not ff_entry or not ff_entry.get("sleeper_id"):
            continue
        sleeper_id = str(ff_entry["sleeper_id"])
        if sleeper_id in seen_sleepers:
            continue
        seen_sleepers.add(sleeper_id)

        features = feature_rows.get(str(gsis_id), {}).copy()
        features["engine_b_score"] = prediction
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
                "engine_b_features": str(ENGINE_B_FEATURES_PATH.relative_to(ROOT)),
                "ff_playerids": str(FF_PLAYERIDS_PATH.relative_to(ROOT)),
            },
        )
        pvos.append(pvo.model_dump())

    return pvos


def main() -> None:
    snapshot = _load_json(SNAPSHOT_PATH)
    captured_at = datetime.now(timezone.utc).isoformat()
    batch = build_universe_pvo_batch(
        snapshot,
        prospect_pvos=_load_prospect_pvos(),
        active_pvos=_active_pvos_from_engine_b(),
        captured_at=captured_at,
    )
    run_id = datetime.now(timezone.utc).strftime("phase17-2-%Y%m%dT%H%M%SZ")
    paths = write_universe_pvo_artifacts(batch, output_dir=OUTPUT_DIR, run_id=run_id)
    print(f"Wrote Phase 17.2 universe PVO batch: {paths['batch']}")
    print(f"Wrote Phase 17.2 PVO coverage report: {paths['coverage']}")


if __name__ == "__main__":
    main()
