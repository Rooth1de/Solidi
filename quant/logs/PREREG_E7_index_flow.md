# E7 — S&P 500 deletion/addition forced-flow residual reversal. Pre-registered 2026-11-11 (before any E7 result).
Cumulative trials before: 61. E7 adds 3 -> 64.
Data: fja05680/sp500 point-in-time membership (event dates = membership change dates D), Yahoo daily adj. prices for
every PIT ticker Yahoo still serves (coverage reported), SPY. Events 2004-01 -> 2026-08.
Event day E = last trading day BEFORE D (index funds trade at E's close). Deletion: ticker in list before D, not at D.
Addition: ticker not in list before D, in list at D.
DECOMPOSITION: residual = stock return - beta*SPY return, beta from 120d OLS ending 10 days before E (standard event-study
 market model). Sector factor not available for free -> limitation flagged; checked via mean pairwise residual corr of
 concurrent events (< 0.10 required).
RESIDUAL TRADED: long (deletions) / short (additions) the stock, hedged with -beta (+beta) SPY, entry at close of E.
PAYER: index funds forced to sell (buy) at E's close regardless of price -> temporary residual dislocation that reverts
 as the forced flow ends (deletion rebound; addition reversal).
Trials: (1) deletions H=5 trading days, (2) deletions H=20, (3) additions (short residual) H=5.
Costs: 10bp/side stock + 1bp/side SPY hedge; stress 2x. Delay test: entry at close E+1.
Exclusions: price at E < $5; less than 120d history. Survivorship: events whose ticker Yahoo lacks are missing
 (mostly M&A/bankrupt deletions) -> report coverage; requiring H post-event bars is a survival condition (flagged).
Gates: R1 residual_gate (|beta|<0.10 & R^2<0.10 of daily P&L vs SPY, residual t>=2, mean resid corr<0.10, n>=200,
top name <= 25%) AND R0 (win >= 65%, mean>0 at 2x costs, delay>0, both halves (2004-2014 / 2015-2026) > 0,
H plateau (H=5 and H=20 same sign for deletions), worst trade > -25%, DSR(64) >= 0.95, random-date null p<0.05).
