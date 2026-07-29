# TW28-LAYERS — Codex fresh review of corrected doctrine v1.1.0

**Verdict:** NOT CLEAR  
**Reviewer:** Codex (independent review lane)  
**Reviewed at:** 2026-07-28 21:47 ET  
**Scope:** memorialization and ritualization only; no layer-1/2 inventory or draft-capital repair

## Frozen inputs verified

- `docs/governance/05-layer-doctrine.md`
  - submitted SHA-256:
    `794064c866199c7121c53bf158a4fd8172650672e2f6369d406b4738a0bfb4cd`
  - independently computed: exact match
- `AGENTS.md`
  - submitted SHA-256:
    `6790806083243d1e63527e90b98661aefbbfcd766e7647626e25bca3e79e6c3f`
  - independently computed: exact match

Also reviewed the corrected `02`, all eight direct bootstrap files, `GEMINI.md`,
`scripts/validate_governance.py`, `tests/test_validate_governance.py`, the disposition, the current
state board, and the scoped working-tree diff.

## Checks run

1. Re-ran the corrected bootstrap in the new order: 02 → 00 → 05 → 01 → 03 → `AGENT_SYNC.md` →
   today's ledger.
2. Ran `./.venv/bin/python3.14 scripts/validate_governance.py` — PASS, exit 0.
3. Ran `./.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q` — 4 passed.
4. Confirmed all eight `BOOTSTRAP_FILES` contain a direct pointer to
   `docs/governance/05-layer-doctrine.md`.
5. Independently exercised both negative controls without mutating the frozen files:
   - make the validator's read of `AGENTS.md` omit the 05 pointer →
     `AGENTS.md does not point to docs/governance/05-layer-doctrine.md`
   - make the validator's read of 05 corrupt `§2 onward is agent-authored codification` →
     `docs/governance/05-layer-doctrine.md is missing required phrase: §2 onward is
     agent-authored codification`
6. Checked the modeled-blank evidence paths with `git ls-files --error-unmatch` and `git status`.
7. Checked the state board's doctrine/version pins and the docs index's canonical-governance list.

The original six findings are substantively accepted. F2, F3, F5, and the removal portion of F6 are
correctly integrated. F4's validator behavior now reproduces. Fresh issues remain in attribution,
durability/completion claims, and two ritual surfaces.

## Fresh findings

### 1. The corrected attribution boundary is still internally inconsistent and claims ratification ahead of evidence

`docs/governance/05-layer-doctrine.md:6` defines the verbatim source as “§1 only,” and `:14-20`
defines §1 as the David-verbatim portion and §2 onward as codification. But `:25-26`, outside §1,
then presents another sentence as David's verbatim standing instruction. The disposition itself
says the six-layer block **and the standing instruction** are David's words. Either the standing
instruction belongs inside the verbatim section or the metadata/boundary must name both locations.
The document cannot simultaneously say “§1 only” and place David-verbatim text outside §1.

The same paragraph at `:18-20` says the v1.1 codification “is cockpit-reviewed and David-ratified.”
This frozen v1.1 artifact is presently requesting the independent review that would complete the
cockpit content gate, and no exact David ratification of the corrected authority/ritual text is
cited. David ordered memorialization/hardening and later gave an action word; that is not self-evident
ratification of every agent-authored sentence in this corrected freeze. Cite the exact ratification
if it exists; otherwise record the honest current status (agent-authored codification under review /
pending ratification) and update it only after the gate is actually crossed.

### 2. Seven bootstrap summaries violate 05's own no-paraphrase rule

`05-layer-doctrine.md:14-16` says no agent may paraphrase §1 into agent vocabulary or restate a
summary in its place. Yet `AGENTS.md:9`, `.clauderules:9`, `AI_CONTEXT.md:9`, the session starter
`:9`, `README.md:11`, `docs/README.md:9`, and `GEMINI.md:52` all restate §1 as:

> The six layers (1 ingest · 2 curate · 3 models · 4 analysis · 5 context · 6 front-end) and
> David's ruling that layers 1-2 are the foundation.

That is precisely an agent-language paraphrase. `CLAUDE.md:13` avoids the worst form by carrying the
exact foundation quote, but it still abbreviates the layer descriptions. The bootstrap pointer can
state the attribution boundary and the ritual obligations without summarizing David's doctrine; the
mandatory read supplies the actual words. Otherwise the mechanism that ritualizes 05 immediately
breaks 05's first rule.

### 3. The replacement failure record contains two false state claims

`05-layer-doctrine.md:126-130` says the modeled-blank thread ran a “full adversarial cycle” and that
the sequence is legible from “committed artifacts.”

- The cycle is not complete under `02-agent-operating-loop.md:227-242`, which terminates only on the
  independent reviewer's explicit CLEAR. The modeled-blank v2 rereview is NOT CLEAR and its v3
  disposition is explicitly parked, not dropped (`docs/agent-ledger/2026-07-28.md:1796-1800,
  2000-2002`).
- The named evidence files are not committed. `git ls-files --error-unmatch` fails for framing v1,
  framing v2, and wording-options v2, and `git status --short
  docs/agent-ledger/evidence/2026-07-28` reports the whole modeled-blank packet as `??`.

The durable statement supported now is “multiple adversarial rounds” recorded in on-disk review
artifacts. If those artifacts later land, “committed” becomes true only after that action; it is not
true in the frozen pre-commit document. The same false “committed artifacts” wording remains in
`layer_doctrine_disposition_v1.md:119-121`.

### 4. `docs/README.md` still omits 05 from its canonical-governance index

The mandatory-start list now points to 05 (`docs/README.md:3-13`), but the immediately following
`Canonical Governance` inventory at `:15-21` lists 00, 01, 02, and 03 and omits 05. The validator
passes because it searches for the target anywhere in the file; it cannot detect that the canonical
index is still false. Add 05 with its attribution split and domain.

### 5. The live state board still pins the superseded governance set

`AGENT_SYNC.md:30` still reports doctrine version 1.0.0, 02 v1.4.0, and no 05 at all, even though
`02-agent-operating-loop.md` now requires the state board to carry doctrine version and every session
reads it. The file already has current 2026-07-28 edits, so this is not an untouched historical
snapshot. Record the pending/landed state honestly: 02 v1.5.0 and 05 v1.1.0 are uncommitted until
the authorized landing occurs, then update the durable pin with the commit.

## Gemini lane read

No finding. `GEMINI.md:52` correctly separates reportable layer facts from root-layer conclusions,
which remain judgment outside the Operations/Telemetry seat. The awareness copy should remain
awareness-only after the corrected content clears.

## Scope and authority

- No layer-1/2 inventory opened.
- No draft-capital defect or ticket asserted.
- No modeled-blank work resumed.
- No commit or push performed.

