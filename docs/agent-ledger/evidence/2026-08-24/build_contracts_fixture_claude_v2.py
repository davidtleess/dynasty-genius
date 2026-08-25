"""Regenerator for `tests/fixtures/contracts_slice.json` — v2, post-rename (DG-040).

The contracts upstream changed shape between 2026-08-08 and 2026-08-21: `cols` (List(Struct)
of 13 cap fields) is now published as `season_history` — same 13 fields, same trailing
non-numeric 'Total' row — plus a genuinely new `contract_history` List(Struct) of 11 fields.
`nflreadpy` is unchanged at 0.1.5; the DATA release moved. v1 of this generator sliced a live
`load_contracts()` frame; v2 slices a RAW CAPTURE BLOB instead, because the blob is retained
in `app/data/nflverse_usage/raw/` and therefore reproducible, while the live source MOVES
(v1's own measurement: 51,803 vs 51,808 rows in one session).

Same selection rule as v1, and each clause keeps a contract path testable:
  1. Every row of the 40 lowest-sorted `otc_id` values.
  2. Plus, if absent from that slice, one row of each of: an exact-duplicate PAIR; a null
     `gsis_id` (the `unknown` identity path); `year_signed == 0` (preserved literally); a null
     `season_history` (SQL NULL, never the string "null" — measured 2026-08-24: 62 rows null,
     and every one of them is null in BOTH nested columns).
  3. Nested lists are NEVER sorted; order is preserved exactly. `season_history.year` is not
     always numeric (the trailing 'Total').

Usage:
  .venv/bin/python3.14 docs/agent-ledger/evidence/2026-08-24/build_contracts_fixture_claude_v2.py \
      --raw app/data/nflverse_usage/raw/contracts_<run>.json           # write fixture+manifest
  ... --raw <same> --check                                             # verify byte-identical
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if not (REPO_ROOT / "src" / "dynasty_genius").is_dir():
    raise SystemExit(f"repo root derivation failed: {REPO_ROOT} has no src/dynasty_genius")

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "contracts_slice.json"
SEASON_HISTORY_FIELDS = (
    "year", "team", "base_salary", "prorated_bonus", "roster_bonus", "guaranteed_salary",
    "cap_number", "cap_percent", "cash_paid", "workout_bonus", "other_bonus",
    "per_game_roster_bonus", "option_bonus",
)
CONTRACT_HISTORY_FIELDS = (
    "team", "contract_type", "status", "year_signed", "yrs", "total", "apy", "guarantees",
    "amount_earned", "percent_earned", "effective_apy",
)
NESTED_COLUMNS = ("season_history", "contract_history")
JSON_SCALARS = (str, int, float, bool, type(None))


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nflreadpy")
    except PackageNotFoundError:  # pragma: no cover
        return "unknown"


def _validate_nested(value, expected: tuple[str, ...], column: str) -> None:
    """Validated, never coerced — a non-JSON-scalar or off-shape entry must RAISE (Codex R10)."""
    if value is None:
        return
    if not isinstance(value, list):
        raise TypeError(f"{column} is {type(value).__name__}, expected a list of mappings")
    for entry in value:
        if not isinstance(entry, dict):
            raise TypeError(f"{column} entry is {type(entry).__name__}, expected a mapping")
        if set(entry) != set(expected):
            raise TypeError(f"{column} entry fields {sorted(entry)} != declared {sorted(expected)}")
        for key, inner in entry.items():
            if not isinstance(inner, JSON_SCALARS):
                raise TypeError(f"{column} field {key!r} is {type(inner).__name__}, not JSON scalar")


def _dumps(obj) -> str:
    """Strict JSON: sorted keys, compact separators, no NaN, and NO fallback encoder."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(row) -> str:
    return _dumps(row)


def _iter_records(raw_path: Path):
    """Stream records out of a raw capture blob without loading 1.7 GB of parsed objects."""
    text = raw_path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    head_end = text.index('"records": [')
    envelope = json.loads(text[: head_end].rstrip().rstrip(",") + "}")
    i = text.index("[", head_end) + 1
    while True:
        while i < len(text) and text[i] in " \n\t\r,":
            i += 1
        if i >= len(text) or text[i] == "]":
            break
        record, i = decoder.raw_decode(text, i)
        yield envelope, record


def build(raw_path: Path):
    envelope = None
    records_seen = 0
    ids_census: set[int] = set()
    # Pass 1: the 40 lowest otc_ids require the full id census first.
    for env, record in _iter_records(raw_path):
        envelope = env
        records_seen += 1
        if record.get("otc_id") is not None:
            ids_census.add(record["otc_id"])
    ids = sorted(ids_census)[:40]
    id_set = set(ids)

    chosen: list[dict] = []
    fallbacks = {"exact_duplicate": None, "null_gsis": None,
                 "year_signed_zero": None, "null_season_history": None}
    all_fp = Counter()
    dup_row = None
    for _, record in _iter_records(raw_path):
        for column, fields in (("season_history", SEASON_HISTORY_FIELDS),
                               ("contract_history", CONTRACT_HISTORY_FIELDS)):
            _validate_nested(record.get(column), fields, column)
        if record.get("otc_id") in id_set:
            chosen.append(record)
        fp = _fingerprint(record)
        all_fp[fp] += 1
        if dup_row is None and all_fp[fp] > 1:
            dup_row = record
        if fallbacks["null_gsis"] is None and not record.get("gsis_id"):
            fallbacks["null_gsis"] = record
        if fallbacks["year_signed_zero"] is None and record.get("year_signed") == 0:
            fallbacks["year_signed_zero"] = record
        if fallbacks["null_season_history"] is None and record.get("season_history") is None:
            fallbacks["null_season_history"] = record

    appended = []
    counts = Counter(_fingerprint(r) for r in chosen)
    if not any(c > 1 for c in counts.values()) and dup_row is not None:
        chosen.extend([dup_row, dict(dup_row)])
        appended.append("exact_duplicate_pair")
    for label, pred in (
        ("null_gsis", lambda r: not r.get("gsis_id")),
        ("year_signed_zero", lambda r: r.get("year_signed") == 0),
        ("null_season_history", lambda r: r.get("season_history") is None),
    ):
        if not any(pred(r) for r in chosen) and fallbacks[label] is not None:
            chosen.append(fallbacks[label])
            appended.append(label)

    counts = Counter(_fingerprint(r) for r in chosen)
    manifest = {
        "upstream_rows": records_seen,
        "upstream_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "source_raw_file": raw_path.name,
        "source_snapshot_id": (envelope or {}).get("snapshot_id"),
        "n_columns": len(chosen[0]),
        "base_otc_ids": ids,
        "appended_to_exercise": appended,
        "slice_rows": len(chosen),
        "exact_duplicate_excess": sum(c - 1 for c in counts.values() if c > 1),
        "null_gsis_rows": sum(1 for r in chosen if not r.get("gsis_id")),
        "year_signed_zero_rows": sum(1 for r in chosen if r.get("year_signed") == 0),
        "null_season_history_rows": sum(1 for r in chosen if r.get("season_history") is None),
        "null_contract_history_rows": sum(1 for r in chosen if r.get("contract_history") is None),
        "nested_fields": {
            "season_history": list(SEASON_HISTORY_FIELDS),
            "contract_history": list(CONTRACT_HISTORY_FIELDS),
        },
        "every_season_list_ends_in_total": all(
            r["season_history"][-1]["year"] == "Total"
            for r in chosen if r.get("season_history")
        ),
        "nflreadpy_version": _version(),
    }
    return chosen, manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, required=True,
                    help="raw contracts capture blob to slice (retained provenance)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows, manifest = build(args.raw)
    rendered = json.dumps(rows, indent=1, sort_keys=True, allow_nan=False)
    rendered_manifest = json.dumps(manifest, indent=2, sort_keys=True)
    manifest_path = args.out.with_name(args.out.stem + "_manifest.json")

    if args.check:
        failures = [
            f"{'MISSING' if not p.exists() else 'DIVERGES'} {label}: {p}"
            for p, expected, label in (
                (args.out, rendered, "fixture"),
                (manifest_path, rendered_manifest, "manifest"),
            )
            if not p.exists() or p.read_text(encoding="utf-8") != expected
        ]
        for line in failures:
            print(line)
        print("ALL ARTIFACTS MATCH SOURCE" if not failures else "CHECK FAILED")
        return 0 if not failures else 1

    args.out.write_text(rendered, encoding="utf-8")
    manifest_path.write_text(rendered_manifest, encoding="utf-8")
    print(rendered_manifest)
    for path in (args.out, manifest_path):
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
