# quant/ research harness
- `data/fetch.py` Yahoo v8 daily fetch (CSV cache, gitignored). Survivorship caveat: ETF universe is current-listed.
- `research/engine.py` signals, backtester (lag/cost aware), trade stats, beta-adjusted alpha, Deflated Sharpe, experiment logger.
- `research/h1_run.py` frozen-param disc/OOS; `research/h1_stress.py` cost, delay, cross-asset, random-timing null, shuffled-bar null, sweeps, concentration.
- `logs/experiments.jsonl` every experiment; `logs/DEAD_STRATEGIES.md` rejected list.
Run: `pip install numpy pandas scipy; cd quant/data && python fetch.py SPY QQQ ...; cd ..; python research/h1_stress.py`
Known limits: no intraday data, no options/vol data, no point-in-time single-stock universe, lag0 assumes MOC fill at an unknowable close.

## crypto/ intraday perp research (round 1)
- `crypto/fetch_binance.py`, `crypto/fetch_metrics.py` Binance USD-M archive -> `data/crypto/*.npz` (gitignored).
- `crypto/engine.py` deterministic simulator + bar permutation; `crypto/strategies.py` hypotheses and grids;
  `crypto/gates.py` 4-gate runner; `crypto/diag.py` stress tests; `crypto/dashboard.py` -> `logs/CRYPTO_DASHBOARD.md`.
- Run: `pip install numpy pandas numba; cd quant/crypto; python fetch_binance.py BTCUSDT ...; python selftest.py;
  python gates.py oiflush_long BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,DOGEUSDT,BNBUSDT --tf 5 --perms 500`
- Results: `logs/CRYPTO_REPORT_round1.md`.
