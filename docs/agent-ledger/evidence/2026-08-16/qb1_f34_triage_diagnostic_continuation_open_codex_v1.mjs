#!/usr/bin/env node

/**
 * Reopen blocked QB-1 revision 109 for David's diagnostic-only F34 replay.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_f34_triage_diagnostic_continuation_open_codex_v1.mjs --apply
 *
 * This deliberately does NOT open Round 18. The implementation boundary does
 * not exist until Claude measures the frozen-input F34/TRIAGE facts and Codex
 * performs the requested registration read. A separate revision-guarded
 * transition may then open one bounded implementation round per that read.
 */

import { createHash } from "node:crypto";
import { existsSync, lstatSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  loadRun,
  persistRun,
} from "/Users/davidleess/dg-cockpit/autonomy/core/lib/run-state.mjs";

const STATE_PATH =
  "/Users/davidleess/dynasty-genius/.git/worktrees/dynasty-genius-product/dg-autonomy/run.json";
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 109;
const EXPECTED_CLOSE_HASH =
  "5fd53a7f5f519c5b6072e5b96b5dbdba60643364e9d1a58e9c8f147b29aa75f6";
const REVIEW_SHA256 =
  "080278735787618d974f828a26acd4034d33b4a97d51ca22a7e6e89aa2f52d1b";
const FAILED_ARTIFACT_SHA256 =
  "bb70130db52c4eb6a704911b7f953461400a0e10ad9ccaa9168a9365e5d35167";
const FAILED_STDOUT_SHA256 =
  "f303f2a6bae4ff9cf4f00ccb4cfb75b9f9e2b8fbd2108374c5aa7c1ac3972a80";
const TERMINAL_REPORT_SHA256 =
  "50d19d93adda71baa279731b058fb6d36381870c3c81d3c4a94db2e544360cb2";
const BLOCKED_RECEIPT_SHA256 =
  "02c4b87e744a8517c1ac37b39b6a3ab7ffed0fd157ceb591a158a12234885493";
const REPAIR_ID = "TW16-QB1-F34-TRIAGE-DIAGNOSTIC-CONTINUATION-CODEX-V1";
const DAVID_WORD =
  "continue per your sanctioned mechanism - claude runs the read-only F34 draft-join diagnostic you specified (every affected study player-season, named resolution state and reason, match multiplicity, reconciliation to the H4 nulls, digest proofs; no composition, no repair, no rerun), you do the registration read of the measured facts, claude implements one bounded round per your read, fresh rerun only on your explicit clear - the registered readout comes back to me for my ruling";

const PINNED_FILES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/identity.py",
    "aacb56fc30df7685debae6bed890a99cf7ba818c7b73749b7bd5e58ef1acfde0",
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
    "200c6deec425c0d2c2c57ffe7f0e904bee3a9925648df9bad589d205307eba22",
  ],
  [
    "docs/validation/2026-07-21-qb-1-study-registration.md",
    "319ab63f35c0e47a72e0a6d3f9340e49d635556f069bb940874b16221e828e02",
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_green_round17_review_codex_v1.md",
    REVIEW_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_r17_rerun_terminal_report_claude_v1.md",
    TERMINAL_REPORT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_r17_rerun_blocked_receipt_codex_v1.md",
    BLOCKED_RECEIPT_SHA256,
  ],
  [
    "app/data/backtest/qb_validation/qb_validation_report.json",
    FAILED_ARTIFACT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r17_stdout_claude_v1.txt",
    FAILED_STDOUT_SHA256,
  ],
]);

function fail(message) {
  throw new Error(`F34 diagnostic continuation refused: ${message}`);
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
    run.failureCounts?.["green-review:real-surface-qa"] !== 4
  ) {
    fail(`failure counts changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") {
    fail("the prior recorded Judge STOP ruling is absent or changed");
  }

  const green = (run.reviewRounds ?? []).filter((round) => round.phase === "green-review");
  if (
    green.length !== 17 ||
    green.some((round, offset) => round.index !== offset + 1 || !round.closedAt)
  ) {
    fail("expected exactly seventeen closed green-review rounds indexed 1..17");
  }
  const round17 = green.at(-1);
  if (
    round17.reviewerVerdict !== "CLEAR" ||
    round17.churn?.closeSnapshotHash !== EXPECTED_CLOSE_HASH ||
    !round17.reviewerVerdictEvidence?.includes(REVIEW_SHA256)
  ) {
    fail("Round-17 CLEAR or close snapshot changed");
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

  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "real-surface-qa" ||
    lastCheck?.status !== "failed" ||
    !lastCheck.evidence.includes(FAILED_ARTIFACT_SHA256) ||
    !lastCheck.evidence.includes(FAILED_STDOUT_SHA256) ||
    !lastCheck.evidence.includes("failure_reason=draft_capital_unresolved") ||
    !lastCheck.evidence.includes("no registered result produced, read, or published")
  ) {
    fail("the revision-109 failed-closed execution receipt changed");
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
    "David-authorized diagnostic-only QB-1 continuation: one read-only F34 draft-join TRIAGE replay over frozen admitted study QBs; no composition, repair, implementation round, or rerun until Codex registration read";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      boundedPurpose:
        "one read-only F34 draft-join TRIAGE diagnostic, followed by Codex registration read",
      reopenedFrom: {
        revision: EXPECTED_REVISION,
        phase: "blocked",
        terminalState: "BLOCKED",
        failedArtifactSha256: FAILED_ARTIFACT_SHA256,
        failedStdoutSha256: FAILED_STDOUT_SHA256,
      },
      diagnosticBoundary: {
        frozenAdmittedInputsOnly: true,
        studyQbsOnly: true,
        oneAdmissionAndLoadPass: true,
        readOnly: true,
        shippedF34ResolverOnly: true,
        enumerateEveryAffectedPlayerSeason: true,
        exactResolutionAndReason: true,
        candidateMatchMultiplicityAndKeys: true,
        reconcileToEveryH4NullDraftCapitalRow: true,
        beforeAfterFrameDigests: true,
        compositionRun: false,
        registeredStudyResultComputedOrRead: false,
        accidentalRegisteredResults: "discard unread",
        productRepairs: false,
        productCodeOrTestWrites: false,
        inputMutation: false,
        providerFetch: false,
        rerun: false,
        commit: false,
        push: false,
      },
      conditionalNextGate: {
        owner: "Codex",
        registrationReadRequired: true,
        implementationRoundOpenNow: false,
        implementationRound:
          "one separately revision-guarded bounded round per Codex registration read",
        freshRerunAuthorityGranted: true,
        executionTrigger: "Codex explicit CLEAR after independent implementation review",
        registeredReadoutRecipient: "David for separate ruling",
      },
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

const apply = process.argv.length === 3 && process.argv[2] === "--apply";
if (process.argv.length > (apply ? 3 : 2) || (process.argv[2] && !apply)) {
  fail("usage: node qb1_f34_triage_diagnostic_continuation_open_codex_v1.mjs [--apply]");
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
        implementationRoundOpened: false,
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
      implementationRoundOpened: false,
      executionAuthorizedNow: false,
    },
    null,
    2,
  )}\n`,
);
