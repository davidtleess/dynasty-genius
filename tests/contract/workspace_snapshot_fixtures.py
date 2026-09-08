"""Small coherent source set for archive tests; contains no live/private records."""

import hashlib
import json
from pathlib import Path

from tests.ranking.market_ranks_fixtures import synthetic_sources
from tests.ranking.test_roster_comparison import _row


def encoded(doc):
    return json.dumps(doc, sort_keys=True, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_sources(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    report, market, league = synthetic_sources()
    report["inputs"]["snapshot"]["sha256"] = sha(encoded(league))
    board = report["horizon_board"]
    board["davids_roster"] = [board["all_inspectable"][0]]
    board["annual_producers"] = [
        {
            "model_version": "union_replacement",
            "seasons": 5,
            "replacement": {
                "QB": [
                    {
                        "position": "QB",
                        "rate_ppg": 100.0,
                        "rate_quantity": "expected_season_points_same_window",
                        "player_name": "Synthetic reference",
                        "pool_complete": True,
                    }
                    for _ in range(5)
                ]
            },
        }
    ]
    catalog = {
        "run": "catalog-one",
        "source_report_run": "synthetic",
        "sources": {
            "report_run": "synthetic",
            "report_sha256": sha(encoded(report)),
            "snapshot_sha256": sha(encoded(league)),
        },
        "forecast_years": list(range(2026, 2031)),
        "future_years": list(range(2027, 2031)),
        "ownership_as_of": league["captured_at"],
        "nfl_status_as_of": league["captured_at"],
        "rows_detail": [
            _row(
                "1",
                "Synthetic 1",
                "QB",
                population="owned",
                owned_now=True,
                roster_id=1,
            ),
            _row("2", "Synthetic 2", "QB"),
            _row("3", "Synthetic 3", "QB"),
            _row("4", "Synthetic 4", "QB", population="cut"),
        ],
    }
    documents = {
        "report.json": report,
        "market.json": market,
        "league.json": league,
        "catalog.json": catalog,
    }
    for name, doc in documents.items():
        (root / name).write_bytes(encoded(doc))
    companion = {
        "run": "catalog-one",
        "source_report_run": "synthetic",
        "outputs_sha256": {"catalog.json": sha(encoded(catalog))},
    }
    (root / "catalog-companion.json").write_bytes(encoded(companion))
    manifest = {
        "schema_version": 1,
        "report_run": "synthetic",
        "files": {
            key: {
                "path": str(root / (key + ".json")),
                "sha256": sha(encoded(documents[key + ".json"])),
            }
            for key in ("report", "market", "league")
        },
    }
    (root / "source-manifest.json").write_bytes(encoded(manifest))
    return (
        root / "source-manifest.json",
        root / "catalog.json",
        root / "catalog-companion.json",
    )
