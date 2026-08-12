From Codex — NOT CLEAR on rewritten RED b1247807. Original F1-F8 mechanisms are repaired, but seven residuals remain. Full artifact: docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_red_review_codex_v2.md

R1 David superseded S7c: all Layer 1 ingestion is authorized once cadence/route/prerequisites are determined. Grades stay model-prohibited and raw-retained, but ingestion is authorized at PFF cadence.
R2 CURRENT is never behaviorally asserted. Pin not_due -> due -> current -> due across event, ingest and next event.
R3 RotoViz/C2C cadence is undetermined, but vocabulary cannot express it; S5c claims both axes unknown while asserting only coverage. Add cadence undetermined.
R4 PFF NFL/FBS windows still not distinguished. Pin pre/post NFL noon-next-day and FBS 08:00-next-day from injected game/availability facts.
R5 duplicate-policy test sees only dedupable streams_for output; reject duplicates at raw declarations/constructor.
R6 add controller due-rollup and unknown/inadequate-nonfailure counter-cases plus all declared streams serialized.
R7 held strict-superset of offered seasons must remain adequate; S4c equality alone can license destructive exact-match semantics.

Focused RED reproduced 24 failed, true exit 1; .venv/bin/ruff clean. No GREEN. H2 rushing under test and unrelated.
