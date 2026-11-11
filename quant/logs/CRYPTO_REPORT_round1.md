# Crypto intraday research — round 1 (2026-11-11)

**Result: 0 survivors. 1 watch-list near-miss. Nothing is promoted to paper trading.**
Full table: `CRYPTO_DASHBOARD.md`. Every run: `crypto_experiments.jsonl`.

## Engine (QuantPilot was not available in this session)
`quant/crypto/engine.py`, deterministic, self-tested (`selftest.py`).
- Data: Binance USD-M perpetual 1m klines + funding + 5m open interest, 2023-01-01..2026-10-31, six perps
  (BTC, ETH, SOL, XRP, DOGE, BNB), zero missing bars.
- Fills: signal on close of bar t, taker fill at open of t+1. Fees 5bp taker / 2bp maker per side (VIP0).
  Slippage per side 1bp (BTC, ETH), 2bp (others) for a $50k clip. Funding charged at settlement.
  Stop assumed before target inside one bar. Passive entry only counts if price trades 0.5bp through the limit.
- Open interest is used with a one-bar (5 min) publication lag.
- Gate 1/2 in-sample: 2023-2024. Walk-forward: 180d train -> 30d trade over the whole sample (OOS 2023-07..2026-10).
  2025-26 was not used to choose ideas, with one exception noted below.
- Permutation: Masters bar permutation, 500 runs, whole grid re-optimised on every run, same shuffle on all symbols.
- Pre-registered pass marks: G1 Sharpe>=1.0, >=200 trades, trade PF>=1.10, maxDD>-25%, neighbours' median Sharpe>0;
  G2 p<0.05; G3 OOS Sharpe>=1.0 and positive net per trade; G4 p<0.01.

## What was tested and why it died
| Family | Idea | Outcome |
|---|---|---|
| H1 flow | Taker buy/sell imbalance, follow or fade (5m) | Dead at G1 on every symbol and pooled. No parameter set profitable after costs; gross edge <= 14bp vs 12-14bp round trip. |
| H2 shock | Fade or ride a >=3-5 sigma move on >=1.5-3x volume (5m) | SOL: G1 pass, G2 p=0.022, **G3 fail** (OOS Sharpe -0.17, 2025-26 net -41%). BTC/ETH dead at G1. Pooled taker dead at G1 (Sharpe 0.94). Pooled passive-entry: G1 pass, G2 p=0.026, **G3 fail** (OOS Sharpe -0.55, -10.8bp/trade). |
| H3 funding | Lean against extreme funding into settlement (15m) | Dead at G1. Gross 13-26bp/trade but Sharpe 0.6-0.8 and drawdowns of 31-74% single-name; pooled net ~0. |
| H4 session | Fixed UTC window drift (15m) | Dead at G1. 21:00-01:00 UTC long is the best window on all three majors (gross 10-23bp) but costs take all of it. |
| H5 lead-lag | BTC shock -> alt that has not caught up (1m) | Dead at G1. Gross ~3bp; nothing at 1m clears costs. |
| H6 oiflush | Fade a sharp move while open interest collapses (5m, pooled) | G1 pass, G2 p=0.008, **G3 fail** (OOS Sharpe 0.26, 22 different parameter sets picked across 40 folds). |
| H7 oibuild | Ride/fade a sharp move while open interest expands | Dead at G1 (gross 6-8bp). Useful contrast: only OI *collapse* carries an edge. |
| H6b oiflush_long | H6, long side only, 16-set grid | G1 pass, G2 p=0.002, **G3 fail by a hair** (OOS Sharpe 0.94 < 1.0). Watch-list. |

Lessons: (1) at taker costs nothing on 1m-5m momentum/flow survives; the only gross edges above 30bp/trade are
reversals after forced liquidation. (2) Single-symbol results that pass the in-sample permutation test still die
out of sample. (3) Win rate was 53-61% on every candidate that got past Gate 1; none needed or had 70%+.

## Watch-list: H6b long-only liquidation flush (NOT promoted)
Rules (5m bars, each of the six perps independently, equal notional):
1. r = log return over the last N bars; z = r / (trailing-24h std of 5m returns x sqrt(N)).
2. dOI = change in log open interest over N bars, measured up to the previous bar.
3. If z < -Z and dOI < -Q: buy at the next bar's open (taker).
4. Stop: entry x (1 - |r|). Otherwise exit at the open after H bars. No target. No shorts.
Grid tested: N in {12, 24}, Z in {3, 4}, Q in {1%, 2%}, H in {6, 12} (16 sets). In-sample best: N=24, Z=4, Q=2%, H=6.

| Gate | Result |
|---|---|
| 1 in-sample | Sharpe 1.37, 285 trades, win 60%, +42.7bp net/trade (55.7 gross), trade PF 1.97, maxDD -4.8%, 15/16 sets profitable |
| 2 permutation | p = 0.002 (real 1.37 vs permuted 95th pct 0.38) |
| 3 walk-forward | **FAIL**: Sharpe 0.94, 565 trades (0.47/day), win 56%, +39.9bp/trade, t 2.52, maxDD -10.6%, 20/40 folds up. By year net: 2023 +5.8%, 2024 +22.2%, 2025 +10.8%, 2026 -1.2% |
| 4 WF permutation (diagnostic only) | p = 0.002 (real 0.94 vs permuted median -0.81) |

Average hold 41 min. Returns are per unit of book notional; exposure is 0.8% of bars.
Why it might be real: forced liquidations are price-insensitive sellers; once open interest has already dropped,
the forced flow is spent and resting bids get paid for providing liquidity. The mirror case (OI expanding) shows no edge.
Why it is not promoted:
- Failed the pre-registered Gate 3 mark, and 2026 is negative in walk-forward.
- BTC and ETH contribute ~0; the result is carried by SOL, XRP, DOGE, BNB with 42-91 trades each.
- Entering one bar (5 min) late cuts net per trade from 49bp to 19bp.
- The long-only restriction was chosen after seeing that shorts lost, including a full-sample diagnostic that
  covered 2025-26. Treat its 2025-26 numbers as mildly contaminated.
- Worst single trade -16%: the stop is far away by construction.

## Next round (pre-registered before running)
1. H6c: flush fade on a wider alt universe (top-20 perps by volume) with the same 16-set grid; the claim to test is
   "works on alts, not on BTC/ETH". New symbols are a clean out-of-sample test.
2. H6d: replace the fixed 2% OI drop with liquidation prints if a liquidation feed can be sourced.
3. Execution: 1m entry timing after the 5m signal, since delay sensitivity is the main fragility.
4. Re-validation rule if anything is ever promoted: weekly rerun of Gates 3-4 on the extended sample; demote on
   WF permutation p > 0.05 or two consecutive negative 30-day folds.
