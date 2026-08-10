# Footballguys pilot commit `df715e2` — post-commit divergence audit

Date: 2026-08-10  
Reviewer: Codex, independent review / RED-authoring lane  
Layer: Layer 1 evidence landing, with Layer 2 identity dependency  
Verdict: **CLEAR on post-commit divergence**

## Commit boundary

- `HEAD == df715e20702ec53330f435639edbd19b06c02789` at audit time.
- Parent: `ca9045045875784138bd9506cb5038766ca34758`.
- Measured tree delta: **41 files, 4,045 insertions, zero deletions**.
- Status mix: two modified durable records (`AGENT_SYNC.md`, the 2026-08-09 ledger) and 39 added
  files (the 2026-08-10 ledger plus 38 Footballguys evidence artifacts).
- Exact classification: **1 board + 2 ledgers + 38 paths under the dated evidence directories whose
  basenames begin `footballguys` + 0 other paths**.
- No execution-surface, app/config, test, scheduler, provider payload, or model file landed.

Exact exclusion probes found none of the deliberately parked superseded framings v1–v8, generators
v3–v7, minimized censuses v4–v8, or any full-census JSON/CSV in the commit. The two unrelated local
modified files and the pre-existing parked inventory remain outside this commit.

## Cleared pins and disclosed exception

- framing v9 remains byte-identical to the round-8 pin:
  `70eb47738732eb6cb7971ba4e2cadab94e5db56f5eb3f29557f7a814180d8036`.
- round-7 review remains `4b2f124679ba168917f91ee2bce8342528773f54c4c719b675fd413a50e67b33`.
- round-8 clearance remains `6d8bd2b3fab62e1ce222897208af68921e1ac03131d54090fa72177bb95adc64`.
- identity false-match measurement remains its submitted `34af5de...` pin.
- redundancy preregistration remains its submitted `abf6fa6...` pin.

The only cleared-set divergence is the disclosed post-CLEAR lint revision:

- generator: `06b73ffd...` →
  `8cbe9618cb72c0b23510806cd930aab52175fcd7c9732f0852680c0c819ec6e6`, version
  `fbg-identity-census/8.1`;
- minimized census: `1a54fcf4...` / 11,918 bytes →
  `778623e04a5ea556a55d233a31305e510bf49417d1ff38ba64982bf2be6bc8dc` / 11,993 bytes;
- expected scratch-only full output: `35705ae3...` / 272,158 bytes →
  `f2e6b0045d60aa38159517744a705e8a011bb88ea1b679c76c65cf5ac9b61117` / 272,160 bytes.

Framing v9's old §5 generator/census rows are explicitly superseded by
`footballguys_pilot_post_clear_lint_revision_claude_v1.md`; that disclosed amendment is part of the
commit.

## Independent regeneration and semantic comparison

Using the pinned source bundle and landed generator 8.1:

1. minimized regeneration was byte-identical to the committed JSON at `778623e0...`, 11,993 bytes;
2. full regeneration was byte-identical to the amended scratch target at `f2e6b004...`, 272,160
   bytes, even with `TMPDIR` pointed at the repository;
3. recursive cleared→landed minimized comparison changed exactly three paths:
   `inputs.generator_sha256`, `inputs.generator_version`, and
   `expected_full_census_sha256_note`;
4. all seven substantive blocks are exactly equal: both totals, position guard evaluation,
   top-window counts, both ID commitments, and all 34 wrong-human mappings;
5. the full output retains 608 rows and every row is byte-equal to the cleared full output;
6. the full JSON changes only generator SHA/version metadata; its rows do not change;
7. an existing output path was refused with its hash unchanged, and a repository full-output target
   was refused without creating a file;
8. `.venv/bin/ruff check` on the landed generator reports **All checks passed**.

## Ruling

**Post-commit divergence audit CLEAR.** The commit contains exactly the declared scope, with no
cleared-content divergence except the disclosed lint/version/pointer cascade, and that cascade has
zero measured semantic divergence.

Standing state is unchanged: horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, comparison
not opened. The commit is not a licence for use. H2 QB rushing remains **UNDER TEST** with no result
and is unrelated.
