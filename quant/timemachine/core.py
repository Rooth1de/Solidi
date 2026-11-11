"""Time-machine process simulator: point-in-time data, full scan/decision log, regimes, SQLite store."""
import sqlite3, json, os, numpy as np, pandas as pd
from research.engine import load
DB = os.path.join(os.path.dirname(__file__), "..", "logs", "timemachine.sqlite")

class LookAheadError(Exception): pass
class PITView:
    """Point-in-time view. Strategies call view.hist(sym) and get bars with date <= asof only."""
    def __init__(self, frames: dict): self._f = frames; self.asof = None
    def hist(self, sym, n=None):
        d = self._f[sym]; d = d[d.index <= self.asof]
        return d if n is None else d.iloc[-n:]
    def peek_future(self, *_): raise LookAheadError("strategies may not see the future")
    def has(self, sym): return sym in self._f and (self._f[sym].index <= self.asof).any()

CYCLES = [("1993-01","1999-12","90s bull"),("2000-01","2002-12","dot-com bear"),("2003-01","2007-09","2003-07 bull"),
          ("2007-10","2009-03","GFC"),("2009-04","2019-12","2009-19 bull"),("2020-01","2020-06","covid crash+rebound"),
          ("2020-07","2021-12","2020-21 bull"),("2022-01","2022-12","2022 bear"),("2023-01","2026-12","2023-26 bull")]
def regimes():
    """Point-in-time regime labels per date (only past data used for each label)."""
    spy = load("SPY").c; vix = load("^VIX").c.reindex(spy.index).ffill()
    sma = spy.rolling(200).mean(); dd = spy/spy.cummax() - 1
    trend = np.where(spy > sma, "bull", "bear")
    cross = (pd.Series(trend, index=spy.index) != pd.Series(trend, index=spy.index).shift()).astype(int).rolling(20).sum() > 0
    trend = np.where(cross, "transition", trend); trend = np.where(dd < -0.20, "bear", trend)
    q1 = vix.expanding(252).quantile(1/3).shift(1); q2 = vix.expanding(252).quantile(2/3).shift(1)
    vol = np.where(vix <= q1, "lowvol", np.where(vix <= q2, "midvol", "highvol"))
    cyc = pd.Series("", index=spy.index)
    for a, b, n in CYCLES: cyc[a:b] = n
    return pd.DataFrame({"trend": trend, "vol": vol, "dd": dd.round(3), "cycle": cyc}, index=spy.index)

class Run:
    """Replays a strategy day by day. strategy.scan(view, date) -> list of dict rows (every name shown).
    strategy.decide(rows, state) -> list of trades opened at this date; state keeps open positions.
    Fills/exits are computed by strategy.execute(trade, frames) AFTER the decision is logged (executor role)."""
    def __init__(self, name, frames, strategy, dates):
        self.name, self.view, self.s, self.dates, self.frames = name, PITView(frames), strategy, dates, frames
    def go(self):
        con = sqlite3.connect(DB); cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS scans(run TEXT, date TEXT, sym TEXT, payload TEXT, signal INT, action TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS trades(run TEXT, date TEXT, sym TEXT, side INT, entry TEXT, exit TEXT, gross REAL, cost REAL, net REAL, payload TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS regimes(date TEXT PRIMARY KEY, trend TEXT, vol TEXT, dd REAL, cycle TEXT)")
        cur.execute("DELETE FROM scans WHERE run=?", (self.name,)); cur.execute("DELETE FROM trades WHERE run=?", (self.name,))
        rg = regimes(); cur.executemany("INSERT OR REPLACE INTO regimes VALUES(?,?,?,?,?)", [(str(d.date()), *r) for d, r in rg.iterrows()])
        state = {}; scans = []; trades = []
        for d in self.dates:
            self.view.asof = d
            rows = self.s.scan(self.view, d)
            acts = self.s.decide(rows, state, d)
            for r in rows: scans.append((self.name, str(d.date()), r["sym"], json.dumps({k: v for k, v in r.items() if k != "sym"}, default=float), int(r.get("signal", 0)), acts.get(r["sym"], "")))
            for t in [r for r in rows if acts.get(r["sym"]) == "TRADE"]:
                ex = self.s.execute(t, self.frames, d)          # executor: uses realised future bars, never visible to scan/decide
                if ex: trades.append((self.name, str(d.date()), t["sym"], ex["side"], ex["entry"], ex["exit"], ex["gross"], ex["cost"], ex["net"], json.dumps(ex.get("extra", {}), default=float)))
        cur.executemany("INSERT INTO scans VALUES(?,?,?,?,?,?)", scans); cur.executemany("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?)", trades)
        con.commit(); con.close(); return len(scans), len(trades)

def trades_with_regime(run):
    con = sqlite3.connect(DB)
    T = pd.read_sql("SELECT t.*, r.trend, r.vol, r.cycle, r.dd FROM trades t LEFT JOIN regimes r ON t.date=r.date WHERE run=?", con, params=(run,), parse_dates=["date"])
    con.close(); return T.set_index("date").sort_index()
