"""R2 multi-decade proxy for E8: index-level LETF close pressure (H2 mechanism) replayed day by day, 2006-2026."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from research.engine import load; from timemachine.core import Run, trades_with_regime
F = {s: load(s) for s in ("SPY", "QQQ", "SSO", "QLD")}; FIRST = {"SPY": F["SSO"].index[0], "QQQ": F["QLD"].index[0]}
class H2:
    def scan(self, v, d):
        out = []
        for s in ("SPY", "QQQ"):
            if d < FIRST[s]: continue
            h = v.hist(s, 2)
            if len(h) < 2 or h.index[-1] != d: continue
            r = h.c.iloc[-1]/h.c.iloc[-2] - 1; out.append(dict(sym=s, day_ret=round(r, 4), signal=int(r < -0.01)))
        return out
    def decide(self, rows, st, d): return {r["sym"]: "TRADE" if r["signal"] else "" for r in rows}
    def execute(self, t, F_, d):
        s = F_[t["sym"]]; i = s.index.get_loc(d)
        if i + 1 >= len(s): return None
        g = s.o.iloc[i+1]/s.c.iloc[i] - 1; c = 4/1e4
        return dict(side=1, entry=str(d.date()), exit=str(s.index[i+1].date()), gross=g, cost=c, net=g - c)
dates = F["SPY"]["2006-06-21":].index
print(Run("R2proxy_H2_index", F, H2(), dates).go())
T = trades_with_regime("R2proxy_H2_index")
# unconditional overnight return per regime (benchmark) to isolate the conditional effect
spy = F["SPY"]; base = (spy.o.shift(-1)/spy.c - 1)
import sqlite3; from timemachine.core import DB
rg = pd.read_sql("SELECT * FROM regimes", sqlite3.connect(DB), parse_dates=["date"]).set_index("date")
b = pd.concat([base.rename("on"), rg], axis=1).dropna()["2006-06-21":]
for col in ("trend", "vol", "cycle"):
    print(f"\nby {col}: trade net bps / win / n   | unconditional SPY overnight gross bps")
    for k, g in T.groupby(col):
        print(f"  {k:22s} {g.net.mean()*1e4:6.1f} / {(g.net>0).mean():.2f} / {len(g):4d}   | {b[b[col]==k].on.mean()*1e4:5.1f}")
