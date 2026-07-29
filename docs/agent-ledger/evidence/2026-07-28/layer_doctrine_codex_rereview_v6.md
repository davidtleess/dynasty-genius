# TW28-LAYERS — Codex round-7 review of the round-6 corrected freeze

**Verdict: NOT CLEAR — one finding.**

Layer: `governance` / `cross-layer`. The layers 1–2 dependency check is not applicable: this
reviews the rule and bootstrap package that govern layer selection. It opens no inventory,
draft-capital, modeled-blank, roster-audit, build, commit, or push work.

## Checks independently run

- Recomputed the four submitted SHA-256 values. All matched:
  - disposition v4:
    `2d03ca44188f6a18f5612b90a92a856afb28151418d99ff577027f9886761694`
  - `02-agent-operating-loop.md`:
    `4749c1c6cf415665cfd36f5520f829cb3666eb16234ab428781eccdab4535c07`
  - `AGENT_SYNC.md`:
    `434e468460dc87011a1d20ea8c3fc69a765cc96a4bbdecbdca2f610f447d1983`
  - `05-layer-doctrine.md`:
    `ceb111146ce6ae99ae16d9d13ba47e6c549ba457cd64a09404665e09f4f231ad`
- Confirmed the three round-6 corrections in the submitted files:
  - `02:6,58,68-74` now section-scope the pending activation and put the qualification
    before the ritual mechanics.
  - `AGENT_SYNC.md:14-16` reports six rounds / latest three-finding NOT CLEAR / 24 total.
  - disposition v4 durably records both round 5 and round 6.
- Fresh-agent work-routing test: **PASS**. The board opens only the Layer Doctrine review and
  leaves every fenced thread parked or not open.
- Fresh-agent binding-status test: **FAIL**, as finding 1 describes.
- `rg -U 'full\s+adversarial\s+cycle' docs/governance`: no output, real exit 1.
- `rg -U '1\s+ingest\s*·\s*2\s+curate'` over governance plus all eight bootstrap
  files: no output, real exit 1.
- The two sweeps above were run directly with `rg -U`; no `grep -P`, stderr suppression, or
  `|| echo` success branch was used. Claude's self-correction of his earlier false-PASS probe is
  accepted.
- `.venv/bin/python3.14 scripts/validate_governance.py`: PASS, exit 0.
- `.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q`: 4 passed.

## Finding

### 1. The pending boundary still does not reach the bootstrap package; a fresh agent receives the unratified ritual as binding before it reaches the qualification

The board says the eight pointer texts and validator pins are part of the package David has
**not** ratified and that every package item is pending and non-binding
(`AGENT_SYNC.md:24-36`). `02` now says the same about Required Reading 2a, the preflight/ledger
layer fields, and the ritual (`02:6,68-74`).

But each bootstrap pointer still issues the pending mechanics as a present command:

- `AGENTS.md:9`, `.clauderules:9`, `AI_CONTEXT.md:9`, session starter `:9`,
  `README.md:11`, and `docs/README.md:9` say **"Your obligations"** are to name the
  layer and perform the layers 1–2 check.
- `CLAUDE.md:13` says the doctrine **"outranks every plan, spec, ticket, and backlog"** and
  that the preflight **"must"** carry both ritual records.
- `GEMINI.md:52` requires the layer preflight now.
- None of those pointer lines says the agent-authored obligations are pending, unratified,
  or not yet binding.

That ordering matters. `AGENTS.md`, `CLAUDE.md`, `.clauderules`, or the lane-specific bootstrap
is read **before** `02`; the new `02` banner and the board cannot retract a command already
presented as binding. This review itself reproduced the failure: the supplied bootstrap required
the layer line without exposing its pending status.

The validator reinforces the same incomplete activation. It says the every-session read is
"enforced rather than asserted" (`scripts/validate_governance.py:56-59`), pins
`Layer discipline` and `Priority is never authorization` (`:84-87`), and its focused test calls
the doctrine enforced (`tests/test_validate_governance.py:44-65`). It pins neither
`pending_activation` nor the `not yet binding` boundary, so its PASS cannot detect this exact
regression.

Rerunnable pointer probe:

```bash
rg -n -H "05-layer-doctrine" \
  AGENTS.md CLAUDE.md .clauderules AI_CONTEXT.md \
  "# DYNASTY GENIUS — SESSION STARTER.md" README.md docs/README.md GEMINI.md
```

It shows all eight active pointer lines and their unconditional commands. The fix must make the
pending status true at the first instruction surface, not only later in `02` and the board, and
the mechanical pin must preserve that boundary. This is the same package-activation defect as
round-6 F1, not a new doctrine decision.

## Scope and gate state

No full sprint tollgate was run: this is a markdown/governance review with focused validator
coverage, not a build or phase closeout. Nothing is cleared for ratification, commit, or push.
A future CLEAR would clear content only and would not schedule any action.
