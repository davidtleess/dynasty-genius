# QB-1 D1 seven-fetch substrate audit — Codex v1

Date: 2026-08-14  
Cycle: `TW14-QB1-1`  
Fetch manifest reviewed: `app/data/backtest/qb_validation/raw/fetch_manifest.json`  
Manifest SHA-256: `6223b9471c84f29950c50a43f500cdd577a4af63b1921df3da1fd04e6de85b28`  
Verdict: **NOT CLEAR — substrate bytes pass; one receipt BLOCKER, one runner WARN**

No provider call or study computation was performed by this audit. QB rushing
production (H2) remains **UNDER TEST** with no result.

## Binding substrate sweep

The reusable read-only audit is
`qb1_d1_substrate_audit_codex_v1.py`. It completed with status `passed`:

- exact dataset set and order: weekly, season summary, players, rosters,
  ff-playerids, draft picks, play-by-play;
- **17/17** declared Parquet snapshots exist, are regular files under the raw
  root, and have no undeclared/extra Parquet siblings;
- **17/17 SHA-256 values recomputed byte-exact**;
- exact total: **154,360,748 bytes**;
- every manifest row count, column count, and byte count reproduces;
- every snapshot carries every pinned source column required by the shipped
  validation adapter;
- weekly, season-summary, and roster coverage is exactly 2015–2025;
- every play-by-play snapshot carries exactly its filename season, 2015–2025;
- the draft-picks frame contains the complete admitted 1980–2025 range;
- the completion manifest is not older than any declared snapshot;
- registration pin, nflreadpy `0.1.5`, operation name, verbatim authorization
  text, increasing aware UTC fetch window, and recursive
  `decision_supported=False` root value are present;
- `app/data/backtest/qb_validation/raw` is gitignored and has the exact required
  directory entry in `backup_manifest.json`; anti-rot suite **5/5 passed**.

The fetched bytes and schemas are therefore sound for RED-time admission work.

## Findings

### QB-FETCH-B1 — BLOCKER — the authorization timestamp in the durable receipt is impossible

The manifest records `given_at_local` as `2026-08-14 ~11:0x ET`. The framing
CLEAR that made the fetch gate available was recorded at 11:27 ET, and the
manifest's own fetch window starts at 15:52:11Z (11:52:11 ET). David therefore
could not have given this post-CLEAR word at 11:0x. A durable authorization
receipt may not carry a knowingly impossible timestamp, even when the verbatim
word itself is correct.

**Required correction:** update both the manifest and the script's
`AUTHORIZATION` constant to the exact observed time if independently available;
otherwise use an honest bounded/unknown form such as “exact minute not captured;
after framing CLEAR at 11:27 ET and before fetch start at 11:52:11 ET.” Recompute
and publish the corrected manifest pin. Do not invent precision.

### QB-FETCH-W1 — WARN — reruns do not invalidate or atomically replace an existing completion marker

`run_qb1_d1_fetch.py` writes `fetch_manifest.json` last, but it neither removes
an existing completion manifest before the first provider write nor writes the
new manifest through a temporary file plus atomic replace. On a future
authorized rerun, a failed mid-pass attempt can leave the prior completion
marker in place while snapshot files have started changing. A downstream full
hash sweep should still reject changed bytes, but the script's stronger prose
claim—“a partial tree without fetch_manifest.json is deliberately
non-admissible”—does not hold on rerun.

**Disposition:** this does not invalidate the verified first-run bytes. Pin the
rerun law in RED and fix GREEN: invalidate the old completion marker before any
snapshot write, then emit the new manifest atomically only after the full tree
passes its own census/hash checks.

## Not a finding: completion receipt versus §11 admission envelope

The manifest is not yet itself a `load_validation_sources` state envelope: it
does not carry parsed frames or the exact per-dataset `status` / metadata shape
(`raw_snapshot_path`, `source_timestamp`, `parser_version`, `completeness`).
Claude disclosed this as the intended RED/GREEN boundary. RED will pin an
adapter that verifies this real receipt and tree, builds the seven admissible
states, and refuses any absent/malformed/hash-drifted/partial tree by name.

## Gate posture

RED freezing waits only on QB-FETCH-B1's receipt correction. No refetch is
required. QB-FETCH-W1 is non-blocking for the current substrate and becomes a
RED/Green hardening contract.

