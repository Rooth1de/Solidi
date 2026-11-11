"""Research version of the Calibrain harness loop on free daily data:
labellable bracket question -> walk-forward base rates -> model -> Brier-fitted blend -> EV gate -> risk-limited book -> honest eval."""
import numpy as np, pandas as pd
from research.engine import load
UNI = ["SPY","QQQ","IWM","DIA","EFA","EEM","XLF","XLK","XLE","XLV","XLY","XLP","XLI","XLU","XLB"]
FEATS = ["rsi2","ibs","r3z","sma200","vix","ts","volpct","r1z","tom"]

def bracket_labels(d, k_tp, H, sl_atr=1.0, entry="close"):
    """For each t: entry at close t (or open t+1), outcome over days t+1..t+H. Returns outcome (0 tgt,1 stop,2 neither), R (gross)."""
    o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values; atr = d.atr.values; n = len(d)
    out = np.full(n, -1); R = np.full(n, np.nan); slbp = np.full(n, np.nan)
    for t in range(n - H - 1):
        if np.isnan(atr[t]): continue
        e = c[t] if entry == "close" else o[t+1]; start = t + 1 if entry == "close" else t + 1
        sd = sl_atr*atr[t]; tp, sl = e + k_tp*sd, e - sd; slbp[t] = sd/e*1e4; rr = k_tp/sl_atr
        res = None
        for j in range(start, t + 1 + H):
            oj = o[j] if not (entry == "open" and j == t+1) else e
            if oj <= sl: res = (1, (oj - e)/sd); break          # gap through stop
            if oj >= tp: res = (0, (oj - e)/sd); break          # gap through target
            hs, ht = l[j] <= sl, h[j] >= tp
            if hs: res = (1, -1.0); break                       # incl. both-touched -> stop
            if ht: res = (0, rr); break
        if res is None: res = (2, (c[t+H] - e)/sd)
        out[t], R[t] = res
    return out, R, slbp

def features(d, vix, ts):
    c = d.c; r = c.pct_change(); vol = r.rolling(20).std()
    ch = c.diff(); up = ch.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-ch.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
    f = pd.DataFrame(index=d.index)
    f["rsi2"] = 100 - 100/(1 + up/dn.replace(0, np.nan))
    f["ibs"] = (d.c - d.l)/(d.h - d.l).replace(0, np.nan)
    f["r3z"] = c.pct_change(3)/(vol*np.sqrt(3))
    f["sma200"] = c/c.rolling(200).mean() - 1
    f["vix"] = vix.reindex(d.index).ffill()
    f["ts"] = ts.reindex(d.index).ffill().fillna(0.9)
    f["volpct"] = vol.rolling(252).rank(pct=True)
    f["r1z"] = r/vol
    s = pd.Series(1, index=d.index); ym = d.index.to_period("M"); fs = s.groupby(ym).cumsum(); fe = fs - s.groupby(ym).transform("sum") - 1
    f["tom"] = ((fe >= -1) | (fs <= 3)).astype(float)
    return f

def softmax_fit(X, y, lam=1.0, iters=300, lr=0.5):
    n, k = X.shape; K = 3; W = np.zeros((k + 1, K)); Xb = np.c_[np.ones(n), X]; Y = np.eye(K)[y]
    for _ in range(iters):                                   # full-batch gradient descent (convex)
        Z = Xb @ W; Z -= Z.max(1, keepdims=True); P = np.exp(Z); P /= P.sum(1, keepdims=True)
        G = Xb.T @ (P - Y)/n; G[1:] += lam*W[1:]/n; W -= lr*G
    return W
def softmax_pred(W, X):
    Z = np.c_[np.ones(len(X)), X] @ W; Z -= Z.max(1, keepdims=True); P = np.exp(Z); return P/P.sum(1, keepdims=True)

def build(k_tp, H, entry="close"):
    vix = load("^VIX").c; ts = (vix/load("^VIX3M").c).dropna(); rows = []
    for s in UNI:
        d = load(s)["1999":].copy(); tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(1)
        d["atr"] = tr.rolling(14).mean()
        y, R, slbp = bracket_labels(d, k_tp, H, entry=entry); f = features(d, vix, ts)
        df = f.assign(y=y, R=R, slbp=slbp, sym=s, done=d.index.to_series().shift(-H).values)  # label known after t+H
        # walk-forward base rates: trailing 504 COMPLETED windows (window t completes at t+H -> usable at t if t'<=t-H)
        oh = pd.get_dummies(pd.Series(y, index=d.index).where(lambda v: v >= 0)).reindex(columns=[0.0,1.0,2.0], fill_value=0).astype(float)
        oh[pd.Series(y, index=d.index) < 0] = np.nan
        cnt = oh.shift(H).rolling(504, min_periods=252).sum(); tot = cnt.sum(1)
        for k in range(3): df[f"b{k}"] = (cnt[float(k)] + 1)/(tot + 3)
        rows.append(df)
    return pd.concat(rows).dropna(subset=FEATS + ["b0"]).sort_index()

def walk_forward(D, lam=1.0, first_oos=2005):
    D = D.copy(); D[["m0","m1","m2"]] = np.nan; lab = D[D.y >= 0]
    for yr in range(first_oos, D.index.year.max() + 1):
        cut = pd.Timestamp(f"{yr}-01-01"); tr = lab[(lab.done < cut)]
        mu, sd = tr[FEATS].mean(), tr[FEATS].std(); W = softmax_fit(((tr[FEATS]-mu)/sd).values, tr.y.astype(int).values, lam)
        m = D.index.year == yr; D.loc[m, ["m0","m1","m2"]] = softmax_pred(W, ((D.loc[m, FEATS]-mu)/sd).values)
    D = D[D.index.year >= first_oos].copy()
    # Brier-fitted blend weight on PRIOR OOS years only
    D["w"] = 0.5
    for yr in range(first_oos + 2, D.index.year.max() + 1):
        prior = D[(D.index.year < yr) & (D.y >= 0) & (D.done < pd.Timestamp(f"{yr}-01-01"))]
        Y = np.eye(3)[prior.y.astype(int)]; M = prior[["m0","m1","m2"]].values; B = prior[["b0","b1","b2"]].values
        D.loc[D.index.year == yr, "w"] = min(np.arange(0, 1.01, .05), key=lambda w: ((w*M + (1-w)*B - Y)**2).sum(1).mean())
    for k in range(3): D[f"p{k}"] = D.w*D[f"m{k}"] + (1 - D.w)*D[f"b{k}"]
    return D
