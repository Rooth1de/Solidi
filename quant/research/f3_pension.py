from research.r2 import *
SPLIT = "2015-01-01"
def pens(eq="SPY", bd="TLT", k=5, thr=0.0, cost=2, lag=0, sign=None):
    E, B = load(eq).c, load(bd).c; px = pd.concat([E, B], axis=1, keys=["e","b"]).dropna()["2002-09-01":]
    R = px.pct_change().fillna(0); fs, fe = tdm(px.index); ym = px.index.to_period("M")
    prev = px.groupby(ym).transform("first").shift(0)  # placeholder
    last_prev = px.c if False else None
    # MTD return measured from previous month's last close to close of day -k
    me = px[fe == -1]; mstart = me.shift(1).reindex(px.index, method=None)
    base = px.groupby(ym).apply(lambda g: g.iloc[0]).reindex(ym).set_index(px.index)  # first close of month
    mlast = me.copy(); mlast.index = mlast.index.to_period("M") + 1
    base = mlast.reindex(ym).set_index(px.index)  # prev month-end close
    mtd = px/base - 1; D = (mtd.e - mtd.b)
    W = pd.DataFrame(0.0, index=px.index, columns=["e","b"]); key = pd.Series("", index=px.index)
    sig_days = np.where(fe == -k)[0]; s_flip = rng.choice([-1,1], len(sig_days)) if sign == "random" else np.ones(len(sig_days))
    for j, i in enumerate(sig_days):
        dval = D.iloc[i]
        if np.isnan(dval) or abs(dval) <= thr: continue
        s = -np.sign(dval)*s_flip[j]          # stocks outperformed -> short stocks, long bonds
        span = range(i+1+lag, min(i+k+1+lag, len(px)))  # earn days -(k-1)..+1
        for t in span: W.iloc[t] = [0.5*s, -0.5*s]; key.iloc[t] = str(ym[i])
    net, held = run_w(R, W, cost)
    return net, held, key, R.e
def go(sl, **kw):
    n, h, k, m = pens(**kw); n, h, k, m = n[sl], h[sl], k[sl], m[sl]; return report("", n, h, trades(n, h, k), m)
rows = []
for k in (3, 5):
    for thr in (0.0, 0.02):
        for lab, sl in [("disc", slice(None,"2014")), ("OOS", slice(SPLIT,None))]:
            rows.append({**go(sl, k=k, thr=thr), "name": f"k{k} thr{thr} {lab}"})
P(rows)
O = slice(SPLIT, None)
print("\nCost/delay k5 thr0 OOS (2 legs, cost per leg per side):"); P([{**go(O,k=5,cost=c,lag=l), "name": f"c{c} lag{l}"} for c in (2,5,10) for l in (0,1)])
print("\nBreadth k5 thr0 full 2003+ & OOS:"); P([{**go(sl,eq=e,bd=b,k=5), "name": f"{e}/{b} {lab}"} for e,b in [("SPY","TLT"),("SPY","IEF"),("SPY","AGG"),("QQQ","TLT"),("IWM","IEF"),("EFA","IEF")] for lab, sl in [("all",slice(None,None)),("OOS",O)]])
print("\nRandom-direction null (k5 thr0, full): 300 sign-shuffles")
obs = trades(*[x for x in pens(k=5)[:3]]).mean()
nul = np.array([trades(*pens(k=5, sign="random")[:3]).mean() for _ in range(300)])
print(f"obs {obs*1e4:.1f}bp  null mean {nul.mean()*1e4:.1f}  p={(nul>=obs).mean():.3f}")
print("\nYearly exp_bps / win (k5 thr0):")
n, h, kk, m = pens(k=5); tr = trades(n, h, kk); tr.index = pd.PeriodIndex(tr.index, freq="M")
print(tr.groupby(tr.index.year).agg(lambda x: f"{x.mean()*1e4:.0f}/{(x>0).mean():.2f}").to_string())
