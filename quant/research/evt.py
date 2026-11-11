"""Generic event-trade evaluator with strict gates."""
import numpy as np, pandas as pd
from scipy import stats
from research.engine import dsr
def event_trades(c, ent, exit_up=True, tstop=3, lag=0, cost_bps=10, rel=None):
    """c: close series. ent: bool array (signal at close i). Enter close i+lag; exit at first close where
    (rel-adjusted) daily ret > 0 or after tstop days. rel: benchmark close for hedged (excess) returns."""
    r = c.pct_change().fillna(0).values; rb = rel.pct_change().fillna(0).values if rel is not None else np.zeros(len(c))
    x = r - rb; n = len(c); out = []; i = 0
    while i < n:
        if ent[i]:
            a = i + lag; j = a; age = 0
            while j + 1 < n:
                j += 1; age += 1
                if (exit_up and x[j] > 0) or age >= tstop: break
            if j > a:
                seg = slice(a+1, j+1)
                ret = np.prod(1+r[seg]) - 1 - (np.prod(1+rb[seg]) - 1) - 2*cost_bps/1e4
                out.append((c.index[i], j-a, ret))
            i = max(j, i+1)
        else: i += 1
    t = pd.DataFrame(out, columns=["dt","days","ret"]).set_index("dt")
    mu = pd.Series(x, index=c.index).mean()
    t["excess"] = t.ret - ((1+mu)**t.days - 1)
    return t
def gate(t, label, ntrials, cluster="W"):
    t = t.astype({"ret": float, "excess": float})
    if len(t) < 5: return dict(name=label, n=len(t))
    w, l = t.ret[t.ret > 0], t.ret[t.ret <= 0]
    g = t.excess.groupby(t.index.to_period(cluster)).mean(); tc = stats.ttest_1samp(g, 0).statistic if len(g) > 2 else np.nan
    sr_tr = t.ret.mean()/t.ret.std(); 
    return dict(name=label, n=len(t), win=round((t.ret > 0).mean(), 3), exp_bps=round(t.ret.mean()*1e4, 1),
                excess_bps=round(t.excess.mean()*1e4, 1), t_clust=round(tc, 2),
                payoff=round(w.mean()/abs(l.mean()), 2) if len(l) and len(w) else np.nan,
                be_win=round(abs(l.mean())/(w.mean()+abs(l.mean())), 3) if len(l) and len(w) else np.nan,
                worst=round(t.ret.min(), 3), cvar5=round(t.ret[t.ret <= t.ret.quantile(.05)].mean(), 3),
                worst_over_mean=round(abs(t.ret.min())/t.ret.mean(), 1) if t.ret.mean() > 0 else np.inf,
                dsr_tr=round(dsr(sr_tr*np.sqrt(252), len(t), stats.skew(t.ret), stats.kurtosis(t.ret, fisher=False), ntrials), 3))
