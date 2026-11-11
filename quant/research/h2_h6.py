import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats; from research.engine import load, dsr
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); NT = 40
COST = {"SPY": 2, "QQQ": 2, "IWM": 3}
def legs(sym):
    d = load(sym)["2000":]; on = d.o.shift(-1)/d.c - 1; cc = d.c.pct_change(); gap = d.o/d.c.shift(1) - 1; intra = d.c/d.o - 1
    return pd.DataFrame({"on": on, "cc": cc, "gap": gap, "intra": intra}).dropna()
def g(t, base, label):
    t = t.dropna(); ex = t - base
    w, l = t[t > 0], t[t <= 0]; day = ex.groupby(level=0).mean(); wk = ex.groupby(ex.index.get_level_values(0).to_period("W")).mean()
    return dict(name=label, n=len(t), win=round((t > 0).mean(), 3), exp_bps=round(t.mean()*1e4, 1), base_bps=round(np.mean(base)*1e4, 1),
                excess_bps=round(ex.mean()*1e4, 1), t_clust=round(stats.ttest_1samp(wk, 0).statistic, 2),
                payoff=round(w.mean()/abs(l.mean()), 2), be_win=round(abs(l.mean())/(w.mean()+abs(l.mean())), 3),
                worst=round(t.min(), 4), cvar5=round(t[t <= t.quantile(.05)].mean(), 4), worst_x_mean=round(abs(t.min())/t.mean(), 1) if t.mean() > 0 else np.inf,
                dsr=round(dsr(t.mean()/t.std()*np.sqrt(252), len(t), stats.skew(t), stats.kurtosis(t, fisher=False), NT), 3))
def pool(kind, x, sl, cmult=1.0, syms=("SPY","QQQ","IWM"), side=-1):
    T, B = [], []
    for s in syms:
        L = legs(s)[sl]; c = 2*COST[s]*cmult/1e4
        if kind == "H2": m = (L.cc < -x) if side < 0 else (L.cc > x); r = L.on[m] - c; base = L.on.mean() - c
        else: m = L.gap < -x; r = L.intra[m] - c; base = L.intra.mean() - c
        T.append(r.rename(s)); B += [base]*int(m.sum())
    t = pd.concat(T).sort_index(); return t, np.array(B)
P = lambda rows: print(pd.DataFrame(rows).to_string(index=False))
D, O = slice("2000","2012"), slice("2013", None)
print("=== H2 overnight after down day (buy MOC, sell MOO) ===")
rows = []
for x in (0.01, 0.015, 0.02):
    for lab, sl in (("disc", D), ("OOS", O)):
        t, b = pool("H2", x, sl); rows.append(g(t, b, f"x{x} {lab}"))
P(rows)
print("\nH2 cost stress OOS 5bp/side (x2.5 SPY/QQQ):"); P([g(*pool("H2", x, O, 2.5), f"x{x} 5bp") for x in (0.01, 0.015, 0.02)])
print("\nH2 per instrument OOS:"); P([g(*pool("H2", x, O, syms=(s,)), f"{s} x{x}") for s in ("SPY","QQQ","IWM") for x in (0.01, 0.015, 0.02)])
print("\nH2 by era (x1%): "); P([g(*pool("H2", 0.01, slice(a,b)), f"{a}-{b}") for a,b in (("2000","2006"),("2007","2012"),("2013","2018"),("2019","2022"),("2023","2026"))])
print("\nMechanism check: overnight after UP days > x (expect below base):"); P([g(*pool("H2", x, O, side=1), f"up x{x} OOS") for x in (0.01, 0.015, 0.02)])
print("\nBreadth outside pre-reg (DIA, EFA, XLK, XLF; OOS x1%) — information only:")
for s in ("DIA","XLK","XLF","EFA"): COST[s] = 3
P([g(*pool("H2", 0.01, O, syms=(s,)), s) for s in ("DIA","XLK","XLF","EFA")])
print("\n=== H6 gap-down fade (buy open, sell close) ===")
rows = []
for x in (0.005, 0.01):
    for lab, sl in (("disc", D), ("OOS", O)):
        t, b = pool("H6", x, sl); rows.append(g(t, b, f"g{x} {lab}"))
P(rows)
