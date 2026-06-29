"""Roster Capacity Scenario Simulator.

Read-only, descriptive scenario sandbox over the existing roster cut engine.
Surfaces capacity pressure and value-at-risk; never emits normative verdicts.
"""
from __future__ import annotations

from src.dynasty_genius.roster_capacity.models import (
    CapacityAuditResult,
    CapacityCandidate,
    CapacityHealth,
    PoolRange,
    ScenarioRequest,
    ScenarioResult,
)
from src.dynasty_genius.roster_capacity.scenario_simulator import (
    simulate_capacity_scenarios,
)

__all__ = [
    "CapacityAuditResult",
    "CapacityCandidate",
    "CapacityHealth",
    "PoolRange",
    "ScenarioRequest",
    "ScenarioResult",
    "simulate_capacity_scenarios",
]
