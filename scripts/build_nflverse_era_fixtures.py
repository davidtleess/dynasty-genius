"""Extract per-era column+dtype fingerprints and a complete witness cover of
REAL rows from archived nflverse raw snapshots.

Why this exists. Two ingestion defects this session were only ever findable by
running the code against reality: 2025 swapped `date_modified` for `season_type`
(a source ERA change), and the 2020 file types `season`/`week` as Float64 while
2021+ types them Int32. Neither a property test nor a mutation tool can discover
an era the fixtures do not contain — that ceiling is real and was named by both
lanes. A fingerprint pinned from ARCHIVED REAL SNAPSHOTS is what closes it.

What this writes, per stream and era:
  * an ordered column list and a per-column dtype-kind profile
  * a stable fingerprint hash over that shape
  * a COMPLETE WITNESS COVER — real rows chosen so every observed (column, kind)
    pair has at least one row to replay through capture -> normalize -> store -> export

nflverse is free and public, so unlike the PFF/PlayerProfiler manifests these
fixtures may carry real values. They are small by construction and are the
evidence a future shape change is measured against, not inferred from memory.

    .venv/bin/python3.14 scripts/build_nflverse_era_fixtures.py
    .venv/bin/python3.14 scripts/build_nflverse_era_fixtures.py --check
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW_ROOT = ROOT / "app" / "data" / "nflverse_usage" / "raw"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "nflverse_eras"


def _dtype_kind(value: Any) -> str:
    """A coarse, stable dtype label. Coarse on purpose: the contract is about
    int-vs-float-vs-text, which is exactly what broke, not about width."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def _column_profile(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Observed dtype kinds per column across the whole snapshot, sorted.

    Every kind is recorded, not just the first — a column that is int in one row
    and float in another is precisely the 2020 defect, and collapsing to the
    first observation would hide it.
    """
    kinds: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for column, value in record.items():
            kinds[column].add(_dtype_kind(value))
    return {column: sorted(values) for column, values in sorted(kinds.items())}


class HeterogeneousSnapshot(RuntimeError):
    """A snapshot whose records do not share one exact column set."""


def _exact_column_set(records: list[dict[str, Any]], where: str) -> tuple[str, ...]:
    """Every record must carry the SAME keys. Refuse, naming the row.

    Taking records[0] silently accepted a snapshot where a later row added or
    dropped a provider field, and then pinned a column list that did not describe
    the data (Codex R3-T1).
    """
    expected = set(records[0].keys())
    for index, record in enumerate(records):
        observed = set(record.keys())
        if observed != expected:
            raise HeterogeneousSnapshot(
                f"heterogeneous_snapshot: {where} record {index} — "
                f"unexpected {sorted(observed - expected)}, "
                f"missing {sorted(expected - observed)}"
            )
    return tuple(sorted(expected))


def _fingerprint(columns: list[str], profile: dict[str, list[str]]) -> str:
    payload = {"columns": columns, "dtype_kinds": profile}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def build() -> dict[str, Any]:
    """One entry per (stream, distinct column-set), keyed by fingerprint.

    Corrections from Codex review, each of which was a real defect:
      * T1 — the profile is CUMULATIVE across every row of every snapshot of a
        shape. The first version recomputed it per file and overwrote, so a kind
        seen only in an intervening season was forgotten (int, then str, then
        int yielded {'a': ['int']}).
      * T2 — kinds are recorded PER SEASON as well as merged. A union alone lets
        a season change int->float undetected because the other season already
        contributed float; the union is descriptive metadata, the per-season
        profile is the identity a preflight compares against.
      * T4 — fixture rows are retained PER SEASON, so every pinned dtype variant
        has archived-real rows to replay. Taking them from the first snapshot
        only meant the 2020-2024 injuries fixture carried float rows and the
        later int variant was metadata that never ran.
      * T6 — every source snapshot is content-hashed, so provenance does not rest
        on a mutable directory path.
    """
    by_shape: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}

    for path in sorted(glob.glob(str(RAW_ROOT / "*.json"))):
        raw_bytes = Path(path).read_bytes()
        envelope = json.loads(raw_bytes.decode("utf-8"))
        records = envelope.get("records") or []
        if not records:
            continue
        stream = envelope["stream"]
        season = str(envelope["season"])
        # R3-T1: infer the column set from EVERY record, not records[0]. A field
        # present only on a later row was landing in the dtype map while being
        # omitted from `columns` — the same heterogeneous-batch defect just
        # closed in normalize_rows, reintroduced one layer earlier.
        columns = _exact_column_set(records, f"{stream} {season} {Path(path).name}")
        key = (stream, columns)
        entry = by_shape.setdefault(
            key,
            {
                "stream": stream,
                "columns": list(columns),
                "seasons": set(),
                "rows_by_season": {},
                "kinds_cumulative": defaultdict(set),
                "kinds_by_season": defaultdict(lambda: defaultdict(set)),
                "covered_by_season": {},
                "row_counts": {},
                "sources": {},
            },
        )
        entry["seasons"].add(int(envelope["season"]))
        entry["row_counts"][season] = len(records)
        entry["sources"].setdefault(season, []).append(
            {
                "file": Path(path).name,
                "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                "rows": len(records),
            }
        )
        # T1: accumulate over EVERY row of EVERY snapshot, never overwrite.
        # T2: and keep the same evidence broken out per season.
        for record in records:
            for column, value in record.items():
                kind = _dtype_kind(value)
                entry["kinds_cumulative"][column].add(kind)
                entry["kinds_by_season"][season][column].add(kind)
        # R3-T3: a deterministic GREEDY COVER over every observed (column, kind)
        # pair for this season, not "the first five rows of the first snapshot"
        # (which left 64 pinned variants with no archived row to replay).
        # Greedy, NOT minimal: it takes rows in file order and keeps any that
        # contribute an unseen pair. That is complete and reproducible, but it is
        # not a minimum set cover and must not be described as one.
        entry["rows_by_season"].setdefault(season, [])
        entry["covered_by_season"].setdefault(season, set())
        covered = entry["covered_by_season"][season]
        chosen = entry["rows_by_season"][season]
        for record in records:
            needed = {
                (column, _dtype_kind(value))
                for column, value in record.items()
                if (column, _dtype_kind(value)) not in covered
            }
            if needed:
                chosen.append(record)
                covered |= {
                    (column, _dtype_kind(value)) for column, value in record.items()
                }

    shapes = []
    for entry in by_shape.values():
        cumulative = {
            column: sorted(kinds)
            for column, kinds in sorted(entry["kinds_cumulative"].items())
        }
        by_season = {
            season: {
                column: sorted(kinds) for column, kinds in sorted(columns.items())
            }
            for season, columns in sorted(entry["kinds_by_season"].items())
        }
        fixture_rows = [
            row for season in sorted(entry["rows_by_season"])
            for row in entry["rows_by_season"][season]
        ]
        shapes.append(
            {
                "stream": entry["stream"],
                "seasons": sorted(entry["seasons"]),
                "columns": entry["columns"],
                "dtype_kinds": cumulative,
                "dtype_kinds_by_season": by_season,
                "fingerprint": _fingerprint(entry["columns"], cumulative),
                "row_counts_by_season": entry["row_counts"],
                "source_snapshots": {
                    season: sorted(files, key=lambda f: f["file"])
                    for season, files in sorted(entry["sources"].items())
                },
                "fixture_rows": fixture_rows,
                "fixture_rows_by_season": {
                    season: rows for season, rows in sorted(entry["rows_by_season"].items())
                },
            }
        )
    shapes.sort(key=lambda s: (s["stream"], s["seasons"]))
    return {
        "contract_version": "nflverse-era-fixtures.v2",
        "source": "archived raw snapshots under app/data/nflverse_usage/raw",
        "witness_selection": "deterministic_greedy_column_kind_cover",
        "shapes": shapes,
    }


def _write(bundle: dict[str, Any]) -> None:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    (FIXTURE_ROOT / "era_fingerprints.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def contract_of(shapes: list[dict[str, Any]]) -> dict:
    """CONTRACT identity — columns + per-season dtype profiles, keyed by fingerprint.

    A change here means the provider shape moved. That is always a failure.
    """
    return {
        s["fingerprint"]: {
            "stream": s["stream"],
            "seasons": s["seasons"],
            "columns": s["columns"],
            "dtype_kinds": s["dtype_kinds"],
            "dtype_kinds_by_season": s["dtype_kinds_by_season"],
        }
        for s in shapes
    }


def sources_of(shapes: list[dict[str, Any]]) -> dict:
    """PROVENANCE — which snapshot files exist, and their content hash."""
    return {
        (s["stream"], season, f["file"]): f["sha256"]
        for s in shapes
        for season, files in s["source_snapshots"].items()
        for f in files
    }


def provenance_verdict(live: dict, pinned: dict) -> tuple[bool, dict]:
    """Three distinct provenance transitions, deliberately NOT one verdict.

    R3-T2 was corrected twice. The first version treated any provenance move as
    contract drift, so `--check` failed for the most ordinary reason there is:
    someone ran a capture. A check that cries wolf on normal operation gets
    ignored, which is the failure mode it exists to prevent.

    The second version over-corrected: a REMOVED pinned source exited 0, and the
    success line still counted it among "content-verified" snapshots — reporting
    files it had never read as verified. Deleting evidence the committed bundle
    names is not the same event as adding a capture, and must not pass.

      * tampered — a pinned file's content changed        -> FAIL
      * removed  — a pinned file is gone; unverifiable    -> FAIL
      * added    — a new unpinned file, shape unchanged   -> pass, with a note
    """
    tampered = sorted(k for k in pinned.keys() & live.keys() if pinned[k] != live[k])
    removed = sorted(pinned.keys() - live.keys())
    added = sorted(live.keys() - pinned.keys())
    return (not tampered and not removed), {
        "tampered": tampered,
        "removed": removed,
        "added": added,
        "verified": sorted(k for k in pinned.keys() & live.keys() if pinned[k] == live[k]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Recompute and compare against the committed fixture; write nothing.",
    )
    args = parser.parse_args(argv)

    bundle = build()
    if not bundle["shapes"]:
        print("no archived raw snapshots found — nothing to fingerprint")
        return 1

    target = FIXTURE_ROOT / "era_fingerprints.json"
    if args.check:
        if not target.exists():
            print(f"missing {target}")
            return 1
        committed = json.loads(target.read_text(encoding="utf-8"))
        live = {s["fingerprint"] for s in bundle["shapes"]}
        pinned = {s["fingerprint"] for s in committed["shapes"]}
        if live != pinned:
            print("FINGERPRINT DRIFT")
            print(f"  new shapes:     {sorted(live - pinned)}")
            print(f"  missing shapes: {sorted(pinned - live)}")
            return 1
        # R3-T2, corrected again after its own positive control failed on the
        # BASELINE. The first version conflated two different things:
        #   CONTRACT identity — columns + per-season dtype profiles. A change here
        #                       means the provider shape moved. That is a failure.
        #   PROVENANCE        — which snapshot files exist. Every capture adds
        #                       snapshots, so a same-shape addition is NORMAL and
        #                       must not read as contract drift.
        # Conflating them made `--check` fail routinely for the most ordinary
        # reason there is: someone ran a capture. A check that cries wolf on
        # normal operation gets ignored, which is the failure mode it exists to
        # prevent. Content CHANGE on a pinned source is still tampering and fails.
        live_contract, pinned_contract = contract_of(bundle["shapes"]), contract_of(
            committed["shapes"]
        )
        if live_contract != pinned_contract:
            print("CONTRACT DRIFT — the provider shape moved")
            for fp in sorted(set(live_contract) | set(pinned_contract)):
                live_entry, pinned_entry = live_contract.get(fp), pinned_contract.get(fp)
                if live_entry == pinned_entry:
                    continue
                if pinned_entry is None:
                    print(f"  NEW shape {fp[:12]} ({live_entry['stream']})")
                elif live_entry is None:
                    print(f"  MISSING shape {fp[:12]} ({pinned_entry['stream']})")
                else:
                    for field in sorted(pinned_entry):
                        if pinned_entry[field] != live_entry[field]:
                            print(f"  shape {fp[:12]} {field} differs")
            return 1

        live_sources, pinned_sources = sources_of(bundle["shapes"]), sources_of(
            committed["shapes"]
        )
        ok, detail = provenance_verdict(live_sources, pinned_sources)
        if not ok:
            if detail["tampered"]:
                print(
                    f"PROVENANCE TAMPER — {len(detail['tampered'])} pinned "
                    "snapshot(s) changed content"
                )
                for key in detail["tampered"][:5]:
                    print(f"  {key}")
            if detail["removed"]:
                print(
                    f"PROVENANCE LOSS — {len(detail['removed'])} pinned snapshot(s) "
                    "named by the committed bundle are absent; they cannot be "
                    "content-verified"
                )
                for key in detail["removed"][:5]:
                    print(f"  {key}")
            return 1

        # Count what was actually read and matched — NOT len(pinned_sources).
        print(
            f"ok — {len(pinned_contract)} shapes match; "
            f"{len(detail['verified'])} pinned snapshots content-verified"
        )
        if detail["added"]:
            print(
                f"  note: {len(detail['added'])} snapshot(s) present but UNPINNED, "
                "with no shape change — normal after a capture; re-pin when convenient"
            )
        return 0

    _write(bundle)
    for shape in bundle["shapes"]:
        print(
            f"  {shape['stream']:<14} seasons={shape['seasons']} "
            f"cols={len(shape['columns'])} fp={shape['fingerprint'][:12]}"
        )
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
