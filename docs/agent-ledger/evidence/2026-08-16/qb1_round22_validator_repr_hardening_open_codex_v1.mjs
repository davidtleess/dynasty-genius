#!/usr/bin/env node

/** Close stopped-before-GREEN Round 21 and open the measured Round-22
 * validator-detail hardening. Dry-run default; --apply mutates once. */

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
const RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 129;
const DAVID_WORD = "ok lets get it fixed and keep going";
const REGISTRATION_READ_SHA =
  "063f8453efc1b829786a1f1c3ec68a59098241fcae34aeb677aa0f97f7642453";
const R21_OPEN_HASH =
  "607b377acddedaa708c09a45f24ab0775f5a43aa26e65a123142655013f6b2e4";
const R21_CLOSE_HASH =
  "d36a430e998ddd943ebf04adb011d6d7aae5829a060d26c476ca49f21d237f83";
const R22_OPEN_HASH =
  "eaf819adf64f4e6d0a64764da007c711029d694dde221840f3b28d1f93c79015";
const REPAIR_ID = "TW16-QB1-R22-VALIDATOR-REPR-HARDENING-OPEN-CODEX-V1";

const CLOSE_SCOPE = [
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];
const OPEN_SCOPE = [
  "scripts/run_qb1_study.py",
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];
const PINS = new Map([
  [
    "scripts/run_qb1_study.py",
    "ec19067ca428c72b7ea6852d67fb553d63fa3cb679120f8d44639e5e747e60dc",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "a6a8c122754e520f42218a3364eddd965f52f455232df1cea1369041fdcb4e02",
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
    "docs/agent-ledger/evidence/2026-08-16/qb1_round21_validator_repr_registration_read_codex_v1.md",
    REGISTRATION_READ_SHA,
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
const R21_ROOT = join(SNAPSHOT_ROOT, "green-review-21");
const R21_OPEN = join(R21_ROOT, "open");
const R21_CLOSE = join(R21_ROOT, "close");
const R22_ROOT = join(SNAPSHOT_ROOT, "green-review-22");
const R22_OPEN = join(R22_ROOT, "open");

function fail(message) {
  throw new Error(`Round-22 validator hardening open refused: ${message}`);
}
function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}
function requireFile(path, label) {
  if (!existsSync(path) || !lstatSync(path).isFile()) {
    fail(`${label} is absent or not a regular file`);
  }
}
function scopedHash(root, scope) {
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
function takeSnapshot(destination, scope) {
  for (const relativePath of scope) {
    const source = resolve(WORKTREE, relativePath);
    requireFile(source, relativePath);
    const target = join(destination, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedHash(destination, scope);
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
function requireNoExecution() {
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
function validateRun(run) {
  if (run.id !== RUN_ID) fail(`run id changed: ${run.id}`);
  if (run.schemaVersion !== 3) fail(`schema changed: ${run.schemaVersion}`);
  if (resolve(run.worktree) !== WORKTREE) fail(`worktree changed: ${run.worktree}`);
  if (run.revision !== EXPECTED_REVISION) fail(`revision ${run.revision} != 129`);
  if (run.phase !== "green-review" || run.terminalState !== null) {
    fail(`state ${run.phase}/${run.terminalState} is not ACTIVE green-review`);
  }
  const green = (run.reviewRounds ?? []).filter(
    (round) => round.phase === "green-review",
  );
  if (green.length !== 21 || green.some((round, i) => round.index !== i + 1)) {
    fail("expected exactly twenty-one indexed green-review rounds");
  }
  const round21 = green.at(-1);
  if (
    round21.closedAt !== null ||
    round21.reviewerVerdict !== null ||
    JSON.stringify(round21.scope) !== JSON.stringify(CLOSE_SCOPE) ||
    round21.churn?.openSnapshotHash !== R21_OPEN_HASH
  ) {
    fail("Round-21 open record changed");
  }
  const round20 = green.find((round) => round.index === 20);
  const carried = round20?.findings?.find(
    (finding) => finding.id === "finding-green-review-20-1",
  );
  if (!carried || carried.resolvedInRound !== null) {
    fail("R20-G1 is absent or prematurely resolved");
  }
  if (!existsSync(R21_OPEN) || scopedHash(R21_OPEN, CLOSE_SCOPE) !== R21_OPEN_HASH) {
    fail("Round-21 open snapshot changed");
  }
  if (existsSync(R21_CLOSE)) fail("Round-21 close already exists");
  if (existsSync(R22_ROOT)) fail("Round-22 snapshot directory already exists");
  for (const [relativePath, expected] of PINS) {
    const path = resolve(WORKTREE, relativePath);
    requireFile(path, relativePath);
    const actual = sha256(readFileSync(path));
    if (actual !== expected) fail(`${relativePath} hash ${actual} != ${expected}`);
  }
  const currentCloseHash = scopedHash(WORKTREE, CLOSE_SCOPE);
  if (currentCloseHash !== R21_CLOSE_HASH) {
    fail(`current Round-21 close scope ${currentCloseHash} != ${R21_CLOSE_HASH}`);
  }
  const currentOpenHash = scopedHash(WORKTREE, OPEN_SCOPE);
  if (currentOpenHash !== R22_OPEN_HASH) {
    fail(`current Round-22 open scope ${currentOpenHash} != ${R22_OPEN_HASH}`);
  }
  requireNoExecution();
}

function buildNext(run, closeHash, churn, openHash, now) {
  const next = structuredClone(run);
  const round21 = next.reviewRounds.find(
    (round) => round.phase === "green-review" && round.index === 21,
  );
  const finding = {
    id: "finding-green-review-21-1",
    severity: "BLOCKER",
    criterionId: "R21-G1-VALIDATOR-DETAIL-TOTALITY",
    file: "src/dynasty_genius/eval/qb_validation/execution.py",
    summary:
      "Exclusion-row refusal eagerly formats hostile payload data, so RuntimeError escapes before report_schema_invalid exists and no terminal artifact is written",
    evidence:
      `Independent RED and registration read ${REGISTRATION_READ_SHA}; execution pin 3fd4144c; public path execution.py:2413 -> :1301`,
    fingerprint: sha256(
      Buffer.from("R21-G1|execution.py:1301|hostile-repr|artifactless"),
    ),
    recordedInRound: 21,
    resolvedInRound: null,
  };
  round21.findings.push(finding);
  round21.closedAt = now;
  round21.churn = {
    ...churn,
    openSnapshotHash: R21_OPEN_HASH,
    closeSnapshotHash: closeHash,
  };
  next.reviewRounds.push({
    phase: "green-review",
    index: 22,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...OPEN_SCOPE],
    findings: [],
    churn: { openSnapshotHash: openHash },
    authorization: {
      authority: "David",
      words: [DAVID_WORD],
      registrationClassification: "implementation, not amendment",
      registrationReadSha256: REGISTRATION_READ_SHA,
      continuedFrom: {
        round: 21,
        stoppedBeforeGreen: true,
        measuredFinding: finding.id,
        carriedFinding: "finding-green-review-20-1",
      },
      boundedPurpose:
        "complete the exclusion adapter correction and make the measured exclusion-clause refusals representation-free and terminal-total",
      implementationBoundary: {
        files: [...OPEN_SCOPE],
        adapterRule:
          "remove all repr/stringification inspection; inspect empty_common_pool only in Mapping plus list/tuple reasons; pass unreadable shapes unchanged",
        validatorRule:
          "remove payload representation only from the non-list excluded_folds and malformed exclusion-entry refusal details",
        stableStructuralDetailOnly: true,
        machineFailureReasonUnchanged: "report_schema_invalid",
        validationPredicatesUnchanged: true,
        foldFlagVocabularyUnchanged: true,
        registrationUnchanged: true,
        siblingValidatorClausesUnchanged: true,
        internalInferenceOutputUnchanged: true,
        metricsStatusesClaimsUnchanged: true,
      },
      forbiddenFiles: [
        "src/dynasty_genius/eval/qb_validation/inference.py",
        "src/dynasty_genius/eval/qb_validation/comparisons.py",
        "docs/validation/2026-07-21-qb-1-study-registration.md",
        "docs/validation/2026-07-21-qb-1-study-registration.json",
      ],
      requiredProof: {
        preserveRound21RedEvidence: true,
        hostileEntryReprEndToEndNamedFailure: "report_schema_invalid",
        hostileExcludedContainerReprNamedFailure: "report_schema_invalid",
        atomicSixKeyFailureArtifactBothPublicationPhases: true,
        executionErrorAndArtifactlessEscapeForbidden: true,
        sentinelLeakageForbidden: true,
        unrelatedMetadataFalsePositiveRegression: true,
        allRound20AndRound21ContractsGreen: true,
        focusedCorrectionBundle: true,
        fiveFileBundle: true,
        fullSuite: true,
        scopedStaticChecks: true,
        syntheticTerminalPublication: true,
        oneFreshMetricFreeFinalCompositionProjection: true,
        mandatoryBeforeAfterDigests: true,
        resolveBothCarriedFindingsOnlyAfterIndependentProof: true,
      },
      registeredExecutionDuringRound: false,
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR after independent Round-22 review only",
      registeredReadoutRecipient: "David for separate ruling",
      noCommitOrPush: true,
    },
  });
  next.phase = "green-review";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized bounded Round 22: representation-free exclusion adapter and validator refusals; rerun held for Codex CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: { source: "David, given directly to Codex", words: [DAVID_WORD] },
      closedRound: 21,
      openedRound: 22,
      measuredFinding: finding.id,
      carriedFinding: "finding-green-review-20-1",
      registrationReadSha256: REGISTRATION_READ_SHA,
      closeSnapshotHash: closeHash,
      openSnapshotHash: openHash,
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
  fail("usage: node qb1_round22_validator_repr_hardening_open_codex_v1.mjs [--apply]");
}
const run = await loadRun({ statePath: STATE_PATH });
validateRun(run);
if (!apply) {
  process.stdout.write(`${JSON.stringify({
    mode: "dry-run",
    currentRevision: run.revision,
    nextRevision: run.revision + 1,
    closeRound: 21,
    openRound: 22,
    closeScope: CLOSE_SCOPE,
    openScope: OPEN_SCOPE,
    expectedCloseHash: R21_CLOSE_HASH,
    expectedOpenHash: R22_OPEN_HASH,
    registeredExecutionAuthorizedNow: false,
  }, null, 2)}\n`);
  process.exit(0);
}

let closeCreated = false;
let openCreated = false;
try {
  const closeHash = takeSnapshot(R21_CLOSE, CLOSE_SCOPE);
  closeCreated = true;
  if (closeHash !== R21_CLOSE_HASH) fail("Round-21 close hash changed");
  const churn = measureChurn(R21_OPEN, R21_CLOSE);
  const openHash = takeSnapshot(R22_OPEN, OPEN_SCOPE);
  openCreated = true;
  if (openHash !== R22_OPEN_HASH) fail("Round-22 open hash changed");
  const next = buildNext(run, closeHash, churn, openHash, new Date().toISOString());
  const persisted = await persistRun(next, { statePath: STATE_PATH });
  process.stdout.write(`${JSON.stringify({
    status: "applied",
    revision: persisted.revision,
    phase: persisted.phase,
    terminalState: persisted.terminalState,
    closedRound: 21,
    openedRound: 22,
    closeSnapshotHash: closeHash,
    openSnapshotHash: openHash,
    churn,
    measuredFinding: "finding-green-review-21-1",
    carriedFinding: "finding-green-review-20-1",
    registeredExecutionAuthorizedNow: false,
  }, null, 2)}\n`);
} catch (error) {
  if (openCreated && existsSync(R22_ROOT)) rmSync(R22_ROOT, { recursive: true });
  if (closeCreated && existsSync(R21_CLOSE)) rmSync(R21_CLOSE, { recursive: true });
  throw error;
}
