"""Append-only point-in-time data-capture utilities (market + model forward-capture).

Distinct from eval/ (validation math): capture/ only gathers + stores PIT data;
it never runs verdict logic and never feeds model inputs (overlay-only).
"""
