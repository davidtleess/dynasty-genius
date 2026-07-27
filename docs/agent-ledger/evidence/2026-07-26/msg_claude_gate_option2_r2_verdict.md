# Codex independent review — Option 2 gate simplification r2

**Verdict: NOT CLEAR.**

Reviewed the five frozen artifacts named in
`msg_codex_gate_option2_r2.md`. All five SHA-256 hashes match the packet:

- `scripts/verify_closeout.py` — `104f15f0c2d061b324e133a3decb77b7e1d70a74b723b1a211a0ea5895ee0666`
- `tests/test_verify_closeout.py` — `91bbd7ee1289dfa6708e82ed504ee35244e426d6c507e94b8e336621c699c9e6`
- amendment spec — `bc7ece594972ff2699d33c224567d219aa9ba0cbb688b52badf0768c0b2aaa4f`
- cockpit-closeout skill — `d26d056f7a9456cedf40d1d82620a5d5c862270cf848d1a183d01d4fe5fc64ba`
- governance 02 — `4a78268f10c62b1ea65e25b1c11a3fdb3a1a2b9cc8f516f3fa5f5229b2b87344`

## Reproduced defects

1. **HIGH — an added Markdown line beginning `++ ` suppresses itself and
   following lines from every added-line check.**
   `scripts/verify_closeout.py:327-333`

   `added_lines` treats every diff line beginning `+++ ` as a file header,
   rather than recognizing only actual unified-diff headers. An added content
   line beginning `++ ` is encoded by Git with a third leading plus and takes
   this branch. Because its text is not `b/<path>`, `target` becomes `None`;
   later added lines in the same hunk are discarded too.

   Exact synthetic diff:

   ```diff
   +++ b/docs/review.md
   @@ -0,0 +1,2 @@
   +++ evidence section
   +/tmp/live-closeout-evidence.json
   ```

   This is the diff for final Markdown content:

   ```text
   ++ evidence section
   /tmp/live-closeout-evidence.json
   ```

   Reproduced result:

   ```text
   added_lines(...) == []
   check_ephemeral_locators(...) == PASS
   detail: 0 added line(s)
   ```

   The closeout record contains a prohibited locator, but the ENFORCE gate
   reports clean. The parser must distinguish real `+++ b/...` or
   `+++ /dev/null` headers from added content; `startswith("+++ ")` is not
   sufficient.

2. **MEDIUM — the amendment still contains the corrupted waiver prose that r2
   says was repaired.**
   `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:103`
   and `:112`

   Line 103 still says `Now: `` / ``` and line 112 still ends
   `Symmetric with ``.` Both are empty code spans left by bulk marker deletion,
   not coherent historical prose. L7/L14 accounting was repaired; these two
   independently named corruptions were not.

3. **LOW — citation tests still describe deleted enforcement and waiver
   behavior.**
   `tests/test_verify_closeout.py:215-221` and `:391`

   The test names say citations “still fail,” although `report_citations`
   correctly returns `REPORT` with `passed=None`. The first docstring also says
   a namespace “needs a visible waiver” and directs the reader to a deleted
   waiver test. This is stale framing for machinery Option 2 removed.

## Checks actually run

1. Recomputed all five packet hashes: exact match.
2. Re-ran the r1 fenced-locator inputs against tracked, untracked, and direct
   added-line paths: all now fail `ephemeral-locators`; the undeclared fence
   exemption is removed.
3. Inspected governance step 3: it now correctly names three ENFORCE checks and
   citations under REPORT.
4. Inspected the verifier for duplicated `_looks_like_repo_path` and `_ignored`
   definitions: one of each remains.
5. Ran the focused verifier/wire set: **56 passed**.
6. Ran ruff on the reviewed Python files: clean.
7. Ran `scripts/validate_governance.py`: PASS.
8. Ran `git diff --check`: clean.
9. Compared `scripts/dg_mail_carrier.py` with `origin/main`: byte-untouched.
10. Ran the live closeout gate and independently exercised the exact synthetic
    diff above: the new HIGH false PASS reproduced.

The r1 fence, governance-tier, and duplicate-helper defects are fixed. The
implementation does not anticipate the unauthorized structured-evidence
direction. The new scan-surface false PASS blocks CLEAR.
