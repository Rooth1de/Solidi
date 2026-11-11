import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd; from scipy import stats
from research.engine import dsr, log; from calib.pipeline import *
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); NT = 46; COST_BP = 6.0
def brier(P, y): return ((P - np.eye(3)[y])**2).sum(1).mean()
def auc(s, yb):
    r = stats.rankdata(s); n1 = yb.sum(); n0 = len(yb) - n1; return (r[yb].sum() - n1*(n1+1)/2)/(n1*n0)
def book(D, k_tp, min_ev=0.05, cost_mult=1.0, H=5, maxpos=5, risk=0.005):
    D = D[D.y >= 0].copy(); rr = k_tp; D["cost_r"] = COST_BP*cost_mult/D.slbp
    D["ev"] = D.p0*rr - D.p1 - D.cost_r; D["Rnet"] = D.R - D.cost_r
    cand = D[D.ev >= min_ev].sort_values("ev", ascending=False).sort_index(kind="stable")
    open_until = {}; taken = []; eq = 1.0; daily = {}
    for dt, g in cand.groupby(level=0):
        if daily.get("block") == dt: continue
        open_until = {s: u for s, u in open_until.items() if u > dt}
        for _, r in g.sort_values("ev", ascending=False).iterrows():
            if len(open_until) >= maxpos or r.sym in open_until: continue
            open_until[r.sym] = r.done; taken.append((dt, r.sym, r.ev, r.Rnet, r.y))
    T = pd.DataFrame(taken, columns=["dt","sym","ev","R","y"]).set_index("dt")
    return D, T
def report(D, T, label):
    yb = D.y.astype(int).values; P = D[["p0","p1","p2"]].values; M = D[["m0","m1","m2"]].values; B = D[["b0","b1","b2"]].values
    bs_p, bs_b, bs_m = brier(P, yb), brier(B, yb), brier(M, yb)
    if len(T) < 5: return dict(name=label, n=len(T), skill_cal=round(1-bs_p/bs_b, 4))
    wk = T.R.groupby(T.index.to_period("W")).mean()
    eqR = T.R*0.5  # % equity per trade at 0.5% risk
    return dict(name=label, n=len(T), win=round((T.R > 0).mean(), 3), meanR=round(T.R.mean(), 3), t_clust=round(stats.ttest_1samp(wk, 0).statistic, 2),
                worstR=round(T.R.min(), 2), cvar5R=round(T.R[T.R <= T.R.quantile(.05)].mean(), 2),
                skill_model=round(1-bs_m/bs_b, 4), skill_cal=round(1-bs_p/bs_b, 4), auc_tgt=round(auc(D.p0.values, yb == 0), 3),
                w_mean=round(D.w.mean(), 2), ann_pct=round(eqR.groupby(T.index.year).sum().mean(), 2),
                dsr=round(dsr(T.R.mean()/T.R.std()*np.sqrt(len(T)/(len(D)/15/252)), len(T), stats.skew(T.R), stats.kurtosis(T.R, fisher=False), NT), 3))
P = lambda rows: print(pd.DataFrame(rows).to_string(index=False))
rows = []; keep = {}
for k_tp, H in ((0.5, 5), (0.5, 10), (1.0, 5)):
    D = walk_forward(build(k_tp, H)); keep[(k_tp, H)] = D
    Dl, T = book(D, k_tp, H=H)
    rows.append(report(Dl, T, f"k{k_tp} H{H} 2005-26"))
    for a, b in (("2005","2015"), ("2016","2026")): rows.append(report(Dl[a:b], T[a:b], f"   {a}-{b}"))
    Dl2, T2 = book(D, k_tp, cost_mult=2, H=H); rows.append(report(Dl2, T2, f"   cost x2"))
P(rows)
for (k_tp, H), D in keep.items():
    Dl = D[D.y >= 0].copy(); Dl["ev"] = Dl.p0*k_tp - Dl.p1 - COST_BP/Dl.slbp; Dl["Rnet"] = Dl.R - COST_BP/Dl.slbp
    Dl["bk"] = pd.qcut(Dl.ev, 10, labels=False, duplicates="drop")
    tb = Dl.groupby("bk").agg(ev=("ev","mean"), realR=("Rnet","mean"), win=("Rnet", lambda x: (x>0).mean()), p_tgt=("p0","mean"), hit_tgt=("y", lambda x: (x==0).mean()), n=("ev","size"))
    print(f"\nEV-decile table k{k_tp} H{H} (all OOS decisions, traded or not). Spearman(EV, realised R) = {stats.spearmanr(Dl.ev, Dl.Rnet)[0]:.3f}")
    print(tb.round(3).T.to_string())
