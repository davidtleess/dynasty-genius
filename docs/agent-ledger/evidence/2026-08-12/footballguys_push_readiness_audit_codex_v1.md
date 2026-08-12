# Footballguys publication-range audit — Codex v1

Date: 2026-08-12  
Layer: 1 — governed source intake and publication record  
Candidate: `e6b67756696991b5598525762945d62557b5cdbf`  
Authoritative remote at final check: `origin/main = 3722ff5d543f8dd9601f04c052d726c30f20a510`

## Verdict

**NOT CLEAR for push.** The implementation and mechanical gates are green, but the outgoing
closeout evidence violates the operating loop's durable-evidence locator rule. No push is
authorized or performed by this review.

## Finding 1 — BLOCKING: ephemeral and machine-bound locators in durable evidence

`docs/governance/02-agent-operating-loop.md` lines 454–456 require cited closeout evidence to
live in the repository and prohibit session-scoped or machine-bound locators in the closeout
record, with no exemptions. The outgoing range contains nine concrete locator occurrences across
six evidence files (seven distinct strings after the checker's de-duplication):

- `docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_claude_v6.md:145`
- `docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_claude_v7.md:165`
- `docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_claude_v8.md:176`
- `docs/agent-ledger/evidence/2026-08-11/unattributed_intake_mutation_query_claude_wire_v1.md:9`
- `docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_green_v21_review_codex_v1.md:44,65–67`
- `docs/agent-ledger/evidence/2026-08-12/footballguys_retraction_withdrawn_claude_wire_v1.md:11`

The four named probe scripts cited in the v21 review still exist only in session scratch, not in
the repository. Repair is documentation-only: replace every literal ephemeral/machine-bound
locator with a durable repo citation where the evidence is being retained, or with a descriptive
phrase where the locator is merely narrative. Do not widen the implementation or provider-data
scope. An initial broader scan also matched generic temp-root names used as protocol definitions;
that scope was corrected because those are not concrete dead citations and the framing must retain
its exact fixed-root contract.

## Checks run

- Read the mandatory governance/bootstrap sources and current board; reviewed the complete
  `origin/main..HEAD` range.
- Authoritative remote: `git ls-remote origin refs/heads/main` returned `3722ff5…`.
- Ancestry: `0 behind / 101 ahead`; merge base equals authoritative remote; no merge commits.
- Range: 326 paths; only eight outside docs/ledger state, all reviewed. No provider payload,
  database, archive, model artifact, or full census is present.
- Secret scans: no private-key headers or high-signal AWS, GitHub, Google, Slack, or Stripe
  credentials; no generic credential-assignment hits.
- Final committed pins independently reproduced:
  - RED `9e0a861facd1e1502d66f9bc4672c2055ca7c1719483f387014b5d3453aa76e3`
  - GREEN `a419930b3a0871d3bb2477475699ef2dcc76317125b544b0c2caac12ccd7790d`
- Focused RED: 660 passed, exit 0.
- Ruff `src app`: passed.
- Strict compile of RED and GREEN: passed.
- Exact `scripts/verify_sprint_closeout.py` in a detached worktree at the candidate head, using
  the existing installed Python and frontend dependencies: Python suite PASS, Ruff PASS,
  frontend typecheck/lint/test/banned-language/build PASS, ENFORCE verdict PASS, exit 0.
- The first detached-worktree run failed only because that worktree lacked `frontend/node_modules`;
  the three failures were `ERR_MODULE_NOT_FOUND: typescript`. Binding the already-installed
  dependency directory and rerunning the exact verifier produced the green result above.
- `git diff --check origin/main..HEAD` reports Markdown trailing-space/newline findings across
  the historical evidence record. These are not treated as a separate blocker because many are
  CommonMark hard breaks and the governed closeout verifier passed; no implementation file has a
  diff-check finding.
- The shared working tree's unrelated modified and untracked files were preserved; no product
  implementation or test file was changed by this audit.

## Gate after repair

Claude made the bounded six-file evidence-locator repair and returned hashes. Codex independently
verified the exact diff and preserved every fixed-root protocol definition. The locator repair must
now be committed with this audit record before the added-lines checker can evaluate the repaired
bytes instead of the prior committed bytes. That commit requires David's explicit authorization.
After landing, Codex re-runs the locator and closeout checks, re-verifies the authoritative remote
and final pins, and issues CLEAR or another exact finding. Push remains a separate David
authorization, and CI remains the push gate.

QB rushing H2 remains **UNDER TEST** with no result and is unrelated.
