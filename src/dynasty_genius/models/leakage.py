"""Governed leakage guard — network-free, provider-free.

Extracted from the legacy mixed enrichment script retired on 2026-08-07, which combined
this guard with two unsanctioned acquisition routes: an unauthenticated PlayerProfiler
HTTP client sending a spoofed browser User-Agent, and a direct CFBD client bypassing the
governed ``run_cfbd_foundation_refresh.py`` wrapper. The retired provider route is named
in the retirement contract test and is deliberately not reproduced here — this module
must be greppable as carrying no provider endpoint.

The guard itself was never the problem — it is the market-leakage check that keeps
KTC/ADP-derived columns out of Engine A training rows (``00`` §KTC And Market Data:
"Any market-derived feature in a model training row is leakage and a defect").
It is therefore preserved verbatim in behaviour and moved somewhere it can be
imported **without importing a provider route**.

**This module must never acquire anything.** It takes a frame that is already in
memory and answers one question about its columns. A contract test pins that it
imports no network client and carries no provider URL.

**The report destination is explicit and required.** The original wrote to a fixed
repo-root path as a side effect, so a caller could not choose where a refusal was
recorded and two callers would overwrite each other. ``report_path`` is now a
required keyword argument.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from src.dynasty_genius.models.engine_a_contract import (
    LEAKAGE_REGEX,
    PROHIBITED_COLUMNS,
)

__all__ = ["check_leakage", "find_leaking_columns"]


def find_leaking_columns(df: pd.DataFrame) -> list[str]:
    """Return the offending column names, in frame order. Pure; writes nothing."""
    prohibited_regex = re.compile(LEAKAGE_REGEX, re.IGNORECASE)
    lowered_prohibited = {name.lower() for name in PROHIBITED_COLUMNS}
    return [
        column
        for column in df.columns
        if column.lower() in lowered_prohibited
        or prohibited_regex.match(column.lower())
    ]


def check_leakage(df: pd.DataFrame, *, report_path: Path | str) -> None:
    """Refuse a frame carrying market-derived columns.

    Clean frame → returns ``None`` and **writes nothing**: a passing check must not
    litter the tree with an artifact that a later reader could mistake for a finding.

    Offending frame → writes a durable JSON diagnostic to ``report_path`` **before**
    raising, so the refusal survives the exception, then raises ``ValueError``.
    Fail-closed: the raise is not optional and is never downgraded to a warning.
    """
    offending = find_leaking_columns(df)
    if not offending:
        return

    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "status": "FAILURE",
                "reason": "LEAKAGE DETECTED",
                "offending_columns": offending,
                "timestamp": pd.Timestamp.now().isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    raise ValueError(f"LEAKAGE DETECTED: {offending}")
