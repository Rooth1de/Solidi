import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats; from research.engine import dsr
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); NT = 43
def raw(s): return pd.read_csv(f"data/{s}.csv", index_col=0, parse_dates=True)
PAIRS = [("GOOGL","GOOG",3,"2014-04-03"),("BRK-B","BRK-A",3,None),("FOXA","FOX",10,None),("NWSA","NWS",10,None),("BF-B","BF-A",10,None),
         ("HEI","HEI-A",10,None),("LEN","LEN-B",10,None),("Z","ZG",10,"2015-08-03"),("UAA","UA",10,"2016-04-08")]
CLONES = [("SPY","IVV",1.5,None),("SPY","VOO",1.5,None),("QQQ","QQQM",1.5,None),("GLD","IAU",1.5,None)]
def pair_trades(a, b, cost, start, e, lag=0, look=60, tstop=10):
    A, B = raw(a), raw(b); df = pd.concat([A.adjclose, B.adjclose, A.volume, B.volume], axis=1, keys=["a","b","va","vb"]).dropna()
    if start: df = df[start:]
    s = np.log(df.a/df.b); z = ((s - s.rolling(look).mean())/s.rolling(look).std()).values
    ra, rb = df.a.pct_change().fillna(0).values, df.b.pct_change().fillna(0).values
    ok = ((df.va > 0) & (df.vb > 0)).values; n = len(df); out = []; i = look
    while i < n - 1:
        if ok[i] and abs(z[i]) > e:
            side = -np.sign(z[i]); a0 = i + lag; j = a0; age = 0
            while j + 1 < n:
                j += 1; age += 1
                if np.sign(z[j]) != np.sign(z[i]) or age >= tstop: break
            if j > a0:
                sl = slice(a0+1, j+1)
                gross = side*0.5*((np.prod(1+ra[sl])-1) - (np.prod(1+rb[sl])-1))  # per $ of gross (0.5 each leg)
                net = gross - 0.5*2*2*cost/1e4*1.0 - 0.5*0.01*(j-a0)/252     # 2 legs x 2 sides on 0.5 notional each
                out.append((df.index[i], f"{a}/{b}", j-a0, net, side))
            i = j + 1
        else: i += 1
    return pd.DataFrame(out, columns=["dt","pair","days","ret","side"]).set_index("dt")
def g(t, label):
    if len(t) < 10: return dict(name=label, n=len(t))
    w, l = t.ret[t.ret > 0], t.ret[t.ret <= 0]; wk = t.ret.groupby(t.index.to_period("W")).mean()
    return dict(name=label, n=len(t), pairs=t.pair.nunique(), win=round((t.ret > 0).mean(), 3), exp_bps=round(t.ret.mean()*1e4, 1),
                t_clust=round(stats.ttest_1samp(wk, 0).statistic, 2), payoff=round(w.mean()/abs(l.mean()), 2) if len(l) else np.inf,
                be_win=round(abs(l.mean())/(w.mean()+abs(l.mean())), 3) if len(l) else 0, worst=round(t.ret.min(), 4),
                cvar5=round(t.ret[t.ret <= t.ret.quantile(.05)].mean(), 4), worst_x_mean=round(abs(t.ret.min())/t.ret.mean(), 1) if t.ret.mean() > 0 else np.inf,
                avg_days=round(t.days.mean(), 1), dsr=round(dsr(t.ret.mean()/t.ret.std()*np.sqrt(252/t.days.mean()), len(t), stats.skew(t.ret), stats.kurtosis(t.ret, fisher=False), NT), 3))
def book(pairs, e, lag=0, cm=1.0):
    return pd.concat([pair_trades(a, b, c*cm, s, e, lag) for a, b, c, s in pairs]).sort_index()
P = lambda rows: print(pd.DataFrame(rows).to_string(index=False))
rows = []
for e in (1.5, 2.0):
    T = book(PAIRS, e); rows += [g(T[:"2017"], f"H7 e{e} disc"), g(T["2018":], f"H7 e{e} OOS")]
P(rows)
print("\nDecisive: 1-day delayed entry, and cost x2 (OOS 2018+):")
P([g(book(PAIRS, e, l, cm)["2018":], f"e{e} lag{l} cost x{cm}") for e in (1.5, 2.0) for l in (0, 1) for cm in (1, 2)])
print("\nPer pair, e2.0, OOS lag0 | lag1:")
for a, b, c, s in PAIRS:
    t0, t1 = pair_trades(a, b, c, s, 2.0)["2018":], pair_trades(a, b, c, s, 2.0, 1)["2018":]
    f = lambda t: f"n{len(t):3d} win {(t.ret>0).mean():.2f} exp {t.ret.mean()*1e4:6.1f}bp worst {t.ret.min():+.3f}" if len(t) else "n0"
    print(f"{a+'/'+b:12s} {f(t0)} | {f(t1)}")
print("\nH8 ETF clones e2.0:"); P([g(book(CLONES, 2.0, l)["2011":], f"clones lag{l}") for l in (0, 1)])
