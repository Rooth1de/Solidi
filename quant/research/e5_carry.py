import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats; from research.engine import dsr
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
NT = 54; COINS = ["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK"]; FIRST_OOS = pd.Timestamp("2023-12-01", tz="UTC")
def logit_fit(X, y, lam=1.0, it=500, lr=0.5):
    Xb = np.c_[np.ones(len(X)), X]; w = np.zeros(Xb.shape[1])
    for _ in range(it):
        p = 1/(1 + np.exp(-Xb@w)); g = Xb.T@(p - y)/len(y); g[1:] += lam*w[1:]/len(y); w -= lr*g
    return w
def logit_pred(w, X): return 1/(1 + np.exp(-np.c_[np.ones(len(X)), X]@w))
def coin_frame(c, H, cost, delay=0):
    d = pd.read_csv(f"data/hl/{c}.csv", index_col=0, parse_dates=True); d.index = pd.to_datetime(d.index, utc=True)
    full = pd.date_range(d.index[0], d.index[-1], freq="h"); d = d.reindex(full)
    fr = d.fundingRate.fillna(0.0); pr = d.premium.ffill(); cum = fr.cumsum()
    t = full[full.hour == 0]; Hh = H*24; dl = delay*24
    X = pd.DataFrame(index=t)
    X["f24"] = fr.rolling(24).mean().reindex(t)*8760; X["f7d"] = fr.rolling(168).mean().reindex(t)*8760; X["prem"] = pr.reindex(t)
    a = t + pd.Timedelta(hours=dl); b = a + pd.Timedelta(hours=Hh); ok = b <= full[-1]
    net = np.full(len(t), np.nan)
    net[ok] = (cum.reindex(b[ok]).values - cum.reindex(a[ok]).values) + (pr.reindex(a[ok]).values - pr.reindex(b[ok]).values) - cost/1e4
    X["net"] = net; X["done"] = b; X["coin"] = c; X["y"] = (X.net > 0).astype(float); X.loc[X.net.isna(), "y"] = np.nan
    # walk-forward base rate & win/loss magnitudes from COMPLETED windows only (done <= decision time)
    br, ew, el = [], [], []
    for i, ti in enumerate(t):
        comp = X.iloc[:i][(X.done.iloc[:i] <= ti).values].net.dropna()
        if len(comp) < 60: br.append(np.nan); ew.append(np.nan); el.append(np.nan); continue
        br.append(((comp > 0).sum() + 1)/(len(comp) + 2)); ew.append(comp[comp > 0].mean() if (comp > 0).any() else 0); el.append(-comp[comp <= 0].mean() if (comp <= 0).any() else 0)
    X["base"], X["ewin"], X["eloss"] = br, ew, el
    return X.dropna(subset=["f24", "f7d", "prem"])
def build(H, cost, delay=0): return pd.concat([coin_frame(c, H, cost, delay) for c in COINS]).sort_index()
def walk(D):
    F = ["f24", "f7d", "prem"]; D["m"] = np.nan; months = pd.date_range(FIRST_OOS, D.index.max(), freq="MS")
    lab = D.dropna(subset=["y"])
    for m0 in months:
        tr = lab[lab.done < m0]; mu, sd = tr[F].mean(), tr[F].std().replace(0, 1)
        w = logit_fit(((tr[F] - mu)/sd).values, tr.y.values)
        msk = (D.index >= m0) & (D.index < m0 + pd.offsets.MonthBegin(1)); D.loc[msk, "m"] = logit_pred(w, ((D.loc[msk, F] - mu)/sd).values)
    D = D[D.index >= FIRST_OOS].dropna(subset=["base"]).copy(); D["w"] = 0.5
    for i, m0 in enumerate(months):
        if i < 2: continue
        pr = D[(D.index < m0) & (D.done < m0)].dropna(subset=["y"])
        D.loc[(D.index >= m0) & (D.index < m0 + pd.offsets.MonthBegin(1)), "w"] = min(np.arange(0, 1.01, .05), key=lambda w: ((w*pr.m + (1 - w)*pr.base - pr.y)**2).mean())
    D["p"] = D.w*D.m + (1 - D.w)*D.base; D["ev"] = D.p*D.ewin - (1 - D.p)*D.eloss
    return D
def trade(D, gate):
    rows = []
    for c, g in D.groupby("coin"):
        free = D.index.min() - pd.Timedelta(days=1)
        for ti, r in g.iterrows():
            if ti < free or np.isnan(r.net) or not gate(r): continue
            rows.append((ti, c, r.net)); free = r.done
    return pd.DataFrame(rows, columns=["t", "coin", "net"]).set_index("t").sort_index()
def stats_(T, label, H, yrs):
    if len(T) < 5: return dict(name=label, n=len(T))
    wk = T.net.groupby(T.index.to_period("W")).mean(); half = T.index.min() + (T.index.max() - T.index.min())/2
    cv = T.groupby("coin").net.mean()
    return dict(name=label, n=len(T), win=round((T.net > 0).mean(), 3), mean_pct=round(T.net.mean()*100, 3), t_wk=round(stats.ttest_1samp(wk, 0).statistic, 2),
                h1=round(T[:half].net.mean()*100, 3), h2=round(T[half:].net.mean()*100, 3), worst_pct=round(T.net.min()*100, 2),
                cvar5_pct=round(T.net[T.net <= T.net.quantile(.05)].mean()*100, 2), coins_pos=f"{(cv > 0).sum()}/{len(cv)}",
                apr_if_on=round(T.net.mean()*365/H*100, 1),
                dsr=round(dsr(T.net.mean()/T.net.std()*np.sqrt(len(T)/yrs), len(T), stats.skew(T.net), stats.kurtosis(T.net, fisher=False), NT), 3))
P = lambda r: print(pd.DataFrame(r).to_string(index=False))
GATES = {"calibrated EV>0": lambda r: r.ev > 0, "always-on": lambda r: True, "7d funding>0": lambda r: r.f7d > 0}
for H in (7, 30):
    rows = []; D = walk(build(H, 30)); yrs = (D.index.max() - D.index.min()).days/365.25
    D2 = walk(build(H, 60)); Dd = walk(build(H, 30, delay=1))
    y = D.dropna(subset=["y"]); bs_b = ((y.base - y.y)**2).mean()
    print(f"\n=== H={H}d === Brier skill vs base: model {1 - ((y.m - y.y)**2).mean()/bs_b:+.4f}, blend {1 - ((y.p - y.y)**2).mean()/bs_b:+.4f}, mean w {D.w.mean():.2f}; base win freq OOS {y.y.mean():.3f}")
    for name, gt in GATES.items():
        rows += [stats_(trade(D, gt), f"{name} 30bp", H, yrs), stats_(trade(D2, gt), f"   {name} 60bp", H, yrs), stats_(trade(Dd, gt), f"   {name} delay1d", H, yrs)]
    P(rows)
    T = trade(D, GATES["calibrated EV>0"])
    print("per coin (calibrated, 30bp): ", {c: f"n{len(g)} win {(g.net>0).mean():.2f} mean {g.net.mean()*100:.2f}%" for c, g in T.groupby("coin")})
    print("by year (calibrated): ", {yr: f"n{len(g)} win {(g.net>0).mean():.2f} mean {g.net.mean()*100:.2f}%" for yr, g in T.groupby(T.index.year)})
    print("worst 5 trades:", T.net.nsmallest(5).mul(100).round(2).to_dict())
