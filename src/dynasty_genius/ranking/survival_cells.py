"""Reading the DG-164 retention cells (``retention_R_v3.json``) without changing their meaning.

The file's own definition block says what a cell is: ``R(h) = mean(VOR at h, UNCONDITIONAL)
/ mean(VOR at 0)`` keyed on (position, age band, margin bin), where margin is the conditional
rate ``projection_2y / bar_ppg``. Survival is already inside R. This loader:

* refuses any file that does not carry that unconditional warning, so a superseded cell file
  with different semantics (nine existed at once on 2026-09-06) cannot load by accident;
* returns a suppressed cell's own stated reason and NO ratios — never a neighbour's numbers
  (the rule that held all week and that DG-176 is most tempted to break);
* records the path and sha256 of what it read, because the number on a card must be
  traceable to the bytes that produced it.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

_INF = float("inf")

# Age bands exactly as the cells were FITTED (preserved rebuild_fixed.py:52):
#     pd.cut(age, [19, 23, 25, 27, 29, 31, 45], labels=[...])
# on exact age at September 1 of the season. pd.cut is right-inclusive, so the bands are
# (19, 23], (23, 25], (25, 27], (27, 29], (29, 31], (31, 45]: a 23.5 is "24-25", a 31.5 is
# "32+". Ages outside (19, 45] were excluded from the panel and have no band.
AGE_CUT_EDGES: tuple[float, ...] = (19.0, 23.0, 25.0, 27.0, 29.0, 31.0, 45.0)
AGE_BAND_LABELS: tuple[str, ...] = ("<=23", "24-25", "26-27", "28-29", "30-31", "32+")


def age_band(age: Optional[float]) -> Optional[str]:
    """The cell band for an exact age, by the cells' own right-inclusive cut.

    Sleeper serves whole-year ages (floor of the true age); a served 23 may be anywhere in
    [23, 24) and the panel would have binned the top of that range as "24-25". Callers that
    can compute the exact age at September 1 from a birth date should, and say so.
    """
    if age is None:
        return None
    a = float(age)
    if not math.isfinite(a):
        return None
    if a <= AGE_CUT_EDGES[0] or a > AGE_CUT_EDGES[-1]:
        return None
    for label, lo, hi in zip(AGE_BAND_LABELS, AGE_CUT_EDGES[:-1], AGE_CUT_EDGES[1:]):
        if lo < a <= hi:
            return label
    return None


CellStatus = Literal["cell", "suppressed", "absent"]


@dataclass(frozen=True)
class CellHit:
    status: CellStatus
    key: Optional[tuple[str, str, str]]
    ratios: Optional[tuple[float, ...]]
    n: Optional[int]
    reason: Optional[str]
    mean_vor_at_0: Optional[float] = None


@dataclass(frozen=True)
class _Bin:
    key: tuple[str, str, str]
    lo: float
    hi: float
    published: bool
    ratios: Optional[tuple[float, ...]]
    n: int
    reason: Optional[str]
    mean_vor_at_0: Optional[float]


class RetentionCells:
    def __init__(self, source_path: Path, source_sha256: str, definition: dict,
                 bins: dict[tuple[str, str], list[_Bin]]) -> None:
        self.source_path = source_path
        self.source_sha256 = source_sha256
        self.definition = definition
        self._bins = bins

    @property
    def horizons(self) -> int:
        return int(self.definition["horizons"])

    @property
    def bar_ranks(self) -> dict[str, int]:
        return {k: int(v) for k, v in self.definition["bar_ranks"].items()}

    @classmethod
    def load(cls, path: Path | str) -> "RetentionCells":
        p = Path(path)
        raw_bytes = p.read_bytes()
        raw = json.loads(raw_bytes)
        definition = raw.get("definition") or {}
        warning = str(definition.get("WARNING_double_count", ""))
        if "UNCONDITIONAL" not in warning.upper():
            raise ValueError(
                f"{p} does not declare its ratios as unconditional (no WARNING_double_count "
                "in the definition block). Refusing: a cell file with different semantics "
                "cannot be told apart from the canonical one by its shape alone."
            )
        if "horizons" not in definition or "bar_ranks" not in definition:
            raise ValueError(f"{p} definition block lacks horizons/bar_ranks")
        h = int(definition["horizons"])
        bins: dict[tuple[str, str], list[_Bin]] = {}

        def edge(v: Optional[float], default: float) -> float:
            return default if v is None else float(v)

        for c in raw.get("cells", []):
            key = (c["position"], c["ageband"], c["margin_bin"])
            ratios = tuple(float(c[f"R{k}"]) for k in range(1, h + 1))
            bins.setdefault(key[:2], []).append(_Bin(
                key=key, lo=edge(c.get("edge_lo"), -_INF), hi=edge(c.get("edge_hi"), _INF),
                published=True, ratios=ratios, n=int(c["n"]), reason=None,
                mean_vor_at_0=c.get("mean_VOR_at_0")))
        for c in raw.get("suppressed", []):
            key = (c["position"], c["ageband"], c["margin_bin"])
            bins.setdefault(key[:2], []).append(_Bin(
                key=key, lo=edge(c.get("edge_lo"), -_INF), hi=edge(c.get("edge_hi"), _INF),
                published=False, ratios=None, n=int(c["n"]),
                reason=str(c.get("suppressed_because") or "suppressed"),
                mean_vor_at_0=c.get("mean_VOR_at_0")))
        return cls(p, hashlib.sha256(raw_bytes).hexdigest(), definition, bins)

    def lookup(self, position: str, age: Optional[float], margin: float) -> CellHit:
        band = age_band(age)
        if band is None:
            return CellHit("absent", None, None, None, "age unknown, cannot bin")
        pos = position.upper()
        hits = [b for b in self._bins.get((pos, band), []) if b.lo <= margin < b.hi]
        if len(hits) > 1:
            raise ValueError(f"margin {margin} matched {len(hits)} bins for {pos} {band}: "
                             "the edges are not a partition")
        if not hits:
            return CellHit("absent", None, None, None,
                           f"no cell for {pos} {band} at margin {margin:.3f}")
        b = hits[0]
        if not b.published:
            return CellHit("suppressed", b.key, None, b.n, b.reason, b.mean_vor_at_0)
        return CellHit("cell", b.key, b.ratios, b.n, None, b.mean_vor_at_0)
