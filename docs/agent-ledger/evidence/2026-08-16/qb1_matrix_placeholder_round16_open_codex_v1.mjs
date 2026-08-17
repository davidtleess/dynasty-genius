#!/usr/bin/env node

/**
 * Open David-authorized QB-1 matrix-placeholder implementation round 16.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_matrix_placeholder_round16_open_codex_v1.mjs --apply
 *
 * The installed round-open verb rejects this terminal over-cap continuation.
 * David directly authorized one bounded implementation round and a fresh
 * registered rerun only after Codex's explicit CLEAR. This script pins the
 * terminal state, Round-15 review, exact four-file scope and pins, takes the
 * normal scoped snapshot, and writes through persistRun's revision-guarded
 * atomic writer.
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
const ROUND_ROOT = join(dirname(STATE_PATH), "snapshots", "green-review-16");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 94;
const EXPECTED_ROUND_15_CLOSE_HASH =
  "e428e9fe9d7493def5f1c02a4b9ea1825119292e80b60510487dee6dbca4e09a";
const EXPECTED_SCOPE_HASH =
  "a9c212426e55cbcd08a96428c184703d2e273e821fe20406150fbc0f810fb542";
const ROUND_15_REVIEW_SHA256 =
  "7ea5cab44aafd4435eb5579c46ebbd41fce132d4ed1dccc5bea25a6c357de0a9";
const FAILED_ARTIFACT_SHA256 =
  "ce4369becf5618de0a9a08042655556cfa3b22054607b28efa98a3e710ca112b";
const DAVID_WORD =
  "approved - open one bounded round per your sanctioned mechanism: claude applies the ONE shared placeholder classifier at the matrix weekly records exactly per your registration read's boundary (pool and frame untouched through matrix entry, near misses fail-closed, all-position team rushing totals proven unchanged), and on your explicit clear a fresh rerun fires - the registered readout then comes to me for my ruling";
const REPAIR_ID = "TW16-QB1-MATRIX-PLACEHOLDER-R16-OPEN-CODEX-V1";

const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py",
  "src/dynasty_genius/eval/qb_validation/study_matrix.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py",
    "c00c60ab66781d45cb79d0b122f8c3916167e4f435910385f0b4e7a1d1e74d39",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/study_matrix.py",
    "1d2a6296564dac288d50a69db61b6753afb7cd25219de29f8ac442cd04fc64a1",
  ],
  [
    "scripts/run_qb1_study.py",
    "8d7d525c1f5da0fa9a7311d0d2fef72353ee63969324d27257cfbcf5c0d87c63",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "a75dbc64b1d90a5d2d505963ad8a8a50990c7834259cbfc30e497c9f14f74d17",
  ],
]);

function fail(message) {
  throw new Error(`matrix-placeholder round open refused: ${message}`);
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
    fail(`round-16 snapshot directory already exists: ${ROUND_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-16 scope ${relativePath}`);
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
  if (run.failureCounts?.["green-review:review"] !== 9) {
    fail(`review failure count changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.failureCounts?.["green-review:real-surface-qa"] !== 2) {
    fail(`real-surface failure count changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") {
    fail("the prior recorded Judge STOP ruling is absent or changed");
  }
  const green = (run.reviewRounds ?? []).filter((round) => round.phase === "green-review");
  if (
    green.length !== 15 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly fifteen closed green-review rounds indexed 1..15");
  }
  const round15 = green.at(-1);
  if (
    round15.reviewerVerdict !== null ||
    round15.churn?.closeSnapshotHash !== EXPECTED_ROUND_15_CLOSE_HASH
  ) {
    fail("round-15 review state or close snapshot changed");
  }
  const unresolved = green.flatMap((round) =>
    round.findings.filter(
      (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
    ),
  );
  const criteria = unresolved.map((finding) => finding.criterionId).sort();
  if (
    criteria.length !== 2 ||
    criteria[0] !== "R15-G1-MATRIX-PLACEHOLDER-ADMISSION" ||
    criteria[1] !== "R15-G2-WALL-CENSUS-TOTALITY"
  ) {
    fail(`unexpected unresolved blockers: ${criteria.join(", ")}`);
  }
  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "review" ||
    lastCheck?.status !== "failed" ||
    !lastCheck.evidence.includes(ROUND_15_REVIEW_SHA256)
  ) {
    fail("the failed Round-15 review receipt is absent or changed");
  }
  if (
    !run.stateRepairs?.some(
      (repair) => repair.id === "TW16-QB1-PBP-PARSE-R15-OPEN-CODEX-V1",
    )
  ) {
    fail("round-15 open repair record is absent");
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-16 snapshot directory already exists");
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const review = resolve(
    run.worktree,
    "docs/agent-ledger/evidence/2026-08-16/qb1_green_round15_review_codex_v1.md",
  );
  requireRegularFile(review, "Round-15 independent review");
  if (sha256(readFileSync(review)) !== ROUND_15_REVIEW_SHA256) {
    fail("Round-15 independent review hash changed");
  }
  const failedArtifact = resolve(
    run.worktree,
    "app/data/backtest/qb_validation/qb_validation_report.json",
  );
  requireRegularFile(failedArtifact, "last failed QB-1 artifact");
  if (sha256(readFileSync(failedArtifact)) !== FAILED_ARTIFACT_SHA256) {
    fail("last failed QB-1 artifact hash changed");
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, SCOPE);
  if (currentScopeHash !== EXPECTED_SCOPE_HASH) {
    fail(`current scope hash ${currentScopeHash} != expected ${EXPECTED_SCOPE_HASH}`);
  }
}

function buildOpenRun(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 16,
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
        "Claude applies the one shared exact provider-placeholder classifier at the matrix defensive weekly-record seam and proves all-position team-rushing totals unchanged",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: ROUND_15_REVIEW_SHA256,
      carriedFindings: [
        "R15-G1-MATRIX-PLACEHOLDER-ADMISSION",
        "R15-G2-WALL-CENSUS-TOTALITY",
      ],
      implementationBoundary: {
        classifier:
          "ONE shared classifier used by label and matrix consumers: missing player_id AND missing position AND validated exact zero across all 17 D2 inputs",
        names: "audit evidence only",
        matrixPlacement:
          "defensive weekly records immediately before _validated_weekly_row",
        poolUntouchedThroughMatrixEntry: true,
        frameUntouchedThroughMatrixGates: true,
        failClosedNearMisses: true,
        allPositionTeamRushingTotalsUnchanged: true,
        inputMutation: false,
        registeredValueChange: false,
      },
      priorCensusDisposition:
        "one observed next wall only; the Round-15 last-wall claim is not evidence and must not be repeated",
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR only",
      registeredReadoutRecipient: "David for separate ruling",
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
    "David-authorized QB-1 shared matrix-placeholder implementation round is open; fresh registered rerun fires only after Codex explicit CLEAR; H2 remains UNDER TEST";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 16 },
      boundedPurpose: "one shared placeholder classifier at matrix weekly records",
      carriedBlockers: [
        "R15-G1-MATRIX-PLACEHOLDER-ADMISSION",
        "R15-G2-WALL-CENSUS-TOTALITY",
      ],
      implementationBoundary: {
        files: [...SCOPE],
        oneSharedClassifier: true,
        exactPredicate:
          "missing player_id AND missing position AND validated exact zero across all 17 D2 inputs",
        matrixDefensiveRecordsOnly: true,
        poolAndFrameGatesUntouched: true,
        nearMissesFailClosed: true,
        proveAllPositionTeamRushingTotalsUnchanged: true,
      },
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
    round16: {
      phase: "green-review",
      index: 16,
      scope: SCOPE,
      openSnapshotHash: prospectiveOpenHash,
      authority: DAVID_WORD,
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR only",
    },
    executionHeldPendingCodexClear: true,
    h2Status: "UNDER TEST",
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
      fail("worktree changed while the round-16 open snapshot was being taken");
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
