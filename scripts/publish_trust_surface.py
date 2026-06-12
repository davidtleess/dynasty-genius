"""Publish the governed, provenance-matched trust substrate (Model Trust Console T1).

Copies the four **explicitly pinned** source ``BacktestResult`` runs (one per
position) from the local, gitignored ``app/data/backtest/runs/`` into the tracked,
governed published path ``app/data/backtest/trust_surface/latest/``, and writes a
provenance ``manifest.json``. Deterministic + re-runnable: source runs are pinned
(never "newest valid"), and the publication timestamp is a fixed input.

Descriptive / diagnostic only — ``decision_supported`` is absent/false on every
published artifact + manifest entry. No model/training code is touched.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.dynasty_genius.eval.backtest_artifact import BacktestResult

POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE")

# Pinned source runs for the v1 published substrate (the coherent 2026-05-31 G3 batch).
# Explicit pins — NOT auto-selected by run-date. The T1 audit asserts the published
# manifest run_ids equal these.
PINNED_RUN_IDS: dict[str, str] = {
    "QB": "483f87f9-1a16-4750-a825-0165c7335696",
    "RB": "e639a40c-e88b-4650-ab90-0e8f02fd397d",
    "WR": "fc1e6e1c-180a-4c0b-b93b-cb525ef404f1",
    "TE": "6ba3a451-67be-42e8-a431-c9c3130b3086",
}

# Fixed publication timestamp (deterministic; re-running yields the same manifest).
PUBLICATION_TIMESTAMP = "2026-06-10T00:00:00Z"

SOURCE_VALIDATION_NOTE = (
    "G3 ECR validation run (2026-05-31 batch); descriptive/diagnostic only; "
    "decision support disabled."
)

RUNS_DIR = Path("app/data/backtest/runs")
MODEL_CARDS_DIR = Path("app/data/backtest/model_cards")
PUBLISHED_DIR = Path("app/data/backtest/trust_surface/latest")


def _source_artifact_path(position: str) -> Path:
    return RUNS_DIR / PINNED_RUN_IDS[position] / f"backtest_result_{position}.json"


def publish(
    *,
    runs_dir: Path = RUNS_DIR,
    published_dir: Path = PUBLISHED_DIR,
    publication_timestamp: str = PUBLICATION_TIMESTAMP,
) -> dict[str, object]:
    """Publish the 4 pinned BacktestResult + manifest. Returns the publish report."""
    published_dir.mkdir(parents=True, exist_ok=True)

    manifest_positions: dict[str, dict[str, object]] = {}
    published_files: list[str] = []

    for position in POSITIONS:
        source = runs_dir / PINNED_RUN_IDS[position] / f"backtest_result_{position}.json"
        if not source.is_file():
            raise FileNotFoundError(
                f"pinned source run for {position} not found: {source}"
            )
        artifact = BacktestResult.load(source)
        if str(artifact.run_id) != PINNED_RUN_IDS[position]:
            raise ValueError(
                f"{position}: source artifact run_id {artifact.run_id} "
                f"!= pinned {PINNED_RUN_IDS[position]}"
            )

        dest = published_dir / f"backtest_result_{position}.json"
        shutil.copyfile(source, dest)  # byte-identical to the pinned source run
        published_files.append(dest.name)

        manifest_positions[position] = {
            "source_validation_note": SOURCE_VALIDATION_NOTE,
            "run_id": str(artifact.run_id),
            "run_date": artifact.run_date.isoformat(),
            "git_sha": artifact.git_sha,
            "model_version": artifact.model_version,
            "model_artifact_hash": artifact.model_artifact_hash,
            "market_source": artifact.market_source,
            "market_source_label": artifact.market_source_label,
            "publication_timestamp": publication_timestamp,
            "decision_supported": False,
        }

        # PublishedModelCardSource: the model card's safety text stamped with the
        # PUBLISHED run's provenance. Guard: the card must describe the SAME model
        # version as the published validation run (the honest model-identity check).
        card_path = MODEL_CARDS_DIR / f"{position}_model_card.json"
        if not card_path.is_file():
            raise FileNotFoundError(f"model card for {position} not found: {card_path}")
        card = json.loads(card_path.read_text(encoding="utf-8"))
        if card.get("model_version") != artifact.model_version:
            raise ValueError(
                f"{position}: model card model_version {card.get('model_version')!r} "
                f"!= published {artifact.model_version!r}"
            )
        card_source = {
            "position": position,
            "backtest_run_id": str(artifact.run_id),
            "generated_at": card.get("generated_at"),
            "is_experimental": artifact.promotion_gate.overall_grade == "EXPERIMENTAL",
            "intended_use": card["intended_use"],
            "out_of_scope_uses": card["out_of_scope_uses"],
            "caveats": card["caveats"],
            "known_failure_modes": card["known_failure_modes"],
            "model_version": artifact.model_version,
            "model_artifact_hash": artifact.model_artifact_hash,
            "git_sha": artifact.git_sha,
        }
        source_dest = published_dir / f"model_card_source_{position}.json"
        source_dest.write_text(
            json.dumps(card_source, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        published_files.append(source_dest.name)

    manifest_path = published_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"positions": manifest_positions}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    published_files.append(manifest_path.name)

    # Stat/diff guard: report exactly what landed so broad runs/ contents can't slip in.
    on_disk = sorted(p.name for p in published_dir.iterdir() if p.is_file())
    report = {
        "published_dir": str(published_dir),
        "published_files": sorted(published_files),
        "on_disk_files": on_disk,
        "pinned_run_ids": dict(PINNED_RUN_IDS),
    }
    return report


def main() -> None:
    report = publish()
    print(json.dumps(report, indent=2, sort_keys=True))
    extra = set(report["on_disk_files"]) - set(report["published_files"])
    if extra:
        raise SystemExit(f"stat/diff guard: unexpected files in published path: {sorted(extra)}")


if __name__ == "__main__":
    main()
