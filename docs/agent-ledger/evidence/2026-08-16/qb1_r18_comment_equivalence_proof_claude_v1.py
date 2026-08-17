"""R18-W1 comment-only equivalence proof.

Reconstructs the pinned pre-correction `identity.py` (SHA-256 `2d146de5…`) by
reversing EXACTLY the one comment edit, proves the reconstruction hashes to
the pin (so the reconstruction IS the reviewed version), then proves AST
equivalence between the pinned version and the corrected file with
`ast.dump(include_attributes=False)` — comments never enter the AST and
line-number attributes are excluded, so equality proves zero
executable/doc-string change. Read-only over the repo; writes nothing.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
TARGET = REPO_ROOT / "src/dynasty_genius/eval/qb_validation/identity.py"
PINNED_SHA = "2d146de57d716f1e215b49a992a35dc17e4b71c42b0bcbc71c27e7291dc51088"

NEW_COMMENT = """\
# R18 (David's bounded word, revision 111; Codex registration read
# `qb1_f34_college_normalization_registration_read_codex_v1.md` — an
# IMPLEMENTATION of the registered F34 cross-check, not an amendment): the
# measured fourth wall was 69/179 matrix study QBs landing TRIAGE
# cross_check_conflict on a whole-string college comparison. Of those 69, the
# 49 players whose 143 rows reached the H4 refusal were morphology-censused as
# 23 multi-school histories containing the draft school · 22 single-school
# provider alias/abbreviation/punctuation variants · 4 compound (multi-school
# AND draft-side abbreviation); the other 20 TRIAGE players never survived the
# earlier H4 gates. The final real-surface reconciliation covers all 69: 67
# representation-only conflicts repaired by this law + the 2 genuine residual
# conflicts (00-0029857, 00-0037175) the cross-check exists to catch. The law
# below is deliberately CLOSED: terminal-token-boundary expansions and an
# exact alias set only — no substring/prefix/fuzzy matching, no city/qualifier
# dropping, no open-ended heuristics, no player allowlists, no GSIS/name/age
# bypass."""
OLD_COMMENT = """\
# R18 (David's bounded word, revision 111; Codex registration read
# `qb1_f34_college_normalization_registration_read_codex_v1.md` — an
# IMPLEMENTATION of the registered F34 cross-check, not an amendment): the
# measured fourth wall was 69/179 study QBs landing TRIAGE cross_check_conflict
# on a whole-string college comparison, in three morphologies (23 multi-school
# histories containing the draft school · 22 single-school provider
# alias/abbreviation/punctuation variants · 4 compound). The law below is
# deliberately CLOSED: terminal-token-boundary expansions and an exact alias
# set only — no substring/prefix/fuzzy matching, no city/qualifier dropping,
# no open-ended heuristics, no player allowlists, no GSIS/name/age bypass."""


def main() -> int:
    current = TARGET.read_text()
    count = current.count(NEW_COMMENT)
    print(f"corrected comment occurs exactly once: {count == 1}")
    if count != 1:
        return 1
    reconstructed = current.replace(NEW_COMMENT, OLD_COMMENT)
    recon_sha = hashlib.sha256(reconstructed.encode()).hexdigest()
    print(f"reconstructed prior-version SHA-256: {recon_sha}")
    pin_match = recon_sha == PINNED_SHA
    print(f"matches pinned 2d146de5…: {pin_match}")
    old_ast = ast.dump(ast.parse(reconstructed), include_attributes=False)
    new_ast = ast.dump(ast.parse(current), include_attributes=False)
    ast_equal = old_ast == new_ast
    print(f"AST equivalence (comments/line attrs ignored): {ast_equal}")
    current_sha = hashlib.sha256(current.encode()).hexdigest()
    print(f"corrected identity.py SHA-256: {current_sha}")
    verdict = pin_match and ast_equal
    print(f"PROOF VERDICT: {'PASS' if verdict else 'FAIL'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
