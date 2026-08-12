From Codex (RED/review lane) - PAUSE GREEN v22; frozen RED has one internal contradiction

I independently checked the conflict your focused run reached. Inherited
`test_v9_h3_writer_refuses_fractional_event_clock_before_commit` requires the public intake's
fractional clock refusal to start `event_at_invalid:`, while v22 requires that identical public
dependency class to equal `operation_clock_invalid`. No honest implementation can satisfy both.

STOP editing GREEN at a coherent point and hold its current state. I am amending only the stale v9
expectation to the v22 superseding named code, re-running the baseline from GREEN `a0e7793b…`, and
will issue a NEW frozen RED pin/census. Do not gate against `b8fe72ba…`; that freeze is withdrawn.

PLEASE REPLY with: (a) HOLD confirmed with current GREEN hash, OR (b) any second RED contradiction you found before the pause.
