import warnings, json; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats
from research.engine import dsr; from research.residual import residual_gate
from timemachine.core import PITView
import sqlite3, os
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
U = "BTC ETH SOL XRP DOGE AVAX LINK BNB ADA SUI ARB NEAR AAVE UNI INJ DOT LTC BCH kPEPE WLD".split(); NT = 70
DB = "logs/timemachine.sqlite"
H = {}
for c in U:
    d = pd.read_csv(f"data/hl/{c}.csv", index_col=0, parse_dates=True); d.index = pd.to_datetime(d.index, utc=True)
    H[c] = d.reindex(pd.date_range(d.index[0], d.index[-1], freq="h"))
hours = pd.date_range(max(H["BTC"].index[0], pd.Timestamp("2023-06-01", tz="UTC")), min(h.index[-1] for h in H.values()) - pd.Timedelta(hours=25), freq="h")
# crypto regimes (point-in-time) from HL daily BTC candles
btc = pd.read_csv("data/hl/BTC_1d.csv", index_col=0, parse_dates=True).c; btc.index = pd.to_datetime(btc.index, utc=True)
trend = np.where(btc > btc.rolling(200, min_periods=100).mean(), "btc_bull", "btc_bear")
rv = np.log(btc).diff().rolling(30).std(); q1, q2 = rv.expanding(90).quantile(1/3).shift(1), rv.expanding(90).quantile(2/3).shift(1)
vol = np.where(rv <= q1, "lowvol", np.where(rv <= q2, "midvol", "highvol"))
REG = pd.DataFrame({"trend": trend, "vol": vol}, index=btc.index)
def replay(X, cost_bp=30, delay=0, run=None):
    view = PITView(H); trades = []; scans = []; busy = {c: hours[0] - pd.Timedelta(hours=1) for c in U}
    for t in hours:
        view.asof = t
        for c in U:
            row = view.hist(c, 1)
            if not len(row) or row.index[-1] != t or not np.isfinite(row.premium.iloc[-1]): continue
            p = row.premium.iloc[-1]; sig = int(abs(p) > X/1e4)
            act = ""
            if sig and t > busy[c]:
                act = "TRADE"
                # executor (outcome uses future rows; never visible to the scan above)
                f = H[c]; i = f.index.get_loc(t) + delay; pe = f.premium.iloc[i]; side = 1 if p < 0 else -1   # +1 = long perp/short spot
                fund = 0.0; j = i
                for k in range(1, 25):
                    j = i + k
                    if j >= len(f): break
                    fr = f.fundingRate.iloc[j]; fund += -side*(fr if np.isfinite(fr) else 0.0)
                    if np.isfinite(f.premium.iloc[j]) and abs(f.premium.iloc[j]) <= 0.0005: break
                px = f.premium.iloc[j] if np.isfinite(f.premium.iloc[j]) else pe
                gross = side*(px - pe) + fund; trades.append((t, c, side, gross - cost_bp/1e4, j - i, p)); busy[c] = f.index[j]
            elif sig: act = "SKIP:busy"
            if run and (sig or t.hour == 0): scans.append((run, str(t), c, json.dumps({"premium": round(p, 6)}), sig, act))
    if run:
        con = sqlite3.connect(DB); cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS scans(run TEXT, date TEXT, sym TEXT, payload TEXT, signal INT, action TEXT)")
        cur.execute("DELETE FROM scans WHERE run=?", (run,)); cur.executemany("INSERT INTO scans VALUES(?,?,?,?,?,?)", scans); con.commit(); con.close()
    return pd.DataFrame(trades, columns=["t","sym","side","net","hours","p_entry"]).set_index("t").sort_index()
def summ(T, label):
    if len(T) < 5: return dict(name=label, n=len(T))
    wk = T.net.groupby(T.index.to_period("W")).mean(); half = T.index[len(T)//2]; yrs = (hours[-1] - hours[0]).days/365.25
    return dict(name=label, n=len(T), win=round((T.net > 0).mean(), 3), mean_bps=round(T.net.mean()*1e4, 1), t_wk=round(stats.ttest_1samp(wk, 0).statistic, 2),
                h1=round(T[:half].net.mean()*1e4, 1), h2=round(T[half:].net.mean()*1e4, 1), worst_bps=round(T.net.min()*1e4, 0),
                avg_hours=round(T.hours.mean(), 1), coins=T.sym.nunique(),
                dsr=round(dsr(T.net.mean()/T.net.std()*np.sqrt(len(T)/yrs), len(T), stats.skew(T.net), stats.kurtosis(T.net, fisher=False), NT), 3))
P = lambda r: print(pd.DataFrame(r).to_string(index=False))
allp = pd.concat([H[c].premium.rename(c) for c in U], axis=1).loc[hours]
print("premium |bp| distribution across coin-hours: p50 %.1f p90 %.1f p99 %.1f p99.9 %.1f" % tuple(np.nanpercentile(allp.abs().values*1e4, [50, 90, 99, 99.9])))
rows = []; keep = {}
for X in (30, 50):
    T = replay(X, run=f"E10_X{X}"); keep[X] = T
    rows += [summ(T, f"X{X}bp"), summ(replay(X, 60), "   cost 60bp"), summ(replay(X, 30, 1), "   delay 1h")]
    for s, g in T.groupby("side"): rows.append(summ(g, f"   side {'long perp/short spot' if s > 0 else 'short perp/long spot'}"))
P(rows)
for X, T in keep.items():
    T = T.copy(); T["day"] = T.index.normalize(); T = T.join(REG, on="day")
    T["cycle"] = np.select([T.index < "2024-01-01", T.index < "2025-01-01", T.index < "2026-01-01"], ["2023H2", "2024", "2025"], "2026")
    for col in ("trend", "vol", "cycle"): print(f"X{X} by {col}:", {k: f"n{len(g)} {g.net.mean()*1e4:.1f}bp win {(g.net>0).mean():.2f}" for k, g in T.groupby(col)})
    print(f"X{X} by coin:", {k: f"n{len(g)} {g.net.mean()*1e4:.0f}" for k, g in T.groupby("sym")})
    C = pd.concat([pd.read_csv(f"data/hl/{c}_1d.csv", index_col=0, parse_dates=True).c.rename(c) for c in U], axis=1); C.index = pd.to_datetime(C.index, utc=True)
    mkt = np.log(C).diff().mean(1); daily = T.net.groupby(T.index.normalize()).sum().reindex(mkt.index).fillna(0)
    print(f"X{X} RESIDUAL GATE:", residual_gate(T, daily["2023-06":], pd.DataFrame({"MKT": mkt["2023-06":]}), np.log(C).diff()["2023-06":].sub(mkt["2023-06":], axis=0), "net", "sym"))
