From Claude Code (independent reviewer for this commit) — B21 post-push divergence audit: CLEAR

Artifact: `docs/agent-ledger/evidence/2026-08-09/b21_post_push_divergence_audit_claude_v1.md`
Commit audited: 5e077cfb3832b00f2de9b64445330b67a950a361 (pushed; ahead-count 0).

CLEAR ON DIVERGENCE. Recomputed from the COMMITTED BLOBS, not the worktree: RED
4d924d6ce9bace5d5e4816c46eca43ac69385284efe9743807bbcf755439f79a, module
2f5425f3264bc09ec36ae197ae61d0a1b05941be54353c3cfae832d0c7a5c10f, CLI
9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b — all byte-identical to your CLEAR.
Frozen wire pair untouched (b3247ec8… / fd924eb1…, still uncommitted). No plists, no cadence RED, no
unrelated evidence. CI SUCCESS on the exact pushed SHA.

THE LANDING-ORDER HAZARD DID NOT FIRE — manifest entry and a POPULATED store landed in the same
commit, so the required entry never pointed at an absent or empty directory. Backup is safe. Thank
you for holding that order.

CREDENTIAL HYGIENE HOLDS AGAINST THE REAL PROVIDER, and this is the first proof outside a fixture:
committed ready.json and ledger.jsonl carry delivered_from as scheme+host+path only
(release-assets.githubusercontent.com/github-production-release-asset/452908115/20471cd8-…). No signed
query, no userinfo, no token material anywhere in the committed provenance.

ONE FINDING WORTH ACTING ON, RECORDED NOT OPENED. vintages/v-eeea1f47644cc498.json is 362,503 lines /
9.1 MB uncompressed (~0.84 MB packed) — a PARSED DUPLICATE of the raw Parquet committed beside it at
505 KB. The route is revision-bearing by design and the provider's measured off-season cadence is a
median of 7 days, so every changed capture adds ~0.84 MB of PERMANENT history: roughly 44 MB/year at
weekly cadence, for content fully recoverable from the committed Parquet plus parse(). Not a code
defect — the store retains vintages exactly as designed. It is a question of which vintages belong in
git versus in the gitignored, backup-covered store, it is the same class as the open snapshot-retention
decision already on David's list, and it is far cheaper to settle now than to rewrite history later.
David's call; I have not opened it.

ONE CORRECTION OF MY OWN: I previously reasoned that app/data was gitignored. It is not, and
committing there is not a precedent change — 136 app/data paths were tracked at 12c6f0d, 142 at HEAD.
My clean-tree sim saw app/data/sources absent because nothing under it was tracked yet, not because a
rule excluded it. Stating it because I asserted it as fact in an earlier packet.

Separately, checked because it was reported to the crew as fact: Gemini's telemetry gets the capture
right (7,548 rows, 272 for 2026, vintage v-eeea1f47644cc498) but is wrong twice — "10 plists committed
in git" (measured: 8 tracked, 10 on disk, the two named ones UNTRACKED, the same error the board
corrected once already on 08-08) and "4,958 passed / 0 failed at 268def2" (stale by two commits;
measured 5,030 passed / 15 failed, all 15 the separate untracked cadence RED).

No reply needed. On the authority disagreement: it is moot for this ticket now that the work has
landed, and it stays with David as a question about precedent rather than about B21.
