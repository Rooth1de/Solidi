# Permanent research rules
## R0 (round 1+) Aggressive skepticism: pre-register, count trials cumulatively, OOS only, costs, delay, plateau, tails, DSR.
## R1 (2026-11-11) Residual-First Discipline — applies to every candidate from E6 onward
Before any test, each candidate must state:
 (a) DECOMPOSITION: which shared forces could explain the edge (market beta, sector, style/carry factors,
     liquidity/vol regime) and how they are stripped (factor model, hedge, cross-sectional demeaning).
 (b) RESIDUAL: the exact residual series that is traded (idiosyncratic part only).
 (c) PAYER: who is forced or overreacting in the residual (forced flow, liquidation, temporary liquidity shock).
Preferred form: snap-back / mean-reversion of the residual after forced flow or overreaction.
Automatic rejection (research/residual.py: residual_gate) if ANY of:
 - trade P&L beta to the market factor |b| >= 0.10, or factor model R^2 of trade P&L >= 0.10
 - residual (hedged) P&L clustered t < 2.0 out-of-sample
 - mean pairwise correlation of model residuals >= 0.10 (factor model misses a shared force)
 - < 200 OOS trades (small samples are suspect by default), or one name > 25% of total P&L
 - fails any R0 gate (costs x2, 1-bar delay, both OOS halves, parameter plateau, win >= 65%, tail bound, DSR)
A strategy whose P&L is mainly a shared factor/premium may be kept only as a labelled FACTOR PREMIUM, never as alpha.

## R2 (2026-11-11) Historical Process Simulation — required for every serious candidate
A candidate must be replayed day-by-day by `timemachine/` with a fixed rule set:
 - The strategy only receives a point-in-time data view (PITView): any access to data after the decision date raises.
 - The universe on each date is what was knowable then (PIT index membership incl. delisted names where data exists;
   instruments only after they existed). Gaps in free data (e.g. missing delisted tickers) must be quantified.
 - EVERY scan result is logged (shown / signalled / traded / skipped-and-why), not only trades -> no cherry-picking.
 - Each date carries point-in-time regime labels: trend (bull / bear / transition), volatility (low / mid / high VIX
   terciles from an expanding window), drawdown state; plus named market cycles.
 - Reports: performance by regime and by cycle. A strategy positive in only one regime type is INCOMPLETE.
 - If multi-decade replay is impossible with available data, the candidate file must say why and what proxy (longer-
   history analogue of the same mechanism) was simulated instead.
`timemachine.reviewer.show(date)` reconstructs what the process displayed on any past date.
