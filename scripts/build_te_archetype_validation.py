#!/usr/bin/env python3
"""Build the Phase 13.3 TE archetype validation artifact."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.audit.te_archetype_validation import (  # noqa: E402
    build_te_archetype_validation_artifact,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_eligible(path: Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    return list(data["eligible"])


def _load_predictions(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_validation_from_files(
    *,
    archetype_path: Path,
    eligible_path: Path,
    predictions_path: Path,
    out_path: Path,
    run_id: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    artifact = build_te_archetype_validation_artifact(
        _load_json(archetype_path),
        eligible_rows=_load_eligible(eligible_path),
        prediction_rows=_load_predictions(predictions_path),
        run_id=run_id,
        prediction_source=predictions_path.as_posix(),
        generated_at=generated_at or _utc_timestamp(),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build TE archetype validation aggregate artifact.")
    parser.add_argument("--archetype", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_archetype_validation_20260516")
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    artifact = build_validation_from_files(
        archetype_path=args.archetype,
        eligible_path=args.eligible_manifest,
        predictions_path=args.predictions,
        out_path=args.out,
        run_id=args.run_id,
        generated_at=args.generated_at,
    )
    metadata = artifact["metadata"]
    print(
        f"TE archetype validation written: {args.out} "
        f"matched_labeled={metadata['matched_labeled_prediction_rows']} "
        f"unique={metadata['matched_labeled_unique_players']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
