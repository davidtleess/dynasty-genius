#!/usr/bin/env node

/**
 * Open the conditionally authorized QB-1 season-summary aggregate Round 17.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_season_summary_aggregate_round17_open_codex_v1.mjs --apply
 */

import { createHash } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";

import {
  loadRun,
  persistRun,
} from "/Users/davidleess/dg-cockpit/autonomy/core/lib/run-state.mjs";

const STATE_PATH =
  "/Users/davidleess/dynasty-genius/.git/worktrees/dynasty-genius-product/dg-autonomy/run.json";
const ROUND_ROOT = join(dirname(STATE_PATH), "snapshots", "green-review-17");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 103;
const EXPECTED_SCOPE_HASH =
  "225761eeeb7d334e16dab11a8ef2449c38e8743b868a9c9dc5aa8dfb18728688";
const CENSUS_SCRIPT_SHA256 =
  "6b1321cbba0701037b37e470060d8ad4a86265bfae2d48395e0f93969df0f96e";
const CENSUS_OUTPUT_SHA256 =
  "a8cfb6c6561502fda3e2adffe873f32a3ee03b6c43143e31543d891ab5d5fcd4";
const REGISTRATION_READ_SHA256 =
  "4dda5d2ba9dd3a202d38047adadd8fc94f0159eea7f293c569ef25514b4f3211";
const DAVID_WORD =
  "open the continuation from blocked revision 102 per your sanctioned mechanism - claude runs one read-only identity census across all seven admitted datasets in one pass (results discarded unread, no repairs), you do the registration read of the measured facts, claude then implements one bounded round per your read if the walls are the same placeholder class, fresh rerun only on your explicit clear - the registered readout comes back to me for my ruling";
const REPAIR_ID = "TW16-QB1-SEASON-SUMMARY-AGGREGATE-R17-OPEN-CODEX-V1";

const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/study_matrix.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/study_matrix.py",
    "518e4b82c79d6a9637ae5bca5b6eb0aba7b82afc212ce1d01b7fe8a69d50e389",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "7407dc6c46237d7c3a23e3f3db044f56583db5d553c793fead9486684aab36c9",
  ],
]);

const EVIDENCE_PINS = new Map([
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_seven_dataset_identity_census_claude_v1.py",
    CENSUS_SCRIPT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_seven_dataset_identity_census_claude_v1_output.txt",
    CENSUS_OUTPUT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_season_summary_aggregate_registration_read_codex_v1.md",
    REGISTRATION_READ_SHA256,
  ],
]);

function fail(message) {
  throw new Error(`season-summary Round-17 open refused: ${message}`);
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function requireRegularFile(path, label) {
  if (!existsSync(path) || !lstatSync(path).isFile()) {
    fail(`${label} is not a regular file: ${path}`);
  }
}

function scopedSnapshotHash(root, scope) {
  const hash = createHash("sha256");
  for (const relativePath of [...scope].sort()) {
    hash.update(`${relativePath}\0`);
    try {
      hash.update(readFileSync(resolve(root, relativePath)));
    } catch {
      hash.update("<absent>");
    }
    hash.update("\0");
  }
  return hash.digest("hex");
}

function takeScopedSnapshot(worktree) {
  if (existsSync(ROUND_ROOT)) fail(`snapshot directory already exists: ${ROUND_ROOT}`);
  for (const relativePath of SCOPE) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, relativePath);
    const target = join(ROUND_OPEN, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedSnapshotHash(ROUND_OPEN, SCOPE);
}

function validatePinnedRun(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id is ${run.id ?? "missing"}`);
  if (run.schemaVersion !== 3) fail(`schemaVersion is ${run.schemaVersion ?? "missing"}`);
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision is ${run.revision ?? "missing"}, expected ${EXPECTED_REVISION}`);
  }
  if (run.phase !== "verifying" || run.terminalState !== null) {
    fail(`state is ${run.phase}/${run.terminalState}, expected verifying/null`);
  }
  if (run.failureCounts?.["green-review:real-surface-qa"] !== 3) {
    fail(`real-surface failure history changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") fail("prior Judge STOP record changed");
  const green = (run.reviewRounds ?? []).filter((round) => round.phase === "green-review");
  if (
    green.length !== 16 ||
    green.some((round, offset) => round.index !== offset + 1 || !round.closedAt)
  ) {
    fail("expected exactly sixteen closed green-review rounds indexed 1..16");
  }
  if (green.at(-1)?.reviewerVerdict !== "CLEAR") fail("Round 16 is not closed CLEAR");
  if (
    run.stateRepairs?.at(-1)?.id !==
    "TW16-QB1-SEVEN-DATASET-IDENTITY-CENSUS-CONTINUATION-CODEX-V1"
  ) {
    fail("revision-103 diagnostic continuation record changed");
  }
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  for (const [relativePath, expectedHash] of EVIDENCE_PINS) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, SCOPE);
  if (currentScopeHash !== EXPECTED_SCOPE_HASH) {
    fail(`current scope hash ${currentScopeHash} != ${EXPECTED_SCOPE_HASH}`);
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-17 snapshot already exists");
}

function buildOpenRun(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 17,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...SCOPE],
    findings: [],
    churn: { openSnapshotHash },
    authorization: {
      authority: "David",
      word: DAVID_WORD,
      conditionalAuthoritySatisfied:
        "Census proves the same upstream provider non-player aggregate class; exact season-summary predicate differs because its registered consumer fields differ",
      boundedPurpose:
        "exclude exact provider non-player league aggregates from defensive season-summary records before stage-1b player validation",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: REGISTRATION_READ_SHA256,
      censusEvidence: {
        scriptSha256: CENSUS_SCRIPT_SHA256,
        outputSha256: CENSUS_OUTPUT_SHA256,
        measuredRows: 11,
        seasons: "2015-2025",
      },
      implementationBoundary: {
        files: [...SCOPE],
        exactPredicate:
          "missing player_id AND valid registered study season AND missing position AND null passing_cpoe AND exact validated integral games >= 256",
        names: "audit evidence only",
        placement:
          "defensive copied season_summary records after F1/F14/F15 and exact season coverage, immediately before stage-1b identity/duplicate/CPOE validation",
        poolAndFrameUntouched: true,
        nearMissesFailClosed: true,
        registeredValuesChanged: false,
        noLastWallClaim: true,
      },
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR only",
      registeredReadoutRecipient: "David for separate ruling",
    },
  });
  next.phase = "green-review";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized bounded Round 17: exact season-summary provider non-player aggregate exclusion; fresh registered rerun only after Codex explicit CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 17 },
      boundedPurpose: "season-summary provider non-player aggregate exclusion",
      registrationReadSha256: REGISTRATION_READ_SHA256,
      openSnapshotHash,
      rerunAuthorityGranted: true,
      executionHeldPendingCodexClear: true,
      registeredReadoutRecipient: "David for separate ruling",
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

const apply = process.argv.length === 3 && process.argv[2] === "--apply";
if (process.argv.length > (apply ? 3 : 2) || (process.argv[2] && !apply)) {
  fail("usage: node qb1_season_summary_aggregate_round17_open_codex_v1.mjs [--apply]");
}

const run = await loadRun({ statePath: STATE_PATH });
validatePinnedRun(run);
if (!apply) {
  process.stdout.write(
    `${JSON.stringify(
      {
        mode: "dry-run",
        currentRevision: run.revision,
        nextRevision: run.revision + 1,
        round: 17,
        scope: SCOPE,
        expectedOpenSnapshotHash: EXPECTED_SCOPE_HASH,
        executionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
  process.exit(0);
}

let snapshotCreated = false;
try {
  const openSnapshotHash = takeScopedSnapshot(run.worktree);
  snapshotCreated = true;
  if (openSnapshotHash !== EXPECTED_SCOPE_HASH) {
    fail(`open snapshot hash ${openSnapshotHash} != ${EXPECTED_SCOPE_HASH}`);
  }
  const next = buildOpenRun(run, openSnapshotHash, new Date().toISOString());
  const persisted = await persistRun(next, { statePath: STATE_PATH });
  process.stdout.write(
    `${JSON.stringify(
      {
        status: "applied",
        revision: persisted.revision,
        phase: persisted.phase,
        round: 17,
        openSnapshotHash,
        stateRepair: REPAIR_ID,
        executionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
} catch (error) {
  if (snapshotCreated && existsSync(ROUND_ROOT)) rmSync(ROUND_ROOT, { recursive: true });
  throw error;
}
