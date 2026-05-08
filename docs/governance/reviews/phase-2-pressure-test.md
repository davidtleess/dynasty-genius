# Phase 2 Pressure Test: Identity & Context Unification

To ensure our Phase 2 foundation is "decision-grade" before we resume Engine B modeling, I am delegating these specific pressure-test directives to the specialized agents.

---

## 1. CODEX: ID Collisions & Governance Audit
**Objective:** Stress-test the `dg_id` format and ensure zero market leakage in the identity layer.

**Tasks:**
- **Collision Analysis:** Evaluate the `first_last_pos_birthyear` format against the NFL historical universe. Identify collisions (e.g., same-name players in the same draft class) and propose a deterministic tie-breaker (e.g., `_2`, `_3`) that remains human-readable.
- **Suffix Handling:** Ensure "Jr.", "Sr.", "III", and common name variations (Josh vs. Joshua) resolve to the same `dg_id` without manual intervention.
- **Leakage Veto:** Review `src/dynasty_genius/pipelines/identity.py`. Ensure no market-derived fields (KTC, ADP) are used as primary keys or join-anchors for the identity mapping. If found, issue a governance veto.

---

## 2. GENIE: Databricks Lineage & Delta Integrity
**Objective:** Move Identity Resolution from a script to a governed Databricks platform asset.

**Tasks:**
- **Delta Schema Design:** Define the DDL for `silver.player_identity` with SCD Type 2 tracking (Slowly Changing Dimensions). We need to know when a `sleeper_id` or `pff_id` was updated or corrected.
- **Lineage Integration:** Connect the identity pipeline to the `gen_alpha.gold.artifact_registry` defined in the Databricks Lineage Plan. Every `dg_id` row should be traceable back to its Bronze source snapshot.
- **Promotion Workflow:** Draft the `databricks.yml` configuration to deploy the Identity Resolution job across Dev, Staging, and Prod targets.

---

## 3. CLAUDE: Adapter Integrity & Fuzzy Matching
**Objective:** Verify that source-specific IDs actually resolve to the canonical `dg_id`.

**Tasks:**
- **Source Reconciliation:** Compare 10 high-impact players (e.g., Christian McCaffrey, Puka Nacua, Anthony Richardson) across Sleeper, PFF, and KTC. Verify if their IDs can be automatically resolved to a single `dg_id` using only names and positions.
- **Fuzzy Match Engine:** Implement a "Confidence Level" for ID resolution. If a match is < 95% certain (e.g., name mismatch between Sleeper and PFF), the row must be flagged as `VERIFICATION_STATUS = "CONFLICT"` for manual review.
- **Mock Data Expansion:** Expand `resources/mock_playerprofiler_identity.json` to include 2026/2027 draft prospects to test Engine A integration.

---

## 4. GEMINI (PM): Decision Context Validation
**Objective:** Confirm that the `LeagueContext` supports David's specific decisions.

**Tasks:**
- **Draft Pick Logic:** Verify that the `DraftPick` model in `league_context.py` correctly handles "acquired" vs. "original" picks for trade analysis.
- **Scoring Parity:** Ensure the `is_superflex` and `te_premium` flags propagate correctly to the (future) Valuation engines.
- **Final Sign-off:** Review all agent outputs and certify that Phase 2 satisfies the North Star Architecture before allowing the "Engine B Ignition" sprint to start.
