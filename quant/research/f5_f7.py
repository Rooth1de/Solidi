from research.r2 import *
from research.engine import sig_rsi2
UNI = ["SPY","QQQ","IWM","DIA","EFA","EEM","XLF","XLK","XLE","XLV","XLY","XLP","XLI","XLU","XLB"]
vix = load("^VIX").c; vixmed = vix.rolling(252).median()
def entries(d, kind):
    if kind == "rsi":
        ch = d.c.diff(); up = ch.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-ch.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
        rsi = 100-100/(1+up/dn.replace(0, np.nan)); ent = rsi < 10; ex = d.c > d.c.rolling(5).mean()
    else:
        dnd = (d.c.diff() < 0).astype(int); run = dnd.groupby((dnd == 0).cumsum()).cumsum(); ent = run >= 3; ex = d.c.diff() > 0
    return ent.fillna(False).values, ex.fillna(False).values
def sleeve(sym, kind, cond, lag=0, cost=3):
    d = load(sym)["1999-01-01":]; ent, ex = entries(d, kind)
    if cond: c = (vix > vixmed).reindex(d.index).fillna(False).values; ent = ent & c
    pos = np.zeros(len(d)); p = 0; age = 0; tid = np.full(len(d), -1); cur = -1
    for i in range(len(d)):
        if p == 0 and ent[i]: p, age, cur = 1, 0, i
        elif p == 1:
            age += 1
            if ex[i] or age >= 5: p = 0
        pos[i] = p; tid[i] = cur if p else -1
    held = pd.Series(pos, index=d.index).shift(1+lag).fillna(0); tids = pd.Series(tid, index=d.index).shift(1+lag)
    r = d.c.pct_change().fillna(0); net = held*r - held.diff().abs().fillna(0)*cost/1e4
    tr = pd.DataFrame({"n": net, "t": tids})[held > 0].groupby("t").n.apply(lambda x: np.prod(1+x)-1)
    tr.index = d.index[tr.index.astype(int)]; return net, tr
def book(kind, cond, sl, lag=0, cost=3, uni=UNI):
    nets, trs = [], []
    for s in uni:
        n, t = sleeve(s, kind, cond, lag, cost); nets.append(n.rename(s)); trs.append(t)
    port = pd.concat(nets, axis=1).fillna(0).mean(1)[sl]; tr = pd.concat(trs).sort_index()[sl]
    wk = tr.groupby(tr.index.to_period("W")).mean(); tcl = stats.ttest_1samp(wk, 0).statistic
    held = port != 0
    out = report("", port, held, tr, load("SPY").c.pct_change().reindex(port.index).fillna(0), 28)
    out.update(t_clust=round(tcl, 2)); return out
rows = []
for kind in ("rsi", "streak"):
    for cond in (False, True):
        for lab, sl in [("disc", slice("1999","2009")), ("OOS", slice("2010", None))]:
            rows.append({**book(kind, cond, sl), "name": f"{kind} vix>{'med' if cond else 'any'} {lab}"})
P(rows)
O = slice("2010", None)
print("\nCost/delay OOS (conditioned):")
P([{**book(k, True, O, l, c), "name": f"{k} c{c} lag{l}"} for k in ("rsi","streak") for c in (3,5,10) for l in (0,1)])
print("\nDecay by era (conditioned, 3bp): exp_bps / win / t_clust")
for k in ("rsi","streak"):
    print(k, {f"{s}-{e}": (lambda o: f"{o['exp_bps']}/{o['win']}/{o['t_clust']}")(book(k, True, slice(s,e))) for s,e in [("1999","2004"),("2005","2009"),("2010","2014"),("2015","2019"),("2020","2026")]})

print("\n==== F7 post-panic re-leveraging ====")
v3 = load("^VIX3M").c; ratio = (vix/v3).dropna(); above = (ratio >= 1).astype(int)
runlen = above.groupby((above == 0).cumsum()).cumsum()
ev = ratio.index[(ratio < 1) & (runlen.shift(1) >= 3)]
print("events:", len(ev), "first", ev[0].date(), "last", ev[-1].date())
for sym in ("SPY","QQQ","IWM","EFA"):
    c = load(sym).c; r = c.pct_change()
    for h in (5, 10, 20):
        fr = (c.shift(-h)/c - 1 - 2*3e-4).reindex(ev).dropna()
        allfr = (c.shift(-h)/c - 1 - 2*3e-4)["2006-08":].dropna()
        nul = np.array([rng.choice(allfr.values, len(fr)).mean() for _ in range(3000)])
        pre, post = fr[:"2012"], fr["2013":]
        print(f"{sym} h{h:2d} n{len(fr)} win {(fr>0).mean():.2f} exp {fr.mean()*1e4:6.0f}bp payoff {fr[fr>0].mean()/abs(fr[fr<=0].mean()):.2f} worst {fr.min():.3f} | null win {(allfr>0).mean():.2f} exp {allfr.mean()*1e4:4.0f} p={(nul>=fr.mean()).mean():.3f} | pre13 {pre.mean()*1e4:.0f}bp/{(pre>0).mean():.2f} post13 {post.mean()*1e4:.0f}bp/{(post>0).mean():.2f}")
