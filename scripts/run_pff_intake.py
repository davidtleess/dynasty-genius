"""PFF manual-drop intake — the operator-callable control plane.

A library nobody can invoke is not ingestion. This is the command that makes the PFF manual route
real, so `daily_control` can stop reporting `missing_importer`.

    # index a new manual drop, described by an explicit sidecar
    .venv/bin/python3.14 scripts/run_pff_intake.py --batch-manifest app/data/pff_exports/inbox/batch-001.json

    # index the payloads already held in the canonical tree, in place
    .venv/bin/python3.14 scripts/run_pff_intake.py --backfill-existing \
        --inventory-csv app/data/pff_exports/pff_unique_payload_inventory.csv \
        --download-map-csv app/data/pff_exports/pff_download_file_map.csv

EXIT CODES ARE THE TRANSPORT AXIS, NOT DATA QUALITY.
    0  the batch was durably preserved and the metadata transaction committed — INCLUDING when
       `review_state=review_required`, because an unrecognised schema that was safely quarantined
       and indexed is still a real acquisition. Exiting nonzero there would teach a scheduler to
       treat a genuine manual download as a failed job.
    nonzero  a durability or commit failure, an invalid sidecar, an identity conflict, or backfill
       corruption.

THERE IS NO NETWORK PATH HERE. PFF is a manual_download source: a human exports the files. This
script reads local files and writes a local SQLite ledger, and nothing else.

It installs nothing, schedules nothing, contacts nobody, and spends no money.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.sources.pff_intake import (  # noqa: E402
    PFFIntakeError,
    backfill,
    intake,
)

#: The human drop point, declared explicitly. It is NOT the canonical raw destination (that is the
#: content-addressed store this tool writes) and it is NOT an inferred `~/Downloads` — inferring a
#: location is the same defect as inferring provenance from a filename.
DEFAULT_INBOX = ROOT / "app" / "data" / "pff_exports" / "inbox"
DEFAULT_STORE_ROOT = ROOT / "app" / "data" / "pff_exports"
DEFAULT_LEDGER = ROOT / "app" / "data" / "pff_exports" / "pff_metadata.db"
DEFAULT_STATUS_MARKER = ROOT / "app" / "data" / "ops" / "pff_intake_status_latest.json"
DEFAULT_READY_MARKER = ROOT / "app" / "data" / "ops" / "pff_intake.ready.json"
#: The GOVERNED schema catalog. Defaulting this to None meant the canonical invocation quarantined
#: every payload — including schemas the catalog already recognises — so the documented production
#: route would have flagged all 149 for review. Absent or malformed, the set is empty, which
#: quarantines rather than blesses: the failure direction stays fail-safe.
DEFAULT_SCHEMA_CATALOG = ROOT / "app" / "data" / "pff_exports" / "pff_schema_catalog.json"


class IsolationError(RuntimeError):
    """An isolated run tried to keep a production default."""


def _resolve_paths(args) -> dict:
    """Resolve every path coherently, and REFUSE a run that mixes isolated and production paths.

    THE DEFECT THIS PREVENTS, observed for real: a verification run passed a temporary
    --ledger-path and --store-root but left the marker paths at their defaults. It therefore wrote
    SYNTHETIC fixture timestamps into the live app/data/ops markers, overwriting a real freshness
    clock with a vintage the production ledger had never seen. The same hole is worse for the
    store: a custom --ledger-path with a default --store-root copies payload BYTES into the
    governed content-addressed archive.

    Two rules:
      1. Everything derives from --repo-root, so relocating the root relocates the whole run.
      2. If the ledger or store is moved OUTSIDE the resolved production tree, the run is ISOLATED
         and its markers must be given explicitly. Silence is refused rather than guessed, because
         a wrong guess writes into production.
    """
    repo_root = Path(args.repo_root).resolve()

    # The EXACT canonical production pair for this repo root. Isolation is any deviation from it —
    # not merely "outside app/data". That looser test still allowed a custom ledger or store
    # INSIDE app/data to write the production clock, and let a test ledger be mixed with the
    # governed raw store.
    canonical_store = (repo_root / "app" / "data" / "pff_exports").resolve()
    canonical_ledger = (canonical_store / "pff_metadata.db").resolve()

    store_root = Path(args.store_root).resolve() if args.store_root else canonical_store
    ledger = Path(args.ledger_path).resolve() if args.ledger_path else (store_root / "pff_metadata.db").resolve()

    isolated = store_root != canonical_store or ledger != canonical_ledger

    status_given, ready_given = args.status_marker is not None, args.ready_marker is not None
    if status_given != ready_given:
        raise IsolationError(
            "--status-marker and --ready-marker must be given together: the latest-attempt and "
            "last-good clocks are one contract, and splitting them across roots would leave a "
            "last-good vintage that no status marker corresponds to"
        )
    if isolated and not status_given:
        raise IsolationError(
            "isolated run refused: the resolved store/ledger pair differs from the canonical "
            f"production pair ({canonical_store}, {canonical_ledger}), but the marker paths are "
            "still production defaults "
            f"({DEFAULT_STATUS_MARKER.name}, {DEFAULT_READY_MARKER.name}). Pass explicit "
            "--status-marker and --ready-marker so a non-production run cannot overwrite the real "
            "freshness clock."
        )

    return {
        "repo_root": repo_root,
        "store_root": Path(store_root),
        "ledger_path": Path(ledger),
        "status_marker": Path(args.status_marker) if status_given
                         else repo_root / "app" / "data" / "ops" / DEFAULT_STATUS_MARKER.name,
        "ready_marker": Path(args.ready_marker) if ready_given
                        else repo_root / "app" / "data" / "ops" / DEFAULT_READY_MARKER.name,
    }


def _load_known_schemas(path: Path | None) -> set[str]:
    """The governed catalog of recognised schemas.

    Absent a catalog the set is empty, which quarantines everything for review. That is the honest
    failure direction: an unrecognised payload is preserved and flagged, never silently blessed.
    """
    if path is None or not Path(path).is_file():
        return set()
    try:
        doc = json.loads(Path(path).read_text())
    except (json.JSONDecodeError, OSError):
        # Malformed catalog => empty set => everything quarantines for review. Never bless.
        return set()
    entries = doc if isinstance(doc, list) else doc.get("schemas", [])
    out: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            out.add(entry)
        elif isinstance(entry, dict):
            value = entry.get("schema_sha256") or entry.get("schema_sha")
            if value:
                out.add(str(value))
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_pff_intake.py",
        description="Index PFF manual-drop payloads into the Layer 1 metadata ledger.",
    )
    parser.add_argument("--batch-manifest", type=Path, default=None,
                        help="sidecar declaring each offering's provenance (never inferred)")
    parser.add_argument("--backfill-existing", action="store_true",
                        help="index the already-canonical payloads IN PLACE (no copy, no rewrite)")
    parser.add_argument("--inventory-csv", type=Path, default=None,
                        help="governed unique-payload inventory (backfill mode)")
    parser.add_argument("--download-map-csv", type=Path, default=None,
                        help="governed download/offering map (backfill mode)")
    parser.add_argument("--store-root", type=Path, default=None,
                        help="canonical content-addressed root")
    parser.add_argument("--ledger-path", type=Path, default=None,
                        help="private SQLite METADATA ledger (no paid payload rows)")
    parser.add_argument("--status-marker", type=Path, default=None,
                        help="latest-attempt marker")
    parser.add_argument("--ready-marker", type=Path, default=None,
                        help="last-good marker; advances only on transport success")
    parser.add_argument("--repo-root", type=Path, default=ROOT,
                        help="anchor for repo-relative canonical paths")
    parser.add_argument("--known-schema-catalog", type=Path, default=DEFAULT_SCHEMA_CATALOG,
                        help="governed catalog of recognised schema hashes "
                             f"(default: {DEFAULT_SCHEMA_CATALOG})")
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX,
                        help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = _resolve_paths(args)
    except IsolationError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    if args.backfill_existing:
        if args.inventory_csv is None or args.download_map_csv is None:
            print("--backfill-existing requires --inventory-csv and --download-map-csv",
                  file=sys.stderr)
            return 2
        result = backfill(
            inventory_csv=args.inventory_csv,
            download_map_csv=args.download_map_csv,
            ledger_path=paths["ledger_path"],
            repo_root=paths["repo_root"],
            store_root=paths["store_root"],
            marker_path=paths["status_marker"],
            ready_marker_path=paths["ready_marker"],
        )
        print(json.dumps(result.as_summary(), indent=2, sort_keys=True))
        return 0 if result.status == "ok" else 1

    if args.batch_manifest is None:
        print("either --batch-manifest or --backfill-existing is required", file=sys.stderr)
        return 2

    try:
        result = intake(
            batch_manifest=args.batch_manifest,
            store_root=paths["store_root"],
            ledger_path=paths["ledger_path"],
            marker_path=paths["status_marker"],
            ready_marker_path=paths["ready_marker"],
            repo_root=paths["repo_root"],
            known_schemas=_load_known_schemas(args.known_schema_catalog),
        )
    except PFFIntakeError as exc:
        # An invalid sidecar and an identity conflict are both refusals to accept the batch as
        # offered. Neither is a partial success.
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result.as_summary(), indent=2, sort_keys=True))
    # review_required does NOT change the exit code: transport succeeded.
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
