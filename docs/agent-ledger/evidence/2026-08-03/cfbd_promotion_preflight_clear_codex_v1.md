# CFBD DATA promotion preflight — Codex CLEAR v1

**Date:** 2026-08-03
**Lane:** independent reviewer
**Scope:** `.gitignore` and `app/config/backup_manifest.json` preflight delta only
**Verdict:** **CLEAR**

## Cleared delta

1. `.gitignore` ignores `app/data/training/cfbd_promotion_history/`. Representative nested
   preimage and receipt paths both resolve to that exact rule.
2. `app/config/backup_manifest.json` contains exactly one matching entry, in `required`, with
   `required: true` and `kind: directory`; there is no optional duplicate.
3. The required disposition makes missing or empty promotion history a named backup failure after
   the authorized promotion. The short absent state between commit and David-authorized immediate
   execution is intentionally fail-closed.

## Checks

- Literal two-file diff reviewed; changes are additive and correctly scoped.
- `git diff --check -- .gitignore app/config/backup_manifest.json`: clean.
- JSON query: one required match, zero optional matches.
- `git check-ignore -v`: nested preimage and receipt examples both matched `.gitignore:55`.
- Independent four-file backup contract run: **54 passed / 0 failed**.
- Pre-execution control: active SHA-256 remains
  `b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38`; candidate SHA-256 remains
  `15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`; promotion-history directory
  remains absent.

## Boundary

This CLEAR closes the two post-implementation preflight fixes. It does not itself commit, execute,
push, refresh, bake off, retrain, promote a model/feature, accept a result, or issue a football
ruling. Commit and real-data execution rest on David's separate word, reported verbatim by the
implementing lane. QB rushing remains a registered hypothesis **UNDER TEST** with no result; this
data movement supplies no evidence about it.
