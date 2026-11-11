import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats
from research.engine import dsr; from research.residual import residual_gate
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
U = "BTC ETH SOL XRP DOGE AVAX LINK BNB ADA SUI ARB NEAR AAVE UNI INJ DOT LTC BCH kPEPE WLD".split()
NT = 61; START, END = "2023-11-01", "2026-11-10"; rng = np.random.default_rng(3)
SLIP = {c: (1 if c in ("BTC","ETH","SOL") else 5) for c in U}
def load_panel():
    C = pd.concat([pd.read_csv(f"data/hl/{c}_1d.csv", index_col=0, parse_dates=True).c.rename(c) for c in U], axis=1)
    C.index = pd.to_datetime(C.index, utc=True).normalize()
    F = {}
    for c in U:
        f = pd.read_csv(f"data/hl/{c}.csv", index_col=0, parse_dates=True).fundingRate; f.index = pd.to_datetime(f.index, utc=True)
        F[c] = f.resample("D").sum(min_count=1)      # daily funding paid (sum of hourly rates), UTC day
    F = pd.DataFrame(F).reindex(C.index)
    R = np.log(C).diff()
    return C, R, F
C, R, F = load_panel()
live = R.notna(); n_live = live.sum(1)
MKT_LOO = (R.sum(1).values[:, None] - R.fillna(0).values)/(n_live.values[:, None] - 1); MKT_LOO = pd.DataFrame(MKT_LOO, index=R.index, columns=U).where(live)
MKT = R.mean(1)
beta = pd.DataFrame(index=R.index, columns=U, dtype=float); E = beta.copy()
for c in U:
    cov = R[c].rolling(60, min_periods=40).cov(MKT_LOO[c]); var = MKT_LOO[c].rolling(60, min_periods=40).var()
    beta[c] = (cov/var).shift(1)
E = R - beta*MKT_LOO
SIG = E.rolling(60, min_periods=40).std().shift(1); Z = E/SIG
window = (R.index >= START) & (R.index <= END) & (n_live >= 10).values
fund_med = F.median(1)

def e6a(k, confirm, lag=0, cost_mult=1.0, rand=False):
    rows = []; daily = pd.Series(0.0, index=R.index)
    for c in U:
        z, e, r, b, mk, f = Z[c].values, E[c].values, R[c].values, beta[c].values, MKT_LOO[c].values, F[c].values
        fm = fund_med.values; f_bask = (F.sum(1).values - np.nan_to_num(f))/(n_live.values - 1)
        idx = np.where(window)[0]; i = idx[0]; last = idx[-1]
        while i <= last - 6:
            sig = 0
            if rand: sig = rng.choice([-1, 1]) if rng.random() < rand else 0
            elif np.isfinite(z[i]) and abs(z[i]) > k:
                sig = -int(np.sign(z[i]))
                if confirm and not (np.isfinite(f[i]) and ((sig > 0 and f[i] < fm[i]) or (sig < 0 and f[i] > fm[i]))): sig = 0
            if sig == 0 or not np.isfinite(b[i]): i += 1; continue
            a = i + lag; bb = b[i]; pnl = 0.0; j = a
            for d in range(1, 6):
                j = a + d
                if j > last or not np.isfinite(r[j]): break
                day = sig*(r[j] - bb*mk[j]) - sig*np.nan_to_num(f[j]) + sig*bb*np.nan_to_num(f_bask[j])
                pnl += day; daily.iloc[j] += day
                if sig*(r[j] - bb*mk[j]) > 0: break
            cost = cost_mult*(2*(4.5 + SLIP[c]) + abs(bb)*2*(4.5 + 3))/1e4
            daily.iloc[min(j, last)] -= cost
            rows.append((R.index[i], c, sig, pnl - cost, j - a, abs(bb))); i = j + 1
    T = pd.DataFrame(rows, columns=["t","sym","side","net","days","beta"]).set_index("t").sort_index()
    return T, daily[window]

def e6b(lag=0, cost_mult=1.0):
    f7 = F.rolling(7, min_periods=5).mean(); rows = []; daily = pd.Series(0.0, index=R.index)
    mondays = [t for t in R.index[window] if t.dayofweek == 0]
    for t0 in mondays:
        i = R.index.get_loc(t0) + lag
        fr = (f7.iloc[i] - f7.iloc[i].mean()).dropna(); bt = beta.iloc[i].dropna(); names = fr.index.intersection(bt.index)
        if len(names) < 10: continue
        fr = fr[names].sort_values(); lo, hi = fr.index[:5], fr.index[-5:]
        wl = pd.Series(1/5, index=lo); ws = pd.Series(-1/5, index=hi)
        # scale short leg so that sum(beta*w) = 0
        bl, bs = (wl*bt[lo]).sum(), (ws*bt[hi]).sum(); ws = ws*(bl/-bs) if bs != 0 else ws
        w = pd.concat([wl, ws]); gross = w.abs().sum(); w = w/gross*2      # 1 unit long-equivalent per side
        pnl = 0.0
        for d in range(1, 8):
            j = i + d
            if j >= len(R): break
            day = (w*R.iloc[j][w.index].fillna(0)).sum() - (w*F.iloc[j][w.index].fillna(0)).sum()
            pnl += day; daily.iloc[j] += day
        cost = cost_mult*w.abs().sum()*2*(4.5 + 5)/1e4; daily.iloc[min(i + 7, len(R) - 1)] -= cost
        rows.append((t0, "PORT", pnl - cost, 7, 0))
    T = pd.DataFrame(rows, columns=["t","sym","net","days","beta"]).set_index("t"); return T, daily[window]

def summ(T, label):
    if len(T) < 5: return dict(name=label, n=len(T))
    wk = T.net.groupby(T.index.to_period("W")).mean(); half = T.index[len(T)//2]
    yrs = (T.index.max() - T.index.min()).days/365.25
    return dict(name=label, n=len(T), win=round((T.net > 0).mean(), 3), mean_bps=round(T.net.mean()*1e4, 1), t_wk=round(stats.ttest_1samp(wk, 0).statistic, 2),
                h1=round(T[:half].net.mean()*1e4, 1), h2=round(T[half:].net.mean()*1e4, 1), worst=round(T.net.min()*100, 2),
                payoff=round(T.net[T.net > 0].mean()/abs(T.net[T.net <= 0].mean()), 2),
                dsr=round(dsr(T.net.mean()/T.net.std()*np.sqrt(len(T)/yrs), len(T), stats.skew(T.net), stats.kurtosis(T.net, fisher=False), NT), 3))
P = lambda r: print(pd.DataFrame(r).to_string(index=False))
factors = pd.DataFrame({"MKT": MKT[window], "BTC": R.BTC[window]})
residp = E[window]
print(f"mean pairwise residual correlation (factor-model adequacy): {np.nanmean(residp.corr().values[np.triu_indices(len(U), 1)]):.3f}; raw return corr: {np.nanmean(R[window].corr().values[np.triu_indices(len(U), 1)]):.3f}")
rows = []
for confirm in (False, True):
    for k in (1.5, 2.0, 2.5):
        T, dly = e6a(k, confirm); rows.append(summ(T, f"E6a k{k} {'confirmed' if confirm else 'plain'}"))
P(rows)
print("\nE6a stress (k=2.0):"); P([summ(e6a(2.0, cf, l, cm)[0], f"{'conf' if cf else 'plain'} cost x{cm} lag{l}") for cf in (False, True) for cm, l in ((2, 0), (1, 1))])
T, dly = e6a(2.0, False)
null = []
for _ in range(200):
    Tn, _ = e6a(2.0, False, rand=len(T)/(window.sum()*len(U))); null.append(Tn.net.mean())
print(f"random-timing null (plain k2): obs {T.net.mean()*1e4:.1f}bp vs null mean {np.mean(null)*1e4:.1f}bp, p={np.mean(np.array(null) >= T.net.mean()):.3f}")
g = residual_gate(T, dly, factors, residp, "net", "sym"); print("RESIDUAL GATE E6a plain k2:", g)
Tc, dlyc = e6a(2.0, True); print("RESIDUAL GATE E6a confirmed k2:", residual_gate(Tc, dlyc, factors, residp, "net", "sym"))
print("E6a plain k2 by side:", {s: f"n{len(x)} win {(x.net>0).mean():.2f} {x.net.mean()*1e4:.0f}bp" for s, x in T.groupby("side")})
print("\n=== E6b residual funding carry ===")
Tb, dlyb = e6b(); P([summ(Tb, "E6b base"), summ(e6b(0, 2)[0], "E6b cost x2"), summ(e6b(1)[0], "E6b lag1d")])
print("RESIDUAL GATE E6b:", residual_gate(Tb, dlyb, factors, residp, "net", "sym"))
