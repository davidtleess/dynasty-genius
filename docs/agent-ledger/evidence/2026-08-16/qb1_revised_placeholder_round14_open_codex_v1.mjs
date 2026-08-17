#!/usr/bin/env node

/**
 * Open David-authorized QB-1 revised-placeholder implementation round 14.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_revised_placeholder_round14_open_codex_v1.mjs --apply
 *
 * The installed round-open verb correctly rejects this terminal, over-cap run.
 * David directly authorized one bounded implementation round and preserved the
 * already-granted registered rerun only after Codex's explicit CLEAR. This
 * script validates revision 80, the closed Round-13 review, the corrected
 * registration read, failed artifact, and exact file pins; takes the normal
 * scoped open snapshot; and writes only through persistRun's revision-guarded
 * atomic writer.
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
const ROUND_ROOT = join(SNAPSHOT_ROOT, "green-review-14");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 80;
const EXPECTED_ROUND_13_CLOSE_HASH =
  "0ebb1bf627a928389ab52df8e6ede6b763be62e077c6f81419df284efe1ba027";
const EXPECTED_SCOPE_HASH = EXPECTED_ROUND_13_CLOSE_HASH;
const FAILED_ARTIFACT_SHA256 =
  "fb222a60957e2ae4a353ed730ff5ddccdfac5cb9bbc803cdc2cefe6c62306244";
const REGISTRATION_READ_SHA256 =
  "729c68e074d49a6c1b6c6abf7b85236d36c390ec8f65f8b084f25f2c3114fdce";
const ROUND_13_REVIEW_SHA256 =
  "30100ea34c04f6406bf00fd4d28885e8dd4beb63993809cdfe44fc9f94f35525";
const DAVID_WORD =
  "approved - open one bounded round per your sanctioned mechanism: claude implements your revised placeholder predicate exactly (missing player_id AND missing position AND exact validated zero across all 17 D2 inputs, names as audit evidence only, label-builder records only, full pool untouched to the matrix), and on your explicit clear the already-granted rerun fires - the registered readout then comes to me for my ruling";
const REPAIR_ID = "TW16-QB1-REVISED-PLACEHOLDER-R14-OPEN-CODEX-V1";

const SCOPE = [
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "scripts/run_qb1_study.py",
    "8a559c314823ffcb572c020f85268c04e7f782861a88e5d42abf639e045907bf",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "634d7ce76521b63c26b8021c0c6926a11440b17410c4cc86229c9c635fe8afa3",
  ],
]);

function fail(message) {
  throw new Error(`revised-placeholder round open refused: ${message}`);
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
    fail(`round-14 snapshot directory already exists: ${ROUND_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-14 scope ${relativePath}`);
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
  if (run.failureCounts?.["green-review:review"] !== 8) {
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
    green.length !== 13 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly thirteen closed green-review rounds indexed 1..13");
  }
  const round13 = green.at(-1);
  if (
    round13.reviewerVerdict !== null ||
    round13.churn?.closeSnapshotHash !== EXPECTED_ROUND_13_CLOSE_HASH
  ) {
    fail("round-13 review state or close snapshot hash changed");
  }
  const unresolved = green.flatMap((round) =>
    round.findings.filter(
      (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
    ),
  );
  if (
    unresolved.length !== 1 ||
    unresolved[0].criterionId !== "R13-G1-LABEL-PLACEHOLDER-PREDICATE-INCOMPLETE"
  ) {
    fail(`unexpected unresolved blockers: ${unresolved.map((finding) => finding.id).join(", ")}`);
  }
  const lastCheck = run.checks?.at(-1);
  if (
    lastCheck?.name !== "review" ||
    lastCheck?.status !== "failed" ||
    !lastCheck.evidence.includes(ROUND_13_REVIEW_SHA256)
  ) {
    fail("the failed Round-13 review receipt is absent or changed");
  }
  if (
    !run.stateRepairs?.some(
      (repair) => repair.id === "TW16-QB1-TEAM-AGGREGATE-R13-OPEN-CODEX-V1",
    )
  ) {
    fail("round-13 open repair record is absent");
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-14 snapshot directory already exists");
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
    "docs/agent-ledger/evidence/2026-08-16/qb1_label_placeholder_registration_read_codex_v2.md",
  );
  requireRegularFile(registrationRead, "corrected registration-read evidence");
  if (sha256(readFileSync(registrationRead)) !== REGISTRATION_READ_SHA256) {
    fail("corrected registration-read evidence hash changed");
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
    index: 14,
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
        "Claude implements only the revised provider-placeholder classifier at copied records passed to build_label_table: missing player_id AND missing position AND exact validated zero across all 17 D2 inputs; names are audit evidence only; the full admitted pool remains untouched for build_study_matrix",
      registrationClassification: "implementation, not amendment",
      classificationEvidenceSha256: REGISTRATION_READ_SHA256,
      round13ReviewSha256: ROUND_13_REVIEW_SHA256,
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
    "David-authorized QB-1 revised-placeholder implementation round is open; the already-granted registered rerun fires only after Codex explicit CLEAR; H2 remains UNDER TEST";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 14 },
      boundedPurpose: "label-builder-input revised placeholder exclusion only",
      carriedBlockers: ["R13-G1-LABEL-PLACEHOLDER-PREDICATE-INCOMPLETE"],
      implementationBoundary: {
        predicate:
          "missing player_id AND missing position AND exact validated zero across all 17 D2 inputs",
        names: "audit evidence only",
        application: "copied records passed to build_label_table only",
        failClosedPreserved: true,
        inputMutation: false,
        globalPoolFilter: false,
        fullPoolToMatrix: true,
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
    round14: {
      phase: "green-review",
      index: 14,
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
      fail("worktree changed while the round-14 open snapshot was being taken");
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
