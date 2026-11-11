# E9 — Market-stress residual snap-back, PIT S&P 500, decades-long time-machine replay. Pre-registered 2026-11-11. NOT YET RUN.
Cumulative trials before: 66. E9 adds 2 -> 68.
Motivation from the dead register: idiosyncratic shocks continue (news). This tests residual dislocations created by
NON-idiosyncratic forced flow: on market-wide deleveraging days (SPY < -2% AND VIX up > 15%), liquidity withdrawal
(Nagel 2012) dislocates stocks' residuals for reasons unrelated to their own news.
DECOMPOSITION (point-in-time): e = r - b_m*SPY - b_s*SECTOR, SECTOR = the SPDR sector ETF (XLB..XLY, 9 ETFs) with the
 highest trailing 250d correlation to the stock as of t-1 (free, PIT sector assignment); betas 120d through t-1.
RESIDUAL TRADED: long the 10 most negative residual-z stocks among PIT S&P 500 members on stress days (close > $10),
 each hedged with -b_m SPY and -b_s SECTOR; exit at the first close with positive residual, max 5 days.
PAYER: deleveraging sellers (risk-parity, vol-targeting, margin calls) dumping liquid names irrespective of news.
Trials: (1) as above, (2) top 20 instead of top 10.
PROCESS SIMULATION (R2): timemachine.Run over 2004-01 -> 2026-11, PIT membership incl. delisted names where Yahoo has
 data (coverage 64% in 2003 -> 100% 2026, reported per year); every stress-day scan logged with all ranked names;
 regime/cycle tables (GFC, 2011, 2015-16, 2018Q4, 2020, 2022, 2025-04 expected to dominate event count).
 Survivorship stress: missing-name haircut as in G2. Costs 5bp/side stock + 1bp/side per ETF hedge, stress 2x.
Gates: R1 residual_gate + R0 (win >= 65%, 2x cost > 0, delay 1d > 0, plateau top10/top20, positive in >= 4 of the
 6 named stress cycles, n >= 200, DSR(68) >= 0.95, random-stress-day null p < 0.05).
