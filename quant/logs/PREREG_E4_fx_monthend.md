# E4 — Month-end FX equity-hedge rebalancing flow (Melvin & Prins 2015 JFM). Pre-registered 2026-11-11.
Cumulative trials before: 50. E4: 2 variants -> 52.
Payer: international equity managers re-size currency hedges at the month-end WMR 4pm London fix (calendar-bound,
price-insensitive). If US equities outperformed the foreign market month-to-date, foreign holders of US stocks must
sell more USD forward (and US holders of foreign stocks buy back less foreign currency) -> USD weakens into the fix.
Data (Yahoo daily, 2004-2026): EURUSD=X/^STOXX50E, GBPUSD=X/^FTSE, JPY=X(USD/JPY)/^N225, AUDUSD=X/^AXJO,
CAD=X(USD/CAD)/^GSPTSE; SPY for US. Month-end days from SPY's trading calendar; FX/indices forward-filled to it.
Signal at close of trading day -k: D = MTD(SPY) - MTD(foreign local index), MTD from prior month-end close.
D>0 -> short USD vs that currency; D<0 -> long USD. Hold from FX close day -k to FX close on the last trading day
(Yahoo FX daily close is after the 16:00 London fix).
Variants: k=3 (primary), k=2. Equal-weight basket of 5 pairs = 1 trade per month. Costs 2bp/side/pair; stress 4bp.
Disc 2004-2014 (pre-publication), OOS 2015-2026 (post-publication).
Gates (all, OOS): monthly basket win >= 65%; mean > 0 at 1x and 2x costs; t >= 2.0; random-sign null p < 0.05;
1-day delayed entry still > 0; both OOS halves > 0; worst month reported; DSR(52) >= 0.95; >= 3 of 5 pairs positive.
