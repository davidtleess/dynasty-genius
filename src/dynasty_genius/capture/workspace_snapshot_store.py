"""The workspace snapshot archive (DG-190, 2026-09-08; David: "lets build").

What David is looking at today — the five-year forecasts, the market prices they are compared against, and the
league that frames both — exists for one day and is then gone. This module keeps an exact copy so that a later
evaluation can say what was known, and when.

It is a filing cabinet, not a scoreboard. Nothing here grades a forecast, scores an outcome or claims an advantage;
every receipt carries ``evaluation_status: "ungraded"``, and saving September 6 forecasts on September 8 records
precisely that and never backdates the capture to the forecast date.

Three properties do the real work:

1. **Identity is content.** ``snapshot_id`` is a sha256 over the schema version and every archived byte. It excludes
   the save time and the capture code, so saving the same sources twice converges on one archive that keeps its
   ORIGINAL saved time — a second look is not a second observation, and a later count cannot double it.

   A snapshot identifies a saved READING, not an independent forecast. The same underlying forecast can be archived
   more than once under different ids if the rendering around it changes, and the six-field ``source`` tuple in the
   receipt is what identifies the forecast underneath. **A count of snapshots is therefore never a count of
   independent predictions or samples**, and nothing here should be presented as one. Callers that want "have I
   already saved this forecast?" must compare the source tuple, not the id.
2. **The archive verifies itself.** Every file's hash is recorded beside it in ``snapshot.json``, and the receipt is
   a pure function of the archived payloads. Listing, reading and re-saving all re-derive both and refuse on any
   disagreement, so corruption fails loudly instead of returning a plausible receipt.
3. **A count is derived, never asserted.** Populations are counted from the rows and cross-checked against the
   coverage block that claims to summarise them. Zero is a count; missing is not; a boolean is not a number.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "workspace_snapshot.v1"

#: The six raw source artifacts, archived byte for byte exactly as the loader verified them.
ARTIFACT_NAMES: tuple[str, ...] = (
    "source-manifest.json",
    "report.json",
    "market.json",
    "league.json",
    "catalog.json",
    "catalog-companion.json",
    "evaluation-plan.json",
)
#: The two derived documents the surface actually read.
DERIVED_NAMES: tuple[str, ...] = ("ranks.json", "comparison.json")
MANIFEST_NAME = "snapshot.json"
TEMP_PREFIX = ".tmp-"
DEFAULT_POPULATION = "default"
UNKNOWN_CODE = "unknown"
#: Shared stores this archive must never be pointed at, however the caller spells the path.
SHARED_STORE_PARTS = (("app", "data"), ("app", "cache"))
#: The platform's own aliases. Everything else that is a link is refused, including a user-created parent symlink
#: pointing at a shared location.
SYSTEM_ALIASES = {"/tmp": "/private/tmp", "/var": "/private/var"}


class WorkspaceSnapshotError(ValueError):
    """The bundle or the archive cannot be trusted; the message says exactly what failed."""


@dataclass(frozen=True)
class SnapshotBundle:
    """The verified sources and the two documents derived from them."""

    artifacts: dict[str, bytes]
    ranks: dict
    comparison: dict


# --- canonical form and small validators ------------------------------------------------------------


def canonical_bytes(document: Any, *, what: str) -> bytes:
    """The contract's canonical JSON. ``allow_nan=False`` is also how a non-finite number is refused: an infinity
    or a NaN cannot be archived as if it were a measurement."""
    try:
        return json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except ValueError as exc:
        raise WorkspaceSnapshotError(f"{what} contains a value that is not finite or not serialisable: {exc}") from exc


def strict_json(payload: bytes, what: str) -> Any:
    """Parse a raw artifact the careful way.

    ``json.loads`` accepts ``NaN`` and ``Infinity`` by default, silently overflows ``1e999`` to infinity, and keeps
    only the last of a duplicated key. Each of those would archive something that is not the document it appears to
    be, so each is refused here instead.
    """

    def refuse_constant(name: str) -> Any:
        raise WorkspaceSnapshotError(f"{what} contains {name}, which is not a finite number")

    def finite(text: str) -> float:
        value = float(text)
        if not (value == value and abs(value) != float("inf")):
            raise WorkspaceSnapshotError(f"{what} contains {text}, which is not a finite number")
        return value

    def unique(pairs: list[tuple[str, Any]]) -> dict:
        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            duplicated = sorted({key for key in keys if keys.count(key) > 1})
            raise WorkspaceSnapshotError(
                f"{what} repeats the key(s) {', '.join(duplicated)}; a duplicate key silently discards a value"
            )
        return dict(pairs)

    try:
        return json.loads(payload, parse_constant=refuse_constant, parse_float=finite, object_pairs_hook=unique)
    except WorkspaceSnapshotError:
        raise
    except ValueError as exc:
        raise WorkspaceSnapshotError(f"{what} is not readable JSON: {exc}") from exc


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _text(value: Any, what: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise WorkspaceSnapshotError(f"{what} is {value!r}, not a non-empty string")
    return value


def _count(value: Any, what: str) -> int:
    # A boolean is an int in Python and is never a population size. Counting one would report True as 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceSnapshotError(f"{what} is {value!r}, not a whole number")
    if value < 0:
        raise WorkspaceSnapshotError(f"{what} is {value}, which is not a population size")
    return value


def _instant(value: Any, what: str) -> datetime:
    text = _text(value, what)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise WorkspaceSnapshotError(f"{what} is {text!r}, which is not a readable timestamp") from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _day(value: Any, what: str) -> date:
    text = _text(value, what)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise WorkspaceSnapshotError(f"{what} is {text!r}, which is not a YYYY-MM-DD date") from exc


def _unique_ids(rows: Iterable[dict], what: str) -> list[str]:
    seen: list[str] = []
    known: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise WorkspaceSnapshotError(f"{what} contains {row!r}, which is not a player row")
        identity = _text(row.get("sleeper_id"), f"a {what} row's sleeper_id")
        if identity in known:
            raise WorkspaceSnapshotError(
                f"{what} carries a duplicate player {identity}; refusing to archive a population that counts "
                f"someone twice"
            )
        known.add(identity)
        seen.append(identity)
    return seen


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) != float("inf")


# --- the archive location ----------------------------------------------------------------------------


def _archive_root(root: Path | str) -> Path:
    """The archive must be a private, real place, and the returned root is canonical.

    A link standing where a directory is expected is exactly how ``app/cache`` silently became the shared trunk
    cache, so every symlink in the path is refused — except the platform's own aliases (``/tmp`` and ``/var``),
    without which no temporary directory on macOS would be usable at all. A user-created parent symlink
    pointing somewhere shared is not an alias and is refused.

    This defends a controlled local root. It does not claim to defend against an adversary replacing directories
    underneath us while we run.
    """
    path = Path(root)
    for candidate in (path, *path.parents):
        if not candidate.is_symlink():
            continue
        alias = SYSTEM_ALIASES.get(str(candidate))
        if alias is not None and str(candidate.resolve()) == alias:
            continue
        raise WorkspaceSnapshotError(
            f"the archive path crosses the symlink {candidate}; an archive must be a real private directory, "
            f"because a link here silently writes somebody else's store"
        )
    if path.exists() and not path.is_dir():
        raise WorkspaceSnapshotError(f"the archive root {path} exists and is not a directory")
    resolved = path.resolve()
    parts = resolved.parts
    for shared in SHARED_STORE_PARTS:
        for index in range(len(parts) - len(shared) + 1):
            if tuple(parts[index : index + len(shared)]) == shared:
                raise WorkspaceSnapshotError(
                    f"the archive root {path} resolves inside the shared {'/'.join(shared)} store; this archive "
                    f"never writes there"
                )
    return resolved


def _snapshot_dir(root: Path, snapshot_id: str) -> Path:
    if not isinstance(snapshot_id, str) or len(snapshot_id) != 64 or set(snapshot_id) - set("0123456789abcdef"):
        raise WorkspaceSnapshotError(
            f"{snapshot_id!r} is not a snapshot id; an id is 64 lowercase hexadecimal characters"
        )
    directory = root / snapshot_id
    if directory.is_symlink():
        raise WorkspaceSnapshotError(f"the archived snapshot {snapshot_id} is a symlink, not a directory")
    return directory


# --- identity ------------------------------------------------------------------------------------------


def _validated_artifacts(artifacts: Any) -> dict[str, bytes]:
    if not isinstance(artifacts, dict):
        raise WorkspaceSnapshotError("the bundle's artifacts are not a mapping of name to bytes")
    missing = [name for name in ARTIFACT_NAMES if name not in artifacts]
    if missing:
        raise WorkspaceSnapshotError(f"the bundle is missing the raw artifact(s) {', '.join(missing)}")
    extra = sorted(set(artifacts) - set(ARTIFACT_NAMES))
    if extra:
        raise WorkspaceSnapshotError(f"the bundle carries unexpected artifact(s) {', '.join(extra)}")
    for name in ARTIFACT_NAMES:
        payload = artifacts[name]
        if not isinstance(payload, (bytes, bytearray)):
            raise WorkspaceSnapshotError(f"the artifact {name} is {type(payload).__name__}, not bytes")
        if len(payload) == 0:
            raise WorkspaceSnapshotError(f"the artifact {name} is empty")
        document = strict_json(bytes(payload), f"the artifact {name}")
        if not isinstance(document, dict):
            raise WorkspaceSnapshotError(
                f"the artifact {name} is a {type(document).__name__}, not a JSON object"
            )
    return {name: bytes(artifacts[name]) for name in ARTIFACT_NAMES}


def _content_id(artifacts: dict[str, bytes], derived: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    digest.update(SCHEMA_VERSION.encode("utf-8"))
    for name in (*ARTIFACT_NAMES, *DERIVED_NAMES):
        payload = artifacts.get(name) if name in artifacts else derived[name]
        digest.update(b"\0")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(payload).encode("ascii"))
    return digest.hexdigest()


# --- the receipt ------------------------------------------------------------------------------------------


def _counts(ranks: dict, comparison: dict, market: dict) -> dict[str, int]:
    """Count the populations from the ROWS, then require the coverage block to agree.

    An earlier version of this took model, market and paired straight from coverage and called that a cross-check.
    It could not fail: it compared the summary with itself. Every number below is now counted from the rows that
    are actually archived, and the coverage block is the thing being checked.
    """
    coverage = ranks.get("coverage")
    if not isinstance(coverage, dict):
        raise WorkspaceSnapshotError("the ranks payload carries no coverage block")
    rows = ranks.get("rows")
    if not isinstance(rows, list):
        raise WorkspaceSnapshotError("the ranks payload carries no rows")
    _unique_ids(rows, "the ranks rows")

    entries = market.get("entries")
    if not isinstance(entries, list) or any(not isinstance(row, dict) for row in entries):
        raise WorkspaceSnapshotError("the archived market carries no valid entries")
    counted = {
        "market_picks": [row for row in entries if row.get("position") == "PICK"],
        "model_players": [row for row in rows if row.get("model_value") is not None],
        "market_players": [row for row in rows if row.get("market_value") is not None],
        "common_players": [
            row for row in rows if row.get("our_rank") is not None and row.get("market_rank") is not None
        ],
        "roster_players": [row for row in rows if row.get("on_roster") is True],
        "total_players": rows,
    }
    for field, measured in counted.items():
        declared = _count(coverage.get(field), f"the ranks coverage {field}")
        if declared != len(measured):
            raise WorkspaceSnapshotError(
                f"the ranks coverage claims {field} {declared} while its own rows carry {len(measured)}"
            )

    roster_rows = comparison.get("roster")
    available_rows = comparison.get("available")
    if not isinstance(roster_rows, list) or not isinstance(available_rows, list):
        raise WorkspaceSnapshotError("the comparison payload carries no roster or available population")
    roster_ids = set(_unique_ids(roster_rows, "the comparison roster"))
    available_ids = set(_unique_ids(available_rows, "the comparison available population"))

    # A player is either David's or someone he could add. Being both would double him in any later count.
    both = sorted(roster_ids & available_ids)
    if both:
        raise WorkspaceSnapshotError(
            f"{', '.join(both)} appear(s) on David's roster and in the available population at the same time"
        )
    ranked_roster = {row["sleeper_id"] for row in counted["roster_players"]}
    if ranked_roster != roster_ids:
        only_ranks = sorted(ranked_roster - roster_ids)
        only_comparison = sorted(roster_ids - ranked_roster)
        raise WorkspaceSnapshotError(
            f"the two payloads name different rosters: only in the ranks {only_ranks or 'none'}, only in the "
            f"comparison {only_comparison or 'none'}"
        )

    # Availability is the default population only. Cut, retired and unknown rows stay archived in full; they are
    # simply not a claim about what David can pick up.
    default_rows = [row for row in available_rows if row.get("population") == DEFAULT_POPULATION]
    with_forecasts = [
        row for row in default_rows if _finite_number(row.get("now_points")) and _finite_number(row.get("future_points"))
    ]
    starting = [row for row in default_rows if row.get("starting_estimate") is True]

    # `market` is market PLAYERS and `available` is the RELEVANT (default) pool. The two extra keys exist so the
    # whole catalog is never read as the relevant pool: picks are not players, and 510 catalog rows are not 433
    # available ones.
    return {
        "model": len(counted["model_players"]),
        "market": len(counted["market_players"]),
        "market_picks": len(counted["market_picks"]),
        "paired": len(counted["common_players"]),
        "roster": len(roster_rows),
        "available": len(default_rows),
        "available_total": len(available_rows),
        "available_with_forecasts": len(with_forecasts),
        "available_without_forecasts": len(default_rows) - len(with_forecasts),
        "starting_estimates": len(starting),
    }


def _build_receipt(
    bundle: SnapshotBundle, *, snapshot_id: str, saved_at: datetime, code_sha: str
) -> dict[str, Any]:
    ranks, comparison = bundle.ranks, bundle.comparison
    if not isinstance(ranks, dict) or not isinstance(comparison, dict):
        raise WorkspaceSnapshotError("the bundle's ranks and comparison must both be documents")
    rank_source = ranks.get("source")
    comparison_source = comparison.get("source")
    if not isinstance(rank_source, dict) or not isinstance(comparison_source, dict):
        raise WorkspaceSnapshotError("the ranks or comparison payload carries no source block")

    # The two documents must describe the same capture, or the archive would pair a forecast with someone else's
    # market. Each disagreement names the field so a person can go and look.
    for field in ("report_run", "report_sha256", "ownership_as_of"):
        ours = _text(rank_source.get(field), f"the ranks source {field}")
        theirs = _text(comparison_source.get(field), f"the comparison source {field}")
        if ours != theirs:
            raise WorkspaceSnapshotError(
                f"the ranks and the comparison disagree about {field}: {ours!r} against {theirs!r}"
            )

    basis = ranks.get("basis")
    if not isinstance(basis, dict):
        raise WorkspaceSnapshotError("the ranks payload carries no basis block")
    years = basis.get("years")
    if not isinstance(years, list) or not years or any(isinstance(y, bool) or not isinstance(y, int) for y in years):
        raise WorkspaceSnapshotError(f"the ranks basis years {years!r} are not a list of whole years")
    if comparison.get("forecast_years") != years:
        raise WorkspaceSnapshotError(
            f"the ranks and the comparison disagree about the forecast years: {years} against "
            f"{comparison.get('forecast_years')!r}"
        )

    forecast_date = _day(rank_source.get("forecast_date"), "the ranks source forecast_date")
    market_as_of = _instant(rank_source.get("market_as_of"), "the ranks source market_as_of")
    ownership_as_of = _instant(rank_source.get("ownership_as_of"), "the ranks source ownership_as_of")
    if forecast_date > saved_at.date():
        raise WorkspaceSnapshotError(
            f"the forecast is dated {forecast_date}, after the moment it was saved ({saved_at.date()})"
        )
    for label, instant in (("market_as_of", market_as_of), ("ownership_as_of", ownership_as_of)):
        if instant > saved_at:
            raise WorkspaceSnapshotError(f"the source {label} is dated after the moment it was saved")

    # Derived from the archived catalog, so the receipt is complete whether or not the comparison carries the field.
    # When it does carry it, the two must agree: a copy proves nothing, a cross-check proves something.
    catalog_content_sha = _sha256(
        canonical_bytes(strict_json(bundle.artifacts["catalog.json"], "the archived catalog"),
                        what="the archived catalog")
    )
    declared = comparison_source.get("catalog_content_sha256")
    if declared is not None and _text(declared, "the comparison catalog_content_sha256") != catalog_content_sha:
        raise WorkspaceSnapshotError(
            f"the comparison declares catalog_content_sha256 {declared[:12]}… while the archived catalog hashes "
            f"{catalog_content_sha[:12]}…"
        )

    # When the producers stamped the underlying files, which is a different fact from the date the forecast is
    # nominally for. Absent stays null rather than being filled in from the forecast date.
    generated = {}
    for label, artifact in (("report_generated_at", "report.json"), ("catalog_generated_at", "catalog.json")):
        document = strict_json(bundle.artifacts[artifact], f"the archived {artifact}")
        stamped = (document.get("provenance") or {}).get("generated_at") if isinstance(document, dict) else None
        if stamped is None:
            generated[label] = None
            continue
        if _instant(stamped, f"the {artifact} provenance generated_at") > saved_at:
            raise WorkspaceSnapshotError(f"the {artifact} was generated after the moment it was saved")
        generated[label] = _text(stamped, f"the {artifact} provenance generated_at")

    plan = strict_json(bundle.artifacts["evaluation-plan.json"], "the evaluation plan")
    if not isinstance(plan, dict) or not plan:
        raise WorkspaceSnapshotError(
            "the evaluation plan is not a declaration document; baselines and populations must be declared before "
            "any outcome is read"
        )
    if plan.get("declared_at") is not None and _instant(plan["declared_at"], "the plan declared_at") > saved_at:
        raise WorkspaceSnapshotError("the evaluation plan declared_at is dated after the moment it was saved")
    status_as_of = comparison_source.get("nfl_status_as_of")
    if status_as_of is not None:
        try:
            stated = _instant(status_as_of, "the comparison nfl_status_as_of")
        except WorkspaceSnapshotError:
            stated = None                 # the catalog carries an RFC-1123 string here; unparseable is not a lie
        if stated is not None and stated > saved_at:
            raise WorkspaceSnapshotError("the comparison nfl_status_as_of is dated after the moment it was saved")

    return {
        "snapshot_id": snapshot_id,
        "saved_at": saved_at.isoformat(),
        "forecast_date": forecast_date.isoformat(),
        "report_generated_at": generated["report_generated_at"],
        "catalog_generated_at": generated["catalog_generated_at"],
        "market_as_of": _text(rank_source.get("market_as_of"), "market_as_of"),
        "ownership_as_of": _text(rank_source.get("ownership_as_of"), "ownership_as_of"),
        "years": list(years),
        "source": {
            "report_run": _text(rank_source.get("report_run"), "report_run"),
            "report_sha256": _text(rank_source.get("report_sha256"), "report_sha256"),
            "market_sha256": _text(rank_source.get("market_sha256"), "market_sha256"),
            "league_sha256": _text(rank_source.get("league_sha256"), "league_sha256"),
            "catalog_run": _text(comparison_source.get("catalog_run"), "catalog_run"),
            "catalog_content_sha256": catalog_content_sha,
        },
        "counts": _counts(ranks, comparison, strict_json(bundle.artifacts["market.json"], what="the archived market")),
        "evaluation_plan": plan,
        "capture_code_sha": code_sha,
        "evaluation_status": "ungraded",
    }


def _validated_code_sha(code_sha: Any) -> str:
    text = _text(code_sha, "code_sha")
    if text == UNKNOWN_CODE:
        return text
    if len(text) == 40 and not set(text) - set("0123456789abcdef"):
        return text
    raise WorkspaceSnapshotError(
        f"code_sha {text!r} is neither a commit nor {UNKNOWN_CODE!r}; the capture code identity is never a model "
        f"version, and claiming a commit that does not contain the running code is worse than admitting ignorance"
    )


def _validated_instant(captured_at: Any) -> datetime:
    if not isinstance(captured_at, datetime) or captured_at.tzinfo is None:
        raise WorkspaceSnapshotError(
            "captured_at must be a timezone-aware instant; a naive clock cannot be compared with a dated source"
        )
    return captured_at.astimezone(timezone.utc)


# --- reading an archived snapshot -----------------------------------------------------------------------


def _load_archived(directory: Path) -> tuple[dict[str, Any], SnapshotBundle]:
    """Read one archived snapshot and prove it is what it says it is."""
    manifest_path = directory / MANIFEST_NAME
    if manifest_path.is_symlink():
        raise WorkspaceSnapshotError(f"the archived {directory.name}/{MANIFEST_NAME} is a symlink, not a file")
    try:
        manifest = strict_json(manifest_path.read_bytes(), f"the archived {directory.name}/{MANIFEST_NAME}")
    except OSError as exc:
        raise WorkspaceSnapshotError(f"the archived snapshot {directory.name} has no readable {MANIFEST_NAME}") from exc
    if not isinstance(manifest, dict):
        raise WorkspaceSnapshotError(
            f"the archived {directory.name}/{MANIFEST_NAME} is a {type(manifest).__name__}, not a manifest"
        )

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise WorkspaceSnapshotError(
            f"the archived snapshot {directory.name} declares schema {manifest.get('schema_version')!r}, not "
            f"{SCHEMA_VERSION!r}"
        )
    files = manifest.get("files")
    receipt = manifest.get("receipt")
    if not isinstance(files, dict) or not isinstance(receipt, dict):
        raise WorkspaceSnapshotError(f"the archived {directory.name}/{MANIFEST_NAME} is missing its files or receipt")

    payloads: dict[str, bytes] = {}
    for name in (*ARTIFACT_NAMES, *DERIVED_NAMES):
        member = directory / name
        if member.is_symlink():
            raise WorkspaceSnapshotError(
                f"the archived {directory.name}/{name} is a symlink; an archived file must be the real bytes"
            )
        try:
            payload = member.read_bytes()
        except OSError as exc:
            raise WorkspaceSnapshotError(f"the archived snapshot {directory.name} is missing {name}") from exc
        recorded = files.get(name)
        actual = _sha256(payload)
        if recorded != actual:
            raise WorkspaceSnapshotError(
                f"the archived {directory.name}/{name} does not match the hash recorded beside it "
                f"({actual[:12]}… against {str(recorded)[:12]}…); the archive has been altered"
            )
        payloads[name] = payload

    bundle = SnapshotBundle(
        artifacts={name: payloads[name] for name in ARTIFACT_NAMES},
        ranks=json.loads(payloads["ranks.json"]),
        comparison=json.loads(payloads["comparison.json"]),
    )
    identity = _content_id(bundle.artifacts, {name: payloads[name] for name in DERIVED_NAMES})
    if identity != directory.name or receipt.get("snapshot_id") != directory.name:
        raise WorkspaceSnapshotError(
            f"the archived snapshot {directory.name} does not hash to its own name; the archive has been altered"
        )

    # The receipt is a pure function of the archived payloads plus the two facts it records about the save itself.
    # Re-deriving it is what catches an edited count, which no file hash would notice.
    rebuilt = _build_receipt(
        bundle,
        snapshot_id=directory.name,
        saved_at=_instant(receipt.get("saved_at"), "the archived saved_at"),
        code_sha=_validated_code_sha(receipt.get("capture_code_sha")),
    )
    if rebuilt != receipt:
        raise WorkspaceSnapshotError(
            f"the archived receipt for {directory.name} does not match the payloads it summarises; the archive has "
            f"been altered"
        )
    return receipt, bundle


# --- the public surface --------------------------------------------------------------------------------------


def save_snapshot(
    root: Path | str, bundle: SnapshotBundle, *, captured_at: datetime, code_sha: str
) -> dict[str, Any]:
    """Archive one snapshot. Returns ``{created, snapshot}``; saving the same content twice returns the first one."""
    saved_at = _validated_instant(captured_at)
    code = _validated_code_sha(code_sha)
    artifacts = _validated_artifacts(bundle.artifacts)
    derived = {
        "ranks.json": canonical_bytes(bundle.ranks, what="the ranks payload"),
        "comparison.json": canonical_bytes(bundle.comparison, what="the comparison payload"),
    }
    checked = SnapshotBundle(artifacts=artifacts, ranks=bundle.ranks, comparison=bundle.comparison)
    snapshot_id = _content_id(artifacts, derived)
    receipt = _build_receipt(checked, snapshot_id=snapshot_id, saved_at=saved_at, code_sha=code)

    archive = _archive_root(root)
    destination = _snapshot_dir(archive, snapshot_id)
    if destination.exists():
        existing, _ = _load_archived(destination)
        return {"created": False, "snapshot": existing}

    archive.mkdir(parents=True, exist_ok=True)
    payloads = {**artifacts, **derived}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "receipt": receipt,
        "files": {name: _sha256(payload) for name, payload in payloads.items()},
    }
    staging = Path(tempfile.mkdtemp(dir=archive, prefix=TEMP_PREFIX))
    try:
        for name, payload in payloads.items():
            (staging / name).write_bytes(payload)
        (staging / MANIFEST_NAME).write_bytes(canonical_bytes(manifest, what="the archive manifest"))
        try:
            os.rename(staging, destination)
        except OSError:
            # Either another save published this exact content first — in which case converging on it is correct —
            # or the publish genuinely failed and the caller must hear about it.
            if not destination.exists():
                raise
            shutil.rmtree(staging, ignore_errors=True)
            existing, _ = _load_archived(destination)
            return {"created": False, "snapshot": existing}
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"created": True, "snapshot": receipt}


def list_snapshots(root: Path | str) -> list[dict[str, Any]]:
    """Every archived receipt, newest first. An archive that does not exist is empty, and looking does not create it."""
    archive = _archive_root(root)
    if not archive.exists():
        return []
    receipts: list[dict[str, Any]] = []
    for entry in sorted(archive.iterdir()):
        if entry.name.startswith(TEMP_PREFIX):
            continue
        named_like_a_snapshot = len(entry.name) == 64 and not set(entry.name) - set("0123456789abcdef")
        if not named_like_a_snapshot:
            continue
        # Something wearing a snapshot's name that is not a directory is a snapshot that has been replaced. Saying
        # so is the point: a listing that silently skipped it would report the archive as smaller than it is.
        if entry.is_symlink() or not entry.is_dir():
            raise WorkspaceSnapshotError(
                f"the archive entry {entry.name} is named like a snapshot but is not a directory"
            )
        receipt, _ = _load_archived(_snapshot_dir(archive, entry.name))
        receipts.append(receipt)
    receipts.sort(key=lambda item: (item["saved_at"], item["snapshot_id"]), reverse=True)
    return receipts


def read_snapshot(root: Path | str, snapshot_id: str) -> dict[str, Any]:
    """One archived snapshot, validated: its receipt and the two payloads the surface read."""
    archive = _archive_root(root)
    directory = _snapshot_dir(archive, snapshot_id)
    if not directory.is_dir():
        raise FileNotFoundError(f"no archived snapshot {snapshot_id}")
    receipt, bundle = _load_archived(directory)
    return {"snapshot": receipt, "ranks": bundle.ranks, "comparison": bundle.comparison}
