"""QB-1 execution surfaces: D1 receipt admission, H5 bridge, D5 panels, terminal path.

GREEN against the frozen TW14-QB1-1 execution RED (Codex, 2026-08-14):
``tests/contract/test_qb1_execution_red.py`` (`4e6d7dc5…`) and the unparked seams of
``tests/contract/test_qb_validation_program_red.py`` (`7e95079…`). Every refusal is a
named :class:`QBValidationFailure`; nothing here computes a study result, and every
emitted mapping carries ``decision_supported=False`` where the contract pins it.

Registration: binding pin ``37065566…`` — registered values are read from the canonical
object handed in by callers, never re-declared here as tunable constants.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Mapping

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
from src.dynasty_genius.eval.qb_validation.guards import validate_report_output
from src.dynasty_genius.eval.qb_validation.registration import (
    require_registration_hash,
)

# The exact seven D1 datasets, spec order (sources.VALIDATION_DATASETS mirrors this;
# imported there rather than re-typed here to keep one authority).
from src.dynasty_genius.eval.qb_validation.sources import (
    VALIDATION_DATASETS,
    load_validation_sources,
)
from src.dynasty_genius.eval.qb_validation.status import evaluate_power_and_status

# The frozen runner output root, repo-relative (F24/F31; shipped OUTPUT_ROOT law).
FROZEN_OUTPUT_ROOT = Path("app") / "data" / "backtest" / "qb_validation"

# The binding pre-registration pin: the canonical-JSON SHA-256 of the ratified
# registration object (docs/validation/2026-07-21-qb-1-study-registration.json;
# prose §Authority in the .md twin). Every D1 completion receipt must carry
# exactly this pin — a fetch not bound to the registration is not admissible
# (green-review G2).
REGISTRATION_PIN = "37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d"

# The D5 registered case panel (governing spec D5; the seven ids are pinned by the
# execution RED — Daniels/Nix enter as SECOND-SEASON predictions per registration §4).
CASE_PANEL_IDS = frozenset(
    {
        "daniels_2025",
        "nix_2025",
        "mayfield_2025",
        "richardson_2025",
        "maye_2025",
        "allen_2019_twin",
        "richardson_2024_twin",
    }
)

_GENERATIONAL_SUFFIXES = re.compile(r"\b(jr|sr|ii|iii|iv)\b")
_PUNCTUATION = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ── D1: completion-receipt admission (fail-before-parse) ───────────────────────


def admit_fetch_manifest(
    raw_root: Path,
    *,
    repo_root: Path,
    frame_loader: Callable[[Path], Any],
    expected_registration_pin: str = REGISTRATION_PIN,
) -> dict[str, dict[str, Any]]:
    """Admit the seven-dataset D1 substrate through its completion receipt.

    Verification ORDER is the contract: the receipt's shape, its binding
    ``registration_pin`` (green-review G2 — a receipt not bound to the exact
    registration refuses BEFORE any hashing or parsing), the exact seven-name
    set, and EVERY snapshot's existence, byte count, and SHA-256 are verified
    BEFORE ``frame_loader`` is called once — content drift refuses as
    ``source_snapshot_drift`` with zero frames parsed. Emitted per-dataset state
    carries the §11 presence metadata (raw_snapshot_path, source_timestamp,
    parser_version, completeness, sha256).
    """
    raw_root = Path(raw_root)
    manifest_path = raw_root / "fetch_manifest.json"
    if not manifest_path.is_file():
        raise QBValidationFailure(
            "source_unavailable", f"no completion receipt at {manifest_path}"
        )
    try:
        receipt = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QBValidationFailure(
            "source_unavailable", f"completion receipt unreadable: {exc}"
        ) from exc
    if not isinstance(receipt, dict) or not isinstance(receipt.get("datasets"), dict):
        raise QBValidationFailure(
            "source_unavailable", "completion receipt lacks a datasets mapping"
        )
    receipt_pin = receipt.get("registration_pin")
    if not receipt_pin:
        raise QBValidationFailure(
            "preregistration_missing",
            "completion receipt lacks registration_pin — the fetch is not "
            "bound to the registration",
        )
    if receipt_pin != expected_registration_pin:
        raise QBValidationFailure(
            "registration_drift",
            f"receipt registration_pin {receipt_pin!r} != binding "
            f"{expected_registration_pin}",
        )
    datasets = receipt["datasets"]
    if set(datasets) != set(VALIDATION_DATASETS):
        raise QBValidationFailure(
            "source_unavailable",
            f"receipt datasets {sorted(datasets)} != pinned {sorted(VALIDATION_DATASETS)}",
        )
    source_timestamp = receipt.get("finished_at")
    parser_version = receipt.get("nflreadpy_version")
    if not source_timestamp or not parser_version:
        raise QBValidationFailure(
            "source_unavailable", "receipt lacks finished_at/nflreadpy_version"
        )

    # Pass 1 — verify EVERY snapshot before parsing ANY frame.
    verified: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for dataset in VALIDATION_DATASETS:
        snapshots = (datasets[dataset] or {}).get("snapshots")
        if not isinstance(snapshots, list) or not snapshots:
            raise QBValidationFailure(
                "source_unavailable", f"{dataset}: receipt has no snapshots"
            )
        rows: list[tuple[Path, dict[str, Any]]] = []
        for snapshot in snapshots:
            path = Path(repo_root) / str(snapshot.get("file"))
            if not path.is_file():
                raise QBValidationFailure(
                    "source_snapshot_drift", f"{dataset}: missing snapshot {path}"
                )
            if path.stat().st_size != snapshot.get("bytes"):
                raise QBValidationFailure(
                    "source_snapshot_drift", f"{dataset}: byte-count drift at {path}"
                )
            if _sha256_file(path) != snapshot.get("sha256"):
                raise QBValidationFailure(
                    "source_snapshot_drift", f"{dataset}: sha256 drift at {path}"
                )
            rows.append((path, snapshot))
        verified[dataset] = rows

    # Pass 2 — parse, verify the receipt's row claims against the parsed frames.
    sources: dict[str, dict[str, Any]] = {}
    for dataset in VALIDATION_DATASETS:
        frames = []
        claimed_rows = 0
        first_path, first_snapshot = verified[dataset][0]
        for path, snapshot in verified[dataset]:
            frame = frame_loader(path)
            if len(frame) != snapshot.get("rows"):
                raise QBValidationFailure(
                    "source_snapshot_drift",
                    f"{dataset}: parsed rows {len(frame)} != receipt {snapshot.get('rows')}",
                )
            claimed_rows += int(snapshot.get("rows") or 0)
            frames.append(frame)
        if len(frames) == 1:
            combined = frames[0]
        else:
            import pandas as pd

            combined = pd.concat(frames, ignore_index=True)
        sources[dataset] = {
            "status": "ok",
            "frame": combined,
            "rows": claimed_rows,
            "metadata": {
                "raw_snapshot_path": str(first_path),
                "source_timestamp": source_timestamp,
                "parser_version": str(parser_version),
                "completeness": "complete",
                "sha256": first_snapshot.get("sha256"),
                # R2-G6: EVERY admitted snapshot's identity is preserved — a
                # multi-snapshot dataset (pbp: 11 files) must reach terminal
                # provenance complete, never first-file-only.
                "snapshots": [
                    {
                        "path": str(path),
                        "sha256": snapshot.get("sha256"),
                        "rows": snapshot.get("rows"),
                    }
                    for path, snapshot in verified[dataset]
                ],
            },
        }
    return sources


def admit_and_load_validation_pool(
    raw_root: Path,
    *,
    repo_root: Path,
    frame_loader: Callable[[Path], Any],
    expected_registration_pin: str = REGISTRATION_PIN,
) -> dict[str, Mapping[str, Any]]:
    """The pinned D1 composition seam: receipt admission INTO the F1 source gate.

    ``admit_fetch_manifest`` emits the receipt envelope (completeness
    ``"complete"``, verified snapshot provenance); ``load_validation_sources``
    requires the F1 shape (completeness ``"ok"``). This seam is the ONE
    sanctioned translation between them: admission first (hash-before-parse,
    registration-pin binding), then a shape-exact envelope mapping that
    rewrites ONLY the receipt's verified ``"complete"`` completeness into the
    F1 gate's ``"ok"`` vocabulary, then the UNCHANGED F1 gate. Any other
    completeness value passes through untranslated and refuses downstream —
    the seam never launders an unverified state. (Green-review G1: the two
    stages were individually green and jointly unusable; the composition is
    now itself a pinned contract.)
    """
    admitted = admit_fetch_manifest(
        raw_root,
        repo_root=repo_root,
        frame_loader=frame_loader,
        expected_registration_pin=expected_registration_pin,
    )
    # R15 (Codex registration read `qb1_pbp_parse_seam_registration_read_
    # codex_v1.md`; David's bounded word, 2026-08-16): the raw snapshot is
    # hash-verified BEFORE parse (above, byte-untouched on disk), and the
    # registered transformation the registration pins "at parse" —
    # ``posteam → offense_team`` plus the REG filter — is applied HERE on the
    # read-back copy via the shared adapter parser, so the F1 gate and the
    # matrix receive the PARSED frame §11 describes. One parser, one rename
    # table (the adapter's own); a named ingest refusal crosses the F33 wall
    # as the SAME named study failure, never a generic error. The import is
    # function-local, mirroring study_matrix, so the one-way F33 wall keeps
    # its direction (study → adapter only at call time).
    from src.dynasty_genius.adapters.nflreadpy_qb_adapter import (
        ValidationIngestError,
        parse_validation_pbp,
    )

    # Parse BEFORE the F1 source gate (the ruled ordering — the read pins the
    # shared parse "after receipt admission, before the parsed-frame source
    # gate/matrix", and the F1 gate's own contract gates a PARSED frame). An
    # absent pbp entry is left for the gate's named "pbp: absent" refusal —
    # the only skip condition is one the gate itself refuses on.
    pool: dict[str, dict[str, Any]] = {}
    for dataset, state in admitted.items():
        metadata = dict(state["metadata"])
        if metadata.get("completeness") == "complete":
            metadata["completeness"] = "ok"
        entry = {**state, "metadata": metadata}
        if dataset == "pbp":
            try:
                entry["frame"] = parse_validation_pbp(state["frame"])
            except ValidationIngestError as failure:
                raise QBValidationFailure(failure.reason, failure.detail) from failure
        pool[dataset] = entry
    return load_validation_sources(pool)


# ── H5: identity bridge (fp_id → fantasypros_id → gsis_id ONLY) ────────────────


def validate_identity_duplicates(
    rows: list[Mapping[str, Any]], *, source_key: str, target_key: str
) -> dict[str, Any]:
    """F16: duplicate identical claims collapse AUDIBLY; conflicts exclude to triage."""
    claims: dict[str, list[str]] = {}
    duplicate_count = 0
    for row in rows:
        source_id = row.get(source_key)
        target_id = row.get(target_key)
        if source_id is None or target_id is None:
            continue
        bucket = claims.setdefault(str(source_id), [])
        if str(target_id) in bucket:
            duplicate_count += 1
        else:
            bucket.append(str(target_id))
    mapping: dict[str, str] = {}
    triage: list[dict[str, Any]] = []
    conflict_count = 0
    for source_id, targets in claims.items():
        if len(targets) == 1:
            mapping[source_id] = targets[0]
        else:
            conflict_count += 1
            triage.append(
                {
                    "source_id": source_id,
                    "target_ids": sorted(targets),
                    "reason": "identity_conflict",
                }
            )
    return {
        "mapping": mapping,
        "duplicate_count": duplicate_count,
        "conflict_count": conflict_count,
        "triage": triage,
    }


def build_h5_static_join(
    *,
    dp_rows: list[Mapping[str, Any]],
    crosswalk_rows: list[Mapping[str, Any]],
    observed_at: str,
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    """The §9.3 static join: DP ``fp_id`` → crosswalk ``fantasypros_id`` → ``gsis_id``.

    Name equality can NEVER create a join (the F32 reconciliation gate stays an
    independent check, not the join key). Every joined pair carries the honest
    retrospective provenance the registration pins: ``observed_at`` (the crosswalk
    snapshot date) and ``assumed_effective=True``.
    """
    join_contract = (registration.get("h5") or {}).get("join") or {}
    if join_contract.get("pit_bridge_used") is not False:
        raise QBValidationFailure(
            "registration_drift", "h5.join.pit_bridge_used must be false by registration"
        )
    duplicates = validate_identity_duplicates(
        list(crosswalk_rows), source_key="fantasypros_id", target_key="gsis_id"
    )
    crosswalk_names = {
        str(row["fantasypros_id"]): row.get("name")
        for row in crosswalk_rows
        if row.get("fantasypros_id") is not None
    }
    joined_rows: list[dict[str, Any]] = []
    unresolved_count = 0
    for dp_row in dp_rows:
        fp_id = dp_row.get("fp_id")
        gsis_id = duplicates["mapping"].get(str(fp_id)) if fp_id is not None else None
        if gsis_id is None:
            unresolved_count += 1
            continue
        joined_rows.append(
            {
                **{k: v for k, v in dp_row.items()},
                "gsis_id": gsis_id,
                "crosswalk_name": crosswalk_names.get(str(fp_id)),
                "observed_at": observed_at,
                "assumed_effective": True,
            }
        )
    return {
        "joined_rows": joined_rows,
        "unresolved_count": unresolved_count,
        "duplicate_count": duplicates["duplicate_count"],
        "conflict_count": duplicates["conflict_count"],
        "triage": duplicates["triage"],
    }


def validate_join_coverage(
    joined: int, evaluable: int, *, registration: Mapping[str, Any]
) -> dict[str, Any]:
    """F18: coverage below the REGISTERED floor excludes the fold by rule."""
    floor = ((registration.get("h5") or {}).get("join") or {}).get("coverage_floor")
    if not isinstance(floor, (int, float)):
        raise QBValidationFailure(
            "registration_drift", "h5.join.coverage_floor missing from registration"
        )
    if isinstance(evaluable, bool) or not isinstance(evaluable, int) or evaluable <= 0:
        raise QBValidationFailure(
            "identity_join_empty", f"evaluable pool is {evaluable!r}"
        )
    if isinstance(joined, bool) or not isinstance(joined, int) or not 0 <= joined <= evaluable:
        # Green-review G7: a joined count outside [0, evaluable] is impossible
        # cardinality (coverage > 1.0 or negative), never admissible evidence.
        raise QBValidationFailure(
            "join_coverage_invalid",
            f"joined {joined!r} must be an int with 0 <= joined <= "
            f"evaluable {evaluable!r}",
        )
    coverage = joined / evaluable
    if coverage < floor:
        raise QBValidationFailure(
            "join_coverage_low",
            f"coverage {coverage:.4f} below registered floor {floor}",
        )
    return {"coverage": coverage, "admitted": True, "decision_supported": False}


def _normalize_name(name: str) -> str:
    """The REGISTERED normalization chain (h5.join.normalization), no additions:
    NFKD → ASCII fold → lowercase → strip punctuation and generational suffixes →
    collapse whitespace."""
    folded = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    lowered = folded.lower()
    no_punctuation = _PUNCTUATION.sub(" ", lowered)
    no_suffix = _GENERATIONAL_SUFFIXES.sub(" ", no_punctuation)
    return _WHITESPACE.sub(" ", no_suffix).strip()


def reconcile_identity_names(
    pairs: list[Mapping[str, Any]], *, registration: Mapping[str, Any]
) -> dict[str, Any]:
    """F32: the independent name-reconciliation gate over JOINED pairs.

    A missing raw name COUNTS in the mismatch numerator (conservative, registered).
    Strictly-greater-than-threshold breaches; exactly-at-threshold admits.
    """
    join_contract = (registration.get("h5") or {}).get("join") or {}
    threshold = join_contract.get("reconciliation_threshold")
    if not isinstance(threshold, (int, float)):
        raise QBValidationFailure(
            "registration_drift", "h5.join.reconciliation_threshold missing"
        )
    if not pairs:
        raise QBValidationFailure("identity_join_empty", "no joined pairs to reconcile")
    mismatch_count = 0
    for pair in pairs:
        dp_name = pair.get("dp_name")
        crosswalk_name = pair.get("crosswalk_name")
        if not dp_name or not crosswalk_name:
            mismatch_count += 1  # missing raw name counts, by registered rule
            continue
        if _normalize_name(str(dp_name)) != _normalize_name(str(crosswalk_name)):
            mismatch_count += 1
    mismatch_rate = mismatch_count / len(pairs)
    if mismatch_rate > threshold:
        raise QBValidationFailure(
            "join_reconciliation_failed",
            f"mismatch rate {mismatch_rate:.4f} exceeds registered {threshold}",
        )
    return {
        "mismatch_count": mismatch_count,
        "mismatch_rate": mismatch_rate,
        "admitted": True,
        "decision_supported": False,
    }


def load_h5_snapshots(
    root: Path, *, registration: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """§9.1: bind the four registered DP snapshot files to their pinned SHA-256s.

    Fail-closed on a missing file or one byte of drift; the registered pins are
    the ONLY admission basis."""
    root = Path(root)
    snapshots = (registration.get("h5") or {}).get("snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise QBValidationFailure(
            "registration_drift", "h5.snapshots missing from registration"
        )
    results: list[dict[str, Any]] = []
    for snapshot in sorted(snapshots, key=lambda row: row["season"]):
        path = root / f"values_{snapshot['comparison_date']}.csv"
        if not path.is_file():
            raise QBValidationFailure(
                "source_unavailable", f"registered H5 snapshot missing: {path}"
            )
        actual = _sha256_file(path)
        if actual != snapshot["sha256"]:
            raise QBValidationFailure(
                "source_snapshot_drift",
                f"{path.name}: sha256 {actual} != registered {snapshot['sha256']}",
            )
        results.append(
            {
                "season": snapshot["season"],
                "comparison_date": snapshot["comparison_date"],
                "path": path,
                "sha256": actual,
                "bytes": path.stat().st_size,
            }
        )
    return results


# ── D5 panels (F10 / F13 / F29) ────────────────────────────────────────────────


def require_case_panel(panel: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """F10: the registered case panel — exactly the seven ids, each row honest."""
    ids = {row.get("id") for row in panel}
    if ids != set(CASE_PANEL_IDS):
        raise QBValidationFailure(
            "case_panel_incomplete",
            f"case panel ids {sorted(map(str, ids))} != registered {sorted(CASE_PANEL_IDS)}",
        )
    if len(panel) != len(CASE_PANEL_IDS):
        # Green-review G7: an id-set check alone admits duplicate rows — the
        # panel is EXACTLY seven rows, one per registered id.
        raise QBValidationFailure(
            "case_panel_incomplete",
            f"case panel carries {len(panel)} rows for {len(CASE_PANEL_IDS)} "
            "registered ids — duplicate rows are not admissible",
        )
    for row in panel:
        if row.get("decision_supported") is not False:
            raise QBValidationFailure(
                "no_verdict_violation", f"case {row.get('id')} lacks decision_supported=False"
            )
        if row.get("id") in {"daniels_2025", "nix_2025"} and "second-season" not in str(
            row.get("scope_note", "")
        ):
            raise QBValidationFailure(
                "case_panel_incomplete",
                f"{row['id']} must carry the second-season scope note (registration §4)",
            )
    return list(panel)


def require_threshold_sensitivity(panel: Mapping[str, Any]) -> Mapping[str, Any]:
    """F13: the binary-vs-continuous archetype panel with ±1 yd/game boundary cases."""
    required = (
        "binary_dual_threat_gate",
        "continuous_rushing_moderator",
        "boundary_cases_yards_per_game",
    )
    missing = [key for key in required if key not in panel]
    if missing:
        raise QBValidationFailure(
            "sensitivity_panel_incomplete", f"threshold panel missing {missing}"
        )
    boundaries = panel["boundary_cases_yards_per_game"]
    if not isinstance(boundaries, list) or not {-1, 1} <= set(boundaries):
        raise QBValidationFailure(
            "sensitivity_panel_incomplete",
            "threshold panel must include the ±1 yd/game boundary cases",
        )
    return panel


def validate_sensitivity_panel(panel: Mapping[str, Any]) -> Mapping[str, Any]:
    """F29: unfiltered primary + ≥4-games slice + the H5 margin readout, all present."""
    unfiltered = panel.get("unfiltered_primary")
    min_four = panel.get("min_four_games")
    margins = panel.get("h5_margin_sensitivity")
    if not isinstance(unfiltered, Mapping) or unfiltered.get("min_qualifying_games") is not None:
        raise QBValidationFailure(
            "sensitivity_panel_incomplete",
            "unfiltered_primary with min_qualifying_games=None is required (F29)",
        )
    if not isinstance(min_four, Mapping) or min_four.get("min_qualifying_games") != 4:
        raise QBValidationFailure(
            "sensitivity_panel_incomplete", "min_four_games slice is required (F29)"
        )
    if not isinstance(margins, Mapping) or margins.get("margins") != [0.025, 0.05, 0.10]:
        raise QBValidationFailure(
            "sensitivity_panel_incomplete",
            "h5_margin_sensitivity must carry the registered margins",
        )
    return panel


# ── F25 / F31 / F33 boundary guards ────────────────────────────────────────────


def validate_frozen_hashes(expected: Mapping[Path, str]) -> None:
    """F25: one byte of drift on a frozen boundary artifact refuses by name."""
    for path, pinned in expected.items():
        path = Path(path)
        if not path.is_file() or _sha256_file(path) != pinned:
            raise QBValidationFailure(
                "frozen_boundary_drift", f"frozen artifact drifted or missing: {path}"
            )


def validate_artifact_tracking(paths: list[Path], *, repo_root: Path) -> None:
    """F31: every study artifact lives under the frozen output root — no exceptions."""
    root = (Path(repo_root) / FROZEN_OUTPUT_ROOT).resolve()
    for path in paths:
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(root):
            raise QBValidationFailure(
                "output_path_violation",
                f"{resolved} is outside the frozen output root {root}",
            )


_CONSUMER_SCAN_ROOTS = ("src", "app")

# The three MARKER CLASSES of the registered F33 wall (green-review G5):
#   package  — importing or naming the study package;
#   raw_root — reading/naming the frozen study output root;
#   loaders  — importing or calling the adapter's seven registered
#              ``load_validation_*`` ingestion functions (word-bounded, so a
#              private helper like ``_load_validation_report`` never matches).
_PACKAGE_MARKERS = ("eval.qb_validation", "eval/qb_validation")
_RAW_ROOT_MARKER = "app/data/backtest/qb_validation"
_VALIDATION_LOADER_PATTERN = re.compile(
    r"\bload_validation_(?:weekly_stats|season_summary|players|rosters"
    r"|ff_playerids|draft_picks|pbp)\b"
)

# OCCURRENCE-SPECIFIC allowlist: repo-relative path (exact file, or the study
# package directory prefix) → the marker classes that path may legitimately
# hold. A file holding ANY class not granted to it violates the wall — there
# are no whole-file escape hatches (green-review G5).
_STUDY_PACKAGE_PREFIX = "src/dynasty_genius/eval/qb_validation/"
_CONSUMER_ALLOWED_CLASSES: dict[str, frozenset[str]] = {
    # Single-adapter law (QB-1 spec v8 D1): the repo's ONE nflreadpy adapter
    # DEFINES the seven loaders and names the raw root; it may not import the
    # study package.
    "src/dynasty_genius/adapters/nflreadpy_qb_adapter.py": frozenset(
        {"loaders", "raw_root"}
    ),
    # Declarative governance surfaces: registry/daily-control may NAME the raw
    # root in route prose; neither may import the package or touch the loaders.
    "src/dynasty_genius/sources/source_registry.py": frozenset({"raw_root"}),
    "src/dynasty_genius/sources/daily_control.py": frozenset({"raw_root"}),
}
_STUDY_PACKAGE_CLASSES = frozenset({"package", "raw_root", "loaders"})


def _consumer_marker_classes(text: str) -> set[str]:
    present: set[str] = set()
    if any(marker in text for marker in _PACKAGE_MARKERS):
        present.add("package")
    if _RAW_ROOT_MARKER in text:
        present.add("raw_root")
    if _VALIDATION_LOADER_PATTERN.search(text):
        present.add("loaders")
    return present


def enforce_consumer_boundary(*, repo_root: Path) -> None:
    """F33: no product surface imports the study package, calls the registered
    ``load_validation_*`` adapter functions, or reads the frozen study root.

    The wall is enforced per MARKER CLASS with an occurrence-specific
    allowlist: the study package holds every class; the single adapter holds
    its own loader definitions and the raw-root name; the two declarative
    governance surfaces may name the raw root in prose. Everything else under
    ``src``/``app`` holding any class is a consumer-boundary violation (the
    descriptive/no-verdict wall)."""
    repo = Path(repo_root)
    for scan_root in _CONSUMER_SCAN_ROOTS:
        base = repo / scan_root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            relative = path.relative_to(repo).as_posix()
            if relative.startswith(_STUDY_PACKAGE_PREFIX):
                allowed = _STUDY_PACKAGE_CLASSES
            else:
                allowed = _CONSUMER_ALLOWED_CLASSES.get(relative, frozenset())
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            violating = _consumer_marker_classes(text) - allowed
            if violating:
                raise QBValidationFailure(
                    "consumer_boundary_violation",
                    f"{relative} holds unsanctioned QB-1 study markers "
                    f"{sorted(violating)}",
                )


# ── D5 terminal report + atomic writer + runner ────────────────────────────────

_REPORT_SCHEMA = "qb_validation_report.v1"
_METRIC_BLOCKS = ("inputs", "folds", "comparisons", "case_panel", "sensitivity_panels")


def assemble_terminal_report(
    *,
    generated_at: str,
    registration_hash: str,
    run_status: str,
    failure_reason: str | None = None,
    inputs: Mapping[str, Any] | None = None,
    folds: list[Mapping[str, Any]] | None = None,
    comparisons: list[Mapping[str, Any]] | None = None,
    case_panel: list[Mapping[str, Any]] | None = None,
    sensitivity_panels: list[Mapping[str, Any]] | None = None,
    disclosures: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """D5: the single terminal report shape — failed carries NO metric-bearing block;
    ok carries the complete schema and passes the F26 report validator."""
    if run_status == "failed":
        if not failure_reason:
            raise QBValidationFailure(
                "report_schema_invalid", "failed report requires failure_reason"
            )
        if disclosures is not None:
            # The failed shape is pinned metric-free at exactly six keys; the
            # registered disclosures ride ONLY a complete ok report (R2-G3).
            raise QBValidationFailure(
                "report_schema_invalid", "failed report may not carry disclosures"
            )
        supplied = [
            name
            for name, value in zip(
                _METRIC_BLOCKS, (inputs, folds, comparisons, case_panel, sensitivity_panels)
            )
            if value is not None
        ]
        if supplied:
            raise QBValidationFailure(
                "report_schema_invalid",
                f"failed report may not carry metric blocks: {supplied}",
            )
        return {
            "schema_version": _REPORT_SCHEMA,
            "generated_at": generated_at,
            "registration_hash": registration_hash,
            "run_status": "failed",
            "failure_reason": failure_reason,
            "decision_supported": False,
        }
    if run_status != "ok":
        raise QBValidationFailure(
            "report_schema_invalid", f"unknown run_status {run_status!r}"
        )
    if failure_reason is not None:
        raise QBValidationFailure(
            "report_schema_invalid", "ok report may not carry failure_reason"
        )
    missing = [
        name
        for name, value in zip(
            (*_METRIC_BLOCKS, "disclosures"),
            (inputs, folds, comparisons, case_panel, sensitivity_panels, disclosures),
        )
        if value is None
    ]
    if missing:
        # R3-G1 ruling: disclosures are REQUIRED on every ok report — an ok
        # publication without the registered disclosures is not a valid D5
        # report shape.
        raise QBValidationFailure(
            "report_schema_invalid", f"ok report missing blocks: {missing}"
        )
    report = {
        "schema_version": _REPORT_SCHEMA,
        "generated_at": generated_at,
        "registration_hash": registration_hash,
        "run_status": "ok",
        "inputs": dict(inputs),
        "folds": [dict(row) for row in folds],
        "comparisons": [dict(row) for row in comparisons],
        "case_panel": [dict(row) for row in case_panel],
        "sensitivity_panels": [dict(row) for row in sensitivity_panels],
        "decision_supported": False,
    }
    if disclosures is not None:
        report["disclosures"] = [dict(row) for row in disclosures]
    return report


def write_terminal_report_atomic(
    payload: Mapping[str, Any],
    destination: Path,
    *,
    repo_root: Path,
    replace: Callable[[Path, Path], None] | None = None,
) -> None:
    """Atomic terminal write under the frozen root: temp sibling → replace.

    An interrupted replacement leaves NO partial final artifact (the temp is
    cleaned up and the destination never exists half-written)."""
    destination = Path(destination)
    validate_artifact_tracking([destination], repo_root=repo_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".tmp")
    temp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True))
    replace_fn = replace or (lambda source, target: source.replace(target))
    try:
        replace_fn(temp, destination)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


# The closed key vocabulary of a terminal report payload: the runner's own
# binding stamps, the status pair, the five metric blocks, and the registered
# disclosures. Anything else in an ``execute`` return is schema drift and
# refuses (green-review G3).
_TERMINAL_REPORT_KEYS = frozenset(
    {
        "schema_version",
        "generated_at",
        "registration_hash",
        "run_status",
        "failure_reason",
        "decision_supported",
        "disclosures",
        *_METRIC_BLOCKS,
    }
)

# The exact registered per-fold attrition vocabulary (R2-G3): the four
# registration ``outcome_classes`` attrition states plus the manifest-driven
# per-lane drop count the ridge lanes report.
_FOLD_ATTRITION_KEYS = frozenset(
    {
        "no_target_season",
        "rookie_no_priors",
        "cohort_ineligible_prior",
        "cohort_ineligible_unobserved",
        "manifest_missing",
    }
)

# The CLOSED D5 fold-flag vocabulary (R3-G2): a fold row may carry these flags
# and nothing else — an unregistered flag string is schema drift, refused.
_FOLD_FLAG_VOCABULARY = frozenset(
    {
        "fold_starved",
        "join_coverage_low",
        "join_reconciliation_failed",
        "degenerate_input",
    }
)

_COMPARISON_REQUIRED_FIELDS = (
    "id",
    "lane",
    "registered_direction",
    "pooled_delta",
    "ci95",
    "p_perm",
    "adjusted_p",
    "excluded_folds",
    "support_status",
    "evaluable_folds",
    "decision_supported",
)

# The H5 rows additionally carry their produced status-evidence fields
# (R7-G1): the NI retention pair plus the one-sided bound, the BH-adjusted
# NI probability, and the emitted flags list.
_H5_COMPARISON_REQUIRED_FIELDS = (
    "p_ni",
    "ni_met",
    "adjusted_p_ni",
    "one_sided_lower_95",
    "flags",
)


# The two disjoint registered status vocabularies (F30 model lane / §9.2 H5).
_MODEL_STATUS_VOCABULARY = frozenset(
    {"supported", "not_separable", "contradicted", "unsupported_power"}
)
_H5_STATUS_VOCABULARY = frozenset(
    {
        "market_noninferior",
        "market_superior",
        "model_superior",
        "inconclusive",
        "unsupported_power",
    }
)


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


# The four ridge feature lanes (R6/R5-G1): every fold's ``manifest_missing``
# mapping carries EXACTLY these keys — production derives them from the fitted
# ridge lanes, and an unknown or absent lane key is schema drift, refused.
RIDGE_LANE_NAMES = ("h1", "h2", "h3", "h4")

# The produced lane set a case row may report (R6-G1-4): the registered naive
# baseline, the four ridge lanes, and — for cases in the registered H5 folds —
# the h5 market lane the composition conditionally builds there. (A first
# draft asserted h5 "can never appear here" from the unconditional lane list
# alone; the real composition's conditional h5 add refuted that in the G4
# end-to-end row — recorded rather than smoothed.)
PRODUCED_LANE_NAMES = ("naive",) + RIDGE_LANE_NAMES + ("h5",)

# The shipped dual-threat rule's registered threshold (R6-G1-3): season rushing
# yards > 400 in any trailing-window season (``is_dual_threat``,
# engine_b_contract). The published F13 gate must carry EXACTLY this number —
# any other value cannot be the shipped computation.
DUAL_THREAT_RUSHING_YARDS = 400

# The shipped rule's trailing window (R7-G3): the three seasons before the
# fold's test season. A boundary row naming a season outside this window
# cannot be the shipped computation.
ARCHETYPE_WINDOW_SEASONS = 3

# The closed H5 margin-leaf schemas (R7-G2): a COMPUTED leaf carries all three
# produced outputs; an UNAVAILABLE leaf carries the named state plus all three
# explicit null outputs. Nothing else — an empty object is neither.
_MARGIN_LEAF_COMPUTED_KEYS = frozenset(
    {"p_ni", "adjusted_p_ni", "ni_met", "decision_supported"}
)
_MARGIN_LEAF_UNAVAILABLE_KEYS = _MARGIN_LEAF_COMPUTED_KEYS | {"state"}

# The produced per-contrast fold-metric shape (R5-G1): CIs are registered at
# the pooled level only, so the per-fold entry names that state rather than
# carrying a fabricated interval.
_FOLD_METRIC_REQUIRED_FIELDS = (
    "paired_delta",
    "spearman_left",
    "spearman_right",
    "common_pool_n",
    "ci",
)

# The produced case-row shape (R5-G1): a case row reports its player identity,
# fold, state, and every lane's verbatim prediction row or honest absence.
_CASE_ROW_REQUIRED_FIELDS = (
    "id",
    "player_name",
    "gsis_id",
    "fold",
    "scope_note",
    "state",
    "lanes",
)
_CASE_STATES = frozenset({"reported", "not_in_evaluable_pool"})
_CASE_LANE_STATES = frozenset({"reported", "not_in_lane_pool"})


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _finite_number_or_none(value: Any) -> bool:
    return value is None or _finite_number(value)


def _probability_or_none(value: Any) -> bool:
    return value is None or (_finite_number(value) and 0.0 <= value <= 1.0)


def _correlation_or_none(value: Any) -> bool:
    return value is None or (_finite_number(value) and -1.0 <= value <= 1.0)


def _bool_or_none(value: Any) -> bool:
    return value is None or isinstance(value, bool)


def _valid_ci95(value: Any) -> bool:
    """A registered 95% interval: a 2-list, either both-None (an honest
    unsupported state) or two finite numbers with lower <= upper."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return False
    lower, upper = value
    if lower is None and upper is None:
        return True
    return _finite_number(lower) and _finite_number(upper) and lower <= upper


def _refuse(detail: str) -> None:
    raise QBValidationFailure("report_schema_invalid", detail)


def validate_registered_report_blocks(
    blocks: Mapping[str, Any], *, registration: Mapping[str, Any]
) -> None:
    """The full registered D5 publication gate (R2-G3, deepened per R4-G1):
    an ok report must carry the registration's ENTIRE terminal shape —

    - the exact eight disclosures verbatim (+ the F26 recursive flag);
    - required ``inputs`` fields: non-empty ``snapshot_ids``, the REGISTERED
      ``settings_hash`` exactly, and a ``matrix_version`` string;
    - EXACTLY the registered fold seasons, one row each, with nonnegative
      integer census/attrition/manifest counts, ``metrics_with_CIs``, and
      flags from the closed vocabulary;
    - EXACTLY the 14 registered contrasts — id, lane, and direction bound to
      the registration — with the lane's disjoint status vocabulary, the
      H5-only ``p_ni``/``ni_met`` retention fields, and every numeric field
      typed to its REGISTERED domain (R5-G1: nonnegative fold counts, finite
      deltas, ordered real intervals, probabilities, boolean NI flags);
    - per-fold ``metrics_with_CIs`` CONTENT bound to the registered contrast
      coverage (every model contrast in every fold; H5 only in the registered
      H5 folds; no unregistered ids; typed per-contrast entries);
    - ``manifest_missing`` keyed by EXACTLY the four ridge lanes;
    - the registered case panel (``require_case_panel``) with each row
      carrying its PRODUCED player/fold/state/lane results — never a shell;
    - the three required sensitivity panels through their shipped validators
      PLUS content: the computed F13 gate/moderator structures, the full
      14-contrast pooled readout in BOTH qualifying slices, and the
      four-contrast H5 margin readout over the registered margins.

    It runs at the terminal-runner publication boundary (a RUNNER INVARIANT,
    R3-G1 ruling), so a refusal publishes as a named metric-free failed
    artifact, never a silent crash and never an atomically blessed invalid
    success. (The frozen execution RED's assembler-level success fixture was
    amended under the same ruling to carry the required disclosures; this
    deeper gate binds the RUNNER path — R4-G3 corrected the stale
    explanation that previously stood here.)

    REGISTERED GUARANTEE AND ITS BOUNDARY (David's ruling, 2026-08-16,
    resolving R11-G1-F13-SOURCE-TOTALITY): this gate guarantees INTERNAL
    COHERENCE plus CONFORMANCE TO THE FROZEN REGISTRATION — nothing more.
    Its only inputs are the report and the registration, by design:
    ``validate_registered_report_blocks(blocks, *, registration)``.
    Provenance grounding — that disclosed identities and evidence rows are
    what the producer actually read — is OUTSIDE this gate's scope, for
    every block equally (F13's disclosed pool, the H5 fold evidence, the
    comparisons, the case panel alike): an internally consistent
    fabrication is undetectable from the report alone, by construction.
    Source truth is owned by the pinned admitted inputs, the shipped
    composition, and the end-to-end contracts. Widening this signature
    with any source-binding input, or citing this gate as a provenance
    guarantee, requires a new David ruling — the R12 boundary contracts
    pin both this text and this signature against silent scope creep.
    """
    registered_disclosures = registration.get("disclosures")
    if not isinstance(registered_disclosures, list) or not registered_disclosures:
        raise QBValidationFailure(
            "registration_drift", "registration lacks its disclosures block"
        )
    # Verbatim text plus the recursive No-Verdict flag: every list-element
    # mapping in a report must carry decision_supported=False (F26), so the
    # registered rows ride with exactly that one addition and nothing else.
    expected_disclosures = [
        {**row, "decision_supported": False} for row in registered_disclosures
    ]
    supplied = blocks.get("disclosures")
    if supplied != expected_disclosures:
        raise QBValidationFailure(
            "report_schema_invalid",
            "ok report must carry the registration's exact disclosures verbatim "
            "(text unchanged, decision_supported=False on each row)",
        )
    inputs = blocks.get("inputs")
    if not isinstance(inputs, Mapping):
        raise QBValidationFailure(
            "report_schema_invalid", "ok report needs an inputs mapping"
        )
    snapshot_ids = inputs.get("snapshot_ids")
    if not isinstance(snapshot_ids, list) or not snapshot_ids:
        raise QBValidationFailure(
            "report_schema_invalid", "inputs.snapshot_ids must be a non-empty list"
        )
    registered_settings_hash = (registration.get("scoring") or {}).get("settings_hash")
    if inputs.get("settings_hash") != registered_settings_hash:
        raise QBValidationFailure(
            "report_schema_invalid",
            "inputs.settings_hash must equal the REGISTERED scoring.settings_hash",
        )
    if not isinstance(inputs.get("matrix_version"), str) or not inputs["matrix_version"]:
        raise QBValidationFailure(
            "report_schema_invalid", "inputs.matrix_version string required"
        )

    registered_seasons = list((registration.get("folds") or {}).get("test_seasons") or [])
    if not registered_seasons:
        raise QBValidationFailure(
            "registration_drift", "registration lacks folds.test_seasons"
        )
    folds = blocks.get("folds")
    if not isinstance(folds, list) or not folds:
        raise QBValidationFailure("report_schema_invalid", "ok report needs fold rows")
    fold_seasons = [row.get("test_season") for row in folds]
    if fold_seasons != registered_seasons:
        raise QBValidationFailure(
            "report_schema_invalid",
            f"fold seasons {fold_seasons} != registered {registered_seasons}",
        )
    for row in folds:
        attrition = row.get("attrition")
        if not isinstance(attrition, Mapping) or set(attrition) != _FOLD_ATTRITION_KEYS:
            raise QBValidationFailure(
                "report_schema_invalid",
                f"fold {row.get('test_season')}: attrition keys "
                f"{sorted(attrition) if isinstance(attrition, Mapping) else attrition!r} "
                f"!= registered {sorted(_FOLD_ATTRITION_KEYS)}",
            )
        if not _nonnegative_int(row.get("n_evaluable")):
            raise QBValidationFailure(
                "report_schema_invalid",
                f"fold {row.get('test_season')}: n_evaluable must be a "
                f"nonnegative int, got {row.get('n_evaluable')!r}",
            )
        for name, value in attrition.items():
            if name == "manifest_missing" and isinstance(value, Mapping):
                # R5-G1: the per-lane drop mapping carries EXACTLY the four
                # ridge lanes — an arbitrary lane key is schema drift.
                if set(value) != set(RIDGE_LANE_NAMES):
                    raise QBValidationFailure(
                        "report_schema_invalid",
                        f"fold {row.get('test_season')}: manifest_missing lanes "
                        f"{sorted(map(str, value))} != registered ridge lanes "
                        f"{sorted(RIDGE_LANE_NAMES)}",
                    )
                bad = {k: v for k, v in value.items() if not _nonnegative_int(v)}
                if bad:
                    raise QBValidationFailure(
                        "report_schema_invalid",
                        f"fold {row.get('test_season')}: manifest_missing "
                        f"carries non-nonnegative counts {bad}",
                    )
            elif name == "manifest_missing":
                raise QBValidationFailure(
                    "report_schema_invalid",
                    f"fold {row.get('test_season')}: manifest_missing must be a "
                    f"per-ridge-lane mapping, got {value!r}",
                )
            elif not _nonnegative_int(value):
                raise QBValidationFailure(
                    "report_schema_invalid",
                    f"fold {row.get('test_season')}: attrition {name} must be "
                    f"a nonnegative int, got {value!r}",
                )
        if not isinstance(row.get("metrics_with_CIs"), Mapping):
            raise QBValidationFailure(
                "report_schema_invalid",
                f"fold {row.get('test_season')}: metrics_with_CIs mapping required",
            )
        flags = row.get("flags")
        if not isinstance(flags, list):
            raise QBValidationFailure(
                "report_schema_invalid",
                f"fold {row.get('test_season')}: flags list required",
            )
        unregistered = [flag for flag in flags if flag not in _FOLD_FLAG_VOCABULARY]
        if unregistered:
            # R3-G2: the fold-flag vocabulary is CLOSED — the registered
            # reason itself is the flag, never a composed prefix string.
            raise QBValidationFailure(
                "report_schema_invalid",
                f"fold {row.get('test_season')}: unregistered flags "
                f"{unregistered}; allowed {sorted(_FOLD_FLAG_VOCABULARY)}",
            )
    registered_contrasts = registration.get("contrasts")
    if not isinstance(registered_contrasts, list) or not registered_contrasts:
        raise QBValidationFailure(
            "registration_drift", "registration lacks its contrasts block"
        )
    # R6-G1-1 / R7-G1: the registered fold floors, below-floor status, and FDR
    # q are the registration's own §7/§9.2 law — absent means it drifted.
    fold_floors = registration.get("fold_floors") or {}
    h5_floor = fold_floors.get("h5_lane")
    below_floor_status = fold_floors.get("below_floor_status")
    # R9-G1: the per-fold evaluable-pool floor is the registration's own §7
    # law (fold_min_evaluable_n) — the producer refuses point statistics on a
    # starved fold, so the gate must bind the same floor to reconcile them.
    fold_min_evaluable_n = fold_floors.get("fold_min_evaluable_n")
    if (
        not _nonnegative_int(fold_floors.get("model_lane"))
        or not _nonnegative_int(h5_floor)
        or not _nonnegative_int(fold_min_evaluable_n)
        or not isinstance(below_floor_status, str)
        or not below_floor_status
    ):
        raise QBValidationFailure(
            "registration_drift",
            "registration lacks its fold_floors block (model_lane, h5_lane, "
            "fold_min_evaluable_n, below_floor_status)",
        )
    fdr_q = (registration.get("inference") or {}).get("fdr_q")
    if not _finite_number(fdr_q) or not 0.0 < fdr_q < 1.0:
        raise QBValidationFailure(
            "registration_drift",
            f"registration lacks a valid inference.fdr_q, got {fdr_q!r}",
        )
    comparisons = blocks.get("comparisons")
    if not isinstance(comparisons, list) or not comparisons:
        raise QBValidationFailure(
            "report_schema_invalid", "ok report needs comparison rows"
        )
    if [row.get("id") for row in comparisons] != [
        spec["id"] for spec in registered_contrasts
    ]:
        raise QBValidationFailure(
            "report_schema_invalid",
            f"comparison ids {[row.get('id') for row in comparisons]} != the "
            f"registered contrast set {[spec['id'] for spec in registered_contrasts]}",
        )
    for row, spec in zip(comparisons, registered_contrasts):
        missing = [field for field in _COMPARISON_REQUIRED_FIELDS if field not in row]
        if missing:
            raise QBValidationFailure(
                "report_schema_invalid",
                f"comparison {row.get('id')}: missing required fields {missing}",
            )
        if row.get("lane") != spec["lane"] or row.get("registered_direction") != spec[
            "direction"
        ]:
            raise QBValidationFailure(
                "report_schema_invalid",
                f"comparison {row.get('id')}: lane/direction "
                f"({row.get('lane')!r}, {row.get('registered_direction')!r}) != "
                f"registered ({spec['lane']!r}, {spec['direction']!r})",
            )
        vocabulary = (
            _H5_STATUS_VOCABULARY if spec["lane"] == "h5" else _MODEL_STATUS_VOCABULARY
        )
        if row.get("support_status") not in vocabulary:
            raise QBValidationFailure(
                "report_schema_invalid",
                f"comparison {row.get('id')}: support_status "
                f"{row.get('support_status')!r} outside the {spec['lane']} lane's "
                f"registered vocabulary",
            )
        if spec["lane"] == "h5":
            # §9.2 NI retention + R7-G1 produced status evidence: every H5 row
            # carries the retention pair, the one-sided bound, the BH-adjusted
            # NI probability, and the emitted flags list.
            absent = [
                field for field in _H5_COMPARISON_REQUIRED_FIELDS if field not in row
            ]
            if absent:
                raise QBValidationFailure(
                    "report_schema_invalid",
                    f"comparison {row.get('id')}: h5 status-evidence fields "
                    f"{absent} absent",
                )
        # R5-G1: the comparison numerics carry their REGISTERED domains, not
        # merely their key names — presence-only admitted -9 folds, string
        # intervals, and non-probability p values as ok.
        if not _nonnegative_int(row.get("evaluable_folds")):
            _refuse(
                f"comparison {row.get('id')}: evaluable_folds must be a "
                f"nonnegative int, got {row.get('evaluable_folds')!r}"
            )
        if not _finite_number_or_none(row.get("pooled_delta")):
            _refuse(
                f"comparison {row.get('id')}: pooled_delta must be a finite "
                f"number or None, got {row.get('pooled_delta')!r}"
            )
        if not _valid_ci95(row.get("ci95")):
            _refuse(
                f"comparison {row.get('id')}: ci95 must be [None, None] or two "
                f"finite ordered numbers, got {row.get('ci95')!r}"
            )
        if not _probability_or_none(row.get("p_perm")):
            _refuse(
                f"comparison {row.get('id')}: p_perm must be a probability or "
                f"None, got {row.get('p_perm')!r}"
            )
        if spec["lane"] == "h5":
            if not _probability_or_none(row.get("p_ni")):
                _refuse(
                    f"comparison {row.get('id')}: p_ni must be a probability "
                    f"or None, got {row.get('p_ni')!r}"
                )
            if not _bool_or_none(row.get("ni_met")):
                _refuse(
                    f"comparison {row.get('id')}: ni_met must be a boolean or "
                    f"None, got {row.get('ni_met')!r}"
                )
            if not _probability_or_none(row.get("adjusted_p_ni")):
                _refuse(
                    f"comparison {row.get('id')}: adjusted_p_ni must be a "
                    f"probability or None, got {row.get('adjusted_p_ni')!r}"
                )
            if not _finite_number_or_none(row.get("one_sided_lower_95")):
                _refuse(
                    f"comparison {row.get('id')}: one_sided_lower_95 must be "
                    f"finite or None, got {row.get('one_sided_lower_95')!r}"
                )
            if not isinstance(row.get("flags"), list):
                _refuse(
                    f"comparison {row.get('id')}: flags must be a list, got "
                    f"{row.get('flags')!r}"
                )
        if not _probability_or_none(row.get("adjusted_p")):
            _refuse(
                f"comparison {row.get('id')}: adjusted_p must be a probability "
                f"or None, got {row.get('adjusted_p')!r}"
            )
        excluded = row.get("excluded_folds")
        if excluded is not None:
            # The PRODUCED exclusion shape (measured from the composition):
            # each entry names its test_season and its reasons from the closed
            # registered fold-flag vocabulary.
            if not isinstance(excluded, list):
                # R22 (read 063f8453…): FIXED structural wording only — zero
                # access, formatting, repr, str, hashing, or type naming of
                # the refused container (a hostile __repr__ or metaclass
                # __name__ must never fire before the named refusal exists).
                # The row id is already validated against the registered
                # contrast set above, so its interpolation is safe.
                _refuse(
                    f"comparison {row.get('id')}: excluded_folds must be None "
                    f"or a list of exclusion rows"
                )
            seen_seasons = set()
            for entry in excluded:
                if (
                    not isinstance(entry, Mapping)
                    or not _nonnegative_int(entry.get("test_season"))
                    or not isinstance(entry.get("reasons"), (list, tuple))
                    or not entry["reasons"]
                    or any(
                        reason not in _FOLD_FLAG_VOCABULARY
                        for reason in entry["reasons"]
                    )
                ):
                    # R22 (read 063f8453…): FIXED structural wording only —
                    # zero derivation from the refused entry (see the
                    # container refusal above for the full rationale).
                    _refuse(
                        f"comparison {row.get('id')}: an exclusion row needs "
                        f"a mapping with a non-negative integer test_season "
                        f"and non-empty registered reasons"
                    )
                if entry["test_season"] in seen_seasons:
                    _refuse(
                        f"comparison {row.get('id')}: duplicate excluded "
                        f"test_season {entry['test_season']}"
                    )
                seen_seasons.add(entry["test_season"])
        # R7-G1: the shipped TOTAL status functions are the only status
        # authority. The gate reconstructs the canonical payload from the
        # row's own published evidence — exactly the production mapping in
        # ``contrast_status`` — invokes ``evaluate_power_and_status``, and
        # requires exact equality of the emitted status (and for H5 the
        # emitted ni_met and flags). The shipped function's own refusals
        # (impossible fold totals, non-probabilities, reversed or
        # sign-contradictory intervals) propagate under their honest names.
        status = row.get("support_status")
        ci_low, ci_high = row["ci95"][0], row["ci95"][1]
        if spec["lane"] != "h5":
            payload: dict[str, Any] = {"folds": row["evaluable_folds"]}
            if row.get("pooled_delta") is not None:
                payload["pooled_delta"] = row["pooled_delta"]
                if row["pooled_delta"] > 0:
                    payload["direction"] = "registered"
                elif row["pooled_delta"] < 0:
                    payload["direction"] = "wrong"
            if ci_low is not None and ci_high is not None:
                payload["ci_excludes_zero"] = bool(ci_low > 0 or ci_high < 0)
            if row.get("adjusted_p") is not None:
                payload["passes_fdr"] = bool(row["adjusted_p"] <= fdr_q)
            emitted = evaluate_power_and_status(payload)
            if status != emitted["support_status"]:
                _refuse(
                    f"comparison {row.get('id')}: published status {status!r} "
                    f"!= the shipped status function's "
                    f"{emitted['support_status']!r} for this row's own evidence"
                )
        else:
            numerics = (
                row.get("pooled_delta"),
                ci_low,
                ci_high,
                row.get("one_sided_lower_95"),
                row.get("p_ni"),
                row.get("adjusted_p_ni"),
            )
            if all(value is not None for value in numerics):
                emitted = evaluate_power_and_status(
                    {
                        "lane": "h5",
                        "folds": row["evaluable_folds"],
                        "pooled_delta": row["pooled_delta"],
                        "ci95": [ci_low, ci_high],
                        "one_sided_lower_95": row["one_sided_lower_95"],
                        "p_ni": row["p_ni"],
                        "adjusted_p_ni": row["adjusted_p_ni"],
                    }
                )
                if (
                    status != emitted["support_status"]
                    or row.get("ni_met") != emitted["ni_met"]
                    or list(row.get("flags") or []) != list(emitted.get("flags") or [])
                ):
                    _refuse(
                        f"comparison {row.get('id')}: published "
                        f"status/ni_met/flags ({status!r}, {row.get('ni_met')!r}, "
                        f"{row.get('flags')!r}) != the shipped H5 function's "
                        f"({emitted['support_status']!r}, {emitted['ni_met']!r}, "
                        f"{emitted.get('flags')!r})"
                    )
            elif all(value is None for value in numerics):
                # R8-G1: the one registered direct assignment
                # ``contrast_status`` makes is for WHOLLY unavailable numerics
                # below the floor — and its produced schema is exact: the
                # registered status, ``ni_met=False`` (the producer never
                # emits None here), and exactly the registered flag.
                if row["evaluable_folds"] >= h5_floor:
                    _refuse(
                        f"comparison {row.get('id')}: {row['evaluable_folds']} "
                        f"evaluable folds meet the registered floor {h5_floor} "
                        f"but status numerics are missing — incomplete "
                        f"evidence cannot carry a label"
                    )
                if (
                    status != below_floor_status
                    or row.get("ni_met") is not False
                    or list(row.get("flags") or [])
                    != ["registered_below_floor_rule"]
                ):
                    _refuse(
                        f"comparison {row.get('id')}: a below-floor row with "
                        f"wholly unavailable numerics must carry exactly "
                        f"({below_floor_status!r}, ni_met=False, "
                        f"['registered_below_floor_rule']), got ({status!r}, "
                        f"ni_met={row.get('ni_met')!r}, {row.get('flags')!r})"
                    )
            else:
                # R8-G1: partial H5 evidence is neither computable by the
                # shipped total function nor the honestly-unavailable special
                # case — it carries no status at any fold count.
                names = (
                    "pooled_delta",
                    "ci95_low",
                    "ci95_high",
                    "one_sided_lower_95",
                    "p_ni",
                    "adjusted_p_ni",
                )
                missing = [
                    name
                    for name, value in zip(names, numerics)
                    if value is None
                ]
                _refuse(
                    f"comparison {row.get('id')}: partial H5 evidence "
                    f"(missing {missing}) is neither complete for the shipped "
                    f"status function nor wholly unavailable — partial "
                    f"evidence cannot carry a status"
                )

    # R5-G1: per-fold metric coverage is bound to the registered contrast set —
    # every model contrast reports in every registered fold; H5 contrasts may
    # appear only in the registered H5 folds (a fold excluded by a registered
    # gate reports honestly rather than being forced); any key outside the
    # registered contrast ids is schema drift.
    model_ids = {spec["id"] for spec in registered_contrasts if spec["lane"] != "h5"}
    h5_ids = {spec["id"] for spec in registered_contrasts if spec["lane"] == "h5"}
    h5_seasons = set((registration.get("h5") or {}).get("folds") or [])
    for row in folds:
        season = row.get("test_season")
        metrics = row.get("metrics_with_CIs")
        supplied_ids = set(metrics)
        missing_model = model_ids - supplied_ids
        if missing_model:
            _refuse(
                f"fold {season}: metrics_with_CIs lacks registered model "
                f"contrasts {sorted(missing_model)}"
            )
        unregistered_ids = supplied_ids - model_ids - h5_ids
        if unregistered_ids:
            _refuse(
                f"fold {season}: metrics_with_CIs carries unregistered "
                f"contrast ids {sorted(map(str, unregistered_ids))}"
            )
        stray_h5 = (supplied_ids & h5_ids) - (h5_ids if season in h5_seasons else set())
        if stray_h5:
            _refuse(
                f"fold {season}: H5 contrasts {sorted(stray_h5)} reported "
                f"outside the registered H5 folds {sorted(h5_seasons)}"
            )
        for contrast_id, entry in metrics.items():
            if not isinstance(entry, Mapping):
                _refuse(
                    f"fold {season}: metrics_with_CIs[{contrast_id}] must be a "
                    f"mapping, got {entry!r}"
                )
            absent = [
                field for field in _FOLD_METRIC_REQUIRED_FIELDS if field not in entry
            ]
            if absent:
                _refuse(
                    f"fold {season}: metrics_with_CIs[{contrast_id}] lacks "
                    f"required fields {absent}"
                )
            if not _finite_number_or_none(entry.get("paired_delta")):
                _refuse(
                    f"fold {season}: metrics_with_CIs[{contrast_id}].paired_delta "
                    f"must be a finite number or None, got {entry.get('paired_delta')!r}"
                )
            for side in ("spearman_left", "spearman_right"):
                if not _correlation_or_none(entry.get(side)):
                    _refuse(
                        f"fold {season}: metrics_with_CIs[{contrast_id}].{side} "
                        f"must be a correlation in [-1, 1] or None, got "
                        f"{entry.get(side)!r}"
                    )
            if not _nonnegative_int(entry.get("common_pool_n")):
                _refuse(
                    f"fold {season}: metrics_with_CIs[{contrast_id}].common_pool_n "
                    f"must be a nonnegative int, got {entry.get('common_pool_n')!r}"
                )
            ci = entry.get("ci")
            # R6-G1-4: the per-fold CI object is CLOSED to its emitted contract
            # — CIs are registered at the pooled level only, and the entry
            # names exactly that state; an empty or reshaped mapping is drift.
            if (
                not isinstance(ci, Mapping)
                or set(ci) != {"state", "decision_supported"}
                or ci.get("state") != "pooled_level_only"
                or ci.get("decision_supported") is not False
            ):
                _refuse(
                    f"fold {season}: metrics_with_CIs[{contrast_id}].ci must be "
                    f'exactly {{"state": "pooled_level_only", '
                    f'"decision_supported": False}}, got {ci!r}'
                )

    # R9-G1: H5 per-fold evidence reconciliation — the gate IMPLEMENTS the
    # producer's admission invariant rather than approximating it. The
    # producer (comparisons: a starved fold nulls all three statistics;
    # otherwise paired_delta = spearman_left - spearman_right exactly when
    # both Spearmans exist, else None; inference._reconcile_fold refuses any
    # disagreement) admits a fold iff that reconciled delta is non-null. The
    # gate recomputes the producer-shaped EXPECTED delta from the entry's own
    # published support — non-null exactly when the common pool meets the
    # registered fold_min_evaluable_n floor and both Spearmans are present —
    # and requires the published paired_delta to EQUAL it, including
    # nullness. Key presence is never evidence, a positive pool below the
    # floor is never support, and a delta that does not equal the difference
    # of its own Spearmans is not a producible record.
    h5_evaluable: dict[str, set[int]] = {
        contrast_id: set() for contrast_id in h5_ids
    }
    for row in folds:
        season = row["test_season"]
        if season not in h5_seasons:
            continue
        present_here = set(row["metrics_with_CIs"]) & h5_ids
        for contrast_id in present_here:
            entry = row["metrics_with_CIs"][contrast_id]
            delta = entry.get("paired_delta")
            left = entry.get("spearman_left")
            right = entry.get("spearman_right")
            computable = (
                entry["common_pool_n"] >= fold_min_evaluable_n
                and left is not None
                and right is not None
            )
            expected_delta = left - right if computable else None
            if (delta is None) != (expected_delta is None) or (
                delta is not None and delta != expected_delta
            ):
                _refuse(
                    f"fold {season}: metrics_with_CIs[{contrast_id}]."
                    f"paired_delta {delta!r} != the producer-shaped expected "
                    f"delta {expected_delta!r} (spearman_left - spearman_right "
                    f"exactly when common_pool_n "
                    f"{entry['common_pool_n']} >= the registered "
                    f"fold_min_evaluable_n {fold_min_evaluable_n} and both "
                    f"Spearmans are present, otherwise None) — the producer "
                    f"cannot emit this record"
                )
            if expected_delta is not None:
                h5_evaluable[contrast_id].add(season)
        # R7-G2: PER-CONTRAST exclusion handling — ANY missing H5 contrast in
        # a registered H5 fold requires that fold to name its exclusion
        # through the closed registered flag vocabulary.
        if present_here != h5_ids and not row.get("flags"):
            _refuse(
                f"fold {season}: H5 contrasts "
                f"{sorted(h5_ids - present_here)} are absent from a registered "
                f"H5 fold that names no exclusion flag — omission without a "
                f"named exclusion is not admissible"
            )
    for row in comparisons:
        if row["id"] not in h5_ids:
            continue
        # R8-G2: EXACT two-sided reconciliation against derived content —
        # the claimed evaluable count must equal the mechanically derived
        # evaluable-season set, and the row's named exclusions must be
        # exactly that set's registered complement. Under-reporting is as
        # inadmissible as over-claiming.
        excluded_seasons = [
            entry["test_season"] for entry in (row.get("excluded_folds") or [])
        ]
        bad_excluded = [
            season for season in excluded_seasons if season not in h5_seasons
        ]
        if bad_excluded:
            _refuse(
                f"comparison {row['id']}: excluded_folds {bad_excluded} are "
                f"not registered H5 seasons {sorted(h5_seasons)}"
            )
        evaluable_seasons = h5_evaluable[row["id"]]
        if row["evaluable_folds"] != len(evaluable_seasons):
            _refuse(
                f"comparison {row['id']}: evaluable_folds "
                f"{row['evaluable_folds']} != the {len(evaluable_seasons)} "
                f"registered H5 folds whose emitted metric content is "
                f"mechanically evaluable {sorted(evaluable_seasons)}"
            )
        expected_excluded = h5_seasons - evaluable_seasons
        if set(excluded_seasons) != expected_excluded:
            _refuse(
                f"comparison {row['id']}: excluded_folds seasons "
                f"{sorted(excluded_seasons)} != the registered complement "
                f"{sorted(expected_excluded)} of its evaluable folds — every "
                f"non-contributing registered H5 fold names its exclusion, "
                f"and no contributing fold may be excluded"
            )

    case_panel = require_case_panel(blocks.get("case_panel") or [])
    registered_season_set = set(registered_seasons)
    for case_row in case_panel:
        absent = [
            field for field in _CASE_ROW_REQUIRED_FIELDS if field not in case_row
        ]
        if absent:
            # R5-G1: an id/scope_note shell is not a case result — every row
            # carries its produced player, fold, state, and lane readout.
            _refuse(f"case {case_row.get('id')}: missing produced fields {absent}")
        if case_row.get("state") not in _CASE_STATES:
            _refuse(
                f"case {case_row.get('id')}: state {case_row.get('state')!r} "
                f"outside {sorted(_CASE_STATES)}"
            )
        if case_row.get("fold") not in registered_season_set:
            _refuse(
                f"case {case_row.get('id')}: fold {case_row.get('fold')!r} is "
                f"not a registered test season"
            )
        # R6-G1-4: case identity is bound to a PRODUCED registered player —
        # blank identity fields cannot be a resolved case.
        for field in ("player_name", "gsis_id"):
            if not isinstance(case_row.get(field), str) or not case_row[field].strip():
                _refuse(
                    f"case {case_row.get('id')}: {field} must be a non-empty "
                    f"string, got {case_row.get(field)!r}"
                )
        lanes = case_row.get("lanes")
        if not isinstance(lanes, Mapping) or not lanes:
            _refuse(
                f"case {case_row.get('id')}: lanes must be a non-empty mapping, "
                f"got {lanes!r}"
            )
        # R6-G1-4 / R7-G4: lane keys come from the lanes the composition can
        # PRODUCE FOR THIS CASE'S FOLD — the h5 market lane exists only in the
        # registered H5 folds, so it can never appear on a case outside them.
        allowed_lanes = set(PRODUCED_LANE_NAMES)
        if case_row["fold"] not in h5_seasons:
            allowed_lanes.discard("h5")
        unknown_lanes = set(lanes) - allowed_lanes
        if unknown_lanes:
            _refuse(
                f"case {case_row.get('id')} (fold {case_row['fold']}): lanes "
                f"{sorted(map(str, unknown_lanes))} are not producible for this "
                f"fold — allowed {sorted(allowed_lanes)}"
            )
        any_reported = False
        for lane_name, lane_row in lanes.items():
            if not isinstance(lane_row, Mapping) or lane_row.get(
                "state"
            ) not in _CASE_LANE_STATES:
                _refuse(
                    f"case {case_row.get('id')}: lane {lane_name} must carry a "
                    f"state in {sorted(_CASE_LANE_STATES)}"
                )
            if lane_row.get("state") == "reported":
                any_reported = True
                for field in ("y_pred", "y_true"):
                    if not _finite_number(lane_row.get(field)):
                        _refuse(
                            f"case {case_row.get('id')}: lane {lane_name} "
                            f"reported without a finite {field}"
                        )
        # R6-G1-4: row/lane-state consistency — "reported" means at least one
        # lane reported; "not_in_evaluable_pool" means none did.
        if (case_row["state"] == "reported") != any_reported:
            _refuse(
                f"case {case_row.get('id')}: row state {case_row['state']!r} "
                f"inconsistent with its lane states "
                f"({'some' if any_reported else 'no'} lane reported)"
            )

    panels = blocks.get("sensitivity_panels")
    if not isinstance(panels, list) or [
        panel.get("id") for panel in panels
    ] != ["archetype_threshold", "qualifying_games", "h5_margin"]:
        raise QBValidationFailure(
            "report_schema_invalid",
            "sensitivity_panels must be exactly [archetype_threshold, "
            "qualifying_games, h5_margin]",
        )
    archetype, qualifying, h5_margin = panels
    require_threshold_sensitivity(archetype)
    validate_sensitivity_panel(
        {
            "unfiltered_primary": qualifying.get("unfiltered_primary"),
            "min_four_games": qualifying.get("min_four_games"),
            "h5_margin_sensitivity": {"margins": h5_margin.get("margins")},
        }
    )

    # R5-G1: the F13 panel carries COMPUTED result structures — a boolean or
    # None where the computed gate/moderator belongs is a placeholder, refused.
    gate = archetype.get("binary_dual_threat_gate")
    if not isinstance(gate, Mapping):
        _refuse(
            f"archetype_threshold.binary_dual_threat_gate must be the computed "
            f"result mapping, got {gate!r}"
        )
    # R6-G1-3: the gate is bound to the SHIPPED computation, not to shape —
    # the registered 400-yard threshold exactly, a rule that names it, and
    # arithmetic that could only come from a real partition of the pool.
    if not isinstance(gate.get("rule"), str) or str(
        DUAL_THREAT_RUSHING_YARDS
    ) not in gate["rule"]:
        _refuse(
            f"binary_dual_threat_gate.rule must name the shipped "
            f"{DUAL_THREAT_RUSHING_YARDS}-yard rule, got {gate.get('rule')!r}"
        )
    if gate.get("threshold_yards") != DUAL_THREAT_RUSHING_YARDS:
        _refuse(
            f"binary_dual_threat_gate.threshold_yards must be the shipped "
            f"{DUAL_THREAT_RUSHING_YARDS}, got {gate.get('threshold_yards')!r}"
        )
    gate_folds = gate.get("per_fold")
    if not isinstance(gate_folds, list) or not gate_folds:
        _refuse("binary_dual_threat_gate.per_fold must be a non-empty list")
    if [entry.get("test_season") for entry in gate_folds] != registered_seasons:
        _refuse(
            f"binary_dual_threat_gate.per_fold seasons "
            f"{[entry.get('test_season') for entry in gate_folds]} != registered "
            f"{registered_seasons}"
        )
    for entry in gate_folds:
        for field in (
            "n_evaluable",
            "dual_threat_count",
            "pocket_count",
            "boundary_case_count",
            "flips_at_minus_1_ypg",
            "flips_at_plus_1_ypg",
        ):
            if not _nonnegative_int(entry.get(field)):
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{entry.get('test_season')}]"
                    f".{field} must be a nonnegative int, got {entry.get(field)!r}"
                )
        season_label = entry.get("test_season")
        n_pool = entry["n_evaluable"]
        if entry["dual_threat_count"] + entry["pocket_count"] != n_pool:
            _refuse(
                f"binary_dual_threat_gate.per_fold[{season_label}]: dual "
                f"({entry['dual_threat_count']}) + pocket "
                f"({entry['pocket_count']}) != n_evaluable ({n_pool}) — this "
                f"cannot be the shipped partition of the evaluable pool"
            )
        boundary_cases = entry.get("boundary_cases")
        if not isinstance(boundary_cases, list):
            _refuse(
                f"binary_dual_threat_gate.per_fold[{season_label}]"
                f".boundary_cases must be a list"
            )
        if entry["boundary_case_count"] != len(boundary_cases):
            _refuse(
                f"binary_dual_threat_gate.per_fold[{season_label}]: "
                f"boundary_case_count {entry['boundary_case_count']} != "
                f"len(boundary_cases) {len(boundary_cases)}"
            )
        for field in (
            "boundary_case_count",
            "flips_at_minus_1_ypg",
            "flips_at_plus_1_ypg",
        ):
            if entry[field] > n_pool:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}].{field} "
                    f"({entry[field]}) exceeds the evaluable pool ({n_pool})"
                )
        # R7-G3: boundary rows are bound to the SHIPPED computation — the
        # trailing window, a positive-integer qualifying-game count, the
        # registered boundary relation, and gate/flip booleans RECOMPUTED
        # from the boundary seasons themselves.
        trailing_window = {
            season_label - offset
            for offset in range(1, ARCHETYPE_WINDOW_SEASONS + 1)
        }

        def _validated_window(
            rows: Any, owner: str, *, fold_label: Any = season_label
        ) -> dict[int, tuple[float, int]]:
            """Validate disclosed window rows and return {season: (yards, games)}.

            Shared by the per-player evidence rows and the boundary-case rows so
            the two disclosures are held to one standard. An empty list is the
            caller's decision to allow or refuse — this helper validates rows."""
            window_map: dict[int, tuple[float, int]] = {}
            for window_entry in rows:
                if (
                    not isinstance(window_entry, Mapping)
                    or not _nonnegative_int(window_entry.get("season"))
                    or not _finite_number(window_entry.get("rushing_yards"))
                    or not _nonnegative_int(window_entry.get("qualifying_games"))
                ):
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{fold_label}].{owner}: "
                        f"window season rows need season/rushing_yards/"
                        f"qualifying_games, got {window_entry!r}"
                    )
                window_season = window_entry["season"]
                if window_season not in trailing_window:
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{fold_label}].{owner}: "
                        f"window season {window_season} is outside the shipped "
                        f"trailing window {sorted(trailing_window)}"
                    )
                if window_season in window_map:
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{fold_label}].{owner}: "
                        f"duplicate window season {window_season} — one observed "
                        f"row per season, so a repeat can only inflate the "
                        f"derived classifications"
                    )
                window_map[window_season] = (
                    window_entry["rushing_yards"],
                    window_entry["qualifying_games"],
                )
            return window_map

        # R11 (full-evidence redesign — David's word, 2026-08-15): the fold
        # disclosure is TOTAL. One unique evidence row per evaluable player,
        # and EVERY fold total — dual/pocket partition, boundary membership,
        # flip totals — derives from those rows. R10-G1 established that
        # boundary rows alone cannot verify dual_threat_count/pocket_count;
        # with the whole pool disclosed, no caller total participates in F13
        # at all.
        evaluable_players = entry.get("evaluable_players")
        if not isinstance(evaluable_players, list):
            _refuse(
                f"binary_dual_threat_gate.per_fold[{season_label}] must "
                f"disclose evaluable_players — one evidence row per evaluable "
                f"player — as a list, got {evaluable_players!r}"
            )
        if len(evaluable_players) != n_pool:
            _refuse(
                f"binary_dual_threat_gate.per_fold[{season_label}]: "
                f"evaluable_players discloses {len(evaluable_players)} rows "
                f"for an evaluable pool of {n_pool} — the disclosure must "
                f"cover every evaluable player exactly once"
            )
        player_windows: dict[str, dict[int, tuple[float, int]]] = {}
        for player_entry in evaluable_players:
            if (
                not isinstance(player_entry, Mapping)
                or not isinstance(player_entry.get("player_id"), str)
                or not player_entry["player_id"].strip()
                or not isinstance(player_entry.get("window_seasons"), list)
            ):
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: an "
                    f"evaluable_players row needs a non-empty player_id and a "
                    f"window_seasons list, got {player_entry!r}"
                )
            evidence_pid = player_entry["player_id"]
            if evidence_pid in player_windows:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: "
                    f"duplicate evaluable player {evidence_pid!r} — one "
                    f"evidence row per player"
                )
            player_windows[evidence_pid] = _validated_window(
                player_entry["window_seasons"],
                f"evaluable_players[{evidence_pid}]",
            )
        derived_dual = 0
        derived_boundary_players: set[str] = set()
        derived_flips = {"flips_at_minus_1_ypg": 0, "flips_at_plus_1_ypg": 0}
        for evidence_pid, window_map in player_windows.items():
            base_any = any(
                yards > DUAL_THREAT_RUSHING_YARDS
                for yards, _games in window_map.values()
            )
            minus_any = any(
                yards > DUAL_THREAT_RUSHING_YARDS - games
                for yards, games in window_map.values()
            )
            plus_any = any(
                yards > DUAL_THREAT_RUSHING_YARDS + games
                for yards, games in window_map.values()
            )
            if base_any:
                derived_dual += 1
            if minus_any != base_any:
                derived_flips["flips_at_minus_1_ypg"] += 1
            if plus_any != base_any:
                derived_flips["flips_at_plus_1_ypg"] += 1
            if any(
                abs(yards - DUAL_THREAT_RUSHING_YARDS) <= games * 1.0
                for yards, games in window_map.values()
            ):
                derived_boundary_players.add(evidence_pid)
        if (
            entry["dual_threat_count"] != derived_dual
            or entry["pocket_count"] != n_pool - derived_dual
        ):
            _refuse(
                f"binary_dual_threat_gate.per_fold[{season_label}]: "
                f"dual_threat_count/pocket_count "
                f"({entry['dual_threat_count']}/{entry['pocket_count']}) != "
                f"the evidence-derived partition ({derived_dual}/"
                f"{n_pool - derived_dual}) over the disclosed evaluable "
                f"players — R10-G1: caller totals never substitute for "
                f"evidence"
            )
        for flip_field, derived_total in derived_flips.items():
            if entry[flip_field] != derived_total:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]."
                    f"{flip_field} ({entry[flip_field]}) != the "
                    f"evidence-derived flip total ({derived_total}) over the "
                    f"disclosed evaluable players"
                )
        flip_sums = {"flips_at_minus_1_ypg": 0, "flips_at_plus_1_ypg": 0}
        seen_boundary_players: set[str] = set()
        for case_entry in boundary_cases:
            if (
                not isinstance(case_entry, Mapping)
                or not isinstance(case_entry.get("player_id"), str)
                or not case_entry["player_id"].strip()
                or not isinstance(case_entry.get("binary_dual_threat"), bool)
                or not isinstance(case_entry.get("flips_at_minus_1_ypg"), bool)
                or not isinstance(case_entry.get("flips_at_plus_1_ypg"), bool)
                or not isinstance(case_entry.get("boundary_seasons"), list)
                or not case_entry["boundary_seasons"]
            ):
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: a "
                    f"boundary case must carry player_id, boolean gate/flip "
                    f"states, and non-empty boundary_seasons, got {case_entry!r}"
                )
            # R9-G2: the producer DISCLOSES its full observed trailing-window
            # evidence — every (season, rushing_yards, qualifying_games) row
            # the shipped classification read — replacing the R8-era trusted
            # window_high_season_count. With the rows themselves on the
            # record, the gate derives every classification, flip boolean,
            # and count from evidence, and a caller total has nothing left
            # to assert.
            player_id = case_entry["player_id"]
            if player_id in seen_boundary_players:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: "
                    f"duplicate boundary case for player {player_id!r} — the "
                    f"shipped producer emits at most one case per evaluable "
                    f"player, so a repeated row can only inflate aggregates"
                )
            seen_boundary_players.add(player_id)
            # R11: a boundary case is a VIEW over the fold's per-player
            # evidence, never a second evidence source — its player must be
            # a disclosed evaluable player and its window rows must EQUAL
            # that player's disclosed evidence exactly.
            if player_id not in player_windows:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: "
                    f"boundary case player {player_id!r} is absent from the "
                    f"disclosed evaluable_players — a case cannot cite "
                    f"evidence the pool disclosure does not carry"
                )
            window_rows = case_entry.get("window_seasons")
            if not isinstance(window_rows, list) or not window_rows:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: a "
                    f"boundary case must disclose window_seasons — its full "
                    f"observed trailing-window season rows — as a non-empty "
                    f"list, got {window_rows!r}"
                )
            window_by_season = _validated_window(
                window_rows, f"boundary_cases[{player_id}]"
            )
            if window_by_season != player_windows[player_id]:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: "
                    f"boundary case {player_id!r} window_seasons disagree "
                    f"with the player's disclosed evaluable_players evidence "
                    f"— one evidence source, no forked story"
                )
            base_any = False
            minus_any = False
            plus_any = False
            derived_band: dict[int, tuple[float, int]] = {}
            for window_season, (yards, games) in window_by_season.items():
                base_any = base_any or yards > DUAL_THREAT_RUSHING_YARDS
                minus_any = minus_any or yards > DUAL_THREAT_RUSHING_YARDS - games
                plus_any = plus_any or yards > DUAL_THREAT_RUSHING_YARDS + games
                if abs(yards - DUAL_THREAT_RUSHING_YARDS) <= games * 1.0:
                    derived_band[window_season] = (yards, games)
            boundary_by_season: dict[int, tuple[float, int]] = {}
            for season_entry in case_entry["boundary_seasons"]:
                if (
                    not isinstance(season_entry, Mapping)
                    or not _nonnegative_int(season_entry.get("season"))
                    or not _finite_number(season_entry.get("rushing_yards"))
                ):
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{season_label}]: "
                        f"boundary season rows need season/rushing_yards/"
                        f"qualifying_games, got {season_entry!r}"
                    )
                games = season_entry.get("qualifying_games")
                if not _nonnegative_int(games) or games < 1:
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{season_label}]: "
                        f"qualifying_games must be a positive integer, got "
                        f"{games!r} — a non-positive count cannot qualify a "
                        f"boundary season"
                    )
                if season_entry["season"] not in trailing_window:
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{season_label}]: "
                        f"boundary season {season_entry['season']} is outside "
                        f"the shipped trailing window {sorted(trailing_window)}"
                    )
                yards = season_entry["rushing_yards"]
                if abs(yards - DUAL_THREAT_RUSHING_YARDS) > games * 1.0:
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{season_label}]: "
                        f"{yards} rushing yards with {games} qualifying games "
                        f"violates the registered boundary relation "
                        f"abs(yards - {DUAL_THREAT_RUSHING_YARDS}) <= games"
                    )
                if season_entry["season"] in boundary_by_season:
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{season_label}]: "
                        f"duplicate boundary season {season_entry['season']}"
                    )
                boundary_by_season[season_entry["season"]] = (yards, games)
            # R9-G2: the boundary rows must be EXACTLY the boundary-band
            # subset of the disclosed window evidence — same seasons, same
            # yards, same games. A boundary row absent from the window rows
            # (or disagreeing with them) is fabricated evidence; a
            # band-satisfying window row missing from the boundary rows is a
            # concealed one.
            if boundary_by_season != derived_band:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: "
                    f"boundary_seasons {sorted(boundary_by_season)} != the "
                    f"boundary-band subset {sorted(derived_band)} of the "
                    f"disclosed window_seasons under the registered relation "
                    f"abs(yards - {DUAL_THREAT_RUSHING_YARDS}) <= games"
                )
            # R9-G2: EXACT recomputation, both directions, from the FULL
            # window evidence. Every classification and both flip booleans
            # are derived from the disclosed rows themselves — no caller
            # count participates — so equality is required: an impossible
            # asserted False is as inadmissible as an impossible asserted
            # True.
            expected_binary = base_any
            if case_entry["binary_dual_threat"] is not expected_binary:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]: "
                    f"binary_dual_threat {case_entry['binary_dual_threat']!r} "
                    f"!= the recomputed any-season rule ({expected_binary}) "
                    f"over its disclosed window seasons"
                )
            for flip_field, shifted_any in (
                ("flips_at_minus_1_ypg", minus_any),
                ("flips_at_plus_1_ypg", plus_any),
            ):
                expected_flip = shifted_any != expected_binary
                if case_entry[flip_field] is not expected_flip:
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{season_label}]: "
                        f"{flip_field}={case_entry[flip_field]!r} != the "
                        f"recomputed shifted-threshold flip {expected_flip} "
                        f"— flip booleans are exact in both directions"
                    )
                if case_entry[flip_field]:
                    flip_sums[flip_field] += 1
            for field in (
                "continuous_rush_yds_per_game_t_minus_1",
                "continuous_rush_att_per_game_t_minus_1",
            ):
                if field in case_entry and not _finite_number_or_none(
                    case_entry[field]
                ):
                    _refuse(
                        f"binary_dual_threat_gate.per_fold[{season_label}]: "
                        f"{field} must be finite or None"
                    )
        # R11: boundary MEMBERSHIP totality — the boundary cases must be
        # EXACTLY the disclosed evaluable players whose evidence carries a
        # band season. A concealed boundary player and a fabricated one are
        # both refusals, and with membership total the per-case recomputation
        # covers every player the band touches.
        if seen_boundary_players != derived_boundary_players:
            _refuse(
                f"binary_dual_threat_gate.per_fold[{season_label}]: "
                f"boundary_cases players {sorted(seen_boundary_players)} != "
                f"the evidence-derived boundary set "
                f"{sorted(derived_boundary_players)} — every disclosed "
                f"evaluable player with a band season is a boundary case, "
                f"and no other player is"
            )
        # R8-G3: aggregate totality — a player the shipped rule flips at
        # ±1 ypg necessarily has a boundary season (the flip's witness season
        # lies within ±games of the threshold), so every flipping player IS a
        # boundary case and the per-fold aggregate counts must EQUAL the sums
        # of the boundary-case flip booleans.
        for flip_field in ("flips_at_minus_1_ypg", "flips_at_plus_1_ypg"):
            if entry[flip_field] != flip_sums[flip_field]:
                _refuse(
                    f"binary_dual_threat_gate.per_fold[{season_label}]."
                    f"{flip_field} ({entry[flip_field]}) != the sum "
                    f"({flip_sums[flip_field]}) of its boundary-case flip "
                    f"booleans — every flip is a boundary case"
                )
    moderator = archetype.get("continuous_rushing_moderator")
    if (
        not isinstance(moderator, Mapping)
        or not isinstance(moderator.get("basis"), str)
        or "h2" not in moderator["basis"]
    ):
        # R6-G1-3: the moderator's basis is the REGISTERED h2 manifest — an
        # unrelated basis string is not the registered continuous construct.
        _refuse(
            f"archetype_threshold.continuous_rushing_moderator must name its "
            f"registered h2 manifest basis, got {moderator!r}"
        )
    if archetype.get("boundary_cases_yards_per_game") != [-1, 1]:
        _refuse(
            f"boundary_cases_yards_per_game must be exactly [-1, 1], got "
            f"{archetype.get('boundary_cases_yards_per_game')!r}"
        )

    # R5-G1: BOTH qualifying slices carry the full 14-contrast pooled readout.
    all_contrast_ids = {spec["id"] for spec in registered_contrasts}
    for slice_name in ("unfiltered_primary", "min_four_games"):
        slice_block = qualifying.get(slice_name)
        pooled = (
            slice_block.get("pooled_deltas")
            if isinstance(slice_block, Mapping)
            else None
        )
        if not isinstance(pooled, Mapping):
            _refuse(
                f"qualifying_games.{slice_name}.pooled_deltas mapping is "
                f"required, got {pooled!r}"
            )
        if set(pooled) != all_contrast_ids:
            _refuse(
                f"qualifying_games.{slice_name}.pooled_deltas ids "
                f"{sorted(map(str, pooled))} != the registered contrast set "
                f"{sorted(all_contrast_ids)}"
            )
        for contrast_id, entry in pooled.items():
            if not isinstance(entry, Mapping):
                _refuse(
                    f"qualifying_games.{slice_name}.pooled_deltas[{contrast_id}] "
                    f"must be a mapping, got {entry!r}"
                )
            if not _finite_number_or_none(entry.get("pooled_delta")):
                _refuse(
                    f"qualifying_games.{slice_name}.pooled_deltas[{contrast_id}]"
                    f".pooled_delta must be a finite number or None, got "
                    f"{entry.get('pooled_delta')!r}"
                )
            if not _nonnegative_int(entry.get("evaluable_folds")):
                _refuse(
                    f"qualifying_games.{slice_name}.pooled_deltas[{contrast_id}]"
                    f".evaluable_folds must be a nonnegative int, got "
                    f"{entry.get('evaluable_folds')!r}"
                )

    # R5-G1: the H5 margin panel carries its per-contrast readout for exactly
    # the four registered H5 contrasts; each present margin key is registered
    # and typed. (A contrast whose margin sensitivity could not be computed
    # reports an honest empty mapping rather than being forced.)
    registered_margins = list(
        (registration.get("h5") or {}).get("margin_sensitivity") or []
    )
    if h5_margin.get("margins") != registered_margins:
        _refuse(
            f"h5_margin.margins {h5_margin.get('margins')!r} != registered "
            f"{registered_margins!r}"
        )
    readout = h5_margin.get("readout")
    if not isinstance(readout, Mapping):
        _refuse(
            f"h5_margin.readout mapping is required, got {readout!r}"
        )
    if set(readout) != h5_ids:
        _refuse(
            f"h5_margin.readout ids {sorted(map(str, readout))} != the "
            f"registered H5 contrasts {sorted(h5_ids)}"
        )
    allowed_margin_keys = {str(margin) for margin in registered_margins}
    for contrast_id, margin_map in readout.items():
        if not isinstance(margin_map, Mapping):
            _refuse(
                f"h5_margin.readout[{contrast_id}] must be a mapping, got "
                f"{margin_map!r}"
            )
        # R6-G1-2 (Codex ruling, registration §9.2): ALL registered margins are
        # reported for EVERY H5 contrast regardless of outcome — an
        # uncomputable cell is present with honest null outputs, never absent.
        if set(margin_map) != allowed_margin_keys:
            _refuse(
                f"h5_margin.readout[{contrast_id}] margin keys "
                f"{sorted(map(str, margin_map))} != the registered set "
                f"{sorted(allowed_margin_keys)} — every registered margin cell "
                f"must be present (§9.2)"
            )
        for margin_key, leaf in margin_map.items():
            if not isinstance(leaf, Mapping):
                _refuse(
                    f"h5_margin.readout[{contrast_id}][{margin_key}] must be a "
                    f"mapping, got {leaf!r}"
                )
            # R7-G2: the leaf schema is CLOSED. A computed leaf carries all
            # three produced outputs; an unavailable leaf carries the named
            # state plus all three explicit nulls. An empty object is neither.
            keys = set(leaf)
            if keys == _MARGIN_LEAF_UNAVAILABLE_KEYS:
                if leaf.get("state") != "unavailable" or any(
                    leaf.get(field) is not None
                    for field in ("p_ni", "adjusted_p_ni", "ni_met")
                ):
                    _refuse(
                        f"h5_margin.readout[{contrast_id}][{margin_key}]: an "
                        f"unavailable leaf carries state='unavailable' and all "
                        f"three null outputs, got {dict(leaf)!r}"
                    )
            elif keys == _MARGIN_LEAF_COMPUTED_KEYS:
                if (
                    not _probability_or_none(leaf.get("p_ni"))
                    or leaf.get("p_ni") is None
                    or not _probability_or_none(leaf.get("adjusted_p_ni"))
                    or leaf.get("adjusted_p_ni") is None
                    or not isinstance(leaf.get("ni_met"), bool)
                ):
                    _refuse(
                        f"h5_margin.readout[{contrast_id}][{margin_key}]: a "
                        f"computed leaf carries probability p_ni/adjusted_p_ni "
                        f"and boolean ni_met, got {dict(leaf)!r}"
                    )
            else:
                _refuse(
                    f"h5_margin.readout[{contrast_id}][{margin_key}]: leaf keys "
                    f"{sorted(map(str, keys))} match neither the computed "
                    f"{sorted(_MARGIN_LEAF_COMPUTED_KEYS)} nor the unavailable "
                    f"{sorted(_MARGIN_LEAF_UNAVAILABLE_KEYS)} schema"
                )
            if leaf.get("decision_supported") is not False:
                _refuse(
                    f"h5_margin.readout[{contrast_id}][{margin_key}] lacks "
                    f"decision_supported=False"
                )


_CODE_REPO_ROOT = Path(__file__).resolve().parents[4]


def _failure_origin_sites(traceback: Any) -> list[dict[str, Any]]:
    """R19: the ordered in-repository traceback frames of a caught
    ``QBValidationFailure`` — outermost in-repository frame to the raise
    origin. Each site carries ONLY the repository-relative ``path``, the
    code-object ``function`` name, and a positive ``line``. No source text,
    expression, argument, local variable, or exception message enters the
    diagnostic: raw ``failure.detail`` can interpolate registered values and
    is process-local by law (registration read 86bace11…). Frames outside the
    repository (including ``.venv``) are omitted."""
    sites: list[dict[str, Any]] = []
    while traceback is not None:
        code = traceback.tb_frame.f_code
        try:
            relative = Path(code.co_filename).resolve().relative_to(_CODE_REPO_ROOT)
        except (OSError, ValueError):
            traceback = traceback.tb_next
            continue
        if not relative.parts or relative.parts[0] == ".venv":
            traceback = traceback.tb_next
            continue
        sites.append(
            {
                "path": relative.as_posix(),
                "function": code.co_name,
                "line": int(traceback.tb_lineno),
            }
        )
        traceback = traceback.tb_next
    return sites


def _notify_failure_observer(
    observer: Callable[[Mapping[str, Any]], None] | None,
    *,
    phase: str,
    failure: QBValidationFailure,
) -> None:
    """R19: hand the closed failure-origin diagnostic — ``{"phase", "sites"}``
    — to the optional in-memory observer, strictly AFTER the atomic artifact
    write. Observer absence, an empty in-repository tail, or an observer
    exception never affects the terminal report."""
    if observer is None:
        return
    try:
        sites = _failure_origin_sites(failure.__traceback__)
        if not sites:
            return
        observer({"phase": phase, "sites": sites})
    except Exception:
        return


def run_qb1_study(
    *,
    execute: Callable[[], Mapping[str, Any]],
    output_path: Path,
    registration_hash: str,
    generated_at: str,
    repo_root: Path,
    registration: Mapping[str, Any] | None = None,
    failure_observer: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """The named-failure runner: every invocation terminates in a VISIBLE atomic
    terminal artifact under the frozen root (green-review G3).

    R3-G1 ruling — the D5 registered schema is a RUNNER INVARIANT for every
    successful publication: an ok report can be published ONLY when the
    canonical ``registration`` object is supplied (its canonical hash must
    equal ``registration_hash``) and the report passes
    ``validate_registered_report_blocks`` against it. An ok payload arriving
    without the registration, or failing the registered schema, publishes as
    a named metric-free ``report_schema_invalid`` failed artifact — never as
    ``ok``. Failed publications need no registration by design.

    - A named ``QBValidationFailure`` from ``execute`` becomes an atomic failed
      report (no metric blocks), never a silent crash.
    - An ORDINARY exception (e.g. ``ValueError``) becomes a named metric-free
      ``execution_error`` failed report — it never escapes artifact-less.
      Process-control exceptions (``KeyboardInterrupt``, ``SystemExit``) are
      deliberately NOT caught.
    - A returned payload is never trusted: it is re-assembled through the
      closed D5 schema under the runner's OWN binding ``generated_at`` /
      ``registration_hash`` stamps (a payload carrying different stamps, an
      unknown key, or an invalid status refuses), then No-Verdict-validated
      (``validate_report_output``) BEFORE publication. A payload that fails
      either gate publishes as a named metric-free failed report — invalid
      evidence is never atomically blessed.

    REGISTERED GUARANTEE AND ITS BOUNDARY (David's ruling, 2026-08-16,
    resolving R11-G1-F13-SOURCE-TOTALITY): this runner and its publication
    gate guarantee INTERNAL COHERENCE plus CONFORMANCE TO THE FROZEN
    REGISTRATION — nothing more. Provenance grounding — that the published
    evidence is the evidence the producer actually read — is OUTSIDE this
    gate's scope, for every block equally: a validator whose only input is
    the report cannot notarize its own producer, and an internally
    consistent fabrication is undetectable here by construction. Source
    truth is owned by (a) the pinned admitted inputs
    (``admit_fetch_manifest`` and the frozen-hash checks), (b) the shipped
    composition code, and (c) the end-to-end contracts that exercise it.
    Adding a source-binding input to this gate, or citing this gate as a
    provenance guarantee, requires a new David ruling — see the boundary
    contracts in ``test_qb1_green_correction_contracts.py`` (R12).
    """

    def _publish_failed(reason: str) -> dict[str, Any]:
        report = assemble_terminal_report(
            generated_at=generated_at,
            registration_hash=registration_hash,
            run_status="failed",
            failure_reason=reason,
        )
        write_terminal_report_atomic(report, output_path, repo_root=repo_root)
        return report

    try:
        result = dict(execute())
    except QBValidationFailure as failure:
        # R19: artifact first, then the metric-free origin diagnostic — the
        # observer can never block or corrupt the atomic envelope. The
        # ordinary-Exception path below deliberately emits NO diagnostic.
        report = _publish_failed(failure.reason)
        _notify_failure_observer(failure_observer, phase="execute", failure=failure)
        return report
    except Exception:
        return _publish_failed("execution_error")

    try:
        unknown = set(result) - _TERMINAL_REPORT_KEYS
        if unknown:
            raise QBValidationFailure(
                "report_schema_invalid",
                f"payload carries unknown keys {sorted(map(str, unknown))}",
            )
        for stamp, binding in (
            ("schema_version", _REPORT_SCHEMA),
            ("generated_at", generated_at),
            ("registration_hash", registration_hash),
            # decision_supported=True is a No-Verdict violation and REFUSES —
            # it is never silently re-stamped to False (green-review G3).
            ("decision_supported", False),
        ):
            if stamp in result and result[stamp] != binding:
                raise QBValidationFailure(
                    "report_schema_invalid",
                    f"payload {stamp} {result[stamp]!r} != the runner's "
                    f"binding {binding!r}",
                )
        report = assemble_terminal_report(
            generated_at=generated_at,
            registration_hash=registration_hash,
            run_status=result.get("run_status", ""),
            failure_reason=result.get("failure_reason"),
            inputs=result.get("inputs"),
            folds=result.get("folds"),
            comparisons=result.get("comparisons"),
            case_panel=result.get("case_panel"),
            sensitivity_panels=result.get("sensitivity_panels"),
            disclosures=result.get("disclosures"),
        )
        validate_report_output(report)
        if report["run_status"] == "ok":
            # R3-G1: the registered-schema gate is unconditional at the
            # publication boundary — no registration object, no ok report.
            if registration is None:
                raise QBValidationFailure(
                    "report_schema_invalid",
                    "ok publication requires the canonical registration object "
                    "for the registered-schema gate",
                )
            require_registration_hash(registration, registration_hash)
            validate_registered_report_blocks(report, registration=registration)
    except QBValidationFailure as failure:
        published = _publish_failed(failure.reason)
        _notify_failure_observer(
            failure_observer, phase="publication_gate", failure=failure
        )
        return published

    write_terminal_report_atomic(report, output_path, repo_root=repo_root)
    return report
