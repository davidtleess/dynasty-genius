"""DG-048 RED — the Daily Control runner is RETIRED and refuses to run.

David's ruling 2026-08-26: "retire daily control." The scheduled-control-plane
role is superseded by the capture-gap alert (DG-044), the capture-health
surface, and event-stream attestation (DG-049). A retired control tool must not
be able to write a fresh marker that resurrects the illusion of a consulted
control plane — every invocation refuses, loudly, naming its successors.

The MODULE (src/dynasty_genius/sources/daily_control.py) is NOT retired: it is
library code imported by pff_intake and qb_validation, and its own contract
tests still bind it.

TDD DEVIATION, DOCUMENTED: the bare-invocation path is deliberately NOT probed
in its RED state — RED for ``main([])`` means executing a LIVE control-plane
run, which fetches from the network and writes through worktree symlinks into
production stores (this exact mistake was made once, 2026-08-26 15:25, and is
recorded in the DG-048 ticket). The refusal gate is a single code path shared
by every mode; RED was watched on the two read-only modes (--dry-run,
--preflight), and the bare test below pins the same gate after the fact.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _runner():
    name = "run_layer1_daily_control"
    if name in sys.modules:
        return sys.modules[name]
    path = REPO_ROOT / "scripts" / "run_layer1_daily_control.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


class TestRetiredRunnerRefuses:
    def test_dry_run_refuses_and_names_successors(self, capsys):
        rc = _runner().main(["--dry-run"])
        assert rc != 0
        out = capsys.readouterr().out.lower()
        assert "retired" in out
        assert "capture-gap alert" in out or "dg-044" in out

    def test_preflight_refuses_too(self, capsys):
        # No mode survives retirement: even the read-only path must refuse, or
        # a scheduled preflight would keep the marker's illusion alive.
        rc = _runner().main(["--preflight"])
        assert rc != 0
        assert "retired" in capsys.readouterr().out.lower()

    def test_bare_invocation_hits_the_same_gate(self, capsys):
        # Safe ONLY once the gate exists (see module docstring). The gate sits
        # before argparse, so this cannot reach the live-run path.
        rc = _runner().main([])
        assert rc != 0
        assert "retired" in capsys.readouterr().out.lower()

    def test_refusal_writes_nothing(self, tmp_path, monkeypatch):
        # A retired tool touching data on a stray call would be its own kind of
        # resurrection. Refusal is words only.
        monkeypatch.chdir(tmp_path)
        _runner().main(["--dry-run"])
        assert list(tmp_path.iterdir()) == []
