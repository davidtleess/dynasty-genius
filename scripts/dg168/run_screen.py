import json, sys
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,".")
from scripts.dg168.dominance_screen import market_price, find_contradictions, LEAGUE_TRANSLATION
board={r["name"]:r for r in json.load(open("docs/asset-number/board_2026-09-05T1300Z.json"))}
# ⛔ READ THE LIVE FILE, NOT THE WORKTREE COPY. dg-work.sh materialises tracked paths
# from git, and app/data/valuation IS tracked — so a worktree holds the COMMITTED
# market file (2026-07-22) while the daily refresh writes the live one in the trunk
# tree (2026-09-05). Both exist at the same relative path. Measured: 28.2 MB against
# 29.7 MB, six weeks apart, and nothing on the path distinguishes them.
MARKET = Path("/Users/davidleess/dynasty-genius-product/app/data/valuation/"
              "universe_market_divergence_latest.json")
_m = json.load(open(MARKET))
print(f"  market snapshot {_m.get('market_snapshot_date')}  captured {_m.get('captured_at')}")
mk=_m["players"]
players=[]
for row in mk:
    nm=(row.get("player") or {}).get("full_name"); mp=market_price(row)
    b=board.get(nm)
    if mp is None or not b or b.get("V") is None or not b.get("A"): continue
    players.append({"name":nm,"pos":((row.get("player") or {}).get("position") or "").upper(),
        "market":mp,"production":b["A"],"career":b["V"]/b["A"],
        "age":(row.get("player") or {}).get("age")})
pairs=find_contradictions(players)
beaten=defaultdict(list); beats=defaultdict(list)
for p in pairs:
    beaten[p["worse"]["name"]].append(p["better"]); beats[p["better"]["name"]].append(p["worse"])
print(f"  priced by both: {len(players)}")
print(f"  contradictions surviving the format translation: {len(pairs)} pairs, "
      f"{len(beaten)} overpaid / {len(beats)} underpaid\n")
print("  THE MARKET OVERPAYS:\n")
for nm,by in sorted(beaten.items(),key=lambda kv:-len(kv[1]))[:5]:
    me=next(p for p in players if p["name"]==nm)
    ex=sorted(by,key=lambda x:-x["production"])[:3]
    print(f"   {nm} ({me['pos']}, {me['age']:.0f}) — the market prices him like {len(by)} "
          f"players who all produce more AND last longer.")
    print(f"      {', '.join(x['name'] for x in ex)}\n")
print("  THE MARKET UNDERPAYS:\n")
for nm,ov in sorted(beats.items(),key=lambda kv:-len(kv[1]))[:5]:
    me=next(p for p in players if p["name"]==nm)
    print(f"   {nm} ({me['pos']}, {me['age']:.0f}) — beats {len(ov)} players priced the same, on both axes")
from collections import Counter
print(f"\n  overpaid by position: {dict(Counter(next(p for p in players if p['name']==n)['pos'] for n in beaten))}")
