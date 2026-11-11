import warnings, os, glob; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from research.engine import load; from research.evt import *
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); NT = 35
P = lambda rows: print(pd.DataFrame(rows).to_string(index=False))
D = "data/stocks"; spy = load("SPY").c["2003":]
h = pd.read_csv("data/ext/sp500_hist.csv", parse_dates=["date"]).set_index("date")
mem = h.tickers.str.split(",").reindex(spy.index, method="ffill")
files = {os.path.basename(f)[:-4]: f for f in glob.glob(f"{D}/*.csv") if not f.endswith("_missing.txt")}
# coverage
cov = pd.Series({d.year: 0 for d in spy.index}, dtype=float)
yr_cov = mem.groupby(mem.index.year).apply(lambda s: np.mean([np.mean([t in files for t in row]) for row in s.iloc[::21]]))
print("coverage of PIT members with Yahoo data, by year:", yr_cov.round(2).to_dict())
def stock_trades(t, k, lag=0, cost=6):
    d = pd.read_csv(files[t], index_col=0, parse_dates=True)["2003":]
    c = d.adjclose.reindex(spy.index); raw = d.close.reindex(spy.index)
    if c.notna().sum() < 300: return None
    ism = pd.Series([t in m if isinstance(m, list) else False for m in mem], index=spy.index)
    r = c.pct_change(); idio = r - spy.pct_change(); sd = idio.rolling(60).std().shift(1)
    ent = ((idio < -k*sd) & ism & (raw > 10) & c.notna()).fillna(False).values
    cc = c.ffill(); tr = event_trades(cc, ent, True, 5, lag, cost, rel=spy)
    if len(tr) == 0: return None
    tr["tk"] = t; return tr
def run(k, lag=0, cost=6):
    return pd.concat([x for t in files if (x := stock_trades(t, k, lag, cost)) is not None]).sort_index()
res = {}
for k in (2, 3):
    T = run(k); res[k] = T
    P([gate(T[:"2014"], f"k{k} disc", NT, "W"), gate(T["2015":], f"k{k} OOS", NT, "W")])
for k in (2, 3):
    print(f"\nstress OOS k{k}:"); P([gate(run(k, l, c)["2015":], f"k{k} cost{c} lag{l}", NT) for c, l in ((12, 0), (6, 1), (12, 1))])
for k in (2, 3):
    T = res[k]; y = T.groupby(T.index.year).agg(n=("ret","size"), win=("ret", lambda x: (x>0).mean()), exp=("ret", lambda x: x.mean()*1e4))
    print(f"\nby year k{k}:\n", y.round(2).T.to_string())
    # survivorship haircut: missing member share per year -> assume their trades occur at same rate and each loses 5%
    m = T.groupby(T.index.year).ret.agg(["mean","size"]); cv = yr_cov.reindex(m.index)
    miss_n = m["size"]*(1-cv)/cv; adj = (m["mean"]*m["size"] + miss_n*(-0.05)).sum()/(m["size"]+miss_n).sum()
    print(f"haircut stress k{k}: raw mean {T.ret.mean()*1e4:.1f}bp -> with missing names at -5% each: {adj*1e4:.1f}bp")
