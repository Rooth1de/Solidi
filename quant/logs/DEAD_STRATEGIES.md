# Dead strategy register (do not rediscover)
Updated 2026-11-11. Data: Yahoo daily adj. OHLC, SPY 1993-2026 + 20 ETFs. OOS = 2010+ (post-publication).

| ID | Rule (SPY/ETFs, long-only, daily) | Why dead |
|---|---|---|
| H1-IBS | Long if IBS<0.2, hold 1d | OOS beta-adj alpha t=0.67; net edge <0 at 5-10bp/side; Sharpe 0.74->0.57 post-2010; 2/15 ETFs t>2 |
| H1-RSI2 | RSI(2)<10 & close>SMA200, exit close>SMA5 | alpha t 3.7 (pre-2010) -> 1.35 (OOS); DSR 0.84; 0/15 ETFs t>2; unproven post-publication |
| H1-STREAK | 3 consecutive down closes, exit first up close | edge vanishes with 1-day fill delay (t=-0.08); n=2 neighbour t=0.09; negative on GLD/XLE/XLB |
Family-level: all three are the same underlying bet (short-term index reversal); they are ONE hypothesis, not three. Exposure 8-20%, CAGR ~4-5% vs B&H Sharpe 0.85 OOS.
