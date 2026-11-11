import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd; from scipy import stats
from research.engine import load, dsr; from research.residual import residual_gate
from timemachine.core import Run, trades_with_regime
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
NT = 66
LETF = {"TSLA": ["TSLL","TSLT"], "NVDA": ["NVDL","NVDU"], "COIN": ["CONL"], "MSTR": ["MSTX","MSTU"], "PLTR": ["PLTU"], "AMD": ["AMDL"],
        "SMCI": ["SMCX"], "AAPL": ["AAPU"], "AMZN": ["AMZU"], "META": ["FBL"], "MSFT": ["MSFU"], "GOOGL": ["GGLL"]}
frames = {s: load(s) for s in list(LETF) + ["QQQ", "SPY"] + sum(LETF.values(), [])}
first = {s: min(frames[l].index[0] for l in ls) for s, ls in LETF.items()}   # date the first LETF existed (knowable then)

class E8:
    def __init__(self, k, cost_mult=1.0): self.k, self.cm = k, cost_mult
    def scan(self, v, d):
        rows = []; q = v.hist("QQQ", 122)
        for s, ls in LETF.items():
            if d < first[s]: continue                       # instrument did not exist yet -> not in universe
            h = v.hist(s, 122)
            if len(h) < 122 or h.index[-1] != d or q.index[-1] != d: rows.append(dict(sym=s, note="insufficient/no bar")); continue
            r = h.c.pct_change().iloc[1:]; rq = q.c.pct_change().reindex(r.index)
            b = np.cov(r.iloc[:-1], rq.iloc[:-1])[0, 1]/rq.iloc[:-1].var()
            e = r - b*rq; sig = e.iloc[:-1].std(); z = e.iloc[-1]/sig
            lv = sum((v.hist(l, 20).c*v.hist(l, 20).volume).mean() for l in ls if v.has(l))
            flow = lv/(h.c.iloc[-20:]*h.volume.iloc[-20:]).mean()
            rows.append(dict(sym=s, beta=round(b, 3), resid_day=round(e.iloc[-1], 4), z=round(z, 2), letf_dv_ratio=round(flow, 4), signal=int(abs(z) > self.k)))
        return rows
    def decide(self, rows, state, d):
        return {r["sym"]: ("TRADE" if r.get("signal") else ("SKIP:" + r["note"] if "note" in r else "")) for r in rows}
    def execute(self, t, F, d):
        s, q = F[t["sym"]], F["QQQ"]; i = s.index.get_loc(d); iq = q.index.get_loc(d)
        if i + 1 >= len(s) or iq + 1 >= len(q) or s.index[i+1] != q.index[iq+1]: return None
        side = -int(np.sign(t["z"])); b = t["beta"]
        on, onq = s.o.iloc[i+1]/s.c.iloc[i] - 1, q.o.iloc[iq+1]/q.c.iloc[iq] - 1
        gross = side*(on - b*onq); cost = self.cm*(2*3 + abs(b)*2*1)/1e4
        return dict(side=side, entry=str(d.date()), exit=str(s.index[i+1].date()), gross=gross, cost=cost, net=gross - cost,
                    extra=dict(z=t["z"], beta=b, flow=t["letf_dv_ratio"], on_q=onq))

def summ(T, label):
    if len(T) < 5: return dict(name=label, n=len(T))
    wk = T.net.groupby(T.index.to_period("W")).mean(); half = T.index[len(T)//2]
    return dict(name=label, n=len(T), win=round((T.net > 0).mean(), 3), mean_bps=round(T.net.mean()*1e4, 1), t_wk=round(stats.ttest_1samp(wk, 0).statistic, 2),
                h1=round(T[:half].net.mean()*1e4, 1), h2=round(T[half:].net.mean()*1e4, 1), worst=round(T.net.min()*100, 2),
                payoff=round(T.net[T.net > 0].mean()/abs(T.net[T.net <= 0].mean()), 2),
                dsr=round(dsr(T.net.mean()/T.net.std()*np.sqrt(len(T)/((T.index.max() - T.index.min()).days/365.25)), len(T), stats.skew(T.net), stats.kurtosis(T.net, fisher=False), NT), 3))
P = lambda r: print(pd.DataFrame(r).to_string(index=False))
dates = frames["QQQ"]["2022-08-09":].index
rows = []
for k in (1.5, 2.0):
    for cm, tag in ((1.0, ""), (2.0, " cost x2")):
        name = f"E8_k{k}{tag.replace(' ', '_')}"; ns, nt = Run(name, frames, E8(k, cm), dates).go()
        T = trades_with_regime(name); rows.append(summ(T, name + f" (scans logged {ns})"))
P(rows)
T = trades_with_regime("E8_k2.0"); import json
X = pd.json_normalize(T.payload.map(json.loads)); X.index = T.index; T = pd.concat([T, X], axis=1)
print("\nmechanism: down-day (side +1) vs up-day (side -1):", {s: f"n{len(g)} win {(g.net>0).mean():.2f} {g.net.mean()*1e4:.1f}bp" for s, g in T.groupby("side")})
T["flow_terc"] = pd.qcut(T.flow, 3, labels=["low", "mid", "high"])
print("by LETF flow-proxy tercile (mechanism predicts high > low):", {s: f"n{len(g)} {g.net.mean()*1e4:.1f}bp win {(g.net>0).mean():.2f}" for s, g in T.groupby("flow_terc")})
print("by trend regime:", {s: f"n{len(g)} {g.net.mean()*1e4:.1f}bp win {(g.net>0).mean():.2f}" for s, g in T.groupby("trend")})
print("by vol regime:", {s: f"n{len(g)} {g.net.mean()*1e4:.1f}bp win {(g.net>0).mean():.2f}" for s, g in T.groupby("vol")})
print("by cycle:", {s: f"n{len(g)} {g.net.mean()*1e4:.1f}bp" for s, g in T.groupby("cycle")})
print("by name:", {s: f"n{len(g)} {g.net.mean()*1e4:.0f}bp" for s, g in T.groupby("sym")})
# R1 gate: daily P&L vs QQQ and SPY; residual panel of names
daily = T.net.groupby(level=0).mean().reindex(dates).fillna(0)
rq = frames["QQQ"].c.pct_change().reindex(dates); panel = pd.DataFrame({s: frames[s].c.pct_change().reindex(dates) - rq for s in LETF})
print("\nRESIDUAL GATE k2.0:", residual_gate(T.rename(columns={"sym": "sym"}), daily, pd.DataFrame({"QQQ": rq, "SPY": frames["SPY"].c.pct_change().reindex(dates)}), panel, "net", "sym"))
