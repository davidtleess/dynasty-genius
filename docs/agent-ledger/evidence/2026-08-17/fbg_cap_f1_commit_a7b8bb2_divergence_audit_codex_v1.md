# Footballguys FBG-CAP-F1 commit `a7b8bb2` divergence audit — Codex v1

Date: 2026-08-17 ET
Reviewer: Codex, independent binding lane
Commit: `a7b8bb222cf64ac437a148e59842e18da452b958`
Parent: `d39ff341678a904a1eeac07f263610843f1346f5`

## Verdict

**CLEAR — zero divergence between commit `a7b8bb2` and the final reviewed/staged set.**

The committed repair test is byte-exact to the reviewed pin, the committed review is byte-exact to
the disclosed post-format pin, and the remaining eight committed paths are exactly the two state
documents plus seven evidence artifacts named in the post-commit confirmation. No executable,
configuration, store, capture, scheduler, or horizon-adjudication path appears in the commit.

## Commit boundary

- Actual parent: `d39ff341678a904a1eeac07f263610843f1346f5`.
- Actual scope: 10 paths, 379 insertions, 13 deletions.
- Path dispositions: three modified paths (`AGENT_SYNC.md`, the daily ledger, and the Phase A
  contract) plus seven added evidence artifacts.
- `git diff --check d39ff34 a7b8bb2`: clean.
- Authoritative remote: `git ls-remote origin refs/heads/main` returned the full audited SHA.

## Blob verification

| Committed path | SHA-256 of `git show a7b8bb2:<path>` | Disposition |
|---|---|---|
| `tests/contract/test_footballguys_phase_a_red.py` | `36de40c39eaec52a772d975ba98c61f0a4276c851d8c27da486342610a833789` | Exact reviewed repair pin |
| `docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_remediation_review_codex_v1.md` | `2dd9105c1b0d6155bce122c3e7f45a4ac924068d6e93ccde9fe09268476bf9d3` | Exact final post-format review pin |
| `docs/agent-ledger/evidence/2026-08-17/fbg_first_capture_review_codex_v1.md` | `6534ce119df6eee14a217de40c37c5e4dc14857e97a0f68e765f09318af37e80` | Exact first-capture review pin |
| `docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_remediation_delta_claude_v1.md` | `6bf5aa25b73eb72e51b461a33e62f5e2df662370c5c08b6b670c9cba95e556f1` | Named staged delta wire |
| `docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_remediation_clear_wire_codex_v1.md` | `43a3e18e873bab6b989f3deef6b39f98cdf9349aac6c83ff6e9d0adf267c62c6` | Named historical CLEAR wire |
| `docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_clear_ack_wire_claude_v1.md` | `20ea897306a0d6ee4d7fa37cf72e43e4e424477977a7d34fced7b31363780840` | Named historical ACK wire |
| `docs/agent-ledger/evidence/2026-08-17/realized_scorer_and_orphaned_producers_codex_v1.md` | `b27f2c57452c8effa658ce68f00b42937554a55e4be61768596bb0daf375aa0d` | Named pre-existing review record in the staged state set |
| `docs/agent-ledger/evidence/2026-08-17/task1_task2_review_reply_codex_v1.md` | `270b1401b98b9c994e41cbd4a982d7b76b54da23b55e8886e20c74c626a82e85` | Named pre-existing review reply in the staged state set |
| `AGENT_SYNC.md` | `928e1a60379ca94b8ff0c549a805a34e025141b8e8eb460ca2811263bfdb3ff4` | Exact committed board state; adds the two disclosed Codex review blocks |
| `docs/agent-ledger/2026-08-17.md` | `00a9e0208842a0f935150ab83fda1b50f508675d116dcc4c4fffc41aac826661` | Exact committed preflight/remediation/review record |

## Apparent count/pin drift — reconciled

The historical ACK wire says `9 files, +375/-13` and cites the pre-format review hash
`993df7a6...`; the final commit says `10 files, +379/-13` and carries `2dd9105c...`. This is not an
undocumented divergence:

1. The ACK describes the staged set before the ACK file itself was added. Adding that five-line
   artifact moves the set from 9 to 10 paths and from 375 to 380 insertions.
2. Codex's later formatting-only sweep removed one Markdown formatting line from the review,
   moving 380 to 379 insertions. The formatting-correction record explicitly ordered restaging the
   final `2dd9105c...` review and corrected ledger pin before commit.
3. The delivered CLEAR and ACK wires intentionally remain byte-verbatim at the historical
   `993df7a6...` pin; the governing ledger and context-clear handoff explicitly distinguish that
   historical pin from the final post-format pin.

The arithmetic and the committed blobs therefore reconcile exactly with the disclosed transition.

## Repair and CI proof

- The committed contract differs from `d39ff34` only at the two already-reviewed fixture edits:
  current repository truth is `objects.required=true`, while only the named S23 historical
  pre-capture negative forces the objects row optional.
- The prior independent review recorded the exact 665-test gate, focused anti-rot gate, scoped Ruff,
  helper probes, and unchanged-store hashes. Because the committed test blob is byte-exact to that
  pin, those checks apply without qualification.
- Exact-head GitHub Actions run `32076527038` completed **success** on
  `a7b8bb222cf64ac437a148e59842e18da452b958`: Python checks passed, including pytest, Ruff,
  compilation, governance bootstrap, and storage policy; Frontend checks also passed.

## Boundaries

- No intake or capture was invoked by this audit.
- No governed store, paid archive, source, manifest, scheduler, or analysis-readiness state changed.
- The Footballguys horizon adjudication remains a separate David gate.
- The current working tree contains unrelated parked changes and post-commit handoff/wire files;
  they are outside `a7b8bb2`, preserved, and do not alter this commit verdict.
