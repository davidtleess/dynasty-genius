"""Comp v3.x verified data extraction — the numeric source for the comp doc.

Bases (locked framing + the v3.4-v3.7 Codex round corrections):
- BOARD = rows whose divergence signal_status is gates_passed or inside_band
  (status membership, NOT percentile presence). No gates_blocked row can reach a
  served artifact under the current runner (whole-run fail-close); the row-level
  "signal withheld" state is a future per-row-quarantine ticket, not a present state.
- DG ranks = COMPETITION RANKING over the producer's model-backed rows. The
  PER-POSITION partitions (QB47/RB111/WR199/TE111) are the populations for both
  position ranks AND model percentiles; the 468-row UNION is the population for
  the OVERALL rank only — overall rank and percentile share no denominator.
  Ties share the lowest rank (T-TE1 x11); canonical DG id keys the rank maps and
  breaks ROW order only, never rank values. Ranks are filter-stable.
- Market rank = FantasyCalc NATIVE market_overlay.position_rank (a LABEL; never
  subtracted against DG ranks — the stored percentile delta is the only arithmetic).
- Display delta = stored model_minus_market_delta x 100, EXACT-DECIMAL
  half-away-from-zero integer (json parsed with parse_float=Decimal; binary-float
  scaling is a defect), -0 normalized to 0. Producer integer field = production home.
- FA facts report BOTH scopes: the 97 board FAs (market read exists) and the full
  model-valued FA pool inside the cohort (valued, with or without a market read).
- Movement = GLOBAL latest capture pair, same-player renderable intersection,
  |display-delta change| >= 1; sign-neutral tie order by CANONICAL DG id (history
  keys are sleeper ids, mapped before ordering); decomposition reports the 2+ pp
  subset. "Model held" and "market moved" are DERIVED per scope (full compared
  set AND the surfaced roster separately — a clause renders only from its own
  scope's derivation); percentile-shift attribution verifies raw xVAR across ALL
  common model-backed rows before naming cohort composition. Off-board roster
  players classify strictly: "DG read unavailable" (model-routed, xVAR null) or
  "pre-model"; anything finer awaits a producer classifier.
- Group facts: count + valued x/y are the renderable layer. The value basis is
  RULED (David 2026-07-12: the governed team_value_matrix starter+depth-credit
  definition) — raw sums are NOT computed here (the ruled producer artifact is
  the only legitimate source). Because the ruled basis is CROSS-POSITION
  (FLEX/SUPER_FLEX starters + pooled bench depth), the coverage gate is the
  FULL skill-roster dependency closure per roster (unknown-position rostered
  rows FAIL closure; IR/taxi active-set refinement is producer-owned), below.
- Team aliases normalize for display: LVR->LV, SFO->SF, LA->LAR, KAN->KC,
  NOR->NO, NWE->NE, TAM->TB; unknown -> rendered as-is (designed fallback).

Scope honesty — this script verifies what it prints from the latest artifact AND
the movement/model-held blocks from market_divergence_history.db. It does NOT
verify: the volatility capture-start date (fc_forward_capture.db) or the DVS/xVAR
clamp ties. Those facts are verified by separate probes recorded in the ledger.
"""
import collections
import hashlib
import json
import os
import pathlib
import sqlite3
import sys
from decimal import ROUND_HALF_UP, Decimal

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from src.dynasty_genius.universe_market_divergence import (  # noqa: E402
    MODEL_BACKED_ROUTES,
    MODEL_BACKED_STATUSES,
)

ART = REPO_ROOT / "app/data/valuation/universe_market_divergence_latest.json"
BOARD_STATUSES = {"gates_passed", "inside_band"}

NUMERIC_BOUND = Decimal("1e12")  # no governed quantity approaches this


def strict_pairs(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise SystemExit(f"FAIL-CLOSED: duplicate JSON key {k!r}")
        seen[k] = v
    return seen


def strict_loads(raw, label):
    # r14-6: the ONLY sanctioned JSON entry point — duplicate keys rejected,
    # non-finite tokens rejected, applied to exact bytes before any use.
    return json.loads(
        raw, parse_float=Decimal, object_pairs_hook=strict_pairs,
        parse_constant=lambda s: (_ for _ in ()).throw(
            ValueError(f"non-finite token {s} in {label}")))


def validate_universe_rows(rows_in, source_label):
    def walk(v, path):
        if isinstance(v, dict):
            for k2, x in v.items():
                if k2 == "decision_supported" and x is not False:
                    raise SystemExit(f"FAIL-CLOSED[{source_label}]: nested "
                                     f"decision_supported={x!r} at {path}")
                walk(x, path)
        elif isinstance(v, list):
            for x in v:
                walk(x, path)
        elif isinstance(v, bool):
            pass
        elif isinstance(v, float):
            if v != v or v in (float("inf"), float("-inf")) or abs(v) > float(NUMERIC_BOUND):
                raise SystemExit(f"FAIL-CLOSED[{source_label}]: non-finite/unbounded float at {path}")
        elif isinstance(v, Decimal):
            if not v.is_finite() or abs(v) > NUMERIC_BOUND:
                raise SystemExit(f"FAIL-CLOSED[{source_label}]: unbounded/non-finite "
                                 f"Decimal at {path}")
        elif isinstance(v, int):
            if abs(v) > NUMERIC_BOUND:
                raise SystemExit(f"FAIL-CLOSED[{source_label}]: unbounded int at {path}")
    for r in rows_in:
        walk(r, (r.get("player") or {}).get("full_name") or r.get("dg_player_id") or "?")
    return rows_in
TEAM_ALIASES = {"LVR": "LV", "SFO": "SF", "LA": "LAR", "KAN": "KC",
                "NOR": "NO", "NWE": "NE", "TAM": "TB"}

# Reproducible evidence pin (Codex round-5): DG_AS_OF=YYYY-MM-DD rebuilds the row
# universe from market_divergence_history.db for that capture date (full payloads,
# 12k rows/day) instead of the live latest artifact, so a frozen comp's numbers
# regenerate after the daily runner moves the store. Movement pairs the pinned
# date with the previous renderable capture date.
AS_OF = os.environ.get("DG_AS_OF")
AS_OF_REF = os.environ.get("DG_AS_OF_REF")
if AS_OF_REF and not AS_OF:
    raise SystemExit("FAIL-CLOSED: DG_AS_OF_REF supplied without DG_AS_OF — a partial "
                     "pin must abort, never silently run live (Codex r9-2)")
if AS_OF and AS_OF_REF:
    # Full-fidelity pin (Codex r8-3): the Jul-11 artifact is git-tracked (ed1a0ae,
    # PR #146), so a ref-pinned run reads the EXACT original artifact — rows AND
    # all three root freshness facts — via git. Fail-closed on date mismatch.
    import subprocess
    blob = subprocess.run(
        ["git", "show", f"{AS_OF_REF}:app/data/valuation/universe_market_divergence_latest.json"],
        capture_output=True, cwd=REPO_ROOT, check=True).stdout
    d = strict_loads(blob, "git-pinned artifact")
    if d.get("market_snapshot_date") != AS_OF:
        raise SystemExit(f"FAIL-CLOSED: ref {AS_OF_REF} artifact is "
                         f"{d.get('market_snapshot_date')!r}, not DG_AS_OF {AS_OF!r}")
    rows = validate_universe_rows(d["players"], "git-pinned artifact")
    print(f"PINNED (git ref {AS_OF_REF}): root+rows are git-immutable for {AS_OF}; "
          "root freshness facts ORIGINAL. Movement pair comes from the history db "
          "(mutable) — per-day content hashes print with the movement block; "
          "reproduction requires matching hashes (r10-4).")
elif AS_OF:
    import sqlite3
    HIST = REPO_ROOT / "app/data/market_divergence_history.db"
    # (note: app/data/valuation/market_divergence_history.db is a 0-byte stray; the
    # 78MB live store is at app/data/. Flagged in the 2026-07-13 ledger.)
    # r13-2: ONE connection + transaction serves BOTH the board rows and the
    # movement evidence in refless mode (a WAL swap between two connections
    # could pair board A with movement B — probe-proven).
    _PIN_CONN = sqlite3.connect(HIST)
    _PIN_CONN.execute("BEGIN")
    dates = [x[0] for x in _PIN_CONN.execute(
        "SELECT DISTINCT capture_date FROM market_divergence_history ORDER BY capture_date")]
    if AS_OF not in dates:
        raise SystemExit(f"FAIL-CLOSED: DG_AS_OF {AS_OF!r} not in history dates {dates}")
    _pin_rows = []
    for _sid, _ds, _pl in _PIN_CONN.execute(
            "SELECT player_id, decision_supported, payload_json "
            "FROM market_divergence_history WHERE capture_date=?", (AS_OF,)):
        if not (isinstance(_ds, int) and not isinstance(_ds, bool) and _ds == 0):
            raise SystemExit(f"FAIL-CLOSED: SQL decision_supported={_ds!r} for "
                             f"{_sid} on {AS_OF} at LOAD TIME (No-Verdict Line)")
        _pin_rows.append(strict_loads(_pl, "history-pinned row"))
    rows = validate_universe_rows(_pin_rows, "history-pinned rows")
    _mo = next((r["market_overlay"] for r in rows if r.get("market_overlay")
                and (r["market_overlay"] or {}).get("source_timestamp")), {})
    # Root build metadata is NOT persisted in history (only per-row payloads), so a
    # pinned run must never fabricate the root clock from row timestamps (Codex r7-5).
    # It fails closed to an explicit marker; per-row capture range is reported instead.
    _cts = sorted({r.get("captured_at") for r in rows if r.get("captured_at")})
    d = {"players": rows,
         "market_snapshot_date": AS_OF,
         "market_source_timestamp": _mo.get("source_timestamp", "unknown (pinned)"),
         "captured_at": ("UNAVAILABLE UNDER PIN — root build clock not persisted in history; "
                         f"per-row captures span {_cts[0]}..{_cts[-1]}" if _cts
                         else "UNAVAILABLE UNDER PIN")}
    print(f"PINNED-DEGRADED: DG_AS_OF={AS_OF} rows={len(rows)} — history rebuild; "
          "root freshness facts INCOMPLETE (contract: degraded). For full-fidelity "
          "evidence use DG_AS_OF_REF=<commit> (the artifact is git-tracked).")
else:
    d = strict_loads(open(ART, "rb").read(), "live artifact")
    rows = validate_universe_rows(d["players"], "live artifact")


def name(r):
    return (r.get("player") or {}).get("full_name") or r.get("dg_player_id")


def pos(r):
    return (r.get("player") or {}).get("position") or "?"


def team(r):
    t = (r.get("player") or {}).get("team")
    return TEAM_ALIASES.get(t, t)


def xvar(r):
    return (r.get("valuation") or {}).get("xvar")


def div(r):
    return r.get("divergence") or {}


def model_backed(r):
    v = r.get("valuation") or {}
    return (
        pos(r) != "?"
        and v.get("xvar") is not None
        and v.get("engine_path") in MODEL_BACKED_ROUTES
        and v.get("valuation_status") in MODEL_BACKED_STATUSES
    )


cohort = [r for r in rows if model_backed(r)]
board = [r for r in cohort if div(r).get("signal_status") in BOARD_STATUSES]
suppressed = [r for r in cohort if div(r).get("signal_status") == "gates_blocked"]


def ranked(items):
    return sorted(items, key=lambda r: (-xvar(r), r.get("dg_player_id") or ""))


# DG ranks over the FULL model cohort (the model_percentile population),
# stable across every display filter. COMPETITION RANKING (v3.6): equal xVAR
# shares the lowest rank of the tie group; canonical-id order breaks ROW order
# only, never rank values.
def canon_id(r):
    cid = r.get("dg_player_id")
    if not cid:
        raise SystemExit(f"FAIL-CLOSED: missing dg_player_id for {name(r)!r}")
    return cid


def comp_ranks(items):
    """Competition ranking keyed by CANONICAL DG id — display names may collide
    (duplicate/conflict seed); ids never silently overwrite."""
    ordered = ranked(items)
    values = [xvar(r) for r in ordered]
    ranks, ties = {}, {}
    first_at = {}
    for i, v in enumerate(values):
        if v not in first_at:
            first_at[v] = i + 1
    counts = collections.Counter(values)
    for i, r in enumerate(ordered):
        cid = canon_id(r)
        if cid in ranks:
            raise SystemExit(f"FAIL-CLOSED: duplicate canonical id {cid!r}")
        ranks[cid] = first_at[values[i]]
        ties[cid] = counts[values[i]]
    return ranks, ties


dg_overall_rank, overall_tie = comp_ranks(cohort)
bypos = collections.defaultdict(list)
for r in cohort:
    bypos[pos(r)].append(r)
dg_pos_rank, pos_tie = {}, {}
for p, items in bypos.items():
    pr, pt = comp_ranks(items)
    dg_pos_rank.update(pr)
    pos_tie.update(pt)


def rank_label(prefix, r):
    cid = canon_id(r)
    if pos_tie.get(cid, 1) > 1:
        return f"T-{prefix}{dg_pos_rank[cid]} x{pos_tie[cid]}"
    return f"{prefix}{dg_pos_rank[cid]}"


def overall_label(r):
    cid = canon_id(r)
    if overall_tie.get(cid, 1) > 1:
        return f"T-{dg_overall_rank[cid]} x{overall_tie[cid]}"
    return str(dg_overall_rank[cid])


def fc_rank(r):
    return (r.get("market_overlay") or {}).get("position_rank")


def pct(v):
    dec = v if isinstance(v, Decimal) else Decimal(str(v))
    return str(int((dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def display_delta(value):
    """v3.6 rounding contract: EXACT-DECIMAL half-away-from-zero integer, -0 -> 0.

    Binary float scaling misrounds serialized decimals (-0.285 * 100 =
    -28.499999... -> -28 instead of the exact -29). Route through Decimal on the
    shortest serialized form; the producer integer field is the production home.
    """
    dec = value if isinstance(value, Decimal) else Decimal(str(value))
    out = int((dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return 0 if out == 0 else out


def delta_pts(r):
    return f"{display_delta(div(r)['model_minus_market_delta']):+d}"


sig_display = {
    "MODEL_HIGH_MARKET_LOW": "we rank higher",
    "MODEL_LOW_MARKET_HIGH": "market higher",
    "INSIDE_BAND": "within band",
}

print(f"ARTIFACT: market_snapshot_date={d['market_snapshot_date']} "
      f"market_source_timestamp={d['market_source_timestamp']} captured_at={d['captured_at']}")
cohc = collections.Counter(pos(r) for r in cohort)
engc = collections.Counter((r.get("valuation") or {}).get("engine_path") for r in board)
posc = collections.Counter(pos(r) for r in board)
sigc = collections.Counter(div(r).get("signal") for r in board)
statc = collections.Counter(div(r).get("signal_status") for r in board)
volc = collections.Counter(
    (r.get("market_overlay") or {}).get("market_volatility_status") for r in board
)
print(f"MODEL COHORT: {len(cohort)} union rows (OVERALL-rank population only; "
      f"percentile + position-rank populations are the per-position partitions) | {dict(cohc)}")
print(f"BOARD (gates_passed+inside_band): {len(board)} | {dict(posc)} | engines: {dict(engc)}")
print(f"SUPPRESSED (gates_blocked, incl volatile_market): {len(suppressed)}")
print(f"SIGNALS: {dict(sigc)} | status: {dict(statc)}")
print(f"VOLATILITY (board rows): {dict(volc)}")
print(f"NON-BOARD: {len(rows) - len(board)} of {len(rows)} total")

mine = [
    r for r in board
    if isinstance(r.get("league_context"), dict) and r["league_context"].get("roster_id") == 1
]
mine_all = [
    r for r in rows
    if isinstance(r.get("league_context"), dict) and r["league_context"].get("roster_id") == 1
]
msig = collections.Counter(div(r).get("signal") for r in mine)
print(f"\nDAVID ROSTER: {len(mine_all)} players, {len(mine)} on-board | "
      f"we-higher {msig.get('MODEL_HIGH_MARKET_LOW', 0)} "
      f"· market-higher {msig.get('MODEL_LOW_MARKET_HIGH', 0)} "
      f"· within band {msig.get('INSIDE_BAND', 0)} "
      f"· not compared {len(mine_all) - len(mine)} (classified in OFF-BOARD below)")
print("| Player | Pos | Team | DG Rank (cohort) | Market Rank (FC native) "
      "| Model pct | Market pct | Δ (stored) | Read |")
print("|---|---|---|---|---|---|---|---|---|")
for r in sorted(mine, key=lambda r: -div(r)["model_minus_market_delta"]):
    n = name(r)
    p = pos(r)
    print(f"| {n} | {p} | {team(r)} | {rank_label(p, r)} | {p}{fc_rank(r)} | "
          f"{pct(div(r)['model_percentile'])} | {pct(div(r)['market_percentile'])} | "
          f"{delta_pts(r)} | {sig_display.get(div(r).get('signal'), '?')} |")
off = [name(r) for r in mine_all if r not in mine]
print(f"off-board: {off}")

def is_fa(r):
    lc = r.get("league_context")
    return isinstance(lc, dict) and not lc.get("rostered")


fa = [r for r in board if is_fa(r)]
fa_pool = [r for r in cohort if is_fa(r)]
fa_x = ranked(fa)
fa_mix = collections.Counter(pos(r) for r in fa_x[:15])
below_repl = sum(1 for r in fa if xvar(r) < 0)
pool_below = sum(1 for r in fa_pool if xvar(r) < 0)
print(f"\nFREE AGENTS — board (market read): {len(fa)} ({below_repl} below replacement) | "
      f"FULL model-valued FA pool in cohort: {len(fa_pool)} ({pool_below} below replacement) "
      f"| top-15 board mix by raw xVAR: {dict(fa_mix)}")
print("top 8 FA by raw xVAR:",
      [f"{name(r)} ({pos(r)}, xVAR {xvar(r):.1f})" for r in fa_x[:8]])

no_mkt_fa = ranked([r for r in fa_pool if not any(x is r for x in board)])
if no_mkt_fa:
    ex = max(no_mkt_fa, key=lambda r: xvar(r))
    print(f"SHOW-ALL-VALUED exemplar (highest-xVAR valued/no-market FA): {name(ex)} "
          f"({team(ex)} {pos(ex)}), overall {overall_label(ex)}, "
          f"{rank_label(pos(ex), ex)}, market read: "
          f"{'none' if fc_rank(ex) is None else fc_rank(ex)}")

SKETCH_ROWS = ["Tucker Kraft", "Rome Odunze", "Xavier Legette", "Theo Johnson",
               "Kaelon Black", "Ashton Jeanty", "J.J. McCarthy"]
row_by_name = {}
for r in cohort:
    if name(r) in SKETCH_ROWS:
        if name(r) in row_by_name:
            raise SystemExit(f"FAIL-CLOSED: ambiguous sketch name {name(r)!r}")
        row_by_name[name(r)] = r
print("\nSKETCH ROWS (DG overall + position labels, competition ranking):",
      {n: (overall_label(row_by_name[n]), rank_label(pos(row_by_name[n]), row_by_name[n]))
       for n in SKETCH_ROWS})

# GROUP FACTS (basis RULED 2026-07-12: the governed team_value_matrix definition).
# TWO censuses, both emitted and labeled (r11 #2):
#   DISPLAY census = full-roster valued x/y per position (what group headers show).
#   DEPENDENCY census = the EXACT governed graph (r11 #1): active (not IR/taxi)
#   SKILL_POSITIONS rows only — K/DEF/FB never block — with NUMERIC xVAR consumed
#   regardless of engine route/status (the matrix does not filter on route); a
#   blocker = an active skill row whose xVAR is null/non-numeric, or an active
#   row with unknown position (it MAY be skill). LIMITATION (named): rosters
#   derive from player rows in this artifact — an EMPTY league roster is
#   invisible here; the governed producer iterates the league snapshot's roster
#   list and owns that case.
SKILL = {"QB", "RB", "WR", "TE"}
cohort_ids = {id(r) for r in cohort}
gcount = collections.defaultdict(int)      # display census: model-valued
gtotal = collections.defaultdict(int)      # display census: rostered
dep_bad = collections.defaultdict(int)     # dependency census: active blockers
roster_ids_all = set()
for r in rows:
    lc = r.get("league_context") or {}
    if not isinstance(lc, dict) or not lc.get("rostered") or lc.get("roster_id") is None:
        continue
    rid = lc["roster_id"]
    roster_ids_all.add(rid)
    q = pos(r)
    if q in SKILL:
        gtotal[(rid, q)] += 1
        if id(r) in cohort_ids:
            gcount[(rid, q)] += 1
    if lc.get("on_ir") or lc.get("on_taxi"):
        continue  # outside the governed dependency graph
    if q == "?":
        dep_bad[rid] += 1          # unknown MAY be skill -> fail closed
        continue
    if q not in SKILL:
        continue                   # K/DEF/FB: never a dependency
    v = xvar(r)
    if v is None:
        dep_bad[rid] += 1          # active skill row without numeric xVAR
rosters = sorted(roster_ids_all)
print(f"\nDAVID GROUP FACTS ({len(rosters)} rosters; two censuses, labeled):")
for q in ("QB", "RB", "WR", "TE"):
    opp = [rid for rid in rosters if rid != 1]
    complete_opp = sum(1 for rid in opp if gcount.get((rid, q), 0) == gtotal.get((rid, q), 0))
    print(f"  {q}: DISPLAY valued {gcount.get((1, q), 0)}/{gtotal.get((1, q), 0)} "
          f"| same-position complete OPPONENT groups {complete_opp}/{len(opp)} (receipt fact)")
opp = [rid for rid in rosters if rid != 1]
closure = sum(1 for rid in opp if dep_bad.get(rid, 0) == 0)
me_closed = dep_bad.get(1, 0) == 0
print(f"  DEPENDENCY GATE (exact governed graph: active SKILL rows w/ numeric xVAR; "
      f"K/DEF never block; route/status not filtered; empty-roster case producer-owned): "
      f"{closure}/{len(opp)} opponents closed; David closed: {me_closed} "
      f"(David's active blockers: {dep_bad.get(1, 0)})")

# v3.5 MOVEMENT: latest two history capture days, same-player intersection,
# renderable statuses both days, movement = |display-delta change| >= 1.
HIST = REPO_ROOT / "app/data/market_divergence_history.db"
_reuse = globals().get("_PIN_CONN")
with (_reuse if _reuse is not None else sqlite3.connect(HIST)) as conn:
    # r12-9 + r13-2: one explicit read transaction spans date selection,
    # reconciliation, raw tuples, and payload parsing — and in refless-pin mode
    # it is the SAME transaction that supplied the board rows.
    if _reuse is None:
        conn.execute("BEGIN")
    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT capture_date FROM market_divergence_history ORDER BY capture_date")]
    if AS_OF:
        dates = [x for x in dates if x <= AS_OF]  # the pin bounds the movement pair too
        if len(dates) < 2:
            raise SystemExit(f"FAIL-CLOSED: no movement pair at or before DG_AS_OF {AS_OF!r}")
        if dates[-1] != AS_OF:
            # r9-3: a missing pinned day must never silently slide to older days
            raise SystemExit(f"FAIL-CLOSED: pinned day {AS_OF!r} has no movement capture; "
                             f"latest at-or-before is {dates[-1]!r}")
    if not AS_OF:
        # r12-2 + r13-1: the latest history day must match the live artifact in
        # IDs AND canonical content — a same-size mutated or ID-swapped endpoint
        # must never pass as movement.
        _art = {}
        for _r in rows:
            _sid = _r.get("sleeper_player_id")
            if _sid is not None:
                _art[str(_sid)] = hashlib.sha256(
                    json.dumps(_r, sort_keys=True, default=str).encode()).hexdigest()
        _mismatch = _missing = 0
        _n_hist = 0
        for _sid, _pl in conn.execute(
                "SELECT player_id, payload_json FROM market_divergence_history "
                "WHERE capture_date=?", (dates[-1],)):
            _n_hist += 1
            _hh = hashlib.sha256(json.dumps(
                strict_loads(_pl, "live-reconcile row"), sort_keys=True,
                default=str).encode()).hexdigest()
            _k = str(_sid)
            if _k not in _art:
                _missing += 1
            elif _art[_k] != _hh:
                _mismatch += 1
        if _n_hist != len(_art) or _missing or _mismatch:
            raise SystemExit(
                f"FAIL-CLOSED: latest history day {dates[-1]} does not reconcile with the "
                f"live artifact — {_n_hist} vs {len(_art)} rows, {_missing} unknown ids, "
                f"{_mismatch} content mismatches (mutated or swapped endpoint)")
    if not AS_OF and d.get("market_snapshot_date") != dates[-1]:
        # r10-5: a stale artifact + newer history must never mix dates silently
        raise SystemExit(f"FAIL-CLOSED: artifact day {d.get('market_snapshot_date')!r} != "
                         f"latest history day {dates[-1]!r} — stale artifact or unflushed history")
    d_prev, d_last = dates[-2], dates[-1]
    payloads = {}
    raw_rows = {}
    # r11-8: ONE explicit read transaction; movement payloads are parsed FROM
    # the same raw rows the manifest hashes — a concurrent exact-set replacement
    # can never pair manifest A with payload B.
    for cd in (d_prev, d_last):
        raw_rows[cd] = []
        for r in conn.execute(
                "SELECT player_id, decision_supported, payload_json "
                "FROM market_divergence_history WHERE capture_date=?", (cd,)):
            _pid, _ds = str(r[0]), r[1]
            if not (isinstance(_ds, int) and not isinstance(_ds, bool) and _ds == 0):
                raise SystemExit(f"FAIL-CLOSED: SQL decision_supported={_ds!r} for "
                                 f"{_pid} on {cd} at LOAD TIME (No-Verdict Line)")
            raw_rows[cd].append((_pid, _ds, r[2]))


    def _validate_payload(node, pid, cd):
        # r12-5: EVERY nested decision_supported must be exact JSON false (the
        # 24,402 real sites live under valuation/divergence — a top-level check
        # was insufficient, probe-proven). r12-10: finiteness is validated HERE,
        # before any semantic use of the payload.
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "decision_supported" and v is not False:
                    raise SystemExit(f"FAIL-CLOSED: nested decision_supported="
                                     f"{v!r} for {pid} on {cd} (No-Verdict Line)")
                _validate_payload(v, pid, cd)
        elif isinstance(node, list):
            for v in node:
                _validate_payload(v, pid, cd)
        elif isinstance(node, bool):
            pass
        elif isinstance(node, (float, Decimal, int)):
            bad = (isinstance(node, float) and (node != node or abs(node) == float("inf"))) or \
                  (isinstance(node, Decimal) and not node.is_finite()) or \
                  abs(Decimal(str(node)) if not isinstance(node, Decimal) else node) > NUMERIC_BOUND
            if bad:
                raise SystemExit(f"FAIL-CLOSED: non-finite/unbounded numeric for {pid} on {cd}")

    for cd in (d_prev, d_last):
        payloads[cd] = {}
        for pid, _ds, pj in raw_rows[cd]:
            parsed = strict_loads(pj, f"movement payload {pid}")
            _validate_payload(parsed, pid, cd)
            payloads[cd][pid] = parsed
    conn.execute("COMMIT")
conn.close()


def renderable(p_row):
    return (p_row.get("divergence") or {}).get("signal_status") in BOARD_STATUSES


# Canonical-identity invariants (r10 #3, scoped exactly in r11 #3): the MOVEMENT
# FEED SCOPE is every RENDERABLE pair — for those, dg_player_id must be stable
# across both days and non-empty; empty history keys are rejected everywhere.
# Broader (non-renderable) canonical churn is disclosed, not asserted stable.
for cd in (d_prev, d_last):
    for pid in payloads[cd]:
        if not str(pid).strip():
            raise SystemExit("FAIL-CLOSED: empty history player id")
_dg_churn_all = 0
for pid in set(payloads[d_prev]) & set(payloads[d_last]):
    a, b = payloads[d_prev][pid], payloads[d_last][pid]
    da_, db_ = a.get("dg_player_id"), b.get("dg_player_id")
    if da_ != db_:
        _dg_churn_all += 1
        if renderable(a) and renderable(b):
            raise SystemExit(
                f"FAIL-CLOSED: renderable pair {pid!r} changed dg_player_id {da_!r}->{db_!r}")
        continue
    if renderable(a) and renderable(b) and not (da_ and str(da_).strip()):
        raise SystemExit(f"FAIL-CLOSED: renderable pair {pid!r} lacks a dg_player_id")
print(f"IDENTITY INVARIANTS: renderable pairs dg-id-stable; non-renderable canonical "
      f"churn disclosed: {_dg_churn_all} rows changed dg_player_id across the pair "
      f"(producer-preflight fact, not asserted stable)")

moved_all, moved_mine, eligible_mine = [], [], 0
moved_rostered = moved_fa = 0
mine_2plus = 0
newly_comparable_mine = []
for pid, b in payloads[d_last].items():
    if not renderable(b):
        continue
    lc = b.get("league_context") or {}
    is_mine = isinstance(lc, dict) and lc.get("roster_id") == 1
    a = payloads[d_prev].get(pid)
    if a is None or not renderable(a):
        if is_mine:
            newly_comparable_mine.append((b.get("player") or {}).get("full_name") or pid)
        continue
    da = display_delta(a["divergence"]["model_minus_market_delta"])
    db = display_delta(b["divergence"]["model_minus_market_delta"])
    if is_mine:
        eligible_mine += 1
    if abs(db - da) >= 1:
        moved_all.append(pid)
        if isinstance(lc, dict) and lc.get("rostered"):
            moved_rostered += 1
        else:
            moved_fa += 1
        if is_mine:
            moved_mine.append(pid)
            if abs(db - da) >= 2:
                mine_2plus += 1
# r11-1: hashes ENFORCE, not just report — DG_MOVEMENT_HASHES pins the expected
# manifest ("day:sha256,day:sha256"); any mismatch (mutation, synthetic rows,
# wrong day set) aborts. Full digests; label counts truthfully (row payloads).
_expected = {}
_manifest_raw = os.environ.get("DG_MOVEMENT_HASHES", "")
if _manifest_raw:
    # r14-1: EXACT grammar — exactly two raw tokens, no whitespace tolerance,
    # no empty fields, calendar-valid ISO dates. Anything else aborts.
    import datetime
    _toks = _manifest_raw.split(",")
    if len(_toks) != 2:
        raise SystemExit(f"FAIL-CLOSED: manifest must be exactly two raw "
                         f"day:hash tokens, got {len(_toks)}")
    for _tok in _toks:
        _day_k, _sep, _hex = _tok.partition(":")
        if not _sep or _tok != f"{_day_k}:{_hex}" or _tok.strip() != _tok:
            raise SystemExit(f"FAIL-CLOSED: malformed manifest token {_tok!r}")
        try:
            _parsed = datetime.date.fromisoformat(_day_k)
        except ValueError:
            raise SystemExit(f"FAIL-CLOSED: manifest day {_day_k!r} is not a "
                             "calendar-valid ISO date") from None
        if _parsed.isoformat() != _day_k:
            # r15: fromisoformat also accepts 20260709 / 2026-W28-4 — only the
            # canonical YYYY-MM-DD spelling is legal manifest grammar
            raise SystemExit(f"FAIL-CLOSED: manifest day {_day_k!r} is not "
                             "canonical YYYY-MM-DD")
        if not (len(_hex) == 64 and all(ch in "0123456789abcdef" for ch in _hex)):
            raise SystemExit(f"FAIL-CLOSED: manifest digest for {_day_k!r} is not "
                             "64 lowercase hex chars")
        if _day_k in _expected:
            raise SystemExit(f"FAIL-CLOSED: duplicate manifest key {_day_k!r} — "
                             "last-write-wins would mask a bad digest")
        _expected[_day_k] = _hex
if AS_OF_REF and not _expected:
    # r12-1: ref-pinned evidence is only reproducible WITH the manifest — require it
    raise SystemExit("FAIL-CLOSED: ref-pinned movement requires DG_MOVEMENT_HASHES "
                     "(day:sha256,day:sha256) — without it, history mutation passes silently")
if _expected and set(_expected) != {d_prev, d_last}:
    raise SystemExit(f"FAIL-CLOSED: manifest days {sorted(_expected)} != the selected pair "
                     f"[{d_prev}, {d_last}] — exact two-day set required")
# MANIFEST V3 (r9-7 + r10-6, guard RED): the spec-pinned raw-tuple digest —
# one canonical enclosing JSON array of [player_id, capture_date,
# decision_supported, payload_json-as-stored], sorted by player_id. A column
# flip OR any payload byte change breaks it. Generations V1/V2 are retired;
# their manifests abort loudly by design.
for _day in (d_prev, d_last):
    _tuples = []
    for _pid, _ds, _pl in raw_rows[_day]:
        if not (isinstance(_ds, int) and not isinstance(_ds, bool) and _ds == 0):
            raise SystemExit(f"FAIL-CLOSED: decision_supported={_ds!r} for {_pid} on {_day} "
                             "— the constitutional column must be the exact integer 0")
        _parsed = strict_loads(_pl, f"manifest tuple {_pid}")
        def _walk(v):
            if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
                raise SystemExit(f"FAIL-CLOSED: non-finite value in payload for {_pid}")
            if isinstance(v, dict):
                for x in v.values():
                    _walk(x)
            elif isinstance(v, list):
                for x in v:
                    _walk(x)
        _walk(_parsed)
        _tuples.append([_pid, _day, _ds, _pl])
    _tuples.sort(key=lambda r: r[0])
    _dig = hashlib.sha256(json.dumps(
        _tuples, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    print(f"MOVEMENT-DAY CONTENT HASH {_day}: {_dig} ({len(_tuples)} raw stored tuples)")
    if _expected:
        if _day not in _expected:
            raise SystemExit(f"FAIL-CLOSED: movement day {_day!r} not in the pinned hash manifest")
        if _expected[_day] != _dig:
            raise SystemExit(f"FAIL-CLOSED: movement content hash mismatch for {_day} — "
                             f"expected {_expected[_day][:16]}…, got {_dig[:16]}… (history mutated)")
if _expected:
    print(f"MOVEMENT HASHES VERIFIED: both days match the pinned manifest ({d_prev}, {d_last})")
print(f"\nMOVEMENT ({d_prev} -> {d_last}, same-player renderable intersection, "
      f"|display-delta change| >= 1): board-wide {len(moved_all)} "
      f"({moved_rostered} rostered · {moved_fa} free agents) "
      f"| David {len(moved_mine)} of {eligible_mine} eligible ({mine_2plus} moved 2+)"
      f" | newly comparable on roster: {newly_comparable_mine}")
# History keys are SLEEPER ids (runner stores sleeper_player_id) — map to the
# canonical DG id before the sign-neutral tiebreak (Codex round-4 #1).
sleeper_to_dg = {}
for r in rows:
    sid = r.get("sleeper_player_id")
    if sid is None:
        continue
    if str(sid) in sleeper_to_dg:
        raise SystemExit(f"FAIL-CLOSED: duplicate sleeper id {sid!r}")
    sleeper_to_dg[str(sid)] = r.get("dg_player_id")
mover_rows = []
for pid in moved_mine:
    a, b = payloads[d_prev][pid], payloads[d_last][pid]
    change = (display_delta(b["divergence"]["model_minus_market_delta"])
              - display_delta(a["divergence"]["model_minus_market_delta"]))
    nm = (b.get("player") or {}).get("full_name") or pid
    dg_id = sleeper_to_dg.get(str(pid))
    if not dg_id:
        raise SystemExit(f"FAIL-CLOSED: mover {nm!r} (history id {pid!r}) has no canonical DG id")
    mover_rows.append((-abs(change), dg_id, change, nm, (b.get("player") or {}).get("position")))
# Sign-neutral canonical ordering: |move| desc, then CANONICAL DG id — never sign.
mover_rows.sort()
print("top David movers (sign-neutral canonical-id order):",
      [f"{nm} ({p}, {chg:+d})" for _, _, chg, nm, p in mover_rows[:5]])

# "Model held" and "market-led" are DERIVED, never asserted (Codex r4 #6, r5 #2):
# raw xVAR compared across the pair (all compared + the surfaced roster scope);
# market movement counted the same way; percentile shifts are attributed to
# MODEL-COHORT composition (the producer's _model_cohorts spans all model-backed
# rows, not the board).
xvar_changed = pct_changed = mkt_changed = 0
xvar_changed_mine = mkt_changed_mine = compared_mine = 0
mover_mkt_changed = 0


def payload_model_backed(row):
    v = row.get("valuation") or {}
    return (bool((row.get("player") or {}).get("position"))
            and v.get("xvar") is not None
            and v.get("engine_path") in MODEL_BACKED_ROUTES
            and v.get("valuation_status") in MODEL_BACKED_STATUSES)


for pid in set(payloads[d_prev]) & set(payloads[d_last]):
    a, b = payloads[d_prev][pid], payloads[d_last][pid]
    if not (renderable(a) and renderable(b)):
        continue
    va = (a.get("valuation") or {}).get("xvar")
    vb = (b.get("valuation") or {}).get("xvar")
    lc = b.get("league_context") or {}
    if va != vb:
        xvar_changed += 1
        if isinstance(lc, dict) and lc.get("roster_id") == 1:
            xvar_changed_mine += 1
    if a["divergence"]["model_percentile"] != b["divergence"]["model_percentile"]:
        pct_changed += 1
    ma = (a.get("market_overlay") or {}).get("market_value")
    mb = (b.get("market_overlay") or {}).get("market_value")
    if isinstance(lc, dict) and lc.get("roster_id") == 1:
        compared_mine += 1
        if ma != mb:
            mkt_changed_mine += 1
        if pid in set(moved_mine) and ma != mb:
            mover_mkt_changed += 1
    if ma != mb:
        mkt_changed += 1
coh_prev = sum(1 for r in payloads[d_prev].values() if payload_model_backed(r))
coh_last = sum(1 for r in payloads[d_last].values() if payload_model_backed(r))
prev_ids = {pid for pid, r in payloads[d_prev].items() if payload_model_backed(r)}
last_ids = {pid for pid, r in payloads[d_last].items() if payload_model_backed(r)}
# Attribution guard: verify raw xVAR across ALL common model-backed rows (not
# just the renderable/compared set) before naming cohort composition the cause.
common_mb = prev_ids & last_ids
mb_xvar_changed = sum(
    1 for pid in common_mb
    if (payloads[d_prev][pid].get("valuation") or {}).get("xvar")
    != (payloads[d_last][pid].get("valuation") or {}).get("xvar"))
# Percentiles move PER POSITION — attribute position-cohort membership changes.
def pos_of(row):
    return (row.get("player") or {}).get("position")
pos_prev = collections.Counter(pos_of(payloads[d_prev][pid]) for pid in prev_ids)
pos_last = collections.Counter(pos_of(payloads[d_last][pid]) for pid in last_ids)
ent_by_pos = collections.Counter(pos_of(payloads[d_last][pid]) for pid in last_ids - prev_ids)
ex_by_pos = collections.Counter(pos_of(payloads[d_prev][pid]) for pid in prev_ids - last_ids)
shift_by_pos = collections.Counter()
pos_transitions_all = pos_transitions_mb = 0
for pid in set(payloads[d_prev]) & set(payloads[d_last]):
    a, b = payloads[d_prev][pid], payloads[d_last][pid]
    if pos_of(a) != pos_of(b):
        pos_transitions_all += 1
        if pid in common_mb:
            pos_transitions_mb += 1
    if renderable(a) and renderable(b) and a["divergence"]["model_percentile"] != b["divergence"]["model_percentile"]:
        shift_by_pos[pos_of(b)] += 1
attribution_ok = (mb_xvar_changed == 0 and pos_transitions_mb == 0)
attribution_clause = (
    "attribution VERIFIED: composition-only cause holds"
    if attribution_ok else
    "attribution SUPPRESSED: guards failed — composition-only cause may NOT be claimed")
print(f"MODEL-HELD derivation (per scope): full compared set {xvar_changed} changed -> "
      f"{'HOLDS' if xvar_changed == 0 else 'FAILS'}; David roster {xvar_changed_mine} "
      f"changed -> {'HOLDS' if xvar_changed_mine == 0 else 'FAILS'}. "
      f"MARKET-MOVED derivation (per scope): full set {mkt_changed}; David "
      f"{mkt_changed_mine} of {compared_mine} compared; gap-movers with market change "
      f"{mover_mkt_changed} of {len(moved_mine)}. Percentile shifts: {pct_changed} — "
      f"{attribution_clause}; raw xVAR changed for {mb_xvar_changed} of "
      f"{len(common_mb)} common model-backed rows; PER-POSITION cohort composition "
      f"{ {q: (pos_prev[q], pos_last[q]) for q in ('QB', 'RB', 'WR', 'TE')} } "
      f"entrants {dict(ent_by_pos)} exits {dict(ex_by_pos)} "
      f"renderable shifts by position {dict(shift_by_pos)} "
      f"| common-player position transitions: model-backed {pos_transitions_mb}, all rows {pos_transitions_all} (guarded, never assumed) "
      f"(union {coh_prev}->{coh_last} is context, never the attribution)")

# Off-board roster classification is DATA-BACKED, never asserted (Codex r5 #3):
for r in mine_all:
    if any(x is r for x in mine):
        continue
    v = r.get("valuation") or {}
    if (v.get("engine_path") in MODEL_BACKED_ROUTES
            and v.get("valuation_status") in MODEL_BACKED_STATUSES | {"MODEL_UNCERTAIN"}
            and v.get("xvar") is None):
        cls = "DG read unavailable (model-routed, xVAR null)"
    elif v.get("engine_path") not in MODEL_BACKED_ROUTES:
        cls = f"pre-model / not model-routed ({v.get('engine_path')})"
    else:
        cls = "unclassified (needs producer classifier)"
    mo = r.get("market_overlay") or {}
    print(f"OFF-BOARD {name(r)}: engine_path={v.get('engine_path')} "
          f"status={v.get('valuation_status')} xvar={v.get('xvar')} "
          f"market_rank={mo.get('position_rank')} -> {cls}")

braelon = next((r for r in rows if name(r) == "Braelon Allen"), None)
if braelon is not None:
    mo = braelon.get("market_overlay") or {}
    print(f"BRAELON ALLEN state: model_backed={model_backed(braelon)} "
          f"market_rank={mo.get('position_rank')} (market read "
          f"{'EXISTS' if mo.get('position_rank') is not None else 'absent'}; "
          f"DG read unavailable)")

gp = [r for r in board if div(r).get("signal_status") == "gates_passed"]
hi = sorted([r for r in gp if div(r)["signal"] == "MODEL_HIGH_MARKET_LOW"],
            key=lambda r: -div(r)["model_minus_market_delta"])
lo = sorted([r for r in gp if div(r)["signal"] == "MODEL_LOW_MARKET_HIGH"],
            key=lambda r: div(r)["model_minus_market_delta"])
print("\nUNIVERSE EXTREMES (by |stored percentile delta|, gates_passed only):")
print("  we-see-more:",
      [f"{name(r)} ({pos(r)}, {delta_pts(r)})" for r in hi[:5]])
print("  market-pays-more:",
      [f"{name(r)} ({pos(r)}, {delta_pts(r)})" for r in lo[:5]])

# ---------------------------------------------------------------------------
# V4 GRAMMAR (2026-07-13, post-round-3 audits + Codex frozen-comp verdict).
# Producer-side once: the widened/narrowed mover sentences (audit F P0 + Codex
# persona flag), rank/verdict collision detection (audit E P0, convergent),
# and FA closest-calls distance-below-the-line (both pools; the market-read
# subset SIZE is derived per run — 97 on the pinned 07-11 day). Appended; nothing above changes.
# ---------------------------------------------------------------------------
print("\n=== V4 GRAMMAR ===")
for _, dg_id, chg, nm, p in mover_rows:
    a, b = None, None
    for sid, d in sleeper_to_dg.items():
        if d == dg_id:
            a, b = payloads[d_prev].get(sid), payloads[d_last].get(sid)
            break
    da = display_delta(a["divergence"]["model_minus_market_delta"])
    db = display_delta(b["divergence"]["model_minus_market_delta"])
    ma = (a.get("market_overlay") or {}).get("market_value")
    mb = (b.get("market_overlay") or {}).get("market_value")
    if ma is None or mb is None:
        raise SystemExit(f"FAIL-CLOSED: mover {nm!r} missing market_value pair")
    price = "market price up" if mb > ma else ("market price down" if mb < ma else "market price flat")
    arrow = "▲" if mb > ma else ("▼" if mb < ma else "●")
    # v3.14:429 lead-language rule: name WHOSE lead grew/shrank, never a bare gap verb.
    side = "DG" if db > 0 else "market"
    if (da > 0) != (db > 0) and da != 0 and db != 0:
        gap = (f"the lead crossed sides, a {abs(db-da)}pp move "
               f"({'DG' if da>0 else 'market'} {abs(da)}pp → {side} {abs(db)}pp)")
    elif abs(db) > abs(da):
        gap = f"the {side} lead grew {abs(db)-abs(da)}pp (now {abs(db)}pp)"
    elif abs(db) < abs(da):
        gap = f"the {side} lead shrank {abs(da)-abs(db)}pp (now {abs(db)}pp)"
    else:
        gap = f"the {side} lead held at {abs(db)}pp"
    print(f"  {nm} ({p}): {arrow} {price} ({ma} → {mb}) · {gap}")

# Rank/verdict collisions on David's roster: native positional-rank ordering
# contradicts (or ties against) a non-band signal. DG rank = competition rank
# over the model cohort; market rank = FantasyCalc NATIVE label (different
# pools — which is exactly why the on-row juxtaposition can lie; audit E P0,
# Codex first-time-manager persona, convergent).
print("\nRANK/VERDICT COLLISIONS (David roster, gates_passed rows w/ both ranks):")
ncoll = 0
for r in board:
    lc = r.get("league_context") or {}
    if not (isinstance(lc, dict) and lc.get("roster_id") == 1):
        continue
    sig = div(r).get("signal")
    if sig not in ("MODEL_HIGH_MARKET_LOW", "MODEL_LOW_MARKET_HIGH"):
        continue
    dgr = dg_pos_rank.get(canon_id(r))
    mkr = fc_rank(r)
    if dgr is None or mkr is None:
        continue
    dd = display_delta(div(r)["model_minus_market_delta"])
    if (dd > 0 and dgr >= mkr) or (dd < 0 and dgr <= mkr):
        ncoll += 1
        print(f"  {name(r)} ({pos(r)}): DG {pos(r)}{dgr} · Mkt {pos(r)}{mkr} vs "
              f"'{sig_display[sig]} · {abs(dd)}pp'  -> pools-differ annotation, BOTH labels kept (Codex r2-4)")
if ncoll == 0:
    print("  none on the current pair")

# FA nearest-to-the-line distances (fail-closed): the replacement line is
# xVAR 0 by construction; distance below = |xVAR|. Renders as "N.N under the
# line" on the closest-call rows (Codex r2 acceptance item 2).
fa_by_xvar = sorted(fa_pool, key=lambda r: (-xvar(r), canon_id(r)))
nearest = fa_by_xvar[:2]
for r in nearest:
    if xvar(r) is None or xvar(r) >= 0:
        raise SystemExit(f"FAIL-CLOSED: FA nearest-to-line {name(r)!r} has xVAR {xvar(r)!r}"
                         " (None or above the line) — the all-below-replacement claim breaks")
print("\nFA NEAREST TO THE LINE (by xVAR, fail-closed):",
      [f"{name(r)} ({pos(r)}, {abs(xvar(r)):.1f} under the line)" for r in nearest])

# Same derivation for the MARKET-READ subset (size derived per run): the
# Allen/Hunt 2.0/3.5 claim renders in that toggle state and must fail-close too.
fa_board_by_xvar = sorted(fa, key=lambda r: (-xvar(r), canon_id(r)))
nearest_board = fa_board_by_xvar[:2]
for r in nearest_board:
    if xvar(r) is None or xvar(r) >= 0:
        raise SystemExit(f"FAIL-CLOSED: market-read FA nearest {name(r)!r} has xVAR {xvar(r)!r}")
print(f"FA NEAREST (market-read {len(fa)} subset, fail-closed):",
      [f"{name(r)} ({pos(r)}, {abs(xvar(r)):.1f} under the line)" for r in nearest_board])

