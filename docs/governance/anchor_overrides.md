# Data-Driven Anchor Overrides

This file documents approved exceptions to the default generational-anchor lock.

## Ryan Williams

- Baseline DVU: `116.0`
- Reconciled DVU: `88.0`
- Strategy reference: `c538874`
- Status: `Conditional Tier-2`
- Quantitative evidence: verified 2025 sophomore production of `49` receptions, `689` receiving yards, and `4 TD`.
- Rationale: the 2025 sophomore line materially undercuts the prior anchor-tier assumption. The update is a data-driven reconciliation, not narrative drift.

## Arch Manning

- Baseline DVU: `120.0`
- Governed DVU: `90.0`
- Governance reference: `medical_qualitative_override`
- Quantitative evidence: the anchor profile remains documented as `0.30 Dominator` and `9.2 RAS`; the governed SSoT value is intentionally reduced to `90.0`.
- Rationale: the current `gen_alpha.gold.genius_state` value reflects a governed qualitative/medical-risk adjustment layered on top of the original anchor profile. This is not hidden drift; it is an intentional rule-backed override that keeps accuracy concerns visible while preserving the audit trail for the original 120-DVU thesis.

## Guardrail

Unauthorized anchor drift remains a compliance failure. For example, a Jeremiah Smith move from `120.0` to `110.0` must fail unless a separate documented data-driven override is approved.
