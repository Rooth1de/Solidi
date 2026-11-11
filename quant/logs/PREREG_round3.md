# Pre-registration, round 3 (written BEFORE running). 2026-11-11. Cumulative trials before: 29.
Gates (all required): net per-trade win >= 65%; positive net expectancy at base AND 2x costs; drift/beta-adjusted
excess > 0 with clustered t >= 2.0 in OOS; survives 1-bar delay with positive excess; plateau across the pre-set grid
(no single-cell significance); worst trade and 1% CVaR reported, worst trade <= 15x mean net trade or capped by a
pre-set stop; DSR(cumulative trials) reported; breadth across instruments.

G1 CRYPTO LIQUIDATION REVERSAL. Data: Yahoo BTC-USD (2014+), ETH-USD (2017+); breadth: SOL, XRP, BNB, ADA, DOGE.
 Payer: forced liquidation of leveraged perpetual longs (exchange liquidation engines are price-insensitive) ->
 overshoot. Rule: daily ret < -k*sd20 -> buy at close, exit first up close, 3-day time stop.
 k in {1.5, 2.0} -> 2 trials. Costs 10bp/side base, 20 stress. Disc <=2021, OOS 2022+.
 Crowding: high (many bots), but the payer is forced.

G2 LARGE-CAP IDIOSYNCRATIC OVERREACTION (pooled, point-in-time S&P 500 membership from fja05680/sp500).
 Data: Yahoo daily for every ticker that was a member 2003+. Payer: liquidity provision to non-informational
 idiosyncratic selling (fund flows, de-risking); large caps have deep liquidity -> quick reversion.
 Rule: (stock ret - SPY ret) < -k*sd60(idio) on a day the stock is an index member, close > $10;
 buy at close, SPY-hedged (beta 1), exit first day stock beats SPY, 5-day time stop. k in {2, 3} -> 2 trials.
 Costs 5bp/side stock + 1bp/side hedge. Disc 2004-2014, OOS 2015+.
 KNOWN BIAS: Yahoo lacks most delisted tickers -> losers that later failed are missing. Will report coverage
 and a haircut stress (assume each missing-name trade = -5%).

G3 BOND MONTH-END INDEX EXTENSION. Data: Yahoo TLT, IEF, LQD, AGG. Payer: passive bond-index funds must extend
 duration at month-end when the index rolls in new issues (mechanical, price-insensitive).
 Rule: long TLT for the last N trading days of the month (enter close of day -(N+1)), N in {1,2} -> 2 trials.
 Costs 2bp/side. Disc 2003-2013, OOS 2014+.
Total new trials: 6 -> cumulative 35.

## Round 3b (after G1-G3 died; written before running). Cumulative before: 35.
H2 LETF/HEDGING REBALANCE OVERNIGHT REVERSAL. Payer: leveraged/inverse ETFs and short-gamma option dealers must
 trade WITH the day's move into the close (Cheng&Madhavan 2009; Shum et al 2016 RoF; Barbon et al 2021: end-of-day
 momentum that dissipates next day). Forced, price-insensitive, AUM rising.
 Rule: if close-to-close ret < -x, buy at the close (MOC), sell at next open (MOO). x in {1.0,1.5,2.0}% -> 3 trials.
 Instruments SPY, QQQ, IWM (pooled; cluster by day). Costs 2bp/side SPY/QQQ, 3 IWM; stress 5bp/side.
 Benchmark: unconditional overnight return (overnight premium) -> report excess over it.
 Mechanism check (not a trial): up days x should show BELOW-normal overnight returns.
 Disc 2000-2012, OOS 2013+. Realism: MOC cutoff 15:50 -> signal uses close; test plateau over x and a
 'signal from close of 15:50 proxy' is unavailable -> flagged.
H6 GAP-DOWN FADE. Payer: opening-auction imbalance (overnight sell orders) absorbed intraday.
 Rule: open/prev close -1 < -g -> buy at open, sell at close. g in {0.5,1.0}% -> 2 trials. Same instruments/costs/split.
Cumulative: 40.

## Round 3c (before running). Cumulative before: 40.
H7 SHARE-CLASS SPREAD REVERSION. Same cash flows, different voting/liquidity -> spread anchored; temporary
 class-specific liquidity demand (index/ETF flows hit one class) is the payer. Pairs (A=liquid,B=other):
 GOOGL/GOOG (2014-04+), BRK-B/BRK-A, FOXA/FOX, NWSA/NWS, BF-B/BF-A, HEI/HEI-A, LEN/LEN-B, Z/ZG, UAA/UA.
 (LBRDK dropped: no data.) s=log(A/B); z=(s-mean60)/sd60 using closes <= t. z<-e: long A/short B $-neutral at close;
 z>e: reverse. Exit when z crosses 0, 10-day stop. Skip signal if either volume==0. e in {1.5, 2.0} -> 2 trials.
 Costs per leg per side: 3bp GOOGL/GOOG/BRK; 10bp others; borrow 1%/yr on short leg. Disc <=2017, OOS 2018+.
 DECISIVE test: 1-day delayed entry (stale-close artifacts in thin classes must not be the source).
H8 ETF CLONES (SPY/IVV, SPY/VOO, QQQ/QQQM, GLD/IAU), same rule e=2.0, costs 1.5bp/leg/side -> 1 trial.
Cumulative: 43.
