#!/usr/bin/env node

/**
 * Reopen blocked QB-1 revision 118 for a diagnostic-only report-schema read.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_report_schema_diagnostic_continuation_open_codex_v1.mjs --apply
 *
 * This opens no implementation round and authorizes no composition or runner
 * invocation. Claude first determines whether the rejected real payload or a
 * durable clause-detail artifact survived the failed process. If neither did,
 * the diagnostic reports `diagnostic_payload_unavailable`; it must not recreate
 * the payload by running the composition again.
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
const EXPECTED_REVISION = 118;
const EXPECTED_CLOSE_HASH =
  "e0ad5565ec19124e38bae5850ec0235bca5e31880fcc9539b659aa405eeae7dc";
const REVIEW_SHA256 =
  "eeba301f1e89f3db0a4faef6587dbd3db88c6fe729ac5d7d360660d34891d9a7";
const FAILED_ARTIFACT_SHA256 =
  "80d060195858da20dfa3b56a35bb6db929e60a46b1e7f53bc15500da8b9c4e62";
const FAILED_STDOUT_SHA256 =
  "ecc7b05d3ca3778a825c8ebfef846d2e0569d52bd8fd17d4a23bc7d5b3930311";
const TERMINAL_REPORT_SHA256 =
  "46211e9e2d829c6de3ad8be9a7ac0486d63e8bb107c4ab7ee3d82ed1bd1fd8b0";
const REPAIR_ID =
  "TW16-QB1-REPORT-SCHEMA-DIAGNOSTIC-CONTINUATION-CODEX-V1";
const DAVID_WORDS = ["ok lets continue until we get throught h5", "go"];

const PINNED_FILES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/identity.py",
    "7cf4173732ca13a47e224b470e104243de5a15dcfcd90b0a456b4f96537c4d43",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/study_matrix.py",
    "6c607badab90342e9f5508d09278614236be1095fd44702949910a5dca54a89d",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/ridge_lane.py",
    "02e7a980cc3295d4b0a975be98cbb59b54be4fb01c4143f80099936151b4deb0",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py",
    "e5cb3955142b365a9dc929e18a7ceda33f647613fc8610442a2b39fa7ca73edf",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "12df03a0258c62f375675cfa7b068ba4564db83e2474da29959ef1537831e3e8",
  ],
  [
    "scripts/run_qb1_study.py",
    "7de911cccdcb17ae0e37ca48b5816a50420dbcd0e61303f663553d381c97a798",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "5b2ae90833f5a83c9bd05677fef5edadd07b7aa8ebcf93d8b4c78b78ae1a0086",
  ],
  [
    "docs/validation/2026-07-21-qb-1-study-registration.md",
    "319ab63f35c0e47a72e0a6d3f9340e49d635556f069bb940874b16221e828e02",
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_green_round18_review_codex_v1.md",
    REVIEW_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_r18_rerun_terminal_report_claude_v1.md",
    TERMINAL_REPORT_SHA256,
  ],
  [
    "app/data/backtest/qb_validation/qb_validation_report.json",
    FAILED_ARTIFACT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r18_stdout_claude_v1.txt",
    FAILED_STDOUT_SHA256,
  ],
]);

function fail(message) {
  throw new Error(`report-schema diagnostic continuation refused: ${message}`);
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function requirePinnedFile(worktree, relativePath, expectedHash) {
  const path = resolve(worktree, relativePath);
  if (!existsSync(path) || !lstatSync(path).isFile()) {
    fail(`${relativePath} is absent or not a regular file`);
  }
  const actualHash = sha256(path);
  if (actualHash !== expectedHash) {
    fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
  }
}

function validatePinnedRun(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id is ${run.id ?? "missing"}`);
  if (run.schemaVersion !== 3) fail(`schemaVersion is ${run.schemaVersion ?? "missing"}`);
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
  if (
    run.failureCounts?.["green-review:review"] !== 9 ||
    run.failureCounts?.["green-review:real-surface-qa"] !== 5
  ) {
    fail(`failure counts changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") {
    fail("the prior recorded Judge STOP ruling is absent or changed");
  }

  const green = (run.reviewRounds ?? []).filter(
    (round) => round.phase === "green-review",
  );
  if (
    green.length !== 18 ||
    green.some((round, offset) => round.index !== offset + 1 || !round.closedAt)
  ) {
    fail("expected exactly eighteen closed green-review rounds indexed 1..18");
  }
  const round18 = green.at(-1);
  if (
    round18.reviewerVerdict !== "CLEAR" ||
    round18.churn?.closeSnapshotHash !== EXPECTED_CLOSE_HASH ||
    !round18.reviewerVerdictEvidence?.includes(REVIEW_SHA256)
  ) {
    fail("Round-18 CLEAR or close snapshot changed");
  }
  const unresolved = green.flatMap((round) =>
    (round.findings ?? []).filter(
      (finding) =>
        finding.severity === "BLOCKER" && finding.resolvedInRound == null,
    ),
  );
  if (unresolved.length !== 0) {
    fail(`unexpected unresolved review BLOCKERs: ${unresolved.map((f) => f.id).join(", ")}`);
  }
  if (
    run.stateRepairs?.at(-1)?.id !==
    "TW16-QB1-F34-COLLEGE-NORMALIZATION-R18-OPEN-CODEX-V1"
  ) {
    fail("Round-18 opening repair record changed");
  }

  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "real-surface-qa" ||
    lastCheck?.status !== "failed" ||
    !lastCheck.evidence?.includes(FAILED_ARTIFACT_SHA256) ||
    !lastCheck.evidence?.includes(FAILED_STDOUT_SHA256) ||
    !lastCheck.evidence?.includes(TERMINAL_REPORT_SHA256) ||
    !lastCheck.evidence?.includes("failure_reason=report_schema_invalid") ||
    !lastCheck.evidence?.includes("no registered result produced, read, or published")
  ) {
    fail("the revision-118 failed-closed execution receipt changed");
  }
  for (const [relativePath, expectedHash] of PINNED_FILES) {
    requirePinnedFile(run.worktree, relativePath, expectedHash);
  }
}

function buildContinuation(run, now) {
  const next = structuredClone(run);
  next.phase = "verifying";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized diagnostic-only QB-1 continuation: identify the report-schema refusal from durable rejected-payload evidence if available; no composition, repair, implementation round, or rerun until Codex registration read";
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
        "one read-only diagnostic of the Round-18 report_schema_invalid publication refusal, followed by Codex registration read",
      reopenedFrom: {
        revision: EXPECTED_REVISION,
        phase: "blocked",
        terminalState: "BLOCKED",
        failedArtifactSha256: FAILED_ARTIFACT_SHA256,
        failedStdoutSha256: FAILED_STDOUT_SHA256,
        terminalReportSha256: TERMINAL_REPORT_SHA256,
      },
      diagnosticBoundary: {
        frozenArtifactsAndCodeOnly: true,
        readOnly: true,
        publicationPathOnly: true,
        enumerateDurableRejectedPayloadOrClauseDetailArtifacts: true,
        useShippedValidatorOnlyIfRejectedPayloadIsAlreadyDurable: true,
        identifyExactNamedSchemaClauseIfMeasurable: true,
        payloadUnavailableDisposition: "diagnostic_payload_unavailable",
        sourceInspectionMayProveInformationErasure: true,
        runnerInvocation: false,
        compositionInvocation: false,
        foldsModelFitInferenceOrComparisonInvocation: false,
        registeredComparisonValuesReadOrPublished: false,
        accidentalRegisteredResults: "discard unread",
        reportArtifactMutation: false,
        stdoutReceiptMutation: false,
        productRepairs: false,
        productCodeOrTestWrites: false,
        inputMutation: false,
        providerFetch: false,
        rerun: false,
        commit: false,
        push: false,
        beforeAfterArtifactDigestsRequired: true,
      },
      conditionalNextGate: {
        owner: "Codex",
        diagnosticEvidenceRequired: true,
        registrationReadRequired: true,
        implementationRoundOpenNow: false,
        implementationRound:
          "one separately revision-guarded bounded round only after Codex classifies the measured clause or diagnostic unavailability",
        futureFreshRerunAuthorizedByDavid: true,
        executionTrigger: "Codex explicit CLEAR after independent implementation review",
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
    "usage: node qb1_report_schema_diagnostic_continuation_open_codex_v1.mjs [--apply]",
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
        payloadUnavailableDisposition: "diagnostic_payload_unavailable",
        implementationRoundOpened: false,
        compositionAuthorizedNow: false,
        executionAuthorizedNow: false,
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
      implementationRoundOpened: false,
      compositionAuthorizedNow: false,
      executionAuthorizedNow: false,
    },
    null,
    2,
  )}\n`,
);
