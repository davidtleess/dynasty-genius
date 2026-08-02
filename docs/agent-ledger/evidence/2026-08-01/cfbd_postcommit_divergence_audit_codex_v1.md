# CFBD QB GREEN — post-commit divergence audit

**Commit:** `4d8127d42dc41f4cfa721aff4594dbff4fe5c94e`  
**Parent:** `30c15f5a74a51baa76cffdf4db99427d571a764c`  
**Reviewer:** Codex  
**Disposition:** **DIVERGENCE FOUND**

## Checks performed

- Read `git show 4d8127d`, including the commit message, all 37 paths, and the production/test diff.
- Verified `main` is exactly one commit ahead of `origin/main`; no push occurred.
- Re-ran the two independent contract suites: **22 passed** (`11` RED + `11` GREEN-review).
- Ran Ruff over all nine committed production/test paths: **clean**.
- Ran `git diff --check 4d8127d^ 4d8127d` scoped to those nine production/test paths: **clean**.
- Checked the committed message against the final ledger and GREEN-clear artifact. The eleven-finding
  count, four-round count, reviewer attribution, and one Claude self-caught defect are accurate. The
  `39.5` values are described as coverage, not importance; no model-fit or promotion contamination is
  claimed.

## Zero-drift surface that passed

The four production files and five test files are the state Codex cleared. The committed behavior
still satisfies G1-G7, including the two final G1 alias/team rows and G2 failure-vs-empty semantics.
No post-clear production/test edit, comment change, whitespace change, or section reordering was
found in those nine paths.

The CFBD evidence packets and daily-ledger entries are the relevant durable audit trail. Committing
the complete daily ledger is verifier-exempt state-record maintenance under `02`; it does not widen
the production contract.

## Divergence

`docs/data-inventory.md` is outside the cleared CFBD GREEN and contains three unrelated
PFF/PlayerProfiler state changes:

1. The source table's PFF row was rewritten from the earlier three-export description to the
   149-payload/7-family acquisition state.
2. The detailed PFF row was changed to claim first off-machine verification in backup
   `20260801T141500Z`.
3. The PlayerProfiler row was changed to claim first off-machine verification in the same run.

Those facts may be accurate, but Codex did not clear them as part of the CFBD GREEN. The file is not
one of `02`'s verifier-exempt state-doc pair (`AGENT_SYNC.md` and the daily ledger), and David's item
1 word was to commit **the GREEN**. A post-commit disclosure does not retroactively make unrelated
content part of the cleared state.

Therefore the 37-file commit does not have zero divergence from the CFBD state Codex cleared. The
cycle remains open. The correction should remove those three `docs/data-inventory.md` hunks from the
CFBD commit line (or otherwise receive a new, explicit David disposition); Codex will audit the
correction commit before closing the loop.

## Non-blocking observations

- Full-commit `git diff --check 4d8127d^ 4d8127d` reports Markdown whitespace in six evidence files.
  Those evidence files existed before the GREEN verdict and this does not prove post-clear drift, so
  it is not the divergence basis above. It does mean the commit-level diff is not literally
  `diff --check` clean; the earlier clean result did not inspect then-untracked evidence files.
- The current working tree has seven untracked paths, not three: the three deliberately withheld NGS
  paths plus four framing/message artifacts created after the commit. The latter are post-commit
  thread work, not contamination of `4d8127d`.
