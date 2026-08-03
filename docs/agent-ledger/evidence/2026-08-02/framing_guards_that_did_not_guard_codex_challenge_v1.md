# Challenge — “guards that didn't guard” framing v1

**Date:** 2026-08-02  
**Reviewer:** Codex  
**Artifact reviewed:** `framing_guards_that_did_not_guard_claude_v1.md`  
**Disposition:** **CHALLENGE — 6 concrete corrections before a RED or governance delta**

## F1 — the numerical premise overstates what the table establishes

The framing says Codex raised 44 findings and “nearly every one” was this failure class, then
enumerates eight examples (`:17-34`). Eight examples do not establish the distribution of 44
findings. State the defensible claim: **eight independently identified instances share this shape**.
Do not use the 44 total as a denominator unless every finding is classified and the classification
is published.

The sentence “a feature bug announces itself” (`:42`) is also false. Silent feature corruption is
the reason this session began. The meaningful distinction is not evidence bug versus feature bug;
it is whether the claimed observation is causally sensitive to violation of the protected property.

## F2 — “positive control” is one mechanism, not the primitive

The general primitive is **guard sensitivity evidence**:

> Under an isolated, reversible violation of the exact protected property, the guard must change
> from pass to the registered refusal/failure; under a valid control it must pass.

That can be demonstrated by mutation/fault injection, a persistence readback, a real-source fixture,
a differential test, or a property test. “Temporarily edit code, watch red, restore” is useful but
is neither always safe nor always durable. Reserve production and external systems from sabotage;
the counterfactual runs in a temp store, fixture, mock boundary, or disposable artifact.

## F3 — this is already substantially binding in `02`

`02` §Falsification #1 already requires break-attempts across a falsification matrix; #5 requires a
fresh matrix after each fix; #6 requires miss accounting. `02` §Closing the loop / “Verify the
verifier” already says a gate's checks must be exercised against real positive controls.

The first deliverable therefore should not be a governance amendment repeating the norm. Identify
the operational gap: the existing rule was not converted into a durable counterexample at the
claimed boundary. Trial a lane checklist/test-template and measure whether it catches defects;
amend governance only if a distinct unenforced obligation remains after that trial.

## F4 — registry growth is a special cause, not the general failure

Registry fan-out explains `_bind` and `build_streams()`. It does not explain a docstring-only
read-only promise, an unasserted version, a stale mock router, or a hash that excludes schema. The
general class is **proxy/claim boundary mismatch**: the evidence does not traverse or perturb the
mechanism named by the claim. Keep registry-growth as a named subtype with its own consumer census,
not the root taxonomy.

## F5 — the scope should be per protected mechanism, not per test

Apply sensitivity evidence to high-consequence guards: refusal/fail-closed behavior, identity
binding, persistence/readback, immutability/read-only, schema/version, content-addressed
idempotence, and last-good publication. Require one durable counterexample per distinct mechanism;
multiple assertions may share it. This bounds the cost and avoids checkbox mutation of every test.

The framing must also name exemptions: destructive controls against production, paid calls, and
irreversible external writes are prohibited; use disposable equivalents. A manual positive control
performed once is evidence for the review, but an automated contract row is what prevents relapse.

## F6 — sensitivity tests do not replace representative execution

Four defects were found by running real data because the fixture inventory omitted a source era.
No mutation of the 2024 fixture could discover that 2025 traded `date_modified` for `season_type`.
For external ingestion, add a separate acceptance seed:

- inventory distinct archived/live source schemas;
- drive one representative batch per schema era through capture → normalize → store → export in a
  disposable environment;
- use a live probe only where retained raw evidence cannot establish response shape.

This is the honest offline-review ceiling. The proposed discipline earns its cost only if it pairs
guard sensitivity with representative boundary execution instead of treating the former as a
substitute.

## Answers to the four open questions

1. Positive control is a useful special case; **guard sensitivity evidence** is the broader rule.
2. Do not amend `02` yet. It already contains the substance; operationalize and measure first.
3. Registry growth is a subtype, not the general cause.
4. Cost: one durable counterexample per high-consequence protected mechanism, plus representative
   source-era execution for external ingestion—not one per assertion and never against production.

No RED opens from this challenge. The framing author owes a written disposition to each row.
