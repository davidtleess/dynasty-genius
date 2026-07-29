# TW28-LAYERS — Codex round-9 review of the round-8 corrected freeze

**Verdict: NOT CLEAR — three findings.**

Layer: `governance` / `cross-layer`. The layers 1–2 dependency check is not applicable: this
reviews the rule and bootstrap package that govern layer selection. It opens no inventory,
draft-capital, modeled-blank, roster-audit, build, commit, or push work.

## Checks independently run

- Completed the current bootstrap in order: `02`, `00`, `05`, `01`, `03`,
  `AGENT_SYNC.md`, and today's ledger.
- Recomputed all ten submitted SHA-256 values for disposition v5, the eight bootstrap files,
  the validator, and its test; all matched.
- Recomputed the unchanged hashes for `05`, `02`, `AGENT_SYNC.md`, and disposition v4; all
  still matched.
- Confirmed both advertised fixes:
  - all eight primary pointer lines now say the every-session read and ritual obligations are
    agent-authored, pending David's ratification, and not yet binding;
  - `REQUIRED_BOOTSTRAP_PHRASES` now checks every `BOOTSTRAP_FILES` entry, and the focused
    test iterates those files.
- `.venv/bin/python3.14 scripts/validate_governance.py`: PASS, exit 0.
- `.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q`: 5 passed.
- Falsified the pointer-local claim by replacing the validator's read function in memory with a
  binding `05` pointer plus the two required phrases in an unrelated footer. The validator
  returned `[]` (no failures); finding 2 gives the rerunnable probe.
- The full sprint tollgate was still running when this verdict was written. Claude explicitly
  said its result would be reported before commit. It supplies no clearance evidence yet.

## Findings

### 1. The sixth authority leak survives in the unchanged central mechanism: `02` and the validator still command and enforce the unratified read/ritual

The eight first-contact pointers are now qualified correctly. The next file a fresh agent reads is
not:

- `02:6` says Required Reading 2a, the preflight/ledger layer fields, and the layer-discipline
  mechanics are pending and not ratified.
- `02:47` nevertheless says read `05` **"always, every session, no exceptions."**
- `02:68-74` says the mechanics are not binding, but `02:88` then says
  **"Read it during bootstrap, every session. Two mechanics bind the working loop."**
- `02:126-132` separately says every agent **must** record the pending preflight fields, outside
  the qualified `§Layer discipline` subsection.

The validator and its test activate the same pending delivery mechanism:

- `scripts/validate_governance.py:66-69` says the every-session read is
  **"enforced rather than asserted"** and makes the `05` pointer a required bootstrap target.
- `tests/test_validate_governance.py:44-55` is named
  `test_governance_validator_enforces_layer_doctrine`, says `05` is read every session, and
  requires that target.
- `docs/README.md:18`, under `Canonical Governance`, still says **"Read every session"** with
  no pending qualifier.

Those statements contradict `AGENT_SYNC.md:28-36`, which places Required Reading 2a, the
preflight/ledger fields, all pointer text, and the validator pins inside the pending,
non-binding package. Fixing the eight primary lines but retaining active mandatory language and
mechanical enforcement centrally is the sixth instance of the same authority-leak family.

Rerunnable sweep:

```bash
rg -n -H -i \
  "always, every session|read every session|read it during bootstrap|two mechanics bind|must establish|enforced rather than asserted" \
  docs/governance/02-agent-operating-loop.md docs/README.md \
  scripts/validate_governance.py tests/test_validate_governance.py
```

### 2. The new bootstrap guard is whole-file phrase presence, not a guard on the `05` pointer; it can still pass a binding first-contact pointer

`validate_bootstrap_files` reads each complete file and accepts it when each required phrase occurs
**anywhere** in that file (`scripts/validate_governance.py:196-205`). The new focused test repeats
the same whole-file predicate (`tests/test_validate_governance.py:91-97`). Neither check associates
the pending language with the `05` pointer or detects a contradictory binding instruction.

Rerunnable falsifier:

```bash
.venv/bin/python3.14 -c 'import scripts.validate_governance as v; v.BOOTSTRAP_FILES=["AGENTS.md"]; v.REQUIRED_BOOTSTRAP_TARGETS=["docs/governance/05-layer-doctrine.md"]; v.REQUIRED_BOOTSTRAP_PHRASES=["PENDING DAVID\x27S RATIFICATION","NOT YET BINDING"]; v.read_text=lambda _p: "2a. docs/governance/05-layer-doctrine.md — ALWAYS, EVERY SESSION; binding.\nHistorical footer: PENDING DAVID\x27S RATIFICATION; NOT YET BINDING."; failures=[]; v.validate_bootstrap_files(failures); print(failures)'
```

Actual result: `[]`.

There is already a live same-file illustration: `docs/README.md:9` supplies both required phrases,
so the file passes, while its second `05` pointer at `docs/README.md:18` says `Read every session`
under `Canonical Governance` without the pending boundary. Claude's negative control correctly
proves removal of the only phrases fails; it does not prove the phrases qualify the instruction
they are meant to guard.

### 3. The fresh-agent board is stale and its ordered ratification/commit model contradicts the new conditional commit state

`AGENT_SYNC.md:14-16` still reports six review rounds, a latest three-finding NOT CLEAR, and
24 defects. The durable ledger now reports eight rounds, a latest two-finding NOT CLEAR, and 26
defects (`docs/agent-ledger/2026-07-28.md:2583-2631`). This reintroduces the stale-board defect the
round-6 correction claimed to fix.

The same board says the four gates are **"in order"** and places David's ratification before commit
authorization (`AGENT_SYNC.md:18-38`). The durable ledger now says gate 2 remains open while gate 3
is given conditionally (`docs/agent-ledger/2026-07-28.md:2579,2631`), and the submitted packet says
the intended action after CLEAR is to commit the doctrine while it remains explicitly unratified.

That may be David's intended override, but it is not represented on the cold-start board. A fresh
agent must not be left to choose whether the ordered ratification gate still blocks the conditional
commit or whether the 22:49 word supersedes that order. Record the conditional word and the truthful
gate relationship durably before any commit; do not resolve it only in cockpit prose.

The disposition's count also says **"26 defects across eight rounds"** but prints seven round
figures (`6 · 5 · 5 · 3 · 2 · 3 · 2`; disposition v5 final section and ledger `:2628`). If the
superseded in-flight review is the eighth round, name how it is counted; otherwise the round count
is one high.

## Scope and gate state

David's 22:49 word is conditional commit authorization only. This NOT CLEAR does not satisfy its
condition. It is not ratification and not push authorization. The full sprint tollgate had not
reported a terminal result at verdict time; even absent the findings, the packet was not
gate-complete.
