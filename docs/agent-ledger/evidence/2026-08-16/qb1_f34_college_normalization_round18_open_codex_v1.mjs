#!/usr/bin/env node

/**
 * Open the conditionally authorized QB-1 F34 college-normalization Round 18.
 * Dry-run is the default; the sole mutating form adds `--apply`.
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
const ROUND_ROOT = join(dirname(STATE_PATH), "snapshots", "green-review-18");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 110;
const EXPECTED_REASON =
  "David-authorized diagnostic-only QB-1 continuation: one read-only F34 draft-join TRIAGE replay over frozen admitted study QBs; no composition, repair, implementation round, or rerun until Codex registration read";
const EXPECTED_SCOPE_HASH =
  "c6e9dc22c5dd11730976311175d703a37fcd53a7f104784641e7ebc0b25922bd";
const DIAGNOSTIC_SCRIPT_SHA256 =
  "af612c030c211b79825314a4b51264c939dc098d5bd2a3cdda5c3451475ace3d";
const DIAGNOSTIC_OUTPUT_SHA256 =
  "404fefce1d3e74c02857291f29935d1e0c7621d646373a6b4a4a58efd2c31a64";
const REGISTRATION_READ_SHA256 =
  "58509f3cccc9cf7da9e776633553c4a765b4cae78eff2a2362265ac7a9e3bfe3";
const FAILED_REPORT_SHA256 =
  "bb70130db52c4eb6a704911b7f953461400a0e10ad9ccaa9168a9365e5d35167";
const DAVID_WORD =
  "continue per your sanctioned mechanism - claude runs the read-only F34 draft-join diagnostic you specified (every affected study player-season, named resolution state and reason, match multiplicity, reconciliation to the H4 nulls, digest proofs; no composition, no repair, no rerun), you do the registration read of the measured facts, claude implements one bounded round per your read, fresh rerun only on your explicit clear - the registered readout comes back to me for my ruling";
const REPAIR_ID = "TW16-QB1-F34-COLLEGE-NORMALIZATION-R18-OPEN-CODEX-V1";

const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/identity.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/identity.py",
    "aacb56fc30df7685debae6bed890a99cf7ba818c7b73749b7bd5e58ef1acfde0",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "200c6deec425c0d2c2c57ffe7f0e904bee3a9925648df9bad589d205307eba22",
  ],
]);

const OUT_OF_SCOPE_PINS = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/study_matrix.py",
    "6c607badab90342e9f5508d09278614236be1095fd44702949910a5dca54a89d",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/ridge_lane.py",
    "02e7a980cc3295d4b0a975be98cbb59b54be4fb01c4143f80099936151b4deb0",
  ],
  [
    "scripts/run_qb1_study.py",
    "7de911cccdcb17ae0e37ca48b5816a50420dbcd0e61303f663553d381c97a798",
  ],
  ["app/data/backtest/qb_validation/qb_validation_report.json", FAILED_REPORT_SHA256],
]);

const EVIDENCE_PINS = new Map([
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_f34_triage_diagnostic_claude_v2.py",
    DIAGNOSTIC_SCRIPT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_f34_triage_diagnostic_claude_v2_output.txt",
    DIAGNOSTIC_OUTPUT_SHA256,
  ],
  [
    "docs/agent-ledger/evidence/2026-08-16/qb1_f34_college_normalization_registration_read_codex_v1.md",
    REGISTRATION_READ_SHA256,
  ],
]);

function fail(message) {
  throw new Error(`F34 college-normalization Round-18 open refused: ${message}`);
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
    run.failureCounts?.["green-review:real-surface-qa"] !== 4
  ) {
    fail(`failure history changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") fail("prior Judge STOP record changed");
  const green = (run.reviewRounds ?? []).filter((round) => round.phase === "green-review");
  if (
    green.length !== 17 ||
    green.some((round, offset) => round.index !== offset + 1 || !round.closedAt)
  ) {
    fail("expected exactly seventeen closed green-review rounds indexed 1..17");
  }
  if (green.at(-1)?.reviewerVerdict !== "CLEAR") fail("Round 17 is not closed CLEAR");
  if ((run.reviewRounds ?? []).some((round) => !round.closedAt)) {
    fail("an earlier review round remains open");
  }
  if (
    run.stateRepairs?.at(-1)?.id !==
    "TW16-QB1-F34-TRIAGE-DIAGNOSTIC-CONTINUATION-CODEX-V1"
  ) {
    fail("revision-110 diagnostic continuation record changed");
  }
  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "real-surface-qa" ||
    lastCheck?.status !== "failed" ||
    !lastCheck?.evidence?.includes(FAILED_REPORT_SHA256) ||
    !lastCheck?.evidence?.includes("draft_capital_unresolved")
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
  if (existsSync(ROUND_ROOT)) fail("green-review-18 snapshot already exists");
}

function buildOpenRun(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 18,
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
      conditionalAuthoritySatisfied:
        "Diagnostic v2 fully enumerates and reconciles the F34/H4 wall; Codex registration read classifies closed college normalization as implementation, not amendment",
      boundedPurpose:
        "implement the registered F34 college cross-check over provider school-history and closed alias formats without weakening true mismatch TRIAGE",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: REGISTRATION_READ_SHA256,
      diagnosticEvidence: {
        scriptSha256: DIAGNOSTIC_SCRIPT_SHA256,
        outputSha256: DIAGNOSTIC_OUTPUT_SHA256,
        affectedPlayerSeasonRows: 143,
        affectedPlayers: 49,
        representationOnlyTriagePlayers: 67,
        genuineFallbackConflictPlayers: 2,
      },
      implementationBoundary: {
        files: [...SCOPE],
        studySideTokenization: "split present players.college_name on literal semicolon",
        baseNormalization: "existing normalize_name applied independently per institution",
        terminalTokenAliases: { st: "state", col: "college" },
        exactAliases: {
          "n c state": "north carolina state",
          ucf: "central florida",
          "miami oh": "miami ohio",
          uab: "ala birmingham",
        },
        comparison: "exact canonical draft-institution membership in canonical study-institution set",
        fuzzyOrSubstringMatching: false,
        missingLawUnchanged: true,
        trueMismatchTriageUnchanged: true,
        resolverAndCapitalLawsOtherwiseUnchanged: true,
        registeredValuesChanged: false,
        noLastWallClaim: true,
      },
      requiredRealSurfaceProof: {
        affectedPlayersResolveDrafted: 49,
        affectedH4RowsGainAuthoritativeCapital: 143,
        allRepresentationOnlyTriageResolveDrafted: 67,
        residualTriageExactPlayers: ["00-0029857", "00-0037175"],
        residualReasons: "cross_check_conflict",
        h4GateSurvivingNullDraftCapitalRows: 0,
        frameDigestsUnchanged: true,
      },
      rerunAuthorityGranted: true,
      executionTrigger: "Codex explicit CLEAR only",
      registeredReadoutRecipient: "David for separate ruling",
    },
  });
  next.phase = "green-review";
  next.terminalState = null;
  next.reasonCodes = [];
  next.reason =
    "David-authorized bounded Round 18: exact F34 provider college normalization; fresh registered rerun only after Codex explicit CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 18 },
      boundedPurpose: "registered F34 provider college normalization",
      diagnosticScriptSha256: DIAGNOSTIC_SCRIPT_SHA256,
      diagnosticOutputSha256: DIAGNOSTIC_OUTPUT_SHA256,
      registrationReadSha256: REGISTRATION_READ_SHA256,
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

const apply = process.argv.length === 3 && process.argv[2] === "--apply";
if (process.argv.length > (apply ? 3 : 2) || (process.argv[2] && !apply)) {
  fail("usage: node qb1_f34_college_normalization_round18_open_codex_v1.mjs [--apply]");
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
        round: 18,
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
        round: 18,
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
