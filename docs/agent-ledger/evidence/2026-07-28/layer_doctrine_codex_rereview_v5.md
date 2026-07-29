# TW28-LAYERS — Codex round-5 corrected-freeze re-review

**Verdict:** NOT CLEAR

**Layer:** governance / cross-layer.

**Scope held:** review only. No layer-1/2 inventory, draft-capital work,
modeled-blank resumption, build, commit, or push.

## Checks performed

1. Rebooted from repository sources in the required order:
   `02` → `00` → corrected `05` → `01` → `03` → `AGENT_SYNC.md` →
   today's ledger.
2. Recomputed every submitted SHA-256. All three matched:
   - `05` v1.2.1:
     `ceb111146ce6ae99ae16d9d13ba47e6c549ba457cd64a09404665e09f4f231ad`
   - `AGENT_SYNC.md`:
     `b5c269ab2ee817af213206eeb0c9e67ac0d6675250addd92993d800bf8b8f200`
   - corrected disposition v3:
     `ca14b22c6d9b0a38e9c78a45a88f9535fe1d4172884d472c4ecb7e5ed083a10f`
3. Applied the fresh-agent boot test. Work routing still points only to the Layer
   Doctrine review; all fenced threads remain parked or not open.
4. Read the corrected authority metadata against every active authority statement
   in `02` and against the board's ratification gate.
5. Swept `AGENT_SYNC.md` for v1.2.0/v1.2.1 pins and current-round state.
6. Read the entire supplied disposition and searched it for the round-five F1
   disposition, new hashes, v1.2.1, and the updated defect count.
7. Re-ran multiline-safe wrapped-phrase and shorthand-enumeration sweeps: no hits.
8. Ran `.venv/bin/python3.14 scripts/validate_governance.py`: PASS, exit 0.
9. Ran `.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q`:
   4 passed.

## Confirmed round-five fixes

- `05` metadata is now genuinely section-scoped: §1 is standing doctrine; §2
  onward is pending, under review, and must not be cited as standing authority
  before David ratifies it.
- The correction note accurately records the recurring authority-leak family.
- Disposition v3 no longer invents a cross-document pre-commit duty.
- The choice not to amend `02`'s sweep rule tonight is scope-correct. The
  candidate amendment may remain named; it is not severe enough to route as a
  separate David decision inside this memorialize-and-ritualize thread.
- `AGENT_SYNC.md`'s doctrine version pins now say 1.2.1.

## Findings

### 1. `02` still activates §2's pending authority before David ratifies it

The corrected metadata at `docs/governance/05-layer-doctrine.md:5-10` says the
file is not uniformly standing doctrine and explicitly orders agents not to
cite §2 onward as standing doctrine until David ratifies it.

But the first document a fresh agent reads says, without a pending qualifier:

- `docs/governance/02-agent-operating-loop.md:56-60`: `05` **governs**
  sequencing/root-layer questions and **outranks** every plan, spec, ticket, and
  backlog;
- `:74-79`: the same authority claim is repeated and its mechanics bind the
  working loop.

Those are precisely the agent-authored authority placement and ritual in pending
§§2-3. A fresh agent receives them as binding workflow before it reaches `05`'s
warning. The v1.2.1 metadata fix therefore does not close the authority leak
across the active package.

The board compounds the ambiguity by making gate 2 only “David ratifies §2
onward of `05`,” while `02` v1.5.0 itself is an uncommitted governance amendment
that carries the enforcement text.

**Expected correction:** make the package's activation boundary explicit without
presuming David's decision. Either the affected `02` provisions are pending
until ratification of the package, or the board must identify exactly which
agent-authored artifacts David is being asked to ratify. The reviewer should
not choose that scope silently.

**Multiline-safe rerun:**

```text
rg -n -U "authority_section_2_onward|NOT David-ratified|governs\s+\*\*sequencing|outranks\s+every" \
  docs/governance/05-layer-doctrine.md \
  docs/governance/02-agent-operating-loop.md \
  AGENT_SYNC.md
```

### 2. The live board still reports the previous three-finding round

`AGENT_SYNC.md:14-15` says:

```text
round-four review returned NOT CLEAR (3 findings), dispositioned,
corrected freeze re-issued — awaiting Codex review
```

At the moment this freeze was issued, the live state was the later two-finding
review: both findings accepted, `05` advanced to v1.2.1, and a new corrected
freeze awaited Codex. The version pins were synchronized, but the board's
current-state sentence was not.

This repeats the stale-round half of the earlier board finding. Fresh-agent work
routing still passes, but the active review state is false.

**Rerunnable probe:**

```text
nl -ba AGENT_SYNC.md | sed -n '8,25p'
```

### 3. The supplied durable disposition does not record round-five F1 and retains the old freeze

The only supplied disposition is
`layer_doctrine_disposition_v3.md`. It remains titled and framed as Claude's
disposition of the prior three-finding review at `:1-4`. It adds a correction
for round-five F2 at `:12-21`, but contains no disposition of round-five F1
(section-scoped authority), no v1.2.1 freeze, and no current two-finding outcome.

Its frozen table at `:88-96` still records the previous hashes:

- old `AGENT_SYNC.md` `829ff50f...`;
- old `05` `c6c5e0de...` v1.2.0.

Its running count at `:98-103` remains 19 across four rounds rather than the
submitted 21 across five. The chat summary carries the missing facts, but the
durable artifact does not.

**Rerunnable probe:**

```text
rg -n -U "SECTION-SCOPED|round-5|v1\.2\.1|ceb111|b5c269|Twenty-one|21 defects" \
  docs/agent-ledger/evidence/2026-07-28/layer_doctrine_disposition_v3.md
```

Expected result on the submitted freeze: only the F2 correction's phrase
“round-5 finding 2” appears; the F1 disposition and current freeze facts are
absent.

## Boundary on this verdict

The metadata design itself is sound, version pins are updated, boot routing
passes, and deterministic checks are green. None resolves the binding-status,
live-state, or durable-record contradictions above.

