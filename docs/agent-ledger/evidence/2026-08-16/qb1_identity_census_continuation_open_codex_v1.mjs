#!/usr/bin/env node

/**
 * Reopen blocked QB-1 revision 102 for David's diagnostic-only continuation.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_identity_census_continuation_open_codex_v1.mjs --apply
 *
 * This deliberately does NOT open a green-review round. The implementation
 * boundary does not exist until Claude's one-pass seven-dataset identity census
 * is measured and Codex performs the requested registration read. A separate
 * revision-guarded transition may open one implementation round only if those
 * facts establish the same provider-placeholder class.
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
const EXPECTED_REVISION = 102;
const EXPECTED_CLOSE_HASH =
  "1220791a59a6a3f2a10eb010a5c68e72808777b8d21de25036b222252da64058";
const REVIEW_SHA256 =
  "332766dfbd56a478083c422368d75bcaf252f0718bd2e483e75aed2702f854d5";
const EXECUTION_RECEIPT_SHA256 =
  "852ab32edb7d8c5b53a977c1c64ac375491391d536517f406cad56652a6c099b";
const FAILED_ARTIFACT_SHA256 =
  "7ebeedb031953fd54a2a7a37d386bc52b332ec4471e4e4f67162059f1147105e";
const FAILED_STDOUT_SHA256 =
  "fe90756113cd6c84457ff907fa31a935f6c3970b18def8035e1c6236b2c2b1d5";
const REPAIR_ID = "TW16-QB1-SEVEN-DATASET-IDENTITY-CENSUS-CONTINUATION-CODEX-V1";
const DAVID_WORD =
  "open the continuation from blocked revision 102 per your sanctioned mechanism - claude runs one read-only identity census across all seven admitted datasets in one pass (results discarded unread, no repairs), you do the registration read of the measured facts, claude then implements one bounded round per your read if the walls are the same placeholder class, fresh rerun only on your explicit clear - the registered readout comes back to me for my ruling";

const DATASETS = [
  "weekly",
  "season_summary",
  "players",
  "rosters",
  "ff_playerids",
  "draft_picks",
  "pbp",
];

const PINNED_FILES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py",
    "e5cb3955142b365a9dc929e18a7ceda33f647613fc8610442a2b39fa7ca73edf",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/study_matrix.py",
    "518e4b82c79d6a9637ae5bca5b6eb0aba7b82afc212ce1d01b7fe8a69d50e389",
  ],
  [
    "scripts/run_qb1_study.py",
    "7de911cccdcb17ae0e37ca48b5816a50420dbcd0e61303f663553d381c97a798",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "7407dc6c46237d7c3a23e3f3db044f56583db5d553c793fead9486684aab36c9",
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_green_round16_review_codex_v1.md",
    REVIEW_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_round16_execution_failed_closed_receipt_codex_v1.md",
    EXECUTION_RECEIPT_SHA256,
  ],
  [
    "app/data/backtest/qb_validation/qb_validation_report.json",
    FAILED_ARTIFACT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r16_stdout_claude_v1.txt",
    FAILED_STDOUT_SHA256,
  ],
]);

function fail(message) {
  throw new Error(`identity-census continuation refused: ${message}`);
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
    run.failureCounts?.["green-review:real-surface-qa"] !== 3
  ) {
    fail(`failure counts changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") {
    fail("the prior recorded Judge STOP ruling is absent or changed");
  }

  const green = (run.reviewRounds ?? []).filter((round) => round.phase === "green-review");
  if (
    green.length !== 16 ||
    green.some((round, offset) => round.index !== offset + 1 || !round.closedAt)
  ) {
    fail("expected exactly sixteen closed green-review rounds indexed 1..16");
  }
  const round16 = green.at(-1);
  if (
    round16.reviewerVerdict !== "CLEAR" ||
    round16.churn?.closeSnapshotHash !== EXPECTED_CLOSE_HASH ||
    !round16.reviewerVerdictEvidence?.includes(REVIEW_SHA256)
  ) {
    fail("Round-16 CLEAR or close snapshot changed");
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
    !lastCheck.evidence.includes("failure_reason=stat_value_invalid") ||
    !lastCheck.evidence.includes("no registered result produced or published")
  ) {
    fail("the revision-102 failed-closed execution receipt changed");
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
    "David-authorized diagnostic-only QB-1 continuation: one read-only identity census across all seven admitted datasets; no composition, result access, repair, or implementation round until Codex registration read";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      boundedPurpose:
        "one read-only identity census across all seven admitted datasets, followed by Codex registration read",
      reopenedFrom: {
        revision: EXPECTED_REVISION,
        phase: "blocked",
        terminalState: "BLOCKED",
        failedArtifactSha256: FAILED_ARTIFACT_SHA256,
      },
      diagnosticBoundary: {
        datasets: [...DATASETS],
        oneAdmissionAndLoadPass: true,
        readOnly: true,
        identityCensusOnly: true,
        censusFactsRouteTo: "Codex for registration read",
        compositionRun: false,
        registeredStudyResultComputed: false,
        accidentalRegisteredResults: "discard unread",
        productRepairs: false,
        productCodeWrites: false,
        inputMutation: false,
        providerFetch: false,
        commit: false,
        push: false,
      },
      conditionalNextGate: {
        owner: "Codex",
        samePlaceholderClassRequired: true,
        implementationRoundOpenNow: false,
        implementationRound:
          "one separately bounded round per Codex registration read only if measured walls are the same placeholder class",
        freshRerunAuthorityGranted: true,
        executionTrigger: "Codex explicit CLEAR after independent implementation review",
        registeredReadoutRecipient: "David for separate ruling",
      },
      priorJudgeStopRuling: {
        ruling: next.judgeRuling.ruling,
        ruledAt: next.judgeRuling.ruledAt,
      },
      recordedAt: now,
    },
  ];
  next.updatedAt = now;
  return next;
}

const apply = process.argv.length === 3 && process.argv[2] === "--apply";
if (process.argv.length > (apply ? 3 : 2) || (process.argv[2] && !apply)) {
  fail("usage: node qb1_identity_census_continuation_open_codex_v1.mjs [--apply]");
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
        datasets: DATASETS,
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
