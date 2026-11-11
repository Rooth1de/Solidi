"""E9 (logs/PREREG_E9_stress_residual.md): market-stress residual snap-back, PIT S&P 500, time-machine replay 2004-2026."""
import warnings, os, glob, json, sqlite3; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats
from research.engine import load, dsr; from research.residual import residual_gate
from timemachine.core import Run, trades_with_regime, DB
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
NT = 68; rng = np.random.default_rng(21)
SECT = ["XLB","XLE","XLF","XLI","XLK","XLP","XLU","XLV","XLY"]
spy = load("SPY"); idx = spy["2002-06":].index
files = {os.path.basename(f)[:-4]: f for f in glob.glob("data/stocks/*.csv") if not f.endswith("_missing.txt")}
ADJ = pd.DataFrame({t: pd.read_csv(f, index_col=0, parse_dates=True).adjclose for t, f in files.items()}).reindex(idx)
RAW = pd.DataFrame({t: pd.read_csv(f, index_col=0, parse_dates=True).close for t, f in files.items()}).reindex(idx)
ETF = pd.DataFrame({s: load(s).c for s in SECT + ["SPY"]}).reindex(idx)
VIX = load("^VIX").c.reindex(idx).ffill()
h = pd.read_csv("data/ext/sp500_hist.csv", parse_dates=["date"]).set_index("date")
MEM = h.tickers.str.split(",").reindex(idx, method="ffill")
frames = {"ADJ": ADJ, "RAW": RAW, "ETF": ETF, "VIX": VIX.to_frame("v"), "MEM": MEM.to_frame("m")}
R_ALL = ADJ.pct_change(); E_ALL = ETF.pct_change()

def is_stress(etf_hist, vix_hist):
    rs = etf_hist.SPY.iloc[-1]/etf_hist.SPY.iloc[-2] - 1; dv = vix_hist.v.iloc[-1]/vix_hist.v.iloc[-2] - 1
    return rs < -0.02 and dv > 0.15, rs, dv

class E9:
    def __init__(self, N, cost_mult=1.0, lag=0, force=False): self.N, self.cm, self.lag, self.force = N, cost_mult, lag, force
    def scan(self, v, d):
        e = v.hist("ETF", 252); vx = v.hist("VIX", 2)
        st, rs, dv = is_stress(e, vx)
        if not (st or self.force): return [dict(sym="_MARKET", spy=round(rs, 4), vix_chg=round(dv, 3), stress=0, signal=0)]
        px = v.hist("ADJ", 252); raw = v.hist("RAW", 1).iloc[-1]; mem = v.hist("MEM", 1).m.iloc[-1]
        if px.index[-1] != d: return [dict(sym="_MARKET", note="no bar")]
        r = px.pct_change().iloc[1:]; er = e.pct_change().iloc[1:]
        names = [t for t in mem if t in px.columns and np.isfinite(r[t].iloc[-1]) and raw.get(t, 0) > 10 and r[t].iloc[:-1].notna().sum() >= 240]
        rows = [dict(sym="_MARKET", spy=round(rs, 4), vix_chg=round(dv, 3), stress=1, members=len(mem), scanned=len(names), signal=0)]
        past = slice(None, -1)
        C = r[names].iloc[past].corrwith  # trailing 250d correlation as of t-1
        corr = pd.DataFrame({s: r[names].iloc[past].corrwith(er[s].iloc[past]) for s in SECT})
        sec = corr.idxmax(1)
        out = []
        for t in names:
            y = r[t].iloc[-121:-1]; X = np.c_[np.ones(120), er.SPY.iloc[-121:-1], er[sec[t]].iloc[-121:-1]]; ok = np.isfinite(y.values) & np.isfinite(X).all(1)
            if ok.sum() < 100: continue
            b, *_ = np.linalg.lstsq(X[ok], y.values[ok], rcond=None); res = y.values[ok] - X[ok]@b
            e_t = r[t].iloc[-1] - b[1]*er.SPY.iloc[-1] - b[2]*er[sec[t]].iloc[-1]
            out.append(dict(sym=t, sector=sec[t], b_m=round(b[1], 3), b_s=round(b[2], 3), resid=round(e_t, 4), z=round(e_t/res.std(), 2)))
        out.sort(key=lambda x: x["z"])
        for i, o in enumerate(out): o["rank"] = i + 1; o["signal"] = int(i < self.N)
        return rows + out
    def decide(self, rows, state, d):
        acts = {}
        for r in rows:
            if not r.get("signal"): continue
            if state.get(r["sym"], pd.Timestamp(0)) >= d: acts[r["sym"]] = "SKIP:held"; continue
            acts[r["sym"]] = "TRADE"
        return acts
    def execute(self, t, F, d):
        i = idx.get_loc(d) + self.lag; r = R_ALL[t["sym"]].values; m = E_ALL.SPY.values; s = E_ALL[t["sector"]].values
        pnl = 0.0; j = i
        for k in range(1, 6):
            j = i + k
            if j >= len(idx) or not np.isfinite(r[j]): return None if k == 1 else dict(side=1, entry=str(idx[i].date()), exit=str(idx[j-1].date()), gross=pnl, cost=self._c(t), net=pnl - self._c(t), extra=dict(days=k-1, z=t["z"], truncated=1))
            day = r[j] - t["b_m"]*m[j] - t["b_s"]*s[j]; pnl += day
            if day > 0: break
        return dict(side=1, entry=str(idx[i].date()), exit=str(idx[j].date()), gross=pnl, cost=self._c(t), net=pnl - self._c(t), extra=dict(days=j - i, z=t["z"], sector=t["sector"]))
    def _c(self, t): return self.cm*(2*5 + 2*1*(abs(t["b_m"]) + abs(t["b_s"])))/1e4

class Holding(E9):   # wraps decide to track held-until dates (one position per name)
    def decide(self, rows, state, d):
        acts = super().decide(rows, state, d)
        for r in rows:
            if acts.get(r["sym"]) == "TRADE": state[r["sym"]] = idx[min(idx.get_loc(d) + self.lag + 5, len(idx) - 1)]
        return acts

def summ(T, label):
    if len(T) < 5: return dict(name=label, n=len(T))
    wk = T.net.groupby(T.index.to_period("W")).mean(); half = T.index[len(T)//2]
    return dict(name=label, n=len(T), days=T.index.nunique(), win=round((T.net > 0).mean(), 3), mean_bps=round(T.net.mean()*1e4, 1), t_wk=round(stats.ttest_1samp(wk, 0).statistic, 2),
                h1=round(T[:half].net.mean()*1e4, 1), h2=round(T[half:].net.mean()*1e4, 1), worst=round(T.net.min()*100, 1),
                payoff=round(T.net[T.net > 0].mean()/abs(T.net[T.net <= 0].mean()), 2),
                dsr=round(dsr(T.net.mean()/T.net.std()*np.sqrt(len(T)/22.8), len(T), stats.skew(T.net), stats.kurtosis(T.net, fisher=False), NT), 3))
P = lambda r: print(pd.DataFrame(r).to_string(index=False))
dates = idx[idx >= "2004-01-02"]
runs = {}
for N in (10, 20):
    for cm, lag, tag in ((1.0, 0, ""), (2.0, 0, "_costx2"), (1.0, 1, "_delay1")):
        name = f"E9_N{N}{tag}"; print(name, Run(name, frames, Holding(N, cm, lag), dates).go()); runs[name] = trades_with_regime(name)
P([summ(T, n) for n, T in runs.items()])
T = runs["E9_N10"]; X = pd.json_normalize(T.payload.map(json.loads)); X.index = T.index; T = pd.concat([T, X], axis=1)
EPIS = {"GFC": ("2007-10", "2009-03"), "2011": ("2011-07", "2011-10"), "2015-16": ("2015-08", "2016-02"), "2018Q4": ("2018-10", "2018-12"),
        "2020": ("2020-02", "2020-04"), "2022": ("2022-01", "2022-10"), "2025-04": ("2025-03", "2025-05")}
print("\nN10 by stress episode:", {k: (f"days {len(g.index.unique())} n{len(g)} {g.net.mean()*1e4:.0f}bp win {(g.net>0).mean():.2f}" if len(g := T[a:b]) else "none") for k, (a, b) in EPIS.items()})
for col in ("trend", "vol", "cycle"): print(f"N10 by {col}:", {k: f"n{len(g)} {g.net.mean()*1e4:.0f}bp win {(g.net>0).mean():.2f}" for k, g in T.groupby(col)})
print("N10 by year:", {y: f"{len(g)}/{g.net.mean()*1e4:.0f}" for y, g in T.groupby(T.index.year)})
# random NON-stress-day null: same procedure forced on 400 random non-stress days, day-level means
con = sqlite3.connect(DB); sd = set(pd.read_sql("SELECT DISTINCT date FROM trades WHERE run='E9_N10'", con).date); con.close()
cand = [d for d in dates if str(d.date()) not in sd]; pick = sorted(rng.choice(len(cand), 400, replace=False))
Run("E9_null_nonstress", frames, Holding(10, 1.0, 0, force=True), pd.DatetimeIndex([cand[i] for i in pick])).go()
Tn = trades_with_regime("E9_null_nonstress"); dm_n = Tn.net.groupby(level=0).mean(); dm_s = T.net.groupby(level=0).mean()
boot = [rng.choice(dm_n.values, len(dm_s)).mean() for _ in range(5000)]
print(f"\nnull: non-stress days same rule mean {Tn.net.mean()*1e4:.1f}bp win {(Tn.net>0).mean():.2f} | stress-day mean of day-means {dm_s.mean()*1e4:.1f}bp, p={np.mean(np.array(boot) >= dm_s.mean()):.3f}")
# R1 gate
daily = pd.Series(0.0, index=idx)
for dt, r in T.iterrows(): daily[dt] += r.net/10
daily = daily[dates]
panel = R_ALL[list(dict.fromkeys(T.sym))[:150]].sub(E_ALL.SPY, axis=0).loc[dates]
print("\nRESIDUAL GATE N10:", residual_gate(T, daily, pd.DataFrame({"SPY": E_ALL.SPY[dates]}), panel, "net", "sym"))
# survivorship haircut: coverage of PIT members with data, by year
cov = MEM.groupby(MEM.index.year).apply(lambda s: np.mean([np.mean([t in files for t in row]) for row in s.iloc[::21]]))
m = T.groupby(T.index.year).net.agg(["mean", "size"]); cv = cov.reindex(m.index); miss = m["size"]*(1 - cv)/cv
print(f"survivorship haircut (missing names' trades at -5%): raw {T.net.mean()*1e4:.1f}bp -> {((m['mean']*m['size'] + miss*-0.05).sum()/(m['size'] + miss).sum())*1e4:.1f}bp; at 0bp: {((m['mean']*m['size']).sum()/(m['size'] + miss).sum())*1e4:.1f}bp")
