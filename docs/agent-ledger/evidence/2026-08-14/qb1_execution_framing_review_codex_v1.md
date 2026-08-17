# QB-1 execution framing v1 — independent challenge (Codex v1)

Date: 2026-08-14
Work item: `TW14-QB1-1`
Reviewed artifact: `docs/agent-ledger/evidence/2026-08-14/qb1_execution_framing_claude_v1.md`
Reviewed SHA-256: `b29823a7b8122c2bb889b80d0d0e8e564c84e83b96207595b90f7c276cf7fbf7`
Verdict: **NOT CLEAR — four BLOCKERs, two WARNs**

This review covers execution mechanics only. It does not reopen a registered value, execute the
study, or make a result claim. QB rushing production (H2) remains **UNDER TEST** until the
pre-registered study is executed and David rules on the registered result.

## Independent checks

1. Read framing v1 and the full ratified registration, including Addendum A.
2. Reproduced the registration binding exactly: the file is 11,009 raw bytes with one terminal
   newline and raw SHA-256 `eb56943a17549f268894128a9f4a7b9fe421d542bae9538f5781d9f667b13782`;
   parsing then canonicalizing with shipped `build_registration` produces 11,008 bytes and the
   binding SHA-256 `37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d`.
3. Verified all four `/var/tmp/dp-values/values_*.csv` files by byte count and SHA-256; all match
   §9.1 exactly.
4. Counted 14 modules under `src/dynasty_genius/eval/qb_validation/`.
5. Ran the principal contract suite: **120 passed, 9 xfailed**. The nine strict parked seams are
   F10, F13, F16, F18, F25, F29, F31, F32, and F33.
6. Verified `status.py` still refuses every H5 payload as `h5_status_not_implemented`.
7. Drove the proposed machine-output path through the shipped F24 guard:
   `app/data/validation_runs/qb1/run.json` refuses as `output_path_violation`; the registered
   `app/data/backtest/qb_validation/run.json` path passes and is gitignored.
8. Verified the registered D1 raw-snapshot directory is absent/empty locally. All seven default
   validation loaders call `nflreadpy` when no fixture/injected loader is supplied.
9. Verified the local DP store contains the expected 2,185 rows across four dates, but its schema
   carries Sleeper ID/value/position and no DP raw name or FantasyPros ID.
10. Verified each pinned DP values file carries `fp_id` and `player`, but no Sleeper or GSIS ID.
    The registered D1 ff-playerids field set is exactly `gsis_id`, `sleeper_id`, `name`.

## Findings

### QB-R1-B1 — BLOCKER — Q3 chooses an output path forbidden by the frozen F24/D5 contract

Framing v1 proposes machine artifacts under `app/data/validation_runs/qb1/`. The frozen spec,
shipped `OUTPUT_ROOT`, F24 guard, F31 ignore rule, and D5 output law all require machine artifacts
under `app/data/backtest/qb_validation/` only. The proposed path fails today with the named
`output_path_violation`.

**Required ruling:** Q3 must use a run-scoped child of
`app/data/backtest/qb_validation/` for every machine artifact, including terminal failure
artifacts. A tracked `docs/validation/` readout is a separate publication derived from one
completed, validated terminal artifact; it is not the runner's output root and must not be
written on a failed or partial run. Changing F24 is a registered-value/spec change and is out of
scope for this execution cycle.

### QB-R1-B2 — BLOCKER — the readiness inventory and RED seed set omit executable work that is still deliberately parked

The tree is not missing only an orchestrator and a standalone-file bridge. The direct contract
suite reports **9 strict XFAILs**:

- D4: F16 duplicate/conflict semantics, F18 coverage gate, F32 name reconciliation;
- D5: F10 case panel, F13 threshold sensitivity, F25 frozen-boundary assertion, F29 sensitivity
  panel, F31 artifact tracking;
- boundary: F33 consumer-wall tripwire.

Separately, `evaluate_power_and_status` explicitly refuses H5 with
`h5_status_not_implemented`. There is also no D5 `qb_validation_report.v1` assembler/terminal
writer. Those are required for an executable study, not optional hardening after a runner exists.

**Required correction:** framing v2 must enumerate the complete GREEN scope and map every parked
seam plus H5 status and the end-to-end terminal writer/orchestrator to a RED family. The RED must
pin, at minimum: H5's total status precedence and both `ci_p_disagreement` directions; the F10/
F13/F25/F29/F31 report surfaces; F33's consumer wall; every invocation writing one terminal
artifact; failures carrying no metrics; and no partial/interim artifact being publishable as a
result. The existing strict-XFAIL rows must be unparked in the same reviewed change that builds
their seams.

### QB-R1-B3 — BLOCKER — “no provider contact” contradicts the registered fresh-D1 build and the current local substrate

QB-1 is registered to build a fresh matrix from seven D1 datasets. No registered raw snapshots
exist under `app/data/backtest/qb_validation/raw/` in this worktree. With no injected source
bundle, every default validation loader imports and calls `nflreadpy`. The four local H5 files and
the 2,185-row DP store solve only the H5 market substrate; they do not supply weekly stats,
season summaries, players, rosters, ff-playerids, draft picks, or play-by-play.

**Required correction:** framing v2 must choose and pin one honest route before RED:

- enumerate an existing local, immutable seven-dataset bundle and its injected-loader/provenance
  route, then verify the §11 presence gates; or
- disclose that execution requires provider-backed `nflreadpy` reads and establish that this is
  inside David's execution authority.

Silent substitution from the legacy QB store is barred by D2a. “No provider contact because the
four H5 files are local” is therefore false for the whole study as currently framed.

### QB-R1-B4 — BLOCKER — Q1 does not identify a computable, independently checkable H5 identity key

The four pinned values files contain `fp_id` and `player`, but no Sleeper or GSIS ID. The registered
D1 crosswalk contract admits `gsis_id`, `sleeper_id`, and `name`, but not `fantasypros_id`. The
local DP store has Sleeper IDs but drops both the raw name and FantasyPros ID, so it cannot by
itself bind a stored row back to the raw name needed for F32. Joining the raw values files to the
D1 crosswalk by normalized name would make the subsequent name-reconciliation gate tautological
rather than independent.

**Required correction:** Q1 must name the primary identifier path, every input it consumes, and
why F32 remains an independent check. Plausible routes have different authority consequences:
using `fantasypros_id` requires reconciling it with the frozen D1/source-registry allowed fields;
adding historical `db_playerids.csv` snapshots exceeds the four-file input declaration; using the
existing store requires a provable raw-to-store binding that its current schema does not carry.
The framing may not choose among those silently. Until one route is shown computable and
authorized, “exactly four pinned files” is not enough to implement the registered static join.

### QB-R1-W1 — WARN — Q2 needs an exact governed path and narrower commit language

The durable copy should land under the already governed/gitignored study root, with its exact
path and backup-manifest entry pinned together. “Repo commit stays prohibited” is overbroad:
the four GPL source files remain untracked and uncommitted; code, tests, the manifest entry, and a
human-gated readout still use the normal gate-path commit. The framing should say that plainly.

### QB-R1-W2 — WARN — the registration-hash RED needs a positive canonical-file case

The newline fact is real, but the seed should not merely say raw hashing is rejected. Pin the
observable contract: parsing the real newline-terminated file and canonicalizing it **passes**;
changing any object value fails the initial gate as `preregistration_missing`; drift after the pin
is established fails separately as `registration_drift`. That distinguishes a correct semantic
object gate from a runner that simply refuses the real file because it hashed raw bytes.

## Positions on Q1–Q4

- **Q1:** not ruled; BLOCKED by QB-R1-B4 until the primary identity route is explicit and
  independently reconcilable.
- **Q2:** adopt durable copy + manifest together, conditional on an exact path under
  `app/data/backtest/qb_validation/` and the narrower untracked-source wording in W1.
- **Q3:** rule differently per QB-R1-B1: machine artifacts stay under the frozen F24 root;
  `docs/validation/` is a separate, terminal-success publication surface.
- **Q4:** sequencing is correct. The scorer cycle is presently staged at its human commit gate,
  so no QB autonomy run or RED round opens yet. Codex retains RED authorship once that commit
  lands and the scorer run is cleanly closed.

## Gate posture

No QB run was initialized; the active scorer run remains authoritative. No study execution,
provider contact, data copy, manifest edit, model result, commit, push, or grounding build was
performed. H2 remains **UNDER TEST** with no result.
