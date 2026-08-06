"""F-feature-refresh — CLI for the source-hash-gated feature refresh runner.

Thin, cwd-independent wrapper over the runner. `--preflight` is a readiness-only
check (no assemble, no write, no runtime-dir creation); the full run regenerates a
CANDIDATE only (publish/scheduler are T2/T4) via the shared feature builder, gated on
the source content hash (honest `noop` when the upstream source is unchanged).

This script derives features only — it never trains or writes model artifacts.

    .venv/bin/python3.14 scripts/run_feature_refresh.py --preflight
    .venv/bin/python3.14 scripts/run_feature_refresh.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# cwd-independent: put the repo root on sys.path BEFORE importing the package, so a
# standalone/launchd invocation from outside the repo does not crash on import.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.features.feature_assembly import (  # noqa: E402
    assemble_feature_candidate,
)
from src.dynasty_genius.features.feature_publish import (  # noqa: E402
    publish_runtime,
)
from src.dynasty_genius.features.feature_refresh_runner import (  # noqa: E402
    compute_source_hash,
    run_feature_refresh,
)
from src.dynasty_genius.nflverse_usage import (  # noqa: E402
    load_nextgen_from_export,
    nextgen_export_provenance,
)

_DEFAULT_RUNTIME_DIR = ROOT / "app" / "data" / "features_runtime"
_DEFAULT_SEED = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
_LOCK_NAME = "feature_refresh.lock"
# Integrity floors for the scheduled publish: a non-empty candidate with all four
# positions present in the inference season. The validation gate does the rest.
_MIN_TOTAL_ROWS = 4
_MIN_POSITION_ROWS = {"QB": 1, "RB": 1, "WR": 1, "TE": 1}


_STREAM_LOADERS = (
    ("player_stats", "load_player_stats", None),
    ("rosters", "load_rosters", None),
    ("snap_counts", "load_snap_counts", None),
    ("pbp", "load_pbp", None),
    ("participation", "load_participation", 2019),
)


def _load_stream_isolated(nfl, attr: str, seasons: list[int]):
    """Load ONE stream, stepping its OWN season ceiling down once on failure.

    CH1. The five frames were built in a single dict literal, so ANY loader raising
    aborted the whole function and `_resolve_default_source` then stepped the ENTIRE
    window down for ALL FIVE. Measured cost: `player_stats` 2026 404s while `rosters`
    2026 returns real rows, so 2,930 valid current-season roster rows were discarded
    every morning while the run reported `ok`.

    Both failure modes are isolated here, because they are different exception types
    from different causes: `ConnectionError` is a missing upstream parquet, and
    `ValueError` is the installed client refusing a season outside its own bounds.
    `_resolve_default_source` caught only the former, so the latter would have crashed
    the run outright once an earlier loader started succeeding.

    Returns (frame, provenance). A stream that cannot load at ANY season in its window
    is `unavailable` with an EMPTY frame — it never caps a healthy stream. A stream that
    loads and legitimately returns no rows is `loaded_empty`, which is a different fact
    and is kept distinct so an empty frame cannot be mistaken for an absent one.
    """
    import pandas as pd

    load = getattr(nfl, attr)
    error_type: str | None = None
    attempts_made = 0
    # Candidate windows are DEDUPLICATED and empties dropped, so a single-season
    # window yields exactly ONE attempt. F2: `fallback_used` must record a retry
    # that actually happened, not one the loop merely intended — with `[2026]` the
    # second candidate is empty, no second call occurs, and reporting a fallback
    # would be a false statement about acquisition.
    candidates: list[list[int]] = []
    for window in (seasons, seasons[:-1]):
        if window and window not in candidates:
            candidates.append(list(window))
    for window in candidates:
        attempts_made += 1
        try:
            frame = _pd_frame(load(seasons=list(window)))
        except (ConnectionError, ValueError) as exc:
            error_type = type(exc).__name__
            continue
        # F1: `effective_season` is an OBSERVED fact about returned rows, never the
        # requested ceiling. A provider asked for 2024-2026 that returns only through
        # 2025 must not be reported as 2026, and a successful EMPTY frame has no
        # effective season at all — reporting one would assert coverage that does not
        # exist, which is the same false-source-state class as the original defect.
        seasons_present = None
        if len(frame) and "season" in frame:
            non_null = frame["season"].dropna()
            if len(non_null):
                seasons_present = int(non_null.astype(int).max())
        status = "loaded" if seasons_present is not None else "loaded_empty"
        return frame, {
            "status": status,
            "effective_season": seasons_present,
            "fallback_used": attempts_made > 1,
            # F4: the TRIGGERING error is preserved when a fallback succeeds — that is
            # the contract, and it is what tells a reader why the season stepped back.
            # (An earlier comment here claimed the opposite of what this line does.)
            "error_type": error_type if attempts_made > 1 else None,
        }
    return pd.DataFrame(), {
        "status": "unavailable",
        "effective_season": None,
        "fallback_used": attempts_made > 1,
        "error_type": error_type,
    }


def _pd_frame(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _load_source(seasons_window: list[int] | None) -> dict:
    """Lazily load the full upstream source frame set (nflreadpy) for the shared builder.

    Loads every frame `build_engine_b_features` consumes so the regenerated candidate is
    fully scoreable. Participation is only available from 2019 on, so it is scoped to the
    in-window seasons >= 2019. The real invocation is David-gated (T3 catch-up run).
    """
    import nflreadpy as nfl  # lazy: keep standalone import light + optional

    window = list(seasons_window or [])
    ng_seasons = [s for s in window if s >= 2016]
    sources: dict = {}
    provenance: dict = {}
    for name, attr, floor in _STREAM_LOADERS:
        stream_window = [s for s in window if floor is None or s >= floor]
        sources[name], provenance[name] = _load_stream_isolated(nfl, attr, stream_window)
    # F3: refuse when ANY of the five is still unavailable after its bounded attempts.
    # A schema-less empty frame is NOT a safe substitute for a required stream: the real
    # builder immediately groups rosters on gsis_id/season and snaps on
    # pfr_player_id/season and indexes PBP/participation columns, so an unavailable
    # stream reaches it as a KeyError rather than a controlled report. Codex withdrew its
    # own original rc=0 expectation here as vacuous against production — the fake runner
    # in RED-v1 hid the real builder's column access.
    # `loaded_empty` is NOT unavailable and still proceeds to normal downstream validation.
    unavailable = sorted(n for n, pv in provenance.items() if pv["status"] == "unavailable")
    if unavailable:
        raise _StreamsUnavailable(unavailable)
    sources["__stream_provenance__"] = provenance
    # NGS comes from the LAST-GOOD LOCAL EXPORT, not from three live calls inside
    # the 09:15 scheduled chain (David's word 2026-07-31, Codex sequencing step 3,
    # on Gemini's explicit RELINQUISH of this file). Three network round-trips in
    # the critical path were three new ways the morning halts, with no cached
    # fallback despite the registry declaring failure_behavior="use_cached".
    # Absence returns {} and the NGS columns are simply not merged — the
    # downstream per-position features are optional-if-present by contract.
    sources.update(load_nextgen_from_export(ng_seasons))
    return sources


class _StreamsUnavailable(RuntimeError):
    """One or more provider streams could not load at any season in their window."""

    def __init__(self, streams: list[str]) -> None:
        self.streams = streams
        super().__init__(
            "refusing to publish: source stream(s) unavailable after bounded "
            "retry — " + ", ".join(streams)
        )


def _resolve_default_source(season_start: int, ceiling: int) -> tuple[dict, int]:
    """Bounded-probe source load for the arg-less (dynamic) default window.

    The discovery ceiling is the current CALENDAR year, which in the offseason names a season
    whose upstream parquet does not exist yet — nflreadpy 404s (ConnectionError) on the missing
    file before any derivation can run. So attempt the full window through `ceiling`, and on a
    source-load ConnectionError step the ceiling DOWN exactly once and retry. If neither
    `ceiling` nor `ceiling - 1` loads, FAIL CLOSED (raise): a >1-year gap is a genuine upstream
    outage, never a fabricated season. Returns (read_fns, effective_end) for the season that
    actually loaded.
    """
    last_err: ConnectionError | None = None
    for end in (ceiling, ceiling - 1):
        if end < season_start:
            break
        try:
            return _load_source(list(range(season_start, end + 1))), end
        except ConnectionError as exc:  # missing upstream parquet (offseason) / transport
            last_err = exc
    raise ConnectionError(
        f"dynamic source probe found no loadable season at {ceiling} or {ceiling - 1} "
        f"(upstream likely unavailable): {last_err}"
    )


def _package_version() -> str | None:
    """nflreadpy version if resolvable (part of the C4 source hash); None otherwise."""
    try:
        from importlib.metadata import version

        return version("nflreadpy")
    except Exception:
        return None


def _builder_config() -> dict:
    """Builder constants that change the candidate -> part of the C4 source hash.

    Any change to these thresholds alters the produced candidate, so they must be in the
    source hash or an identical-frame run would falsely noop after a constant change.
    """
    from scripts.assemble_engine_b_dataset import MIN_GAMES_THRESHOLD
    from src.dynasty_genius.models.engine_b_contract import (
        DUAL_THREAT_RUSHING_THRESHOLD,
    )

    return {
        "MIN_GAMES_THRESHOLD": MIN_GAMES_THRESHOLD,
        "DUAL_THREAT_RUSHING_THRESHOLD": DUAL_THREAT_RUSHING_THRESHOLD,
    }


def _te_artifact_hashes() -> dict:
    """Content hashes of the TE rubric/eligible artifacts the builder reads from disk.

    `build_engine_b_features` falls back to reading these committed artifacts when the
    frames lack `te_rubric`/`te_eligible`, so their bytes are a genuine source input (C4):
    changing them changes the candidate and MUST change the source hash (no false noop).
    """
    from scripts.assemble_engine_b_dataset import (
        TE_ARCHETYPE_RUBRIC_PATH,
        TE_ELIGIBLE_MANIFEST_PATH,
    )

    out: dict[str, str | None] = {}
    for label, path in (
        ("te_archetype_rubric", TE_ARCHETYPE_RUBRIC_PATH),
        ("te_eligible_manifest", TE_ELIGIBLE_MANIFEST_PATH),
    ):
        p = Path(path)
        out[label] = (
            hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        )
    return out


def _source_provenance(read_fns: dict, seasons_window: list[int]) -> dict:
    """Full C4 source-hash input set the CLI feeds to `compute_source_hash`.

    Covers every input the builder consumes that can change the candidate: the loader
    frames, the seasons window, the nflreadpy package version (if resolvable), the builder
    constants, and the on-disk TE rubric/eligible artifact byte-hashes. Wall-clock is
    intentionally excluded (C5 — the runner strips `generated_at`).
    """
    return {
        "loader_outputs": {
            k: v for k, v in read_fns.items() if k != "__stream_provenance__"
        },
        "stream_provenance": read_fns.get("__stream_provenance__", {}),
        "seasons_window": seasons_window,
        "package_version": _package_version(),
        "builder_config": _builder_config(),
        "te_rubric_artifacts": _te_artifact_hashes(),
        "identity_inputs": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate the engine_b feature candidate (source-hash-gated)."
    )
    parser.add_argument("--runtime-dir", default=str(_DEFAULT_RUNTIME_DIR))
    parser.add_argument("--seed-path", default=str(_DEFAULT_SEED))
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="readiness-only check; never assembles, writes, or creates the runtime dir",
    )
    parser.add_argument("--season-start", type=int, default=2018)
    parser.add_argument(
        "--season-end",
        type=int,
        default=None,
        help="inference/latest season; default None -> Option B dynamic derivation: the max "
        "season actually present in loaded player_stats (avoids defaulting into an unplayed "
        "calendar year, and auto-advances when real new-season data lands).",
    )
    args = parser.parse_args(argv)

    if args.preflight:
        ready = bool(args.seed_path) and Path(args.seed_path).exists()
        print(f"preflight ready={ready} seed_path={args.seed_path}")
        return 0 if ready else 1

    # Serialize on a lock BEFORE any source load, so a still-running scheduled refresh is
    # never doubled (which could corrupt the atomic publish). Refuse fast and cheaply —
    # no nflreadpy load — if a prior run is (or appears) in progress.
    runtime_dir = Path(args.runtime_dir)
    lock_path = runtime_dir / _LOCK_NAME
    if lock_path.exists():
        print(
            f"refusing to run: {lock_path} present — a prior feature refresh may be in "
            f"progress (locked). Remove the lock if no run is active."
        )
        return 1
    runtime_dir.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("locked by scripts/run_feature_refresh.py\n")
    try:
        # Full run: load source, hash content, then validate + ATOMICALLY PUBLISH the
        # runtime (source-hash-gated; honest noop when the source is unchanged). NO commit,
        # no model write — the runtime lands under the gitignored features_runtime/ dir.
        # Option B — dynamic latest-available season via a BOUNDED PROBE. With --season-end
        # UNSET, anchor the discovery ceiling on the current calendar year, but tolerate the
        # offseason gap where that year's upstream data does not exist yet: load the window
        # through the ceiling, and on a source 404 step down ONCE (and FAIL CLOSED beyond,
        # never fabricate). Then derive season_end = the max season actually present in
        # player_stats. So the daily arg-less scheduler resolves to the latest PLAYED season
        # (e.g. 2025 in the offseason), never an unplayed calendar year, never crashes on the
        # missing-parquet 404, and auto-advances the moment real new-season data lands. An
        # explicit --season-end overrides (back-compat). T4's inference-scoped publish gate
        # still catches a degraded latest season, so this fixes the offseason block (and the
        # post-kickoff September edge) without masking a broken feed.
        if args.season_end is None:
            ceiling = datetime.now(timezone.utc).year
            try:
                read_fns, discovery_end = _resolve_default_source(args.season_start, ceiling)
            except _StreamsUnavailable as exc:
                print(str(exc))
                return 1  # before any hash or publish
            except ConnectionError as exc:
                print(f"refusing to publish: {exc}")
                return 1  # lock released by the enclosing finally; no hash/publish attempted
            ps = read_fns["player_stats"]
            season_end = (
                int(ps["season"].max())
                if (len(ps) and "season" in ps and ps["season"].notna().any())
                else discovery_end  # loaded-but-empty -> fail-closed downstream, never fabricate
            )
        else:
            season_end = args.season_end
            try:
                read_fns = _load_source(list(range(args.season_start, season_end + 1)))
            except _StreamsUnavailable as exc:
                print(str(exc))
                return 1  # before any hash or publish

        seasons_window = list(range(args.season_start, season_end + 1))
        source_hash = compute_source_hash(**_source_provenance(read_fns, seasons_window))
        # CH1: the provenance rides ALONGSIDE the frames, never as one of them — the
        # builder must keep receiving exactly the loader frames it always received.
        stream_provenance = read_fns.pop("__stream_provenance__", {})
        inference_season = season_end

        def publish_fn(candidate_path, **kwargs):
            return publish_runtime(
                candidate_path,
                inference_season=inference_season,
                min_total_rows=_MIN_TOTAL_ROWS,
                min_position_rows=_MIN_POSITION_ROWS,
                **kwargs,
            )

        result = run_feature_refresh(
            runtime_dir=args.runtime_dir,
            seed_path=args.seed_path,
            now_fn=lambda: datetime.now(timezone.utc),
            read_fns=read_fns,
            source_inputs={
                "source_hash": source_hash,
                "seasons_window": seasons_window,
                "stream_provenance": stream_provenance,
                # Which NGS export vintage this build consumed — or that none was
                # available, and why. Absence is legitimate; a build that silently
                # produced NGS-free features with no stated cause is not. Recorded
                # beside the hash rather than inside it: the export's frames are
                # already part of `loader_outputs`, so a changed vintage already
                # changes the source hash on its own.
                "nextgen_export": nextgen_export_provenance(),
            },
            assemble_fn=assemble_feature_candidate,
            publish_fn=publish_fn,
        )
        status = result.get("status")

        # NGS provenance sidecar. It belongs as a FIELD in the refresh report, but
        # the report is written by `feature_refresh_runner.py`, which persists only
        # `source_hash` and `seasons_window` from `source_inputs` and is NOT a file
        # this lane owns. Written beside the runtime rather than dropped: a build
        # that consumed no NGS must say so with a reason, and one that did must name
        # the exact export vintage. Folding it into the report is a one-line change
        # in the runner and needs that file's handoff.
        try:
            (Path(args.runtime_dir) / "nextgen_export_provenance.json").write_text(
                json.dumps(
                    {"status": status, **nextgen_export_provenance()},
                    indent=1, sort_keys=True, default=str,
                ) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass  # never fail a good refresh over a provenance sidecar

        print(status)
        # Unattended-scheduler alertability: ok/noop are healthy (exit 0); a blocked
        # publish (validation/write failure) or any other status is a real failure the
        # launchd run must surface as nonzero.
        return 0 if status in {"ok", "noop"} else 1
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
