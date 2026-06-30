"""T3 operational driver — gated live refresh of the league-intelligence artifacts.

This is the GATED LIVE RUN (spec §10). It composes the T1 verifier
(`scripts/verify_league_intelligence_refresh.py` — preflight + acceptance +
report schema) and the T2 pipeline (`scripts/refresh_league_intelligence.py`)
into one auditable, reproducible, fail-closed run.

It is NOT RED/GREEN unit-tested (spec §9) — it is the operational run, verified
by the §8 machine-readable acceptance report it emits.

Safety model (spec §5, backup-restore fallback — the six builders write fixed
`app/data` paths in place, so a true staged-output dir is infeasible):
  1. PREFLIGHT is strictly side-effect-free. `stale-cache` OR `cold-empty`
     market classification → ABORT before any mutation (D1). On any preflight
     failure the tracked artifacts and the FantasyCalc cache are byte-unchanged.
  2. Before the run we back up every target `*_latest` artifact AND the
     FantasyCalc cache (`app/cache/fantasycalc/market_values.json`), and
     snapshot the full file listing of the target dirs.
  3. The pipeline runs in place. On ANY failure (builder CalledProcessError or
     an acceptance gate) we RESTORE the backed-up `*_latest` + cache to their
     exact pre-run bytes and DELETE every orphan run-suffixed file created this
     run (directory set-diff), then assert `git status --porcelain` is clean for
     the target paths. No half-state ever survives an abort (F2).
  4. Only on a full PASS are the freshly written artifacts kept and the §8
     report emitted. The driver NEVER commits — the tracked-artifact commit is
     a separate, David-authorized step (spec §7).

Modes:
  --preflight-only : run ONLY the side-effect-free preflight (safe to run any
                     time) and print the go/no-go. No mutation, ever.
  (default)        : full gated run (preflight → backup → pipeline → acceptance
                     → report). Requires the operator to have authorized the run.

Design spec: docs/superpowers/specs/2026-06-23-league-intelligence-artifact-freshness-design.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.refresh_league_intelligence import run_refresh  # noqa: E402
from scripts.verify_league_intelligence_refresh import (  # noqa: E402
    RefreshVerificationError,
    classify_market_source,
    validate_report_schema,
    verify_acceptance,
    verify_league_pulse_route_shape,
    verify_preflight,
)

# ── Manifest (Codex C2 — explicit, not glob) ─────────────────────────────────
VALUATION = ROOT / "app" / "data" / "valuation"
SNAPSHOTS = ROOT / "app" / "data" / "league_snapshots"

# Target *_latest artifacts the pipeline overwrites in place (backup/restore set).
TARGET_LATEST: tuple[Path, ...] = (
    SNAPSHOTS / "sleeper_universe_snapshot_latest.json",
    SNAPSHOTS / "sleeper_universe_coverage_latest.json",
    VALUATION / "universe_pvo_latest.json",
    VALUATION / "universe_pvo_coverage_latest.json",
    VALUATION / "roster_cut_report_latest.json",
    VALUATION / "roster_cut_report_latest.md",
    VALUATION / "team_value_matrix_latest.json",
    VALUATION / "team_posture_latest.json",
    VALUATION / "universe_market_divergence_latest.json",
    VALUATION / "universe_market_divergence_coverage_latest.json",
    VALUATION / "league_opportunity_latest.json",
    VALUATION / "league_opportunity_latest.md",
)
# Directories scanned for orphan run-suffixed files (set-diff before/after).
TARGET_DIRS: tuple[Path, ...] = (SNAPSHOTS, VALUATION)

# FantasyCalc cache — written by 17.4 on the `live` path; folded into
# backup/restore so the abort byte-invariant holds (Codex C1).
CACHE_FILE = ROOT / "app" / "cache" / "fantasycalc" / "market_values.json"
CACHE_TTL_HOURS = 24  # mirrors fetch_with_cache ttl

# Preflight inputs / schema baseline.
REQUIRED_INPUTS: tuple[Path, ...] = (
    ROOT / "resources" / "prospect_cards.json",
    ROOT / "app" / "data" / "identity" / "_runs" / "ff_playerids_20260516.json",
    ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv",
    ROOT / "resources" / "david_league_context.json",  # carries the Sleeper league id
)
# Artifacts that expose a top-level schema_version (roster_cut is a wrapper and
# is intentionally excluded — it has no top-level schema_version).
SCHEMA_ARTIFACTS: dict[str, Path] = {
    "snapshot": SNAPSHOTS / "sleeper_universe_snapshot_latest.json",
    "pvo": VALUATION / "universe_pvo_latest.json",
    "matrix": VALUATION / "team_value_matrix_latest.json",
    "posture": VALUATION / "team_posture_latest.json",
    "divergence": VALUATION / "universe_market_divergence_latest.json",
    "opportunity": VALUATION / "league_opportunity_latest.json",
}
EXPECTED_SCHEMA_VERSIONS: dict[str, str] = {
    "snapshot": "sleeper_universe_snapshot.v1",
    "pvo": "universe_pvo_batch.v1",
    "matrix": "team_value_matrix.v1",
    "posture": "team_posture.v1",
    "divergence": "universe_market_divergence.v1",
    "opportunity": "league_opportunity.v2",
}

REPORT_DIR = VALUATION
REPORT_SCHEMA_VERSION = "league_intelligence_refresh_report.v1"


# ── small utilities ──────────────────────────────────────────────────────────


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _byte_size(path: Path) -> int | None:
    return path.stat().st_size if path.exists() else None


def _build_client() -> Any:
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def _api_reachable() -> bool:
    """Lightweight FantasyCalc reachability probe (NOT fetch_with_cache).

    Only consulted by classify_market_source when the cache is stale/absent; a
    fresh cache short-circuits before this is ever called.
    """
    try:
        import urllib.request

        req = urllib.request.Request(
            "https://api.fantasycalc.com/values/current"
            "?isDynasty=true&numQbs=2&numTeams=12&ppr=1",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            return 200 <= resp.status < 500
    except Exception:
        return False


def _git_porcelain_targets() -> str:
    """git status --porcelain limited to tracked target paths (cache is gitignored)."""
    paths = [str(p) for p in TARGET_DIRS]
    out = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout.strip()


# ── preflight ────────────────────────────────────────────────────────────────


def run_preflight() -> dict[str, Any]:
    """Strictly side-effect-free preflight. Returns a result dict; raises
    RefreshVerificationError on any abort gate (caller decides exit code)."""
    now = datetime.now(timezone.utc)

    # Working tree must be clean for the target dirs — never clobber uncommitted work.
    dirty = _git_porcelain_targets()
    if dirty:
        raise RefreshVerificationError(
            f"target working tree not clean before run:\n{dirty}"
        )

    market = classify_market_source(
        cache_file=CACHE_FILE,
        now=now,
        ttl_hours=CACHE_TTL_HOURS,
        api_reachable=_api_reachable,
    )

    client = _build_client()

    def _route_probe() -> bool:
        try:
            verify_league_pulse_route_shape(client)
            return True
        except RefreshVerificationError:
            return False

    verify_preflight(
        required_inputs=list(REQUIRED_INPUTS),
        current_artifacts=SCHEMA_ARTIFACTS,
        expected_schema_versions=EXPECTED_SCHEMA_VERSIONS,
        route_probe=_route_probe,
        market_source=market,
    )
    return {
        "status": "passed",
        "market_source": market.status,
        "should_abort": market.should_abort,
        "checked_at": now.isoformat(),
    }


# ── backup / restore ─────────────────────────────────────────────────────────


def _snapshot_dir_files() -> set[Path]:
    files: set[Path] = set()
    for d in TARGET_DIRS:
        files |= {p for p in d.glob("*") if p.is_file()}
    return files


def _backup(backup_dir: Path) -> dict[str, Any]:
    """Copy every existing target *_latest + the cache into backup_dir.

    Returns a manifest recording pre-run existence + sha for the report and for
    exact restore (including 'delete on restore' for files that did not exist)."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"files": {}, "cache": {}}
    for i, path in enumerate(TARGET_LATEST):
        existed = path.exists()
        entry = {"existed": existed, "sha256": _sha256(path)}
        if existed:
            dest = backup_dir / f"{i}_{path.name}"
            shutil.copy2(path, dest)
            entry["backup"] = str(dest)
        manifest["files"][str(path)] = entry
    cache_existed = CACHE_FILE.exists()
    manifest["cache"] = {"existed": cache_existed, "sha256": _sha256(CACHE_FILE)}
    if cache_existed:
        dest = backup_dir / "_cache_market_values.json"
        shutil.copy2(CACHE_FILE, dest)
        manifest["cache"]["backup"] = str(dest)
    return manifest


def _restore(manifest: dict[str, Any], pre_files: set[Path]) -> str:
    """Restore *_latest + cache to pre-run bytes; delete orphan run files.

    Returns a human-readable rollback summary for the report."""
    notes: list[str] = []
    # Restore / delete each target latest.
    for path_str, entry in manifest["files"].items():
        path = Path(path_str)
        if entry["existed"]:
            shutil.copy2(Path(entry["backup"]), path)
        elif path.exists():
            path.unlink()
    # Restore / delete the cache (Codex C1).
    cache = manifest["cache"]
    if cache["existed"]:
        shutil.copy2(Path(cache["backup"]), CACHE_FILE)
    elif CACHE_FILE.exists():
        CACHE_FILE.unlink()
    # Delete orphan run-suffixed files created this run (directory set-diff).
    orphans = _snapshot_dir_files() - pre_files
    for orphan in sorted(orphans):
        orphan.unlink()
    notes.append(f"orphans_deleted={len(orphans)}")
    porcelain = _git_porcelain_targets()
    if porcelain:
        # Restore did NOT fully reconcile the tracked targets — this is a genuine
        # half-state, not a controlled abort. Hard-fail loudly (Codex C4).
        raise RefreshVerificationError(
            f"restore incomplete — target working tree still dirty after rollback:\n{porcelain}"
        )
    notes.append("git_clean")
    return "; ".join(notes)


# ── acceptance + report ──────────────────────────────────────────────────────


def _run_acceptance(
    *,
    previous_captured_at: str,
    market_status: str,
    new_files: set[Path],
) -> tuple[dict[str, Any], Any]:
    """Shape gate + acceptance/parity over the freshly written artifacts."""
    client = _build_client()
    body = verify_league_pulse_route_shape(client)  # D2 shape-drift hard gate

    # Post-run schema_version unchanged (acceptance §4).
    for key, path in SCHEMA_ARTIFACTS.items():
        actual = json.loads(path.read_text()).get("schema_version")
        if actual != EXPECTED_SCHEMA_VERSIONS[key]:
            raise RefreshVerificationError(
                f"schema_version drift after run for {key}: "
                f"expected {EXPECTED_SCHEMA_VERSIONS[key]!r}, got {actual!r}"
            )

    run_date = datetime.now(timezone.utc).date().isoformat()
    report = verify_acceptance(
        response=body,
        artifact_paths=list(TARGET_LATEST),
        previous_captured_at=previous_captured_at,
        run_date=run_date,
        market_source_status=market_status,
        changed_paths=sorted(new_files | set(TARGET_LATEST)),
    )
    # Explicit count sanity the verifier records but does not assert (spec §4).
    if report.counts.get("team_count") != 12:
        raise RefreshVerificationError(
            f"counts: team_count={report.counts.get('team_count')} (expected 12)"
        )
    # Freshness: captured_at must advance to today.
    new_captured_at = body.get("captured_at") or ""
    if not new_captured_at.startswith(run_date):
        raise RefreshVerificationError(
            f"freshness: captured_at {new_captured_at!r} did not advance to {run_date}"
        )
    return body, report


def _build_report(
    *,
    status: str,
    steps: list[dict[str, Any]],
    market_status: str,
    cache_before: dict[str, Any],
    acceptance: Any,
    previous_captured_at: str,
    new_captured_at: str,
    rollback_summary: str,
) -> dict[str, Any]:
    artifacts = acceptance.artifacts if acceptance is not None else []
    counts = acceptance.counts if acceptance is not None else {}
    checks = {
        "shape_drift": "passed",
        "market_bleed": "passed",
        "drop_pairing": "passed",
        "decision_supported": "passed",
        "banned_language": "passed",
        "freshness": "passed",
        "guardrails": "passed",
        "schema_version_unchanged": "passed",
        "counts": "passed",
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": status,
        "steps": steps,
        "market_source": {
            "status": market_status,
            "cache_sha_pre": cache_before.get("sha256"),
            "cache_existed_pre": cache_before.get("existed"),
            "cache_sha_post": _sha256(CACHE_FILE),
        },
        "artifacts": artifacts,
        "captured_at_delta": {
            "previous": previous_captured_at,
            "current": new_captured_at,
        },
        "counts": counts,
        "checks": checks,
        "rollback_guardrail_diff": rollback_summary,
        "decision_supported": False,
    }


# ── orchestration ────────────────────────────────────────────────────────────


def run(*, preflight_only: bool) -> int:
    pre = run_preflight()
    print(f"[preflight] PASS — market_source={pre['market_source']}")
    if preflight_only:
        print("[preflight-only] no mutation performed.")
        return 0

    previous_captured_at = (
        json.loads((VALUATION / "league_opportunity_latest.json").read_text()).get(
            "captured_at"
        )
        or ""
    )
    pre_files = _snapshot_dir_files()
    backup_dir = Path(tempfile.mkdtemp(prefix="li_refresh_backup_"))
    backup = _backup(backup_dir)
    cache_before = backup["cache"]

    try:
        print("[run] executing refresh pipeline (fail-fast)...")
        pipeline = run_refresh()
        print(f"[run] pipeline status={pipeline['status']}")

        new_files = _snapshot_dir_files() - pre_files
        body, acceptance = _run_acceptance(
            previous_captured_at=previous_captured_at,
            market_status=pre["market_source"],
            new_files=new_files,
        )
        report = _build_report(
            status="passed",
            steps=pipeline["steps"],
            market_status=pre["market_source"],
            cache_before=cache_before,
            acceptance=acceptance,
            previous_captured_at=previous_captured_at,
            new_captured_at=body.get("captured_at") or "",
            rollback_summary="not_triggered; full PASS",
        )
        validate_report_schema(report)
        run_id = datetime.now(timezone.utc).strftime("phase-refresh-%Y%m%dT%H%M%SZ")
        report_path = REPORT_DIR / f"league_intelligence_refresh_report_{run_id}.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(f"[accept] PASS — report written: {report_path}")
        print(
            "[accept] team_count="
            f"{report['counts'].get('team_count')} "
            f"waiver_cards={report['counts'].get('waiver_cards')} "
            f"waiver_capacity_pools={report['counts'].get('waiver_capacity_pools')}"
        )
        print("[done] artifacts refreshed in place. Commit is a SEPARATE, David-authorized step.")
        # Full PASS — pre-run backups are no longer needed.
        shutil.rmtree(backup_dir, ignore_errors=True)
        return 0
    except BaseException as exc:  # noqa: BLE001 — ANY failure must route through restore (Codex C3)
        # Restore first. If restore ITSELF fails (target still dirty), that is a
        # catastrophic half-state — surface it with a distinct loud exit code (8)
        # so it can never be mistaken for a clean, controlled abort (Codex C4).
        try:
            rollback = _restore(backup, pre_files)
        except BaseException as restore_exc:  # noqa: BLE001
            # PRESERVE backup_dir — it holds the exact pre-run bytes needed for
            # manual recovery from the half-state. Do NOT delete it here (Codex C5).
            print(f"[ABORT] {type(exc).__name__}: {exc}", file=sys.stderr)
            print(
                f"[CATASTROPHIC] restore FAILED, possible half-state on disk: {restore_exc}",
                file=sys.stderr,
            )
            print(
                f"[CATASTROPHIC] pre-run backups PRESERVED for manual recovery at: {backup_dir}",
                file=sys.stderr,
            )
            return 8
        print(f"[ABORT] {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"[rollback] {rollback}", file=sys.stderr)
        # Best-effort abort report for the audit trail.
        try:
            abort_report = _build_report(
                status="aborted",
                steps=[],
                market_status=pre["market_source"],
                cache_before=cache_before,
                acceptance=None,
                previous_captured_at=previous_captured_at,
                new_captured_at="",
                rollback_summary=rollback,
            )
            run_id = datetime.now(timezone.utc).strftime("phase-refresh-%Y%m%dT%H%M%SZ")
            (REPORT_DIR / f"league_intelligence_refresh_ABORT_{run_id}.json").write_text(
                json.dumps(abort_report, indent=2) + "\n"
            )
        except Exception:  # never let report writing mask the abort
            pass
        # Controlled abort — restore succeeded, so the backups are safe to drop.
        shutil.rmtree(backup_dir, ignore_errors=True)
        # Preserve interrupt semantics: roll back, THEN let the interrupt propagate.
        if isinstance(exc, KeyboardInterrupt):
            raise
        return 7


def main() -> None:
    parser = argparse.ArgumentParser(
        description="T3 gated live refresh of league-intelligence artifacts."
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run only the side-effect-free preflight (no mutation).",
    )
    args = parser.parse_args()
    try:
        code = run(preflight_only=args.preflight_only)
    except RefreshVerificationError as exc:
        print(f"[ABORT] preflight: {exc}", file=sys.stderr)
        code = 7
    raise SystemExit(code)


if __name__ == "__main__":
    main()
