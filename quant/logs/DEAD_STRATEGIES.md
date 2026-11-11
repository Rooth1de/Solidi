# Dead strategy register (do not rediscover)
Updated 2026-11-11. Data: Yahoo daily adj. OHLC, SPY 1993-2026 + 20 ETFs. OOS = 2010+ (post-publication).

| ID | Rule (SPY/ETFs, long-only, daily) | Why dead |
|---|---|---|
| H1-IBS | Long if IBS<0.2, hold 1d | OOS beta-adj alpha t=0.67; net edge <0 at 5-10bp/side; Sharpe 0.74->0.57 post-2010; 2/15 ETFs t>2 |
| H1-RSI2 | RSI(2)<10 & close>SMA200, exit close>SMA5 | alpha t 3.7 (pre-2010) -> 1.35 (OOS); DSR 0.84; 0/15 ETFs t>2; unproven post-publication |
| H1-STREAK | 3 consecutive down closes, exit first up close | edge vanishes with 1-day fill delay (t=-0.08); n=2 neighbour t=0.09; negative on GLD/XLE/XLB |
Family-level: all three are the same underlying bet (short-term index reversal); they are ONE hypothesis, not three. Exposure 8-20%, CAGR ~4-5% vs B&H Sharpe 0.85 OOS.

## Round 2 (2026-11-11) — win-rate >= 65% filter added. Cumulative trials: 29.
| ID | Rule | Win | Why dead |
|---|---|---|---|
| F2-TOM | Long SPY trading days -1..+3 of month | 55% OOS | Not better than a random 4-day window post-2009 (p=0.31); alpha t~0; dies at 5bp/side |
| F3-PENSION | MTD equity-vs-bond spread, fade into month-end (crude proxy of Harvey/Mazzoleni/Melone) | 49% | No effect in proxy form; exact paper signal not replicated -> re-test only with faithful replication |
| F4-SHORTVOL | Short VIXY when VIX/VIX3M<x | 35-46%/episode, 55-62% monthly | OOS alpha<0; -34% single day; -30% on 2026-11-05. Filter cut 2018/2020 damage but not 1-day spikes |
| F5-REVPOOL | RSI2 / 3-down on 15 ETFs, VIX-conditioned | 60-64% net | Drift-adjusted excess 7-9bp/trade = cost-fragile; streak dies with 1d delay; Nagel VIX conditioning adds ~nothing on ETFs |
| F8-PUTWRITE | CBOE PUT index | 73% monthly | Zero alpha 2010+ after beta 0.58; negative skew. High win rate = beta + short gamma |
WATCHLIST (unproven, not dead, not promotable): F7 post-panic re-leveraging (see report); F5 RSI2-pooled (thin, real-looking residual).
Lesson: win rate is a design choice (exit placement), not evidence. All 5 families above with 60-73% win rates had ~zero risk-adjusted alpha.
