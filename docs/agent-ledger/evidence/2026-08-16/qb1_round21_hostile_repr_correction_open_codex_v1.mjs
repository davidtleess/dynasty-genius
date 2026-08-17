#!/usr/bin/env node

/**
 * Close the terminalized-but-open Round 20 and open David-authorized Round 21
 * for the single R20-G1 hostile-representation correction.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_round21_hostile_repr_correction_open_codex_v1.mjs --apply
 */

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
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

const WORKTREE = resolve(process.cwd());
const STATE_PATH = resolve(
  execFileSync("git", ["rev-parse", "--git-path", "dg-autonomy/run.json"], {
    encoding: "utf8",
  }).trim(),
);
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 128;
const EXPECTED_TERMINAL_REASON = "review failed 3 times in green-review";
const DAVID_WORD = "ok lets get it fixed and keep going";
const REVIEW_SHA256 =
  "b8dd8ae3f6789a3820f241cf05f3fdfb97c70ced90785e9912e40834df193d33";
const ROUND20_OPEN_HASH =
  "cf5062ed249249b79b86d0b2a8134cab729518fed6ac86232ae644d9b1a7bd92";
const CURRENT_SCOPE_HASH =
  "607b377acddedaa708c09a45f24ab0775f5a43aa26e65a123142655013f6b2e4";
const REPAIR_ID = "TW16-QB1-R21-HOSTILE-REPR-CORRECTION-OPEN-CODEX-V1";

const SCOPE = [
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const PINS = new Map([
  [
    "scripts/run_qb1_study.py",
    "ec19067ca428c72b7ea6852d67fb553d63fa3cb679120f8d44639e5e747e60dc",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "9661c5363b88c8a3f0b067fc3ae02cfc2e0f9465eca4b4d015ad78a094652cd1",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "3fd4144c75544e0941a913ec93c1e6d428de409742e591afd7bbe32f209ba2ab",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/inference.py",
    "63ea820185cfb4640d5796e2a81e26f171fc813dfc74d67568e43054d998cd28",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/comparisons.py",
    "7d50a0a7929770d1b94c7a8e5b2ea5051ceb307db169e9b19f62008065857c7c",
  ],
  [
    "docs/validation/2026-07-21-qb-1-study-registration.md",
    "319ab63f35c0e47a72e0a6d3f9340e49d635556f069bb940874b16221e828e02",
  ],
  [
    "docs/validation/2026-07-21-qb-1-study-registration.json",
    "eb56943a17549f268894128a9f4a7b9fe421d542bae9538f5781d9f667b13782",
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_green_round20_review_finding_codex_v1.md",
    REVIEW_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_registration_read_codex_v1.md",
    "0453ca804e2bd8ee62451e953a7762583cbdf93e9bdd677e39226207521509ac",
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_diagnostic_output_claude_v1.json",
    "37d935dd4c8d372931ad92639045b7da6b392b3a7f74c5b48c11ce45b771ce61",
  ],
  [
    "app/data/backtest/qb_validation/qb_validation_report.json",
    "0c0cd6308a14dc44a177335ddafc2876f65e2010d3ae1748e8e912e197540956",
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r19_stdout_claude_v1.txt",
    "ceb2fba7a8c18b9b48380de5037e0e8b00c09f80681bc297a23e02700109bb7f",
  ],
]);

const SNAPSHOT_ROOT = join(dirname(STATE_PATH), "snapshots");
const ROUND20_ROOT = join(SNAPSHOT_ROOT, "green-review-20");
const ROUND20_OPEN = join(ROUND20_ROOT, "open");
const ROUND20_CLOSE = join(ROUND20_ROOT, "close");
const ROUND21_ROOT = join(SNAPSHOT_ROOT, "green-review-21");
const ROUND21_OPEN = join(ROUND21_ROOT, "open");

function fail(message) {
  throw new Error(`Round-21 hostile-repr correction open refused: ${message}`);
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function requireRegularFile(path, label) {
  if (!existsSync(path) || !lstatSync(path).isFile()) {
    fail(`${label} is absent or not a regular file`);
  }
}

function scopedSnapshotHash(root) {
  const hash = createHash("sha256");
  for (const relativePath of [...SCOPE].sort()) {
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

function takeSnapshot(destination) {
  for (const relativePath of SCOPE) {
    const source = resolve(WORKTREE, relativePath);
    requireRegularFile(source, relativePath);
    const target = join(destination, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedSnapshotHash(destination);
}

function measureChurn(openDir, closeDir) {
  let output;
  try {
    output = execFileSync(
      "git",
      ["diff", "--no-index", "--numstat", openDir, closeDir],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
    );
  } catch (error) {
    if (error.status === 1 && typeof error.stdout === "string") {
      output = error.stdout;
    } else {
      fail(`churn measurement failed: ${error.message}`);
    }
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

function requireNoExecutionProcess() {
  const table = execFileSync("ps", ["-axo", "pid=,command="], {
    encoding: "utf8",
  });
  const live = table.split("\n").filter(
    (line) =>
      line.includes("scripts/run_qb1_study.py") ||
      line.includes("qb1_exclusion_row_postgreen_projection"),
  );
  if (live.length) fail(`execution-like process remains: ${live.join(" | ")}`);
}

function validatePinnedRun(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id changed: ${run.id}`);
  if (run.schemaVersion !== 3) fail(`schema version changed: ${run.schemaVersion}`);
  if (resolve(run.worktree) !== WORKTREE) fail(`worktree changed: ${run.worktree}`);
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision is ${run.revision}, expected ${EXPECTED_REVISION}`);
  }
  if (run.phase !== "blocked" || run.terminalState !== "BLOCKED") {
    fail(`state is ${run.phase}/${run.terminalState}, expected blocked/BLOCKED`);
  }
  if (run.reason !== EXPECTED_TERMINAL_REASON) fail(`reason changed: ${run.reason}`);
  if (run.checks?.at(-1)?.name !== "review" || run.checks.at(-1).status !== "failed") {
    fail("last failed-review receipt changed");
  }
  if (!run.checks.at(-1).evidence.includes(REVIEW_SHA256)) {
    fail("last failed-review receipt no longer cites the review finding");
  }

  const green = (run.reviewRounds ?? []).filter(
    (round) => round.phase === "green-review",
  );
  if (green.length !== 20 || green.some((round, index) => round.index !== index + 1)) {
    fail("expected exactly twenty indexed green-review rounds");
  }
  const round20 = green.at(-1);
  if (
    round20.closedAt !== null ||
    round20.reviewerVerdict !== null ||
    round20.churn?.openSnapshotHash !== ROUND20_OPEN_HASH ||
    JSON.stringify(round20.scope) !== JSON.stringify(SCOPE)
  ) {
    fail("Round-20 open record changed");
  }
  const blocker = round20.findings?.find(
    (finding) => finding.id === "finding-green-review-20-1",
  );
  if (
    !blocker ||
    blocker.severity !== "BLOCKER" ||
    blocker.criterionId !== "R20-G1-NAMED-FAILURE-TOTALITY" ||
    blocker.resolvedInRound !== null
  ) {
    fail("R20-G1 blocker is absent, changed, or prematurely resolved");
  }
  if (!existsSync(ROUND20_OPEN) || scopedSnapshotHash(ROUND20_OPEN) !== ROUND20_OPEN_HASH) {
    fail("script-owned Round-20 open snapshot changed");
  }
  if (existsSync(ROUND20_CLOSE)) fail("Round-20 close snapshot already exists");
  if (existsSync(ROUND21_ROOT)) fail("Round-21 snapshot directory already exists");

  for (const [relativePath, expectedHash] of PINS) {
    const path = resolve(WORKTREE, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  if (scopedSnapshotHash(WORKTREE) !== CURRENT_SCOPE_HASH) {
    fail("current two-file scope hash changed");
  }
  requireNoExecutionProcess();
}

function buildContinuation(run, closeSnapshotHash, churn, openSnapshotHash, now) {
  const next = structuredClone(run);
  const round20 = next.reviewRounds.find(
    (round) => round.phase === "green-review" && round.index === 20,
  );
  round20.closedAt = now;
  round20.churn = {
    ...churn,
    openSnapshotHash: ROUND20_OPEN_HASH,
    closeSnapshotHash,
  };
  next.reviewRounds.push({
    phase: "green-review",
    index: 21,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...SCOPE],
    findings: [],
    churn: { openSnapshotHash },
    authorization: {
      authority: "David",
      words: [DAVID_WORD],
      continuedFrom: {
        terminalRevision: EXPECTED_REVISION,
        round: 20,
        blocker: "finding-green-review-20-1",
        reviewEvidenceSha256: REVIEW_SHA256,
      },
      boundedPurpose:
        "remove representation inspection from the terminal exclusion-row adapter while preserving the Round-20 registered alignment",
      implementationBoundary: {
        files: [...SCOPE],
        seam: "_canonical_excluded_folds called only by contrast_status",
        reprOrStringificationInspectionForbidden: true,
        exactTokenInspectionOnlyWhenStructurallyReadable: true,
        readableShape: "entry Mapping and reasons list/tuple",
        unreadableShapesPassThroughUnchangedToRegisteredValidator: true,
        registeredValidatorMustRefuseMalformedShapesAs: "report_schema_invalid",
        exactInternalReason: "empty_common_pool",
        requiredCooccurringRegisteredReason: "fold_starved",
        duplicateInternalReasonRefuses: true,
        internalReasonWithoutFoldStarvedRefuses: true,
        unrelatedMetadataNeverTriggersCanonicalization: true,
        allOtherUnknownReasonsPreservedForGateRefusal: true,
        internalInferenceOutputUnchanged: true,
        publicationVocabularyAndRegistrationUnchanged: true,
        metricsInferenceStatusesAndClaimsUnchanged: true,
      },
      forbiddenFiles: [
        "src/dynasty_genius/eval/qb_validation/execution.py",
        "src/dynasty_genius/eval/qb_validation/inference.py",
        "src/dynasty_genius/eval/qb_validation/comparisons.py",
        "docs/validation/2026-07-21-qb-1-study-registration.md",
        "docs/validation/2026-07-21-qb-1-study-registration.json",
      ],
      requiredProof: {
        redFirstHostileReprRegression: true,
        hostileReprEndToEndFailureReason: "report_schema_invalid",
        executionErrorForbiddenForMalformedExclusionShape: true,
        unrelatedMetadataFalsePositiveRegression: true,
        allOriginalRound20ContractsRemainGreen: true,
        focusedCorrectionBundle: true,
        fiveFileBundle: true,
        fullSuite: true,
        scopedStaticChecks: true,
        syntheticTerminalPublication: true,
        oneFreshMetricFreeFinalCompositionProjection: true,
        mandatoryBeforeAfterDigests: true,
        resolveCarriedFindingOnlyAfterProof: true,
      },
      registeredExecutionDuringRound: false,
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR after independent Round-21 review only",
      registeredReadoutRecipient: "David for separate ruling",
      noCommitOrPush: true,
    },
  });
  next.phase = "green-review";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized bounded Round 21: close R20-G1 hostile-repr failure surface; registered exclusion alignment unchanged; one fresh rerun only after Codex explicit CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: { source: "David, given directly to Codex and Claude", words: [DAVID_WORD] },
      reopenedFrom: {
        revision: EXPECTED_REVISION,
        phase: "blocked",
        terminalState: "BLOCKED",
        reason: EXPECTED_TERMINAL_REASON,
      },
      closedRound: 20,
      openedRound: 21,
      carriedFinding: "finding-green-review-20-1",
      closeSnapshotHash,
      openSnapshotHash,
      registeredExecutionAuthorizedNow: false,
      rerunHeldPendingCodexClear: true,
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

const apply = process.argv.length === 3 && process.argv[2] === "--apply";
if (process.argv.length > (apply ? 3 : 2) || (process.argv[2] && !apply)) {
  fail("usage: node qb1_round21_hostile_repr_correction_open_codex_v1.mjs [--apply]");
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
        closeRound: 20,
        openRound: 21,
        scope: SCOPE,
        expectedScopeHash: CURRENT_SCOPE_HASH,
        carriedFinding: "finding-green-review-20-1",
        registeredExecutionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
  process.exit(0);
}

let round20CloseCreated = false;
let round21OpenCreated = false;
try {
  const closeSnapshotHash = takeSnapshot(ROUND20_CLOSE);
  round20CloseCreated = true;
  if (closeSnapshotHash !== CURRENT_SCOPE_HASH) fail("Round-20 close hash changed");
  const churn = measureChurn(ROUND20_OPEN, ROUND20_CLOSE);

  const openSnapshotHash = takeSnapshot(ROUND21_OPEN);
  round21OpenCreated = true;
  if (openSnapshotHash !== CURRENT_SCOPE_HASH) fail("Round-21 open hash changed");

  const next = buildContinuation(
    run,
    closeSnapshotHash,
    churn,
    openSnapshotHash,
    new Date().toISOString(),
  );
  const persisted = await persistRun(next, { statePath: STATE_PATH });
  process.stdout.write(
    `${JSON.stringify(
      {
        status: "applied",
        revision: persisted.revision,
        phase: persisted.phase,
        terminalState: persisted.terminalState,
        closedRound: 20,
        openedRound: 21,
        closeSnapshotHash,
        openSnapshotHash,
        churn,
        carriedFinding: "finding-green-review-20-1",
        stateRepair: REPAIR_ID,
        registeredExecutionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
} catch (error) {
  if (round21OpenCreated && existsSync(ROUND21_ROOT)) {
    rmSync(ROUND21_ROOT, { recursive: true });
  }
  if (round20CloseCreated && existsSync(ROUND20_CLOSE)) {
    rmSync(ROUND20_CLOSE, { recursive: true });
  }
  throw error;
}
