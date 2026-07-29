# TW28-LAYERS — Codex round-3 re-review

**Verdict:** NOT CLEAR

**Layer:** governance / cross-layer.

**Scope held:** review only. No layer-1/2 inventory, draft-capital ticket or repair,
modeled-blank resumption, code change, commit, or push.

## Checks performed

1. Rebooted from the repository instructions in the mandatory order: `02`, `00`,
   corrected `05`, `01`, `03`, then `AGENT_SYNC.md`.
2. Applied David's fresh-agent test before relying on the implementer's summary:
   asked what the board authorizes a new agent to begin.
3. Recomputed all five submitted frozen SHA-256 values; each matched:
   - `05`: `c6c5e0dedbe989b8e58b51401cb437d5a5aa38c0d6023c4373188527a37f516b`
   - `02`: `fd5012c2c5d4e52211f3fdbf581e99864fc6282f6d8b3b218ee827c7cd4cbaf1`
   - `AGENTS.md`: `4e544402871ebedf86637245ef37ca49f554366cae9268f1d258a297f7a9bd4b`
   - `docs/README.md`: `33ad6d7173ae86bf3557516f75e47590cd8a3f5ec343ffe0eeca380ed189f12e`
   - `AGENT_SYNC.md`: `5c0f710066ab76f9496d2429ae032bcc36a4f9c94a60d6cd16056e258e83a28b`
4. Read the corrected artifacts and round-3 disposition directly, then searched the
   governance and board files for the claims round 3 said it removed or updated.
5. Ran `.venv/bin/python3.14 scripts/validate_governance.py`: PASS, exit 0.
6. Ran `.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q`:
   4 passed.

## Fresh-agent boot result

The central boot-state test **passes**. A fresh agent would begin only the Layer
Doctrine review. The board parks modeled-blank, roster-audit, prospect-prior and
false-prior work, and leaves the layer-1/2 inventory and draft-capital question not
open. No work on those items is authorized by the corrected board.

That routing success does not clear the content defects below.

## Findings

### 1. `02` still overclaims a completed review cycle

`docs/governance/02-agent-operating-loop.md:98-102` still says the cockpit ran a
**"full adversarial cycle."** The same file defines the cycle as repeating until the
independent reviewer replies with explicit CLEAR at `:227-238`. That did not happen:
the modeled-blank re-review returned NOT CLEAR and remains parked.

Round-3 disposition correctly identifies this as false at
`layer_doctrine_disposition_v2.md:44-55`, but the frozen `02` retains it. The
post-fix sweep therefore did not reach every governing copy of the assertion.

**Rerunnable probe:**

```text
rg -n "full adversarial cycle" docs/governance
```

Expected correction: use the truthful incomplete state (for example, “multiple
adversarial rounds”) rather than claiming cycle completion.

### 2. `02` still paraphrases the six layers after round 3 says the enumeration is gone

`docs/governance/02-agent-operating-loop.md:67-71` first says §1 is David-verbatim,
then restates his six layers in agent shorthand:

```text
1 ingest · 2 curate · 3 models · 4 analysis · 5 context · 6 front-end
```

`docs/governance/05-layer-doctrine.md:15-18` says agents may not paraphrase §1 and
must quote it or point to it. The round-3 disposition says at
`layer_doctrine_disposition_v2.md:39-42` that the enumeration is gone from all eight
pointers. It is not gone from this governing ritual document.

**Rerunnable probe:**

```text
rg -n "1 ingest" docs/governance/02-agent-operating-loop.md
```

Expected correction: point to `05` §1 and, if the ruling itself is needed, retain
only the exact quotation. Remove the agent-vocabulary layer enumeration.

### 3. The new board freezes a stale round state and skips the ratification gate

`AGENT_SYNC.md:12-14` says round-three findings **"are being dispositioned."** The
submitted disposition and corrected freeze already exist; the live state is that
round 3 is awaiting Codex review. The board was stale at the moment it was frozen.

The same lines say the next gates are **Codex CLEAR, then David's keystroke to
commit**. But `docs/governance/05-layer-doctrine.md:23-26` explicitly says §2 onward
is not yet David-ratified and that ordering/hardening work did not constitute
ratification. David's “let it finish” keeps the review moving; it does not, on the
record presented, ratify every agent-authored sentence. The board therefore omits
the ratification gate that `05` itself requires.

Expected correction: state the actual review round, then make the gates explicit:
Codex CLEAR; David ratification of §2 onward; and the separately authorized
commit/push actions. A single David instruction may satisfy more than one gate only
when it explicitly does so.

## Boundary on this verdict

The validator and focused tests are green, and the top-level fresh-agent routing is
correct. Those checks do not falsify the three textual/state findings above. No full
sprint tollgate was requested or needed to establish this markdown-only NOT CLEAR.

