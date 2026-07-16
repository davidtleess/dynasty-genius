# League snapshot scheduled capture — daily league-data freshness (F1)

**Date:** 2026-07-15
**Status:** DRAFT — awaiting cockpit CLEAR, then David authorization
**Authoring lane:** Claude spec · Codex RED · Gemini advisory
**Scope:** the league-data capture + derivation chain (snapshot → posture / value matrix / cut
report) and its publication contract. It is **not** the F4 on-surface age badge, the
freshness-skew guard at compositing consumers, or the 001b-N7 live-ownership read — each is a
named follow-up below.

## 1. Problem (measured, not inferred)

The Sleeper league snapshot — the source for rosters, ownership, postures, and every
cross-league artifact — has no scheduled owner. It was last captured June 23 by a hand run;
everything derived from it froze with it. David's directive (2026-07-15, via Studio 003,
verbatim): **"we have to have frequent refreshes of our league data."** This is the third
instance of the no-scheduled-owner defect class (Phase-0 margin artifact; 001b-N7 ownership
flag; now the league chain).

**Root cause:** two structural facts. (a) No launchd job captures the league —
`ops/launchd/` holds seven jobs covering market, model, features, what-changed, scoring, and
backup only. (b) The existing refresh pipeline overwrites **git-tracked** `*_latest`
artifacts in place — `scripts/run_league_intelligence_refresh.py:66-72` names them as its
backup/restore target set — so simply scheduling it daily would leave the working tree
permanently dirty (verified: `git ls-files` confirms the snapshot, posture, matrix, and
cut-report paths are all tracked).

**Reproduced (not asserted):**

```
$ ls ops/launchd/ | grep -ic "league\|snapshot"
1        # the one hit is dynasty-fc-snapshot — the FantasyCalc MARKET snapshot, not league

$ python3 - <<'EOF'  (captured_at of snapshot + derived chain)
sleeper_universe_snapshot_latest.json -> 2026-06-23T13:17:20.007866+00:00
team_posture_latest.json             -> 2026-06-23T13:17:30.931850+00:00
team_value_matrix_latest.json        -> 2026-06-23T13:17:30.723485+00:00
roster_cut_report_latest.json        -> 2026-06-23T13:17:30.083572+00:00
EOF
```

22 days stale at authoring; the derived chain sits 10 seconds behind the snapshot — one
sequential run, frozen together.

**Consequence today:** every league-facing surface answers from a June photograph — partner
postures, rosters through daily waivers, Trade Lab counterparty inputs — while `GET
/api/league/pulse` composites those June stamps beside same-day market data with no skew
signal. David is actively rebuilding; counterparty scouting is his weekly question.

## 2. Design

Extend the house **seed-split pattern** (third instance; precedents `.gitignore:85-89` —
`features_runtime/`, `valuation_runtime/`) to the league chain, with capture-and-accumulate
per the standing compounding preference (Codex boundary, cockpit-converged 2026-07-15).

**New producer:** `scripts/run_league_snapshot_capture.py` — one daily run that (1) captures
the Sleeper league state via the existing adapter layer, (2) executes the derivation chain
(posture, value matrix, cut report) against the fresh snapshot, and (3) publishes the whole
set atomically to the gitignored runtime prefix. Committed `*_latest` files remain as SEEDS —
untouched by the daily run, refreshed only by David-authorized data commits.

**Runtime layout (gitignored, backup-manifest-covered):**

```
app/data/league_runtime/
  runs/<run_id>/            # IMMUTABLE per-run capture: snapshot.json, coverage.json,
                            #   team_posture.json, team_value_matrix.json,
                            #   roster_cut_report.json, provenance.json
  ready_latest.json         # marker, written LAST after full-chain acceptance:
                            #   run_id · per-artifact sha256 digests · exact artifact set
                            #   (relative names within runs/<run_id>/ ONLY — any path
                            #   escaping that prefix rejects the marker) ·
                            #   source_captured_at = the wall-clock START instant of the
                            #   Sleeper HTTP fetch (ISO-8601 UTC, stamped immediately
                            #   before the request is issued; NOT build/derive time)
                            # UPDATE PROTOCOL: temp-file write + fsync + atomic os.rename —
                            #   a crash between write and rename leaves the PRIOR marker
                            #   intact, so the prior valid run keeps serving (never a forced
                            #   seed fallback from a torn writer)
  capture_status_latest.json  # terminal status marker (ok | failed:<named_reason>), every run
```

**Key signatures (injectable seams for a hermetic RED):**

```python
def run_capture(*, fetch_league_state, derive_chain, runtime_root: Path,
                clock, run_id: str) -> CaptureResult   # never touches tracked paths
def load_league_set(runtime_root: Path, seed_paths: SeedPaths) -> LeagueSet
    # resolves the marker-pinned run (digest-verified) or falls back to seeds
    # with caveat "league_snapshot_seed_fallback"; NEVER mixes runtime + seed members
```

**Atomicity law:** the marker names one complete run; consumers resolve exactly that set or
the seed set — a new snapshot is never composited with an old matrix. A failed/aborted run
writes the status marker with a named reason, leaves the last good run readable, and never
publishes a partial set.

**Fallback ladder (exact):** the marker is the ONLY acceptance record. (i) Valid marker →
serve its digest-verified run. (ii) Marker present but invalid (corrupt / traversal /
digest-mismatch / missing member) → **seeds directly**, named caveat — a run directory
without a valid acceptance record is never served, even if it looks complete (it may be an
unaccepted partial). (iii) Marker absent → seeds directly, named caveat. The "prior valid
run" rung exists only via the atomic-rename protocol (a failed publish leaves the PRIOR
VALID marker in place — that is still case (i), not a scan of `runs/`). The loader never
scans `runs/` to guess a servable run.

**Cadence & ordering:** daily (matches the pipeline and the league's daily waivers; season-
aware revisit is a follow-up). Slot proposal 09:20 local, but the contract is
**marker-not-clock**: downstream consumers gate on marker presence/freshness, never wall-clock
position (07-14 margin-race lesson). LaunchAgent install is David-gated and sequenced in §5.

**Same-change-set obligations:** `app/config/league_capture_config.json` (the F14 threshold
artifact — tracked, schema-versioned, with rationale); `.gitignore` entry; `app/config/backup_manifest.json` entry
for `league_runtime/runs/` (irreplaceable PIT — past rosters/postures cannot be re-fetched);
capture-health registration of `capture_status_latest.json`; **loader migration as contract**
— every direct reader of the four tracked `*_latest` paths is enumerated in **Appendix A**
(15 files, grep-verified 2026-07-15) and each consumer moves to `load_league_set`; the RED
mechanically bans survivors (F17); a hard-coded path that survives is a defect.

**Surface parity (standing order):** this is a backend contract cycle — closure requires
captures of every direct consuming renderer (League Pulse, Roster Audit, Trade Lab
counterparty inputs, **the What-Changed report surface, and the Roster Capacity simulator** —
the consumer graph per Appendix A) rendering the real runtime-fed payloads, nominal +
degraded (seed-fallback) states, desktop + mobile, before the cycle is called done.

## 3. Out of scope (named, not hidden)

- **F4 age badge on league modules** — visual surface; own slice through the design gates
  (shape-before-code, impeccable, unanchored audit). Copy law it inherits (Gemini framing,
  overclaim check): league data is labeled "snapshot as of <timestamp>" — never phrasing that
  implies a live connection to Sleeper.
- **Freshness-skew guard at compositing consumers** — consumer-side change over the new
  provenance fields; own spec (stale-source threshold 24h+2h ruled; pairwise threshold
  derived there).
- **001b-N7 live-ownership read** — complementary request-time fix, separately costed.
- **Season-aware cadence tuning** — daily now; in-season revisit named for the season
  checklist.
- **Retention/pruning of runs/** — accumulate now; any deletion is David-gated per the
  backup no-delete clause. Disk cost surfaces by name in the capture status if it grows.

## 4. Falsification seeds — the RED matrix

Test path: `tests/contract/test_league_snapshot_capture_red.py`. **Test-construction law:**
all seams injected (`tmp_path` runtime root, fake fetcher/deriver/clock); never assert the
live gitignored artifact; never hit the network.

| # | Seed (inputs/state) | Required behavior |
|---|---|---|
| F1 | Happy path: valid fetch + derivation | run dir written immutable; marker written LAST; digests match files; `source_captured_at` = fetch clock, not build clock |
| F2 | Derivation raises mid-chain | NO marker advance; no partial set under `runs/<id>/` acceptance; status marker `failed:<named>`; prior run still loadable |
| F3 | Marker present but a digest mismatches its file | `load_league_set` rejects the run, falls back to seeds WITH `league_snapshot_seed_fallback` caveat — never a silent mix |
| F4 | Marker absent (first boot) | seed fallback + caveat; no crash |
| F5 | Marker malformed JSON / missing fields / wrong types | fail closed, named reason; seed fallback |
| F6 | Marker names an artifact set with a member missing on disk | reject whole run; fallback; never partial resolution |
| F7 | Re-run with an existing `run_id` | REJECT with named reason `run_id_conflict`; the immutable prefix is never overwritten and no fresh id is silently minted |
| F8 | Fetcher returns empty rosters / malformed Sleeper payload | fail closed, no publish, named reason (`sleeper_payload_invalid:*`); payload validation runs BEFORE any derivation is attempted |
| F9 | Tracked-path isolation | a full successful run leaves `git status` of the four tracked seed paths byte-identical (probed via tmp repo fixture) |
| F10 | Mixed-vintage impossibility | loader output set's per-artifact `run_id`s are identical, always — constructed adversarial state (new snapshot + old matrix on disk) cannot surface |
| F11 | Ordering: invalid payload + a deriver that would also raise | payload validation is sequenced BEFORE derive — the recorded reason is `sleeper_payload_invalid:*`, never the deriver's error; distinct named reasons throughout, first failure recorded, not overwritten |
| F15 | Crash between marker temp-write and atomic rename (injected rename failure) | prior marker intact; prior valid run keeps serving; status marker records the failed publish with a named reason |
| F16 | Marker whose artifact set names a path escaping `runs/<run_id>/` (traversal, absolute path, `..`) or omits/adds a member vs the canonical set | marker rejected as a whole, named reason; **seeds directly** per the fallback ladder — a rejected marker leaves no discoverable acceptance record and the loader never scans `runs/` |
| F12 | Backup-manifest anti-rot | `league_runtime/runs` covered in `app/config/backup_manifest.json` (extends the existing anti-rot contract test's scope) |
| F13 | `decision_supported` untouched | derived posture/matrix/cut artifacts keep their existing descriptive flags recursively false; capture adds no verdict field |
| F14 | Structurally valid payload containing roster entries with unknown/unresolvable player ids (Gemini framing seed) | **CHOSEN CONTRACT: publish with disclosed unresolved counts** (per-artifact `unresolved_count` + row-level disclosure — the G4-2 morning-tape precedent), WITH the executable systemic floor: config `app/config/league_capture_config.json` (schema-versioned, carries `unresolved_threshold_bp` + rationale per the north-star threshold-provenance law), **default 500 bp (5%)**; denominator = distinct rostered player ids in the snapshot; comparison by integer cross-multiplication `unresolved_count * 10_000 >= unresolved_threshold_bp * total_rostered` — **`>=`: exactly AT the threshold fails closed** as `sleeper_identity_suspect` (fail-closed at the named suspicion point), one below publishes with disclosure. Boundary RED cases: 18/360 (= 500 bp exactly) → fail closed; 17/360 → publish with `unresolved_count=17`. Missing/malformed/wrong-type config → fail closed, named `league_capture_config_invalid` (never a silent hardcoded default) |
| F17 | Loader-migration anti-rot | a source scan over `app/` + `src/` + the non-producer scripts asserts NO reference to the four tracked `*_latest` league paths outside `load_league_set`, the seed definitions, and the Appendix-A producer chain — a surviving direct reader fails the suite |

## 5. Sequence (cockpit-TDD)

1. Cockpit CLEAR on this spec (Codex technical; Gemini advisory).
2. **David authorizes** the RED.
3. Codex authors the RED (F1–F17), demonstrably red on `main`.
4. Claude GREENs in a fresh worktree; focused suite + full gate (locked consumer surfaces
   are touched via the loader migration); self-probes the matrix.
5. Codex independent review → CLEAR; surface-parity captures per §2.
6. **David-authorized, each by name:** commit → PR → merge; first supervised real run;
   LaunchAgent install (separate word, per the Phase-0b precedent).

## 6. Risks

| Risk | Mitigation |
|---|---|
| Loader migration misses a hard-coded reader | enumerated grep list in the RED; survivor = defect, not follow-up |
| Runtime disk growth (daily ~8MB snapshot) | accumulate-by-design; size surfaced in status marker; pruning David-gated |
| Sleeper API shape drift breaks capture silently | F8 fail-closed + capture-health amber on stale marker (26h law) |
| Seed staleness misread as fresh after fallback | F3/F4 caveat is load-bearing; skew-guard follow-up adds the compositing signal |
| Wake-ordering race with 09:45 what-changed | marker-not-clock contract; the open wake-ordering guard spec covers the class |
| This spec proves capture, not consumer truth | surface-parity captures + the named F4/skew follow-ups; no "fresh" claim beyond the marker |

## Appendix A — direct readers of the tracked league `*_latest` paths (grep-verified 2026-07-15)

**Producer chain (stays path-aware by design; retargeted to the runtime prefix, not the loader):**
`scripts/run_league_intelligence_refresh.py` · `scripts/refresh_league_intelligence.py` ·
`scripts/build_team_posture.py` · `scripts/build_team_value_matrix.py` ·
`scripts/build_roster_cut_report.py` · `scripts/build_sleeper_universe_snapshot.py` (via
`src/dynasty_genius/sleeper_universe.py`)

**Consumers (migrate to `load_league_set`; F17 bans survivors):**
`app/api/routes/league_pulse.py:41,45` · `app/api/routes/trade.py:60` ·
`app/api/routes/trade_market.py:69` · `scripts/run_what_changed_report.py` ·
`scripts/run_roster_capacity_audit.py` · `scripts/build_league_opportunity_map.py` ·
`scripts/build_universe_pvo_batch.py` · `src/dynasty_genius/team_posture.py` ·
`src/dynasty_genius/team_value_matrix.py` (reader portions; their builder portions belong to
the producer chain above — the RED's scan distinguishes by call site, not file name)
