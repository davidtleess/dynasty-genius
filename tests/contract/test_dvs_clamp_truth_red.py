"""RED — `dvs_clamped` must state whether the RAW score exceeded 100, not whether
the SHIPPED score reads 100.

Found by Codex reviewing the disclosure serialization (2026-08-18): Engine A
discards its `raw_score` and the assembler infers the flag from the already
rounded+clamped output via `>= 100.0`. A raw score of 99.99589 rounds to 100.0 and
is then disclosed as clamped — a false disclosure, and the exact inverse of the
honesty the field exists to provide. Engine B's path is already correct
(`dvs_raw > 100.0`), so these contracts pin the two paths that are not.

Semantics fixed here, explicitly, because the blend previously had none:
  * Engine A / Engine B : clamped == raw > 100.0 (strictly). Raw exactly 100.0
    truncates nothing, so it is NOT clamped.
  * Blend               : the blend is a weighted average of two components that
    are each already clamped to [0,100] under weights summing to 1, so the blend
    itself can never truncate. `dvs_clamped` states what happened to THIS score,
    so a blend row is disclosed as NOT clamped (False) even when a component was
    truncated — which also keeps the derived `xvar_ceiling_bound` truthful.
    Component-level truncation is a different fact and would need its own named
    field; none is invented here.

    *(Corrected 2026-08-18, Codex finding F6. This paragraph previously said the
    blend is clamped when EITHER component was clamped — a rule Codex rejected in
    round 2 and the implementation abandoned in round 3. The stale text survived
    the code change and contradicted `pvo_assembler.py:431-439`,
    `test_dvs_clamp_connected_red.py:7-11`, and
    `test_blend_score_is_not_clamped_even_when_a_component_was`. Recorded rather
    than silently overwritten: a docstring that outlives its semantics is a trap
    for the next agent, who would read it as the contract and "repair" working
    code back to the defect.)*
"""
from __future__ import annotations

from typing import Any

from src.dynasty_genius.scoring import engine_a as engine_a_module


class _StubModel:
    """Returns a fixed PPG so the raw score is exactly controllable."""

    def __init__(self, ppg: float) -> None:
        self._ppg = ppg

    def predict(self, _x: Any) -> list[float]:
        return [self._ppg]


def _score_with_raw_ppg(monkeypatch, ppg: float, pos: str = "WR") -> dict:
    """Drive the real Engine A scoring path with a controlled prediction."""
    scorer = engine_a_module.EngineAScorer()
    monkeypatch.setattr(scorer, "_load", lambda: None)
    monkeypatch.setattr(scorer, "_models", {pos: _StubModel(ppg)}, raising=False)
    monkeypatch.setattr(scorer, "_version", "test_stub", raising=False)
    return scorer.score(position=pos, pick=1.0, round_=1.0, age=21.0)


def test_engine_a_reports_not_clamped_when_raw_rounds_up_to_one_hundred(monkeypatch):
    """The exact defect: raw 99.9958… rounds to 100.0 but truncated nothing."""
    p90 = engine_a_module._P90_PPG["WR"]
    ppg = p90 * 0.9999589041095889  # raw score 99.99589…
    result = _score_with_raw_ppg(monkeypatch, ppg)

    assert result["dynasty_value_score"] == 100.0
    assert result["dvs_clamped"] is False


def test_engine_a_reports_not_clamped_at_exactly_one_hundred(monkeypatch):
    """Boundary: raw exactly 100.0 loses nothing, so it is not clamped."""
    result = _score_with_raw_ppg(monkeypatch, engine_a_module._P90_PPG["WR"])

    assert result["dynasty_value_score"] == 100.0
    assert result["dvs_clamped"] is False


def test_engine_a_reports_clamped_when_raw_exceeds_one_hundred(monkeypatch):
    """A genuinely truncated score must say so."""
    p90 = engine_a_module._P90_PPG["WR"]
    result = _score_with_raw_ppg(monkeypatch, p90 * 1.25)  # raw 125.0

    assert result["dynasty_value_score"] == 100.0
    assert result["dvs_clamped"] is True


def test_engine_a_reports_not_clamped_for_an_ordinary_score(monkeypatch):
    """Control: a mid-range score is neither clamped nor mislabelled."""
    p90 = engine_a_module._P90_PPG["WR"]
    result = _score_with_raw_ppg(monkeypatch, p90 * 0.60)

    assert result["dynasty_value_score"] == 60.0
    assert result["dvs_clamped"] is False
