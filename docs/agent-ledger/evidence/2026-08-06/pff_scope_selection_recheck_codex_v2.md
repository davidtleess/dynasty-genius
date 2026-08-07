# PFF scope-selection recheck — Codex v2

**Reviewed commit:** `71806b8`

**Catalog SHA-256:** `0e0b33279a809838d62a76d6db8fe36f45fbdb61e0302e464c5310b19f4a9477`

**Verdict:** **NOT CLEAR — withdrawal is complete, but §3.3's proposed remediation is internally
inconsistent.**

## Verified corrections

- The catalog contains exactly one `### §3.3` heading.
- R5 and A3 now report 149 payloads and the 134,392 raw payload-row sum without presenting a
  deduplicated total.
- N15b correctly labels 134,392 as a raw payload-row sum not proved double-counted.
- N15c correctly labels 106,867 as an unadopted policy output, not an observation count and not
  canonical.
- No active catalog sentence still asserts that 134,392 is double-counted, inflated, or overstated.
  The surviving 27,525 / 20.5% mentions are explicitly historical and withdrawn.
- P1–P5 and the measured row-level result are represented accurately through §3.3 line 397.

## P6 — §3.3's proposed key and conflict statement contradict each other

Section 3.3 says a real rule requires a row-level union keyed on
`(player_id, scope, season, report, league)` and a value-conflict policy for all 9,518 differing
rows. But including `scope` in the key means cross-scope `REG` and `REGPO` rows do **not** collide.
They are separate keys.

Recomputing the 9,518 changed-row comparisons shows:

- **9,515** changed comparisons are across different scopes;
- only **3** are changed comparisons against same-scope `REGPO` variants in the selection audit.

The catalog therefore misclassifies almost the entire 9,518 set as same-key conflicts. The correct
separation is:

1. raw evidence remains versioned by payload/content identity;
2. a normalized current-state view keyed by `(player_id, scope, season, report, league)` needs a
   deterministic same-scope payload/vintage selection and conflict rule;
3. collapsing across `scope` is a different, decision-specific aggregation problem and cannot be
   solved by calling the result a row-level union.

The withdrawal itself stands. The blocker is the replacement rule, not the withdrawn arithmetic.

## P7 — committed evidence fails the whitespace gate

`git show --check HEAD` reports trailing whitespace on lines 3–5 and a blank line at EOF in
`pff_scope_selection_review_codex_v1.md`. That file originated in the Codex lane; responsibility for
the whitespace is mine. It nevertheless now exists inside the unpushed commit and should be cleaned
before push.

## Required correction

- Replace §3.3's final proposed-rule paragraph with the three-grain separation above.
- Narrow "no aggregate observation count" to "no deduplicated/current-state cross-payload total";
  the 134,392 raw payload-row sum remains publishable at its stated raw grain.
- Make `git show --check HEAD` clean.
