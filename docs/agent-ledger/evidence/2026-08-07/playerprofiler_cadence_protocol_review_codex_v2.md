# PlayerProfiler cadence protocol v1 — independent review

**Reviewer:** Codex, independent reviewing lane  
**Layer:** Layer 1 ingestion inventory  
**Artifact:** `docs/agent-ledger/evidence/2026-08-07/playerprofiler_cadence_protocol_claude_v1.md`  
**Reviewed SHA-256:** `ee32c040e4a116e224df81c974e2b977e3d24758fd544fac03ba0afe7619f54f`

## Verdict

**NOT CLEAR.** The manual-export direction is right and David's *"ok do it"* does not authorize a
new scripted fetcher. The artifact nevertheless overstates the capability finding and describes a
three-export hash comparison as though it could close a source-publication clock. It cannot do so
as written.

No network call was made during this review.

## Findings

### P1 — HIGH: the route inventory is factually incomplete

The artifact says **"no automated retrieval path exists"** and that no live HTTP client exists in
the PlayerProfiler code. Its search covered `src/dynasty_genius/playerprofiler*.py` and
`scripts/run_playerprofiler*.py`, but omitted two tracked scripts that contain PlayerProfiler HTTP
clients:

- `scripts/probe_playerprofiler.py:31,41,97-109` uses `httpx.AsyncClient.post` against the old
  `wp-admin/admin-ajax.php` route.
- `scripts/enrich_training_data.py:122-180` defines `PPClient` and uses
  `httpx.AsyncClient.get` against the same route for `/players` and `/player/<id>`.

The codebase therefore contains **two live-coded automated acquisition paths**, not only the one
probe named in the artifact. Nothing in this review establishes that either path works today, is
sanctioned, or may be run. The supported conclusion is narrower: **no functioning, sanctioned
automated route to the current subscriber-export resource has been demonstrated; the governed
production adapter is manual-file ingestion.** The whole-repo route inventory must be stated before
calling the gap a capability fact.

### P2 — MEDIUM: the authority correction swings too far

David's *"ok do it"* was given against a forward-observation protocol. It authorizes that bounded
protocol work; it does **not** silently authorize building or running a new HTTP fetcher. Declining
the fetcher is correct.

But the artifact then says authorization changes nothing and that no action follows. The accurate
state is: **execution is authorized within the stated manual-export shape, but it has a human input
dependency — David must supply each export batch.** The next action is therefore a concrete export
request/schedule to David, not an architecture build and not a claim that the authorization was
ineffective. The document itself grants no authority, but David's separate word already did.

### P3 — HIGH: the proposed observations do not measure source-publish cadence

Weekly manual downloads measure **endpoint states observed at retrieval times**. They do not expose
publication times. The current `pp_player_season` schema has no `published`, `updated`, `modified`,
or export/source timestamp column, and the status marker records our run time.

Accordingly:

- different observations prove that the export state differed at the two sample times;
- identical observations prove only that the compared representation matched at those endpoints;
- neither result establishes how often PlayerProfiler published, whether intermediate changes
  occurred, or a recurring source schedule.

The artifact correctly says it cannot establish a declared schedule, but contradicts that boundary
by promising a **"lower-resolution bound on publication rhythm"** and an answer of **"changes at
least weekly vs does not."** The protocol can produce a bounded **observed-change series**, not the
catalog's source-publish cadence. A-C cannot close from this series alone unless the closure contract
is explicitly changed or provider publication metadata/documentation is obtained.

### P4 — HIGH: the experimental unit is undefined

"Three exports" is not a reproducible grain. The held `player_season` ingestion comprises **31 CSV
files and 36 position-season blocks**. `read_export` explicitly warns that filenames are download
order artifacts and identifies coverage from file content.

Each observation must therefore be defined as either:

1. one pinned position-season slice, in which case the conclusion is limited to that slice; or
2. one complete report batch with a manifest of the exact position-season blocks expected at every
   observation.

The protocol currently permits three incomparable files to be called three observations of "the
same report." It needs an explicit report configuration, filters, seasons, positions, completeness
rule, and missing-file treatment before collection begins.

### P5 — HIGH: raw-file hashing alone is not a trustworthy change detector

`Hash each export and compare` conflates substantive change with representation change: row order,
line endings, quoting, schema order, or a partial export can change raw bytes without changing the
underlying rows. Conversely, a missing slice must be reported as incomplete/unavailable, not merely
"changed."

Each observation needs a small private manifest containing at least:

- UTC observation time and report/filter identity;
- expected and observed position-season blocks;
- file count, byte count, row count, and column/header hash;
- raw SHA-256 for exact-byte identity;
- a deterministic semantic digest at a pinned row grain and canonicalization version; and
- an explicit schema/coverage result before any content comparison.

The existing loader already distinguishes raw file SHA from normalized, sorted-row content hashes;
the protocol should preserve that distinction rather than reduce it to one unspecified hash.

### P6 — HIGH: private raw-evidence retention is unspecified

"Any folder outside the repo" is not a governed retention rule, and an outside-repo folder is not
made safe by this repo's `.gitignore`. If only hashes survive, a later reviewer cannot replay a
semantic comparison, diagnose schema drift, or verify that the observations were comparable.

Before the first new export, pin:

- the private local retention location;
- who may access it and how long the exact bytes remain;
- whether it is backup-covered or deliberately regenerable; and
- the rule that no subscriber rows enter Git or review artifacts.

This does not require committing private data. It does require retaining the exact delivered files
long enough to audit the observation series, consistent with `01`'s raw-before-parse rule where raw
capture is feasible.

### P7 — MEDIUM: weekly/three exports is a pilot, not a closure threshold

Weekly is a reasonable **operational choice** if David accepts the manual burden. It is not derived
from source evidence, and "finest cheap / coarse enough" is not measured. Three exports are the
minimum needed to create two intervals, but two intervals are not sufficient to infer a recurring
cadence.

The protocol should call this a **three-observation off-season pilot**, not a minimum that closes the
clock. It should pre-state the only valid outputs (`changed`, `unchanged`, `incomparable`) and avoid a
sample-count pass criterion. If recurring rhythm is still desired after the pilot, the observation
window and season phases need a separate, burden-aware decision.

### P8 — MEDIUM: this is an N6 pilot, not an N1-N8 closure protocol

The protocol samples only `player_season` (N6) and correctly concedes that `medical_history`,
`roster_week`, and `pbp` need their own series. N1-N8 therefore remains open even if the pilot is
executed perfectly. The title and purpose should be narrowed to **PlayerProfiler `player_season`
observed-change pilot**, with N7/N8 treated as derived identity/capture state rather than additional
provider publication clocks.

## What is sound

- The governed production adapter consumes David's manual subscriber exports.
- No new scripted login/fetcher is authorized by *"ok do it."*
- Off-season results cannot be generalized to in-season behavior.
- No-change over a few intervals is non-diagnostic.
- Observed change is not a provider-declared schedule.
- The other PlayerProfiler source streams require separate evidence.
- A-C remains open; no checkbox should move from this protocol.

## Required v2 shape

Reframe the document as an **authorized, human-dependent N6 observed-change pilot**. Correct the
whole-repo route inventory; define one comparable observation batch; retain exact private bytes
under an explicit policy; record raw plus semantic hashes and coverage/schema metadata; and state
that the pilot does **not** by itself close the catalog's source-publish cadence field.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
