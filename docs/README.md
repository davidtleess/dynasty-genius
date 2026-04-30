# Dynasty Genius Docs Index

- `mission.md` — canonical product mission and competitive objective.
- `roadmap.md` — phased delivery plan from foundation to product surfaces.
- `model-architecture.md` — two-engine architecture and unified value layer.
- `next-sprint.md` — immediate implementation priorities and done criteria.
- `mission-recalibration-2026-04-29.md` — dated snapshot from recalibration session.
- `codex-review-2026-04-30.md` — independent code review baseline.
- `product-strategy-2026-04-30.md` — Session B product strategy review: highest-value decisions, surfaces to retire, deferral list, and the next three product features after validation improves.
- `decision-output-contracts.md` — canonical David-facing output schemas for rookie, roster, and trade endpoints; companion to the product strategy doc.
- `review-rookie-evaluator-2026-04-30.md` — Session B review of Session A's rookie-evaluator wiring against the output contract; includes merge recommendation and follow-up list.
- `review-rookie-drivers-and-ranks-2026-04-30.md` — Session B review of Session A's `top_drivers` and class-ranks additions; recommends NO-MERGE pending centered driver attribution and removal of intercept-as-driver.
- `review-trade-quarantine-2026-04-30.md` — Session B review of Session A's trade-quarantine work; recommends MERGE with non-blocking follow-ups (drop `experimental_totals`, remove `deprecated_fields` runtime block, drop legacy field-name pairs, align enum values).
- `review-roster-auditor-2026-04-30.md` — Session B review of Session A's roster-auditor cleanup; recommends MERGE; flags contract drift on `signal` enum and envelope shape that should be resolved by updating the contract to formalize a "heuristic surface" envelope.
- `session-summary-2026-04-30.md` — end-of-day summary covering setup, merged product-safety changes, current branch state, next work, and deferred surfaces.
- `storage-strategy.md` — git vs artifact storage policy for data, caches, models, and future GitHub setup.
