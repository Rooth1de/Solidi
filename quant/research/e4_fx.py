import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats; from research.engine import load, dsr
from research.r2 import tdm
NT = 52; rng = np.random.default_rng(5)
PAIRS = {"EURUSD=X": ("^STOXX50E", +1), "GBPUSD=X": ("^FTSE", +1), "JPY=X": ("^N225", -1), "AUDUSD=X": ("^AXJO", +1), "CAD=X": ("^GSPTSE", -1)}
spy = load("SPY").c["2003-12":]; cal = spy.index; fs, fe = tdm(cal)
me = cal[fe == -1]
def run(k, cost=2, delay=0, signs=None):
    rows = []
    for fx, (idx, usd_quote) in PAIRS.items():
        f = load(fx).c.reindex(cal, method="ffill"); e = load(idx).c.reindex(cal, method="ffill")
        for m_i, last in enumerate(me[1:], 1):
            prev = me[m_i - 1]; i_last = cal.get_loc(last); i_sig = i_last - k + 1; i_ent = i_sig + delay
            if i_ent >= i_last: continue
            sig_day, ent_day = cal[i_sig], cal[i_ent]
            vals = [spy[prev], spy[sig_day], e[prev], e[sig_day], f[ent_day], f[last]]
            if any(pd.isna(v) for v in vals): continue
            D = (spy[sig_day]/spy[prev] - 1) - (e[sig_day]/e[prev] - 1)
            short_usd = 1 if D > 0 else -1
            if signs is not None: short_usd *= signs.get((fx, last), 1)
            pair_ret = f[last]/f[ent_day] - 1                    # return of the quoted pair
            r = short_usd * usd_quote * pair_ret - 2*cost/1e4    # usd_quote=+1: XXXUSD (long pair = short USD)
            rows.append((last, fx, r))
    T = pd.DataFrame(rows, columns=["m","fx","r"])
    return T, T.groupby("m").r.mean()
def g(b, label):
    b = b.dropna(); w, l = b[b > 0], b[b <= 0]
    if len(b) < 5: return dict(name=label, n=len(b))
    return dict(name=label, n=len(b), win=round((b > 0).mean(), 3), mean_bps=round(b.mean()*1e4, 2), t=round(stats.ttest_1samp(b, 0).statistic, 2),
                payoff=round(w.mean()/abs(l.mean()), 2), worst_bps=round(b.min()*1e4, 1),
                dsr=round(dsr(b.mean()/b.std()*np.sqrt(12), len(b), stats.skew(b), stats.kurtosis(b, fisher=False), NT), 3))
P = lambda r: print(pd.DataFrame(r).to_string(index=False))
rows = []
for k in (3, 2):
    T, b = run(k)
    rows += [g(b[:"2014"], f"k{k} disc 2004-14"), g(b["2015":], f"k{k} OOS 2015-26"), g(b["2015":"2020"], "  OOS 2015-20"), g(b["2021":], "  OOS 2021-26"),
             g(run(k, 4)[1]["2015":], "  OOS cost 4bp"), g(run(k, 2, 1)[1]["2015":], "  OOS delay 1d")]
P(rows)
T, b = run(3); O = T[T.m >= "2015"]
print("\nper pair OOS k3 (mean bps / win):", {fx: f"{g_.r.mean()*1e4:.1f}/{(g_.r>0).mean():.2f}" for fx, g_ in O.groupby("fx")})
obs = b["2015":].mean(); keys = list(zip(T.fx, T.m))
nul = []
for _ in range(1000):
    sg = {kk: rng.choice([-1, 1]) for kk in keys}; nul.append(run(3, signs=sg)[1]["2015":].mean())
print(f"random-sign null k3 OOS: obs {obs*1e4:.2f}bp, null mean {np.mean(nul)*1e4:.2f}bp, p={np.mean(np.array(nul) >= obs):.3f}")
