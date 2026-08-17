#!/usr/bin/env node

/**
 * Audit-only completion of terminal QB-1 green-review round 7.
 *
 * The third failed `review` receipt terminalized the run before the chained
 * finding verbs ran. This script does not unblock or reopen the run. It adds
 * the four measured blockers, takes the normal close snapshot, measures churn,
 * and persists exclusively through the revision-guarded atomic writer.
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
const OPEN_DIR = join(SNAPSHOT_ROOT, "green-review-7", "open");
const CLOSE_DIR = join(SNAPSHOT_ROOT, "green-review-7", "close");
const RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 39;
const OPEN_HASH =
  "dbe9aacefa731ec5fb62b79fa1e02084229185b7679f8044c25cc267c3e325c1";
const REVIEW_HASH =
  "25ac1c8fd7c3fcfa85ab213a6779c8e5d82960223dff6e270de705e4aa7b6310";
const PROBE_HASH =
  "b939e7814dd34f8bce9e10669c403c0f77df6117c9be9f0919c2971727949f55";

const FINDINGS = [
  {
    criterionId: "R7-G1-STATUS-TOTALITY",
    file: "src/dynasty_genius/eval/qb_validation/execution.py",
    summary:
      "Publication gate does not enforce the registered total status functions or fold totals.",
    evidence:
      "Public runner accepts wrong-direction supported, above-floor unsupported_power, 9 model folds, and market_noninferior with p_ni=.99 and missing adjusted/one-sided evidence; probe lines 33-113.",
  },
  {
    criterionId: "R7-G2-H5-RECONCILIATION",
    file: "src/dynasty_genius/eval/qb_validation/execution.py",
    summary:
      "H5 margin leaves and per-fold evidence remain shell-tolerant and non-exact.",
    evidence:
      "Public runner accepts 12 empty margin leaves, partial c11 omission without flag, and evaluable_folds=0 with four c11 metric rows; probe lines 116-174.",
  },
  {
    criterionId: "R7-G3-F13-SEMANTICS",
    file: "src/dynasty_genius/eval/qb_validation/execution.py",
    summary:
      "F13 boundary rows are typed but not bound to the registered computation.",
    evidence:
      "Public runner accepts season 1900, 10000 rushing yards, qualifying_games=-10.5 as a modern plus-or-minus-one-yard boundary case; probe lines 177-217.",
  },
  {
    criterionId: "R7-G4-CASE-FOLD-LANE",
    file: "src/dynasty_genius/eval/qb_validation/execution.py",
    summary:
      "Case lane validation permits H5 outside the registered H5 folds.",
    evidence:
      "Public runner publishes a reported H5 lane on a 2025 case although H5 folds are 2021-2024; probe lines 220-236.",
  },
];

function fail(message) {
  throw new Error(`round-7 terminal record repair refused: ${message}`);
}

function fingerprint(phase, criterionId, file) {
  const normalize = (value) => String(value).trim().replace(/\s+/g, " ").toLowerCase();
  return createHash("sha256")
    .update([phase, criterionId, file].map(normalize).join("\0"))
    .digest("hex");
}

function snapshotHash(root, scope) {
  const hash = createHash("sha256");
  for (const relativePath of [...scope].sort()) {
    hash.update(`${relativePath}\0`);
    hash.update(readFileSync(resolve(root, relativePath)));
    hash.update("\0");
  }
  return hash.digest("hex");
}

function takeSnapshot(worktree, scope, destination) {
  if (existsSync(destination)) fail(`close snapshot already exists: ${destination}`);
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    if (!existsSync(source) || !lstatSync(source).isFile()) {
      fail(`scope path is not a regular file: ${relativePath}`);
    }
    const target = join(destination, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return snapshotHash(destination, scope);
}

function measureChurn(openDir, closeDir) {
  let output = "";
  try {
    output = execFileSync(
      "git",
      ["diff", "--no-index", "--numstat", openDir, closeDir],
      { encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"] },
    );
  } catch (error) {
    if (error.status === 1 && typeof error.stdout === "string") output = error.stdout;
    else fail(`churn measurement failed: ${error.message}`);
  }
  let filesChanged = 0;
  let linesChanged = 0;
  for (const line of output.split("\n")) {
    const match = line.match(/^(\d+|-)\t(\d+|-)\t/);
    if (!match) continue;
    filesChanged += 1;
    if (match[1] !== "-") linesChanged += Number(match[1]);
    if (match[2] !== "-") linesChanged += Number(match[2]);
  }
  return { filesChanged, linesChanged };
}

function validate(run) {
  if (run.id !== RUN_ID) fail(`run id changed: ${run.id}`);
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision ${run.revision} != ${EXPECTED_REVISION}`);
  }
  if (run.phase !== "blocked" || run.terminalState !== "BLOCKED") {
    fail(`run is not terminal BLOCKED: ${run.phase}/${run.terminalState}`);
  }
  if (run.reason !== "review failed 3 times in green-review") {
    fail(`terminal reason changed: ${run.reason}`);
  }
  const round = run.reviewRounds.find(
    (candidate) => candidate.phase === "green-review" && candidate.index === 7,
  );
  if (!round || round.closedAt !== null || round.findings.length !== 0) {
    fail("round 7 is absent, closed, or already has findings");
  }
  if (round.churn?.openSnapshotHash !== OPEN_HASH) fail("round-7 open hash changed");
  if (snapshotHash(OPEN_DIR, round.scope) !== OPEN_HASH) {
    fail("round-7 open snapshot identity failed");
  }
  if (existsSync(CLOSE_DIR)) fail("round-7 close snapshot already exists");
  return round;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 1 || args[0] !== "--apply") {
    fail("the only invocation is this script with exactly --apply");
  }
  const run = await loadRun({ statePath: STATE_PATH });
  const round = validate(run);
  let createdClose = false;
  try {
    const closeHash = takeSnapshot(run.worktree, round.scope, CLOSE_DIR);
    createdClose = true;
    const churn = measureChurn(OPEN_DIR, CLOSE_DIR);
    const now = new Date().toISOString();
    const next = structuredClone(run);
    const target = next.reviewRounds.find(
      (candidate) => candidate.phase === "green-review" && candidate.index === 7,
    );
    target.findings = FINDINGS.map((finding, index) => ({
      id: `finding-green-review-7-${index + 1}`,
      severity: "BLOCKER",
      ...finding,
      fingerprint: fingerprint("green-review", finding.criterionId, finding.file),
      recordedInRound: 7,
      resolvedInRound: null,
    }));
    target.churn = {
      filesChanged: churn.filesChanged,
      linesChanged: churn.linesChanged,
      openSnapshotHash: OPEN_HASH,
      closeSnapshotHash: closeHash,
    };
    target.closedAt = now;
    next.reason =
      "review failed 3 times in green-review; round 7 NOT CLEAR with 4 recorded BLOCKERs";
    next.stateRepairs = [
      ...(next.stateRepairs ?? []),
      {
        id: "TW15-QB1-R7-TERMINAL-RECORD-CODEX-V1",
        status: "applied",
        purpose:
          "audit-only finding and close recording after the third failed review receipt terminalized before finding verbs",
        reviewHash: REVIEW_HASH,
        probeHash: PROBE_HASH,
        terminalStatePreserved: "BLOCKED",
        recordedAt: now,
      },
    ];
    next.updatedAt = now;
    const persisted = await persistRun(next, { statePath: STATE_PATH });
    process.stdout.write(
      `${JSON.stringify(
        {
          result: "APPLIED",
          persistedRevision: persisted.revision,
          terminalState: persisted.terminalState,
          round7: {
            closedAt: target.closedAt,
            findings: target.findings.map((finding) => finding.id),
            churn: target.churn,
          },
        },
        null,
        2,
      )}\n`,
    );
  } catch (error) {
    if (createdClose && existsSync(CLOSE_DIR)) {
      rmSync(CLOSE_DIR, { recursive: true, force: true });
    }
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 64;
});
