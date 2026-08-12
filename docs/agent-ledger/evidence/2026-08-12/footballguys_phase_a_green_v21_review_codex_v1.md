# Footballguys Phase A GREEN v21 adversarial review — Codex v1

Date: 2026-08-12  
Layer: 1 — governed intake and persistence  
GREEN reviewed: `src/dynasty_genius/sources/footballguys_intake.py`  
GREEN SHA-256: `a0e7793b58b79e90a98371ede3ac2dd164e3504dd36b447a0244a7a0f97a832f`  
Frozen RED: `tests/contract/test_footballguys_phase_a_red.py`  
Frozen RED SHA-256: `528afecded652b5ad06070c1dd73ae46813f7da444f4aa3b1ee1447f7000dec6`

## Verdict

**CLEAR against RED v21; NOT CLEAR for production.** The four v21 repairs are correct and their
staged censuses show zero inherited regression. Two further writer-boundary defect families were
reproduced on the stable GREEN pin.

## Accepted v21 gate

- C1 24F→20F, H3 20F→18F, H2 18F→4F, M4 4F→0F; 602/602 strict exit 0.
- Full suite: 5,835 passed; the only 15 failures are the standing untracked cadence RED; zero
  collection errors; Ruff and strict compile clean.
- GREEN and RED hashes were stable before/after the strict and full-suite gates.
- The real-store byte-copy probe reported zero failures and live bytes remained unchanged.

## Findings

### 1. Critical — semantic writes report success against absent or corrupt retained evidence

After one valid `write_semantic_assertion`, Codex independently mutated each governed edge:

- delete the row from `semantic_attachments`;
- delete the row from `semantic_evidence_objects`;
- replace the retained evidence blob with different bytes.

Replaying the identical assertion returned `{"status": "noop"}` in all three cases while
`semantic_state` returned `unknown / active_evidence_unverifiable`. The writer's equality
predicate treats a missing attachment as acceptable and never descriptor/row-revalidates the
content-addressed evidence object before noop. The same omission lets a new assertion reuse an
existing evidence identity and report `written` against missing/corrupt object bytes.

That violates the live framing boundary that full attachment equality, including retained bytes,
precedes noop or evidence-id reuse. A success result cannot truthfully coexist with evidence the
reducer rejects.

Probe: a scratch-only v21 follow-up probe script (not retained in-repo). GREEN hash before/after:
`a0e7793b…` / `a0e7793b…`.

### 2. Critical — the write-time clock is neither validated nor pinned as one dependency

The semantic writer passes `self.clock()` directly as the optional `now` argument. With a clock
returning `None`, a semantic attachment declaring `2099-01-01T00:00:00Z` was accepted, persisted,
and reduced to `known redraft`, `eligible_for_phase_c=True`: `None` disabled the future check.
Text, integer, and naive clocks instead leaked bare `TypeError`.

The intake path consults the clock three times. Invalid clocks raised bare errors only after the
receipt and semantics stores had been created. A dependency returning valid once and `None`
later published the paid ZIP under `objects/` and then raised `AttributeError` before a receipt
could commit. This is a real orphan-publication path caused by dependency drift, not an injected
crash point.

The write operation must observe and validate one timezone-aware whole-second clock instant before
protected mutation, then reuse it for declared-retrieval validation, event allocation, and failure
recording. An invalid dependency must refuse by name without creating governed databases or raw
objects. Semantic writes require the same pure-before-store rule.

Probes: three scratch-only v22 clock probe scripts — a base clock probe, a none/future-clock probe, and a changing-clock probe (not retained in-repo). GREEN hash was byte-equal before/after
every probe.

## Scope

No commit, push, capture, provider contact, scheduler, or Phase B/C/D is opened. H2 QB rushing
remains **UNDER TEST** and unrelated.
