# Round 2 report (2026-11-11)
Families tested: F2 TOM, F3 pension rebalancing, F4 short vol w/ term-structure filter, F5 VIX-conditioned pooled reversal,
F7 post-panic re-leveraging, F8 PutWrite. Cumulative trials 29 (see PREREG_round2.md, written before each run).
Survivors promoted to paper: NONE. Watchlist: F7, F5-RSI2.
Scripts: research/f2_tom.py f3_pension.py f4_shortvol.py f5_f7.py f5_f7_break.py; results in experiments.jsonl.
Binding constraint: data. Daily OHLC from Yahoo only. The highest-quality high-win-rate structural edges
(closing-auction imbalance fades, index-rebalance/reconstitution flow, options VRP with defined risk, overnight
drift) need intraday, auction-imbalance, constituent-change, or option-chain data.
