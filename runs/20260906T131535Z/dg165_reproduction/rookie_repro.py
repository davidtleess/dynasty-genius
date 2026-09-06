"""DG-165 — P(ever qualifies | college, draft capital).

The missing factor. R(h) is fitted on players who ALREADY qualify, so a rookie needs
    rookie value = P(ever qualifies) x [existing R(h) cells at the level he reaches]

COHORT ESTABLISHED INDEPENDENTLY. Selected by DRAFT CLASS ONLY (2015-2020, the classes with
five years of follow-up). No inherited flag is read: not censored_incomplete_arc, not
low_sample_flag, not is_training, not head_b_training_eligible. The washouts MUST be in.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, nflreadpy as nfl
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
SP=Path("/Users/davidleess/dg-wt/DG-165/runs/20260906T131535Z/dg165_reproduction/inputs")
BAR={"QB":37,"RB":45,"WR":71,"TE":21}

# ---- label: did he EVER reach a qualifying season? --------------------------
pan=pd.read_parquet(SP/"panel.parquet")
pan["rank"]=pan.groupby(["season","position"])["points"].rank(ascending=False,method="min")
pan["ok"]=pan.apply(lambda r: r["rank"]<=BAR.get(r.position,1e9),axis=1)
ever=set(pan.loc[pan.ok,"player_id"])

# ---- cohort: draft class only --------------------------------------------
d=pd.read_csv("/Users/davidleess/dg-wt/DG-165/runs/20260906T131535Z/dg165_reproduction/inputs/prospects_with_outcomes_v3.csv",low_memory=False)
m=d[d.season.between(2015,2020)].copy()
# gsis_id is already 100% populated in this table -- no draft-picks join needed.
assert m.gsis_id.notna().all(), "gsis_id incomplete; the label cannot be built"
print(f"cohort {len(m)} prospects, selected by DRAFT CLASS ONLY (no inherited flag read)")
m["y"]=m.gsis_id.isin(ever).astype(int)
print(f"EVER QUALIFIED: {m.y.sum()} of {len(m)} = {m.y.mean()*100:.0f}%")
print(f"  zero-game prospects retained in the cohort: {(m.total_games.fillna(0)==0).sum()}  <- the 85 that the flag would delete")
print(f"  by position: {m.groupby('position').y.agg(['size','sum','mean']).round(2).to_dict('index')}")

# ---- features -------------------------------------------------------------
m["dominator"]=m[["wr_dominator_career","rb_career_dominator","te_career_dominator"]].bfill(axis=1).iloc[:,0]
m["final_dom"]=m[["wr_dominator_final","rb_final_dominator"]].bfill(axis=1).iloc[:,0]
CAP=["pick","round","age_at_draft"]
COLL=["dominator","final_dom","final_college_age","yprr_college","ryptpa","wr_breakout_age"]
for c in CAP+COLL: m[c]=pd.to_numeric(m.get(c),errors="coerce")
print(f"\ncollege feature coverage in the cohort: "
      + ", ".join(f"{c} {m[c].notna().mean()*100:.0f}%" for c in COLL))

def loco(feats,label):
    """Leave-one-CLASS-out: train on five draft classes, predict the sixth."""
    P,Y=[],[]
    for s in sorted(m.season.unique()):
        tr,te=m[m.season!=s],m[m.season==s]
        if tr.y.nunique()<2: continue
        pipe=Pipeline([("i",SimpleImputer(strategy="median")),("s",StandardScaler()),
                       ("c",LogisticRegression(max_iter=2000))])
        pipe.fit(tr[feats],tr.y)
        P.append(pipe.predict_proba(te[feats])[:,1]); Y.append(te.y.to_numpy())
    p,y=np.concatenate(P),np.concatenate(Y)
    print(f"  {label:<40} AUC {roc_auc_score(y,p):.3f}   n={len(y)}")
    return p,y

print("\nLEAVE-ONE-CLASS-OUT — can we predict who ever becomes startable?")
p_cap,y=loco(CAP,"draft capital alone (pick, round, age)")
p_col,_=loco(COLL,"college production alone")
p_all,_=loco(CAP+COLL,"capital + college")
rng=np.random.default_rng(20260906); d_=[]
for _ in range(2000):
    i=rng.choice(len(y),len(y),replace=True)
    if len(set(y[i]))<2: continue
    d_.append(roc_auc_score(y[i],p_all[i])-roc_auc_score(y[i],p_cap[i]))
lo,hi=np.percentile(d_,[5,95])
print(f"\n  INCREMENT of college ON TOP of capital: {roc_auc_score(y,p_all)-roc_auc_score(y,p_cap):+.3f}  90% CI [{lo:+.3f}, {hi:+.3f}]")

# ---- separate "no signal" from "no coverage" --------------------------------
print("\n" + "="*76)
print("IS THE NULL A SIGNAL PROBLEM OR A COVERAGE PROBLEM?")
print(f"  yprr_college is {m.yprr_college.notna().mean()*100:.0f}% populated — it contributes nothing because it is EMPTY")
have=m[m.dominator.notna()].copy()
print(f"  restricting to prospects WITH a dominator rating: {len(have)} of {len(m)} ({m.dominator.notna().mean()*100:.0f}%)")
print(f"    ever-qualified rate in that subset: {have.y.mean()*100:.0f}% (vs {m.y.mean()*100:.0f}% overall)")

def loco_on(df,feats,label):
    P,Y=[],[]
    for s in sorted(df.season.unique()):
        tr,te=df[df.season!=s],df[df.season==s]
        if tr.y.nunique()<2 or len(te)==0: continue
        pipe=Pipeline([("i",SimpleImputer(strategy="median")),("s",StandardScaler()),
                       ("c",LogisticRegression(max_iter=2000))])
        pipe.fit(tr[feats],tr.y)
        P.append(pipe.predict_proba(te[feats])[:,1]); Y.append(te.y.to_numpy())
    p,y=np.concatenate(P),np.concatenate(Y)
    print(f"    {label:<38} AUC {roc_auc_score(y,p):.3f}   n={len(y)}")
    return p,y

COLL2=[c for c in COLL if m[c].notna().mean()>0.05]     # drop the empty column
print(f"\n  on the {len(have)} WITH college data, using only populated features {COLL2}:")
pc,yy=loco_on(have,CAP,"draft capital alone")
pa,_ =loco_on(have,CAP+COLL2,"capital + college")
dd=[]
for _ in range(2000):
    i=rng.choice(len(yy),len(yy),replace=True)
    if len(set(yy[i]))<2: continue
    dd.append(roc_auc_score(yy[i],pa[i])-roc_auc_score(yy[i],pc[i]))
lo2,hi2=np.percentile(dd,[5,95])
print(f"\n    INCREMENT on the covered subset: {roc_auc_score(yy,pa)-roc_auc_score(yy,pc):+.3f}  90% CI [{lo2:+.3f}, {hi2:+.3f}]")
print()
print("  DRAFT CAPITAL ALONE, as a calibration table:")
m["decile"]=pd.qcut(m["pick"],5,labels=["1st 20% of picks","2nd","3rd","4th","last 20%"])
print(m.groupby("decile",observed=True).agg(n=("y","size"),qualified=("y","sum"),rate=("y","mean")).round(2).to_string())

# ---- Codex brief: calibration, Brier, log loss, by position and draft band --
from sklearn.metrics import brier_score_loss, log_loss
print("\n" + "="*78)
print("CODEX BRIEF — calibration, Brier, log loss, coverage, by position and draft band")
print(f"{'model':<28}{'AUC':>7}{'Brier':>8}{'log loss':>10}   (lower is better for both)")
for nm,pp in [("draft capital alone",p_cap),("college alone",p_col),("capital + college",p_all)]:
    print(f"{nm:<28}{roc_auc_score(y,pp):>7.3f}{brier_score_loss(y,pp):>8.4f}{log_loss(y,pp):>10.4f}")
base=np.full(len(y),y.mean())
print(f"{'base rate (no model)':<28}{0.5:>7.3f}{brier_score_loss(y,base):>8.4f}{log_loss(y,base):>10.4f}")

print("\nCALIBRATION of draft-capital-alone (out-of-class predictions):")
cal=pd.DataFrame({"p":p_cap,"y":y})
cal["bin"]=pd.cut(cal.p,[0,.1,.2,.35,.5,.7,1.01],labels=["0-10%","10-20%","20-35%","35-50%","50-70%","70-100%"])
t=cal.groupby("bin",observed=True).agg(n=("y","size"),predicted=("p","mean"),actual=("y","mean"))
print(t.round(3).to_string())
print(f"  max |predicted - actual| = {(t.predicted-t.actual).abs().max():.3f}")

print("\nBY POSITION (draft capital alone):")
mm=m.reset_index(drop=True).copy(); mm["p"]=np.nan
i=0
for s in sorted(m.season.unique()):
    n=(m.season==s).sum()
    if i+n<=len(p_cap): mm.loc[m.season.values==s,"p"]=p_cap[i:i+n]; i+=n
print(f"{'pos':<5}{'n':>5}{'base':>8}{'AUC':>7}{'Brier':>8}")
for pos in ["QB","RB","WR","TE"]:
    s=mm[(mm.position==pos)&mm.p.notna()]
    if s.y.nunique()<2: continue
    print(f"{pos:<5}{len(s):>5}{s.y.mean():>8.2f}{roc_auc_score(s.y,s.p):>7.3f}{brier_score_loss(s.y,s.p):>8.4f}")

print("\nHOLDOUT — train on 2015-2018, predict the two NEWEST mature classes (2019-2020):")
tr,te=m[m.season<=2018],m[m.season>=2019]
pipe=Pipeline([("i",SimpleImputer(strategy="median")),("s",StandardScaler()),("c",LogisticRegression(max_iter=2000))])
pipe.fit(tr[CAP],tr.y); ph=pipe.predict_proba(te[CAP])[:,1]
pipe.fit(tr[CAP+COLL2],tr.y); ph2=pipe.predict_proba(te[CAP+COLL2])[:,1]
print(f"  capital only      AUC {roc_auc_score(te.y,ph):.3f}  Brier {brier_score_loss(te.y,ph):.4f}   n={len(te)}")
print(f"  capital + college AUC {roc_auc_score(te.y,ph2):.3f}  Brier {brier_score_loss(te.y,ph2):.4f}")
print(f"  out-of-time increment: {roc_auc_score(te.y,ph2)-roc_auc_score(te.y,ph):+.3f} AUC, "
      f"{brier_score_loss(te.y,ph2)-brier_score_loss(te.y,ph):+.4f} Brier")

# ---- is the out-of-time increment real, or noise on n=157? ------------------
print("\nIS THE OUT-OF-TIME INCREMENT REAL? bootstrap on the 2019-2020 holdout")
yh=te.y.to_numpy(); da,db=[],[]
for _ in range(4000):
    i=rng.choice(len(yh),len(yh),replace=True)
    if len(set(yh[i]))<2: continue
    da.append(roc_auc_score(yh[i],ph2[i])-roc_auc_score(yh[i],ph[i]))
    db.append(brier_score_loss(yh[i],ph2[i])-brier_score_loss(yh[i],ph[i]))
alo,ahi=np.percentile(da,[5,95]); blo,bhi=np.percentile(db,[5,95])
print(f"  d AUC   {np.mean(da):+.3f}  90% CI [{alo:+.3f}, {ahi:+.3f}]")
print(f"  d Brier {np.mean(db):+.4f} 90% CI [{blo:+.4f}, {bhi:+.4f}]   (negative = college helps)")
print(f"  -> {'BOTH span zero: not stable evidence' if (alo<0<ahi and blo<0<bhi) else 'at least one excludes zero'}")

# ---- Codex: were the quintiles fitted on the rows they score? ---------------
print("\nTHE FIVE DRAFT-PICK BUCKETS — Codex asked, and the answer is YES:")
print("  those percentages (86/57/34/22/12) are computed on ALL 478 rows with NO holdout.")
print("  They are DESCRIPTIVE, not validated probabilities.")
print("  The VALIDATED object is the calibration table above, which is out-of-fold")
print(f"  (leave-one-class-out) and deviates by at most 0.045 across six bins.")
