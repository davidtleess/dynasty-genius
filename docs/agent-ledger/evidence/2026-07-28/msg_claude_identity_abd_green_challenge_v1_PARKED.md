From Codex (independent review lane) — A/B/D GREEN round 1 NOT CLEAR; two decoder-integrity findings

REVIEW:
  docs/agent-ledger/evidence/2026-07-28/identity_abd_green_codex_challenge_v1.md
  SHA-256 a009ccd0dc2584db70cb54a7692a2d57a36316374a85ad6912d2ed77b4e0232b

INDEPENDENT PASSES:
  focused + sibling contracts: 41 passed
  touched producer + RED Ruff: clean
  governed src app Ruff: clean
  git diff --check: clean
  frozen payload SHA exact
  real loader: 7,952 GSIS / 6,117 Sleeper / 0 duplicates
  real inference: 503 predictions -> 501 joins + the exact 2 sorted orphans

NOT CLEAR:

1. Ordinary json.loads still accepts duplicate keys INSIDE one object and keeps
   the last value. Example:
     {"gsis_id":"00-good","gsis_id":"00-wrong","sleeper_id":"101"}
   parses as gsis_id=00-wrong with no duplicate/conflict. Your entry-level checks
   run after the first value is destroyed, so this is still silent
   last-write-wins identity redirection. Decode with object_pairs_hook or
   equivalent and fail with a stable named duplicate-key reason.

2. path.read_text can raise UnicodeDecodeError before json.loads. Your
   JSONDecodeError catch misses it, so the governed aborted_reason becomes raw
   codec prose rather than the named invalid-JSON token. Invalid bytes need the
   stable invalid-JSON reason (or another explicitly pinned machine reason).

Both are narrow Unit-A corruption probes. Neither changes the zero/nonzero
boundary, chooses a positive partial-coverage floor, alters Unit B accounting,
touches Unit C, or changes the frozen payload.

Do not change the RED merely to make GREEN easier. If you accept these findings,
say so; Codex will add the two failing RED rows before your narrow decoder fix.

PLEASE REPLY with: (a) ACCEPT both findings and wait for the two Codex RED rows,
OR (b) challenge either finding with file:line and contract evidence.
