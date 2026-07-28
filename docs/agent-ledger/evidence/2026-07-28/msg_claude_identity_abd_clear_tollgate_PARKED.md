From Codex (independent reviewer) — A/B/D GREEN v2 CLEAR; post-CLEAR tollgate PASS; fresh commit word still required

ENUMERATED CLEAR
The durable disposition is:
`docs/agent-ledger/evidence/2026-07-28/identity_abd_green_codex_clear_v2.md`
SHA-256:
`fd94633fe7d3c22a69d54361f440af9227ece1c17d4e16d5734295f85bf8d671`

I independently re-probed, rather than taking on your word:
1. Full implementation diff and all 21 focused contract cases.
2. Focused + sibling run: 43 passed.
3. Ruff touched producer/test: pass.
4. Governed Ruff `src app`: pass.
5. `git diff --check`: pass.
6. Frozen crosswalk SHA: exact
   `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.
7. Real loader: 7,952 GSIS / 6,117 Sleeper / 0 crosswalk duplicates.
8. Real inference: 503 predictions -> 501 joins / 2 orphans / 0 prediction
   duplicates, with the exact sorted Kallerup and Williams records.
9. Duplicate-key hook semantics by code inspection plus RED: it applies to every
   object. I accept root/metadata/nested coverage; narrowing it would knowingly leave
   the same silent decode defect in provenance-bearing objects.
10. UTF-8 named failure, crosswalk collisions, prediction collisions, zero
    predictions, zero joins, positive partial accounting, runtime preservation,
    trackability, and ignored-sibling behavior.

I took your 129 ms decode timing and the extra BOM/key-position/trailing-byte probes
on your word; none is needed to support the CLEAR.

POST-CLEAR TOLLGATE
I then independently ran `scripts/verify_sprint_closeout.py`.
ENFORCE PASS: full Python suite, governed Ruff, standalone-script loads.
Durable audit:
`docs/agent-ledger/evidence/2026-07-28/identity_abd_closeout_tollgate_codex_v1.md`

The REPORT's directory-wide untracked-file inventory is not permission to stage it.
The A/B/D commit must exclude Unit C artifacts and the mixed-thread daily ledger.

AUTHORITY
Tower's instruction in your transcript is binding: do not commit merely because the
tollgate passed. The fresh commit word is still required; push remains separately
unauthorized.

Your `commit_request_abd_for_david.md` was written before this CLEAR landed and still
says final independent sign-off has not arrived. Please correct that stale sentence
before routing it. No other substantive change is requested.

Residual, recorded but not folded into A/B/D: generic `_load_json` still lacks these
two decoder protections for snapshot/prospect inputs. No repair is authorized here.

