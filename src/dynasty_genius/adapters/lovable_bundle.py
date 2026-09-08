"""A portable, versioned read-model bundle for the Lovable interface.

WHAT THIS IS. One JSON file carrying the three payloads this product already serves —
``/api/research/market-ranks``, ``/api/research/comparison`` and ``/api/research/available`` — with
their values unaltered, wrapped in the provenance that says which single snapshot they all belong to.

ON "UNALTERED". The payloads are parsed and re-serialised, so the values are carried through exactly
while the original HTTP bytes are not. ``snapshot.report_sha256`` is the byte-level anchor: it is the
producer's own hash of the report these payloads were derived from, and it is checked to be the same
across all three.

WHY IT RESHAPES NOTHING. Every way our meaning can be lost is a flattening step: a tied rank turned
into its start, an absent comparison turned into a verdict, a null turned into a zero. This module
has no per-player row to get wrong, so ties stay intervals and absences stay absences by construction
rather than by care.

WHAT THIS MODULE DOES NOT CLAIM. Nothing here describes how the Lovable client computes what it
shows; that is a question for its source, not something inferable from a rendered screen. The one
claim made is about units: our value is projected points above replacement over five seasons and the
market's is a trade price, so **ours cannot be consumed as an equivalent price**, and a margin
between the two lanes cannot be reproduced from our numbers.

WHERE PRICES COME FROM. ``/api/research/market-ranks`` only. The player-detail route serves a second
market overlay dated 2026-07-22, six weeks behind the ranks payload, flagged in its own response as
``market_overlay_static_caveat``. A bundle mixing the two would publish July prices beside September
ranks and nothing would look wrong, so :data:`STALE_OVERLAY_FIELDS` is refused on sight.

FAIL CLOSED. A bundle is either provably one snapshot or it is not written at all. There is no
warning field inside the output, because a warning inside a data file is invisible to the consumer
that matters.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping

BUNDLE_KIND = "dg.read-model.bundle"
BUNDLE_VERSION = 1

HEADSHOT_PATH_TEMPLATE = "/assets/headshots/{sleeper_id}.jpg"

#: Fields that exist ONLY on the six-week-stale player-detail market overlay. Their presence in a
#: rank row means someone merged the two market lanes, which is the failure this refuses.
STALE_OVERLAY_FIELDS = ("market_rank_overall", "market_rank_position", "source_timestamp")

_PAYLOAD_NAMES = ("market_ranks", "comparison", "available")

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


class BundleRejected(Exception):
    """The payloads do not provably belong to one verified snapshot."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise BundleRejected(message)


def _source_of(payload: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    source = payload.get("source")
    _require(isinstance(source, Mapping), f"{name}: no source block, so its provenance is unknown")
    assert isinstance(source, Mapping)  # for type checkers; _require already raised
    return source


def _disagreement(field: str, values: Mapping[str, Any], why: str) -> BundleRejected:
    return BundleRejected(
        f"payloads name different {field} values, {why}: "
        + ", ".join(f"{n}={str(v)[:24]}" for n, v in sorted(values.items()))
    )


def _agree_on(field: str, values: Mapping[str, Any], why: str) -> None:
    """Every payload that publishes ``field`` must publish the same value for it."""
    published = {n: v for n, v in values.items() if v is not None}
    if len(set(map(str, published.values()))) > 1:
        raise _disagreement(field, published, why)


def _check_one_snapshot(payloads: Mapping[str, Mapping[str, Any]]) -> None:
    """One snapshot means more than one report.

    The same report run can legitimately be paired with a later catalog or a later roster capture, so
    a bundle whose payloads agree only on the report would still be mixing boards. Every dimension
    each payload publishes has to line up.
    """
    runs: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for name in _PAYLOAD_NAMES:
        source = _source_of(payloads[name], name)
        run = source.get("report_run")
        digest = source.get("report_sha256")
        _require(isinstance(run, str) and run, f"{name}: source.report_run is empty")
        _require(isinstance(digest, str) and digest, f"{name}: source.report_sha256 is empty")
        _require(
            _SHA256.match(str(digest)),
            f"{name}: source.report_sha256 is not a sha256 digest: {digest!r}",
        )
        runs[name] = str(run)
        hashes[name] = str(digest)

    if len(set(runs.values())) != 1:
        raise _disagreement("report_run", runs, "so they are not one snapshot")
    if len(set(hashes.values())) != 1:
        raise _disagreement("report_sha256", hashes, "so they are not one snapshot")

    sources = {n: _source_of(payloads[n], n) for n in _PAYLOAD_NAMES}
    # The catalog decides which players the available board holds; market-ranks publishes none.
    _agree_on(
        "catalog_run",
        {n: s.get("catalog_run") for n, s in sources.items()},
        "so the available board and the forecasts come from different catalogs",
    )
    # The roster capture decides who owns whom.
    _agree_on(
        "ownership_as_of",
        {n: s.get("ownership_as_of") for n, s in sources.items()},
        "so ownership was captured at different moments",
    )
    # Only some payloads publish the catalog's content hash; check it wherever two of them do.
    _agree_on(
        "catalog_content_sha256",
        {n: s.get("catalog_content_sha256") for n, s in sources.items()},
        "so the catalog bytes differ between payloads",
    )


def _check_rows(market_ranks: Mapping[str, Any]) -> None:
    """A row this module cannot read is refused, never stepped over.

    Skipping a malformed row would let a truncated or half-migrated payload through with a silently
    smaller board, which is the failure mode that looks like nothing at all.
    """
    rows = market_ranks.get("rows")
    _require(isinstance(rows, list), "market_ranks: no rows")
    assert isinstance(rows, list)
    for index, row in enumerate(rows):
        _require(
            isinstance(row, Mapping),
            f"market_ranks row {index} is {type(row).__name__}, not an object",
        )
        assert isinstance(row, Mapping)
        _require(row.get("sleeper_id"), f"market_ranks row {index} has no sleeper_id")
        for field in STALE_OVERLAY_FIELDS:
            if field in row:
                raise BundleRejected(
                    f"market_ranks row {row['sleeper_id']} carries {field}, which belongs to the "
                    "stale player-detail market overlay, not to this snapshot"
                )


def _check_blocks(market_ranks: Mapping[str, Any], available: Mapping[str, Any]) -> None:
    """The counts and the basis are what a client renders instead of deriving. Check their shape."""
    coverage = market_ranks.get("coverage")
    _require(isinstance(coverage, Mapping) and coverage, "market_ranks: no coverage block")
    assert isinstance(coverage, Mapping)
    for key, value in coverage.items():
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            f"market_ranks: coverage.{key} is not a count: {value!r}",
        )

    basis = market_ranks.get("basis")
    _require(isinstance(basis, Mapping), "market_ranks: no basis block")
    assert isinstance(basis, Mapping)
    years = basis.get("years")
    _require(
        isinstance(years, list) and years,
        "market_ranks: basis.years is empty, so the number has no stated horizon",
    )

    populations = available.get("populations")
    _require(isinstance(populations, Mapping), "available: no populations block")
    assert isinstance(populations, Mapping)
    _require(populations.get("default"), "available: populations.default is missing")


def build_bundle(
    *,
    market_ranks: Mapping[str, Any],
    comparison: Mapping[str, Any],
    available: Mapping[str, Any],
    generated_at: str,
    headshot_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Validate three payloads and wrap them, unchanged, in one versioned envelope.

    ``generated_at`` is supplied by the caller rather than read from a clock, so a bundle is
    reproducible and a test is not comparing against the time it happened to run.
    """
    _require(
        market_ranks.get("status") == "available",
        f"market_ranks: status is {market_ranks.get('status')!r}, not 'available'",
    )

    payloads = {"market_ranks": market_ranks, "comparison": comparison, "available": available}
    _check_one_snapshot(payloads)
    _check_rows(market_ranks)
    _check_blocks(market_ranks, available)

    available_source = _source_of(available, "available")
    _require(
        available_source.get("pinned") is True,
        "available: source.pinned is not true, so the catalog could move under the bundle",
    )

    ranks_source = _source_of(market_ranks, "market_ranks")
    comparison_source = _source_of(comparison, "comparison")

    for field in (
        "market_sha256",
        "league_sha256",
        "forecast_date",
        "market_as_of",
        "ownership_as_of",
    ):
        _require(ranks_source.get(field), f"market_ranks: source.{field} is empty")

    snapshot = {
        "report_run": ranks_source["report_run"],
        "report_sha256": ranks_source["report_sha256"],
        "market_sha256": ranks_source["market_sha256"],
        "league_sha256": ranks_source["league_sha256"],
        "catalog_run": available_source.get("catalog_run"),
        "catalog_content_sha256": comparison_source.get("catalog_content_sha256"),
        "census_run_id": available_source.get("census_run_id"),
        "forecast_date": ranks_source["forecast_date"],
        "market_as_of": ranks_source["market_as_of"],
        "ownership_as_of": ranks_source["ownership_as_of"],
        "nfl_status_as_of": comparison_source.get("nfl_status_as_of"),
    }
    for field in ("catalog_run", "census_run_id"):
        _require(snapshot[field], f"available: source.{field} is empty")

    return {
        "kind": BUNDLE_KIND,
        "bundle_version": BUNDLE_VERSION,
        # when this file was written — NOT a freshness claim. The three as-of times in `snapshot`
        # are the only honest freshness, and they are genuinely different moments.
        "generated_at": generated_at,
        "snapshot": snapshot,
        "basis": copy.deepcopy(market_ranks.get("basis")),
        "coverage": copy.deepcopy(market_ranks.get("coverage")),
        "populations": copy.deepcopy(available.get("populations")),
        "payloads": {
            "market_ranks": copy.deepcopy(dict(market_ranks)),
            "comparison": copy.deepcopy(dict(comparison)),
            "available": copy.deepcopy(dict(available)),
        },
        # Identity is a separate labelled block so an image reference can never be mistaken for part
        # of a price snapshot. `ids` stays null unless a caller actually read a cache directory:
        # this bundle asserts no file exists.
        "identity": {
            "kind": "headshot_reference",
            "path_template": HEADSHOT_PATH_TEMPLATE,
            "note": (
                "Local cache references only. This bundle does not assert that any file is present; "
                "a client must fall back to initials when one is missing."
            ),
            "ids": list(headshot_ids) if headshot_ids is not None else None,
        },
    }


def write_bundle(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Refuse an occupied path, then build, then create exclusively.

    A bundle is evidence: someone will compare a consumer's behaviour against a specific file and its
    hash. Silently replacing one would destroy the thing being compared against, so an existing path
    is refused BEFORE any work, and the write itself uses exclusive-create so a file appearing in the
    meantime is not clobbered either.
    """
    destination = Path(path)
    if destination.exists():
        raise BundleRejected(
            f"{destination} already exists; a written bundle is immutable evidence. "
            "Write to a new path rather than replacing it."
        )
    bundle = build_bundle(**kwargs)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(destination, "x", encoding="utf-8") as handle:
            handle.write(json.dumps(bundle, indent=2, sort_keys=False) + "\n")
    except FileExistsError as clash:
        raise BundleRejected(f"{destination} appeared while this bundle was building") from clash
    return bundle


# ── loaders ─────────────────────────────────────────────────────────────────────────────────────

_ENDPOINTS = {
    "market_ranks": "/api/research/market-ranks",
    "comparison": "/api/research/comparison",
    "available": "/api/research/available",
}


def load_from_api(base_url: str, *, timeout: float = 60.0) -> dict[str, Any]:
    """Read the three payloads from a running preview. Read-only; no authentication is sent."""
    out: dict[str, Any] = {}
    for name, path in _ENDPOINTS.items():
        with urllib.request.urlopen(base_url.rstrip("/") + path, timeout=timeout) as response:
            out[name] = json.loads(response.read().decode("utf-8"))
    return out


def load_from_dir(directory: str | Path) -> dict[str, Any]:
    """Read the three payloads from files saved earlier, for a reproducible rebuild."""
    base = Path(directory)
    names = {
        "market_ranks": ("market_ranks.json", "market-ranks.json"),
        "comparison": ("comparison.json",),
        "available": ("available.json",),
    }
    out: dict[str, Any] = {}
    for key, candidates in names.items():
        for candidate in candidates:
            path = base / candidate
            if path.exists():
                out[key] = json.loads(path.read_text())
                break
        else:
            raise BundleRejected(f"{key}: none of {candidates} found in {base}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base-url", help="a running preview, e.g. http://127.0.0.1:8794")
    source.add_argument("--from-dir", help="a directory of previously saved payloads")
    parser.add_argument("--out", required=True, help="where to write the bundle")
    parser.add_argument(
        "--generated-at",
        required=True,
        help="ISO 8601 UTC stamp for this build; passed in so the bundle is reproducible",
    )
    parser.add_argument(
        "--headshot-dir",
        help="optional local headshot cache; when given, its ids are listed in the identity block",
    )
    args = parser.parse_args(argv)

    payloads = (
        load_from_api(args.base_url) if args.base_url else load_from_dir(args.from_dir)
    )
    headshot_ids = None
    if args.headshot_dir:
        headshot_ids = sorted(p.stem for p in Path(args.headshot_dir).glob("*.jpg"))

    try:
        bundle = write_bundle(
            args.out, generated_at=args.generated_at, headshot_ids=headshot_ids, **payloads
        )
    except BundleRejected as rejected:
        print(f"REFUSED: {rejected}", file=sys.stderr)
        return 2

    snapshot = bundle["snapshot"]
    print(
        f"wrote {args.out}\n"
        f"  report run   {snapshot['report_run']}  report {snapshot['report_sha256'][:12]}\n"
        f"  forecast     {snapshot['forecast_date']}\n"
        f"  market as of {snapshot['market_as_of']}\n"
        f"  ownership    {snapshot['ownership_as_of']}\n"
        f"  rows         {len(bundle['payloads']['market_ranks']['rows'])} ranked, "
        f"{len(bundle['payloads']['available']['rows'])} available"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
