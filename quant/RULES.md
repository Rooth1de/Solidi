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
