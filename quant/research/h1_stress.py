import sys, numpy as np, pandas as pd; sys.path.insert(0, "."); from research.engine import *
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
SPLIT = "2010-01-01"; rng = np.random.default_rng(7)
RULES = {"IBS": lambda d: sig_ibs(d, .2, 1), "RSI2": lambda d: sig_rsi2(d, 10), "STREAK3": lambda d: sig_streak(d, 3)}
def oos(d, f, c=2, lag=0): return backtest(d, f(d), c, lag)[SPLIT:]
spy = load("SPY")

print("\n[1] COST x DELAY, SPY OOS: avg_trade_bps / alpha_t / sharpe")
for n, f in RULES.items():
    for lag in (0, 1):
        out = []
        for c in (2, 5, 10):
            s = summarize(oos(spy, f, c, lag)); out.append(f"{c}bp:{s['avg_trade_bps']:>6}/{s['alpha_t']:>5}/{s['sharpe']:>5}")
        print(f"{n:8s} lag{lag}  " + "  ".join(out))

print("\n[2] CROSS-ASSET OOS (lag0, 3bps): alpha_t | avg_trade_bps   (TLT,GLD,USO = negative controls)")
syms = ["SPY","QQQ","IWM","DIA","EFA","EEM","XLF","XLE","XLK","XLV","XLY","XLP","XLI","XLU","XLB","TLT","GLD","USO"]
tab = {}
for s in syms:
    d = load(s); tab[s] = {n: (lambda r: f"{r['alpha_t']:>5} |{r['avg_trade_bps']:>6}")(summarize(oos(d, f, 3))) for n, f in RULES.items()}
print(pd.DataFrame(tab).T.to_string())
eq_syms = syms[:15]
for n, f in RULES.items():
    a = [summarize(oos(load(s), f, 3))["alpha_t"] for s in eq_syms]
    print(f"{n}: equity ETFs with alpha_t>2: {sum(x>2 for x in a)}/15, median alpha_t {np.median(a):.2f}")

print("\n[3] RANDOM-TIMING NULL (SPY OOS, 2000 draws, same #trades & durations): p-value of mean net trade ret")
for n, f in RULES.items():
    bt = oos(spy, f, 2); tr = trades(bt); r = spy.c.pct_change()[SPLIT:].values; N = len(r); obs = tr.ret.mean(); cnt = 0
    for _ in range(2000):
        m = 0
        for dur in tr.days.values:
            i = rng.integers(0, N-dur); m += np.prod(1+r[i:i+dur])-1-2*2e-4
        cnt += (m/len(tr)) >= obs
    print(f"{n:8s} obs {obs*1e4:5.1f}bp  p={cnt/2000:.3f}   (unconditional daily mean = {r.mean()*1e4:.1f}bp)")

print("\n[4] SHUFFLED-BAR NOISE TEST (20 shuffles, full history): mean alpha_t should be ~0")
d = spy; ret = d.c.pct_change().fillna(0).values; rel = np.c_[d.o/d.c, d.h/d.c, d.l/d.c]
for n, f in RULES.items():
    ts = []
    for _ in range(20):
        idx = rng.permutation(len(d)); c = 100*np.cumprod(1+ret[idx]); k = rel[idx]
        fake = pd.DataFrame({"o": k[:,0]*c, "h": k[:,1]*c, "l": k[:,2]*c, "c": c}, index=d.index)
        ts.append(summarize(backtest(fake, f(fake), 2, 0))["alpha_t"])
    print(f"{n:8s} mean alpha_t {np.mean(ts):5.2f}  sd {np.std(ts):4.2f}")
print("   real-data full-history alpha_t:", {n: summarize(backtest(spy, f(spy), 2, 0))["alpha_t"] for n, f in RULES.items()})

print("\n[5] PARAM SWEEP, SPY OOS alpha_t (lag0, 2bps) — want a plateau, not a peak")
print("IBS x,hold:", {(x,h): summarize(oos(spy, lambda d: sig_ibs(d,x,h)))["alpha_t"] for x in (.1,.2,.3) for h in (1,)})
print("RSI2 x:", {x: summarize(oos(spy, lambda d: sig_rsi2(d,x)))["alpha_t"] for x in (5,10,15,20)})
print("STREAK n:", {n: summarize(oos(spy, lambda d: sig_streak(d,n)))["alpha_t"] for n in (2,3,4)})

print("\n[6] CONCENTRATION / TAIL, SPY OOS")
for n, f in RULES.items():
    bt = oos(spy, f, 2); tr = trades(bt); top = tr.ret.sort_values(ascending=False)
    k = max(1, int(.05*len(tr))); yr = bt.net.groupby(bt.index.year).sum()
    ex = bt.net[~bt.index.year.isin([2020, 2022])]
    print(f"{n:8s} top5% trades = {top[:k].sum()/tr.ret.sum():.0%} of PnL | yrs negative {int((yr<0).sum())}/{len(yr)} | worst {tr.ret.min():.1%} on {tr.ret.idxmin().date()} | sharpe ex-2020/22 {sharpe(ex):.2f}")
