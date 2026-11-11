import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from research.engine import load; from research.evt import *
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); NT = 35
P = lambda rows: print(pd.DataFrame(rows).to_string(index=False))
print("=== G1 crypto liquidation reversal ===")
def g1(sym, k, lag=0, cost=10):
    c = load(sym).c.iloc[:-1]; r = c.pct_change(); sd = r.rolling(20).std().shift(1)
    return event_trades(c, (r < -k*sd).fillna(False).values, True, 3, lag, cost)
rows = []
for k in (1.5, 2.0):
    for sym in ("BTC-USD", "ETH-USD"):
        t = g1(sym, k)
        rows += [gate(t[:"2021"], f"{sym} k{k} disc", NT), gate(t["2022":], f"{sym} k{k} OOS", NT)]
P(rows)
print("\nstress OOS (BTC,ETH): cost x lag"); P([gate(g1(s, k, l, c)["2022":], f"{s} k{k} c{c} lag{l}", NT) for s in ("BTC-USD","ETH-USD") for k in (1.5,2.0) for c in (10,20) for l in (0,1)])
print("\nbreadth OOS 2022+ k1.5 (c10)"); P([gate(g1(s, 1.5)["2022":], s, NT) for s in ("BTC-USD","ETH-USD","SOL-USD","XRP-USD","BNB-USD","ADA-USD","DOGE-USD")])

print("\n=== G3 bond month-end extension ===")
from research.r2 import tdm
def g3(sym, N, lag=0, cost=2):
    c = load(sym).c["2003":]; fs, fe = tdm(c.index); ent = (fe == -(N+1))
    if lag: ent = np.r_[False, ent[:-1]]
    return event_trades(c, ent, False, N, 0, cost)
rows = []
for N in (1, 2):
    t = g3("TLT", N); rows += [gate(t[:"2013"], f"TLT N{N} disc", NT, "M"), gate(t["2014":], f"TLT N{N} OOS", NT, "M")]
P(rows)
print("\nbreadth/stress OOS 2014+"); P([gate(g3(s, N, l, c)["2014":], f"{s} N{N} c{c} lag{l}", NT, "M") for s in ("TLT","IEF","LQD","AGG") for N in (1,2) for c,l in ((2,0),(5,0),(2,1))])
