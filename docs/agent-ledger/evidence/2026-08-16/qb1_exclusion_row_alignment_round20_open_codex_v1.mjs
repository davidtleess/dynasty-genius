#!/usr/bin/env node

/** Open the conditionally authorized QB-1 exclusion-row alignment Round 20. */

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
const ROUND_ROOT = join(dirname(STATE_PATH), "snapshots", "green-review-20");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 125;
const EXPECTED_REASON =
  "David-authorized diagnostic-only QB-1 continuation: one frozen-input composition replay intercepted at the measured exclusion-row self-check; persist shapes and vocabulary words only; no runner, repair, implementation round, or rerun until Codex registration read";
const EXPECTED_SCOPE_HASH =
  "cf5062ed249249b79b86d0b2a8134cab729518fed6ac86232ae644d9b1a7bd92";
const REGISTRATION_READ_SHA256 =
  "0453ca804e2bd8ee62451e953a7762583cbdf93e9bdd677e39226207521509ac";
const DIAGNOSTIC_SCRIPT_SHA256 =
  "d83f5be183917e75f8e8d83f184d1e564c309d53445847941b926d7997f4550e";
const DIAGNOSTIC_OUTPUT_SHA256 =
  "37d935dd4c8d372931ad92639045b7da6b392b3a7f74c5b48c11ce45b771ce61";
const FAILED_ARTIFACT_SHA256 =
  "0c0cd6308a14dc44a177335ddafc2876f65e2010d3ae1748e8e912e197540956";
const FAILED_STDOUT_SHA256 =
  "ceb2fba7a8c18b9b48380de5037e0e8b00c09f80681bc297a23e02700109bb7f";
const TERMINAL_REPORT_SHA256 =
  "0f05fadd02f4a5489edbc73b4b5504318e667a6f13eb08af7596091e4679584d";
const DAVID_WORDS = ["ok lets continue until we get throught h5", "go"];
const REPAIR_ID = "TW16-QB1-EXCLUSION-ROW-ALIGNMENT-R20-OPEN-CODEX-V1";

const SCOPE = [
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const PINS = new Map([
  [
    "scripts/run_qb1_study.py",
    "898e50429fc4930ee813ce63a79126b9c2413891aba4ff2a5e3edc5edddbe790",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "26c1766c4d279ad8ce6cdb8031900116719e97a102276e58cd4b775ad7d0f938",
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
    "docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_diagnostic_claude_v1.py",
    DIAGNOSTIC_SCRIPT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_diagnostic_output_claude_v1.json",
    DIAGNOSTIC_OUTPUT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_registration_read_codex_v1.md",
    REGISTRATION_READ_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_r19_rerun_terminal_report_claude_v1.md",
    TERMINAL_REPORT_SHA256,
  ],
  [
    "app/data/backtest/qb_validation/qb_validation_report.json",
    FAILED_ARTIFACT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r19_stdout_claude_v1.txt",
    FAILED_STDOUT_SHA256,
  ],
]);

function fail(message) {
  throw new Error(`exclusion-row alignment Round-20 open refused: ${message}`);
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

function takeScopedSnapshot() {
  if (existsSync(ROUND_ROOT)) fail(`snapshot directory already exists: ${ROUND_ROOT}`);
  for (const relativePath of SCOPE) {
    const source = resolve(WORKTREE, relativePath);
    requireRegularFile(source, relativePath);
    const target = join(ROUND_OPEN, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedSnapshotHash(ROUND_OPEN, SCOPE);
}

function requireNoRunner() {
  const processTable = execFileSync("ps", ["-axo", "pid=,command="], {
    encoding: "utf8",
  });
  const live = processTable
    .split("\n")
    .filter(
      (line) =>
        line.includes("scripts/run_qb1_study.py") ||
        line.includes("qb1_registered_rerun_r19_stdout_claude_v1.txt"),
    );
  if (live.length) fail(`runner-like process remains: ${live.join(" | ")}`);
}

function validateDiagnostic() {
  const output = JSON.parse(
    readFileSync(
      resolve(
        WORKTREE,
        "docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_diagnostic_output_claude_v1.json",
      ),
      "utf8",
    ),
  );
  const totals = output.projection?.totals;
  const rows = output.projection?.rows;
  if (
    output.aborted_before_validator_returned !== true ||
    output.intercept_fired !== true ||
    output.hashes_before_equal_after !== true ||
    totals?.comparison_rows !== 14 ||
    totals?.exclusion_entries !== 12 ||
    totals?.violating_entries !== 12 ||
    totals?.violations_by_conjunct?.reason_word_outside_vocabulary !== 12 ||
    !Array.isArray(rows)
  ) {
    fail("diagnostic totals or boundary proof changed");
  }
  const modelRows = rows.filter((row) => row.lane === "model");
  const h5Rows = rows.filter((row) => row.lane === "h5");
  if (
    modelRows.length !== 10 ||
    modelRows.some((row) => row.excluded_length !== 0) ||
    h5Rows.length !== 4 ||
    h5Rows.some((row) => row.excluded_length !== 3)
  ) {
    fail("diagnostic comparison topology changed");
  }
  for (const entry of h5Rows.flatMap((row) => row.entries)) {
    const words = entry.reasons.map((reason) => reason.word);
    if (
      JSON.stringify(words) !==
        JSON.stringify([
          "empty_common_pool",
          "fold_starved",
          "degenerate_input",
        ]) ||
      JSON.stringify(entry.violated_conjuncts) !==
        JSON.stringify(["reason_word_outside_vocabulary"])
    ) {
      fail("diagnostic reason projection changed");
    }
  }
}

function validatePinnedRun(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id is ${run.id ?? "missing"}`);
  if (run.schemaVersion !== 3) {
    fail(`schemaVersion is ${run.schemaVersion ?? "missing"}`);
  }
  if (resolve(run.worktree) !== WORKTREE) {
    fail(`worktree is ${run.worktree ?? "missing"}, expected ${WORKTREE}`);
  }
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision is ${run.revision ?? "missing"}, expected ${EXPECTED_REVISION}`);
  }
  if (run.phase !== "verifying" || run.terminalState !== null) {
    fail(`state is ${run.phase}/${run.terminalState}, expected verifying/null`);
  }
  if (run.reason !== EXPECTED_REASON) fail(`reason changed: ${run.reason}`);

  const rounds = (run.reviewRounds ?? []).filter(
    (round) => round.phase === "green-review",
  );
  if (
    rounds.length !== 19 ||
    rounds.some((round, offset) => round.index !== offset + 1 || !round.closedAt)
  ) {
    fail("expected exactly nineteen closed review rounds indexed 1..19");
  }
  if (
    rounds.at(-1)?.reviewerVerdict !== "CLEAR" ||
    rounds.at(-1)?.reviewerVerdictEvidence !==
      "0cd53b74b9b18085ba1209e457f977db222225473a86d1d594474fa29890558a"
  ) {
    fail("Round-19 CLEAR changed");
  }
  const lastRepair = run.stateRepairs?.at(-1);
  if (
    lastRepair?.id !==
      "TW16-QB1-EXCLUSION-ROW-DIAGNOSTIC-CONTINUATION-CODEX-V1" ||
    lastRepair?.conditionalNextGate?.registrationReadRequired !== true ||
    lastRepair?.conditionalNextGate?.noAutomaticVocabularyWidening !== true
  ) {
    fail("revision-125 diagnostic continuation record changed");
  }
  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "real-surface-qa" ||
    lastCheck?.status !== "failed" ||
    !lastCheck.evidence?.includes(FAILED_ARTIFACT_SHA256) ||
    !lastCheck.evidence?.includes(FAILED_STDOUT_SHA256) ||
    !lastCheck.evidence?.includes("grant consumed")
  ) {
    fail("last failed real-surface receipt changed");
  }

  for (const [relativePath, expectedHash] of PINS) {
    const path = resolve(WORKTREE, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  validateDiagnostic();
  requireNoRunner();
  const currentScopeHash = scopedSnapshotHash(WORKTREE, SCOPE);
  if (currentScopeHash !== EXPECTED_SCOPE_HASH) {
    fail(`current scope hash ${currentScopeHash} != ${EXPECTED_SCOPE_HASH}`);
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-20 snapshot already exists");
}

function buildOpenRun(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 20,
    openedAt: now,
    closedAt: null,
    reviewerVerdict: null,
    reviewerVerdictEvidence: null,
    scope: [...SCOPE],
    findings: [],
    churn: { openSnapshotHash },
    authorization: {
      authority: "David",
      words: [...DAVID_WORDS],
      conditionalAuthoritySatisfied:
        "Revision-125 diagnostic measured exactly 12 H5 exclusion rows whose sole failed conjunct is the unregistered internal reason empty_common_pool; Codex registration read classifies terminal-adapter canonicalization as implementation, not amendment",
      boundedPurpose:
        "canonicalize the internal empty_common_pool diagnostic to its already-cooccurring registered terminal state fold_starved at the report adapter only",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: REGISTRATION_READ_SHA256,
      diagnosticEvidence: {
        scriptSha256: DIAGNOSTIC_SCRIPT_SHA256,
        outputSha256: DIAGNOSTIC_OUTPUT_SHA256,
        comparisonRows: 14,
        exclusionEntries: 12,
        violatingEntries: 12,
        soleFailedConjunct: "reason_word_outside_vocabulary",
        soleUnregisteredReason: "empty_common_pool",
        affectedLane: "h5",
      },
      implementationBoundary: {
        files: [...SCOPE],
        seam: "contrast_status terminal-report adapter",
        removeOnlyExactInternalReason: "empty_common_pool",
        requiredCooccurringRegisteredReason: "fold_starved",
        duplicateInternalReasonRefuses: true,
        internalReasonWithoutFoldStarvedRefuses: true,
        otherUnknownReasonsPreservedForGateRefusal: true,
        registeredReasonOrderAndMetadataPreserved: true,
        noneAndEmptyCollectionsPreserved: true,
        internalInferenceOutputUnchanged: true,
        publicationVocabularyUnchanged: true,
        registrationUnchanged: true,
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
        redFirst: true,
        measuredTwelveEntryShape: true,
        missingFoldStarvedRefusal: true,
        duplicateInternalReasonRefusal: true,
        unrelatedUnknownReasonStillRejected: true,
        registeredOrderAndMetadataPreserved: true,
        noneAndEmptyPreserved: true,
        losslessInternalInferenceCarried: true,
        metricStatusAndDecisionSupportedEquality: true,
        focusedCorrectionBundle: true,
        fiveFileBundle: true,
        scopedStaticChecks: true,
        syntheticTerminalPublication: true,
        oneMetricFreeFinalCompositionProjection: true,
      },
      finalProjectionBoundary: {
        outsideRegisteredRunner: true,
        abortAtValidationSeam: true,
        shapesAndVocabularyWordsOnly: true,
        metricsOrPayloadValuesPersisted: false,
        beforeAfterDigestsRequired: true,
      },
      registeredExecutionDuringRound: false,
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR after independent Round-20 review only",
      registeredReadoutRecipient: "David for separate ruling",
      noCommitOrPush: true,
    },
  });
  next.phase = "green-review";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized bounded Round 20: terminal-report exclusion-row adapter alignment; internal inference and registered publication vocabulary unchanged; fresh rerun only after Codex explicit CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: {
        source: "David, given directly to Claude",
        words: [...DAVID_WORDS],
        boundedInterpretation:
          "continue the staged fail-closed loop through H5; Codex gates remain intact; no commit or push; completed readout returns untouched to David",
      },
      openedRound: { phase: "green-review", index: 20 },
      boundedPurpose: "terminal-report exclusion-row adapter alignment",
      diagnosticScriptSha256: DIAGNOSTIC_SCRIPT_SHA256,
      diagnosticOutputSha256: DIAGNOSTIC_OUTPUT_SHA256,
      registrationReadSha256: REGISTRATION_READ_SHA256,
      openSnapshotHash,
      registrationAndGateVocabularyHeld: true,
      internalInferenceHeld: true,
      rerunAuthorityGranted: true,
      executionHeldPendingCodexClear: true,
      registeredReadoutRecipient: "David for separate ruling",
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

const apply = process.argv.length === 3 && process.argv[2] === "--apply";
if (process.argv.length > (apply ? 3 : 2) || (process.argv[2] && !apply)) {
  fail(
    "usage: node qb1_exclusion_row_alignment_round20_open_codex_v1.mjs [--apply]",
  );
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
        round: 20,
        scope: SCOPE,
        expectedOpenSnapshotHash: EXPECTED_SCOPE_HASH,
        classification: "implementation, not amendment",
        registeredExecutionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
  process.exit(0);
}

let snapshotCreated = false;
try {
  const openSnapshotHash = takeScopedSnapshot();
  snapshotCreated = true;
  if (openSnapshotHash !== EXPECTED_SCOPE_HASH) {
    fail(`open snapshot hash ${openSnapshotHash} != ${EXPECTED_SCOPE_HASH}`);
  }
  const next = buildOpenRun(run, openSnapshotHash, new Date().toISOString());
  const persisted = await persistRun(next, { statePath: STATE_PATH });
  process.stdout.write(
    `${JSON.stringify(
      {
        status: "applied",
        revision: persisted.revision,
        phase: persisted.phase,
        round: 20,
        openSnapshotHash,
        stateRepair: REPAIR_ID,
        registeredExecutionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
} catch (error) {
  if (snapshotCreated && existsSync(ROUND_ROOT)) {
    rmSync(ROUND_ROOT, { recursive: true });
  }
  throw error;
}
