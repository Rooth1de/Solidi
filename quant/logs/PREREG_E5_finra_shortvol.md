# E5 — FINRA daily short-sale volume as a liquidity-provision / retail-flow signal. Pre-registered 2026-11-11.
STATUS: blocked on data access (cdn.finra.org not in this environment's allowlist). Not run. Cumulative before: 52; E5 adds 2 -> 54.
Data (free): FINRA Reg SHO daily consolidated short-sale volume files (CNMSshvol*.txt; ShortVolume/TotalVolume per
symbol per day), Yahoo daily prices, point-in-time S&P 500 membership (fja05680/sp500). Sample: all files available.
Payer / rationale: off-exchange short volume is dominated by wholesalers/market makers selling short to fill retail
BUY orders (liquidity provision); an abnormal short-volume ratio = abnormal retail order imbalance that market makers
absorb and are compensated for (Boehmer, Jones, Zhang & Zhang 2021 JF "Tracking Retail Investor Activity";
Boehmer, Jones & Zhang 2008). Less crowded than price patterns: requires a separate daily data pipeline.
Question (calibrated harness form): for S&P 500 members (PIT), close > $10, at close t: SPY-hedged long bracket and
short bracket, TP = 0.5*sigma_5d, SL = 1.0*sigma_5d (sigma from 60d idio vol), horizon 5 days, conservative ties.
Features (5): SVR_z = (short vol ratio - 20d mean)/20d sd; SVR_z 5d avg; idio 5d return z; log dollar volume z;
VIX prior close. Model: multinomial logit, L2=1, monthly WF refit (expanding), first 24 months training.
Base rates per stock (trailing 250 completed windows, Laplace); Brier-fitted blend; EV gate >= 0.05R; costs 5bp/side
stock + 1bp hedge; max 10 concurrent, 1 per stock, 0.5% risk per trade.
Variants: horizon 5d and 10d -> 2 trials.
Gates: identical to E3 (G1-G9), plus a placebo: shuffle SVR across stocks within each day -> skill must vanish.
