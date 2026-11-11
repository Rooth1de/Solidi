# E6 — Residual-first experiments on Hyperliquid perps. Pre-registered 2026-11-11 (before any E6 result).
Cumulative trials before: 54. E6 adds 7 -> 61.
Universe (fixed, liquid, listed by 2023-11): BTC ETH SOL XRP DOGE AVAX LINK BNB ADA SUI ARB NEAR AAVE UNI INJ DOT LTC BCH kPEPE WLD.
Data: Hyperliquid daily perp candles (UTC), hourly funding & premium. Test window 2023-11-01 -> 2026-11-10 (>=10 coins live).

## E6a Residual liquidation snap-back (6 trials: k in {1.5, 2.0, 2.5} x {plain, forced-flow confirmed})
DECOMPOSITION: r_it = beta_i * MKT_-i,t + e_it, MKT_-i = equal-weight return of the OTHER live coins (leave-one-out);
 beta_i from rolling 60d OLS through t-1; sigma_e from rolling 60d residual stdev through t-1. Shared forces stripped:
 crypto market beta (dominant factor). Sector not modelled -> checked via mean pairwise residual correlation (< 0.10 required).
RESIDUAL TRADED: e_i only. Long coin perp + short beta*EW basket of the other coins (or the mirror for shorts).
PAYER: forced liquidations / deleveraging concentrated in one coin push its residual beyond fair value; liquidity
 providers who absorb it are paid by the snap-back. Confirmation variant: that day's coin funding below the cross-
 sectional median (longs flushed) for longs / above median for shorts.
Signal at daily close t: z = e_it/sigma_e < -k -> long residual; z > +k -> short residual.
Exit: close of first day the position's residual return is > 0, or after 5 days. One position per coin.
P&L = sign*(sum r_i - beta*sum MKT_-i) + funding (long pays coin funding; short basket receives beta*avg funding) - costs.
Costs round trip: coin 2*(4.5 taker + slip; slip 1bp BTC/ETH/SOL, 5bp others) + basket beta*2*(4.5+3). Stress 2x.
## E6b Residual funding carry (1 trial)
DECOMPOSITION: strips the market-wide funding level (the S1 factor) by cross-sectional demeaning.
RESIDUAL TRADED: f_i(7d mean) - cross-sectional mean. Weekly (Mon 00:00 UTC): short the 5 highest-residual-funding perps,
 long the 5 lowest, each side beta-weighted to be market neutral (sum beta*w = 0), hold 7 days.
PAYER: coin-specific leverage demand (crowded longs in a single name pay funding and tend to unwind).
P&L = price residual + funding received - costs (round trip 2*(4.5+5)bp per leg).
## Gates
RULES.md R1 residual_gate (|beta|<0.10, R^2<0.10, residual t>=2, mean resid corr<0.10, n>=200, top coin <=25%) AND
R0: win >= 65% (E6a only; E6b is a weekly portfolio -> report weekly hit rate, gate 60%), mean>0 at 2x costs,
1-day delayed entry > 0, both halves > 0, plateau across k (E6a: >=2 of 3 k values positive & t>1.5 for the chosen
variant family), worst trade reported and > -15% of notional, random-timing null p<0.05 (E6a), DSR(61) >= 0.95.
