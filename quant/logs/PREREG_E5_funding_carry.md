# E5 — Delta-neutral perp funding carry with a calibrated entry gate. Pre-registered 2026-11-11, before fetching results.
(Replaces FINRA E5, which stays parked: cdn.finra.org blocked.) Cumulative trials before: 52. E5 adds 2 -> 54.
Data: Hyperliquid public API (api.hyperliquid.xyz, free, already allowlisted): hourly fundingRate and premium
(perp vs oracle spot index) per coin, May 2023 -> Nov 2026. Coins (liquid, spot-hedgeable): BTC ETH SOL XRP DOGE AVAX LINK.
Payer: leveraged longs pay funding to shorts (structural demand for leverage). Trade: SHORT perp + LONG spot (delta-neutral).
P&L per $ notional over a hold from hour a to hour b:  sum(fundingRate over (a,b]) + (premium_a - premium_b) - costs.
 (Basis term: short perp gains if the perp premium over spot shrinks.) Costs round trip, both legs:
 base 30bp (perp taker 4.5bp + spot taker 10bp, x2 sides), stress 60bp.
Decision: daily at 00:00 UTC per coin when flat. Holds of H = 7 days and H = 30 days -> 2 trials. Non-overlapping per coin.
Calibrated gate (harness form): label = 1{net P&L over H > 0}. Features (3): mean funding last 24h (annualised),
mean funding last 7d, current premium. Per-coin base rate = trailing completed-window frequency of a positive net carry
(Laplace, >= 60 windows). Model: pooled logistic L2=1, monthly WF refit on completed labels; first training through
2023-11-30, OOS 2023-12 -> 2026-11. Blend w by Brier on prior OOS months. EV = p*E[win] - (1-p)*E[|loss|] with E[.]
from trailing completed trades of that coin (walk-forward). Enter if EV > 0.
Benchmarks reported alongside: (a) ALWAYS-ON carry (enter whenever flat), (b) simple rule: enter if 7d mean funding > 0.
Gates (all, OOS): win >= 65% net; mean net > 0 at 1x and 2x costs; trade t (clustered by entry week) >= 2.0;
both OOS halves > 0; entry delayed 1 day still > 0; >= 4 of 7 coins positive; worst trade and 5% CVaR reported,
worst trade > -5% of notional; DSR(54) >= 0.95; model Brier skill vs base reported (informational: a structural
premium may be harvestable from the base rate alone; the calibrated gate must not underperform always-on).
Known risks not in the data: exchange/custody failure, auto-deleveraging, spot borrow not needed (long spot).
