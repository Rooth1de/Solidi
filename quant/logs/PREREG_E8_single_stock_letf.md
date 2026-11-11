# E8 — Single-stock leveraged-ETF close pressure: overnight residual reversal. Pre-registered 2026-11-11. NOT YET RUN.
Cumulative trials before: 64. E8 adds 2 -> 66.
Why: H2 confirmed the LETF close-pressure mechanism on index ETFs (+2.9bp, t 2.9) but too small vs costs. Single-stock
2x/3x LETFs (TSLL, NVDL, CONL, MSTX/MSTU, etc.) are large relative to their underlying's float/volume, so the forced
rebalance (proportional to AUM*L*(L-1)*daily return, executed at the close) should be far larger per name.
Names (fixed): TSLA, NVDA, COIN, MSTR, PLTR, AMD, SMCI, AAPL, AMZN, META, MSFT, GOOGL (those with >= 1 single-stock
LETF); event days only while an LETF existed (first LETF listing date taken from Yahoo history start of the LETF).
DECOMPOSITION: residual day return e = r_stock - beta*r_QQQ (beta 120d through t-1); overnight residual
 e_on = (open_{t+1}/close_t - 1) - beta*(QQQ open/close - 1). Strips market/tech-sector beta (QQQ).
RESIDUAL TRADED: e_on only (stock vs beta*QQQ), MOC entry at close t, MOO exit at open t+1.
PAYER: LETF issuers' forced end-of-day rebalancing in the direction of the day's move -> close overshoots -> reverts overnight.
Signal: |e_t|/sigma_e > k, trade opposite sign. k in {1.5, 2.0} -> 2 trials. Costs 3bp/side stock + 1bp/side QQQ, stress 2x.
Proxy for flow size (reported, not traded): LETF dollar volume / stock dollar volume.
Gates: RULES.md R1 + R0 (win >= 65%, 2x cost > 0, both halves of available sample > 0, plateau k, n >= 200, top name
<= 25% of P&L, random-day null p < 0.05, DSR(66) >= 0.95). Mechanism check: up-day and down-day both reverse.
