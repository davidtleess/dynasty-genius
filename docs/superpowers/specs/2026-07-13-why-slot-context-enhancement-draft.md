# The "Why" Slot — Context Enhancement Draft v0 (from the comp audits' core product gap)

**Finding (both unanchored audits, 2026-07-13):** every interesting row dead-ends in a math receipt; the manager finishes the thought in Sleeper. "Whoever finishes the thought owns the morning."

**Sourcing status, probed:** Sleeper (already on the constitution's ground-truth list — NO new-source escalation required) serves `injury_status`, `injury_body_part`, `depth_chart_position/order`, and `news_updated` per player. Our universe snapshot normalizer RETAINS ONLY age/full_name/position/sleeper_status/team/years_exp (probed against `sleeper_universe_snapshot_latest.json`) — the context fields are dropped at ingestion, not absent at the source.

**Scoped fix (one adapter cycle, no new source):**
1. Retain `injury_status`, `injury_body_part`, `depth_chart_position`, `depth_chart_order`, `news_updated` in the player payload of the universe snapshot (additive; schema_version bump; PIT-safe).
2. The inspector's "Why it moved" slot renders, from these fields only: injury designation (or "no designation"), depth-chart line ("CAR WR2"), and "Sleeper profile updated <date>" — facts, never narrative. In-season, the usage feed (snaps/routes/targets — already the estimate-responsiveness doctrine's inputs) joins the slot.
3. What stays honest: no headline synthesis, no "because" claims — the slot presents context facts beside the movement; the manager connects them. League NEWS TEXT remains a future David decision (that WOULD be a new content surface).

**Falsification seeds:** absent fields render the designed "no designation / no depth-chart data" states; `news_updated` renders date-qualified per the freshness law; the fields never enter any model input (context display only — leakage guard); snapshot schema bump versioned; normalizer round-trip test.

**Gate:** cockpit cycle (Gemini framing → Codex RED → GREEN → dual-CLEAR) on David's sequencing; commits David-gated as always.
