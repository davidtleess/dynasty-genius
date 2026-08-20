"""Promoted generator for `tests/fixtures/contracts_slice.json` (batch stream 5).

Contracts has NO season axis, so a slice is taken by player rather than by season. Same
provenance discipline as streams 1-4: own repo-root derivation with a fail-loud check, upstream
row count + sha256 + nflreadpy version, stated selection rule, `--check` over fixture AND manifest.

SELECTION RULE, and each clause exists to keep a contract path testable:
  1. Every row of the 40 lowest-sorted `otc_id` values.
  2. Plus, if absent from that slice, one row of each of: an exact-duplicate PAIR; a row with a
     null `gsis_id` (the `unknown` identity path); a row with `year_signed == 0` (1,106 exist,
     preserved literally); a row with a null `cols` (SQL NULL, never the string "null").
  3. The nested `cols` list is NEVER sorted and its order is preserved exactly — measured across
     all 45,875 non-null lists: numeric years ascend, are unique, and every list ends in exactly
     one non-numeric token 'Total'. `year` is therefore NOT always numeric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if not (REPO_ROOT / "src" / "dynasty_genius").is_dir():
    raise SystemExit(f"repo root derivation failed: {REPO_ROOT} has no src/dynasty_genius")
sys.path.insert(0, str(REPO_ROOT / "src"))

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "contracts_slice.json"
NESTED_FIELDS = (
    "year", "team", "base_salary", "prorated_bonus", "roster_bonus", "guaranteed_salary",
    "cap_number", "cap_percent", "cash_paid", "workout_bonus", "other_bonus",
    "per_game_roster_bonus", "option_bonus",
)


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nflreadpy")
    except PackageNotFoundError:  # pragma: no cover
        return "unknown"


JSON_SCALARS = (str, int, float, bool, type(None))


def _plain(value):
    """polars hands a Series for a List column; convert explicitly, preserving order.

    Validated, not coerced. The banned `default=` fallback appeared three times in an earlier
    draft of this very file (Codex R10) — the exact option the design declares forbidden. A
    value that is not already JSON-compatible must RAISE, never be stringified into apparent
    success.
    """
    if value is None:
        return None
    items = value.to_list() if hasattr(value, "to_list") else list(value)
    for entry in items:
        if not isinstance(entry, dict):
            raise TypeError(f"nested entry is {type(entry).__name__}, expected a mapping")
        for key, inner in entry.items():
            if not isinstance(inner, JSON_SCALARS):
                raise TypeError(f"nested field {key!r} is {type(inner).__name__}, not JSON scalar")
    return items


def _dumps(obj) -> str:
    """Strict JSON: sorted keys, compact separators, no NaN, and NO fallback encoder."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(row) -> str:
    payload = {k: (_plain(v) if k == "cols" else v) for k, v in row.items()}
    return _dumps(payload)


def build():
    import nflreadpy as nr

    frame = nr.load_contracts()
    records = [
        {k: (_plain(v) if k == "cols" else v) for k, v in r.items()} for r in frame.to_dicts()
    ]
    upstream_hash = hashlib.sha256(
        _dumps(records).encode()
    ).hexdigest()

    ids = sorted({r["otc_id"] for r in records})[:40]
    chosen = [r for r in records if r["otc_id"] in ids]
    appended = []

    counts = Counter(_fingerprint(r) for r in chosen)
    if not any(c > 1 for c in counts.values()):
        allc = Counter(_fingerprint(r) for r in records)
        fp = next((f for f, c in allc.items() if c > 1), None)
        if fp is not None:
            row = next(r for r in records if _fingerprint(r) == fp)
            chosen.extend([row, dict(row)])
            appended.append("exact_duplicate_pair")

    for label, pred in (
        ("null_gsis", lambda r: not r.get("gsis_id")),
        ("year_signed_zero", lambda r: r.get("year_signed") == 0),
        ("null_cols", lambda r: r.get("cols") is None),
    ):
        if not any(pred(r) for r in chosen):
            extra = next((r for r in records if pred(r)), None)
            if extra is not None:
                chosen.append(extra)
                appended.append(label)

    counts = Counter(_fingerprint(r) for r in chosen)
    manifest = {
        "upstream_rows": len(records),
        "upstream_sha256": upstream_hash,
        "n_columns": len(records[0]),
        "base_otc_ids": ids,
        "appended_to_exercise": appended,
        "slice_rows": len(chosen),
        "exact_duplicate_excess": sum(c - 1 for c in counts.values() if c > 1),
        "null_gsis_rows": sum(1 for r in chosen if not r.get("gsis_id")),
        "year_signed_zero_rows": sum(1 for r in chosen if r.get("year_signed") == 0),
        "null_cols_rows": sum(1 for r in chosen if r.get("cols") is None),
        "nested_fields": list(NESTED_FIELDS),
        "every_list_ends_in_total": all(
            r["cols"][-1]["year"] == "Total" for r in chosen if r.get("cols")
        ),
        "nflreadpy_version": _version(),
    }
    return chosen, manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows, manifest = build()
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
