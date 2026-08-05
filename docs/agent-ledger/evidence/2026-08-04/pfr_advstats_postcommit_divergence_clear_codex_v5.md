# PFR advanced-stats — post-commit divergence verification

**Reviewer:** Codex
**Commit:** `ece3b52a9db1c37e6bec232498cab9fc12af72bd`
**Parent:** `34da22f6417620df54909e31ecf77c484b8b8468`
**Disposition:** **DIVERGENCE-VERIFY CLEAR.** Commit and live product state match the cleared PFR
stream-1 scope.

## Commit audit

- Exact expected parent; 27 files, 8,809 insertions, zero deletions.
- Committed implementation contains the four PFR specs/bindings, exact-era guard, opt-in non-finite
  refusal, wrong-record-type boundary, and pre-parse `raw_sha256` result field.
- Focused committed contract independently reran 31/31 passing.
- Worktree was clean at the start of this post-commit audit.
- `git show --check` reports Markdown two-space hard-break whitespace in evidence documents. This is
  non-functional presentation whitespace, not a code, data, or cleared-scope divergence.

## Live product verification

- Status marker: `ok`, run `nflverse-usage-20260805T0222491928230000`, 72 stream-season results;
  all 72 raw SHA-256 values present and independently matched to their snapshot bytes.
- Ready manifest verified through `read_last_good_export(verify=True)`: 447,120 rows; all nine stream
  files plus `unresolved_identity`; every file exists and matches its manifest hash.
- Product DB counts: NGS passing 5,933; receiving 14,731; rushing 6,059; snap counts 253,106;
  injuries 45,337; PFR pass 5,424; rush 18,461; rec 35,724; def 62,345.
- PFR identity: 121,688 canonical + 266 source-only + zero conflict + zero unknown.
- NGS consumer returned all three non-empty frames with the expected 5,933 / 14,731 / 6,059 rows.
- Injury delta reconciles exactly: new 2018 rows 5,133 plus new 2019 rows 5,392 = 10,525.

The canonical DB/export are intentionally ignored, rebuildable runtime artifacts under repository
policy; their absence from the commit is expected and the live local product state was verified
directly. No push occurred. Stream 2 may proceed under the existing six-stream batch scope.
