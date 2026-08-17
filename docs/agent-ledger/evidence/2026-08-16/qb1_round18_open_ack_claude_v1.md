From Claude (write lane) — ACK revision 111 / Round 18 open: exact registered F34 college-normalization boundary accepted; RED-before-GREEN begins [w#qb1-exec-1]

ACK (a). Verified from durable state: run ACTIVE `green-review`, revision 111,
Round 18 open, reason = the David-authorized bounded Round 18; open receipt
`qb1_f34_college_normalization_round18_open_receipt_codex_v1.md`
(`56eecef8c33e1fb146bea1d9c511d862501db9192ad0bbbf2c9b93b291bfd08a`) and
registration read
`qb1_f34_college_normalization_registration_read_codex_v1.md`
(`58509f3cccc9cf7da9e776633553c4a765b4cae78eff2a2362265ac7a9e3bfe3`)
reproduced by my own shasum. BOTH opening pins reproduced: `identity.py`
`aacb56fc30df7685debae6bed890a99cf7ba818c7b73749b7bd5e58ef1acfde0`, correction
contracts `200c6deec425c0d2c2c57ffe7f0e904bee3a9925648df9bad589d205307eba22`.

Boundary accepted exactly — two files only. One PRIVATE canonicalization path
used only by the existing F34 `_college_check`: study side splits a present
`players.college_name` on literal `;` with `normalize_name` run independently
per nonempty institution token; draft side normalizes its single college under
the same law; terminal-token-boundary expansions ONLY (`st`→`state`,
`col`→`college`); the CLOSED exact alias set ONLY (`n c state`→`north
carolina state` · `ucf`→`central florida` · `miami oh`→`miami ohio` ·
`uab`→`ala birmingham`); both-present passes iff the canonical draft
institution is an EXACT member of the canonical study set; disjoint stays
`conflict`; either-missing stays `missing` under the registered degraded age
law. Forbidden list accepted verbatim (no substring/prefix/fuzzy, no
city/qualifier dropping, no open-ended heuristics, no allowlists, no
GSIS/name/age bypass); every other resolver/audit/matrix/lane law preserved.

Route accepted: RED-before-GREEN over the 23/4/22 classes + every closed
alias rule + one-field near misses + the two exact negative controls (Ryan
Griffin Tulane vs Connecticut; Anthony Brown Oregon/Boston College vs Purdue
— both remain TRIAGE) · mandatory final-pin real-surface replay with NO
composition (49 players/143 H4 rows → authoritative DRAFTED with original
round/pick · all 67 representation-only TRIAGE → DRAFTED · residual TRIAGE
exactly {00-0029857, 00-0037175} both cross_check_conflict · zero H4
gate-surviving null capital · bidirectional count reconciliation · admitted
frame digests unchanged) · stable pins, exact two-file diff, contracts,
five-file bundle, scoped Ruff, py_compile, diff-check, proportionate full
suite.

No registered rerun (held on your explicit CLEAR), no top-level composition,
no input mutation, no registered-value/pin/gate change, no provider fetch, no
publication, no commit, no push. A failure re-parks. H2 QB rushing remains
UNDER TEST with no result.
