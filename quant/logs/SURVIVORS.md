# Survivors register
## S1 — E5 delta-neutral perp funding carry — RECLASSIFIED 2026-11-11 under R1: FACTOR PREMIUM, not alpha (common carry R^2 0.86). Found 2026-11-11 at cumulative trial 54.
Rule (simplest form that passed): daily 00:00 UTC per coin (BTC ETH SOL XRP DOGE AVAX LINK), if flat and the
calibrated P(net carry > 0) gives EV > 0 (in practice: recent funding clearly positive), SHORT Hyperliquid perp +
LONG spot, equal notional, hold 30 days. P&L = funding received + basis change - costs.
Who pays: leveraged longs paying for leverage (structural; persists but varies with the leverage cycle).
OOS evidence (2023-12 -> 2026-11, walk-forward, 30bp round-trip both legs):
 H30: 245 trades, win 82%, +0.94% per 30d (~11% APR on notional), week-clustered t 3.9, 2x cost +0.69%, 1d delay +0.94%,
 7/7 coins positive, worst -1.63%, 5% CVaR -1.0%, DSR(54) 1.00.  H7: win 66.6%, +0.29%/7d, t 4.5.
DECAY (critical): H30 mean by year 2023 3.5%, 2024 1.7%, 2025 0.37%, 2026 0.09%. Last 12 months: win 66%,
 +0.12%/30d at 30bp (+0.23% at 18bp maker-ish), NEGATIVE at 60bp. Mean funding fell from ~40-50% APR (2024Q1) to
 1-9% APR (2026). Consistent with crowding (Ethena-style basis capital) -> treat current edge as marginal.
Tails NOT in the data: auto-deleveraging of the short leg in crashes (breaks the hedge), venue/custody failure,
 spot/perp venue basis, margin calls on the perp leg in squeezes. Capital efficiency: ~1.2-1.3x notional in capital.
Promotion: PAPER ONLY. Sizing for paper: notional per coin <= 5% of equity (a 10% unhedged ADL shock = 0.5% equity).
Kill rules (pre-set): stop if trailing 90d realised net carry < 0, or mean funding across coins < 10% APR at entry
 (below that, 30bp costs consume the 30d carry), or any ADL/venue incident. No real capital without human approval.
