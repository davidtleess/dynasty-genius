// TW14-QB1-1 — Claude pre-execution audit probe for the Codex R5-G2 repair script
// (qb1_r5_g2_state_repair_codex_v1.mjs, pin 1c947db4…).
//
// Question under test: the installed library's takeSnapshot() separates path and
// content with SPACES (loop-control.mjs lines ~126-141), while the repair script's
// scopedSnapshotHash() uses NUL ("\0") separators. The recorded round-4
// openSnapshotHash 3f634bfd… was produced by the library at round-open time, so the
// script's identity comparison can only pass if the two algorithms agree on these
// inputs — or if one of the two readings is wrong.
//
// Read-only: recomputes the scoped hash over snapshots/green-review-1/open both
// ways and compares each to the recorded hash. No writes anywhere.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT =
  "/Users/davidleess/dynasty-genius/.git/worktrees/dynasty-genius-product/dg-autonomy/snapshots/green-review-1/open";
const EXPECTED = "3f634bfd27c78ae19cc2b5b0398d77f41304780afb6df71631ac9906fc66c54d";
const SCOPE = [
  "src/dynasty_genius/eval/qb_validation/execution.py",
  "src/dynasty_genius/eval/qb_validation/status.py",
  "src/dynasty_genius/eval/qb_validation/__init__.py",
  "scripts/run_qb1_study.py",
  "tests/contract/test_qb1_green_correction_contracts.py",
  "tests/contract/test_qb1_execution_red.py",
];

function hashWith(separator) {
  const hash = createHash("sha256");
  for (const rel of [...SCOPE].sort()) {
    hash.update(`${rel}${separator}`);
    try {
      hash.update(readFileSync(resolve(ROOT, rel)));
    } catch {
      hash.update("<absent>");
    }
    hash.update(separator);
  }
  return hash.digest("hex");
}

const libStyle = hashWith(" ");
const codexStyle = hashWith("\0");
console.log(JSON.stringify({
  expectedRecorded: EXPECTED,
  libStyleSpaceSeparators: libStyle,
  libStyleMatches: libStyle === EXPECTED,
  codexStyleNulSeparators: codexStyle,
  codexStyleMatches: codexStyle === EXPECTED,
}, null, 2));
