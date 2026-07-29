# TW28-LAYERS-1 — Codex hardening review v1

**Verdict:** NOT CLEAR  
**Reviewer:** Codex (independent review lane)  
**Reviewed at:** 2026-07-28 21:20 ET  
**Scope:** memorialization and ritualization only; no draft-capital investigation or repair

## Frozen inputs reviewed

- `docs/governance/05-layer-doctrine.md`
  - SHA-256 `f11ea7f22dfc409e44831c182b069a7d2f8c70e8ba630e6c0e9f52a3504acd99`
- `docs/governance/02-agent-operating-loop.md`
  - SHA-256 `1e878b7acb1a83163f756594c25fcb698c18703e888acc102e3cc0fa0ab3e03a`
- `CLAUDE.md`
  - SHA-256 `4f7b1cb49fa19fb72c9e03801cb08d9b02d8fcfbbd35ccdb91a78fa3d2d6d83b`

## Checks performed

1. Read the three frozen artifacts and their scoped git diff.
2. Compared the authority language with:
   - `docs/governance/00-product-constitution.md:176-197,293-297`
   - `docs/governance/01-north-star-architecture.md:204-229`
3. Checked every bootstrap target named by `scripts/validate_governance.py:39-58`, plus the stale
   bootstrap reset in `docs/governance/02-agent-operating-loop.md:252-260`.
4. Inspected the governance validator and its focused tests.
5. Ran:
   - `./.venv/bin/python3.14 scripts/validate_governance.py` — PASS
   - `./.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q` — 3 passed
6. Independently reproduced the runtime draft-field counts with:

```bash
jq '{captured_at, universe:(.players|length), engine_b:([.players[]|select(.valuation.engine_path=="ENGINE_B")]|{rows:length,round_present:map(select(.nfl_draft_round!=null))|length,pick_present:map(select(.nfl_draft_pick!=null))|length,class_present:map(select(.draft_class!=null))|length}), engine_a:([.players[]|select(.valuation.engine_path=="ENGINE_A")]|{rows:length,round_present:map(select(.nfl_draft_round!=null))|length,pick_present:map(select(.nfl_draft_pick!=null))|length,class_present:map(select(.draft_class!=null))|length}), all:{round_present:([.players[]|select(.nfl_draft_round!=null)]|length),pick_present:([.players[]|select(.nfl_draft_pick!=null)]|length),class_present:([.players[]|select(.draft_class!=null)]|length)}}' app/data/valuation_runtime/universe_pvo_runtime.json
```

Result:

- `captured_at`: `2026-07-28T13:30:04.081845+00:00`
- universe: 12,203 rows
- Engine B: 501 rows; all three fields present on 0
- Engine A: 80 rows; all three fields present on 80
- whole universe: all three fields present on 80

The submitted figures reproduce exactly.

## Findings

### 1. The document falsely attributes agent-authored codification to David

`05-layer-doctrine.md:5-14` labels the whole document “David-authored,” gives `author: David
(verbatim)`, and says the whole document is his own words rather than an agent synthesis. That is
false on the face of the review request: the authority placement and ritual mechanics are expressly
Claude Code's judgments. Only the blockquote at `:21-49` and the separately quoted priority sentence
at `:16-17` are represented as David's verbatim words.

The same over-attribution propagates into `02-agent-operating-loop.md:46,57,67` and `CLAUDE.md:13`.
Separate the verbatim source from the implementing codification: identify exactly which passages are
David's words, label the surrounding authority/evidence/ritual prose as agent-authored codification,
and do not make an unratified authority interpretation appear David-authored.

### 2. The failure narrative turns a field-presence measurement into an unproved root-cause finding

The probe establishes that the served PVO's Engine B rows do not materialize the three draft fields.
It does **not** establish `05-layer-doctrine.md:100-103`'s claim that data is “not ingested, or not
joined through to where the model reads it,” nor that the defect is already known to be at layer 1
or 2.

That distinction is load-bearing because:

- `00-product-constitution.md:176-197` calls draft capital the strongest single **rookie**
  predictor and gives the rookie decision order.
- `01-north-star-architecture.md:204-229` defines Engine B for active-player forecasting and
  expressly disallows rookie-only pre-NFL features from leaking into active-player training unless
  explicitly modeled as a prior.

The memorial may record the exact PVO absence and that it exposed an unanswered foundation question.
It may not declare ingestion, curation, or Engine B feature use to be the proved cause without the
separate investigation David has not opened. The accurate status is: field absence proved; intended
materialization and root layer not yet established.

### 3. Rank 2 is defensible only as domain-specific authority, not blanket supremacy over 01

Keeping 05 second in the displayed authority list is directionally correct: 00 governs analytical
truth, 05 governs sequencing/investment and the root-layer check, and 01 governs technical
architecture. It should not outrank 00 globally, and it should not be subordinate to 01 on the
sequencing question that 01 does not govern.

But `05-layer-doctrine.md:60-63` and `02-agent-operating-loop.md:54-63` say that whenever 05 and 01
conflict, 05 governs. That is broader than David's quoted doctrine and clashes with the same operating
loop's instruction to stop and log conflicts. Resolve by domain:

- sequencing/investment/root-layer question → 05;
- implementation architecture inside authorized work → 01;
- genuine overlap or ambiguity → stop, log, and escalate.

Also narrow “what may be worked on” at `02:46,57`. The ritual itself says upper-layer work is not
forbidden (`05:129-131`); priority doctrine must not silently become task authorization.

### 4. The ritual is not wired: all current enforcement checks pass while most agents can miss 05

Only `CLAUDE.md` received the direct bootstrap pointer. The exact startup lists still omit 05 in:

- `AGENTS.md:5-12`
- `.clauderules:5-12`
- `GEMINI.md:46-57`
- `# DYNASTY GENIUS — SESSION STARTER.md:5-12`
- `AI_CONTEXT.md:5-12`
- `README.md:5-16`
- `docs/README.md:3-19`
- the discipline-reset bootstrap list at `02-agent-operating-loop.md:252-260`

The mechanical gate also omits the new standing doctrine:

- `scripts/validate_governance.py:13-37` does not require the file.
- `scripts/validate_governance.py:50-58` does not require bootstrap files to point to it.
- `scripts/validate_governance.py:60-82` pins no doctrine phrases.
- `tests/test_validate_governance.py:23-40` hardcodes the old target set.

The validator and its focused tests therefore pass today while this “always, every session, no
exceptions” doctrine is absent from most bootstrap surfaces. Memorialization is present; ritualization
is not yet durable. Wire the canonical target and a minimal phrase/contract check into the validator,
update its tests, and bring every direct bootstrap list into alignment.

### 5. A mandatory singular layer cannot represent the work the doctrine itself is governing

`05-layer-doctrine.md:120-127` and `02-agent-operating-loop.md:75-85,103-106,452-464` require one
layer numbered 1–6. Yet the implementing lane's own ledger correctly calls this governance work
“meta” and says it does not sit at one layer. More generally, the failure mode being prevented is
precisely a mismatch between a presenting layer and a root layer; forcing one number hides that
relationship.

The ritual should accept:

- primary/presenting layer **or layers**;
- `cross-layer governance` for work such as this;
- for any work touching layers 3–6, the layer-1/2 dependency check, evidence, and result.

Keep the review finding mandatory when a framing exists. For genuinely mechanical work with no
framing artifact, a proportional preflight check is enough; do not manufacture a framing document
solely to fill the box. This preserves the ritual without turning it into a misleading singular label
or a paperwork generator.

### 6. The ~3.5-hour figure is not independently supportable from the cited evidence

`05-layer-doctrine.md:76-79` and `02-agent-operating-loop.md:89-97` memorialize a cockpit-duration
figure but provide no rerunnable source for it. The repository evidence supports multiple review
rounds and the sequence of work; it does not, from these artifacts, support elapsed cockpit time.
Remove the duration or cite a reliable clock source. The failure remains fully legible without an
unverified number.

## Requested lane disposition

- **Authority placement:** rank 2 is acceptable only with domain-scoped conflict resolution; the
  blanket “05 wins over 01” rule is not clear.
- **Reviewer enforcement:** workable after plural/cross-layer support and proportional handling for
  work with no framing artifact.
- **Gemini:** an Operations/Telemetry **awareness copy is warranted** because Gemini's required
  startup and preflight behavior change. It must request no judgment and no reply; send it after the
  corrected frozen draft is ready.
- **Scope fence:** held. No draft-capital investigation or repair is proposed here.

