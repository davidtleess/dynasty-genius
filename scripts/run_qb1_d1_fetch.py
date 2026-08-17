"""QB-1 D1 seven-dataset fetch — the one build pass David authorized 2026-08-14.

Authorization of record: David's word, verbatim: "run the seven fetches - authorized"
(2026-08-14, given directly in the Claude pane after the framing-v5 CLEAR at
qb1_execution_framing_review_codex_v5.md c3ead4ff). Scope is EXACTLY the framing-v5
operation table: seven literal current nflreadpy calls, raw snapshots written under the
frozen root BEFORE any parsing, per-dataset provenance with SHA-256. Nothing here parses,
filters, joins, or computes a study value — fetch is separated from downstream use by
contract.

Fail-loud: any error aborts the pass with no completion manifest; a partial tree without
`fetch_manifest.json` is deliberately non-admissible (the D1 gates read completeness, and
an incomplete fetch must never masquerade as substrate).

Registration: docs/validation/2026-07-21-qb-1-study-registration.md, binding pin 37065566…
(this script fetches inputs; it asserts nothing about the study and changes no registered
value). decision_supported=False is inherited by everything downstream.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW_ROOT = ROOT / "app" / "data" / "backtest" / "qb_validation" / "raw"
STUDY_SEASONS = list(range(2015, 2026))  # feature seasons 2015..2025 per the registration

AUTHORIZATION = {
    "word_verbatim": "run the seven fetches - authorized",
    "given_by": "David",
    # Honest bounded window (Codex D1-audit B1): the word arrived in the Claude pane
    # AFTER the framing-v5 CLEAR report (11:27 ET) and BEFORE fetch start (11:52:11 ET);
    # the exact submission instant was not independently captured.
    "given_at_local": "2026-08-14, between 11:27 ET and 11:52 ET (Claude pane, direct; exact instant not independently captured)",
    "framing": "qb1_execution_framing_claude_v5.md 1efa8760",
    "framing_clear": "qb1_execution_framing_review_codex_v5.md c3ead4ff",
}


def invalidate_completion_manifest(raw_root: Path) -> None:
    """W1 (Codex D1 audit): a rerun removes any stale completion receipt BEFORE the
    first provider write, so a partial rerun can never hide behind an old success."""
    (Path(raw_root) / "fetch_manifest.json").unlink(missing_ok=True)


def write_completion_manifest_atomic(
    manifest_path: Path,
    payload: dict,
    *,
    replace=None,
) -> None:
    """W1: the completion receipt is an atomic same-directory commit — temp sibling,
    validated as JSON, then replace. An interrupted write leaves no receipt."""
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp = manifest_path.with_name(manifest_path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    replace_fn = replace or (lambda source, target: source.replace(target))
    try:
        replace_fn(temp, manifest_path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot(frame, dataset: str, name: str) -> dict:
    directory = RAW_ROOT / dataset
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.parquet"
    frame.write_parquet(path)
    return {
        "file": str(path.relative_to(ROOT)),
        "rows": frame.height,
        "columns": frame.width,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def main() -> int:
    import nflreadpy as nfl

    invalidate_completion_manifest(RAW_ROOT)  # W1: stale success dies before any write
    started = datetime.now(timezone.utc).isoformat()
    datasets: dict[str, dict] = {}

    # 1. weekly — full weekly all-position player stats, 2015-2025
    frame = nfl.load_player_stats(seasons=STUDY_SEASONS, summary_level="week")
    datasets["weekly"] = {
        "call": "load_player_stats(seasons=2015..2025, summary_level='week')",
        "snapshots": [_snapshot(frame, "weekly", "weekly_2015_2025")],
    }
    print(f"weekly: {frame.height} rows", flush=True)

    # 2. season_summary — official REG season summaries (the pinned CPOE source)
    frame = nfl.load_player_stats(seasons=STUDY_SEASONS, summary_level="reg")
    datasets["season_summary"] = {
        "call": "load_player_stats(seasons=2015..2025, summary_level='reg')",
        "snapshots": [_snapshot(frame, "season_summary", "season_summary_2015_2025")],
    }
    print(f"season_summary: {frame.height} rows", flush=True)

    # 3. players — full player-attributes frame (H4 age source + §10 cross-check)
    frame = nfl.load_players()
    datasets["players"] = {
        "call": "load_players()",
        "snapshots": [_snapshot(frame, "players", "players_full")],
    }
    print(f"players: {frame.height} rows", flush=True)

    # 4. rosters — full seasonal roster frames, 2015-2025 (REG filter is downstream)
    frame = nfl.load_rosters(seasons=STUDY_SEASONS)
    datasets["rosters"] = {
        "call": "load_rosters(seasons=2015..2025)",
        "snapshots": [_snapshot(frame, "rosters", "rosters_2015_2025")],
    }
    print(f"rosters: {frame.height} rows", flush=True)

    # 5. ff_playerids — the current full crosswalk (fresh D1 envelope; the 2026-05-16
    #    pinned copy remains the separate §9.3 H5 join instrument)
    frame = nfl.load_ff_playerids()
    datasets["ff_playerids"] = {
        "call": "load_ff_playerids()",
        "snapshots": [_snapshot(frame, "ff_playerids", "ff_playerids_full")],
    }
    print(f"ff_playerids: {frame.height} rows", flush=True)

    # 6. draft_picks — the full drafted list (1980-2025 coverage filter is downstream)
    frame = nfl.load_draft_picks()
    datasets["draft_picks"] = {
        "call": "load_draft_picks()",
        "snapshots": [_snapshot(frame, "draft_picks", "draft_picks_full")],
    }
    print(f"draft_picks: {frame.height} rows", flush=True)

    # 7. pbp — THE DOMINANT CALL: full play-by-play per season (bounded memory; one raw
    #    snapshot per season so a mid-pass failure leaves an honest partial tree with no
    #    completion manifest)
    pbp_snapshots = []
    for season in STUDY_SEASONS:
        frame = nfl.load_pbp(seasons=[season])
        pbp_snapshots.append(_snapshot(frame, "pbp", f"pbp_{season}"))
        print(f"pbp {season}: {frame.height} rows", flush=True)
    datasets["pbp"] = {
        "call": "load_pbp(seasons=[s]) for s in 2015..2025 (per-season snapshots)",
        "snapshots": pbp_snapshots,
    }

    manifest = {
        "operation": "qb1_d1_seven_dataset_fetch",
        "authorization": AUTHORIZATION,
        "registration_pin": "37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d",
        "nflreadpy_version": getattr(nfl, "__version__", "unknown"),
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "datasets": datasets,
        "decision_supported": False,
    }
    manifest_path = RAW_ROOT / "fetch_manifest.json"
    write_completion_manifest_atomic(manifest_path, manifest)  # W1: atomic commit
    total_bytes = sum(
        snap["bytes"] for entry in datasets.values() for snap in entry["snapshots"]
    )
    print(
        f"COMPLETE: 7 datasets, {sum(len(e['snapshots']) for e in datasets.values())} "
        f"snapshots, {total_bytes:,} bytes, manifest {manifest_path.relative_to(ROOT)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
