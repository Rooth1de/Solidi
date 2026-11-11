"""Minimal, strict research engine. Signals use info <= close[t]; position decided at close t.
lag=0: fill at close t (MOC, optimistic). lag=1: fill at close t+1 (pessimistic delay)."""
import numpy as np, pandas as pd, json, os, time
from scipy import stats
DATA = os.path.join(os.path.dirname(__file__), "..", "data")
def load(sym):
    d = pd.read_csv(os.path.join(DATA, f"{sym}.csv"), index_col=0, parse_dates=True)
    f = d.adjclose / d.close                      # adjust OHLC consistently for dividends
    d = d.assign(o=d.open*f, h=d.high*f, l=d.low*f, c=d.adjclose)
    return d[["o","h","l","c","volume"]].dropna()

# ---------- signals: return desired position (0/1) at each close ----------
def sig_ibs(d, x=0.2, hold=1):
    ibs = (d.c-d.l)/(d.h-d.l).replace(0, np.nan)
    ent = (ibs < x).fillna(False).values; return _hold_n(ent, hold)
def sig_rsi2(d, x=10, trend=200, exit_sma=5):
    ch = d.c.diff(); up = ch.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-ch.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
    rsi = 100-100/(1+up/dn.replace(0, np.nan))
    ent = ((rsi < x) & (d.c > d.c.rolling(trend).mean())).fillna(False).values
    ex = (d.c > d.c.rolling(exit_sma).mean()).fillna(False).values
    pos = np.zeros(len(d)); p = 0
    for i in range(len(d)):
        if p == 0 and ent[i]: p = 1
        elif p == 1 and ex[i]: p = 0
        pos[i] = p
    return pos
def sig_streak(d, n=3):
    dn = (d.c.diff() < 0).astype(int)
    run = dn.groupby((dn == 0).cumsum()).cumsum()
    ent = (run >= n).values
    pos = np.zeros(len(d)); p = 0; up = (d.c.diff() > 0).values
    for i in range(len(d)):
        if p == 0 and ent[i]: p = 1
        elif p == 1 and up[i]: p = 0
        pos[i] = p
    return pos
def _hold_n(ent, hold):
    pos = np.zeros(len(ent)); left = 0
    for i in range(len(ent)):
        if ent[i]: left = hold
        if left > 0: pos[i] = 1; left -= 1
    return pos

# ---------- backtest ----------
def backtest(d, pos, cost_bps=2.0, lag=0):
    pos = pd.Series(pos, index=d.index)
    held = pos.shift(1+lag).fillna(0)             # position earning day t's close-close return
    r = d.c.pct_change().fillna(0)
    turn = held.diff().abs().fillna(held.abs())
    net = held*r - turn*cost_bps/1e4
    return pd.DataFrame({"net": net, "gross": held*r, "held": held, "mkt": r})
def trades(bt):
    h = bt.held.values; n = bt.net.values; out = []; i = 0
    while i < len(h):
        if h[i] > 0:
            j = i
            while j+1 < len(h) and h[j+1] > 0: j += 1
            out.append((bt.index[i], j-i+1, np.prod(1+n[i:j+1])-1)); i = j+1
        else: i += 1
    return pd.DataFrame(out, columns=["start","days","ret"]).set_index("start")

# ---------- metrics ----------
def sharpe(x): x = np.asarray(x); return np.sqrt(252)*x.mean()/x.std() if x.std() > 0 else 0.0
def dsr(sr_ann, n_obs, skew, kurt, n_trials, sr_var=None):
    """Deflated Sharpe prob (Bailey & Lopez de Prado). Per-period SR. Returns P(true SR>0 | N trials)."""
    sr = sr_ann/np.sqrt(252); sv = sr_var if sr_var else 1.0/n_obs
    emc = 0.5772156649
    sr0 = np.sqrt(sv)*((1-emc)*stats.norm.ppf(1-1/n_trials)+emc*stats.norm.ppf(1-1/(n_trials*np.e))) if n_trials > 1 else 0
    den = np.sqrt(1-skew*sr+(kurt-1)/4*sr**2)
    return stats.norm.cdf((sr-sr0)*np.sqrt(n_obs-1)/den)
def summarize(bt, n_trials=10):
    n = bt.net; tr = trades(bt); exp = (bt.held > 0).mean()
    eq = (1+n).cumprod(); dd = (eq/eq.cummax()-1).min()
    # beta-adjusted alpha (daily): net = a + b*mkt
    X = np.c_[np.ones(len(bt)), bt.mkt.values]; b, *_ = np.linalg.lstsq(X, n.values, rcond=None)
    res = n.values-X@b; se = np.sqrt(res.var(ddof=2)*np.linalg.inv(X.T@X).diagonal()); 
    # "in-market" per-trade stats
    tt = stats.ttest_1samp(tr.ret, 0) if len(tr) > 2 else None
    return dict(n_trades=len(tr), exposure=round(exp,3), cagr=round(eq.iloc[-1]**(252/len(n))-1,4),
        sharpe=round(sharpe(n),2), maxdd=round(dd,3), avg_trade_bps=round(tr.ret.mean()*1e4,1) if len(tr) else 0,
        trade_t=round(tt.statistic,2) if tt else 0, hit=round((tr.ret>0).mean(),3) if len(tr) else 0,
        payoff=round(tr.ret[tr.ret>0].mean()/abs(tr.ret[tr.ret<=0].mean()),2) if (tr.ret<=0).any() and (tr.ret>0).any() else None,
        worst_trade=round(tr.ret.min(),3) if len(tr) else 0, alpha_ann=round(b[0]*252,4), alpha_t=round(b[0]/se[0],2), beta=round(b[1],2),
        dsr=round(dsr(sharpe(n), len(n), stats.skew(n), stats.kurtosis(n, fisher=False), n_trials),3))
def log(entry, path=os.path.join(os.path.dirname(__file__), "..", "logs", "experiments.jsonl")):
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S"); open(path, "a").write(json.dumps(entry, default=str)+"\n")
