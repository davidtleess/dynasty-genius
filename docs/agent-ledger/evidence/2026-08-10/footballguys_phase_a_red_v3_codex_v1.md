# Footballguys Phase A RED v3 — Codex

Date: 2026-08-10
Author: Codex, RED owner
Authority: Claude accepted all seven findings from the adversarial GREEN review of `f9b57d3` and
requested RED v3 before repairing GREEN.

## Artifact

- Path: `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256: `3b5383380c2bdbe0d9f0d85da10704bed721f7033f0a0f2a67b8c6331eeaa565`
- Size: 1,674 lines / 68,244 bytes
- Supersedes amended RED pin:
  `35e48037034983234fd05f66cc22876ece713bfe99e7db89b841e417bba600aa`
- Framing pin remains:
  `f44b5ab008c02206cbcba26dacab6efdfd85fcdc279282207c4ae5e99d7301ff`

## Contract changes

RED v3 preserves every prior test and makes these production boundaries executable:

1. **Real selected-role schema validation:** malformed ADP, malformed identity sidecar, and an ADP
   payload with no `adp_*` field all refuse before publish; no `fault_at` proxy can satisfy them.
2. **Durable semantic seam:** `write_semantic_assertion(record)` and `semantic_state(key=...)` have
   a frozen nested record shape. Evidence bytes are supplied to the writer; GREEN computes and
   persists hash/size. First write, idempotent no-op, changed-claim conflict, and fresh-root durable
   read-back are asserted.
3. **Epoch-correct fixture manifests:** the checked-in repository row remains optional during the
   empty pre-capture epoch; ordinary driver positives model the post-capture epoch with objects
   required. A dedicated pre-capture test proves raw publication refuses while the row is optional.
4. **Readiness semantics:** unknown horizon advances acquisition freshness as
   `review_required/not-AR`; a retained/hash-verified provider-authentic assertion unlocks AR in
   the fixture world. Transition tests seed that assertion rather than inventing readiness.
5. **Complete staged write:** monkeypatched legal short writes must converge to the complete source
   payload; the retained bytes, canonical filename, and receipt must agree.
6. **Directory durability:** the fsync oracle fingerprints descriptor identities and requires the
   objects parent itself, plus staging/objects `st_dev` equality.
7. **Persisted receipt integrity:** post-receipt byte corruption and a hard-link alias both render
   the named integrity state on a fresh load. The receipt schema must persist all signed fields,
   including `source` and ordered role records. A signed-field mutation cannot become a clock.
8. **Global cross-store conflict:** independently backed-up valid receipt/observation databases
   with the same offering and different signatures are restored together; the union must render
   `offering_identity_conflict`, with no AR or clock fallback.
9. **Durable attempt overlay:** a malformed intake is re-read through a fresh composition root and
   must render the literal failed-attempt notice without advancing acquisition freshness.

## Failing census against landed GREEN `09e2955e...`

```text
201 collected
24 failed
177 passed
0 skipped
0 xfailed
```

The 24 failures are expected and attributable:

- 3 real role-schema failures;
- 2 durable semantic-writer/read-back/conflict failures;
- 6 unknown-horizon readiness failures (success + five crash convergence cases);
- 2 transition tests blocked on the missing semantic seam;
- 1 short-write coherence failure;
- 1 wrong-parent fsync failure;
- 4 persisted integrity/schema/global-conflict failures;
- 1 post-receipt hard-link integrity failure;
- 1 optional-row first-capture refusal failure;
- 1 durable failed-attempt visibility failure;
- 1 direct unknown-horizon readiness/AR failure;
- 1 effective-horizon-to-AR wiring failure.

The total above is 24; some categories deliberately distinguish the receipt-schema and hard-link
controls from the broader persisted-state trio so a partial integrity repair cannot turn the suite
green.

## Quality and scope

- `py_compile`: pass;
- Ruff: pass;
- `git diff --check` on the RED: pass;
- skip/xfail/skipif scan: zero;
- targeted short-write and fsync tests fail on their load-bearing byte/descriptor assertions,
  not on readiness preconditions;
- no production file, manifest, ignore rule, runtime namespace/store, provider payload, scheduler,
  Phase B/C/D surface, commit, or push was changed by Codex.

The landed `f9b57d3` remains unpushed provenance. RED v3 and repaired GREEN must travel together in
one separately reviewed act; authoring this RED does not authorize that landing.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
