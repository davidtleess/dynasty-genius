"""Rebuilt after the PARTIAL reproduction. Four fixes, each addressing a named defect.

1. INVARIANT counts the PRE-FILTER universe. Every skill row in the artifact gets a row
   out, so a player without a score is a stated blank rather than an absence.
2. ZERO FLOOR on served value against the bar's served value — not a rate margin. The
   input file's own WARNING_zero_floor says the rate test is wrong.
3. NO h=0 AVAILABILITY TERM. That was my unilateral deviation from the spec, and it was
   computed from served/proj which is not P(plays) on a clamped row. Reverted to the
   published form. Availability now enters once, inside `served`.
4. LIMIT TEST REPLACED with one that can fail.
"""
import json, random
from pathlib import Path
random.seed(3)
D="/private/tmp/claude-501/-Users-davidleess/a4d5049a-c405-4f8e-962a-cb0817a24bfd/scratchpad"
R=json.load(open(f"{D}/retention_R_v3.json")); Rc,Rs=R["cells"],R["suppressed"]
INF=float("inf")
lo_=lambda c: -INF if c.get("edge_lo") is None else c["edge_lo"]
hi_=lambda c:  INF if c.get("edge_hi") is None else c["edge_hi"]
key=lambda c:(c["position"],c["ageband"],c["margin_bin"])
Rby={key(c):c for c in Rc}
bins=[(key(c),lo_(c),hi_(c),True) for c in Rc]+[(key(c),lo_(c),hi_(c),False) for c in Rs]

art=json.loads(Path("app/data/valuation_runtime/universe_pvo_runtime.json").read_text())
lg =json.loads(Path("app/data/league_runtime/runs/league-20260904T130046Z/snapshot.json").read_text())
P90_B={"QB":20.1,"RB":15.7,"WR":14.5,"TE":9.4}; P90_A={"QB":16.7,"RB":14.6,"WR":12.7,"TE":9.1}
SKILL={"QB","RB","WR","TE"}

universe=[]                     # EVERY skill row, scored or not
for p in art["players"]:
    pos=(p["player"].get("position") or "").upper()
    if pos not in SKILL: continue
    v=p["valuation"]; dvs=v.get("dynasty_value_score")
    p90=v.get("dvs_p90_ref") or (P90_A if p.get("dvs_engine")=="A" else P90_B)[pos]
    universe.append({"name":p["player"]["full_name"],"pos":pos,"age":p["player"].get("age"),
        "sid":str(p.get("sleeper_player_id")),"proj":p.get("projection_2y"),
        "served":(dvs/100.0*p90 if dvs is not None else None),
        "clamped":bool(v.get("dvs_clamped"))})
print(f"  universe: {len(universe)} skill rows in the artifact "
      f"({sum(1 for x in universe if x['served'] is not None)} scored)")

sids={x["sid"] for x in universe}
mine={str(pid) for r in lg["rosters"] if r.get("roster_id")==lg["david_roster_id"]
      for pid in (r.get("players") or [])}
rost={str(pid) for r in lg["rosters"] for pid in (r.get("players") or [])}
BARs={}; BARp={}
for pos in SKILL:
    free=[x for x in universe if x["pos"]==pos and x["sid"] not in rost
          and x["served"] is not None and x["proj"]]
    b=max(free,key=lambda x:x["served"]); BARs[pos]=b["served"]; BARp[pos]=b["proj"]
print("  bar served: "+"  ".join(f"{p} {BARs[p]:.2f}" for p in ("QB","RB","WR","TE")))

def bandof(a):
    a=float(a); return "<=23" if a<=23 else "24-25" if a<=25 else "26-27" if a<=27 else \
        "28-29" if a<=29 else "30-31" if a<=31 else "32+"
def build(x):
    if x["served"] is None: return None,"no model score in the artifact"
    if x["proj"] is None:   return None,"no projection (no NFL season)"
    if x["age"] is None:    return None,"age unknown"
    m=x["proj"]/BARp[x["pos"]]; b=bandof(x["age"])
    hit=[(k,pub) for k,lo,hi,pub in bins if k[0]==x["pos"] and k[1]==b and lo<=m<hi]
    if len(hit)!=1: return None,f"margin {m:.2f} matched {len(hit)} bins"
    k,pub=hit[0]
    if not pub: return None,f"{k[2]} suppressed"
    return Rby[k],None
def V(x,c,d=1.0):
    if c is None: return None
    A=x["served"]-BARs[x["pos"]]          # served on BOTH sides; availability inside once
    if A<=0: return 0.0
    # David ruled 2026-09-05: this season counts, at full weight. R(0)=1.0 by the cell
    # file's own definition; availability is already inside `served` and must not enter twice.
    return A*(1.0 + sum(d**h*c[f"R{h}"] for h in range(1,6)))

rows=[]
for x in universe:
    c,why=build(x); rows.append({**x,"cell":c,"why":why,"V":V(x,c),
                                 "A":(x["served"]-BARs[x["pos"]]) if x["served"] is not None else None})
assert len(rows)==len(universe), "rows out != universe in"

# --- the two warnings Bob wrote in prose, as assertions that can fail here ---
# 1. ZERO FLOOR consistency: a zero must mean below the bar on the SAME quantity the
#    value uses. Fires if the floor test and the value ever diverge again.
bad=[r for r in rows if r["V"]==0 and r["served"] is not None
     and r["served"] > BARs[r["pos"]] + 1e-9]
assert not bad, f"ZERO FLOOR: {len(bad)} players above the bar were zeroed, e.g. {bad[0]['name']}"
bad2=[r for r in rows if r["V"] is not None and r["V"]>0 and r["served"] <= BARs[r["pos"]]]
assert not bad2, f"ZERO FLOOR: {len(bad2)} players at/below the bar got a positive value"
print(f"  ASSERT zero-floor consistent with the value quantity — holds")

# 2. NO DOUBLE COUNT: survival must not enter V. Perturb S in a copy of every cell and
#    require V to be unchanged. Fires the moment anything multiplies R by S again.
import copy
probe=[r for r in rows if r["cell"]][:200]
moved=0
for r in probe:
    c2=copy.deepcopy(r["cell"])
    for h in range(1,6):
        if f"S{h}" in c2: c2[f"S{h}"] = c2[f"S{h}"]*0.5 + 0.01
    if V(r,c2) != V(r,r["cell"]): moved+=1
assert moved==0, f"DOUBLE COUNT: survival changed V for {moved} players"
print(f"  ASSERT survival does not enter V (perturbed S on {len(probe)} players) — holds")
print(f"  INVARIANT vs PRE-FILTER universe: {len(universe)} in / {len(rows)} out — holds")
priced=[r for r in rows if r["V"] is not None]
print(f"  priced {len(priced)} ({sum(1 for r in priced if r['V']==0)} at zero), blank {len(rows)-len(priced)}")
his=[r for r in rows if r["sid"] in mine]
print(f"  HIS LEAGUE ({len(his)} rostered rows): zero {sum(1 for r in his if r['V']==0)}, "
      f"blank {sum(1 for r in his if r['V'] is None)}, positive {sum(1 for r in his if r['V'] and r['V']>0)}")
json.dump([{k:v for k,v in r.items() if k!='cell'} for r in rows],open("/tmp/v2_rows.json","w"))
top=sorted(priced,key=lambda r:-r["V"])[:20]
print("\n  TOP 20:")
for i,r in enumerate(top,1):
    print(f"   {i:2d}  {r['name'][:24]:24} {r['pos']} {str(r['age']):>4}"
          + ("   [clamped — value is a lower bound]" if r["clamped"] else ""))
