#!/usr/bin/env node

/**
 * Open David-authorized QB-1 full-evidence redesign round 11.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_full_evidence_redesign_round_open_codex_v1.mjs --apply
 *
 * The installed round-open verb correctly rejects this terminal, over-cap run.
 * David directly authorized the full-evidence redesign and then directed Codex
 * to re-run the missing apply step. This script validates the exact blocked
 * revision, takes the normal scoped open snapshot, and writes only through
 * persistRun's revision-guarded atomic writer. It does not resolve the Round 10
 * finding or authorize study execution, publication, commit, or push.
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
const ROUND_ROOT = join(SNAPSHOT_ROOT, "green-review-11");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 61;
const EXPECTED_ROUND_10_CLOSE_HASH =
  "54dd7c6444ca3dc884cefb6fa40de7c9f476d1bb35ace1fdbc4e30670f928730";
const EXPECTED_JUDGE_RULED_AT = "2026-08-15T02:50:23.167Z";
const DAVID_WORD =
  "your redesign-round transition has not persisted - run.json still reads phase " +
  "blocked, revision unchanged since 23:18, no new snapshot on disk. re-run your " +
  "apply step and confirm the new revision number and open-snapshot hash";
const REPAIR_ID = "TW16-QB1-FULL-EVIDENCE-REDESIGN-R11-OPEN-CODEX-V1";
const BLOCKER = "R10-G1-F13-AGGREGATE-TOTALITY";

const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "68c72468c8022ad815ac96eb6594782b618354ae151320bf17c3aae085665eae",
  ],
  [
    "scripts/run_qb1_study.py",
    "c9720e1bc08cd0e85c7a4929c6d4bd219b4dca9ffdea3bf59f900b97203fa4cc",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "5246eaa5ca2f577f15635f185ac2ed72b6e5a3257c786d4aa1f03887e428f1e9",
  ],
]);

function fail(message) {
  throw new Error(`full-evidence redesign round open refused: ${message}`);
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
  if (existsSync(ROUND_ROOT)) {
    fail(`round-11 snapshot directory already exists: ${ROUND_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-11 scope ${relativePath}`);
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
  if (run.failureCounts?.["green-review:review"] !== 6) {
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
    run.checks.length !== 6 ||
    run.checks.some((check) => check.name !== "review" || check.status !== "failed")
  ) {
    fail("expected exactly six failed review receipts");
  }
  if (!Array.isArray(run.reviewRounds)) fail("reviewRounds is not an array");
  const green = run.reviewRounds.filter((round) => round.phase === "green-review");
  if (
    green.length !== 10 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly ten closed green-review rounds indexed 1..10");
  }
  const round10 = green.at(-1);
  if (round10.churn?.closeSnapshotHash !== EXPECTED_ROUND_10_CLOSE_HASH) {
    fail("round-10 close snapshot hash changed");
  }
  const unresolved = round10.findings.filter(
    (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
  );
  if (unresolved.length !== 1 || unresolved[0].criterionId !== BLOCKER) {
    fail(
      `round-10 unresolved blockers changed: ${JSON.stringify(
        unresolved.map((finding) => finding.criterionId),
      )}`,
    );
  }
  if (
    !run.stateRepairs?.some(
      (repair) =>
        repair.id === "TW15-QB1-R10-CLOSE-AFTER-FAILED-CHECK-CODEX-V1",
    )
  ) {
    fail("round-10 close repair record is absent");
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-11 snapshot directory already exists");
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, SCOPE);
  if (currentScopeHash !== EXPECTED_ROUND_10_CLOSE_HASH) {
    fail(
      `current scope hash ${currentScopeHash} != round-10 close ${EXPECTED_ROUND_10_CLOSE_HASH}`,
    );
  }
}

function buildOpenRun(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 11,
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
      boundedPurpose:
        "Claude implements the F13 full-evidence redesign: disclose one unique evidence row for every evaluable player and derive dual/pocket totals, exact boundary membership, and flip totals from those rows; no wider product change, execution, publication, commit, or push",
      executionTrigger: "Codex explicit CLEAR only",
      carriedBlocker: BLOCKER,
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
    "David-authorized QB-1 full-evidence redesign round is open; study execution remains held pending Codex CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 11 },
      boundedPurpose: "F13 full-evidence redesign only",
      carriedBlockers: [BLOCKER],
      openSnapshotHash,
      executionAuthorized: false,
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
  const prospectiveOpenHash = scopedSnapshotHash(run.worktree, SCOPE);
  const preview = {
    mode: apply ? "apply" : "dry-run",
    repairId: REPAIR_ID,
    runId: run.id,
    loadedRevision: run.revision,
    round11: {
      phase: "green-review",
      index: 11,
      scope: SCOPE,
      openSnapshotHash: prospectiveOpenHash,
      authority: DAVID_WORD,
      carriedBlockers: [BLOCKER],
    },
    executionHeldPendingCodexClear: true,
  };

  if (!apply) {
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
    return;
  }

  let createdSnapshot = false;
  try {
    const openSnapshotHash = takeScopedSnapshot(run.worktree, SCOPE, ROUND_OPEN);
    createdSnapshot = true;
    if (openSnapshotHash !== prospectiveOpenHash) {
      fail("worktree changed while the round-11 open snapshot was being taken");
    }
    const persisted = await persistRun(
      buildOpenRun(run, openSnapshotHash, new Date().toISOString()),
      { statePath: STATE_PATH },
    );
    preview.persistedRevision = persisted.revision;
    preview.result = "APPLIED";
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
  } catch (error) {
    if (createdSnapshot && existsSync(ROUND_ROOT)) {
      rmSync(ROUND_ROOT, { recursive: true, force: true });
    }
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 64;
});
