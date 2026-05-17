# Phase 15 - Bayesian Blend k_pos Validation

**Status:** APPROVED FOR PHASE 15 V0 - David approved continuing on 2026-05-17.

The k_pos defaults remain documented assumptions, not empirically fitted residual-variance estimates. Any future change to these constants requires a residual-variance validation update here before implementation.

**Current defaults (from `engine_b_contract.py` `DVS_BLEND_K`):**
- QB: k_pos = 6
- RB: k_pos = 5
- WR: k_pos = 5
- TE: k_pos = 7

**Required future validation:** Fit k_pos from Engine B per-position residual variance before changing these defaults. Document methodology and results here.

**Gate:** Cleared for Phase 15 V0 by David approval to proceed. Residual-variance fitting remains a follow-up calibration task, not a blocker for Trade Lab v0.
