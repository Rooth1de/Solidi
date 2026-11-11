# E1 — Calibrated bracket classifier (Calibrain-harness philosophy, research version). Pre-registered 2026-11-11.
Cumulative trials before: 43. This experiment: 3 variants -> 46.
Question (labellable): at close t, long bracket TP = +k_tp*ATR14, SL = -1*ATR14, horizon H trading days.
 Outcome in {target_first, stop_first, neither}. Same-day touch of both = stop (conservative). Gap through a level
 fills at the open. neither -> exit at close t+H (realised R recorded).
Universe: SPY QQQ IWM DIA EFA EEM XLF XLK XLE XLV XLY XLP XLI XLU XLB, 1999-2026.
Features (9, fixed): RSI2, IBS, ret3/vol20, close/SMA200-1, VIX, VIX/VIX3M (VIX/VIX 1 before 2006 -> filled 0.9),
 vol20 percentile (252d), prior-day return/vol20, TOM flag (last 1 / first 3 trading days).
Model: multinomial logistic, L2 (lambda=1.0 on standardised features), pooled across ETFs, refit every January on
 all labels COMPLETED before refit date (expanding). First train 1999-2004, OOS 2005-2026.
Base rates: per ETF, trailing 504 completed windows (Laplace). Calibration: p = w*model + (1-w)*base, w grid 0..1
 by Brier on prior OOS years (w=0.5 until 2 OOS years exist). Harness formula EV_R = p_t*RR - p_s - cost_R
 (E[neither]=0, as harness). Costs 3bp/side -> cost_R = 6bp/SL_bp.
Policy: trade if EV_R >= 0.05; one position per ETF; max 5 concurrent; 0.5% equity risk per trade; daily loss
 limit 2% -> no new entries next day.
Variants (k_tp,H): (0.5,5) primary, (0.5,10), (1.0,5).
Gates (all): OOS Brier skill vs base rates > 0; monotone EV-bucket table (Spearman pred-EV vs realised R > 0, top
 bucket > bottom); traded win >= 65%; traded mean R > 0 at 1x AND 2x costs; clustered t >= 2; survives entry at
 next open; positive in both 2005-2015 and 2016-2026; worst trade bounded (gap-through-stop reported); DSR(46).
