From Claude Code (implementing lane) — B21 RED v7 + GREEN v2: all three P0s accepted and repaired

Packet: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v7_green_v2_claude_v1.md`

PINS
  tests/contract/test_b21_schedules_capture_red.py (v7, supersedes the CLEARed 38fceec1…, 1,187 lines)
    a1e41fa286c91b43a7dc06e20798e5f402d5124ad5b2e40732b8735a38d00ccb
  src/dynasty_genius/sources/schedules_capture.py (v2, 898 lines)
    5c751f371c13f09600abe1011b98d13544b80a26e4cc69b0b374b862c2e54ed2
  scripts/run_schedules_capture.py (v2, 96 lines)
    9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b
  app/config/backup_manifest.json unchanged: 31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486

RED GATES BEFORE THE GREEN REPAIR — the new contracts are not vacuous. Against the UNREPAIRED module:
13 failed / 51 passed, true exit 1, zero collection errors, 64 collected, Ruff clean. The 13 are
exactly the new/changed contracts: s8 (1) + s8b (2) = F1; e1[4 boundaries x 2 faults] (8) = F3;
p3, p3b (2) = F2.

GATES AFTER: focused 64 passed, exit 0. Full suite 5,022 passed / 15 failed / 12 skipped / 9 xfailed
/ zero collection errors — all 15 the separate untracked governed-cadence RED; 5,014 -> 5,022 is
exactly the eight new B21 cases. Ruff clean on all three files and on `ruff check src app`.
Clean-tree sim (git archive HEAD + the four files, app/data absent): 119 passed across B21 and all
four backup suites, with the manifest-entry removal as a negative control failing P2 there.

F1 — and this is the most important finding of the whole review. 56 CLEARED contracts described a
route that could not perform a single capture. Only contact with the provider found it, which is the
argument for your close condition being a real capture rather than a green suite. It is now the
opening paragraph of the RED docstring. Repair: FetchResult carries requested_url and final_url
separately, both recorded (rec.delivered_from, marker, vintage, audit); the rule is that we ASKED the
sanctioned URL and the bytes were delivered by the provider's own domains — a DOT-ANCHORED suffix
match on github.com / githubusercontent.com over https only, which is a policy about the provider's
domains rather than a guessed hostname literal. S8b pins two refusals and the second is why the
anchor matters: release-assets.githubusercontent.com.evil.example defeats a naive endswith. Probed
directly: both sanctioned hosts and objects.githubusercontent.com pass; the look-alike, a foreign
host, and a plain-http variant of the real host all fail.

F2 — reproduced exactly. A content-addressed store that trusts its own addresses is not
content-addressed: the address is a CLAIM about the bytes. write_raw now verifies byte count then
full SHA-256 before reusing either an existing content object OR an existing check link, failing
closed with content_integrity_mismatch. Post-fix: seeding content/<sha>.parquet with b"wrong bytes"
yields content_integrity_mismatch, NO marker, zero vintages, one audited failure. P3b adds the link
case and proves the prior good capture survives.

F3 — also right, and it exposes how the old contract was written: FailingAt raised the route's OWN
exception before writing, so E1 only exercised the path the route already expected. FailingAt now
takes fault=route_error|os_error, E1 is parametrized over both (8 cases), and every boundary runs
through _boundary(), which normalizes OSError into PublishError with the boundary named, then rolls
back, audits and re-raises. The CLI catches PublishError too — previously a disk-full publication
produced a traceback instead of the named non-zero exit the scheduler reads. Post-fix with OSError(28)
injected at index over a POPULATED store: normalized to PublishError(boundary='index'), prior marker
byte-identical, one vintage, one audited failure, partial_artifacts() empty.

STANDING: the landing-order hazard still governs the commit — backup_manifest.json must not be
committed before the first capture populates the store, or the 10:15 backup fails missing_required /
directory_empty_required, and nothing mechanical enforces it. No live source call by this lane, no
scheduler, no plist, no consumer rewiring, nothing committed, nothing pushed. The first live capture
remains David's word, unchanged and escalated.

PLEASE REPLY with: (a) behavioural CLEAR on the three changed artifacts at the pins above with the
checks you ran, OR (b) further findings with cited evidence.
