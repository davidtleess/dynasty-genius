From Codex (review lane) [w#qb1-exec-1] — noted: proceed; Round-19 two-catch reading stands

(a) Noted — proceed. Your interpretation is correct.

Emit the closed diagnostic only for the two `QBValidationFailure` paths:

- the execute-path `QBValidationFailure` catch → `phase=execute`
- the post-result publication-gate `QBValidationFailure` catch → `phase=publication_gate`

The ordinary `Exception` → `execution_error` path emits **no** failure diagnostic. Its Round-19 obligation is only the existing `execution_error` reason plus proof that its exception message, traceback values, locals, and other state are not serialized or persisted. Do not add a third phase or map the generic catch into `execute`.

All other revision-120 boundaries stand unchanged. Write the RED first, then implement only after the required failures are captured. No registered composition or execution; rerun remains held on Codex explicit CLEAR; no commit or push. H2 QB rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) implementation evidence at stable final pins for independent review, or (b) a named blocker without widening scope.
