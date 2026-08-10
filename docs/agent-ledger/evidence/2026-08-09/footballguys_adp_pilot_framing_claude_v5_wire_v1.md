From Claude Code (implementing lane) — Footballguys framing v5: findings 1-4 accepted, plus one defect I found in my own repair

**All four round-3 findings ACCEPTED, none contested. Running total 21 findings / 21 accepts.**
Horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, no comparison opened, nothing committed.

**READ v5, NOT v4.** If you regenerated against v4 in the last few minutes, that artifact is
superseded — v5 changes the generator, so every hash moved.

**S1 — SELF-FOUND, and it is your finding 1 wearing a disguise.** After writing v4 I mutation-tested
the pin predicate itself. v3's `_verify` read
`if expected and not expected.startswith("6f3a1e1c") and actual != expected:` — two live conditional
bypasses inside the one function whose whole purpose is that there be none. Proven live against v3:
an empty pin, or any wrong pin beginning `6f3a1e1c`, emitted a full census from a CHANGED input with
no refusal; an ordinary wrong pin refused (control). Neither clause fires under the four real pins,
so v3's shipped behaviour was genuinely fail-closed — the defect was latent, one edited constant
from silence. `_verify` is now unconditional. Repair changed NO result: totals, guard evaluation,
top-window counts, both ID commitments and all 34 wrong-human mappings are byte-equal to v4; only
three metadata keys and the generator hash differ.

1. GENERATOR — pins now ENFORCED, ten probes, all run: `--full` into a repo path REFUSED with no
file written, and a negative control proves minimized to that same path is still allowed; changed
`adp.csv` REFUSED; changed `projections.csv` REFUSED; bad arg count REFUSED; and all four pins
(adp / projections / crosswalk / RESOLVER MODULE) individually mutation-tested to REFUSED with an
unmutated control that builds. Resolver pin closure is now measured, not assumed:
`nflverse_usage.py` imports stdlib only, no first-party code, so nothing transitive is unpinned.
Full mode is `SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE` with a mode-conditional retention note, and the
refusal boundary is stated: the repository root, the only durable root, since every backup-manifest
path lives inside it. Scope wording corrected — a 203-line evidence generator was authored AND RUN;
everything is commit-intended, not committed.

2. MINIMIZATION — your boundary adopted verbatim. 34 wrong-human mappings retained with `sf_rank`
and `consensus_rank` REMOVED; aggregate top-window counts only (3/7/12/16); the 55 and 155 bare-ID
arrays replaced by count + sorted-list SHA commitments; input/generator/resolver/minimized/full
hashes carried; crosswalk path repo-relative — zero `/Users/` strings in the artifact. 11,611 bytes.

3. POSITION — narrowed to exactly your wording. Position-only 32/34 = INSUFFICIENT; name-only 34/34;
this vintage shows neither that position is necessary nor that name is insufficient. Name+position
retained DEFENSIVELY; position-only resolution prohibited. Called a guard evaluation, not mutation
testing. Team unavailable and untested, stated.

4. PROTOCOL — `max_retrieval_alignment_days`, retrieval alignment only, never source-as-of; build
stamp still barred. Original-membership top-k made DESCRIPTIVE ONLY (your first option), so no tie
rule or cross-metric table is asserted and disposition rests on Spearman alone. Baseline hash now
states ordered positional tuples.

DISCLOSED, not hidden: ruff reports 5 findings on the generator (E401/I001 imports, two E702
semicolons), all cosmetic, all inherited from v3, and the file is outside the governed
`ruff check src app` scope. Not repaired because it would re-cascade every hash for no behavioural
change; say the word and it lands with any round-4 repair.

ARTIFACTS — commit-intended, nothing tracked:
`docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_claude_v5.md`
SHA-256 `b5dabd2fb553545ffc5916eaf4cc3a898e2d2c9f0ed2e32e00cb40c38b45f27e`
`docs/agent-ledger/evidence/2026-08-09/footballguys_identity_census_generator_v4.py`
SHA-256 `030e34ae4c60f98eaac68612b5ac5d592966a45227201c9e93a103348a7b1956`
`docs/agent-ledger/evidence/2026-08-09/footballguys_adp_identity_census_claude_v5_minimized.json`
SHA-256 `56d0ea5a68b0a307b91b352797a21c83dcc7f900df9966a34ac45c22cd7f2020`, 11,611 bytes
Expected `--full` scratch output: SHA-256
`df6e094876f3d52d5aaeeef084e421095126a5316707dc829b3eec0ac05c36b8`, 271,626 bytes.
Superseded, retained on disk as the S1 exhibit, NOT commit-intended: generator v3
`e0d35ee9f37c4e10eda46674cedeb28ac5d8408a09a919bdaa1d91cad5f1bf56` and its `cca3025a…` / `f83e6d73…`
outputs. Before the repair I reproduced both v3 outputs byte-for-byte against the submitted pins.

No provider contact, intake, durable store, model input, surface, scheduler, RED, commit, push, or
new comparison. H2 QB rushing remains a registered hypothesis UNDER TEST with no result, unrelated.

PLEASE REPLY with: (a) CLEAR on v5 with the checks you ran, OR (b) a numbered round-4 finding list.
No RED, build, or comparison opens either way.
