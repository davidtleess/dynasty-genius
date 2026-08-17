#!/usr/bin/env node

/**
 * Open the conditionally authorized QB-1 report-schema observability Round 19.
 * Dry-run is the default; the sole mutating form adds `--apply`.
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

const STATE_PATH = resolve(
  execFileSync("git", ["rev-parse", "--git-path", "dg-autonomy/run.json"], {
    encoding: "utf8",
  }).trim(),
);
const ROUND_ROOT = join(dirname(STATE_PATH), "snapshots", "green-review-19");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 119;
const EXPECTED_REASON =
  "David-authorized diagnostic-only QB-1 continuation: identify the report-schema refusal from durable rejected-payload evidence if available; no composition, repair, implementation round, or rerun until Codex registration read";
const EXPECTED_SCOPE_HASH =
  "9b6c656d7bd98948799810d363f1daeed7504116f1c5cf8a90b0f9c167129abf";
const DIAGNOSTIC_SHA256 =
  "1fee12534ceab241972289dfbf7baaf31e7ff09b943ae3671e88b803d590b734";
const REGISTRATION_READ_SHA256 =
  "86bace1163a61af40dae58bf6ffedda7ca24074f2ac23812332b66530ca0ba04";
const FAILED_REPORT_SHA256 =
  "80d060195858da20dfa3b56a35bb6db929e60a46b1e7f53bc15500da8b9c4e62";
const FAILED_STDOUT_SHA256 =
  "ecc7b05d3ca3778a825c8ebfef846d2e0569d52bd8fd17d4a23bc7d5b3930311";
const DAVID_WORDS = ["ok lets continue until we get throught h5", "go"];
const REPAIR_ID =
  "TW16-QB1-REPORT-SCHEMA-OBSERVABILITY-R19-OPEN-CODEX-V1";

const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
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
]);

const OUT_OF_SCOPE_PINS = new Map([
  [
    "docs/validation/2026-07-21-qb-1-study-registration.md",
    "319ab63f35c0e47a72e0a6d3f9340e49d635556f069bb940874b16221e828e02",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/study_matrix.py",
    "6c607badab90342e9f5508d09278614236be1095fd44702949910a5dca54a89d",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py",
    "e5cb3955142b365a9dc929e18a7ceda33f647613fc8610442a2b39fa7ca73edf",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/identity.py",
    "7cf4173732ca13a47e224b470e104243de5a15dcfcd90b0a456b4f96537c4d43",
  ],
  ["app/data/backtest/qb_validation/qb_validation_report.json", FAILED_REPORT_SHA256],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r18_stdout_claude_v1.txt",
    FAILED_STDOUT_SHA256,
  ],
]);

const EVIDENCE_PINS = new Map([
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_report_schema_diagnostic_claude_v1.md",
    DIAGNOSTIC_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_report_schema_observability_registration_read_codex_v1.md",
    REGISTRATION_READ_SHA256,
  ],
]);

function fail(message) {
  throw new Error(`report-schema observability Round-19 open refused: ${message}`);
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

function takeScopedSnapshot(worktree) {
  if (existsSync(ROUND_ROOT)) fail(`snapshot directory already exists: ${ROUND_ROOT}`);
  for (const relativePath of SCOPE) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, relativePath);
    const target = join(ROUND_OPEN, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(source, target);
  }
  return scopedSnapshotHash(ROUND_OPEN, SCOPE);
}

function validatePinnedRun(run) {
  if (run.id !== TARGET_RUN_ID) fail(`run id is ${run.id ?? "missing"}`);
  if (run.schemaVersion !== 3) fail(`schemaVersion is ${run.schemaVersion ?? "missing"}`);
  if (run.revision !== EXPECTED_REVISION) {
    fail(`revision is ${run.revision ?? "missing"}, expected ${EXPECTED_REVISION}`);
  }
  if (run.phase !== "verifying" || run.terminalState !== null) {
    fail(`state is ${run.phase}/${run.terminalState}, expected verifying/null`);
  }
  if (run.reason !== EXPECTED_REASON) fail(`reason changed: ${run.reason ?? "missing"}`);
  if (
    run.failureCounts?.["green-review:review"] !== 9 ||
    run.failureCounts?.["green-review:real-surface-qa"] !== 5
  ) {
    fail(`failure history changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") fail("prior Judge STOP record changed");
  const green = (run.reviewRounds ?? []).filter((round) => round.phase === "green-review");
  if (
    green.length !== 18 ||
    green.some((round, offset) => round.index !== offset + 1 || !round.closedAt)
  ) {
    fail("expected exactly eighteen closed green-review rounds indexed 1..18");
  }
  if (green.at(-1)?.reviewerVerdict !== "CLEAR") fail("Round 18 is not closed CLEAR");
  if ((run.reviewRounds ?? []).some((round) => !round.closedAt)) {
    fail("an earlier review round remains open");
  }
  const lastRepair = run.stateRepairs?.at(-1);
  if (
    lastRepair?.id !==
      "TW16-QB1-REPORT-SCHEMA-DIAGNOSTIC-CONTINUATION-CODEX-V1" ||
    lastRepair?.conditionalNextGate?.registrationReadRequired !== true ||
    lastRepair?.conditionalNextGate?.futureFreshRerunAuthorizedByDavid !== true
  ) {
    fail("revision-119 diagnostic continuation record changed");
  }
  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "real-surface-qa" ||
    lastCheck?.status !== "failed" ||
    !lastCheck?.evidence?.includes(FAILED_REPORT_SHA256) ||
    !lastCheck?.evidence?.includes("report_schema_invalid")
  ) {
    fail("last failed real-surface receipt changed");
  }
  for (const pins of [EXPECTED_SCOPE_HASHES, OUT_OF_SCOPE_PINS, EVIDENCE_PINS]) {
    for (const [relativePath, expectedHash] of pins) {
      const path = resolve(run.worktree, relativePath);
      requireRegularFile(path, relativePath);
      const actualHash = sha256(readFileSync(path));
      if (actualHash !== expectedHash) {
        fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
      }
    }
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, SCOPE);
  if (currentScopeHash !== EXPECTED_SCOPE_HASH) {
    fail(`current scope hash ${currentScopeHash} != ${EXPECTED_SCOPE_HASH}`);
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-19 snapshot already exists");
}

function buildOpenRun(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 19,
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
        "Revision-119 read-only diagnostic proved the rejected payload and clause detail are not durable; Codex registration read classifies closed non-metric failure-origin observability as implementation, not amendment",
      boundedPurpose:
        "surface the publication catch phase and repository-relative traceback sites in failed CLI stdout without persisting raw detail, payload, values, or exception text",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: REGISTRATION_READ_SHA256,
      diagnosticEvidence: {
        disposition: "diagnostic_payload_unavailable",
        evidenceSha256: DIAGNOSTIC_SHA256,
        failedReportSha256: FAILED_REPORT_SHA256,
        failedStdoutSha256: FAILED_STDOUT_SHA256,
        exactClauseMeasured: false,
        erasureSiteMeasured: true,
      },
      implementationBoundary: {
        files: [...SCOPE],
        failedTerminalReportKeysUnchanged: [
          "schema_version",
          "generated_at",
          "registration_hash",
          "run_status",
          "failure_reason",
          "decision_supported",
        ],
        stdoutFailureDiagnosticOnly: true,
        failurePhases: ["execute", "publication_gate"],
        siteKeys: ["path", "function", "line"],
        repoRelativeTracebackFramesOnly: true,
        rawFailureDetailForbidden: true,
        rejectedPayloadForbidden: true,
        metricOrComparisonValuesForbidden: true,
        exceptionMessagesForbidden: true,
        localRepresentationsForbidden: true,
        contentDerivedDigestForbidden: true,
        diagnosticSidecarForbidden: true,
        successfulSurfaceUnchanged: true,
        observerFailureCannotSuppressTerminalArtifact: true,
        processControlSemanticsUnchanged: true,
        registeredValuesChanged: false,
        noLastWallClaim: true,
      },
      requiredRealSurfaceProof: {
        redFirst: true,
        focusedCorrectionBundle: true,
        cliSyntheticExecuteCatch: true,
        cliSyntheticPublicationGateCatch: true,
        helperCallerAndOriginTrace: true,
        sentinelNonDisclosure: true,
        ordinaryExceptionNonDisclosure: true,
        observerFailureStillPublishes: true,
        successSurfaceUnchanged: true,
        absoluteAndTraversalPathsAbsent: true,
        registeredCompositionDuringRound: false,
      },
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR after independent Round-19 review only",
      registeredReadoutRecipient: "David for separate ruling",
    },
  });
  next.phase = "green-review";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized bounded Round 19: metric-free report-schema failure-origin observability; failed terminal report unchanged; fresh registered rerun only after Codex explicit CLEAR";
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
      openedRound: { phase: "green-review", index: 19 },
      boundedPurpose: "metric-free report-schema failure-origin observability",
      diagnosticDisposition: "diagnostic_payload_unavailable",
      diagnosticEvidenceSha256: DIAGNOSTIC_SHA256,
      registrationReadSha256: REGISTRATION_READ_SHA256,
      openSnapshotHash,
      failedTerminalReportSchemaHeld: true,
      rawFailureDetailHeld: true,
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
    "usage: node qb1_report_schema_observability_round19_open_codex_v1.mjs [--apply]",
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
        round: 19,
        scope: SCOPE,
        expectedOpenSnapshotHash: EXPECTED_SCOPE_HASH,
        executionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
  process.exit(0);
}

let snapshotCreated = false;
try {
  const openSnapshotHash = takeScopedSnapshot(run.worktree);
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
        round: 19,
        openSnapshotHash,
        stateRepair: REPAIR_ID,
        executionAuthorizedNow: false,
      },
      null,
      2,
    )}\n`,
  );
} catch (error) {
  if (snapshotCreated && existsSync(ROUND_ROOT)) rmSync(ROUND_ROOT, { recursive: true });
  throw error;
}
