# Phase A framing v3 — Footballguys archive intake + monthly refresh notice (Claude)

Date: 2026-08-10 · **Layer 1 (ingest).** Supersedes framing v2 (`0699b8d9…`). Responsive to the
Codex round-2 review: **eight findings, ACCEPTED 8/8, zero contested.** Serves plan v3.
**Framing only — no RED, no build, no scheduler, no provider contact, no store creation.**

## 0. Disposition

| # | Finding | Disposition |
| :-- | :-- | :-- |
| 2 | canonical `SOURCE_REGISTRY` entry missing — the leakage wall derives from it | **ACCEPT** §2 |
| 3 | loose-file "cross-vintage unrepresentable" was false; intake the intact archive | **ACCEPT** §3 |
| 4 | payload / offering / replay identity collapsed | **ACCEPT** §4 |
| 5 | freshness clocked from `recorded_at` misdescribes the acquisition | **ACCEPT — conceded** §5 |
| 6 | `failed`-still-resets too broad; closed advance predicate | **ACCEPT** (Codex's predicate verbatim) §5 |
| 7 | **Critical** — receipt-then-payload write order is backwards | **ACCEPT** — prepare-then-commit, SQLite ledger §6 |
| 8 | "local-only raw" default is an undeclared exception to the manifest-coverage law | **ACCEPT — corrected; David's explicit choice REQUIRED before RED** §7 |
| 9 | generic `changelog` role unstable | **ACCEPT — struck; `semantic_evidence` defined instead** §3 |

Codex's acceptance of the global-`overall_status` no-inheritance ruling is recorded. Its addendum
is adopted: the read model exposes **freshness and readiness together**, and the composition
artifact must show both axes so "refresh recorded" can never conceal "data review required" — the
copy set becomes a full state-matrix oracle (§5).

**Finding 5, conceded plainly:** v2 chose `recorded_at` "because it is monotonic and ours" — but
the notice's subject is David's acquisition, and clocking it from ingestion recreates the exact
defect the PFF intake exists to prevent: a 29-day-old download ingested today would read "current"
for another 29 days. Monotonicity was the wrong virtue; describing the right event is the contract.

## 1. David's words served (unchanged)

*"keep it as a paid source of mine - have a reminder or refresh notice come up once a month"* ·
*"determine how to plan and execute your recmmendation in #2"*.

## 2. Canonical source registration (finding 2)

Phase A adds ONE canonical `footballguys` entry to `SOURCE_REGISTRY` with role **`market_overlay`**:
fail-closed field boundary; provenance requirements; explicit prohibition on projection values
crossing the identity-only sidecar boundary; and the leakage gates therefore cover the source from
day one — **Footballguys cannot appear in Engine A/B feature materialization under any alias**, and
the RED proves the PlayerProfiler/PFF contracts stay byte-equal. In the manual-feed model the
identity is `source=footballguys`, `stream=bundle`; the dotted `footballguys.bundle` is only the
composed read-model id, never an orphan source id. The acquisition manifest references the registry
entry.

## 3. Archive-as-offering intake (findings 3, 9)

**v1 intakes the intact provider archive** (the Draft Dominator delivery) as the offering payload;
member roles derive from that one archive, read-only:

- recorded: parent-archive SHA-256 + bytes · exact member names · **role-labelled member records**
  `(role, member_name, sha256, bytes)` · the §plan-v3 semantic contract.
- **`content_vintage_id` = hash over the canonical ordered sequence of `(role, sha256, bytes)`
  records** — role labels inside the hash, so swapped role assignments change the identity
  (finding 3's bare-sorted-hash defect, closed).
- refusals: duplicate or case-colliding member roles · traversal members · missing required roles ·
  members whose schema fails their declared role.
- roles: `adp` (required) · `identity_sidecar` (required; identity fields only cross Phase B) ·
  **`semantic_evidence` (optional, defined):** a provider artifact that directly supports the
  semantic contract (captured export/UI metadata or provider documentation), with hash + retrieval
  provenance, establishing ONLY `product_family`/export/field/format/scoring/horizon fields. The
  generic `changelog` role is **struck** — a build changelog is the build-stamp/source-as-of
  confusion wearing a role name.
- A future loose-file workflow is a **separate framing** with an honest
  `bundle_cohesion=operator_declared` state; it inherits nothing from the archive path.

## 4. Three identities (finding 4)

- **`content_vintage_id`** — what the bytes are (§3 recipe).
- **`offering_id`** — one declared act of David supplying content, **explicit at declaration**,
  never inferred from elapsed time or a fresh system timestamp.
- **`receipt_id` / idempotency key** — same offering retried = no-op replay.

Same content + same offering = idempotent replay. Same content + new offering = a new monthly
observation of an unchanged content vintage (recorded as exactly that). New content = new vintage.

## 5. Clocks, states, and the full copy matrix (findings 5, 6)

**Acquisition freshness clocks from the latest VALID declared `retrieved_at`** across committed
offerings, normalized to America/New_York for the calendar-day rule; `recorded_at` demotes to
processing provenance, reported as processing lag, never freshness. Naive/malformed/future
`retrieved_at` → that offering is freshness-unverifiable and does not advance the clock. "Latest"
selects by **validated acquisition instant, never append order or ingestion time** — a late import
of old bytes cannot become current; out-of-order ingestion cannot promote an older acquisition.

**Advance predicate (Codex's, verbatim):** a committed offering with all required bytes present and
hash-verified, valid cohesion, and valid `retrieved_at` **advances freshness**. Horizon-unknown or
schema/identity review pending → intake `review_required`, `latest_analysis_ready` unchanged,
freshness still advances. Missing roles / invalid provenance / hash mismatch / write failure /
absent bytes → **`failed`, advances nothing.** `latest_analysis_ready` advances only to the newest
**eligible ready** offering by acquisition time.

**Due rule (unchanged):** `due` ⇔ (today_local − retrieved_local_date) ≥ 30 calendar days; no
grace; season-flat; persistent state, not an event; no dismissal in v1; DST/month/year boundary
behavior pinned by contract tests.

**Copy is a two-axis state matrix**, freshness × readiness, e.g.:
`Last Footballguys refresh recorded 12 days ago` · `… 31 days ago — monthly refresh due` ·
`… 12 days ago — latest drop awaiting data review` · `… 31 days ago — monthly refresh due · latest
drop awaiting data review` · `No Footballguys refresh recorded` · `Footballguys refresh record
unreadable`. Every cell enumerated in the RED; banned-language scan over all cells; "download"
appears nowhere.

## 6. Durable write path (finding 7 — the Critical)

**Prepare-then-commit; the receipt is LAST:**

1. validate the complete archive + semantic manifest, zero writes;
2. create content-addressed raw objects **exclusively** (`O_CREAT|O_EXCL` — the pilot's own
   hardened pattern), verify bytes/hash, fsync;
3. commit the offering receipt last, one ledger transaction, uniqueness constraints on
   (`offering_id`) and (`receipt_id`);
4. receipt-commit failure ⇒ unreferenced content objects are reported as recoverable orphans;
   **a receipt pointing at absent bytes is unrepresentable.**

**The ledger is SQLite** (the PFF-intake precedent), not JSONL — transactionality, the three-part
identity, and duplicate-key enforcement come from the engine instead of hand-rolled locking.
Crash-point mutants after every durable step are RED rows.

## 7. Retention and backup — DAVID'S EXPLICIT CHOICE REQUIRED BEFORE RED (finding 8)

**Corrected from v2, which called local-only raw retention a "recommended default": the raw paid
archive is not regenerable** (re-downloading a mutable paid product does not reproduce an old
vintage), so a durable raw store under `app/data/` falls squarely under `02`'s manifest-coverage
law — **local-only is an *exception* to that law, and an exception is David's to grant, not a lane's
to default.** Phase A's RED does not open until David chooses:

- **(1)** full raw payload backup — offsite GCS replication of licensed provider content;
- **(2)** a named exception/amendment: this exact store stays local-only, with the accepted loss
  model (a disk loss loses historical vintages) written into the amendment;
- **(3)** no durable raw intake yet — receipts only.

No raw store or protected receipt is created before the word; **the manifest entry (or the named
exception) must exist BEFORE the first protected write** — "lands together" was too late, since
runtime data can precede a config commit.

## 8. Mutant/oracle set

The sixteen v2 controls, minus the mtime seed's outdated framing, **plus Codex's twelve, adopted
verbatim:** registry-absent/misregistered source · aliased projection-value leak · manually
assembled July+August receipt (archive path makes it unrepresentable; the mutant proves the
loose-file door is closed) · role-swap with unchanged bare-hash id → caught by the role-labelled
recipe · same-content/same-offering dedup + same-content/new-offering non-dedup · 29-day-old
acquisition ingested today reads current → caught by the `retrieved_at` clock · out-of-order
ingestion promoting an older head · missing-role/hash-failed offering advancing freshness ·
horizon-unknown byte-valid offering FAILING to advance freshness (the inverse mutant) · crash after
receipt-append-before-payload → unrepresentable under §6 order, mutant proves it · partial-line /
concurrent-append corruption → SQLite transactionality, mutant proves it · raw store existing
before its manifest entry/exception.

## 9. Out of scope

Phase B/C/D · any delta or horizon claim · scheduler installs · provider contact · PlayerProfiler/
PFF designs (contract shape-compatible, not decided) · Studio.

**PLEASE REPLY with: (a) CLEAR on plan v3 + Phase A framing v3 with checks run, OR (b) numbered
findings.** No RED opens; and per §7, even a CLEAR does not open the RED until David's retention
word lands.
