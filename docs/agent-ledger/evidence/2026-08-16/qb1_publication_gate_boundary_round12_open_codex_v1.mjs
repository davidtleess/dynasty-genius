#!/usr/bin/env node

/**
 * Open David-authorized QB-1 publication-gate boundary round 12.
 *
 * Dry-run is the default. The sole mutating form is:
 *
 *   node docs/agent-ledger/evidence/2026-08-16/qb1_publication_gate_boundary_round12_open_codex_v1.mjs --apply
 *
 * The installed round-open verb correctly rejects this terminal, over-cap run.
 * David directly authorized one bounded round to document the publication
 * gate's scope. This script validates revision 66 and the exact Round-11 close,
 * takes the normal scoped open snapshot, and writes only through persistRun's
 * revision-guarded atomic writer. It does not authorize study execution,
 * publication, registered-value change, provider fetch, commit, or push.
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
const ROUND_ROOT = join(SNAPSHOT_ROOT, "green-review-12");
const ROUND_OPEN = join(ROUND_ROOT, "open");
const TARGET_RUN_ID = "f8f7551c-a145-46e2-b9b4-dec427f313ba";
const EXPECTED_REVISION = 66;
const EXPECTED_ROUND_11_CLOSE_HASH =
  "7db01034eb5cb418127d71448263a1dd846dbf259686c5c1dee45fcbace24527";
const EXPECTED_JUDGE_RULED_AT = "2026-08-15T02:50:23.167Z";
const DAVID_WORD =
  "i rule the publication gate's registered guarantee is coherence + registration " +
  "conformance - provenance grounding is out of the gate's scope; source truth stays " +
  "with the pinned inputs, the shipped composition, and the end-to-end contracts. open " +
  "one bounded round per your sanctioned mechanism for claude to document the boundary " +
  "in the gate, then re-review under this ruling - execution only on your clear";
const REPAIR_ID = "TW16-QB1-PUBLICATION-GATE-BOUNDARY-R12-OPEN-CODEX-V1";
const CARRIED_FINDING = "R11-G1-F13-SOURCE-TOTALITY";

const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
];

const EXPECTED_SCOPE_HASHES = new Map([
  [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "7b88dc776a476c3535abb904ce31bd7b9a26bab7d349873708b4cd171e31d3f9",
  ],
  [
    "scripts/run_qb1_study.py",
    "7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297",
  ],
  [
    "tests/contract/test_qb1_green_correction_contracts.py",
    "c539e97e703af4eb0bcecdfd7a2365c5485848330d38f3d75690e50655d8ad1b",
  ],
]);

function fail(message) {
  throw new Error(`publication-gate boundary round open refused: ${message}`);
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
    fail(`round-12 snapshot directory already exists: ${ROUND_ROOT}`);
  }
  for (const relativePath of scope) {
    const source = resolve(worktree, relativePath);
    requireRegularFile(source, `round-12 scope ${relativePath}`);
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
  if (run.reason !== "review failed 3 times in green-review") {
    fail(`terminal reason changed: ${JSON.stringify(run.reason)}`);
  }
  if (run.failureCounts?.["green-review:review"] !== 7) {
    fail(`review failure count changed: ${JSON.stringify(run.failureCounts)}`);
  }
  if (
    run.judgeRuling?.ruling !== "STOP" ||
    run.judgeRuling?.ruledAt !== EXPECTED_JUDGE_RULED_AT
  ) {
    fail("the recorded Judge STOP ruling is absent or changed");
  }
  if (
    !Array.isArray(run.checks) ||
    run.checks.length !== 7 ||
    run.checks.some((check) => check.name !== "review" || check.status !== "failed")
  ) {
    fail("expected exactly seven failed review receipts");
  }
  if (!Array.isArray(run.reviewRounds)) fail("reviewRounds is not an array");
  const green = run.reviewRounds.filter((round) => round.phase === "green-review");
  if (
    green.length !== 11 ||
    green.some((round, offset) => round.index !== offset + 1 || round.closedAt === null)
  ) {
    fail("expected exactly eleven closed green-review rounds indexed 1..11");
  }
  const round11 = green.at(-1);
  if (round11.churn?.closeSnapshotHash !== EXPECTED_ROUND_11_CLOSE_HASH) {
    fail("round-11 close snapshot hash changed");
  }
  const unresolved = round11.findings.filter(
    (finding) => finding.severity === "BLOCKER" && finding.resolvedInRound === null,
  );
  if (unresolved.length !== 1 || unresolved[0].criterionId !== CARRIED_FINDING) {
    fail(
      `round-11 unresolved blockers changed: ${JSON.stringify(
        unresolved.map((finding) => finding.criterionId),
      )}`,
    );
  }
  if (
    !run.stateRepairs?.some(
      (repair) =>
        repair.id === "TW16-QB1-FULL-EVIDENCE-REDESIGN-R11-OPEN-CODEX-V1",
    )
  ) {
    fail("round-11 open repair record is absent");
  }
  if (existsSync(ROUND_ROOT)) fail("green-review-12 snapshot directory already exists");
  for (const [relativePath, expectedHash] of EXPECTED_SCOPE_HASHES) {
    const path = resolve(run.worktree, relativePath);
    requireRegularFile(path, relativePath);
    const actualHash = sha256(readFileSync(path));
    if (actualHash !== expectedHash) {
      fail(`${relativePath} hash ${actualHash} != ${expectedHash}`);
    }
  }
  const currentScopeHash = scopedSnapshotHash(run.worktree, SCOPE);
  if (currentScopeHash !== EXPECTED_ROUND_11_CLOSE_HASH) {
    fail(
      `current scope hash ${currentScopeHash} != round-11 close ${EXPECTED_ROUND_11_CLOSE_HASH}`,
    );
  }
}

function buildOpenRun(run, openSnapshotHash, now) {
  const next = structuredClone(run);
  next.reviewRounds.push({
    phase: "green-review",
    index: 12,
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
        "Claude documents in the publication gate that its registered guarantee is coherence plus registration conformance; provenance grounding is out of gate scope and remains owned by pinned inputs, shipped composition, and end-to-end contracts; documentation and boundary contracts only, with no semantic behavior, schema, calculation, input, or output change",
      executionTrigger: "Codex explicit CLEAR only",
      carriedFinding: CARRIED_FINDING,
      carriedFindingDisposition:
        "David ruled provenance grounding out of publication-gate scope; resolve only after the boundary is documented and independently reviewed",
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
    "David-authorized QB-1 publication-gate boundary documentation round is open; study execution remains held pending Codex CLEAR";
  next.stateRepairs = [
    ...(next.stateRepairs ?? []),
    {
      id: REPAIR_ID,
      status: "applied",
      authority: DAVID_WORD,
      openedRound: { phase: "green-review", index: 12 },
      boundedPurpose: "publication-gate boundary documentation only",
      carriedFindings: [CARRIED_FINDING],
      disposition:
        "provenance grounding ruled out of publication-gate scope; source truth remains with pinned inputs, shipped composition, and end-to-end contracts",
      openSnapshotHash,
      executionAuthorized: false,
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
    round12: {
      phase: "green-review",
      index: 12,
      scope: SCOPE,
      openSnapshotHash: prospectiveOpenHash,
      authority: DAVID_WORD,
      carriedFindings: [CARRIED_FINDING],
      disposition: "provenance grounding is outside publication-gate scope",
    },
    executionHeldPendingCodexClear: true,
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
      fail("worktree changed while the round-12 open snapshot was being taken");
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
