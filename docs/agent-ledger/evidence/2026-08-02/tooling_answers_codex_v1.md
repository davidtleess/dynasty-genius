# Codex tooling answers — testing stack and review-lane needs

**Date:** 2026-08-02  
**Scope:** David's two questions: (1) independent assessment of Hypothesis/mutmut/schema tooling;
(2) what Codex's integration-review lane actually needs.

## Answer 1 — Claude's proposed testing tools

### Hypothesis: yes, but the present demonstration is overstated

Hypothesis is useful for Codex-authored REDs and falsification: metamorphic equivalence, numeric
edges, normalization idempotence, row-order invariance, and store state machines are good fits.

The new `tests/contract/test_ingestion_properties_red.py` does fail on the known row-key defect and
shrinks to `week=1, season=2015`. But it does **not** find int/float/text representations unaided:
the test explicitly constructs `as_int`, `as_float`, and `as_text`; Hypothesis varies only the
integer values. Likewise, Hypothesis generates `None`, blank tokens, or duplicates only when the
strategy author includes them. The useful claim is “the property generalizes and shrinks a known
invariant,” not “the library supplied the missing invariant automatically.”

It is installed locally (`6.161.0`) but undeclared. CI installs `requirements.txt`, not
`requirements-dev.txt`, before running all pytest tests. Therefore a committed ordinary test that
imports Hypothesis needs a pinned CI-installed test dependency; its cost is not zero.

### mutmut: approve a targeted pilot, reject the claimed coverage until measured

Mutmut 3.7.0 declares Python 3.14 support. It is a reasonable targeted review aid for functions
such as `normalize_rows`, `UsageStore.apply_season`, and `publish_export`. Do not wire it repo-wide
or into required CI before classifying one pilot's useful, equivalent, and noisy mutants.

It does **not** reliably catch the stored-columns structural-proxy defect. A mutation that removes
the era-union loop would be killed by the existing membership test, which could make the test look
strong while it still never traverses SQLite. Mutation testing changes syntax; it does not invent
the missing capture → store → readback observation. Only an empirical mutant inventory can answer
which persistence mutations survive.

Two current claims/configuration details are wrong:

- Mutmut 3+ documents that it does not mutate code outside functions. `SCHEMA_VERSION` is a
  module-level constant, so the v3-bump gap is not a defect mutmut 3 can be claimed to catch.
- Mutmut 3's documented configuration uses `[tool.mutmut] source_paths` and positional
  module/function patterns. The newly written `--paths-to-mutate` command in
  `requirements-dev.txt` is not the documented v3 interface.

Run any pilot in an isolated worktree or disposable copy. The shared main worktree currently
contains multiple uncommitted bodies, and mutmut itself recommends source control before applying
a mutant.

### Pandera / Great Expectations: no broad adoption now

Pandera currently supports Python 3.14 plus pandas and Polars, so compatibility is not the
objection. The objection is fit: nflverse and the current PFF/PlayerProfiler adapters need exact
era selection, aliases, identity, grain, persistence, and cross-artifact checks. Pandera can
validate a fixed dataframe schema, but it cannot discover an era absent from the inputs, and its
Polars backend does not provide several pandas features such as groupby checks, data-synthesis
strategies, schema inference, or schema persistence.

Do not add Pandera or Great Expectations to the present repair. A later one-adapter pilot may earn
Pandera at a **fixed curated dataframe boundary** if it removes custom validation code while
preserving typed refusals. It does not earn a repo-wide role at raw-ingestion boundaries today.

### What actually covers omitted eras

No package generates a provider era it has never seen. Build a repo-native **schema-era replay
harness** from archived real inputs:

1. register column and dtype fingerprints, not columns alone;
2. retain a minimal sanitized raw fixture for every observed era;
3. drive every fixture through capture → normalize → store → export in a temporary environment;
4. assert source rows, stored rows, keys, era label, readback values, and export schema;
5. compare each cheap live preflight's fingerprint to the registry and refuse an unknown one before
   a full run.

For CFBD, retain request path/params, content type, JSON root, identity fields, and a sanitized
response. For PFF/PlayerProfiler, retain header/schema manifests and redacted representative rows.
This is ordinary pytest plus real fixtures; no framework is required.

## Answer 2 — what Codex's review lane actually needs

### 1. A pinned authoritative source-contract bundle

This is the material gap. Codex can browse the official sources, but the contract is not durable or
bound to the adapter version under review.

- **CFBD:** pin the official OpenAPI document with URL, API version, retrieval time, and SHA-256;
  additionally pin the stat-name catalog or one sanitized real response per used endpoint family.
  The current official Swagger is API 5.17.0 and lists `/stats/season` and
  `/stats/player/season`, not `/stats/team/season`; that alone would have rejected the months-old
  nonexistent route. Dynamic values such as `sacksOpponent` still require a catalog/real response
  because the generic `TeamStat` schema cannot prove which stat names exist.
- **nflverse/nflreadpy:** pin source column+dtypes fingerprints and minimal raw fixtures for each
  observed dataset era. The installed package source is readable already; the missing part is
  versioned provider-shape evidence.
- **PFF/PlayerProfiler:** no public schema package can replace the actual paid/manual export. Keep a
  redacted header manifest and representative row per export vintage so review does not depend on
  prose or another lane's summary.

This can be a small repo script and fixtures. I do not need an MCP server for it.

### 2. Hypothesis as a declared test dependency

I want Hypothesis available reproducibly for adversarial REDs and stateful ingestion/store tests.
It is already local, so the missing capability is dependency/CI declaration, not installation.

### 3. Immutable review targets

The shared working tree changes while review is running. Codex should review a frozen SHA, patch
bundle, or dedicated git worktree. Git already provides this; no download is needed. This removes
the risk that a passing probe and a cited line refer to different moments of the implementation.

### 4. Optional, not required

A targeted mutmut installation would improve test-adequacy audits after the pilot proves useful.
It is not required for ordinary review and cannot replace real-source execution. I do not currently
need DuckDB, Great Expectations, Pandera, another agent skill, a browser extension, or a new MCP:
the terminal, web, GitHub access, browser, SQLite, Polars, pandas, and shared raw artifacts cover
those mechanics.

## Bottom line for David

Add reproducible Hypothesis support and authorize a narrow mutmut pilot if desired. The highest
quality gain, however, is not another plugin: it is downloading and pinning the official provider
contracts and retaining sanitized real schema-era fixtures. That would have prevented the exact
“reasoned from memory” failure that produced `/stats/team/season`; mutation testing would not.
