From Codex (RED/review lane) — STOP/HOLD: v26 readiness oracle is wrong; current pin withdrawn

I independently ran the first stateful-intake control against your in-progress repair. The
ownership boundary succeeds, but the test asserts `result.status == "ready"`. With no effective
horizon evidence this intake correctly returns `review_required`; the v26 test mislabeled the
readiness axis.

STOP GREEN edits now. The frozen pin `656f3f1d…` is WITHDRAWN and any census against it is void as
a whole-run claim. I am changing only that literal expectation to `review_required`, then will
send a new final pin and baseline census. Do not continue until the replacement wire arrives.

This is my RED defect, not a GREEN defect. No commit/push/capture/provider/scheduler/Phase B/C/D.
