# Pre-registration, round 2 (written BEFORE running). 2026-11-11
Win-rate filter added: per-trade net hit rate >= 65% required, plus all round-1 gates.
Gates: OOS alpha/mean t>=2 (or random-null p<0.05 AND t>=1.7 with breadth), survives 5bp/side,
plateau across grid, DSR>=0.95 with cumulative trial count, no single-trade/period dependence,
tail: worst trade loss <= 10x avg trade expectancy or explicit stop justified.
Cumulative trials before this round: 10.

F2 TURN-OF-MONTH (TOM). Payer: month-end/start inflows (payroll, 401k, pension contributions,
 index fund cash reinvestment) -> predictable buying in days -1..+3. Lit: Ariel 1987, Lakonishok&Smidt 1988,
 McConnell&Xu 2008 (31/35 countries); Han,Han&Tian 2025 "disappearing TOM" -> decay risk.
 Rule: long SPY earning days [-a .. +b] of month. Grid (a,b) in {(1,3),(2,3),(1,2),(2,2)}  -> 4 trials.
 Crowding: extremely well known, trivially codeable -> expect decay; demand post-2008 evidence.

F3 PENSION/CALENDAR REBALANCING. Payer: pensions/TDFs rebalancing on fixed calendar (forced,
 committee-bound, price-insensitive). Lit: Harvey, Mazzoleni, Melone (2024-25 WP). Effect claimed to be growing.
 Rule: at close of trading day -k, MTD(SPY)-MTD(TLT) = D. If D>thr: long TLT/short SPY (equal $), else if D<-thr reverse.
 Earn days -(k-1)..+1. Grid k in {3,5}, thr in {0, 0.02} -> 4 trials. All data is PRE-publication (no true post-pub OOS).

F4 SHORT VOL (VIX futures roll / term premium) with term-structure filter. Payer: hedgers paying insurance premium,
 structural demand for convexity. Lit: Simon&Campasano 2014, Dorries/Korn/Power 2023, NY Fed SR867.
 Rule: short VIXY (front-month VIX futures ETF) next day if VIX/VIX3M < x at close. Grid x in {0.90,0.95,1.00} -> 3 trials.
 Costs 5bp/side + 5%/yr borrow. Known to be short gamma: tail gate applies strictly. Disc 2011-2018, OOS 2019+.
Total this round 11 -> cumulative 21.

## Round 2b (added after F2-F4 died; written before running F5/F7)
F5 VIX-CONDITIONED REVERSAL, POOLED. Payer: liquidity providers earn more when intermediaries are constrained
 (Nagel 2012 RFS "Evaporating Liquidity": reversal returns predictable by VIX). High-win shape: exit on first strength.
 Universe: 15 equity ETFs, equal-weight sleeves. Entry E in {RSI2<10 (no trend filter), 3 down closes};
 exit close>SMA5 (RSI2) / first up close (streak), 5-day time stop. Condition C in {none, VIX > 252d median}. -> 4 trials.
 Disc 1999-2009, OOS 2010+. t-stats clustered by entry week. Crowding: high (RSI2 is retail-famous); conditioning is the only novelty.
F7 POST-PANIC RE-LEVERAGING. Payer: vol-target / risk-parity / VA hedgers forced to de-risk in spikes and mechanically
 re-buy as vol normalises (IMF 2018, ECB 2020 FSR). Event: first close with VIX/VIX3M<1 after >=3 closes >=1.
 Long SPY at close, hold h in {5,10,20} -> 3 trials. Breadth on QQQ/IWM/EFA (same events). Null: random entries, same h.
 Low event count (~2006+) -> low power; will report honestly.
Cumulative trials: 21 + 7 = 28.

## F8 PUTWRITE (CBOE PUT index), added before running. 1 trial, no parameters -> cumulative 29.
Payer: structural demand for downside insurance (VRP). Monthly ATM SPX put sale, T-bill collateral.
Test: monthly excess-over-cash (SHY proxy) win rate, beta-adjusted alpha vs SPY, tail, pre/post 2010. Impl. drag 0.5-1%/yr not in index.
