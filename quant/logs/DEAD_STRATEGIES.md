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

## Round 3 (2026-11-11). Cumulative trials: 43. Free data: Yahoo (ETFs, stocks, crypto), GitHub raw (PIT S&P 500).
| ID | Rule | Disc -> OOS | Why dead |
|---|---|---|---|
| G1-CRYPTO-LIQ | BTC/ETH big-down-day reversal | ETH 76% win +164bp -> 57% win, -62bp | Decayed after 2021; negative across BTC/ETH/SOL |
| G2-IDIO-REV | PIT S&P 500 idiosyncratic 2-3sd drop, SPY-hedged | negative both | Large-cap idio shocks continue (news); survivorship stress -100bp |
| G3-BOND-ME | TLT last 1-2 days of month | 67% win t3.96 -> 53% t0.66 | Arbitraged ~2014; dies at 5bp |
| H2-LETF-ON | Buy MOC after >1% down day, sell next open | +2.9bp excess (real, t2.9) | Mechanism real but 3bp << costs; win 56% |
| H6-GAPFADE | Buy open after gap down, sell close | ~50% win | No effect |
| H7-SHARECLASS | 9 dual-class pairs z-score reversion | 70% win t9 -> 53% win 0bp | Arbitraged by 2018; BRK-A stale-close artifact |
| H8-ETFCLONE | SPY/IVV etc. | - | Closing-print noise; lag1 win 14% |
Pattern: every easy-to-code edge with a strong pre-2013 record is gone OOS (consistent with crowding thesis).
Accounting fix: round-1 trades() and round-2 F5 book() omitted exit-day cost from per-trade returns (win rates
overstated by ~2-5pts). Daily equity curves were correct; verdicts unchanged. evt.py (round 3) is correct.

## E1 (2026-11-11) Calibrated bracket classifier, Calibrain-harness philosophy. Cumulative trials: 46.
| ID | Setup | Result | Why dead |
|---|---|---|---|
| E1-CALIB-BRACKET | Multinomial logit on 9 known-anomaly features, 15 ETFs, TP 0.5/1.0 ATR vs SL 1 ATR, 5/10d, blended with walk-forward base rates, EV gate | Traded win 69% (k0.5,H5), +0.03R, t 1.5 | Model Brier skill vs base rates -5%, AUC 0.50, blend weight 0.07: features carry no information beyond base rates; 2016-26 ~0R; negative at 2x cost |
Lesson: base rate of a 0.5ATR-target/1ATR-stop bracket is already ~67% target-first. High win rate is free; EV is not.

## E3 / E4 (2026-11-11). Cumulative trials: 52.
| ID | Setup | Result | Why dead |
|---|---|---|---|
| E3-HOURLY-CALIB | Hourly brackets (TP .5sigma_H / SL 1sigma_H), EQ (SPY/QQQ/IWM) & CRYPTO (BTC/ETH), 7 econ features, WF logit + base-rate blend + EV gate | Model beats base rates (+1.4..4.1% Brier) | Skill = volatility (touch vs neither), not direction; top-EV decile realised R negative everywhere; traded win 53-62% |
| E4-FX-ME-HEDGE | Month-end USD direction from MTD US-minus-foreign equity performance, 5 pairs | Disc wrong sign (t -2.85); OOS +1.6bp t0.5 | Fails all gates; daily FX close can't time the 4pm fix |
