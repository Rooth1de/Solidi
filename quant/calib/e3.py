"""E3: calibrated bracket classifier on hourly data (see logs/PREREG_E3_hourly.md). Walk-forward only."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats
from research.engine import dsr, load
from calib.pipeline import softmax_fit, softmax_pred
NT = 50; RR = 0.5; MIN_EV = 0.05
SEG = {"EQ": dict(syms={"SPY": 2, "QQQ": 2, "IWM": 3}, W=140, WB=490, first_oos="2024-07-01", Hs=(7, 14),
                  feats=["r1z","rdz","closez","gapz","vix","volr","dist"]),
       "CRYPTO": dict(syms={"BTC-USD": 10, "ETH-USD": 10}, W=480, WB=1440, first_oos="2025-05-01", Hs=(12, 24),
                      feats=["r1z","r24z","fund","wknd","us","volr","dist"])}

def hourly(sym, seg):
    d = pd.read_csv(f"data/hourly/{sym}.csv", index_col=0, parse_dates=True)
    d.index = pd.to_datetime(d.index, utc=True)
    if seg == "CRYPTO": d = d.iloc[:-1]
    return d.rename(columns={"open":"o","high":"h","low":"l","close":"c"})[["o","h","l","c"]]

def features(d, seg, W):
    c = d.c; lr = np.log(c).diff(); s1 = lr.rolling(W).std(); f = pd.DataFrame(index=d.index); f["s1"] = s1
    f["r1z"] = lr/s1
    if seg == "EQ":
        et = d.index.tz_convert("America/New_York"); day = pd.Series(et.date, index=d.index)
        k = day.groupby(day).cumcount(); last = k == day.groupby(day).transform("size") - 1
        dclose = c.groupby(day).last(); prior = day.map(dclose.shift(1))
        dopen = d.o.groupby(day).first(); gap = day.map(dopen)/prior - 1
        f["rdz"] = (c/prior - 1)/(s1*np.sqrt(k + 1)); f["closez"] = f.rdz*last.astype(float)
        f["gapz"] = gap/s1
        vix = load("^VIX").c; vix.index = vix.index.date; vprior = vix.shift(1)
        f["vix"] = day.map(vprior).astype(float).ffill()
        f["volr"] = lr.rolling(35).std()/s1; f["dist"] = (c/c.rolling(140).mean() - 1)/(s1*np.sqrt(35))
    else:
        close_h = (d.index + pd.Timedelta(hours=1)).hour
        f["r24z"] = (c/c.shift(24) - 1)/(s1*np.sqrt(24))
        f["fund"] = np.isin(close_h, [0, 8, 16]).astype(float)
        f["wknd"] = (d.index.dayofweek >= 5).astype(float)
        f["us"] = ((close_h >= 14) & (close_h <= 21)).astype(float)
        f["volr"] = lr.rolling(120).std()/s1; f["dist"] = (c/c.rolling(480).mean() - 1)/(s1*np.sqrt(120))
    return f

def labels(d, s1, H, side, entry="close"):
    o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values; n = len(d); sg = 1 if side == "L" else -1
    y = np.full(n, -1); R = np.full(n, np.nan); ex = np.full(n, -1)
    for t in range(n - H - 1):
        if not np.isfinite(s1[t]): continue
        sh = s1[t]*np.sqrt(H); e = c[t] if entry == "close" else o[t+1]
        tp, sl = e*(1 + sg*RR*sh), e*(1 - sg*sh); res = None
        for j in range(t + 1, t + 1 + H):
            if not (entry == "open" and j == t + 1):
                if sg*(o[j] - sl) <= 0: res = (1, sg*(o[j]/e - 1)/sh, j); break
                if sg*(o[j] - tp) >= 0: res = (0, sg*(o[j]/e - 1)/sh, j); break
            hit_s = (l[j] <= sl) if sg > 0 else (h[j] >= sl); hit_t = (h[j] >= tp) if sg > 0 else (l[j] <= tp)
            if hit_s: res = (1, -1.0, j); break
            if hit_t: res = (0, RR, j); break
        if res is None: res = (2, sg*(c[t+H]/e - 1)/sh, t + H)
        y[t], R[t], ex[t] = res
    return y, R, ex

def build(seg, H, entry="close"):
    S = SEG[seg]; out = []
    for sym, cbp in S["syms"].items():
        d = hourly(sym, seg); f = features(d, seg, S["W"]); s1 = f.s1.values
        f["sym"] = sym; f["slbp"] = s1*np.sqrt(H)*1e4; f["cost_r"] = 2*cbp/f.slbp; f["i"] = np.arange(len(d))
        f["done"] = d.index.to_series().shift(-H)
        for side in ("L", "S"):
            y, R, ex = labels(d, s1, H, side, entry); f[f"y{side}"] = y; f[f"R{side}"] = R; f[f"ex{side}"] = ex
            oh = pd.DataFrame(np.eye(3)[np.clip(y, 0, 2)], index=d.index); oh[y < 0] = np.nan
            cnt = oh.shift(H).rolling(S["WB"], min_periods=S["WB"]//2).sum(); tot = cnt.sum(1)
            for k in range(3): f[f"b{side}{k}"] = (cnt[k] + 1)/(tot + 3)
        out.append(f)
    return pd.concat(out).dropna(subset=S["feats"] + ["bL0", "bS0"]).sort_index()

def walk(D, seg):
    S = SEG[seg]; F = S["feats"]; months = pd.date_range(pd.Timestamp(S["first_oos"], tz="UTC"), D.index.max(), freq="MS")
    for side in ("L", "S"):
        for k in range(3): D[f"m{side}{k}"] = np.nan
        lab = D[D[f"y{side}"] >= 0]
        for m0 in months:
            tr = lab[lab.done < m0]; mu, sd = tr[F].mean(), tr[F].std().replace(0, 1)
            W = softmax_fit(((tr[F] - mu)/sd).values, tr[f"y{side}"].astype(int).values, 1.0)
            msk = (D.index >= m0) & (D.index < m0 + pd.offsets.MonthBegin(1))
            D.loc[msk, [f"m{side}{k}" for k in range(3)]] = softmax_pred(W, ((D.loc[msk, F] - mu)/sd).values)
    D = D[D.index >= pd.Timestamp(S["first_oos"], tz="UTC")].copy()
    for side in ("L", "S"):
        D[f"w{side}"] = 0.5
        for idx, m0 in enumerate(months):
            if idx < 2: continue
            pr = D[(D.index < m0) & (D.done < m0) & (D[f"y{side}"] >= 0)]
            Y = np.eye(3)[pr[f"y{side}"].astype(int)]; M = pr[[f"m{side}{k}" for k in range(3)]].values; B = pr[[f"b{side}{k}" for k in range(3)]].values
            w = min(np.arange(0, 1.01, .05), key=lambda w: ((w*M + (1 - w)*B - Y)**2).sum(1).mean())
            D.loc[(D.index >= m0) & (D.index < m0 + pd.offsets.MonthBegin(1)), f"w{side}"] = w
        for k in range(3): D[f"p{side}{k}"] = D[f"w{side}"]*D[f"m{side}{k}"] + (1 - D[f"w{side}"])*D[f"b{side}{k}"]
        D[f"ev{side}"] = D[f"p{side}0"]*RR - D[f"p{side}1"] - D.cost_r
    D["side"] = np.where(D.evL >= D.evS, "L", "S"); D["ev"] = D[["evL", "evS"]].max(1)
    D["Rbest"] = np.where(D.side == "L", D.RL, D.RS) - D.cost_r
    return D

def trade(D, cost_mult=1.0, Lab=None):
    """Non-overlapping per symbol; exit at the resolved bar. Lab: alternative labels (delay test)."""
    rows = []
    for sym, g in D.groupby("sym"):
        busy = -1
        for ts, r in g.iterrows():
            if r.i <= busy: continue
            evs = {s: r[f"p{s}0"]*RR - r[f"p{s}1"] - r.cost_r*cost_mult for s in ("L", "S")}
            s = max(evs, key=evs.get)
            if evs[s] < MIN_EV: continue
            src = r if Lab is None else Lab.loc[(Lab.sym == sym) & (Lab.i == r.i)].iloc[0]
            if src[f"y{s}"] < 0: continue
            rows.append((ts, sym, s, evs[s], src[f"R{s}"] - r.cost_r*cost_mult, src[f"y{s}"])); busy = src[f"ex{s}"]
    return pd.DataFrame(rows, columns=["ts","sym","side","ev","R","y"]).set_index("ts").sort_index()

def brier(P, y): return ((P - np.eye(3)[y])**2).sum(1).mean()
def evaluate(seg, H):
    D = walk(build(seg, H), seg); res = {"cfg": f"{seg} H{H}"}
    sk_m, sk_b = [], []
    for s in ("L", "S"):
        L = D[D[f"y{s}"] >= 0]; y = L[f"y{s}"].astype(int).values
        bb = brier(L[[f"b{s}{k}" for k in range(3)]].values, y)
        sk_m.append(1 - brier(L[[f"m{s}{k}" for k in range(3)]].values, y)/bb); sk_b.append(1 - brier(L[[f"p{s}{k}" for k in range(3)]].values, y)/bb)
    res.update(skill_model=round(np.mean(sk_m), 4), skill_blend=round(np.mean(sk_b), 4), w=round((D.wL.mean() + D.wS.mean())/2, 2))
    A = D.dropna(subset=["Rbest"]); rho, pv = stats.spearmanr(A.ev, A.Rbest); top = A[A.ev >= A.ev.quantile(.9)].Rbest.mean()
    res.update(spearman=round(rho, 3), sp_p=round(pv, 3), topdecR=round(top, 3))
    T = trade(D); T2 = trade(D, 2.0)
    Dd = build(seg, H, "open"); Td = trade(D, 1.0, Lab=Dd[Dd.index >= D.index.min()])
    if len(T) >= 5:
        day = T.R.groupby(T.index.normalize()).mean(); half = T.index.min() + (T.index.max() - T.index.min())/2
        yrs = (D.index.max() - D.index.min()).days/365.25
        res.update(n=len(T), win=round((T.R > 0).mean(), 3), meanR=round(T.R.mean(), 3), t_day=round(stats.ttest_1samp(day, 0).statistic, 2),
                   meanR_2x=round(T2.R.mean(), 3) if len(T2) else None, n_2x=len(T2), meanR_delay=round(Td.R.mean(), 3) if len(Td) else None,
                   h1=round(T[:half].R.mean(), 3), h2=round(T[half:].R.mean(), 3), worstR=round(T.R.min(), 2),
                   cvar5=round(T.R[T.R <= T.R.quantile(.05)].mean(), 2), long_share=round((T.side == "L").mean(), 2),
                   dsr=round(dsr(T.R.mean()/T.R.std()*np.sqrt(len(T)/yrs), len(T), stats.skew(T.R), stats.kurtosis(T.R, fisher=False), NT), 3))
    else: res.update(n=len(T))
    base_win = {s: (D[f"y{s}"] == 0)[D[f"y{s}"] >= 0].mean() for s in ("L", "S")}
    res.update(base_tgt_L=round(base_win["L"], 3), base_tgt_S=round(base_win["S"], 3))
    A["bk"] = pd.qcut(A.ev, 10, labels=False, duplicates="drop")
    dec = A.groupby("bk").agg(ev=("ev", "mean"), realR=("Rbest", "mean"), win=("Rbest", lambda x: (x > 0).mean()), n=("ev", "size"))
    return res, dec, T

if __name__ == "__main__":
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
    allres = []
    for seg in ("EQ", "CRYPTO"):
        for H in SEG[seg]["Hs"]:
            r, dec, T = evaluate(seg, H); allres.append(r)
            print(f"\n{r['cfg']} EV-decile table (all OOS decisions, best side, net R):"); print(dec.round(3).T.to_string())
    R = pd.DataFrame(allres); print("\n", R.to_string(index=False)); R.to_csv("logs/e3_results.csv", index=False)
