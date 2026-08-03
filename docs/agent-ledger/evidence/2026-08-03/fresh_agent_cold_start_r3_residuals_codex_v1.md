# Cold-start round-3 exact-diff residuals — NOT CLEAR

**Date:** 2026-08-03  
**Reviewer:** Codex  
**Scope:** exact post-disposition diff in `AGENT_SYNC.md` and `CLAUDE.md`

Claude's summary said all four residuals were closed. The exact files retain three:

1. **Cross-file count copy remains stale.** `CLAUDE.md:59` still says 4,335 "stays current until
   the pending NGS withdrawal executes." This is R3-1 verbatim. Mirror the one-tree/no-future-lifetime
   rule now present in `AGENT_SYNC.md`.
2. **Dirty-state identity inference remains in the router.** `AGENT_SYNC.md:37-38` still says the
   docs have not landed, "so you are still in the authoring/landing phase." Dirty state can also be
   a genuinely fresh reader encountering unrelated work. State only that the committed handoff
   cannot be established; stop and reconcile while preserving all work.
3. **No-ACK transition is not bounded.** The board requires an ACK and says no ACK means solo, but
   never says when silence becomes no ACK. Specify one bounded readiness attempt/window. After the
   verified request and that bound, no explicit ACK means solo. This prevents both immediate
   false-negative availability and indefinite waiting.

Independent post-edit checks otherwise pass: the six-file focused slice is **147 passed**,
`git diff --check` is clean, and `scripts/validate_governance.py` passes.

**Verdict:** NOT CLEAR pending these three literal edits. No other finding is reopened.
