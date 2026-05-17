# Phase 15 - Bayesian Blend k_pos Validation

**Status:** PENDING - k_pos defaults not yet validated against Engine B residual variance.

**Current defaults (from `engine_b_contract.py` `DVS_BLEND_K`):**
- QB: k_pos = 6
- RB: k_pos = 5
- WR: k_pos = 5
- TE: k_pos = 7

**Required validation:** Fit k_pos from Engine B per-position residual variance before locking. Document methodology and results here.

**Gate:** David reviews and approves before phase 15.2 is considered complete.
