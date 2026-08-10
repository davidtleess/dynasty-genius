# Footballguys `adp.csv` pilot framing v5 — Codex round-5 review

**Date:** 2026-08-09  
**Lane:** Codex, independent technical reviewer / prospective RED author  
**Framing reviewed:** `footballguys_adp_pilot_framing_claude_v5.md`  
**Framing SHA-256:** `b5dabd2fb553545ffc5916eaf4cc3a898e2d2c9f0ed2e32e00cb40c38b45f27e`  
**Generator reviewed:** `footballguys_identity_census_generator_v4.py`  
**Generator SHA-256:** `030e34ae4c60f98eaac68612b5ac5d592966a45227201c9e93a103348a7b1956`  
**Minimized census reviewed:** `footballguys_adp_identity_census_claude_v5_minimized.json`  
**Minimized census SHA-256:** `56d0ea5a68b0a307b91b352797a21c83dcc7f900df9966a34ac45c22cd7f2020`  
**Disposition:** **NOT CLEAR.** The census and unconditional pin repair reproduce. Two current
round-4 findings remain open, and the regenerated artifacts expose two additional mode/provenance
label defects. Horizon and cohort gates remain failed; ingestion RED stays closed.

No provider contact, intake, durable raw store, model input, RED, commit, push, or new redundancy
comparison was performed by this lane. The evidence generator was run only against the pinned
scratch inputs.

## Independent checks that passed

- All three submitted repo-artifact hashes, minimized byte size, and untracked status match.
- Default regeneration is byte-identical to the submitted minimized artifact: 11,611 bytes, SHA-256
  `56d0ea5a68b0a307b91b352797a21c83dcc7f900df9966a34ac45c22cd7f2020`.
- `--full` regeneration matches the expected target: 271,626 bytes, SHA-256
  `df6e094876f3d52d5aaeeef084e421095126a5316707dc829b3eec0ac05c36b8`.
- Both outputs reproduce the exact file-wide and SF verdict ladders.
- Direct `_verify` probes with empty, formerly exempt `6f3a1e1c...`, and ordinary unequal expected
  hashes all refused. The current pin bypass is repaired.
- A full-mode repo target refused with exit 1 and no file written; a full-mode `/private/tmp`
  target succeeded.
- The resolver module's imports are stdlib only, matching the declared dependency-closure claim.
- The five disclosed Ruff findings reproduce exactly. They are cosmetic and outside the governed
  `ruff check src app` surface; they are not a clearance blocker and need not trigger hash churn.

## Findings

### 1. Current round-4 finding 2 remains open: scratch-only is still repo-only

The prior review required a positive scratch-root allowlist and an outside-repository durable-path
refusal. V5 instead narrows the contract to `REPO in out.parents` and asserts the repository is
"the only durable root in play." That assertion is false. `/Users/davidleess/Downloads` and
`/Users/davidleess/Desktop` both exist outside `REPO`; Downloads is where this pilot's source bundle
itself resides. Either is durable, and the generator's condition accepts both. Backup-manifest
membership is irrelevant: retention risk includes local durable copies that no manifest uploads.

Required repair: in `--full` mode, positively allow only resolved recognized temporary roots and
refuse every other destination. Keep the repo refusal and add controls for (a) an outside-repo
durable destination refusing with no file and (b) a valid scratch destination succeeding.

### 2. Current round-4 finding 3 remains open: the disagreement rule is still present

V5 says top-k is descriptive, has no disposition weight, and Spearman alone governs, but framing
lines 178–179 still say `with the more-conservative rule on disagreement`. With one load-bearing
metric there is no cross-metric disagreement. This is the same contradictory clause identified in
the v4 review, unchanged.

Required repair: delete the disagreement clause. If another load-bearing metric is intended, name
it and close its mapping; descriptive top-k cannot serve that role.

### 3. Full mode still labels its scratch-only payload `commit-intended`

The generator's `status` field is unconditional. The reproduced full artifact therefore says:

```json
"mode": "SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE",
"status": "commit-intended; NOT committed at time of generation"
```

That is internally contradictory and repeats the dangerous false-label class that mode-conditional
metadata was supposed to remove. It can cause the full 608-row provider derivative to be handled as
commit-eligible even though its retention note says the opposite.

Required repair: make status conditional. Full mode must say `scratch-only; NOT commit-eligible`
or equivalent; only minimized mode may say `commit-intended`.

### 4. The v5 minimized artifact points to the superseded v4 full-output target

`expected_full_census_sha256_note` still says the full SHA is recorded in `framing v4`. V4 records
the superseded `f83e6d73...` / 271,352-byte target; the current target is in v5 and is
`df6e0948...` / 271,626 bytes. A reviewer following the artifact's own provenance note reaches the
wrong comparison target.

Required repair: point to `framing v5 §5` (or the current framing version generated with the
artifact). Do not point to a superseded framing.

## Ruling

**NOT CLEAR**, limited to findings 1–4 above. The unconditional pin repair and all underlying
census measurements pass. Required next revision is mechanical:

1. enforce a positive scratch-root allowlist for full mode;
2. delete the stale disagreement clause;
3. make full/minimized status metadata mode-conditional; and
4. update the minimized provenance pointer to the current framing.

The five Ruff findings are disclosed, cosmetic, and non-blocking. The decision state remains:
**horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, no comparison opened, nothing
committed.** H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is
unrelated.
