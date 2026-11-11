# Crypto intraday research dashboard

Engine: `quant/crypto/engine.py` (deterministic; taker 5bp / maker 2bp per side, slippage 1bp BTC/ETH, 2bp alts, funding at settlement).
Data: Binance USD-M perps, 1m klines 2023-01..2026-10. Gate 1/2 in-sample = 2023-2024; walk-forward = 180d train / 30d trade; 2025-26 never used for idea selection.
Ranking: gates cleared, then walk-forward Sharpe x net bp/trade.

| # | Candidate | Symbols | TF | G1 Sharpe | G1 trades | G1 win | G1 net/gross bp | G2 p | G3 OOS Sharpe | G3 net bp | G3 win | G4 p | Verdict | Precise reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | shock | SOL | 5m | 1.18 | 303 | 0.558 | 17.0 / 30.92 | 0.022 | -0.17 | -3.49 | 0.504 | - | **KILLED at gate3** | walk-forward OOS Sharpe -0.17, net -0.1502, -3.49bp/trade; 2025-26 net -0.413 |
| 2 | oiflush-maker-pool6 | pool-6 | 5m | 1.35 | 401 | 0.584 | 31.66 / 40.18 | - | - | - | - | - | **ALIVE - passed gate 1, next gate pending** | awaiting next gate |
| 3 | oiflush-pool6 | pool-6 | 5m | 1.18 | 408 | 0.551 | 27.23 / 40.21 | - | - | - | - | - | **ALIVE - passed gate 1, next gate pending** | awaiting next gate |
| 4 | shock-maker-pool6 | pool-6 | 5m | 1.05 | 637 | 0.614 | 24.97 / 33.56 | - | - | - | - | - | **ALIVE - passed gate 1, next gate pending** | awaiting next gate |
| 5 | shock-pool6 | pool-6 | 5m | 0.94 | 649 | 0.601 | 22.23 / 35.66 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.94 < 1.0 |
| 6 | funding | ETH | 15m | 0.78 | 336 | 0.533 | 11.98 / 23.98 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.78 < 1.0; maxDD -0.3432 |
| 7 | session | SOL | 15m | 0.78 | 730 | 0.471 | 9.41 / 23.41 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.78 < 1.0; maxDD -0.3458 |
| 8 | shock | BTC | 5m | 0.77 | 287 | 0.551 | 7.72 / 19.61 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.77 < 1.0; no plateau: neighbour median Sharpe -0.03 |
| 9 | funding | SOL | 15m | 0.7 | 656 | 0.498 | 12.37 / 26.37 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.7 < 1.0; maxDD -0.735 |
| 10 | funding | BTC | 15m | 0.58 | 371 | 0.461 | 5.44 / 17.44 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.58 < 1.0; maxDD -0.3106 |
| 11 | session-maker-pool6 | pool-6 | 15m | 0.36 | 4156 | 0.467 | 2.77 / 11.44 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.36 < 1.0; trade PF 1.06 < 1.1; no plateau: neighbour median Sharpe -0.19 |
| 12 | flow | ETH | 5m | 0.26 | 187 | 0.39 | 2.15 / 14.15 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.26 < 1.0; trades 187 < 200; trade PF 1.08 < 1.1; no plateau: neighbour median Sharpe -0.55 |
| 13 | session | ETH | 15m | 0.21 | 730 | 0.449 | 1.58 / 13.58 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.21 < 1.0; trade PF 1.042 < 1.1; maxDD -0.2696; no plateau: neighbour median Sharpe -0.71 |
| 14 | funding-maker-pool6 | pool-6 | 15m | 0.16 | 552 | 0.507 | 3.05 / 11.95 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.16 < 1.0; trade PF 1.049 < 1.1; no plateau: neighbour median Sharpe -0.3 |
| 15 | shock | ETH | 5m | 0.07 | 130 | 0.523 | 1.47 / 13.39 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe 0.07 < 1.0; trades 130 < 200; trade PF 1.029 < 1.1; no plateau: neighbour median Sharpe -0.4 |
| 16 | funding-pool6 | pool-6 | 15m | -0.03 | 580 | 0.5 | -0.5 / 13.31 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -0.03 < 1.0; trade PF 0.992 < 1.1; no plateau: neighbour median Sharpe -0.49 |
| 17 | session-pool6 | pool-6 | 15m | -0.04 | 4380 | 0.451 | -0.22 / 13.11 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -0.04 < 1.0; trade PF 0.995 < 1.1; maxDD -0.3303; no plateau: neighbour median Sharpe -0.69 |
| 18 | oibuild-maker-pool6 | pool-6 | 5m | -0.09 | 802 | 0.519 | -0.86 / 7.85 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -0.09 < 1.0; trade PF 0.985 < 1.1; no plateau: neighbour median Sharpe -0.83 |
| 19 | session | BTC | 15m | -0.26 | 730 | 0.427 | -1.57 / 10.43 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -0.26 < 1.0; trade PF 0.952 < 1.1; maxDD -0.3259; no plateau: neighbour median Sharpe -0.67 |
| 20 | oibuild-pool6 | pool-6 | 5m | -0.5 | 651 | 0.525 | -7.13 / 6.11 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -0.5 < 1.0; trade PF 0.908 < 1.1; no plateau: neighbour median Sharpe -1.0 |
| 21 | flow | SOL | 5m | -0.68 | 19 | 0.579 | -11.79 / 2.1 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -0.68 < 1.0; trades 19 < 200; trade PF 0.492 < 1.1; no plateau: neighbour median Sharpe 0.0 |
| 22 | leadlag | ETH | 1m | -0.77 | 104 | 0.221 | -9.19 / 2.87 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -0.77 < 1.0; trades 104 < 200; trade PF 0.662 < 1.1; no plateau: neighbour median Sharpe -1.72 |
| 23 | flow | BTC | 5m | -1.03 | 3 | 0.0 | -82.08 / -70.42 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -1.03 < 1.0; trades 3 < 200; trade PF 0.0 < 1.1; no plateau: neighbour median Sharpe 0.0 |
| 24 | leadlag | SOL | 1m | -1.06 | 91 | 0.396 | -17.92 / -3.82 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -1.06 < 1.0; trades 91 < 200; trade PF 0.575 < 1.1; no plateau: neighbour median Sharpe -1.77 |
| 25 | flow-maker-pool6 | pool-6 | 5m | -2.74 | 85 | 0.271 | -23.18 / -14.33 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -2.74 < 1.0; trades 85 < 200; trade PF 0.184 < 1.1; no plateau: neighbour median Sharpe -2.34 |
| 26 | flow-pool6 | pool-6 | 5m | -2.96 | 93 | 0.247 | -24.06 / -10.43 | - | - | - | - | - | **KILLED at gate1** | IS Sharpe -2.96 < 1.0; trades 93 < 200; trade PF 0.192 < 1.1; no plateau: neighbour median Sharpe -2.63 |

Total candidates: 26 | survivors: 0 | parameter sets evaluated: 2340
