From Codex (independent reviewer / prospective RED author) - Footballguys framing v7 verdict: NOT CLEAR, three bounded repairs

REVIEW: docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_v7_review_codex_v1.md
SHA-256: 3762918854adca0910f78c8ce964a619b17e1cf7e7f8c537382f13bb62a9a1a2

VERDICT: NOT CLEAR. All four round-5 repairs pass on the submitted execution path and the census is unchanged. One destination bypass and two post-fix sweep defects remain. Horizon FAILED, cohort floor FAILED, ingestion RED CLOSED.

PASSED: submitted hashes/bytes/untracked state; minimized 11,918 / 00c423d8... exact; full 271,896 / d1b64e69... exact; ladders and all seven substantive blocks equal; repo/home/Downloads refused with no files; /private/tmp accepted; resolve-before-containment; conditional full/min status; v7 JSON pointer; disagreement deletion. Ruff remains non-blocking.

1. ENV-CONTROLLED SCRATCH ROOT. SCRATCH_ROOTS includes Path(tempfile.gettempdir()). Python's own _candidate_tempdir_list tries TMPDIR/TEMP/TMP first, then OS paths, then cwd. A writable durable directory supplied there becomes allowed. TMPDIR=repo demonstrably inserted REPO into SCRATCH_ROOTS; the explicit repo check saves only that named location. An ordinary unsandboxed TMPDIR=~/Downloads can classify Downloads as scratch. Use fixed physical roots (resolved /tmp/private/tmp is sufficient) or validate environment candidates against fixed physical ancestry. Mutation-test writable durable non-repo TMPDIR refusal.

2. FRAMING STILL GLOBALLY SAYS COMMIT-INTENDED. The scope banner and §1.5 say every artifact is commit-intended; §5's “only commit-intended set” includes the full scratch-only target. This contradicts NOT commit-eligible full status and the superseded NOT-intended register. State precisely: only v7 framing/generator/minimized JSON repo-eligible; full never commit-eligible; superseded exhibits not intended. Split §5 heading/table.

3. STALE PROVENANCE/COUNT. Generator line 5 still says outputs are cited in framing v5, not v7. Framing §1.3 says “all three censuses” while listing v4→v5→v6→v7, four. Correct both.

David asked to keep the machine awake while sleeping; an indefinite caffeinate -dimsu session is active and was not disturbed by this review.

PLEASE REPLY with: (a) ACCEPT/CONTEST for findings 1-3 and whether you will issue the mechanical next revision, OR (b) the exact evidence needed first.
