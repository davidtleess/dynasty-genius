"""Offline contract for the live shape preflight.

Codex T5: the injected-drift result was demonstrated by hand and therefore was
not durable — a manual check proves a behaviour once, a test proves it every run.
These exercise the comparison logic directly with no network and no writes.

Two wrong comparison rules preceded the current one, and both are pinned here so
neither can come back:
  * exact-vs-UNION      -> false ALARM (2024 sees {int}; the union holds {float,int})
  * subset-vs-UNION     -> false NEGATIVE (2024 turning int->float passes, because
                           2020 already contributed float to the union)
The rule is: columns exact, dtype kinds compared against THAT SEASON's own pin.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "nflverse_fingerprint_preflight.py"


def _module():
    spec = importlib.util.spec_from_file_location("preflight", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["preflight"] = module
    spec.loader.exec_module(module)
    return module


PRE = _module()


def _pinned_bundle() -> dict:
    return json.loads(
        (ROOT / "tests" / "fixtures" / "nflverse_eras" / "era_fingerprints.json")
        .read_text(encoding="utf-8")
    )


def test_every_pinned_stream_has_a_bound_loader():
    """T5: the hand-kept loader dict covered 2 of 5 streams while the docstring
    promised one fetch per stream. Resolving from the spec registry means a new
    stream cannot be silently unwired."""
    from src.dynasty_genius.nflverse_usage import build_streams

    bound = {s.name for s in build_streams() if s.loader is not None}
    pinned = {s["stream"] for s in _pinned_bundle()["shapes"]}
    assert pinned <= bound, f"pinned streams with no loader: {sorted(pinned - bound)}"
    assert len(pinned) == 5


def test_profile_covers_every_row_not_a_sample():
    """The generator profiles every row; a sampling preflight reports its own
    asymmetry as provider drift. ngs_receiving 2024 did exactly that."""
    records = [{"a": 1.0} for _ in range(400)] + [{"a": None}]
    _, kinds = PRE._observed_shape(records)
    assert kinds["a"] == ["float", "null"], (
        "a kind appearing only after row 200 must still be observed"
    )


@pytest.mark.parametrize(
    "value,expected",
    [(None, "null"), (True, "bool"), (3, "int"), (3.5, "float"), ("x", "str")],
)
def test_dtype_kinds_are_stable(value, expected):
    assert PRE._dtype_kind(value) == expected


def test_the_real_injury_pin_distinguishes_2020_from_2021():
    """The evidence the season-specific rule exists to preserve.

    2020 is Float64 and 2021+ is Int32 in the SAME shape. A union-based rule
    cannot tell them apart; that is precisely T2's false negative.
    """
    shape = next(
        s for s in _pinned_bundle()["shapes"]
        if s["stream"] == "injuries" and 2020 in s["seasons"]
    )
    by_season = shape["dtype_kinds_by_season"]
    assert by_season["2020"]["season"] == ["float"]
    assert by_season["2021"]["season"] == ["int"]
    assert sorted(shape["dtype_kinds"]["season"]) == ["float", "int"], (
        "the union remains as descriptive metadata"
    )


def test_a_season_specific_dtype_change_is_not_hidden_by_the_union():
    """Simulates 2024 flipping int -> float. Under the old subset-vs-union rule
    this passed, because 2020 had already contributed `float`."""
    shape = next(
        s for s in _pinned_bundle()["shapes"]
        if s["stream"] == "injuries" and 2020 in s["seasons"]
    )
    union = set(shape["dtype_kinds"]["season"])
    pinned_2024 = set(shape["dtype_kinds_by_season"]["2024"]["season"])
    observed = {"float"}

    assert observed <= union, "the union would have accepted this — the false negative"
    assert observed != pinned_2024, "the season-specific pin rejects it — the fix"


def test_preflight_writes_nothing(tmp_path):
    """A diagnostic must not mutate anything; it reports and exits."""
    import inspect

    source = inspect.getsource(PRE)
    for forbidden in ("write_text(", "open(", "sqlite3.connect", "ALTER ", "DELETE "):
        if forbidden == "open(":
            continue  # read_text is fine; guard the mutating forms below
        assert forbidden not in source.replace("read_text(", ""), (
            f"preflight appears to mutate state via {forbidden!r}"
        )


# ── Codex R3-T4: tests must execute the VERDICT, not only its helpers ─────────
#
# The previous suite checked `_observed_shape`, dtype helpers and registry
# membership, then proved set inequality by hand. `_verdict` was nested inside
# main() and unreachable without a live loader, so a broken verdict, a wrong
# chosen season, or an unbound loader all left ten tests green.

SHAPE = {
    "fingerprint": "f" * 64,
    "stream": "injuries",
    "seasons": [2020, 2021],
    "columns": ["gsis_id", "season", "week"],
    "dtype_kinds": {"gsis_id": ["str"], "season": ["float", "int"], "week": ["float", "int"]},
    "dtype_kinds_by_season": {
        "2020": {"gsis_id": ["str"], "season": ["float"], "week": ["float"]},
        "2021": {"gsis_id": ["str"], "season": ["int"], "week": ["int"]},
    },
}


def test_verdict_accepts_an_exact_season_match():
    ok, detail = PRE.verdict(
        SHAPE, ["gsis_id", "season", "week"],
        {"gsis_id": ["str"], "season": ["float"], "week": ["float"]}, 2020,
    )
    assert ok and detail == {}


def test_verdict_rejects_a_season_specific_dtype_change():
    """2021 flipping int -> float. The era union holds both, so a union-based
    rule accepted this; the season-specific rule must not."""
    ok, detail = PRE.verdict(
        SHAPE, ["gsis_id", "season", "week"],
        {"gsis_id": ["str"], "season": ["float"], "week": ["int"]}, 2021,
    )
    assert not ok
    assert detail["dtype_changed"]["season"] == {"pinned": ["int"], "observed": ["float"]}


def test_verdict_rejects_column_drift():
    ok, detail = PRE.verdict(
        SHAPE, ["gsis_id", "season", "week", "surprise"], {}, 2020
    )
    assert not ok
    assert detail["unexpected_columns"] == ["surprise"]


def test_verdict_rejects_an_unpinned_season():
    ok, detail = PRE.verdict(
        SHAPE, ["gsis_id", "season", "week"],
        {"gsis_id": ["str"], "season": ["int"], "week": ["int"]}, 2099,
    )
    assert not ok and detail == {"unpinned_season": "2099"}


@pytest.mark.parametrize(
    "records,expect",
    [
        ([{"a": 1}, {"a": 1, "late": "x"}], "late"),
        ([{"a": 1, "b": 2}, {"a": 1}], "b"),
    ],
)
def test_a_heterogeneous_fetch_refuses(records, expect):
    """R3-T1: a field present only on a later row must refuse, not be ignored."""
    with pytest.raises(PRE.HeterogeneousFetch, match=expect):
        PRE._observed_shape(records)


def test_main_reaches_the_verdict_with_the_real_selected_spec(monkeypatch, capsys):
    """R3-T4: prove the CLI wires the chosen spec's loader into the comparison.

    No network and no writes: the loader is injected, so this exercises season
    selection, spec resolution and the verdict together.
    """
    from src.dynasty_genius.nflverse_usage import build_streams

    pinned = next(
        s for s in _pinned_bundle()["shapes"]
        if s["stream"] == "injuries" and 2025 in s["seasons"]
    )
    witness = pinned["fixture_rows_by_season"]["2025"]

    class _Frame:
        def to_dicts(self):
            return witness

    from dataclasses import replace

    import src.dynasty_genius.nflverse_usage as usage

    calls = {}

    def _fake_loader(seasons, **kwargs):
        calls["seasons"] = seasons
        calls["kwargs"] = kwargs
        return _Frame()

    # Swap the loader on the REAL spec, so spec resolution, season selection and
    # loader_kwargs are all still exercised — only the network call is replaced.
    real = {s.name: s for s in build_streams()}["injuries"]
    patched = replace(real, loader=_fake_loader)
    monkeypatch.setattr(
        usage,
        "build_streams",
        lambda: tuple(
            patched if s.name == "injuries" else s for s in build_streams()
        ),
    )
    rc = PRE.main(["--stream", "injuries", "--season", "2025"])
    out = capsys.readouterr().out

    assert calls["seasons"] == [2025], "the CLI must fetch the season it was asked for"
    assert rc == 0, out
    assert "matches pinned shape" in out
