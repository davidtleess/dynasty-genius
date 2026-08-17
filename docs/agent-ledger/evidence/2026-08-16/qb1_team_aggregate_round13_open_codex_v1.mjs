#!/usr/bin/env node

/**
 * Open David-authorized QB-1 team-aggregate implementation round 13.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_team_aggregate_round13_open_codex_v1.mjs --apply
 *
 * The installed round-open verb correctly rejects this terminal, over-cap run.
 * David directly authorized one bounded implementation round and separately
 * authorized the registered rerun only after Codex's explicit CLEAR. This
 * script validates revision 76, the closed Round-12 CLEAR, the failed atomic
 * artifact, and exact file pins; takes the normal scoped open snapshot; and
 * writes only through persistRun's revision-guarded atomic writer.
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
const ROUND_ROOT = join(SNAPSHOT_ROOT, "green-review-13");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 76;
const EXPECTED_ROUND_12_CLOSE_HASH =
  "95b511a6c16292f417f8eadc7b34762dd11b10e7c13f0ec1356efafaea5c3148";
const EXPECTED_SCOPE_HASH =
  "aba351da7093f7cdb2768b57ba3d7c00779f6a33d784e534ea357a00212f4a00";
const FAILED_ARTIFACT_SHA256 =
  "fb222a60957e2ae4a353ed730ff5ddccdfac5cb9bbc803cdc2cefe6c62306244";
const REGISTRATION_READ_SHA256 =
  "cb64ddf51e0e662dd776c6fd8cfd09a0a2aff67be1f90ab3f1c82928c2324425";
const DAVID_WORD =
  'grant both - open one bounded round per your sanctioned mechanism: claude implements the team-aggregate exclusion exactly per your pinned boundary (build_label_table records only, null player_id + player_name "Team", fail-closed preserved, no input mutation), and on your explicit clear the study reruns - the registered readout then comes to me for my ruling';
const REPAIR_ID = "TW16-QB1-TEAM-AGGREGATE-R13-OPEN-CODEX-V1";

const SCOPE = [
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "scripts/run_qb1_study.py",
    "7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "88a39cb88a7c5e1eb3a07b7e1dee80634bf27b8238f1aac702218e1ab160d5af",
  ],
]);

function fail(message) {
  throw new Error(`team-aggregate round open refused: ${message}`);
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
    fail(`round-13 snapshot directory already exists: ${ROUND_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-13 scope ${relativePath}`);
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
  if (!Array.isArray(run.reasonCodes) || run.reasonCodes.length !== 0) {
    fail(`reasonCodes changed: ${JSON.stringify(run.reasonCodes)}`);
  }
  if (run.failureCounts?.["green-review:review"] !== 7) {
    fail(`review failure count changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.failureCounts?.["green-review:real-surface-qa"] !== 1) {
    fail(`real-surface failure count changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (run.judgeRuling?.ruling !== "STOP") {
    fail("the prior recorded Judge STOP ruling is absent or changed");
  }
  if (!Array.isArray(run.reviewRounds)) fail("reviewRounds is not an array");
  const green = run.reviewRounds.filter((round) => round.phase === "green-review");
  if (
    green.length !== 12 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly twelve closed green-review rounds indexed 1..12");
  }
  const round12 = green.at(-1);
  if (
    round12.reviewerVerdict !== "CLEAR" ||
    round12.churn?.closeSnapshotHash !== EXPECTED_ROUND_12_CLOSE_HASH
  ) {
    fail("round-12 CLEAR or close snapshot hash changed");
  }
  const unresolved = green.flatMap((round) =>
    round.findings.filter(
      (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
    ),
  );
  if (unresolved.length !== 0) {
    fail(`unexpected unresolved blockers: ${unresolved.map((finding) => finding.id).join(", ")}`);
  }
  const realSurface = run.checks?.at(-1);
  if (
    realSurface?.name !== "real-surface-qa" ||
    realSurface?.status !== "failed" ||
    !realSurface.evidence.includes("label_row_invalid")
  ) {
    fail("the failed label-row real-surface receipt is absent or changed");
  }
  if (
    !run.stateRepairs?.some(
      (repair) => repair.id === "TW16-QB1-PUBLICATION-GATE-BOUNDARY-R12-OPEN-CODEX-V1",
    )
  ) {
    fail("round-12 open repair record is absent");
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-13 snapshot directory already exists");
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
    "docs/agent-ledger/evidence/2026-08-16/qb1_team_aggregate_registration_read_codex_v1.md",
  );
  requireRegularFile(registrationRead, "registration-read evidence");
  if (sha256(readFileSync(registrationRead)) !== REGISTRATION_READ_SHA256) {
    fail("registration-read evidence hash changed");
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
    index: 13,
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
        "Claude implements only the exact provider team-aggregate exclusion at the records passed to build_label_table: missing player_id AND exact player_name Team; the admitted pool and frozen input remain untouched; every other unusable, malformed, ambiguous, or one-sided identity remains fail-closed",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: REGISTRATION_READ_SHA256,
      failedArtifactSha256: FAILED_ARTIFACT_SHA256,
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
    "David-authorized QB-1 team-aggregate implementation round is open; registered rerun is authorized only after Codex explicit CLEAR; H2 remains UNDER TEST";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 13 },
      boundedPurpose: "label-builder-input team-aggregate exclusion only",
      implementationBoundary: {
        predicate: 'missing player_id AND exact player_name == "Team"',
        application: "records passed to build_label_table only",
        failClosedPreserved: true,
        inputMutation: false,
        globalPoolFilter: false,
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
    round13: {
      phase: "green-review",
      index: 13,
      scope: SCOPE,
      openSnapshotHash: prospectiveOpenHash,
      authority: DAVID_WORD,
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
      fail("worktree changed while the round-13 open snapshot was being taken");
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
