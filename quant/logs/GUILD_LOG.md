# Guild decision record

## Cycle 1 — 2026-11-11 (cumulative trials 68 -> 70)
### Ranger (raw ideas only)
R-1 Intraday entry on market-stress days (E9 mechanism caught earlier in the day).
R-2 Hyperliquid perp-vs-oracle basis dislocations after liquidation bursts.
R-3 Crypto residual CONTINUATION (seen in E6a/E8/G2).
R-4 Funding-carry book switched off on E9 stress days.
R-5 Monthly-opex dealer-hedging pin / unpin.
### Seer (setups)
R-1 -> needs multi-year intraday US equity data: not reachable free (GitHub only 6-month samples). PARKED (data).
R-2 -> SETUP E10: |premium| > X, delta-neutral perp vs spot, exit |premium|<=5bp or 24h; residual by construction
       (perp and spot share all beta); payer = forced liquidations / one-sided perp flow. Sent to Alchemist.
R-3 -> direction was learned from the same data (contaminated); only forward data is clean. PARKED (contamination).
R-4 -> a risk overlay on a factor premium (S1), not alpha under R1. PARKED (not residual).
R-5 -> payer plausible (dealer gamma) but needs options OI data: not available free. PARKED (data).
### Alchemist (E10, pre-registered logs/PREREG_E10_basis_snapback.md, hourly time-machine replay 2023-06 -> 2026-11)
X=30bp: n206, win 96.6%, +36.5bp, t 7.1, both halves +, all 4 cycles +, both BTC regimes +, R1 gate PASSED
 (beta -0.007, R^2 0.007, resid t 7.1, top coin 23%), DSR 1.00. 2x cost (60bp): +6.5bp (t 0.2).
X=50bp: n46 (fails n>=200, top-coin 31%) -> fails R1.
Realistic variant (entry at next hour's premium = executable proxy): 30bp cost win 77.7% +22.4bp t 3.5;
 40bp 68.3% +12.4; 45bp 64.4% +7.4; 50bp 54.5% +2.4; 60bp 38.6% -7.6. Breakeven ~52bp round trip.
 By year (realistic): 2023 +24, 2024 +24, 2025 -7 (n21), 2026 +55 (n10). 64% of trades exit on the 24h stop.
Alchemist verdict: X=30 passes all pre-registered gates on the base spec; edge is cost-sensitive.
### Paladin (risk veto review)
Concerns: (1) `premium` is Hyperliquid's hourly-averaged impact-vs-oracle funding premium, not a guaranteed
 executable basis -> the instant-entry result (96.6%) is not credible; only the 1h-delayed variant is accepted.
 (2) Edge ~1.7x base costs, gone at ~52bp; real spot+perp costs for alts during dislocations are uncertain.
 (3) 2025 negative; events becoming rarer (97 in 2023H2 -> 10 in 2026).
 (4) Discount side needs alt-spot borrow -> not feasible; restricted to SHORT perp / LONG spot (n147, win 81%, +23bp).
 (5) Venue tails absent from data: manipulated-perp settlement, ADL, oracle faults.
Ruling: NO VETO on PAPER; VETO on any capital. Conditions: short-perp/long-spot only; forward shadow log of
 executable basis (HL impactPxs vs oraclePx, plus quoted spot cost) at entry/exit; kill if forward realised
 round-trip cost > 40bp or forward mean net < 0 after 30 trades.
### Guild Master
E10 (S2) -> APPROVED FOR PAPER ONLY (restricted, shadow mode). R-1, R-3, R-4, R-5 -> PARKED (backlog).
Escalations to the human: (a) allowlist free data hosts datafeed.dukascopy.com and data.binance.vision (unblocks
 R-1 intraday and long crypto minute history); (b) approve a daily scheduled job for S2 shadow logging.
