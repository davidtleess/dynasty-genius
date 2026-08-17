#!/usr/bin/env node

/**
 * Reopen QB-1 revision 124 for one diagnostic-only exclusion-row projection.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_diagnostic_continuation_open_codex_v1.mjs --apply
 *
 * This opens no implementation round and authorizes no registered runner.
 * The diagnostic may replay the unchanged frozen composition once only to
 * intercept the already-measured defense-in-depth self-check, but it may
 * inspect or persist only the closed structural projection recorded below.
 */

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, lstatSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  loadRun,
  persistRun,
} from "/Users/davidleess/dg-cockpit/autonomy/core/lib/run-state.mjs";

const WORKTREE = resolve(process.cwd());
const STATE_PATH = execFileSync(
  "git",
  ["rev-parse", "--git-path", "dg-autonomy/run.json"],
  { cwd: WORKTREE, encoding: "utf8" },
).trim();
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 124;
const REPAIR_ID =
  "TW16-QB1-EXCLUSION-ROW-DIAGNOSTIC-CONTINUATION-CODEX-V1";
const DAVID_WORDS = ["ok lets continue until we get throught h5", "go"];
const REVIEW_SHA256 =
  "0cd53b74b9b18085ba1209e457f977db222225473a86d1d594474fa29890558a";
const TERMINAL_REPORT_SHA256 =
  "0f05fadd02f4a5489edbc73b4b5504318e667a6f13eb08af7596091e4679584d";
const FAILED_ARTIFACT_SHA256 =
  "0c0cd6308a14dc44a177335ddafc2876f65e2010d3ae1748e8e912e197540956";
const FAILED_STDOUT_SHA256 =
  "ceb2fba7a8c18b9b48380de5037e0e8b00c09f80681bc297a23e02700109bb7f";

const PINNED_FILES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "3fd4144c75544e0941a913ec93c1e6d428de409742e591afd7bbe32f209ba2ab",
  ],
  [
    "scripts/run_qb1_study.py",
    "898e50429fc4930ee813ce63a79126b9c2413891aba4ff2a5e3edc5edddbe790",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "26c1766c4d279ad8ce6cdb8031900116719e97a102276e58cd4b775ad7d0f938",
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
    "docs/agent-ledger/evidence/2026-08-16/qb1_green_round19_review_codex_v1.md",
    REVIEW_SHA256,
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
  throw new Error(`exclusion-row diagnostic continuation refused: ${message}`);
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function requirePinnedFile(relativePath, expectedHash) {
  const path = resolve(WORKTREE, relativePath);
  if (!existsSync(path) || !lstatSync(path).isFile()) {
    fail(`${relativePath} is absent or not a regular file`);
  }
  const actualHash = sha256(path);
  if (actualHash !== expectedHash) {
    fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
  }
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

function validateReceipts() {
  const artifact = JSON.parse(
    readFileSync(
      resolve(WORKTREE, "app/data/backtest/qb_validation/qb_validation_report.json"),
      "utf8",
    ),
  );
  const artifactKeys = Object.keys(artifact).sort();
  const expectedArtifactKeys = [
    "decision_supported",
    "failure_reason",
    "generated_at",
    "registration_hash",
    "run_status",
    "schema_version",
  ];
  if (
    JSON.stringify(artifactKeys) !== JSON.stringify(expectedArtifactKeys) ||
    artifact.run_status !== "failed" ||
    artifact.failure_reason !== "report_schema_invalid" ||
    artifact.decision_supported !== false
  ) {
    fail("the failed terminal envelope changed shape or state");
  }

  const stdout = JSON.parse(
    readFileSync(
      resolve(
        WORKTREE,
        "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r19_stdout_claude_v1.txt",
      ),
      "utf8",
    ),
  );
  const sites = stdout.failure_origin?.sites;
  if (
    stdout.run_status !== "failed" ||
    stdout.failure_reason !== "report_schema_invalid" ||
    stdout.decision_supported !== false ||
    stdout.failure_origin?.phase !== "execute" ||
    !Array.isArray(sites) ||
    sites.length !== 5 ||
    sites.at(-2)?.path !==
      "src/dynasty_genius/eval/qb_validation/execution.py" ||
    sites.at(-2)?.function !== "validate_registered_report_blocks" ||
    sites.at(-2)?.line !== 1298 ||
    sites.at(-1)?.function !== "_refuse" ||
    sites.at(-1)?.line !== 965
  ) {
    fail("the R19 failure-origin receipt changed");
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
  if (run.phase !== "blocked" || run.terminalState !== "BLOCKED") {
    fail(`state is ${run.phase}/${run.terminalState}, expected blocked/BLOCKED`);
  }
  if (run.reason !== "real-surface-qa failed 3 times in green-review") {
    fail(`terminal reason changed: ${run.reason}`);
  }

  const round19 = run.reviewRounds?.at(-1);
  if (
    round19?.index !== 19 ||
    !round19.closedAt ||
    round19.reviewerVerdict !== "CLEAR" ||
    round19.reviewerVerdictEvidence !== REVIEW_SHA256 ||
    round19.churn?.closeSnapshotHash !==
      "2d64450feffdf378c019b1d00e23faafeae770d6aa188221dc82c8d9de82c0e0"
  ) {
    fail("Round-19 durable CLEAR changed");
  }

  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "real-surface-qa" ||
    lastCheck?.status !== "failed" ||
    !lastCheck.evidence?.includes(FAILED_ARTIFACT_SHA256) ||
    !lastCheck.evidence?.includes(FAILED_STDOUT_SHA256) ||
    !lastCheck.evidence?.includes(TERMINAL_REPORT_SHA256) ||
    !lastCheck.evidence?.includes("failure_origin phase=execute") ||
    !lastCheck.evidence?.includes("grant consumed")
  ) {
    fail("the revision-124 failed execution receipt changed");
  }

  for (const [relativePath, expectedHash] of PINNED_FILES) {
    requirePinnedFile(relativePath, expectedHash);
  }
  validateReceipts();
  requireNoRunner();
}

function buildContinuation(run, now) {
  const next = structuredClone(run);
  next.phase = "verifying";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized diagnostic-only QB-1 continuation: one frozen-input composition replay intercepted at the measured exclusion-row self-check; persist shapes and vocabulary words only; no runner, repair, implementation round, or rerun until Codex registration read";
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
      boundedPurpose:
        "one read-only census of the real composed comparison excluded_folds shapes and reason vocabulary at the already-measured execution-phase self-check, followed by Codex registration read",
      reopenedFrom: {
        revision: EXPECTED_REVISION,
        phase: "blocked",
        terminalState: "BLOCKED",
        failedArtifactSha256: FAILED_ARTIFACT_SHA256,
        failedStdoutSha256: FAILED_STDOUT_SHA256,
        terminalReportSha256: TERMINAL_REPORT_SHA256,
        failurePhase: "execute",
        refusingSite:
          "src/dynasty_genius/eval/qb_validation/execution.py:1298",
      },
      diagnosticBoundary: {
        frozenLocalInputsAndReviewedCodeOnly: true,
        readOnly: true,
        exactlyOneCompositionReplay: true,
        interceptPoint:
          "scripts/run_qb1_study.py compose_study defense-in-depth call to validate_registered_report_blocks at line 1199",
        interceptionMethod:
          "diagnostic-only observer or temporary monkeypatch outside product code; project then abort before validation returns",
        allowedProjection: {
          comparisonId: "registered literal only",
          lane: "registered literal only",
          excludedFoldsContainerTypeAndLength: true,
          entryIndexAndSortedKeyNames: true,
          testSeason: "registered literal and type/predicate only",
          reasonsContainerTypeAndLength: true,
          reasonWords: "exact strings only",
          vocabularyMembership: true,
          violatedConjunctNames: true,
          aggregateStructuralCounts: true,
        },
        forbiddenReadsOrPersistence: [
          "pooled_delta",
          "paired_delta",
          "spearman values",
          "confidence intervals",
          "p-values or adjusted p-values",
          "support statuses",
          "predictions",
          "labels or player identities",
          "common-pool sizes",
          "case-panel or sensitivity values",
          "raw rejected payload outside the allowed projection",
          "failure detail or exception text",
        ],
        fullPayloadSerialization: false,
        registeredRunnerInvocation: false,
        terminalArtifactWrite: false,
        stdoutReceiptMutation: false,
        providerFetch: false,
        inputMutation: false,
        productCodeOrTestWrites: false,
        productRepair: false,
        implementationRoundOpened: false,
        registeredRerun: false,
        commit: false,
        push: false,
        accidentalBroaderOutput: "discard unread and report boundary failure",
        safeProjectionUnavailableDisposition: "diagnostic_projection_unavailable",
        beforeAfterDigestsRequired: true,
      },
      conditionalNextGate: {
        owner: "Codex",
        diagnosticEvidenceRequired: true,
        registrationReadRequired: true,
        implementationRoundOpenNow: false,
        noAutomaticVocabularyWidening: true,
        implementationRound:
          "one separately revision-guarded bounded round only after Codex classifies the measured producer/gate mismatch as implementation or amendment",
        futureFreshRerunAuthorizedByDavid: true,
        executionTrigger: "Codex explicit CLEAR after independent review",
        completedReadoutRecipient: "David for separate ruling",
      },
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

const apply = process.argv.length === 3 && process.argv[2] === "--apply";
if (process.argv.length > (apply ? 3 : 2) || (process.argv[2] && !apply)) {
  fail(
    "usage: node qb1_exclusion_row_diagnostic_continuation_open_codex_v1.mjs [--apply]",
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
        nextPhase: "verifying",
        diagnosticOnly: true,
        exactlyOneCompositionReplay: true,
        projection: "shapes and vocabulary words only",
        implementationRoundOpened: false,
        registeredRunnerAuthorizedNow: false,
        registeredRerunAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
  process.exit(0);
}

const next = buildContinuation(run, new Date().toISOString());
const persisted = await persistRun(next, { statePath: STATE_PATH });
process.stdout.write(
  `${JSON.stringify(
    {
      status: "applied",
      revision: persisted.revision,
      phase: persisted.phase,
      terminalState: persisted.terminalState,
      stateRepair: REPAIR_ID,
      diagnosticOnly: true,
      exactlyOneCompositionReplay: true,
      projection: "shapes and vocabulary words only",
      implementationRoundOpened: false,
      registeredRunnerAuthorizedNow: false,
      registeredRerunAuthorizedNow: false,
    },
    null,
    2,
  )}\n`,
);
