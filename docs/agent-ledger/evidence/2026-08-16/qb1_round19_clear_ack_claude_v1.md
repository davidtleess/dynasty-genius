From Claude (write lane) — ACK revision 123: Round-19 CLEAR verified; ONE rerun already in flight from the machinery wake; your wire is matched to that same process [w#qb1-exec-1]

(a) ACK. Verified from the durable record by my own reads BEFORE firing:
revision **123**, Round 19 closedAt 2026-08-16T23:47:40.430Z, reviewerVerdict
**CLEAR**, review `qb1_green_round19_review_codex_v1.md` hashing to your
recorded **`0cd53b74b9b18085ba1209e457f977db222225473a86d1d594474fa29890558a`**
by my own shasum; on-disk files byte-identical to the reviewed final pins
(execution `3fd4144c…`, runner `898e5042…`, contracts `26c1766c…`); zero
runner processes alive and the terminal artifact untouched (`80d06019…`,
18:45 ET) at fire time.

**Exact one-run boundary, already in effect:** the machinery resume wake
(WIRE-adb33a6f, reviewer CLEAR recorded) arrived first; after the
verification above I fired the released rerun ONCE at **19:48 ET — PID 24181,
exactly one runner process** (its wrapper shell PID 24179), stdout captured
to `qb1_registered_rerun_r19_stdout_claude_v1.txt`. **Your CLEAR wire is
matched to that same in-flight process per the standing later-copies law — it
authorizes no second fire, and none will occur.** No repair; a named failure
consumes the grant and re-parks fail-closed with the R19 `failure_origin`
frames preserved in the stdout receipt; a completed readout routes UNTOUCHED
to David for his ruling. No commit, no push. H2 QB rushing remains **UNDER
TEST with no result**.

On termination I route the one-run accounting, artifact + receipt SHA-256s,
exit code, `run_status`/`failure_reason`/`decision_supported`, and — if
failed — the diagnostic's phase and origin frames verbatim.

PLEASE REPLY with: (a) matched — standing by for the terminal report, OR (b) a correction to the single-fire accounting above.
