from research.r2 import *
SPLIT = "2009-01-01"   # post McConnell & Xu (2008)
def tom(sym, a, b, cost=2, lag=0, start="1994-01-01"):
    d = load(sym)[start:]; r = d.c.pct_change().fillna(0); fs, fe = tdm(d.index)
    mask = pd.Series(((fe >= -a) | (fs <= b)).astype(float), index=d.index)
    mask = mask.shift(lag).fillna(0)
    net, held = run_w(r.to_frame("x"), mask.to_frame("x"), cost)
    key = pd.Series(np.where(fs <= b+lag, (d.index - pd.offsets.MonthBegin(1)).to_period("M"), d.index.to_period("M")), index=d.index).astype(str)
    return net, held, r, key
rows = []
for (a, b) in [(1,3),(2,3),(1,2),(2,2)]:
    net, held, r, key = tom("SPY", a, b)
    for lab, sl in [("disc", slice(None, "2008")), ("OOS", slice(SPLIT, None))]:
        n, h, k = net[sl], held[sl], key[sl]; rows.append(report(f"TOM[-{a},+{b}] {lab}", n, h, trades(n, h, k), r[sl]))
P(rows)
print("\nCost/delay (SPY [-1,+3] OOS):")
P([report(f"cost{c} lag{l}", *(lambda n,h,r,k: (n[SPLIT:], h[SPLIT:], trades(n[SPLIT:], h[SPLIT:], k[SPLIT:]), r[SPLIT:]))(*tom("SPY",1,3,c,l))) for c in (2,5,10) for l in (0,1)])
print("\nDecay by era (SPY [-1,+3]): exp_bps / win / t")
net, held, r, key = tom("SPY", 1, 3)
for s, e in [("1994","2001"),("2002","2008"),("2009","2015"),("2016","2020"),("2021","2026")]:
    tr = trades(net[s:e], held[s:e], key[s:e]); print(s, e, round(tr.mean()*1e4,1), round((tr>0).mean(),3), round(stats.ttest_1samp(tr,0).statistic,2), len(tr))
print("\nRandom-window null (SPY OOS): mean 4-day ret at random month offsets vs TOM")
rr = r[SPLIT:].values; trO = trades(net[SPLIT:], held[SPLIT:], key[SPLIT:]); obs = trO.mean()
null = np.array([np.mean([np.prod(1+rr[i:i+4])-1-4e-4 for i in rng.integers(0, len(rr)-4, len(trO))]) for _ in range(3000)])
print(f"obs {obs*1e4:.1f}bp  null mean {null.mean()*1e4:.1f}bp  p={(null>=obs).mean():.3f}; null win-rate approx {np.mean([(np.prod(1+rr[i:i+4])-1-4e-4)>0 for i in rng.integers(0,len(rr)-4,20000)]):.3f}")
print("\nBreadth OOS [-1,+3], 3bp:")
P([report(s, *(lambda n,h,r,k: (n[SPLIT:], h[SPLIT:], trades(n[SPLIT:], h[SPLIT:], k[SPLIT:]), r[SPLIT:]))(*tom(s,1,3,3))) for s in ["SPY","QQQ","IWM","DIA","EFA","EEM","XLF","XLK","XLE","TLT","GLD"]])
