# E3 — In-house calibrated bracket classifier on free HOURLY data. Pre-registered 2026-11-11, before any E3 result.
Cumulative trials before: 46. E3 adds 4 configs -> 50.

## Data
Yahoo 60m, regular session for equities. Equities SPY, QQQ, IWM: 2023-12-13 -> 2026-11-10 (7 bars/day).
Crypto BTC-USD, ETH-USD: 2024-11-12 -> 2026-11-10 (24 bars/day; last partial bar dropped). VIX: daily close of
the PRIOR day (Yahoo daily). Two segments, evaluated separately: EQ and CRYPTO.

## Question (labellable, both sides, as in the harness)
At the close of bar t: sigma_1h = stdev of hourly close-to-close log returns over the trailing W bars
(EQ W=140 ~20 sessions, incl. overnight returns; CRYPTO W=480 ~20 days). sigma_H = sigma_1h*sqrt(H).
LONG bracket: TP = entry*(1+0.5*sigma_H), SL = entry*(1-1.0*sigma_H). SHORT bracket mirrored. RR = 0.5.
Outcome over bars t+1..t+H in {target_first, stop_first, neither}. Same-bar touch of both = stop. Open beyond a
level (gap) fills at the open. neither -> exit at close of t+H. Entry = close of bar t (delay test: open of t+1).
## Configs (4 trials)
EQ: H=7 (one session), H=14 (two sessions).  CRYPTO: H=12, H=24.
## Features (7 per segment, fixed; each has a stated payer)
EQ:
 r1z    last-bar return / sigma_1h                         liquidity provision to short-term pressure (Nagel)
 rdz    return since prior close / (sigma_1h*sqrt(k+1))    intraday hedging/LETF pressure building (Barbon et al)
 closez rdz * 1{decision at the session's last bar}         LETF/hedger close pressure reverses overnight (our H2)
 gapz   today's open / prior close - 1, / sigma_1h          opening-auction imbalance
 vix    prior-day VIX close                                 liquidity-provision premium rises with VIX
 volr   sigma(35 bars)/sigma(140 bars)                      vol regime (compression vs expansion)
 dist   (close/SMA140 - 1)/(sigma_1h*sqrt(35))             multi-day overextension
CRYPTO:
 r1z    last-bar return / sigma_1h                         liquidity provision
 r24z   24h return / (sigma_1h*sqrt(24))                   leveraged-perp liquidation cascades
 fund   1{bar closes at 00/08/16 UTC}                       perp funding settlement flow
 wknd   1{Saturday/Sunday UTC}                              thin weekend liquidity
 us     1{bar closes 14-21 UTC}                             US-session (spot ETF / CME) flow
 volr   sigma(120)/sigma(480)                               vol regime
 dist   (close/SMA480 - 1)/(sigma_1h*sqrt(120))            multi-day overextension
## Model / calibration / policy (Calibrain-harness structure)
Per segment and side: multinomial logistic, L2 lambda=1 on standardised features, pooled across the segment's
symbols, refit at the start of every calendar month on labels COMPLETED before refit (expanding window).
First training window: EQ through 2024-06-30 (OOS 2024-07 -> 2026-11); CRYPTO through 2025-04-30 (OOS 2025-05 -> 2026-11).
Base rates per symbol and side: trailing completed windows (EQ 490 bars, CRYPTO 1440 bars; min half), Laplace.
Blend p = w*model + (1-w)*base; w on grid 0..1 step .05 minimising Brier on PRIOR OOS months (>=2 months; else 0.5).
EV_R = p_target*0.5 - p_stop - cost_R  (E[neither]=0 as harness). Costs per side: SPY/QQQ 2bp, IWM 3bp, BTC/ETH 10bp.
Trade best side if EV_R >= 0.05; one open position per symbol (no overlap); 0.5% equity risk per trade.
## Acceptance gates (ALL required, per config, OOS only)
G1 Brier skill vs base rates > 0 for the model AND for the blend.
G2 Spearman(EV_R, realised net R) > 0 over all OOS decisions, and top EV decile realised net R > 0.
G3 Traded win rate >= 65% (net of costs).
G4 Traded mean net R > 0 at 1x and at 2x costs.
G5 Day-clustered t-stat of traded net R >= 2.0.
G6 Entry delayed to next bar open: mean net R > 0.
G7 Mean net R > 0 in both halves of the OOS period.
G8 Worst trade >= -3R; 5% CVaR reported.
G9 DSR with 50 cumulative trials >= 0.95.
A config passing G1-G9 = candidate for paper trading (<=0.5% risk). Anything else is logged dead.
