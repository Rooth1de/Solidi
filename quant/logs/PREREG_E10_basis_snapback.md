# E10 — Hyperliquid perp-vs-oracle basis snap-back. Pre-registered 2026-11-11 (Guild cycle 1, Alchemist), before results.
Cumulative trials before: 68. E10 adds 2 -> 70.
Seer setup: when a coin's perp trades at a large premium/discount to its spot oracle, a delta-neutral position
 (perp vs spot) captures the basis snap-back. Residual by construction: perp and spot share all market/sector/coin beta;
 only the dislocation is traded. Payer: forced liquidations / one-sided perp flow pushing the perp away from spot;
 arbitrageurs paid for closing it.
Data: Hyperliquid fundingHistory hourly `premium` (perp vs oracle) and fundingRate, 20 coins (E6 universe), 2023-05 -> 2026-11.
Trigger at hour t: |premium_t| > X. premium < -X: LONG perp / SHORT spot; premium > +X: SHORT perp / LONG spot.
Exit: first hour with |premium| <= 5bp, or 24h time stop. P&L = sign*(premium_entry - premium_exit) + funding
 (long perp pays fundingRate, short perp receives) - costs. Costs round trip 30bp (perp taker 4.5bp x2 + spot 10bp x2),
 stress 60bp. Delay test: enter at hour t+1 premium. One position per coin.
Trials: X = 30bp, X = 50bp.
Caveat (Paladin to weigh): the API `premium` is the funding-premium sample, not a guaranteed executable basis;
 shorting spot for discount trades needs borrow (report long-perp and short-perp sides separately).
Process simulation (R2): hourly time-machine replay, all 20 coins scanned every hour and logged; crypto regimes:
 BTC trend (vs 200d MA), BTC 30d realised-vol tercile (expanding), cycles 2023H2, 2024, 2025, 2026.
Gates: R1 residual_gate (P&L beta to EW crypto market |b|<0.10, R^2<0.10, resid t>=2, n>=200, top coin<=25%),
 R0 (win>=65%, 2x cost>0, delay>0, both halves>0, X plateau, worst trade > -5% notional, DSR(70)>=0.95),
 R2 (positive in >= 3 of 4 cycles and in both BTC trend regimes).
