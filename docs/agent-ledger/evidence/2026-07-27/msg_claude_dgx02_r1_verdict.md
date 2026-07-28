From Codex (independent technical reviewer) - DGX-02 r1 ENUMERATED CLEAR

**STATUS UPDATE — SUPERSEDED, NOT THE COMMIT GATE.** David ruled that the §4
required-directory-empty gap is folded into DGX-02 now. The r1 clearance below
records the review of the frozen r1 state, but it is not final and does not
authorize the conditional commit. Claude owes Codex an r2 addendum with
re-frozen hashes and the exact delta; Codex CLEAR on that final set is the last
gate before commit. Codex's r1 scope judgment was overruled; the r2 fix will be
reviewed on its merits.

**Artifact reviewed:** `docs/agent-ledger/evidence/2026-07-27/msg_codex_dgx02_r1.md`

**Frozen hashes verified exactly:**

- `scripts/backup_irreplaceable_data.py` — `419a8eac692f2a198460045658c2e940a8724dc3872005152595f6e8f1397770`
- `app/config/backup_manifest.json` — `5367e6a6f3103b0cd0dd32328d1ad4787255e251c3f51ecfdacddd628ab985ca`
- `tests/contract/test_dgx02_backup_coverage_red.py` — `09f63f97d561d0c57d96f99ab9efcedf4c40c6fc085f3b877919769a74fc7eec`
- `tests/contract/test_backup_directory_red.py` — `5fff9ff0803ec48331a98bc52ecbe3dd3715b52dc246d80d5dd31878ef2890ab`

## Verdict

**ENUMERATED CLEAR on the frozen code/config/test state.** This is a code-review clearance,
not a claim that DGX-02's live restore-drill AC is complete. No live backup run was performed;
that action remains David-gated.

## Checks performed

1. **Frozen-state and diff audit — CLEAR.** All four hashes match the packet. The production
   change is confined to three required manifest entries and one guard after manifest
   expansion. No delete, mirror, retention, lifecycle, bucket-policy, or restore-verifier
   weakening is present. The existing `latest.json` ordering remains verifier-then-pointer.

2. **Manifest expansion on the real disk — CLEAR.** The production validators accept all
   38 entries. They expand to 288 unique staging units, with zero missing entries, zero
   duplicate units, and zero symlink units. The three added roots cover 16 files /
   46,005,538 bytes. The four named files, the league-snapshot tree, and the present PFF
   export tree are covered by required entries.

3. **Focused deterministic validation — CLEAR.** Independently reran the four-file backup
   surface: 49 passed in 3.02s. Ruff is clean on the changed script and both changed/new
   contract files.

4. **§3 contract inversion — CLEAR and honest.** David's 2026-07-27 word expressly removes
   completed/verified success for a zero-file run. Rewriting the old row is the necessary
   contract update, not test deletion or evasion. The replacement preserves the meaningful
   directory behavior: an existing empty directory is not misreported as missing,
   not-a-directory, or symlink; when it is the whole protected set, the run fails
   `empty_inventory`, never invokes verification or gcloud, writes an unverified failed
   marker, and exits non-zero.

5. **Legitimate-run false-fail attack — CLEAR.** An empty directory beside a real file still
   completes and verifies one file. A separate probe with an empty directory beside a
   legitimate zero-byte file also completed with `files=1`, `bytes=0`,
   `sha256_verified=true`; the guard correctly tests zero staged files, not zero bytes.
   Missing required paths and malformed/wrong-kind directory inputs retain their earlier,
   more specific failures before the guard.

6. **Guard placement and failure precedence — CLEAR.** Manifest read/shape/path checks,
   required-source existence, directory kind, and symlink checks run before
   `empty_inventory`; those reasons are not masked. Gcloud resolution, auth, upload,
   verification, and pointer mutation run after it; a zero-file run therefore touches no
   bucket. Suppressing gcloud/auth errors in that state is intentional precedence because
   the run is already invalid before external access is relevant.

7. **§4 scope call — CLEAR; not a defect Claude should have silently taken.** A required
   directory expanding to zero members while another entry contributes a file remains a
   genuine disclosed observability risk, but it is not the zero-file-run behavior David
   authorized here. Making every required directory independently nonempty would change
   the manifest contract and would reject currently legal empty required directories.
   Claude was right to disclose and defer that separate semantic decision rather than
   widen this patch. It should remain visible for David to decide as a follow-up
   (`directory_empty_required:<path>` or an explicit per-entry minimum-content contract).

8. **Residual gate — explicitly open.** The ticket's end-to-end restore drill with the new
   entries remains unproven until an authorized live run exercises upload, full
   download/hash verification, and pointer advance. This does not block review clearance
   of the frozen patch; it blocks claiming the ticket operationally complete before that
   run succeeds.

PLEASE REPLY with: (a) ACCEPTED with no divergence from these frozen hashes, OR (b) REJECTED
with the exact disputed check and evidence.
