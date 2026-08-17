#!/usr/bin/env node

/**
 * TW14-QB1-1 R5-G2 state repair.
 *
 * Dry-run is the default. The only mutating invocation is:
 *
 *   node docs/agent-ledger/evidence/2026-08-14/qb1_r5_g2_state_repair_codex_v1.mjs --apply
 *
 * The mutation is pinned to run f8f7551c at revision 23. Run-state changes
 * are persisted exclusively through the installed revision-guarded atomic
 * persistRun writer. A concurrent revision change fails closed.
 */

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  renameSync,
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
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 23;
const EXPECTED_OPEN_HASH =
  "3f634bfd27c78ae19cc2b5b0398d77f41304780afb6df71631ac9906fc66c54d";
const EXPECTED_CLOSE_HASH =
  "79e9a76c43648265ed9189ce87fe8d2fd52fc53ef4bcf12f32e2604420fe7fa4";
const EXPECTED_JUDGE_RULED_AT = "2026-08-15T02:50:23.167Z";
const DAVID_WORD = "do it - remediation round plus state repair authorized";
const REPAIR_ID = "TW14-QB1-1-R5-G2-CODEX-V1";

const ROUND_4_SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "src/dynasty_genius/eval/qb_validation/status.py",
  "src/dynasty_genius/eval/qb_validation/__init__.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
  "tests/contract/test_qb1_execution_red.py",
];

const ROUND_6_SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const SOURCE_OPEN = join(SNAPSHOT_ROOT, "green-review-1", "open");
const TARGET_OPEN = join(SNAPSHOT_ROOT, "green-review-4", "open");
const TARGET_CLOSE = join(SNAPSHOT_ROOT, "green-review-4", "close");
const ROUND_6_OPEN = join(SNAPSHOT_ROOT, "green-review-6", "open");

function fail(message) {
  throw new Error(`R5-G2 repair refused: ${message}`);
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
    const absolutePath = resolve(root, relativePath);
    try {
      hash.update(readFileSync(absolutePath));
    } catch {
      hash.update("<absent>");
    }
    hash.update("\0");
  }
  return hash.digest("hex");
}

function measureScopedChurn(openRoot, closeRoot, scope) {
  let filesChanged = 0;
  let linesChanged = 0;
  for (const relativePath of scope) {
    const openPath = resolve(openRoot, relativePath);
    const closePath = resolve(closeRoot, relativePath);
    requireRegularFile(openPath, `round-4 open snapshot ${relativePath}`);
    requireRegularFile(closePath, `round-4 close snapshot ${relativePath}`);
    let stdout = "";
    try {
      stdout = execFileSync(
        "git",
        ["diff", "--no-index", "--numstat", openPath, closePath],
        { encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"] },
      );
    } catch (error) {
      if (error.status === 1 && typeof error.stdout === "string") {
        stdout = error.stdout;
      } else {
        fail(`scoped churn measurement failed for ${relativePath}: ${error.message}`);
      }
    }
    for (const line of stdout.split("\n")) {
      const match = line.match(/^(\d+|-)\t(\d+|-)\t/);
      if (!match) continue;
      filesChanged += 1;
      if (match[1] !== "-") linesChanged += Number(match[1]);
      if (match[2] !== "-") linesChanged += Number(match[2]);
    }
  }
  return { filesChanged, linesChanged };
}

function takeScopedSnapshot(worktree, scope, destination) {
  if (existsSync(destination)) {
    fail(`round-6 open snapshot already exists: ${destination}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-6 scope ${relativePath}`);
    const target = join(destination, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedSnapshotHash(destination, scope);
}

function findRound(run, phase, index) {
  const matches = run.reviewRounds.filter(
    (round) => round.phase === phase && round.index === index,
  );
  if (matches.length !== 1) {
    fail(`expected exactly one ${phase} round ${index}, found ${matches.length}`);
  }
  return matches[0];
}

function validatePinnedRun(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id is ${run.id ?? "missing"}`);
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision is ${run.revision ?? "missing"}, expected ${EXPECTED_REVISION}`);
  }
  if (run.schemaVersion !== 3) fail(`schemaVersion is ${run.schemaVersion ?? "missing"}`);
  if (run.phase !== "blocked" || run.terminalState !== "BLOCKED") {
    fail(`run is not the ruled BLOCKED state (${run.phase}/${run.terminalState})`);
  }
  const reasonCodes = new Set(run.reasonCodes ?? []);
  if (!reasonCodes.has("PHASE_ROUND_CAP") || !reasonCodes.has("JUDGE_STOP")) {
    fail("PHASE_ROUND_CAP/JUDGE_STOP reason codes are not both present");
  }
  if (
    run.judgeRuling?.ruling !== "STOP" ||
    run.judgeRuling?.ruledAt !== EXPECTED_JUDGE_RULED_AT
  ) {
    fail("the pinned Judge STOP ruling is absent or changed");
  }
  if (!Array.isArray(run.reviewRounds)) fail("reviewRounds is not an array");
  const green = run.reviewRounds.filter((round) => round.phase === "green-review");
  if (
    green.length !== 5 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly five closed green-review rounds indexed 1..5");
  }
  const round4 = findRound(run, "green-review", 4);
  if (
    round4.churn?.openSnapshotHash !== EXPECTED_OPEN_HASH ||
    round4.churn?.closeSnapshotHash !== EXPECTED_CLOSE_HASH
  ) {
    fail("round-4 recorded snapshot hashes changed");
  }
  const round5 = findRound(run, "green-review", 5);
  const unresolved = round5.findings.filter(
    (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
  );
  if (!unresolved.some((finding) => finding.criterionId === "R5-G1")) {
    fail("round 5 has no unresolved R5-G1 blocker");
  }
  if (unresolved.filter((finding) => finding.criterionId === "R5-G2").length !== 1) {
    fail("round 5 does not have exactly one unresolved R5-G2 blocker");
  }
  if (existsSync(TARGET_OPEN)) fail("green-review-4/open already exists");
  if (!existsSync(SOURCE_OPEN)) fail("green-review-1/open is absent");
  if (!existsSync(TARGET_CLOSE)) fail("green-review-4/close is absent");
  if (existsSync(ROUND_6_OPEN)) fail("green-review-6/open already exists");
}

function buildUnavailableState(run, observedHash, now) {
  const next = structuredClone(run);
  const round4 = findRound(next, "green-review", 4);
  round4.churn = {
    filesChanged: null,
    linesChanged: null,
    openSnapshotHash: round4.churn.openSnapshotHash,
    closeSnapshotHash: round4.churn.closeSnapshotHash,
    measurementStatus: "unavailable",
    unavailableReason:
      `surviving green-review-1/open scoped hash ${observedHash} did not match ` +
      `recorded round-4 openSnapshotHash ${EXPECTED_OPEN_HASH}`,
  };
  next.phase = "blocked";
  next.terminalState = "BLOCKED";
  next.reason =
    "R5-G2 state repair unavailable: the surviving round-4 baseline failed its pinned identity check";
  next.reasonCodes = [
    ...new Set([...(next.reasonCodes ?? []), "CHURN_BASELINE_UNAVAILABLE"]),
  ];
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "unavailable",
      authority: DAVID_WORD,
      observedOpenSnapshotHash: observedHash,
      expectedOpenSnapshotHash: EXPECTED_OPEN_HASH,
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

function buildRepairedRun(run, churn, round6OpenHash, now) {
  const next = structuredClone(run);
  const round4 = findRound(next, "green-review", 4);
  round4.churn = {
    filesChanged: churn.filesChanged,
    linesChanged: churn.linesChanged,
    openSnapshotHash: EXPECTED_OPEN_HASH,
    closeSnapshotHash: EXPECTED_CLOSE_HASH,
    measurementStatus: "measured",
    measurementBasis:
      "restored snapshots/green-review-4/open vs snapshots/green-review-4/close over the recorded round-4 scope",
  };

  const round5 = findRound(next, "green-review", 5);
  const r5g2 = round5.findings.find(
    (finding) => finding.criterionId === "R5-G2" && finding.resolvedInRound === null,
  );
  r5g2.resolvedInRound = 6;

  next.reviewRounds.push({
    phase: "green-review",
    index: 6,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...ROUND_6_SCOPE],
    findings: [],
    churn: { openSnapshotHash: round6OpenHash },
    authorization: {
      authority: "David",
      word: DAVID_WORD,
      boundedPurpose:
        "one remediation round for R5-G1 after Codex repairs R5-G2; no execution, push, or wider change",
      judgeStopRuling: {
        ruling: next.judgeRuling.ruling,
        ruledAt: next.judgeRuling.ruledAt,
        reasonCodes: ["PHASE_ROUND_CAP", "JUDGE_STOP"],
      },
    },
  });

  next.phase = "green-review";
  next.terminalState = null;
  next.reason =
    "David-authorized bounded remediation round 6 is open; study execution remains held pending Codex CLEAR";
  next.reasonCodes = [];
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      judgeStopRuledAt: next.judgeRuling.ruledAt,
      restoredOpenSnapshotHash: EXPECTED_OPEN_HASH,
      correctedRound4Churn: churn,
      openedRound: { phase: "green-review", index: 6 },
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.some((arg) => arg !== "--apply") || args.filter((arg) => arg === "--apply").length > 1) {
    fail("usage is the script path alone (dry-run) or with exactly --apply");
  }
  const apply = args.includes("--apply");
  const run = await loadRun({ statePath: STATE_PATH });
  validatePinnedRun(run);

  const observedOpenHash = scopedSnapshotHash(SOURCE_OPEN, ROUND_4_SCOPE);
  const observedCloseHash = scopedSnapshotHash(TARGET_CLOSE, ROUND_4_SCOPE);
  if (observedCloseHash !== EXPECTED_CLOSE_HASH) {
    fail(`round-4 close snapshot hash is ${observedCloseHash}, expected ${EXPECTED_CLOSE_HASH}`);
  }

  if (observedOpenHash !== EXPECTED_OPEN_HASH) {
    const preview = {
      mode: apply ? "apply" : "dry-run",
      repairId: REPAIR_ID,
      result: "CHURN_BASELINE_UNAVAILABLE",
      observedOpenHash,
      expectedOpenHash: EXPECTED_OPEN_HASH,
    };
    if (apply) {
      const persisted = await persistRun(
        buildUnavailableState(run, observedOpenHash, new Date().toISOString()),
        { statePath: STATE_PATH },
      );
      preview.persistedRevision = persisted.revision;
    }
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
    process.exitCode = 2;
    return;
  }

  const churn = measureScopedChurn(SOURCE_OPEN, TARGET_CLOSE, ROUND_4_SCOPE);
  const prospectiveRound6OpenHash = scopedSnapshotHash(run.worktree, ROUND_6_SCOPE);
  const preview = {
    mode: apply ? "apply" : "dry-run",
    repairId: REPAIR_ID,
    runId: run.id,
    loadedRevision: run.revision,
    restoredRound4OpenSnapshotHash: observedOpenHash,
    verifiedRound4CloseSnapshotHash: observedCloseHash,
    correctedRound4Churn: churn,
    round6: {
      phase: "green-review",
      index: 6,
      scope: ROUND_6_SCOPE,
      openSnapshotHash: prospectiveRound6OpenHash,
      authority: DAVID_WORD,
    },
    executionHeldPendingCodexClear: true,
  };

  if (!apply) {
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
    return;
  }

  let movedRound4Open = false;
  let createdRound6Open = false;
  try {
    renameSync(SOURCE_OPEN, TARGET_OPEN);
    movedRound4Open = true;
    if (scopedSnapshotHash(TARGET_OPEN, ROUND_4_SCOPE) !== EXPECTED_OPEN_HASH) {
      fail("round-4 open snapshot identity changed during the atomic move");
    }
    const round6OpenHash = takeScopedSnapshot(run.worktree, ROUND_6_SCOPE, ROUND_6_OPEN);
    createdRound6Open = true;
    if (round6OpenHash !== prospectiveRound6OpenHash) {
      fail("worktree changed while the round-6 open snapshot was being taken");
    }
    const persisted = await persistRun(
      buildRepairedRun(run, churn, round6OpenHash, new Date().toISOString()),
      { statePath: STATE_PATH },
    );
    preview.persistedRevision = persisted.revision;
    preview.result = "APPLIED";
    process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
  } catch (error) {
    if (createdRound6Open && existsSync(ROUND_6_OPEN)) {
      rmSync(join(SNAPSHOT_ROOT, "green-review-6"), { recursive: true, force: true });
    }
    if (movedRound4Open && existsSync(TARGET_OPEN) && !existsSync(SOURCE_OPEN)) {
      renameSync(TARGET_OPEN, SOURCE_OPEN);
    }
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 64;
});
