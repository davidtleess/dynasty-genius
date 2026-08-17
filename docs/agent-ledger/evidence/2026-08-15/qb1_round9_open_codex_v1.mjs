#!/usr/bin/env node

/**
 * Open David-authorized bounded QB-1 green-review round 9.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-15/qb1_round9_open_codex_v1.mjs --apply
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
const ROUND_9_ROOT = join(SNAPSHOT_ROOT, "green-review-9");
const ROUND_9_OPEN = join(ROUND_9_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 50;
const EXPECTED_ROUND_8_CLOSE_HASH =
  "205d84b2073a567cd205fde01a74984c087fca742cfbbd1902cd1f12a0058f44";
const EXPECTED_JUDGE_RULED_AT = "2026-08-15T02:50:23.167Z";
const DAVID_WORD =
  "one more bounded round - open round 9 per your sanctioned mechanism, " +
  "claude implements your three R8 smallest corrections, execution only on your clear";
const REPAIR_ID = "TW15-QB1-R9-OPEN-CODEX-V1";

const ROUND_9_SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "913225f529a0c63a30b4ee6b025c3d1ac408a5d6107be15b8a65dc80d83e9f37",
  ],
  [
    "scripts/run_qb1_study.py",
    "ef7a8244d5b141eaa7280f37b269531089f5eeeb6649b230b09fcbe50bde86eb",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "513ed1bd255c9c62368bcb68f8cacfbfdc3284aa5c9df3a0c8a36affd46b9b58",
  ],
]);

const EXPECTED_BLOCKERS = new Set([
  "R8-G1-H5-SPECIAL-CASE",
  "R8-G2-EVALUABLE-RECONCILIATION",
  "R8-G3-F13-TOTALITY",
]);

function fail(message) {
  throw new Error(`round-9 open refused: ${message}`);
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
  if (existsSync(ROUND_9_ROOT)) {
    fail(`round-9 snapshot directory already exists: ${ROUND_9_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-9 scope ${relativePath}`);
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
  if (run.reason !== "review failed 3 times in green-review") {
    fail(`terminal reason changed: ${JSON.stringify(run.reason)}`);
  }
  if (run.failureCounts?.["green-review:review"] !== 4) {
    fail(`review failure count changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (
    run.judgeRuling?.ruling !== "STOP" ||
    run.judgeRuling?.ruledAt !== EXPECTED_JUDGE_RULED_AT
  ) {
    fail("the recorded Judge STOP ruling is absent or changed");
  }
  if (
    !Array.isArray(run.checks) ||
    run.checks.length !== 4 ||
    run.checks.some((check) => check.name !== "review" || check.status !== "failed")
  ) {
    fail("expected exactly four failed review receipts");
  }
  if (!Array.isArray(run.reviewRounds)) fail("reviewRounds is not an array");
  const green = run.reviewRounds.filter((round) => round.phase === "green-review");
  if (
    green.length !== 8 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly eight closed green-review rounds indexed 1..8");
  }
  const round8 = green.at(-1);
  if (round8.churn?.closeSnapshotHash !== EXPECTED_ROUND_8_CLOSE_HASH) {
    fail("round-8 close snapshot hash changed");
  }
  const unresolved = round8.findings.filter(
    (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
  );
  if (
    unresolved.length !== EXPECTED_BLOCKERS.size ||
    unresolved.some((finding) => !EXPECTED_BLOCKERS.has(finding.criterionId))
  ) {
    fail(
      `round 8 unresolved blockers changed: ${JSON.stringify(
        unresolved.map((finding) => finding.criterionId),
      )}`,
    );
  }
  if (!run.stateRepairs?.some((repair) => repair.id === "TW15-QB1-R8-OPEN-CODEX-V1")) {
    fail("round-8 authorization record is absent");
  }
  if (existsSync(ROUND_9_ROOT)) fail("green-review-9 snapshot directory already exists");
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, ROUND_9_SCOPE);
  if (currentScopeHash !== EXPECTED_ROUND_8_CLOSE_HASH) {
    fail(
      `current scope hash ${currentScopeHash} != round-8 close ${EXPECTED_ROUND_8_CLOSE_HASH}`,
    );
  }
}

function buildRound9Run(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 9,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...ROUND_9_SCOPE],
    findings: [],
    churn: { openSnapshotHash },
    authorization: {
      authority: "David",
      word: DAVID_WORD,
      boundedPurpose:
        "Claude implements exactly the three open round-8 smallest corrections; no wider product change, execution, push, or publication",
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
    "David-authorized bounded green-review round 9 is open; study execution remains held pending Codex CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 9 },
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
  const prospectiveOpenHash = scopedSnapshotHash(run.worktree, ROUND_9_SCOPE);
  const preview = {
    mode: apply ? "apply" : "dry-run",
    repairId: REPAIR_ID,
    runId: run.id,
    loadedRevision: run.revision,
    round9: {
      phase: "green-review",
      index: 9,
      scope: ROUND_9_SCOPE,
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
      ROUND_9_SCOPE,
      ROUND_9_OPEN,
    );
    createdSnapshot = true;
    if (openSnapshotHash !== prospectiveOpenHash) {
      fail("worktree changed while the round-9 open snapshot was being taken");
    }
    const persisted = await persistRun(
      buildRound9Run(run, openSnapshotHash, new Date().toISOString()),
      { statePath: STATE_PATH },
    );
    preview.persistedRevision = persisted.revision;
    preview.result = "APPLIED";
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
  } catch (error) {
    if (createdSnapshot && existsSync(ROUND_9_ROOT)) {
      rmSync(ROUND_9_ROOT, { recursive: true, force: true });
    }
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 64;
});
