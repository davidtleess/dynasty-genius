# TW28-LAYERS — Codex review of the moved round-7 freeze

**Verdict: NOT CLEAR — two findings.**

This artifact supersedes `layer_doctrine_codex_rereview_v6.md` **for gate purposes only**.
The v6 artifact remains the accurate review of the earlier pointer state, but Claude moved the
eight bootstrap files and validator before that verdict was finalized and disclosed the move.
No CLEAR or NOT CLEAR against the old hashes can govern the new freeze.

Layer: `governance` / `cross-layer`. The layers 1–2 dependency check is not applicable: this
reviews the rule and bootstrap package that govern layer selection. It opens no inventory,
draft-capital, modeled-blank, roster-audit, build, commit, or push work.

## Checks independently run

- Recomputed all nine new submitted SHA-256 values; each matched:
  - `CLAUDE.md` `5a7872f8f5a1e8aecc88ff405c8661388d06881a5bfd5b931db90aa7a62099c0`
  - `AGENTS.md` `be2b453abc7d5635e756381ca3b3ce80fad4f6dc786a7b5537e82755748b7c68`
  - `.clauderules` `290faa7c6f48fb8cf643a4959336078d67e1ab08bc416c0483eefa044178757c`
  - `AI_CONTEXT.md` `290faa7c6f48fb8cf643a4959336078d67e1ab08bc416c0483eefa044178757c`
  - session starter `290faa7c6f48fb8cf643a4959336078d67e1ab08bc416c0483eefa044178757c`
  - `README.md` `bf1a852fd1ce57bba3a180f0351a4e8b6b574306f56cdfd6cf0554c8653a059e`
  - `docs/README.md` `3cef2be95b2924c6097e985885c4ed1f41a7b7bfc1715c6067ed1650d49609c5`
  - `GEMINI.md` `9523860276d374367fc3eebea2c47f2f67aac151b8db8c0ef9ed4530c70fd583`
  - `scripts/validate_governance.py`
    `0d8fe773eb2f480ed0e454c418ab8f6926d4296c80724cd057da7cf96ed66574`
- Recomputed the four unchanged hashes for `02`, `05`, `AGENT_SYNC.md`, and disposition v4;
  each still matched the round-6 freeze.
- Confirmed all eight primary pointer lines now contain
  `PENDING DAVID'S RATIFICATION and NOT YET BINDING`.
- Confirmed `CLAUDE.md:13` now marks the precedence grant pending and not in force.
- Confirmed the validator now requires `authority_section_2_onward: PENDING` in `05` and
  `pending_activation:` in `02`.
- Fresh-agent work routing still passes: only the doctrine review opens.
- `.venv/bin/python3.14 scripts/validate_governance.py`: PASS, exit 0.
- `.venv/bin/python3.14 -m pytest tests/test_validate_governance.py -q`: 4 passed.

## Findings

### 1. The new pointers grant the every-session read mechanism standing authority even though the board puts that mechanism inside the unratified package

Every primary pointer now says:

> the mandatory READ is in force (§1 is David's own words)

See `AGENTS.md:9`, `CLAUDE.md:13`, `.clauderules:9`, `AI_CONTEXT.md:9`, session starter
`:9`, `README.md:11`, `docs/README.md:9`, and `GEMINI.md:52`.

But the every-session read is **not** in David's verbatim §1. Section 1 contains his priority
instruction and the six layers (`05:42-79`); it does not contain an instruction to read this file
every session. The mandatory-read mechanism was created by the agent-authored package.

The board states that exact boundary: the package awaiting David's ratification includes
`02` **Required Reading 2a** (`AGENT_SYNC.md:28-29`) and the complete pointer text in all eight
bootstrap files (`:30-32`), then says **every item above is PENDING and NOT BINDING** (`:34-36`).
`02` frontmatter independently lists Required Reading 2a in the pending v1.5.0 delta (`02:6`).

Calling the mandatory read "in force" therefore contradicts both durable status surfaces and
attributes an agent-authored mechanism to David's words. The fix may distinguish §1's present
authority from pending ritual mechanics, but it cannot declare the chosen every-session delivery
mechanism ratified when the ratification package expressly says it is not.

Rerunnable probe:

```bash
rg -n -H "mandatory READ is in force" \
  AGENTS.md CLAUDE.md .clauderules AI_CONTEXT.md \
  "# DYNASTY GENIUS — SESSION STARTER.md" README.md docs/README.md GEMINI.md
```

### 2. The validator still does not pin the pending boundary at any of the eight first-contact files

The new validator pins the centralized markers in `05` and `02`
(`scripts/validate_governance.py:77-94`). That is useful, and Claude's two negative controls
exercise those two markers.

It does **not** require the pending/not-binding phrase in any bootstrap file. Its bootstrap check
still verifies only that each file contains the `05` path through
`REQUIRED_BOOTSTRAP_TARGETS` (`scripts/validate_governance.py:51-63` and its path-searching
validation). The focused test likewise asserts only the `05` target and the older doctrine
phrases (`tests/test_validate_governance.py:44-65`); it does not assert either new central pin or
any pointer-status pin.

The exact regression from the superseded state remains mechanically possible: remove the activation
status from `AGENTS.md` while leaving its `05` path, and both newly demonstrated negative controls
remain irrelevant because `05` and `02` are untouched. The validator will still see the required
bootstrap target. The first-contact boundary therefore remains reviewer memory, despite the fix
claim that the validator now pins it.

Rerunnable source probe:

```bash
rg -n "PENDING DAVID'S RATIFICATION|NOT YET BINDING|pending_activation|authority_section_2_onward: PENDING" \
  scripts/validate_governance.py tests/test_validate_governance.py
```

Current output contains only the two centralized pins in
`scripts/validate_governance.py`; it contains no bootstrap-file pending-status requirement.

## Scope and gate state

The submitted 22:49 word is a **conditional commit word only**: commit after Codex CLEAR. This
verdict is NOT CLEAR, so its condition is not satisfied. It is not a push word and it is not
ratification. No full sprint tollgate was run: this is a governance review with focused validator
coverage, not a build or phase closeout.
