"""Pytest discovery wrapper for the conformance suite."""

import importlib.util
from pathlib import Path

_CONFORMANCE_PATH = Path(__file__).with_name("conformance_check.py")
_SPEC = importlib.util.spec_from_file_location("conformance_check", _CONFORMANCE_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

test_rookie_decision_weights_keep_draft_capital_first = (
    _MODULE.test_rookie_decision_weights_keep_draft_capital_first
)
test_2026_tier_1_prospect_map_is_ground_truth_anchored = (
    _MODULE.test_2026_tier_1_prospect_map_is_ground_truth_anchored
)
test_roster_auditor_applies_elite_rb_yac_exception = (
    _MODULE.test_roster_auditor_applies_elite_rb_yac_exception
)
test_trade_output_blocks_verdict_until_unified_valuation_layer = (
    _MODULE.test_trade_output_blocks_verdict_until_unified_valuation_layer
)
test_trade_output_flags_age_curve_sells_with_protocol_support = (
    _MODULE.test_trade_output_flags_age_curve_sells_with_protocol_support
)
test_trade_market_values_normalize_to_dvu_before_aggregation = (
    _MODULE.test_trade_market_values_normalize_to_dvu_before_aggregation
)
