import warnings, os; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats
from research.engine import load, dsr; from research.residual import residual_gate
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
NT = 64; rng = np.random.default_rng(9)
spy = load("SPY").c; rs = spy.pct_change()
h = pd.read_csv("data/ext/sp500_hist.csv", parse_dates=["date"]).sort_values("date")
sets = [set(x.split(",")) for x in h.tickers]; dates = list(h.date)
ev = []
for i in range(1, len(sets)):
    for t in sets[i-1] - sets[i]: ev.append((dates[i], t, "del"))
    for t in sets[i] - sets[i-1]: ev.append((dates[i], t, "add"))
ev = pd.DataFrame(ev, columns=["D","tk","kind"]); ev = ev[(ev.D >= "2004-01-01") & (ev.D <= "2026-08-31")]
cache = {}
def px(t):
    if t not in cache:
        p = f"data/stocks/{t}.csv"; cache[t] = pd.read_csv(p, index_col=0, parse_dates=True)[["close","adjclose"]] if os.path.exists(p) else None
    return cache[t]
def event_trade(t, D, kind, H, lag=0, cost_mult=1.0, rand_E=None):
    d = px(t)
    if d is None: return None
    a = d.adjclose.reindex(spy.index); r = a.pct_change()
    idx = spy.index; iD = idx.searchsorted(D); iE = iD - 1 if rand_E is None else rand_E
    if iE - 130 < 0 or iE + lag + H >= len(idx) or not np.isfinite(a.iloc[iE]) or d.close.reindex(idx).iloc[iE] < 5: return None
    win = slice(iE - 130, iE - 10); y, x = r.iloc[win], rs.iloc[win]; ok = y.notna() & x.notna()
    if ok.sum() < 100: return None
    b = np.cov(y[ok], x[ok])[0, 1]/x[ok].var()
    seg = slice(iE + lag + 1, iE + lag + H + 1); rr, xx = r.iloc[seg], rs.iloc[seg]
    if rr.isna().any(): return None
    sg = 1 if kind == "del" else -1
    daily = sg*(rr - b*xx); cost = cost_mult*(2*10 + abs(b)*2*1)/1e4
    return dict(t=idx[iE], tk=t, kind=kind, beta=b, net=daily.sum() - cost, daily=daily, cost=cost, exit=idx[iE + lag + H])
def run(kind, H, lag=0, cm=1.0):
    out = [x for _, e in ev[ev.kind == kind].iterrows() if (x := event_trade(e.tk, e.D, kind, H, lag, cm)) is not None]
    T = pd.DataFrame([{k: v for k, v in o.items() if k != "daily"} for o in out]).set_index("t").sort_index()
    dl = pd.concat([o["daily"] for o in out], axis=1); port = dl.mean(1).reindex(spy.index).fillna(0)
    for o in out: port.loc[o["exit"]] -= o["cost"]/max(1, dl.notna().sum(1).get(o["exit"], 1))
    return T.rename(columns={"tk": "sym"}), port, out
def summ(T, label):
    wk = T.net.groupby(T.index.to_period("W")).mean()
    a, b = T[:"2014"], T["2015":]
    return dict(name=label, n=len(T), win=round((T.net > 0).mean(), 3), mean_bps=round(T.net.mean()*1e4, 1), t_wk=round(stats.ttest_1samp(wk, 0).statistic, 2),
                h04_14=round(a.net.mean()*1e4, 1), h15_26=round(b.net.mean()*1e4, 1), worst=round(T.net.min()*100, 1),
                payoff=round(T.net[T.net > 0].mean()/abs(T.net[T.net <= 0].mean()), 2),
                dsr=round(dsr(T.net.mean()/T.net.std()*np.sqrt(len(T)/22), len(T), stats.skew(T.net), stats.kurtosis(T.net, fisher=False), NT), 3))
P = lambda r: print(pd.DataFrame(r).to_string(index=False))
for kind in ("del", "add"):
    tot = (ev.kind == kind).sum(); have = sum(px(t) is not None for t in ev[ev.kind == kind].tk)
    print(f"{kind}: {tot} PIT events 2004-2026, Yahoo data for {have} ({have/tot:.0%})")
rows = []; keep = {}
for kind, H in (("del", 5), ("del", 20), ("add", 5)):
    T, port, out = run(kind, H); keep[(kind, H)] = (T, port, out)
    rows += [summ(T, f"{kind} H{H}"), summ(run(kind, H, 0, 2.0)[0], f"   cost x2"), summ(run(kind, H, 1)[0], f"   delay 1d")]
P(rows)
for (kind, H), (T, port, out) in keep.items():
    tks = list(dict.fromkeys(T.sym))[:150]
    panel = pd.concat({t: (px(t).adjclose.reindex(spy.index).pct_change() - T[T.sym == t].beta.iloc[0]*rs) for t in tks}, axis=1)["2004":]
    g = residual_gate(T, port[port != 0], pd.DataFrame({"SPY": rs}), panel, "net", "sym")
    # random-date null: same ticker, random day 250-750 trading days away from the event, same H
    obs = T.net.mean(); nul = []
    for _ in range(100):
        vals = []
        for o in out:
            iE = spy.index.get_loc(o["t"]); off = rng.integers(250, 750)*rng.choice([-1, 1]); x = event_trade(o["tk"], None, kind, H, rand_E=iE + off) if 0 < iE + off < len(spy) - H - 2 else None
            if x: vals.append(x["net"])
        nul.append(np.mean(vals))
    print(f"\n{kind} H{H}: random-date null obs {obs*1e4:.1f}bp vs null {np.mean(nul)*1e4:.1f}bp p={np.mean(np.array(nul) >= obs):.3f}")
    print("  residual gate:", g)
    print("  by era:", {f"{a}-{b}": f"n{len(x)} win {(x.net>0).mean():.2f} {x.net.mean()*1e4:.0f}bp" for a, b in (("2004","2009"),("2010","2014"),("2015","2019"),("2020","2026")) if len(x := T[a:b])})
