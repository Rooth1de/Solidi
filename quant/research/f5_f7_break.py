import warnings; warnings.filterwarnings("ignore")
from research.r2 import *
UNI = ["SPY","QQQ","IWM","DIA","EFA","EEM","XLF","XLK","XLE","XLV","XLY","XLP","XLI","XLU","XLB"]
vix = load("^VIX").c; vixmed = vix.rolling(252).median()
def sleeve_tr(sym, kind, cond, lag=0, cost=3, start="2010"):
    d = load(sym)["1999":]; ch = d.c.diff()
    if kind == "rsi":
        up = ch.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-ch.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
        ent = (100-100/(1+up/dn.replace(0,np.nan)) < 10).values; ex = (d.c > d.c.rolling(5).mean()).values
    else:
        dd = (ch < 0).astype(int); ent = (dd.groupby((dd==0).cumsum()).cumsum() >= 3).values; ex = (ch > 0).values
    if cond: ent = ent & (vix > vixmed).reindex(d.index).fillna(False).values
    r = d.c.pct_change().fillna(0).values; out = []; i = 0; n = len(d)
    while i < n:
        if ent[i]:
            j = i; age = 0
            while j+1 < n:
                j += 1; age += 1
                if ex[j] or age >= 5: break
            a, b = i+1+lag, j+1+lag      # earn days a..b inclusive
            if b < n: out.append((d.index[i], b-a+1, np.prod(1+r[a:b+1])-1-2*cost/1e4))
            i = j+1
        else: i += 1
    t = pd.DataFrame(out, columns=["dt","days","ret"]).set_index("dt")[start:]
    mu = pd.Series(r, index=d.index)[start:].mean(); t["excess"] = t.ret - ((1+mu)**t.days-1) + 2*cost/1e4*0
    return t
print("F5 drift-adjusted (excess vs same-asset unconditional drift x same holding days, net of costs), OOS 2010+")
for kind in ("rsi","streak"):
    for cond in (False, True):
        for lag in (0,1):
            T = pd.concat([sleeve_tr(s, kind, cond, lag) for s in UNI]).sort_index()
            wk = T.excess.groupby(T.index.to_period("W")).mean()
            yr = T.excess.groupby(T.index.year).mean()
            print(f"{kind:6s} cond={cond!s:5s} lag{lag}: n={len(T)} win {(T.ret>0).mean():.3f} exp {T.ret.mean()*1e4:5.1f}bp excess {T.excess.mean()*1e4:5.1f}bp t_clust {stats.ttest_1samp(wk,0).statistic:5.2f} | yrs excess<0: {(yr<0).sum()}/{len(yr)}")

print("\nF7 robustness (SPY, cost 3bp/side)")
v3 = load("^VIX3M").c; ratio = (vix/v3).dropna(); spy = load("SPY").c
allf = {h: (spy.shift(-h)/spy-1-6e-4)["2006-08":].dropna() for h in (3,5,10)}
def events(minrun=3, thr=1.0, dedupe=0):
    ab = (ratio >= 1).astype(int); rl = ab.groupby((ab==0).cumsum()).cumsum()
    ev = list(ratio.index[(ratio < thr) & (rl.shift(1) >= minrun)])
    if dedupe:
        keep = []; 
        for e in ev:
            if not keep or (spy.index.get_loc(e) - spy.index.get_loc(keep[-1])) > dedupe: keep.append(e)
        ev = keep
    return pd.DatetimeIndex(ev)
print("plateau: minrun x thr -> h5 win/exp_bps/p  (null win ~0.59, exp ~18bp)")
for mr in (1,2,3,5):
    row = []
    for thr in (1.0, 0.95):
        ev = events(mr, thr); fr = (spy.shift(-5)/spy-1-6e-4).reindex(ev).dropna()
        nul = np.array([rng.choice(allf[5].values, len(fr)).mean() for _ in range(2000)])
        row.append(f"thr{thr}: n{len(fr)} {(fr>0).mean():.2f}/{fr.mean()*1e4:4.0f}/{(nul>=fr.mean()).mean():.3f}")
    print(f" minrun{mr}: " + " | ".join(row))
ev = events(3, 1.0, dedupe=10)
print("\nde-overlapped events (>10d apart):", len(ev))
for lag in (0, 1):
    for h in (3, 5, 10):
        ent = spy.shift(-lag); fr = (spy.shift(-h-lag)/ent-1-6e-4).reindex(ev).dropna()
        nul = np.array([rng.choice(allf[h].values, len(fr)).mean() for _ in range(2000)])
        print(f" lag{lag} h{h:2d}: n{len(fr)} win {(fr>0).mean():.2f} exp {fr.mean()*1e4:4.0f}bp payoff {fr[fr>0].mean()/abs(fr[fr<=0].mean()):.2f} worst {fr.min():.3f} p={(nul>=fr.mean()).mean():.3f}")
print("\nh5 with -4% close stop vs pure time exit (lag0, de-overlapped):")
r = spy.pct_change()
for stop in (None, -0.04, -0.03):
    res = []
    for e in ev:
        i = spy.index.get_loc(e); path = spy.iloc[i:i+6]/spy.iloc[i]-1
        if stop is not None and (path.iloc[1:] <= stop).any(): res.append(path.iloc[1:][path.iloc[1:] <= stop].iloc[0]-6e-4)
        else: res.append(path.iloc[-1]-6e-4)
    res = pd.Series(res); print(f" stop={stop}: win {(res>0).mean():.2f} exp {res.mean()*1e4:.0f}bp worst {res.min():.3f}")
print("\nEvent list (lag0 h5, de-overlapped):")
fr = (spy.shift(-5)/spy-1-6e-4).reindex(ev)
print(" ".join(f"{d.date()}:{v*100:+.1f}" for d, v in fr.items()))
