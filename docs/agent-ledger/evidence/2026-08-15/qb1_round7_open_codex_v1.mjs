#!/usr/bin/env node

/**
 * TW14-QB1-1: open David-authorized bounded green-review round 7.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-15/qb1_round7_open_codex_v1.mjs --apply
 *
 * The installed openRound verb correctly rejects a terminal, over-cap run.
 * David's direct word authorizes this one exception. The script therefore
 * validates the exact ruled/blocked revision, creates the normal script-owned
 * open snapshot, and writes state only through persistRun's revision-guarded
 * atomic writer. It does not resolve findings or authorize execution.
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
const SNAPSHOT_ROOT = join(dirname(STATE_PATH), "snapshots");
const ROUND_7_OPEN = join(SNAPSHOT_ROOT, "green-review-7", "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 33;
const EXPECTED_ROUND_6_CLOSE_HASH =
  "dbe9aacefa731ec5fb62b79fa1e02084229185b7679f8044c25cc267c3e325c1";
const EXPECTED_JUDGE_RULED_AT = "2026-08-15T02:50:23.167Z";
const DAVID_WORD =
  "one more bounded round - open round 7 per your sanctioned mechanism, " +
  "claude fixes your four R6 blockers, execution only on your clear";
const REPAIR_ID = "TW14-QB1-1-R7-OPEN-CODEX-V1";

const ROUND_7_SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "bd0a725ada7d99e3049ed0c86e674bcda4fa3106d0c60fc7008b39b0ebcb5d00",
  ],
  [
    "scripts/run_qb1_study.py",
    "7015a824b1e38d5cd934c74c6281b66378dfd99e9ff2ccc3181068880e92ab68",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "b459f86b7a37c2f70d30846a6045cf91619df6c5e2d07b1b56a9956ad9fa1a2a",
  ],
]);

const EXPECTED_BLOCKERS = new Set([
  "R6-G1-STATUS",
  "R6-G1-H5-CONTENT",
  "R6-G1-F13",
  "R6-G1-REPORT-CONTENT",
]);

function fail(message) {
  throw new Error(`round-7 open refused: ${message}`);
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

function takeScopedSnapshot(worktree, scope, destination) {
  if (existsSync(destination)) fail(`round-7 open snapshot already exists: ${destination}`);
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-7 scope ${relativePath}`);
    const target = join(destination, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedSnapshotHash(destination, scope);
}

function validatePinnedRun(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id is ${run.id ?? "missing"}`);
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision is ${run.revision ?? "missing"}, expected ${EXPECTED_REVISION}`);
  }
  if (run.schemaVersion !== 3) fail(`schemaVersion is ${run.schemaVersion ?? "missing"}`);
  if (run.phase !== "blocked" || run.terminalState !== "BLOCKED") {
    fail(`run is not the expected BLOCKED state (${run.phase}/${run.terminalState})`);
  }
  if (
    !Array.isArray(run.reasonCodes) ||
    run.reasonCodes.length !== 1 ||
    run.reasonCodes[0] !== "PHASE_ROUND_CAP"
  ) {
    fail(`reasonCodes changed: ${JSON.stringify(run.reasonCodes)}`);
  }
  if (
    run.judgeRuling?.ruling !== "STOP" ||
    run.judgeRuling?.ruledAt !== EXPECTED_JUDGE_RULED_AT
  ) {
    fail("the recorded Judge STOP ruling is absent or changed");
  }
  if (!Array.isArray(run.reviewRounds)) fail("reviewRounds is not an array");
  const green = run.reviewRounds.filter((round) => round.phase === "green-review");
  if (
    green.length !== 6 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly six closed green-review rounds indexed 1..6");
  }
  const round6 = green.at(-1);
  if (round6.churn?.closeSnapshotHash !== EXPECTED_ROUND_6_CLOSE_HASH) {
    fail("round-6 close snapshot hash changed");
  }
  const unresolved = round6.findings.filter(
    (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
  );
  if (
    unresolved.length !== EXPECTED_BLOCKERS.size ||
    unresolved.some((finding) => !EXPECTED_BLOCKERS.has(finding.criterionId))
  ) {
    fail(
      `round 6 unresolved blockers changed: ${JSON.stringify(
        unresolved.map((finding) => finding.criterionId),
      )}`,
    );
  }
  if (existsSync(join(SNAPSHOT_ROOT, "green-review-7"))) {
    fail("green-review-7 snapshot directory already exists");
  }
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, ROUND_7_SCOPE);
  if (currentScopeHash !== EXPECTED_ROUND_6_CLOSE_HASH) {
    fail(
      `current scope hash ${currentScopeHash} != round-6 close ${EXPECTED_ROUND_6_CLOSE_HASH}`,
    );
  }
}

function buildRound7Run(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 7,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...ROUND_7_SCOPE],
    findings: [],
    churn: { openSnapshotHash },
    authorization: {
      authority: "David",
      word: DAVID_WORD,
      boundedPurpose:
        "Claude fixes exactly the four open round-6 blockers; no wider product change, execution, push, or publication",
      executionTrigger: "Codex explicit CLEAR only",
      priorJudgeStopRuling: {
        ruling: next.judgeRuling.ruling,
        ruledAt: next.judgeRuling.ruledAt,
      },
    },
  });
  next.phase = "green-review";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized bounded green-review round 7 is open; study execution remains held pending Codex CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 7 },
      carriedBlockers: [...EXPECTED_BLOCKERS].sort(),
      openSnapshotHash,
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

async function main() {
  const args = process.argv.slice(2);
  if (
    args.some((arg) => arg !== "--apply") ||
    args.filter((arg) => arg === "--apply").length > 1
  ) {
    fail("usage is the script path alone (dry-run) or with exactly --apply");
  }
  const apply = args.includes("--apply");
  const run = await loadRun({ statePath: STATE_PATH });
  validatePinnedRun(run);
  const prospectiveOpenHash = scopedSnapshotHash(run.worktree, ROUND_7_SCOPE);
  const preview = {
    mode: apply ? "apply" : "dry-run",
    repairId: REPAIR_ID,
    runId: run.id,
    loadedRevision: run.revision,
    round7: {
      phase: "green-review",
      index: 7,
      scope: ROUND_7_SCOPE,
      openSnapshotHash: prospectiveOpenHash,
      authority: DAVID_WORD,
      carriedBlockers: [...EXPECTED_BLOCKERS].sort(),
    },
    executionHeldPendingCodexClear: true,
  };

  if (!apply) {
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
    return;
  }

  let createdSnapshot = false;
  try {
    const openSnapshotHash = takeScopedSnapshot(
      run.worktree,
      ROUND_7_SCOPE,
      ROUND_7_OPEN,
    );
    createdSnapshot = true;
    if (openSnapshotHash !== prospectiveOpenHash) {
      fail("worktree changed while the round-7 open snapshot was being taken");
    }
    const persisted = await persistRun(
      buildRound7Run(run, openSnapshotHash, new Date().toISOString()),
      { statePath: STATE_PATH },
    );
    preview.persistedRevision = persisted.revision;
    preview.result = "APPLIED";
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
  } catch (error) {
    if (createdSnapshot && existsSync(join(SNAPSHOT_ROOT, "green-review-7"))) {
      rmSync(join(SNAPSHOT_ROOT, "green-review-7"), {
        recursive: true,
        force: true,
      });
    }
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 64;
});
