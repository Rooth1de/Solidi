import sys, numpy as np, pandas as pd; sys.path.insert(0, "."); from research.engine import *
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
RULES = {"IBS<0.2 hold1": lambda d: sig_ibs(d, .2, 1), "RSI2<10&>SMA200": lambda d: sig_rsi2(d, 10), "3 down closes": lambda d: sig_streak(d, 3)}
SPLIT = "2010-01-01"
d = load("SPY")
print("== SPY, frozen literature params. disc=1993-2009, OOS(post-publication)=2010+, cost 2bps/side, lag0 ==")
rows = []
for name, f in RULES.items():
    bt = backtest(d, f(d), 2.0, 0)
    for lab, s in [("disc", bt[:SPLIT].iloc[:-1]), ("OOS", bt[SPLIT:])]:
        rows.append({"rule": name, "per": lab, **summarize(s)})
bh = pd.DataFrame({"net": d.c.pct_change().fillna(0)}); 
print(pd.DataFrame(rows).to_string(index=False))
print("B&H SPY sharpe disc/OOS:", round(sharpe(bh[:SPLIT].net[:-1]),2), round(sharpe(bh[SPLIT:].net),2))
