# Codex verdict — Option 2 gate simplification NOT CLEAR

Reviewing lane: Codex. Date: 2026-07-26.

## Frozen set

All five SHA-256 values in
`docs/agent-ledger/evidence/2026-07-26/msg_codex_gate_option2.md`
match exactly:

- verifier `e607c702eb81…`
- verifier tests `905a989e2895…`
- amendment spec `d86f9d5f7ba0…`
- closeout skill `d26d056f7a94…`
- governance 02 `0375a28b03b8…`

Tower's arithmetic correction is accepted: David's explicit demotion leaves **three**
ENFORCE checks plus citations as REPORT. “Four” is not the review standard.

## Findings

### 1. HIGH — the retained fence filter is an undeclared exemption from the no-exemptions rule

Locators:

- `scripts/verify_closeout.py:328-347`
- `scripts/verify_closeout.py:373-388`
- `tests/test_verify_closeout.py:397-442`

Option 2 says `ephemeral-locators` has no exemptions: a closeout record must not reproduce
a session-scoped or machine-bound locator, even as quoted evidence. But `added_lines`
still removes every fenced-code line before **both** the locator ENFORCE check and the
citations REPORT see the surface.

End-to-end reproduction, for both a tracked diff and an untracked document:

1. Add a closeout document containing a prose label, an opening code fence, the literal
   obtained by joining `"/"` with `"tmp/live-closeout-evidence.json"`, and a closing
   fence.
2. Run `added_lines`, then pass its result to `check_ephemeral_locators`.
3. `added_lines` returns only the prose label; the locator ENFORCE result is PASS.
4. Passing the same locator directly to `check_ephemeral_locators` returns FAIL.

This is not merely a new edge in machinery David retained. The r7 fence-topology repair
was part of the Thread A machinery David explicitly ordered deleted. The current tests
still pin it. The amendment itself says fence handling was deleted, while the function
and two tests remain.

Under Option 2, the subtractive fix is to stop removing fenced lines from the shared
added-line surface. Citations are REPORT, so quoted examples can be human-audited there;
the exemption-free locator check must see them.

### 2. HIGH — the governing closeout procedure still declares citations ENFORCE

Locator: `docs/governance/02-agent-operating-loop.md:345`.

The executable governance step still lists `dangling-citations` among the ENFORCE checks
and omits `citations` from REPORT. That directly contradicts David's Option 2 ruling, the
script, the skill, and the later durable-evidence paragraph in the same governance file.
A future lane following step 3 would receive two incompatible contracts.

### 3. MEDIUM — the amendment spec retains active and mechanically corrupted waiver contracts

Locators:

- `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:41`
- `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:48`
- `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:101-103`
- `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:112`

The harvest table still maps L7 to ENFORCE and L14 to active reason-bearing waivers.
Section 4b says reversed decisions below are kept historically, which can justify retaining
the narrative, but the deletion pass removed the marker names from that narrative without
rewriting it: line 103 now shows two empty code spans separated by a slash, and line 112
names an empty escape. Those are corrupted sentences, not a usable historical record.

The current-versus-historical boundary needs to be explicit, and the deleted marker syntax
should either be described generically or preserved as quoted historical syntax—not blanked.

### 4. LOW — dead duplicate helpers and stale test framing survived the deletion

Locators:

- `scripts/verify_closeout.py:188-224` duplicates helpers redefined at lines 252-268.
- `tests/test_verify_closeout.py:357-361` still labels the active test section as waiver
  machinery.
- `tests/test_verify_closeout.py:391` says a missing citation “fails” although it now only
  REPORTs.

The first helper definitions are dead at runtime because `cited_paths` resolves the later
global definitions. This does not change behavior, but it is deletion residue in a change
whose safety claim is simplicity.

## Dispositions on the requested questions

1. **Demotion:** correct under David's ruling. I do not argue citations back to ENFORCE.
2. **Remaining judgement enforcement:** the three intended checks are defensible as
   mechanical contracts. The fence exclusion, however, makes the locator contract
   materially weaker than stated.
3. **No-exemptions livability:** livable as a policy. A reviewer can describe the locator
   class and promote any load-bearing artifact into the repo. The blocker is that the code
   currently permits an undocumented fenced escape.
4. **Structured evidence:** no implementation or anticipatory hook found. Option 2 remains
   independent of that future decision.

## Checks actually run

- Five frozen hashes matched.
- Focused set: 57 passed.
- Ruff clean on the five Python review files.
- Governance validator PASS.
- `git diff --check` clean.
- Live gate: three ENFORCE rows, citations REPORT with 16 items, current dirty state
  truthfully produces a parked verdict.
- `scripts/dg_mail_carrier.py` byte-identical to `origin/main`; enable-marker guard remains.
- Disposable end-to-end probe reproduced the fenced false PASS for tracked and untracked
  closeout documents.

## Authority and product boundary

Review only. No frozen implementation artifact, wire-state row, pane claim, carrier state,
or enable marker was edited. This verdict and the daily ledger entry are Codex's only
repository writes for this review.

Governance tooling only. The QB-1 study has not run; H2 QB rushing production remains
**UNDER TEST**.
