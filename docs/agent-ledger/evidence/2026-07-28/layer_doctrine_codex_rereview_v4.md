# TW28-LAYERS — Codex round-4 corrected-freeze re-review

**Verdict:** NOT CLEAR

**Layer:** governance / cross-layer.

**Scope held:** review only. No layer-1/2 inventory, draft-capital work,
modeled-blank resumption, build, commit, or push.

## Checks performed

1. Rebooted from the corrected repository instructions in the mandatory order:
   `02` → `00` → `05` → `01` → `03` → `AGENT_SYNC.md` → today's ledger.
2. Recomputed every submitted SHA-256. All four matched:
   - disposition v3:
     `19211201d60abb174f4c2082b35bc9607177c6b7bb6c7a46ffac834f21297a6c`
   - `02`: `7a5616749224a3d045842310f976452edce7020f93d32be1c7c4ad5a7a01108b`
   - `AGENT_SYNC.md`:
     `829ff50fbe856ef61bcd135720174f5be1a46f33440b83a50ac6c454a4d8a8c2`
   - `05`: `c6c5e0dedbe989b8e58b51401cb437d5a5aa38c0d6023c4373188527a37f516b`
3. Re-ran David's fresh-agent boot test. Routing still passes: only the Layer
   Doctrine review begins; all fenced work remains parked or not open.
4. Re-ran the cycle-overclaim and shorthand-enumeration sweeps with multiline
   mode:

   ```text
   rg -n -U "full\s+adversarial\s+cycle" docs/governance
   rg -n -U "1\s+ingest\s*·\s*2\s+curate" <nine active pointer/ritual files>
   ```

   Both returned no hits.
5. Ran `.venv/bin/python3.14 scripts/validate_governance.py`: PASS, exit 0.
6. Ran `.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q`:
   4 passed.
7. Compared the board's ordered gates with the file-level metadata and §Status
   in `05`; compared disposition v3's stated sweep requirement with the actual
   pre-commit and post-commit rules in `02`.

## Probe correction accepted

The prior v3 review's rerun command
`rg -n "full adversarial cycle" docs/governance` was unsound because the phrase
wrapped across a newline. The finding was real; the supplied reproducer could
have manufactured a false negative. That prior artifact remains immutable as
the historical review packet. This review corrects the habit and uses `rg -U`
with `\s+` for prose-wrapped phrase probes.

## Findings

### 1. Whole-file authority metadata still grants standing authority to unratified agent text

`docs/governance/05-layer-doctrine.md:5` says:

```text
authority: standing doctrine
```

That is file-scoped metadata. The same header says the codification is not
David-ratified at `:8`, and `:23-26` repeats that §2 onward remains under review
and unratified. The corrected board makes David's ratification of §2 onward a
separate, still-open gate at `AGENT_SYNC.md:17-25`.

Those statements cannot all govern cleanly. A fresh agent or validator reading
the ordinary `authority` field can treat the agent-authored authority placement,
ritual, and failure record as standing doctrine before gate 2 occurs. The prose
attribution split does not make the whole-file metadata section-scoped.

This is the authority analogue of the earlier whole-document attribution defect:
the file header still gives the whole file a status only §1 has earned.

**Expected correction:** make the metadata itself section-aware and
non-contradictory—for example, explicitly scope standing authority to §1 and
mark §2 onward as proposed/pending ratification—without selecting David's
eventual ratification decision.

**Rerunnable probe:**

```text
nl -ba docs/governance/05-layer-doctrine.md | sed -n '1,26p'
```

### 2. Disposition v3 attributes a cross-document duty to a rule that only requires an intra-document sweep

`layer_doctrine_disposition_v3.md:8-12` says `02` §Post-fix sweep requires the
author to grep the **"entire document set"**, and names failure to sweep `02`
after fixing `05` as violation of that rule.

The actual binding text at
`docs/governance/02-agent-operating-loop.md:255-259` says:

- pre-commit author sweep: grep the **entire document**—singular—for references;
- dependent documents and downstream modules: reviewer **SHOULD** scan them only
  in the **post-commit** sweep.

There has been no commit. The rule therefore does not define the cross-document
pre-commit duty the disposition says failed. The diagnosis is directionally
right—the dependent `02` copy was missed—but the claimed governance mechanism
is not present.

**Expected correction:** either extend the pre-commit sender rule to the
affected dependent-document set (if that is the intended ritual), or stop
claiming the current rule required it. This is a governance choice about where
the duty lives, not wording that the reviewer should silently select.

**Rerunnable probe:**

```text
rg -n -U "post-fix sweep|entire document set|entire document" \
  docs/governance/02-agent-operating-loop.md \
  docs/agent-ledger/evidence/2026-07-28/layer_doctrine_disposition_v3.md
```

## Confirmed fixes from round four

- The wrapped “full adversarial cycle” claim is gone from governance.
- `02` no longer carries the shorthand layer enumeration.
- `AGENT_SYNC.md` records the actual review round.
- The board now exposes four ordered, non-implying gates: reviewer CLEAR,
  David ratification, commit authority, and push authority.
- The validator passes and the focused tests are green.

Those confirmations do not resolve the two authority/process contradictions
above.

