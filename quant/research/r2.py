import sys, numpy as np, pandas as pd; sys.path.insert(0, "."); from research.engine import load, sharpe, dsr, log
from scipy import stats
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
rng = np.random.default_rng(11); NTRIALS = 21

def tdm(idx):
    s = pd.Series(1, index=idx); ym = idx.to_period("M")
    fs = s.groupby(ym).cumsum(); fe = s.groupby(ym).cumsum() - s.groupby(ym).transform("sum") - 1
    return fs.values, fe.values           # from start: 1..n ; from end: -n..-1

def run_w(R, H, cost_bps, borrow=0.0):
    """R: daily returns df; H: held weights df (weight earning that day's return). Returns net series + held flag."""
    turn = H.diff().abs().sum(1).fillna(H.abs().sum(1))
    net = (H*R).sum(1) - turn*cost_bps/1e4 - (H.clip(upper=0).abs().sum(1))*borrow/252
    return net, (H.abs().sum(1) > 0)

def trades(net, held, key=None):
    """contiguous held segments (or by key, e.g. month) -> compounded net returns"""
    g = (held != held.shift()).cumsum() if key is None else key
    df = pd.DataFrame({"n": net, "g": g})[held.values]
    return df.groupby("g").n.apply(lambda x: np.prod(1+x)-1)

def report(name, net, held, tr, mkt=None, ntr=NTRIALS):
    eq = (1+net).cumprod(); dd = (eq/eq.cummax()-1).min()
    win, loss = tr[tr > 0], tr[tr <= 0]; t = stats.ttest_1samp(tr, 0).statistic if len(tr) > 2 else np.nan
    out = dict(name=name, n=len(tr), win=round((tr > 0).mean(), 3), exp_bps=round(tr.mean()*1e4, 1), t=round(t, 2),
               payoff=round(win.mean()/abs(loss.mean()), 2) if len(loss) and len(win) else np.nan,
               be_win=round(abs(loss.mean())/(win.mean()+abs(loss.mean())), 3) if len(loss) and len(win) else np.nan,
               worst=round(tr.min(), 3), sharpe=round(sharpe(net), 2), cagr=round(eq.iloc[-1]**(252/len(net))-1, 4), maxdd=round(dd, 3),
               expo=round(held.mean(), 2), dsr=round(dsr(sharpe(net), len(net), stats.skew(net), stats.kurtosis(net, fisher=False), ntr), 3))
    if mkt is not None:
        X = np.c_[np.ones(len(net)), mkt.values]; b, *_ = np.linalg.lstsq(X, net.values, rcond=None)
        res = net.values-X@b; se = np.sqrt(res.var(ddof=2)*np.linalg.inv(X.T@X).diagonal())
        out.update(alpha_t=round(b[0]/se[0], 2), beta=round(b[1], 2))
    return out
def P(rows): print(pd.DataFrame(rows).to_string(index=False))
