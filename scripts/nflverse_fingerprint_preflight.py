"""Cheap live preflight: has the provider changed shape since we pinned it?

One small fetch per stream, compare the observed column set and dtype kinds
against `tests/fixtures/nflverse_eras/era_fingerprints.json`, and REFUSE on drift
rather than discovering it three hundred files into a capture.

The failure this prevents is measured, not hypothetical. On 2026-08-02 a capture
ran for six seasons before dying on a shape change in the last one, and a second
provider defect (a column swapped rather than added) had already been silently
absorbed for months. A preflight is seconds; a wasted capture is minutes plus a
half-written store.

It is DIAGNOSTIC, not a gate on ingestion: it reports and exits non-zero, and
nothing calls it automatically. A new shape is not automatically wrong — it needs
a human decision and then a re-pin.

    .venv/bin/python3.14 scripts/nflverse_fingerprint_preflight.py
    .venv/bin/python3.14 scripts/nflverse_fingerprint_preflight.py --stream injuries --season 2025
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures" / "nflverse_eras" / "era_fingerprints.json"


def _dtype_kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


class HeterogeneousFetch(RuntimeError):
    """A live fetch whose records do not share one exact column set."""


def exact_column_set(records: list[dict], where: str) -> list[str]:
    """Every record must carry the SAME keys (R3-T1).

    Taking records[0] here mirrored the generator defect: a provider field
    present only on a later row landed in the dtype map but never in `columns`,
    and the verdict then iterated only the first row's columns — so the addition
    was invisible to the very check meant to catch it.
    """
    expected = set(records[0].keys())
    for index, record in enumerate(records):
        observed = set(record.keys())
        if observed != expected:
            raise HeterogeneousFetch(
                f"heterogeneous_fetch: {where} record {index} — "
                f"unexpected {sorted(observed - expected)}, "
                f"missing {sorted(expected - observed)}"
            )
    return sorted(expected)


def verdict(
    shape: dict, columns: list[str], kinds: dict[str, list[str]], season: int | str
) -> tuple[bool, dict]:
    """Pure comparison: does this observation match ONE pinned shape+season?

    Module level and pure ON PURPOSE. Nested inside main() it was unreachable
    without a live loader, so a broken verdict, a wrong chosen season, or an
    unbound loader all left the preflight suite green (Codex R3-T4).
    """
    if shape["columns"] != columns:
        return False, {
            "unexpected_columns": sorted(set(columns) - set(shape["columns"])),
            "missing_columns": sorted(set(shape["columns"]) - set(columns)),
        }
    per_season = shape.get("dtype_kinds_by_season", {}).get(str(season))
    if per_season is None:
        return False, {"unpinned_season": str(season)}
    diff = {
        column: {"pinned": per_season.get(column), "observed": kinds.get(column)}
        for column in columns
        if sorted(kinds.get(column, [])) != sorted(per_season.get(column, []))
    }
    return (not diff), ({"dtype_changed": diff} if diff else {})


def _observed_shape(records: list[dict]) -> tuple[list[str], dict[str, list[str]]]:
    """Profile EVERY fetched row, matching the generator exactly.

    Sampling the first 200 here while the generator accumulates over every row
    made the comparison asymmetric: ngs_receiving 2024 reported SHAPE DRIFT
    because `avg_yac` is pinned {float, null} and the first 200 rows happened to
    carry no null. A guard whose two sides measure differently reports its own
    asymmetry as a provider change. The rows are already in memory; the cost is
    nil.
    """
    columns = exact_column_set(records, "live fetch")
    kinds: dict[str, set[str]] = {c: set() for c in columns}
    for record in records:
        for column, value in record.items():
            kinds.setdefault(column, set()).add(_dtype_kind(value))
    return columns, {c: sorted(v) for c, v in sorted(kinds.items())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", default="injuries")
    parser.add_argument("--season", type=int, default=None)
    args = parser.parse_args(argv)

    if not FIXTURES.exists():
        print(f"no pinned fingerprints at {FIXTURES}")
        return 1
    bundle = json.loads(FIXTURES.read_text(encoding="utf-8"))
    pinned = [s for s in bundle["shapes"] if s["stream"] == args.stream]
    if not pinned:
        print(f"stream {args.stream!r} is not pinned")
        return 1

    season = args.season or max(max(s["seasons"]) for s in pinned)

    # T5: resolve the loader from the REAL spec registry rather than a hand-kept
    # dict. The hand-kept version wired two of five streams while the docstring
    # promised "one fetch per stream", and the three NGS streams silently had no
    # loader at all. Driving build_streams() means a new stream cannot be
    # forgotten here.
    from src.dynasty_genius.nflverse_usage import build_streams

    spec = next((s for s in build_streams() if s.name == args.stream), None)
    if spec is None or spec.loader is None:
        print(f"stream {args.stream!r} has no bound loader")
        return 1

    frame = spec.loader(seasons=[season], **dict(spec.loader_kwargs))
    records = frame.to_dicts()
    if not records:
        print(f"{args.stream} {season}: provider returned no rows")
        return 1

    columns, kinds = _observed_shape(records)
    matches = [s for s in pinned if verdict(s, columns, kinds, season)[0]]
    if matches:
        print(
            f"ok — {args.stream} {season} matches pinned shape "
            f"{matches[0]['fingerprint'][:12]} ({len(columns)} columns)"
        )
        return 0

    print(f"SHAPE DRIFT — {args.stream} {season} matches no pinned shape")
    print(f"  observed columns ({len(columns)}): {columns}")
    for shape in pinned:
        extra = sorted(set(columns) - set(shape["columns"]))
        missing = sorted(set(shape["columns"]) - set(columns))
        _, detail = verdict(shape, columns, kinds, season)
        print(
            f"  vs {shape['fingerprint'][:12]} seasons={shape['seasons']}: "
            f"unexpected={extra} missing={missing} {detail}"
        )
    print(
        "\nA new shape is not automatically wrong. Decide, then re-pin with "
        "scripts/build_nflverse_era_fixtures.py."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
