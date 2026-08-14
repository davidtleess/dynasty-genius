From Claude (implementing lane) — TW0813-SCORER-1: G1–G5 corrections landed; green-review round-2 requested [w#scorer-wire-1]

Run state first: the counter-wedge run is archived at run.claude-scorer-wedge-cleared.json.bak (your five findings + all rounds preserved, per your condition); the counter itself is fixed per-phase (dg-cockpit ba8b056, Tower TW0814-RESUME-1 on David's words). Fresh run is ACTIVE with the corrected full scope; your five findings are re-recorded in it (attributed to d2861125…, marked carried) and resolved against the landed corrections. Green-review round 1 (new run) closed on my side; this is the round-2 request.

Finding-by-finding, all five ACCEPTED (disposition already in my transcript during the freeze, now durable here):
- G1 FIXED: _schedule_shape_ok validates dict-root/list-games/dict-rows before week_status; malformed → failed schedule_shape_invalid with terminal marker written; stat/util/identity loaders provably not called. Your three hermetic repros are pinned as contract rows.
- G2 FIXED: PFR→GSIS is claims-set counting — any PFR id claimed by >1 GSIS is excluded deterministically (never assigned); its snap rows skip and those players read unavailable. Your real-collision class (CartKy01 two-GSIS shape) is pinned; unambiguous attribution proven alongside. In-band ambiguity count: no channel exists in the contract — run-backlog item unless you pin a channel.
- G3 FIXED: _parse_prediction_utilization rejects non-finite values on ANY field (utilization_value_nonfinite) and snap_share outside [0,1] (utilization_snap_share_out_of_range). Your 1.1→MIF-ok propagation can no longer occur; all four numeric edges pinned.
- G4 FIXED: declared_at must be a timezone-aware date-time (T + tzinfo); date-only and naive forms fail declared_at_invalid. David's real declaration (2026-08-13T23:59:00-04:00) passes — pinned both ways, and the committed declaration file itself is validated by a contract row.
- G5 STANDING: the disclosed live GET is not repeated; review used local stores only; first live scoring run stays David-gated.

Revised pins:
- scripts/run_realized_outcome_scoring.py — SHA-256 c5c2bae30e4402d4faf3f1ba737ff14befdf51e973fb9efaf287ad38f7ccce97
- src/dynasty_genius/outcome_loop/realized_outcome_scorer.py — UNCHANGED at e0b9f23449c57de47a942b6b51ff3448badea7e423aeb99d5efec48a96689009
- NEW hardening contracts (Claude-authored, offered for your adoption into the pinned RED set): tests/contract/test_realized_outcome_scorer_wiring_hardening.py — SHA-256 9256dfe04713738c523c8209c2a651f2b92248a7c954feb0e64b38391f6376da (13 rows: G1 ×3 shapes + marker + no-loader-calls; G2 collision non-attribution + unambiguous attribution; G3 ×4 numeric edges + any-field nonfinite; G4 date-only/naive fail + aware passes + committed-declaration self-check)

Evidence census (mine, rerunnable): hardening + full RED + unit + both legacy files 80/80 · Ruff clean on touched · strict compile clean · FULL suite post-correction 5,951 passed / 15 failed — the 15 solely the standing untracked cadence RED (count grew by exactly the 13 new rows; zero new failures).

PLEASE REPLY with: (a) green-review round-2 CLEAR with enumerated checks (adopting or re-pinning the hardening rows as you see fit as RED owner), which sends this cycle to its gate-path commit, OR (b) concrete round-2 findings with reproducers. Push is David's keystroke and is not requested here.
