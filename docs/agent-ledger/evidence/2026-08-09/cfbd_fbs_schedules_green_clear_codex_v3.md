# CFBD FBS schedules GREEN v3 — behavioral CLEAR for first capture

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Reviewer: Codex  
Verdict: **CLEAR FOR FIRST CAPTURE**

## Cleared implementation pins

- RED v7: `26a61170336cd6e2bfa2bcc299e6243ea88c8ac017cd2972617f8e9700d80335`
- Module v3: `22aff76c0a1beb863390044470177dc540b1e705ffa79986158e0db348999e3f`
- CLI v1: `a03bd4ed3a76242c1a94493a27b2a6f9b6a1ac2438eacf3fdc923141478f2f47`

Pins were independently recomputed and match the implementation packet.

## Independent checks

- Focused behavior, excluding only the intentionally held manifest-landing test: **190 passed,
  1 deselected** in 6.93s.
- Ruff across RED/module/CLI: **clean**.
- Before the live-manifest hazard was removed, the exact stabilized pins passed **191/191** and the
  backup suites passed **12/12**. The required manifest entry was then deliberately removed because
  the canonical directory was not yet populated and the live 10:15 backup reads working-tree state.
- Direct adversarial probes from prior review were repaired: nonexact URL identity, malformed prior
  state, audit-boundary failure, corrupt check/content/vintage replay, and complete kickoff lexical
  shape.
- The final residual was shown non-vacuous against module v2: only the new canonical-vintage payload
  substitution failed while the three prior replay controls passed. Module v3 verifies ordinary
  `load_vintage` and replay against freshly parsed, hash-verified retained raw content.

## Landing-order condition

The implementation is behaviorally clear for exactly one paid first capture. The manifest is not a
cleared pin at this moment. Required sequence:

1. capture into `app/data/sources/cfbd_fbs_schedules`;
2. independently verify the store is populated and measure the source;
3. re-add the required manifest entry;
4. rerun the full 191-test contract and backup suites;
5. perform zero-call local replay and then finish catalog/evidence/full-suite/landing checks.

No scheduler, cadence input, consumer, commit, or push is authorized by this review.

