#!/usr/bin/env node

/**
 * Open David-authorized QB-1 PBP parse-seam implementation round 15.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_pbp_parse_round15_open_codex_v1.mjs --apply
 *
 * The installed round-open verb rejects this terminal, over-cap continuation.
 * David directly authorized one bounded round, a read-only discarded-result
 * wall sweep, and a fresh rerun only after Codex's explicit CLEAR. This script
 * pins the terminal state, prior review/read/artifact, exact three-file scope,
 * and normal scoped snapshot, then uses persistRun's revision-guarded atomic
 * writer.
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
const SNAPSHOT_ROOT = join(dirname(STATE_PATH), "snapshots");
const ROUND_ROOT = join(SNAPSHOT_ROOT, "green-review-15");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 88;
const EXPECTED_ROUND_14_CLOSE_HASH =
  "6147a09aa7c2fcc88a56cd6418430d333642bfc970d43d1f843904c3cb848f23";
const EXPECTED_SCOPE_HASH =
  "bae7112c4e2c397162417544cd47703993906915ebc0ba27873776c090b1e769";
const FAILED_ARTIFACT_SHA256 =
  "ce4369becf5618de0a9a08042655556cfa3b22054607b28efa98a3e710ca112b";
const REGISTRATION_READ_SHA256 =
  "fe95c24b436af3e8355fbffd8ee432675da8edeae41200335ebbebf53042016f";
const ROUND_14_REVIEW_SHA256 =
  "2a9f535ec7a228f7d400646a7e39af03d03fbb7c7834c4df7a23c6355d93d88f";
const DAVID_WORD =
  "approved - open one bounded round per your sanctioned mechanism: claude implements the pbp parse seam exactly per your registration read's boundary, claude also runs a read-only diagnostic sweep enumerating every remaining named wall in the composition (results discarded unread, no repairs), and on your explicit clear a fresh rerun fires - the registered readout then comes to me for my ruling";
const REPAIR_ID = "TW16-QB1-PBP-PARSE-R15-OPEN-CODEX-V1";

const SCOPE = [
  "src/dynasty_genius/adapters/nflreadpy_qb_adapter.py",
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/adapters/nflreadpy_qb_adapter.py",
    "51af156bcdc044975fd42d21b77fe69901b5f5c231ac67c216cd82a6d2293735",
  ],
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "b0c641743dbaf332d47d3508a6ca69c94b4e9797fd28582ec39e7fb9974965da",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "3a9c51f9ec8a2b943871ad9aa8f546166de00468e043a2697b0ffd65b59d039a",
  ],
]);

function fail(message) {
  throw new Error(`PBP parse round open refused: ${message}`);
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
    fail(`round-15 snapshot directory already exists: ${ROUND_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-15 scope ${relativePath}`);
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
  if (run.failureCounts?.["green-review:review"] !== 8) {
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
    green.length !== 14 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly fourteen closed green-review rounds indexed 1..14");
  }
  const round14 = green.at(-1);
  if (
    round14.reviewerVerdict !== "CLEAR" ||
    round14.churn?.closeSnapshotHash !== EXPECTED_ROUND_14_CLOSE_HASH ||
    !round14.reviewerVerdictEvidence?.includes(ROUND_14_REVIEW_SHA256)
  ) {
    fail("round-14 CLEAR or close snapshot changed");
  }
  const unresolvedBlockers = green.flatMap((round) =>
    round.findings.filter(
      (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
    ),
  );
  if (unresolvedBlockers.length !== 0) {
    fail(`unexpected unresolved blockers: ${unresolvedBlockers.map((f) => f.id).join(", ")}`);
  }
  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "real-surface-qa" ||
    lastCheck?.status !== "failed" ||
    !lastCheck.evidence.includes(FAILED_ARTIFACT_SHA256) ||
    !lastCheck.evidence.includes("pbp: offense_team")
  ) {
    fail("the terminal Round-14 real-surface receipt is absent or changed");
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-15 snapshot directory already exists");
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const failedArtifact = resolve(
    run.worktree,
    "app/data/backtest/qb_validation/qb_validation_report.json",
  );
  requireRegularFile(failedArtifact, "failed QB-1 artifact");
  if (sha256(readFileSync(failedArtifact)) !== FAILED_ARTIFACT_SHA256) {
    fail("failed QB-1 artifact hash changed");
  }
  const registrationRead = resolve(
    run.worktree,
    "docs/agent-ledger/evidence/2026-08-16/qb1_pbp_parse_seam_registration_read_codex_v1.md",
  );
  requireRegularFile(registrationRead, "PBP registration-read evidence");
  if (sha256(readFileSync(registrationRead)) !== REGISTRATION_READ_SHA256) {
    fail("PBP registration-read evidence hash changed");
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
    index: 15,
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
        "Claude implements only the already-registered PBP parse seam and runs one read-only discarded-result diagnostic sweep enumerating every remaining named composition wall",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: REGISTRATION_READ_SHA256,
      round14ReviewSha256: ROUND_14_REVIEW_SHA256,
      failedArtifactSha256: FAILED_ARTIFACT_SHA256,
      implementationBoundary: {
        placement: "after receipt admission and before parsed-frame source gate/matrix",
        sharedAdapterOnly: true,
        defensiveCopy: true,
        pbpSemantics: "registered REG filter plus exact posteam to offense_team rename",
        preserveHashBeforeParse: true,
        preserveProvenance: true,
        secondParserForbidden: true,
        competingRenameTableForbidden: true,
        inputMutation: false,
      },
      diagnosticSweep: {
        mode: "read-only",
        purpose: "enumerate every remaining named wall in the composition",
        studyResults: "discarded unread",
        repairs: false,
        providerFetch: false,
      },
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
    "David-authorized QB-1 PBP parse-seam implementation and read-only discarded-result wall sweep are open; fresh registered rerun fires only after Codex explicit CLEAR; H2 remains UNDER TEST";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 15 },
      boundedPurpose: "registered PBP parse seam plus read-only named-wall sweep",
      implementationBoundary: {
        files: [...SCOPE],
        sharedAdapterParse: true,
        defensiveCopyAfterAdmission: true,
        rawInputsUnchanged: true,
        provenanceUnchanged: true,
      },
      diagnosticSweep: {
        readOnly: true,
        enumerateNamedCompositionWalls: true,
        resultsDiscardedUnread: true,
        repairsForbidden: true,
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
    round15: {
      phase: "green-review",
      index: 15,
      scope: SCOPE,
      openSnapshotHash: prospectiveOpenHash,
      authority: DAVID_WORD,
      diagnosticSweep: "read-only; named walls only; study results discarded unread",
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
      fail("worktree changed while the round-15 open snapshot was being taken");
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
