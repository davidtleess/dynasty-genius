#!/usr/bin/env node

/**
 * Close reviewed QB-1 green-review round 10 after the failed-review receipt
 * terminalized the run before the standard round-close verb could run.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-15/qb1_round10_close_after_failed_check_codex_v1.mjs --apply
 *
 * This repair preserves the recorded BLOCKER, failed review receipt, terminal
 * BLOCKED state, and execution hold. It only takes the normal close snapshot,
 * records script-measured churn, and marks the already-reviewed round closed.
 */

import { execFileSync } from "node:child_process";
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
const OPEN_DIR = join(SNAPSHOT_ROOT, "green-review-10", "open");
const CLOSE_DIR = join(SNAPSHOT_ROOT, "green-review-10", "close");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 60;
const EXPECTED_OPEN_HASH =
  "78b1d9f7e573a33a3939795ba05a7351c0e5db5055ea960a299e19f2447d84b5";
const REVIEW_SHA =
  "77f431e56e6b383ae7113c90a1d142e3bd904d942cf64b3fa5517f045ec1f762";
const PROBE_SHA =
  "8e9e072f963077b1fc703ab4c39c41c5e4161509142460c11d79c495ab51d362";
const REPAIR_ID = "TW15-QB1-R10-CLOSE-AFTER-FAILED-CHECK-CODEX-V1";

const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_FINAL_HASHES = new Map([
  [
    SCOPE[0],
    "68c72468c8022ad815ac96eb6594782b618354ae151320bf17c3aae085665eae",
  ],
  [
    SCOPE[1],
    "c9720e1bc08cd0e85c7a4929c6d4bd219b4dca9ffdea3bf59f900b97203fa4cc",
  ],
  [
    SCOPE[2],
    "5246eaa5ca2f577f15635f185ac2ed72b6e5a3257c786d4aa1f03887e428f1e9",
  ],
]);

function fail(message) {
  throw new Error(`round-10 close repair refused: ${message}`);
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
    hash.update(readFileSync(resolve(root, relativePath)));
    hash.update("\0");
  }
  return hash.digest("hex");
}

function takeScopedSnapshot(worktree, scope, destination) {
  if (existsSync(destination)) fail(`close snapshot already exists: ${destination}`);
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, relativePath);
    const target = join(destination, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedSnapshotHash(destination, scope);
}

function measureChurn(openDir, closeDir) {
  let stdout;
  try {
    stdout = execFileSync(
      "git",
      ["diff", "--no-index", "--numstat", openDir, closeDir],
      { encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"] },
    );
  } catch (error) {
    if (error.status === 1 && typeof error.stdout === "string") {
      stdout = error.stdout;
    } else {
      fail(`churn measurement failed: ${error.message}`);
    }
  }
  let filesChanged = 0;
  let linesChanged = 0;
  for (const line of stdout.split("\n")) {
    const match = line.match(/^(\d+|-)\t(\d+|-)\t/);
    if (!match) continue;
    filesChanged += 1;
    if (match[1] !== "-") linesChanged += Number(match[1]);
    if (match[2] !== "-") linesChanged += Number(match[2]);
  }
  return { filesChanged, linesChanged };
}

function validatePinnedState(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id changed: ${run.id}`);
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision ${run.revision} != ${EXPECTED_REVISION}`);
  }
  if (run.phase !== "blocked" || run.terminalState !== "BLOCKED") {
    fail(`run is not BLOCKED (${run.phase}/${run.terminalState})`);
  }
  if (run.reason !== "review failed 3 times in green-review") {
    fail(`terminal reason changed: ${run.reason}`);
  }
  if (run.failureCounts?.["green-review:review"] !== 6) {
    fail("expected six failed green-review receipts");
  }
  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "review" ||
    lastCheck?.status !== "failed" ||
    !lastCheck?.evidence?.includes(REVIEW_SHA) ||
    !lastCheck?.evidence?.includes(PROBE_SHA)
  ) {
    fail("the round-10 failed review receipt is absent or changed");
  }
  const round = run.reviewRounds?.find(
    (candidate) => candidate.phase === "green-review" && candidate.index === 10,
  );
  if (!round || round.closedAt !== null) fail("round 10 is absent or already closed");
  if (JSON.stringify(round.scope) !== JSON.stringify(SCOPE)) fail("round scope changed");
  if (round.churn?.openSnapshotHash !== EXPECTED_OPEN_HASH) fail("open hash changed");
  if (round.reviewerVerdict !== null) fail("unexpected reviewer CLEAR on NOT CLEAR round");
  if (
    round.findings?.length !== 1 ||
    round.findings[0].criterionId !== "R10-G1-F13-AGGREGATE-TOTALITY" ||
    round.findings[0].severity !== "BLOCKER" ||
    round.findings[0].resolvedInRound !== null ||
    !round.findings[0].evidence.includes(REVIEW_SHA) ||
    !round.findings[0].evidence.includes(PROBE_SHA)
  ) {
    fail("round-10 BLOCKER is absent or changed");
  }
  if (existsSync(CLOSE_DIR)) fail("close snapshot already exists");
  requireRegularFile(
    resolve(run.worktree, "docs/agent-ledger/evidence/2026-08-15/qb1_green_round10_review_codex_v1.md"),
    "review artifact",
  );
  requireRegularFile(
    resolve(run.worktree, "docs/agent-ledger/evidence/2026-08-15/qb1_green_round10_adversarial_probe_codex_v1.py"),
    "probe artifact",
  );
  for (const [relativePath, expectedHash] of EXPECTED_FINAL_HASHES) {
    const actualHash = sha256(readFileSync(resolve(run.worktree, relativePath)));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
}

function buildClosedRun(run, closeSnapshotHash, churn, now) {
  const next = structuredClone(run);
  const round = next.reviewRounds.find(
    (candidate) => candidate.phase === "green-review" && candidate.index === 10,
  );
  round.churn = {
    ...churn,
    openSnapshotHash: EXPECTED_OPEN_HASH,
    closeSnapshotHash,
  };
  round.closedAt = now;
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority:
        "David-authorized round 10 plus machinery reviewer wake: proceed per the loop contract",
      purpose:
        "Close the reviewed round after record-check terminalized the run before round-close; preserve NOT CLEAR BLOCKER and terminal BLOCKED",
      closedRound: { phase: "green-review", index: 10 },
      reviewSha256: REVIEW_SHA,
      probeSha256: PROBE_SHA,
      closeSnapshotHash,
      churn,
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
  validatePinnedState(run);
  const preview = {
    mode: apply ? "apply" : "dry-run",
    repairId: REPAIR_ID,
    runId: run.id,
    loadedRevision: run.revision,
    round: 10,
    terminalStatePreserved: "BLOCKED",
    executionAuthorized: false,
  };
  if (!apply) {
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
    return;
  }

  let createdSnapshot = false;
  try {
    const closeSnapshotHash = takeScopedSnapshot(run.worktree, SCOPE, CLOSE_DIR);
    createdSnapshot = true;
    const churn = measureChurn(OPEN_DIR, CLOSE_DIR);
    if (churn.filesChanged !== 3 || churn.linesChanged !== 561) {
      fail(`unexpected measured churn: ${JSON.stringify(churn)}`);
    }
    const persisted = await persistRun(
      buildClosedRun(run, closeSnapshotHash, churn, new Date().toISOString()),
      { statePath: STATE_PATH },
    );
    preview.persistedRevision = persisted.revision;
    preview.closeSnapshotHash = closeSnapshotHash;
    preview.churn = churn;
    preview.result = "APPLIED";
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
  } catch (error) {
    if (createdSnapshot && existsSync(CLOSE_DIR)) {
      rmSync(CLOSE_DIR, { recursive: true, force: true });
    }
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 64;
});
