#!/usr/bin/env node

/**
 * Open David-authorized bounded QB-1 green-review round 8.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-15/qb1_round8_open_codex_v1.mjs --apply
 *
 * The installed round-open verb correctly rejects a terminal, over-cap run.
 * David's direct word authorizes this one exception. This script validates the
 * exact blocked revision, takes the normal scoped open snapshot, and writes
 * only through persistRun's revision-guarded atomic writer. It does not resolve
 * findings, authorize execution, or widen the implementation scope.
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
const ROUND_8_ROOT = join(SNAPSHOT_ROOT, "green-review-8");
const ROUND_8_OPEN = join(ROUND_8_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 40;
const EXPECTED_ROUND_7_CLOSE_HASH =
  "d937ec4da07094f69b4bc5624d4c47407142befa6376cdc61e7aff2e0d8e3337";
const EXPECTED_JUDGE_RULED_AT = "2026-08-15T02:50:23.167Z";
const DAVID_WORD =
  "one more bounded round - open round 8 per your sanctioned mechanism, " +
  "claude implements your four R7 smallest corrections, execution only on your clear";
const REPAIR_ID = "TW15-QB1-R8-OPEN-CODEX-V1";

const ROUND_8_SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "e29edaf9c4a14f00615d440ccb9c7c25aa7d61eb3a2066de6dea67bfc8cfc905",
  ],
  [
    "scripts/run_qb1_study.py",
    "a7bfd8d0a2ef03b82bd78f1f123bad5852be678bbdc4921de06492f1be6d727d",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "b4b408e7536ab8a0a88364d7feda2ceb5722d62e5828e3fb3b5b1a0e3082564f",
  ],
]);

const EXPECTED_BLOCKERS = new Set([
  "R7-G1-STATUS-TOTALITY",
  "R7-G2-H5-RECONCILIATION",
  "R7-G3-F13-SEMANTICS",
  "R7-G4-CASE-FOLD-LANE",
]);

function fail(message) {
  throw new Error(`round-8 open refused: ${message}`);
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
  if (existsSync(ROUND_8_ROOT)) {
    fail(`round-8 snapshot directory already exists: ${ROUND_8_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-8 scope ${relativePath}`);
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
  if (!Array.isArray(run.reasonCodes) || run.reasonCodes.length !== 0) {
    fail(`reasonCodes changed: ${JSON.stringify(run.reasonCodes)}`);
  }
  if (
    run.reason !==
    "review failed 3 times in green-review; round 7 NOT CLEAR with 4 recorded BLOCKERs"
  ) {
    fail(`terminal reason changed: ${JSON.stringify(run.reason)}`);
  }
  if (
    run.judgeRuling?.ruling !== "STOP" ||
    run.judgeRuling?.ruledAt !== EXPECTED_JUDGE_RULED_AT
  ) {
    fail("the recorded Judge STOP ruling is absent or changed");
  }
  if (
    !Array.isArray(run.checks) ||
    run.checks.length !== 3 ||
    run.checks.some((check) => check.name !== "review" || check.status !== "failed")
  ) {
    fail("expected exactly three failed review receipts");
  }
  if (!Array.isArray(run.reviewRounds)) fail("reviewRounds is not an array");
  const green = run.reviewRounds.filter((round) => round.phase === "green-review");
  if (
    green.length !== 7 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly seven closed green-review rounds indexed 1..7");
  }
  const round7 = green.at(-1);
  if (round7.churn?.closeSnapshotHash !== EXPECTED_ROUND_7_CLOSE_HASH) {
    fail("round-7 close snapshot hash changed");
  }
  const unresolved = round7.findings.filter(
    (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
  );
  if (
    unresolved.length !== EXPECTED_BLOCKERS.size ||
    unresolved.some((finding) => !EXPECTED_BLOCKERS.has(finding.criterionId))
  ) {
    fail(
      `round 7 unresolved blockers changed: ${JSON.stringify(
        unresolved.map((finding) => finding.criterionId),
      )}`,
    );
  }
  if (!run.stateRepairs?.some((repair) => repair.id === "TW15-QB1-R7-TERMINAL-RECORD-CODEX-V1")) {
    fail("round-7 terminal record repair is absent");
  }
  if (existsSync(ROUND_8_ROOT)) fail("green-review-8 snapshot directory already exists");
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, ROUND_8_SCOPE);
  if (currentScopeHash !== EXPECTED_ROUND_7_CLOSE_HASH) {
    fail(
      `current scope hash ${currentScopeHash} != round-7 close ${EXPECTED_ROUND_7_CLOSE_HASH}`,
    );
  }
}

function buildRound8Run(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 8,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...ROUND_8_SCOPE],
    findings: [],
    churn: { openSnapshotHash },
    authorization: {
      authority: "David",
      word: DAVID_WORD,
      boundedPurpose:
        "Claude implements exactly the four open round-7 smallest corrections; no wider product change, execution, push, or publication",
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
    "David-authorized bounded green-review round 8 is open; study execution remains held pending Codex CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 8 },
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
  const prospectiveOpenHash = scopedSnapshotHash(run.worktree, ROUND_8_SCOPE);
  const preview = {
    mode: apply ? "apply" : "dry-run",
    repairId: REPAIR_ID,
    runId: run.id,
    loadedRevision: run.revision,
    round8: {
      phase: "green-review",
      index: 8,
      scope: ROUND_8_SCOPE,
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
      ROUND_8_SCOPE,
      ROUND_8_OPEN,
    );
    createdSnapshot = true;
    if (openSnapshotHash !== prospectiveOpenHash) {
      fail("worktree changed while the round-8 open snapshot was being taken");
    }
    const persisted = await persistRun(
      buildRound8Run(run, openSnapshotHash, new Date().toISOString()),
      { statePath: STATE_PATH },
    );
    preview.persistedRevision = persisted.revision;
    preview.result = "APPLIED";
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
  } catch (error) {
    if (createdSnapshot && existsSync(ROUND_8_ROOT)) {
      rmSync(ROUND_8_ROOT, { recursive: true, force: true });
    }
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 64;
});
